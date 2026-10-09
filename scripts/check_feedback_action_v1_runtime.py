"""CPU check of the successor runtime's installation path for feedback-action v1 (no GPU, no network, no provider).

Runs the live first cell's installation code (`runtime.prepare`, i.e. the verified runtime's `verify_bundle` and
hash-pinned `install`, the competition-wheel verification and the game lock) against local replicas of the two
mounts, then the import closure of each interpreter, then the real offline engine inside the installed game
interpreter (the Track 1 engine tests, run with the exact competition game wheels).

Replicas, not the provider mounts:
  --bundle       a directory with the 174 trusted wheels (bytes checked against trusted_manifest.json) and the
                 publisher's three metadata files (README.md, SHA256SUMS, requirements.lock), as the flat mount;
  --competition  a directory with arc_agi_3_wheels/ (the 31 wheels of the frozen manifest) and environment_files/.
A pass shows the installation and import closure work on Linux x86_64 / CPython 3.12 from these bytes. It is not
GPU, CUDA, model-load, provider-mount or attachment evidence.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ENGINE_TESTS = ('tests.test_feedback_action_v1_live', 'tests.test_feedback_action_v1_dispatch',
                'tests.test_feedback_action_v1_live_evaluation')


def check(bundle, competition, work, out, python=sys.executable, engine_tests=True):
    from certification.phase4_integrated_v2.game_assets import stage_games
    from research.feedback_action_v1.live import runtime as R
    runtime = R.load(ROOT)
    work = Path(work)
    work.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    deadline = started + runtime['lifecycle']['installation_seconds']
    report = {'schema': 'feedback_action_v1_runtime_install_check_v1',
              'evidence_class': 'cpu_replica_mounts_not_provider_mounts', 'gpu_used': False, 'network_used': False,
              'model_loaded': False, 'host': {'python': platform.python_version(), 'machine': platform.machine(),
                                             'libc': platform.libc_ver()},
              'installation_deadline_seconds': runtime['lifecycle']['installation_seconds'], 'passed': False}
    manifest = json.loads((ROOT / runtime['game']['manifest']).read_bytes())
    report['games_staged'] = str(stage_games(Path(competition) / runtime['competition']['environment_files'],
                                             work / 'games', manifest))
    if Path(python).resolve() != Path(sys.executable).resolve():
        raise SystemExit('run this check with the interpreter that should create the environments (--python)')
    from scripts.feedback_action_v1_launch import install_pair  # the live first cell's own installation step
    output = work / 'output'
    try:
        pair = install_pair(ROOT, work, output, bundle, competition, deadline)
    finally:
        receipt = json.loads((output / 'control/installation.json').read_bytes())
        report['installation'] = receipt
        report['installation_seconds'] = round(time.monotonic() - started, 1)
        report['process_cleanup'] = receipt.get('process_cleanup')
        report['retained_install_logs'] = sorted(p.name for p in (output / 'logs').glob('install-*.json'))
    report['interpreters'] = pair
    cleanup = report['process_cleanup']
    if engine_tests:
        env = {k: v for k, v in os.environ.items() if k not in ('PYTHONHOME', 'VIRTUAL_ENV')}
        env.update(PYTHONPATH=str(ROOT), CUDA_VISIBLE_DEVICES='', MPLBACKEND='Agg', PYTHONDONTWRITEBYTECODE='1')
        begun = time.monotonic()
        result = subprocess.run([pair['game'], '-m', 'unittest', *ENGINE_TESTS], cwd=ROOT, env=env, capture_output=True,
                                text=True, timeout=3600)
        summary = [line for line in result.stderr.splitlines() if line.startswith(('Ran ', 'OK', 'FAILED'))]
        versions = subprocess.run([pair['game'], '-I', '-c', 'import importlib.metadata as m, json; print(json.dumps('
                                   '{n: m.version(n) for n in ("arc-agi", "arcengine", "numpy", "pydantic")}))'],
                                  capture_output=True, text=True, timeout=120)
        report['engine_tests'] = {'modules': list(ENGINE_TESTS), 'interpreter': pair['game'],
                                  'game_package_versions': json.loads(versions.stdout.strip() or '{}'),
                                  'exit_code': result.returncode, 'summary': summary,
                                  'seconds': round(time.monotonic() - begun, 1),
                                  'stderr_tail': result.stderr[-1200:] if result.returncode else None}
    report['passed'] = (receipt.get('passed') is True and cleanup['groups_absent'] and not cleanup['error']
                        and (not engine_tests or report['engine_tests']['exit_code'] == 0))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(report, indent=1, sort_keys=True, default=str) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--competition', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=ROOT / 'reports/feedback_action_v1/runtime_install_check.json')
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--no-engine-tests', action='store_true')
    args = parser.parse_args()
    value = check(args.bundle, args.competition, args.work, args.out, args.python, not args.no_engine_tests)
    print(json.dumps({k: value.get(k) for k in ('passed', 'installation_seconds', 'process_cleanup', 'interpreters',
                                                'engine_tests')}, indent=1, default=str))
    raise SystemExit(0 if value['passed'] else 1)
