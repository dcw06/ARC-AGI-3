"""Local, pinned upstream loading for the development adapters.

No downloading, dependency installation, Kaggle calls or inference on import.
Callers must run inference under their own reviewed lifecycle supervisor.
"""
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import copy
import re

from .granularity import MODELS


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4*1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def source_pin(model):
    if model not in MODELS:
        raise ValueError('unknown model')
    return json.loads(Path(__file__).with_name('granularity_sources.json').read_text())[
        'semantic_sam' if model == 'semantic_sam_l' else 'unsamv2']


def verify_sources(source, model):
    source = Path(source).resolve()
    entry = source_pin(model)
    links = entry.get('symlinks', {})
    expected = {**entry['files'], **{name: link['link_text_sha256'] for name,link in links.items()}}
    actual = {}
    for folder in entry['runtime_directories']:
        # rglob does not reliably traverse symlinked directories on all Python
        # versions. Refuse them explicitly, including each runtime root.
        for parent in (source/folder, *(source/folder).parents):
            if parent == source:
                break
            if parent.is_symlink():
                raise ValueError('symlinked upstream runtime directory')
        for path in (source/folder).rglob('*'):
            name = path.relative_to(source).as_posix()
            if name in links:
                link = links[name]
                if path.is_symlink():
                    matches = os.readlink(path) == link['target']
                else:
                    # GitHub ZIPs store symlinks as regular files containing
                    # link text. This explicitly pinned archive representation
                    # is accepted only for the four unused legacy config links.
                    matches = path.is_file() and path.read_bytes() == link['target'].encode()
                target = path.parent/link['target']
                if (not matches or not target.resolve().is_relative_to(source) or
                        target.exists() or target.is_symlink() or link['target_state'] != 'absent_in_pinned_tree'):
                    raise ValueError('pinned upstream legacy symlink differs')
                actual[name] = hashlib.sha256(link['target'].encode()).hexdigest()
                continue
            if path.is_symlink():
                raise ValueError('unlisted upstream symlink')
            if path.is_file() and path.suffix in ('.py', '.yaml', '.yml', '.json') and '__pycache__' not in path.parts:
                actual[name] = file_sha(path)
    if actual != expected:
        raise ValueError('upstream runtime source missing, added or changed')
    return entry


def build_semantic_offline(source, checkpoint, upstream):
    """Build without the redundant Swin URL preload; require full model weights.

    The upstream convenience builder loads backbone weights before loading the
    segmentation checkpoint. Override only that initialization dependency,
    without modifying upstream files or relying on a populated download cache.
    """
    import torch
    loader = importlib.import_module('utils.arguments').load_opt_from_config_file
    wrapper = importlib.import_module('semantic_sam.BaseModel').BaseModel
    config = copy.deepcopy(loader(str(Path(source)/'configs/semantic_sam_only_sa-1b_swinL.yaml')))
    config['MODEL']['BACKBONE']['LOAD_PRETRAINED'] = False
    config['MODEL']['BACKBONE']['PRETRAINED'] = ''
    network = upstream.build_model(config)
    checkpoint_state = torch.load(checkpoint, map_location='cpu', weights_only=True)
    if not isinstance(checkpoint_state,dict):
        raise ValueError('Semantic-SAM state dictionary required')
    state = checkpoint_state.get('model', checkpoint_state)
    if not isinstance(state,dict):
        raise ValueError('Semantic-SAM model dictionary required')
    # Match the pinned BaseModel.from_pretrained prefix convention, but refuse
    # missing parameters rather than relying on backbone pretraining to fill them.
    weights = {key[6:]:value for key,value in state.items() if isinstance(key,str) and key.startswith('model.')}
    required = network.state_dict()
    if not required or any(key not in weights or required[key].shape != weights[key].shape for key in required):
        raise ValueError('segmentation checkpoint must cover every model/backbone tensor')
    network.load_state_dict({key:weights[key] for key in required}, strict=True)
    return wrapper(config,network).eval().cuda()


