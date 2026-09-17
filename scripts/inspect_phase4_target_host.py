"""Read-only host prerequisites and evidence-size estimate, without credentials."""
import json
import os
from pathlib import Path
import platform
import shutil
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
credential_keys = ('KAGGLE_API_TOKEN', 'KAGGLE_USERNAME', 'KAGGLE_KEY')
dotenv = dotenv_values(ROOT/'.env', interpolate=False)
sample = {'uuid': 'GPU-00000000-0000-0000-0000-000000000000',
          'used_bytes': 86*1024**3, 'rss_bytes': 128*1024**3,
          'scratch_bytes': 4*1024**3, 'elapsed_seconds': 27539.123456789,
          'monotonic_seconds': 123456789.123456789}
count = int(27540/.25)+1
size = len(json.dumps(sample, sort_keys=True).encode())+2
print(json.dumps({
    'system': platform.system(), 'machine': platform.machine(),
    'python': platform.python_version(), 'nvidia_smi': shutil.which('nvidia-smi'),
    'docker': shutil.which('docker'),
    'environment_wheels': len(list((ROOT/'reports/runs/phase4-v2-assets/arc_agi_3_wheels').glob('*.whl'))),
    'kaggle_token_file_present': (ROOT/'.kaggle/access_token').is_file(),
    'kaggle_json_present': (ROOT/'.kaggle/kaggle.json').is_file(),
    'kaggle_token_env_present': bool(os.environ.get('KAGGLE_API_TOKEN')),
    'kaggle_dotenv_fields_nonempty': {key: bool(dotenv.get(key)) for key in credential_keys},
    'telemetry_design_estimate': {
        'scope': 'synthetic_size_arithmetic_not_measured_GPU_evidence',
        'sample_bytes': size, 'samples_at_nominal_interval': count,
        'payload_bytes_excluding_metadata': size*count,
        'atomic_replacement_bytes_excluding_metadata': 2*size*count,
        'monitor_component_limit_bytes': 16*1024**2,
    },
    'target_install_verified': False,
}, indent=2))
