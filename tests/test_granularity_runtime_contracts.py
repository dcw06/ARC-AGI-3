"""Regressions for pinned links and offline complete-checkpoint construction."""
import copy
import hashlib
import importlib
import importlib.util
import os
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from collections import OrderedDict

from research.object_discovery_boundaries_v1 import granularity_runtime as R


class EnvironmentNames(unittest.TestCase):
    def verify(self,root,versions):
        lock=root/'lock.json';lock.write_text(json.dumps(versions))
        def installed(name):return versions[name]
        with patch.object(R.importlib.metadata,'version',side_effect=installed):
            return R.verify_environment(lock)

    def test_lowercase_wheel_metadata_names_are_valid(self):
        for pillow in ('pillow','Pillow','PILLOW'):
            with self.subTest(name=pillow),tempfile.TemporaryDirectory() as path:
                self.verify(Path(path),{'torch':'2.10.0+cpu','torchvision':'0.25.0+cpu','numpy':'2.5.4',pillow:'12.2.0'})

    def test_alias_duplicates_and_missing_required_packages_refuse(self):
        for versions in ({'torch':'1','torchvision':'1','numpy':'1'},
                         {'torch':'1','torchvision':'1','numpy':'1','pillow':'1','Pillow':'1'}):
            with tempfile.TemporaryDirectory() as path,self.assertRaises(ValueError):
                self.verify(Path(path),versions)


class SourceLinks(unittest.TestCase):
    def fixture(self, root):
        entry=copy.deepcopy(R.source_pin('unsamv2'))
        entry['runtime_directories']=['sam2/sam2']
        payload=b'pinned active model config\n'
        entry['files']={'sam2/sam2/configs/unsamv2_small.yaml':hashlib.sha256(payload).hexdigest()}
        active=root/'sam2/sam2/configs/unsamv2_small.yaml'
        active.parent.mkdir(parents=True);active.write_bytes(payload)
        for name,link in entry['symlinks'].items():
            (root/name).write_bytes(link['target'].encode())
        return entry

    def test_exact_pinned_archive_link_representation_and_active_config_verify(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);entry=self.fixture(root)
            self.assertEqual(len(entry['symlinks']),4)
            with patch.object(R,'source_pin',return_value=entry):
                R.verify_sources(root,'unsamv2')
                (root/'sam2/sam2/configs/unsamv2_small.yaml').write_bytes(b'changed')
                with self.assertRaises(ValueError):R.verify_sources(root,'unsamv2')

    @unittest.skipIf(os.name=='nt','real symlinks checked on Linux')
    def test_real_checkout_links_verify_and_modified_or_external_links_refuse(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);entry=self.fixture(root)
            for name,link in entry['symlinks'].items():
                path=root/name;path.unlink();path.symlink_to(link['target'])
            with patch.object(R,'source_pin',return_value=entry):
                R.verify_sources(root,'unsamv2_plus')
                first=root/next(iter(entry['symlinks']))
                first.unlink();first.symlink_to('/etc/passwd')
                with self.assertRaises(ValueError):R.verify_sources(root,'unsamv2_plus')

    def test_missing_legacy_link_or_new_target_cannot_silently_change_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);entry=self.fixture(root)
            name,link=next(iter(entry['symlinks'].items()))
            with patch.object(R,'source_pin',return_value=entry):
                path=root/name;path.unlink()
                with self.assertRaises(ValueError):R.verify_sources(root,'unsamv2')
                path.write_bytes(link['target'].encode())
                target=path.parent/link['target'];target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(b'new legacy config')
                with self.assertRaises(ValueError):R.verify_sources(root,'unsamv2')

    @unittest.skipIf(os.name=='nt','real symlinks checked on Linux')
    def test_unlisted_links_and_symlinked_runtime_directories_refuse(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);entry=self.fixture(root)
            with patch.object(R,'source_pin',return_value=entry):
                extra=root/'sam2/sam2/unlisted.yaml';extra.symlink_to('/etc/passwd')
                with self.assertRaises(ValueError):R.verify_sources(root,'unsamv2')
                extra.unlink()
                runtime=root/'sam2/sam2';runtime.rename(root/'sam2/real-runtime')
                runtime.symlink_to('real-runtime',target_is_directory=True)
                with self.assertRaises(ValueError):R.verify_sources(root,'unsamv2')


@unittest.skipUnless(importlib.util.find_spec('torch'),'optional CPU Torch dependency')
class OfflineSemanticBuilder(unittest.TestCase):
    def run_builder(self,root,*,missing=False,wrong_shape=False,direct_ordered_state=False):
        import torch
        source_config={'MODEL':{'BACKBONE':{'LOAD_PRETRAINED':True,'PRETRAINED':'https://invalid.example/swin.pth'}}}
        class Network(torch.nn.Module):
            def __init__(self):
                super().__init__();self.backbone=torch.nn.Linear(2,2)
        expected=Network()
        weights={'model.'+k:v for k,v in expected.state_dict().items()}
        if missing:weights.pop('model.backbone.weight')
        if wrong_shape:weights['model.backbone.weight']=torch.zeros((1,1))
        checkpoint=root/'segmentation.pth'
        torch.save(OrderedDict(weights) if direct_ordered_state else {'model':weights},checkpoint)
        events=[]
        def build_model(config):
            # An empty cache / denied network must make no difference: the
            # URL-preload branch is disabled before constructing the backbone.
            if config['MODEL']['BACKBONE']['LOAD_PRETRAINED']:
                raise AssertionError('undeclared backbone download attempted')
            self.assertEqual(config['MODEL']['BACKBONE']['PRETRAINED'],'')
            events.append('build without preload');return Network()
        class Wrapper:
            def __init__(self,config,network):self.model=network
            def eval(self):events.append('eval');return self
            def cuda(self):events.append('cuda stub');return self
        upstream=SimpleNamespace(build_model=build_model,
            build_semantic_sam=lambda **kwargs:(_ for _ in ()).throw(AssertionError('convenience builder called')))
        real_import=importlib.import_module
        def modules(name,*args,**kwargs):
            if name=='utils.arguments':return SimpleNamespace(load_opt_from_config_file=lambda file:source_config)
            if name=='semantic_sam.BaseModel':return SimpleNamespace(BaseModel=Wrapper)
            return real_import(name,*args,**kwargs)
        with patch.object(R.importlib,'import_module',side_effect=modules):
            result=R.build_semantic_offline(root,checkpoint,upstream)
        self.assertTrue(source_config['MODEL']['BACKBONE']['LOAD_PRETRAINED'])
        for name,value in expected.state_dict().items():
            self.assertTrue(torch.equal(result.model.state_dict()[name],value))
        self.assertEqual(events,['build without preload','eval','cuda stub'])

    def test_cold_cache_build_disables_download_and_loads_all_backbone_weights(self):
        with tempfile.TemporaryDirectory() as folder:self.run_builder(Path(folder))

    def test_direct_ordered_state_dictionary_is_supported(self):
        with tempfile.TemporaryDirectory() as folder:self.run_builder(Path(folder),direct_ordered_state=True)

    def test_missing_backbone_weights_cannot_fall_back_to_random_initialization(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'cover every model/backbone tensor'):
                self.run_builder(Path(folder),missing=True)

    def test_mismatched_backbone_weights_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'cover every model/backbone tensor'):
                self.run_builder(Path(folder),wrong_shape=True)


if __name__=='__main__':unittest.main()
