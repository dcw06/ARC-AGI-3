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

from .granularity import MODELS


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4*1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def verify_sources(source, model):
    if model not in MODELS:
        raise ValueError('unknown model')
    source = Path(source).resolve()
    entry = json.loads(Path(__file__).with_name('granularity_sources.json').read_text())[
        'semantic_sam' if model == 'semantic_sam_l' else 'unsamv2']
    actual = {}
    for folder in entry['runtime_directories']:
        for path in (source/folder).rglob('*'):
            if path.is_symlink():
                raise ValueError('symlink in upstream runtime')
            if path.is_file() and path.suffix in ('.py', '.yaml', '.yml', '.json') and '__pycache__' not in path.parts:
                actual[path.relative_to(source).as_posix()] = file_sha(path)
    if actual != entry['files']:
        raise ValueError('upstream runtime source missing, added or changed')
    return entry


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
    if type(expected) is not dict or not {'torch', 'torchvision', 'numpy', 'Pillow'} <= set(expected):
        raise ValueError('backend environment version lock required')
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
    # Upstream build helper resolves config filenames relative to its checkout.
    previous = Path.cwd()
    try:
        os.chdir(source)
        network = upstream.build_semantic_sam(model_type='L', ckpt=str(checkpoint))
    finally:
        os.chdir(previous)

    def image_tensor(image):
        # Same BICUBIC 640-short-edge preprocessing as prepare_image(); the
        # source is always a square448 board, with no added border or overlay.
        enlarged = np.asarray(Image.fromarray(image).resize((640,640), Image.Resampling.BICUBIC))
        return enlarged, torch.from_numpy(enlarged.copy()).permute(2,0,1).to(device)
    return SemanticSAMBackend(network, upstream.SemanticSAMPredictor,
                              upstream.SemanticSamAutomaticMaskGenerator, image_tensor)
