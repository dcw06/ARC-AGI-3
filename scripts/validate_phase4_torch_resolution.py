"""Compare the old and corrected Torch pins against the verified wheel offline."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from certification.phase4_v6.clean_environment import CleanEnvironment
from certification.phase4_v6.torch_wheel_contract import inspect, validate
from certification.phase4_v6.target_install_probe_r3 import verify_torch_contract
import tempfile

def main():
    expected = json.loads((ROOT/'reports/phase4_torch_wheel_inspection.json').read_text())
    folder = ROOT/'reports/runs/phase4-torch-wheel-inspection'
    wheel = folder/expected['wheel']
    with wheel.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == expected['wheel_sha256']
    validate(inspect(wheel), expected)
    verify_torch_contract(folder)
    output = ROOT/'reports/runs/phase4-torch-resolution-local'
    with tempfile.TemporaryDirectory(prefix='p4-torch-resolution-') as directory:
        runner = CleanEnvironment(directory, output, host_python='/usr/bin/python3', seconds=120)
        runner.bootstrap()
        results = {}
        for label, pin in [('old', 'torch==2.10.0+cu128'), ('corrected', 'torch==2.10.0')]:
            command = runner.pip()+['install', '--dry-run', '--no-deps', '--ignore-installed',
                '--no-index', '--only-binary=:all:', '--find-links', str(folder), pin]
            result = subprocess.run(command, env=runner.env, capture_output=True, text=True, timeout=30)
            (output/(label+'.log')).write_text(result.stdout+result.stderr)
            results[label] = {'pin': pin, 'exit_code': result.returncode}
        assert results['old']['exit_code'] != 0
        assert results['corrected']['exit_code'] == 0
        assert 'No matching distribution found' in (output/'old.log').read_text()
        assert 'Would install torch-2.10.0' in (output/'corrected.log').read_text()
    summary = {'passed':True, 'scope':'Torch wheel selection only; dry-run --no-deps',
               'full_dependency_resolution_verified':False, 'cuda_runtime_verified':False,
               'gpu_run_launched':False, 'scratch_removed':not Path(directory).exists(),
               'results':results, 'wheel_sha256':expected['wheel_sha256']}
    (ROOT/'reports/phase4_torch_resolution_local.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))

if __name__ == '__main__':
    main()
