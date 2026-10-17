"""Synthetic packaging/finalization fixtures only; never calls GPU or Kaggle."""
import io
import json
from pathlib import Path
import tempfile
import tarfile
import time
import unittest
from unittest.mock import patch
from scripts import build_semantic_smoke as B
from research.object_discovery_boundaries_v1 import semantic_smoke as S
from tests.archive_transport_fixture import build


class Builder(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        data,pin,original,contents=build(self.root/'input')
        archive=self.root/'worker.tar'
        name='research/object_discovery_boundaries_v1/__init__.py'
        raw=(B.ROOT/name).read_bytes()
        with tarfile.open(archive,'w') as packed:
            member=tarfile.TarInfo(name); member.size=len(raw); packed.addfile(member,io.BytesIO(raw))
        raw=archive.read_bytes(); pin=B.digest(raw)
        data['originals'].append(dict(name='reviewed-worker-source.tar',bytes=len(raw),sha256=pin,mode='unchanged',
            chunks=[dict(name='reviewed-worker-source.tar',offset=0,payload_bytes=len(raw),stored_bytes=len(raw),sha256=pin)]))
        inventory={row['name']:dict(bytes=row['bytes'],sha256=row['sha256']) for row in data['originals'] if row['name']!='upload-manifest.json'}
        original_raw=B.canonical(inventory); original=B.digest(original_raw)
        original_row=next(row for row in data['originals'] if row['name']=='upload-manifest.json')
        original_row.update(bytes=len(original_raw),sha256=original)
        original_row['chunks'][0].update(payload_bytes=len(original_raw),stored_bytes=len(original_raw),sha256=original)
        data['original_payload_manifest_sha256']=original
        manifest_raw=B.canonical(data)
        (self.root/'transport.json').write_bytes(manifest_raw)
        receipt=dict(verified=True,provider_status='COMPLETE',all_pinned_hashes_match=True,
            temporary_originals_removed=True,mounted_transport_files_checked=21,restored_originals_checked=12)
        receipt_raw=B.canonical(receipt); (self.root/'cpu.json').write_bytes(receipt_raw)
        self.protocol=dict(schema='semantic_sam_gpu_smoke_protocol_v1',scope=S.SCOPE,
            competition_sources=['arc-prize-2026-arc-agi-3'],
            dataset_version=1,dataset_ref='daichongwei06/synthetic-dataset',notebook_ref='daichongwei06/synthetic-smoke',
            docker_image='gcr.io/kaggle-private-byod/python@sha256:'+'3'*64,
            transport_manifest_sha256=B.digest(manifest_raw),original_manifest_sha256=original,
            cpu_verification_sha256=B.digest(receipt_raw))

    def build(self,name='review'):
        (self.root/'protocol.json').write_bytes(B.canonical(self.protocol))
        return B.build(self.root/'protocol.json',self.root/'transport.json',self.root/'cpu.json',self.root/'worker.tar',self.root/name)

    def test_byte_identical_review_refuses_missing_authority_before_gpu(self):
        a,b=self.build('a'),self.build('b')
        self.assertEqual(a['review_lock_sha256'],b['review_lock_sha256'])
        book=json.loads((self.root/'a/profile.ipynb').read_bytes())
        with patch.object(Path,'mkdir',side_effect=AssertionError('filesystem touched')):
            with self.assertRaisesRegex(SystemExit,'APPROVAL REQUIRED'):
                exec(''.join(book['cells'][-1]['source']),dict(AUTHORITY=None))

    def test_actual_save_rejects_t4_retries_source_or_authority_drift(self):
        result=self.build()
        authority=dict(approved=True,owner_answer='Synthetic package fixture only',scope=S.SCOPE,
            review_lock_sha256=result['review_lock_sha256'],runtime_lock_sha256=result['runtime_lock_sha256'],
            protocol_sha256=B.digest(B.canonical(self.protocol)),claim_consumed=True,attempt_id='synthetic-no-provider')
        spec=json.loads((self.root/'review/launch-spec.json').read_bytes())
        body=dict(spec['save_fields'],kernel_execution_type=1,text=json.dumps(B.seal(self.root/'review',authority)))
        self.assertTrue(B.validate_save(body,self.root/'review',authority))
        for changed in ({'machine_shape':'NvidiaTeslaT4'},{'enable_tpu':True},{'enable_internet':True},
                        {'session_timeout_seconds':7200},{'dataset_data_sources':[]},
                        {'competition_data_sources':[]},
                        {'id':1},{'kernel_execution_type':True},{'text':json.dumps(dict(cells=[]))}):
            with self.subTest(changed=changed),self.assertRaises((ValueError,KeyError,IndexError)):
                B.validate_save(dict(body,**changed),self.root/'review',authority)

    def test_changed_worker_archive_or_cpu_receipt_refuses(self):
        (self.root/'worker.tar').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'worker archive'): self.build()

    def test_cpu_evidence_and_scientific_scope_cannot_change_silently(self):
        self.protocol['cpu_verification_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'CPU receipt'): self.build()
        self.protocol['scope']=dict(S.SCOPE,granularity=2)
        with self.assertRaisesRegex(ValueError,'scope'): self.build()

    def test_protocol_cannot_omit_or_substitute_competition_binding(self):
        for index,value in enumerate((None,[],['another-competition'])):
            if value is None: self.protocol.pop('competition_sources',None)
            else: self.protocol['competition_sources']=value
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'competition'):
                self.build('missing-competition-'+str(index))

    def test_competition_binding_reaches_live_notebook_and_actual_launch_spec(self):
        self.build()
        packet=self.root/'review'
        metadata=json.loads((packet/'kernel-metadata.json').read_bytes())
        spec=json.loads((packet/'launch-spec.json').read_bytes())
        self.assertEqual(metadata['competition_sources'],['arc-prize-2026-arc-agi-3'])
        self.assertEqual(spec['save_fields']['competition_data_sources'],metadata['competition_sources'])

    def test_disabled_competition_review_save_rejects_execution_or_accelerator(self):
        self.build()
        packet=self.root/'review'
        book=json.loads((packet/'review-notebook.ipynb').read_bytes())
        spec=json.loads((packet/'review-save-spec.json').read_bytes())
        body=dict(spec['save_fields'],kernel_execution_type='QUICK_SAVE',text=json.dumps(book))
        self.assertTrue(B.validate_review_save(body,packet))
        self.assertIsNone(B.CPU.authority_from(book))
        self.assertFalse(book['metadata']['kaggle']['isGpuEnabled'])
        for changed in ({'enable_gpu':True},{'machine_shape':'NvidiaRtxPro6000'},
                        {'enable_tpu':True},{'enable_internet':True},{'kernel_execution_type':1},
                        {'kernel_execution_type':True},{'competition_data_sources':[]},
                        {'dataset_data_sources':[]},{'text':json.dumps(dict(book,cells=[]))}):
            with self.subTest(changed=changed),self.assertRaises((ValueError,KeyError,IndexError)):
                B.validate_review_save(dict(body,**changed),packet)


