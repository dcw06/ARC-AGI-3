"""Route known model/compilation caches into the monitored scratch tree."""
from pathlib import Path


def worker_environment(environment, scratch):
    root = Path(scratch).resolve()
    paths = {
        'TMPDIR': 'tmp', 'TMP': 'tmp', 'TEMP': 'tmp',
        'XDG_CACHE_HOME': 'cache', 'XDG_CONFIG_HOME': 'config',
        'HF_HOME': 'cache/huggingface', 'HF_HUB_CACHE': 'cache/huggingface/hub',
        'TRANSFORMERS_CACHE': 'cache/huggingface/transformers',
        'VLLM_CACHE_ROOT': 'cache/vllm', 'VLLM_CONFIG_ROOT': 'config/vllm',
        'VLLM_ASSETS_CACHE': 'cache/vllm/assets', 'VLLM_RPC_BASE_PATH': 'tmp',
        'TORCH_HOME': 'cache/torch', 'TORCH_EXTENSIONS_DIR': 'cache/torch_extensions',
        'TORCHINDUCTOR_CACHE_DIR': 'cache/torchinductor',
        'TRITON_CACHE_DIR': 'cache/triton', 'CUDA_CACHE_PATH': 'cache/cuda',
        'MPLCONFIGDIR': 'cache/matplotlib',
    }
    result = dict(environment)
    for key, relative in paths.items():
        path = root/relative
        path.mkdir(parents=True, exist_ok=True)
        result[key] = str(path)
    # Source imports must not create unmonitored pycache files in the package.
    result['PYTHONDONTWRITEBYTECODE'] = '1'
    return result