def verify_checkpoint(checkpoint, receipt, model):
    record = json.loads(Path(receipt).read_bytes())
    if (record.get('model') != model or type(record.get('bytes')) is not int or
            record['bytes'] <= 0 or type(record.get('sha256')) is not str or
            len(record['sha256']) != 64 or not record.get('source')):
        raise ValueError('explicit model, source, byte size and SHA256 checkpoint receipt required')
    path = Path(checkpoint)
    if path.is_symlink() or path.stat().st_size != record['bytes'] or file_sha(path) != record['sha256']:
        raise ValueError('checkpoint bytes differ from acquisition receipt')
    return record


def verify_environment(lock):
    """Require an explicit per-backend installed-version lock, not a shared env.

    This checks versions only; wheel provenance and CUDA compatibility require
    the later runtime qualification. It does not claim a deployable GPU image.
    """
    expected = json.loads(Path(lock).read_bytes())
    if type(expected) is not dict or any(type(name) is not str or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',name) for name in expected):
        raise ValueError('backend environment version lock required')
    normalized=[re.sub(r'[-_.]+','-',name).lower() for name in expected]
    if len(set(normalized)) != len(normalized) or not {'torch','torchvision','numpy','pillow'} <= set(normalized):
        raise ValueError('unique backend distribution names and required package versions needed')
    for name, version in expected.items():
        if type(version) is not str or importlib.metadata.version(name) != version:
            raise ValueError('backend environment version differs: ' + name)
    return expected


def load_backend(source, checkpoint, model, device):
    from .granularity_backends import UnSAMv2Backend, SemanticSAMBackend
    if device not in ('cpu', 'cuda'):
        raise ValueError('explicit cpu/cuda device required')
    verify_sources(source, model)
    source, checkpoint = Path(source).resolve(), Path(checkpoint).resolve()
    packages = ('semantic_sam', 'tasks', 'utils') if model == 'semantic_sam_l' else ('sam2', 'training')
    # Multiple forks have the same module names: mixing them in one interpreter
    # must fail rather than silently selecting the already-imported package.
    for package in packages:
        if package in sys.modules:
            raise RuntimeError('use a fresh isolated interpreter: ' + package)
    sys.path.insert(0, str(source if model == 'semantic_sam_l' else source/'sam2'))
    if model != 'semantic_sam_l':
        build = importlib.import_module('sam2.build_sam')
        predictor = importlib.import_module('sam2.sam2_image_predictor')
        generator = importlib.import_module('sam2.automatic_mask_generator')
        for module in (build, predictor, generator):
            if not Path(module.__file__).resolve().is_relative_to(source/'sam2'):
                raise ValueError('a different SAM fork was imported')
        network = build.build_sam2('configs/unsamv2_small.yaml', str(checkpoint),
                                  device=device, apply_postprocessing=False)
        return UnSAMv2Backend(network, predictor.SAM2ImagePredictor,
                             generator.SAM2AutomaticMaskGenerator, model)
    if device != 'cuda':
        raise ValueError('pinned Semantic-SAM helper requires CUDA; no silent CPU port')
    import numpy as np
    import torch
    from PIL import Image
    upstream = importlib.import_module('semantic_sam')
    if not Path(upstream.__file__).resolve().is_relative_to(source):
        raise ValueError('a different Semantic-SAM was imported')
    network = build_semantic_offline(source, checkpoint, upstream)

    def image_tensor(image):
        # Same BICUBIC 640-short-edge preprocessing as prepare_image(); the
        # source is always a square448 board, with no added border or overlay.
        enlarged = np.asarray(Image.fromarray(image).resize((640,640), Image.Resampling.BICUBIC))
        return enlarged, torch.from_numpy(enlarged.copy()).permute(2,0,1).to(device)
    return SemanticSAMBackend(network, upstream.SemanticSAMPredictor,
                              upstream.SemanticSamAutomaticMaskGenerator, image_tensor)
