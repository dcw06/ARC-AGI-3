"""Two isolated offline environments; installation evidence only, no model pilot."""
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

from certification.phase4_v6.clean_environment import CleanEnvironment, ENVIRONMENT_PINS
from certification.phase4_v6.target_install_probe import SECONDS, verify_wheelhouses
from certification.phase4_v6.target_install_probe_r3 import verify_torch_contract, RUNTIME_CHECK

MODEL_PINS = ['vllm==0.19.0', 'torch==2.10.0', 'transformers==4.57.6', 'numpy==2.2.6']
ISOLATION_CHECK = '''
from pathlib import Path
import importlib.metadata as m, importlib.util, json, site, sys
assert sys.prefix != sys.base_prefix and site.ENABLE_USER_SITE is False
root = Path(sys.prefix).resolve()
assert all(Path(d.locate_file('')).resolve().is_relative_to(root) for d in m.distributions())
'''
MODEL_CHECK = RUNTIME_CHECK.replace('import arc_agi, arcengine, torch', 'import torch').replace(
    "'arc-agi':'0.9.8','arcengine':'0.9.3','numpy':'2.4.4'", "'numpy':'2.2.6'") + ISOLATION_CHECK + '''
assert importlib.util.find_spec('arc_agi') is None
assert importlib.util.find_spec('arcengine') is None
'''
GAME_CHECK = ISOLATION_CHECK + '''
import arc_agi, arcengine, numpy, requests, pydantic, dotenv
expected = {'arc-agi':'0.9.8','arcengine':'0.9.3','numpy':'2.4.4',
            'requests':'2.33.1','pydantic':'2.13.2','python-dotenv':'1.2.2'}
versions = {name:m.version(name) for name in expected}
assert versions == expected, versions
assert importlib.util.find_spec('torch') is None
assert importlib.util.find_spec('vllm') is None
assert importlib.util.find_spec('transformers') is None
print(json.dumps({'versions':versions,'isolated_game_imports_passed':True}))
'''


def install_pair(scratch, output, model, game, deadline, host_python=sys.executable):
    runners = {}
    for role, wheels, pins in [('model', model, MODEL_PINS), ('game', game, ENVIRONMENT_PINS)]:
        if time.monotonic() >= deadline-10:
            raise TimeoutError('split installation deadline before '+role)
        folder = scratch/role
        folder.mkdir(exist_ok=False)
        runner = CleanEnvironment(folder, output/role, host_python=host_python,
                                  seconds=max(0, deadline-time.monotonic()))
        # Both roles share one absolute deadline, including their predecessor's work.
        runner.deadline = deadline
        runner.env.update(VLLM_NO_USAGE_STATS='1', USE_TF='0', TRANSFORMERS_NO_TF='1')
        if role == 'game':
            runner.env['CUDA_VISIBLE_DEVICES'] = ''
        runner.bootstrap()
        runner.execute('resolve_'+role, runner.pip()+['install', '--dry-run', '--no-index',
            '--only-binary=:all:', '--find-links', str(Path(wheels).resolve()),
            '--report', str(runner.output/'resolution.json'), *pins])
        runners[role] = runner
    for role, wheels, pins in [('model', model, MODEL_PINS), ('game', game, ENVIRONMENT_PINS)]:
        runners[role].install('install_'+role, wheels, pins)
        runners[role].check()
    return runners


def run(model, environment, manifest, output):
    started = time.monotonic()
    deadline = started+SECONDS
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    report = {'passed':False, 'scope':'split_offline_install_and_cuda_smoke_only',
              'model_loaded':False, 'pilot_launched':False, 'phase4_complete':False,
              'provider_reconciliation_required':True, 'error':None,
              'scratch_removed':None, 'gpu_cleanup_verified':False}
    scratch = None
    def check_deadline():
        if time.monotonic() >= deadline-10:
            raise TimeoutError('split installation deadline')
    try:
        if (platform.system() != 'Linux' or platform.machine() != 'x86_64'
                or sys.version_info[:2] != (3,12)):
            raise ValueError('target Linux x86_64 / Python 3.12 required')
        report['wheelhouses'] = verify_wheelhouses(Path(model), Path(environment), manifest, check_deadline)
        report['torch_wheel_contract'] = verify_torch_contract(model)
        check_deadline()
        with tempfile.TemporaryDirectory(prefix='p4-split-install-') as folder:
            scratch = Path(folder)
            runners = install_pair(scratch, output, model, environment, deadline)
            # Verify game imports before spending work on the CUDA check.
            runners['game'].execute('game_runtime_and_isolation',
                                    [runners['game'].python, '-I', '-c', GAME_CHECK])
            runners['model'].execute('model_cuda_and_isolation',
                                     [runners['model'].python, '-I', '-c', MODEL_CHECK])
        check_deadline()
        report['passed'] = True
    except Exception as exc:
        report['error'] = type(exc).__name__+': '+str(exc)[:512]
    finally:
        report['scratch_removed'] = not scratch.exists() if scratch is not None else None
        try:
            remaining = subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid',
                '--format=csv,noheader,nounits'], text=True, timeout=2).strip()
            report['gpu_cleanup_verified'] = not remaining
            if remaining:
                raise RuntimeError('GPU process inventory not empty after cleanup')
        except Exception as exc:
            report['cleanup_error'] = type(exc).__name__+': '+str(exc)[:512]
            report['passed'] = False
        if report['scratch_removed'] is not True:
            report['passed'] = False
        report['elapsed_seconds'] = time.monotonic()-started
        if report['elapsed_seconds'] >= SECONDS:
            report.update(passed=False, error=report['error'] or 'probe elapsed ceiling')
        (output/'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report