@unittest.skipUnless(__import__('sys').platform=='linux','fixed Linux temporary-prefix cleanup policy')
class Finalization(unittest.TestCase):
    def exercise(self,*,writer=None,gpu='NVIDIA RTX PRO 6000'):
        with tempfile.TemporaryDirectory() as out,tempfile.TemporaryDirectory() as prefix,tempfile.TemporaryDirectory() as sandbox:
            output=Path(out); prefix=Path(prefix); sandbox=Path(sandbox)
            prefix.rmdir(); sandbox.rmdir()
            mount=output/'mounts/dataset'; mount.mkdir(parents=True)
            def stage(mount,work,protocol,deadline,claim):
                claim()
                return dict(synthetic_fixture=True),work/'source'
            class FakeOwner:
                def command(self,argv,log,deadline,env):
                    log.write_text('synthetic CPU fixture, no inference')
                    if '--query-gpu=uuid,name' in argv: return 'GPU-test,'+gpu+'\n'
                    if '--query-compute-apps=gpu_uuid,pid' in argv: return ''
                    dest=Path(argv[argv.index('--output')+1])
                    (dest/'worker-result.json').write_text(json.dumps(dict(cases=['board-06'],purpose='one_image_runtime_smoke')))
                    return ''
                def stop(self,deadline): return dict(groups=[],groups_absent=True)
            authority=dict(review_lock_sha256='1'*64,attempt_id='synthetic-only')
            protocol=dict(dataset_ref='owner/dataset')
            with (patch.object(S,'PREFIX',prefix),patch.object(S,'stage',side_effect=stage) as staging,
                    patch.object(S.shutil,'which',return_value='nvidia-smi')):
                started=time.monotonic()
                if writer:
                    with patch.object(S,'write',side_effect=writer),self.assertRaises(S.LifecycleDeadline):
                        S.execute(protocol,authority,output,sandbox,started,started+30,started+20,FakeOwner(),lambda:None,input_root=output/'mounts')
                    self.assertFalse((output/'completion-witness.json').exists())
                elif 'T4' in gpu:
                    with self.assertRaises(RuntimeError):
                        S.execute(protocol,authority,output,sandbox,started,started+30,started+20,FakeOwner(),lambda:None,input_root=output/'mounts')
                    staging.assert_not_called()
                    self.assertEqual(json.loads((output/'result.json').read_bytes())['status'],'failed')
                else:
                    result=S.execute(protocol,authority,output,sandbox,started,started+30,started+20,FakeOwner(),lambda:None,input_root=output/'mounts')
                    self.assertTrue(result['temporary_environment_removed'])
                    self.assertTrue(result['gpu_cleanup_verified'])
                    self.assertTrue((output/'completion-witness.json').exists())

    def test_synthetic_pipeline_cleans_before_provisional_receipt(self): self.exercise()

    def test_final_write_interruption_never_produces_completion_witness(self):
        original=S.write
        def interrupted(path,raw):
            original(path,raw)
            raise S.LifecycleDeadline('synthetic final deadline immediately after write')
        self.exercise(writer=interrupted)

    def test_gpu_mismatch_refuses_before_archive_staging_or_model_work(self):
        self.exercise(gpu='NVIDIA Tesla T4')


if __name__=='__main__': unittest.main()
