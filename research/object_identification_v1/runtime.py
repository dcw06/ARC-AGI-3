"""CPU-only compatibility rehearsal of pinned InternVL code, never real weights."""
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import socket
import time

from .probe import MODEL, MODEL_REVISION


def verify_model_code(folder):
    folder = Path(folder).resolve()
    pin = json.loads(Path(__file__).with_name('runtime_source_pin.json').read_bytes())
    if pin['repository'] != MODEL or pin['revision'] != MODEL_REVISION:
        raise ValueError('model source pin mismatch')
    for name, expected in pin['files'].items():
        if hashlib.sha256((folder/name).read_bytes()).hexdigest() != expected:
            raise ValueError('model code hash mismatch: '+name)
    if {p.name for p in folder.glob('*.py')} != {n for n in pin['files'] if n.endswith('.py')}:
        raise ValueError('unexpected or missing model Python source')
    return pin


def prepare_pixels(image, dtype):
    """One full-frame 448px InternVL tile; no crop, masks or reference labels.

    Preprocessing stays on CPU; only the resulting tensor may later move to a
    GPU. Matching its dtype to the vision weights is part of the input contract.
    """
    import torch
    from PIL import Image
    from torchvision.transforms import Compose, Normalize, ToTensor

    with Image.open(image) as loaded:
        rendered = loaded.convert('RGB').resize((448, 448), Image.Resampling.BICUBIC)
    transform = Compose([ToTensor(), Normalize(mean=(0.485, 0.456, 0.406),
                                               std=(0.229, 0.224, 0.225))])
    pixels = transform(rendered).unsqueeze(0).to(dtype=dtype)
    if tuple(pixels.shape) != (1, 3, 448, 448) or not torch.isfinite(pixels).all().item():
        raise ValueError('invalid model image tensor')
    preview = io.BytesIO()
    rendered.save(preview, format='PNG')
    return pixels, preview.getvalue()


def cpu_check(folder, cache, inputs=None, previews=None):
    """Exercise imports and a reduced random-weight model with networking disabled.

    This tests the actual pinned model classes against installed CPU libraries.
    It cannot validate full checkpoint loading, Kaggle's image or GPU kernels.
    """
    folder = Path(folder).resolve()
    pin = verify_model_code(folder)
    env = {
        'CUDA_VISIBLE_DEVICES': '', 'NVIDIA_VISIBLE_DEVICES': 'void',
        'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
        'HF_HUB_DISABLE_TELEMETRY': '1', 'HF_HOME': str(Path(cache).resolve()),
        'MPLBACKEND': 'Agg',
    }
    os.environ.update(env)
    started = time.monotonic()
    connections = []

    def refuse_network(*args, **kwargs):
        connections.append('attempted')
        raise PermissionError('CPU compatibility check is offline')

    old_connect, old_create = socket.socket.connect, socket.create_connection
    socket.socket.connect = refuse_network
    socket.create_connection = refuse_network
    try:
        import torch
        if torch.version.cuda is not None or torch.cuda.is_initialized():
            raise ValueError('this rehearsal requires CPU-only PyTorch, not a CUDA build')
        import torchvision
        import timm
        from transformers import AutoConfig, AutoModel

        torch.set_num_threads(2)
        torch.manual_seed(0)
        config = AutoConfig.from_pretrained(str(folder), trust_remote_code=True, local_files_only=True)
        config.force_image_size = 28
        config.dynamic_image_size = False
        config.use_thumbnail = False
        config.min_dynamic_patch = config.max_dynamic_patch = 1
        config.vision_config = config.vision_config.__class__(
            image_size=28, patch_size=14, hidden_size=32, intermediate_size=64,
            num_hidden_layers=1, num_attention_heads=4, use_flash_attn=False)
        config.llm_config = config.llm_config.__class__(
            architectures=['Qwen3ForCausalLM'], vocab_size=64,
            hidden_size=32, intermediate_size=64, num_hidden_layers=1,
            num_attention_heads=4, num_key_value_heads=2, head_dim=8,
            max_position_embeddings=128, eos_token_id=2, bos_token_id=1,
            pad_token_id=0, use_cache=False)
        config.downsample_ratio = 0.5
        config.img_context_token_id = 3
        model = AutoModel.from_config(config, trust_remote_code=True, use_flash_attn=False).eval()
        model.img_context_token_id = 3
        vision_dtype = next(model.vision_model.parameters()).dtype
        pixels = torch.randn(1, 3, 28, 28, dtype=vision_dtype)
        with torch.no_grad():
            features = model.extract_feature(pixels)
            result = model(pixel_values=pixels, input_ids=torch.tensor([[1, 3, 4]]),
                           attention_mask=torch.ones(1, 3, dtype=torch.long),
                           image_flags=torch.ones(1, 1, dtype=torch.long), return_dict=True)
        if tuple(features.shape) != (1, 1, 32) or tuple(result.logits.shape) != (1, 3, 64):
            raise ValueError('unexpected multimodal rehearsal shapes')
        if not torch.isfinite(result.logits).all().item():
            raise ValueError('non-finite multimodal logits')
        if connections:
            raise ValueError('a blocked network request was attempted')
        prepared_images = []
        if inputs is not None:
            destination = Path(previews).resolve() if previews else None
            if destination is not None:
                destination.mkdir(exist_ok=False)
            for image in sorted(Path(inputs).glob('board-*.png')):
                tensor, preview = prepare_pixels(image, vision_dtype)
                tensor_bytes = tensor.contiguous().view(torch.uint8).numpy().tobytes()
                prepared_images.append({
                    'image': image.name, 'image_sha256': hashlib.sha256(image.read_bytes()).hexdigest(),
                    'pixel_tensor_sha256': hashlib.sha256(tensor_bytes).hexdigest(),
                    'shape': list(tensor.shape), 'dtype': str(tensor.dtype),
                    'preview_sha256': hashlib.sha256(preview).hexdigest(),
                    'model_inference': False})
                if destination is not None:
                    (destination/image.name).write_bytes(preview)
            if len(prepared_images) != 6:
                raise ValueError('expected six actual board preprocessing checks')
        return {
            'status': 'cpu_compatibility_rehearsal_passed_not_model_or_gpu_results',
            'model': MODEL, 'revision': MODEL_REVISION, 'source_files': pin['files'],
            'validator_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'source_pin_sha256': hashlib.sha256(Path(__file__).with_name('runtime_source_pin.json').read_bytes()).hexdigest(),
            'versions': {n: importlib.metadata.version(n) for n in
                         ('torch', 'torchvision', 'transformers', 'timm', 'einops', 'pillow', 'safetensors')},
            'model_class': type(model).__name__, 'vision_class': type(model.vision_model).__name__,
            'language_class': type(model.language_model).__name__,
            'pixel_dtype': str(vision_dtype),
            'actual_image_preprocessing': prepared_images,
            'synthetic_parameters': sum(p.numel() for p in model.parameters()),
            'vision_features_shape': list(features.shape), 'logits_shape': list(result.logits.shape),
            'elapsed_seconds': time.monotonic()-started, 'cpu_only_torch': True,
            'cuda_initialized': torch.cuda.is_initialized(), 'network_attempts': len(connections),
            'pretrained_weights_loaded': False, 'study_requests': 0, 'game_actions': 0,
            'kaggle_image_validated': False, 'gpu_runtime_validated': False,
        }
    finally:
        socket.socket.connect, socket.create_connection = old_connect, old_create
