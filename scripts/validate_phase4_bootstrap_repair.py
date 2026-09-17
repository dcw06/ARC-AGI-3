"""Exercise the repaired bootstrap with frozen engine wheels, entirely locally."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from certification.phase4_v6.clean_environment import (
    CleanEnvironment, ENVIRONMENT_PINS, verify_environment_wheels)

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--host-python', default='/usr/bin/python3')
args = parser.parse_args()
summary = {'scope': 'local_clean_bootstrap_and_frozen_engine_install_only',
           'passed': False, 'target_cuda_verified': False, 'model_service_installed': False,
           'gpu_run_launched': False, 'error': None}
with tempfile.TemporaryDirectory(prefix='p4-bootstrap-repair-') as folder:
    env = CleanEnvironment(folder, args.output, host_python=args.host_python)
    try:
        wheels = ROOT/'reports/runs/phase4-v2-assets/arc_agi_3_wheels'
        manifest = json.loads((ROOT/'reports/phase4_v2_offline_package.json').read_text())
        summary['verified_wheels'] = verify_environment_wheels(wheels, manifest)
        env.bootstrap()
        env.install('install_frozen_environment', wheels, ENVIRONMENT_PINS)
        env.check()
        env.execute('runtime_imports_and_isolation', [env.python, '-I', '-c',
            "import arc_agi,arcengine,importlib.metadata as m,json,pathlib,sys; "
            "expected={'arc-agi':'0.9.8','arcengine':'0.9.3','requests':'2.33.1',"
            "'numpy':'2.4.4','pydantic':'2.13.2','python-dotenv':'1.2.2'}; "
            "versions={name:m.version(name) for name in expected}; "
            "assert versions==expected; root=pathlib.Path(sys.prefix); "
            "assert all(pathlib.Path(d.locate_file('')).is_relative_to(root) for d in m.distributions()); "
            "print(json.dumps({'versions':versions,'all_distributions_inside_venv':True}))"])
        summary['passed'] = True
    except Exception as exc:
        summary['error'] = type(exc).__name__+': '+str(exc)
summary['scratch_removed'] = not Path(folder).exists()
summary['stages'] = env.stages
(args.output/'summary.json').write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
raise SystemExit(0 if summary['passed'] else 1)
