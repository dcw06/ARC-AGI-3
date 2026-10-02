"""Inspect unpacked Track 3 review source, reject live execution, and CPU-rehearse the packaged entrypoint."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MODE_LINE = "MODE='live'\n"


def verify(folder):
    # This verifier reads the candidate's embedded source; it does not reuse a historical notebook.
    from scripts.review_action_effect_history_v1_notebook import verify_bindings
    lock, code, payload = verify_bindings(Path(folder))
    if (lock['scope'] != 'stagnation-supervision-v1' or lock['status'] != 'review_candidate_gpu_disabled'
            or lock.get('live_gate_deliberately_disabled') is not True):
        raise ValueError('wrong Track 3 review candidate')
    authority = __import__('base64').b64decode(payload['research/stagnation_supervision_v1/closed_loop/authority.py'])
    if b'LIVE_DISABLED = True' not in authority:
        raise ValueError('candidate must retain the closed live gate')
    return lock, code, payload


def execute(code, env, folder, timeout):
    path = Path(folder) / 'cell.py'
    path.write_text(code, encoding='utf-8')
    return subprocess.run([sys.executable, str(path)], cwd=folder, env=env,
                          capture_output=True, text=True, timeout=timeout)


def review(folder, *, record=False):
    folder = Path(folder).resolve()
    lock, code, payload = verify(folder)
    env = {k: v for k, v in os.environ.items() if not k.startswith(('SSV_', 'AEH_')) and k != 'PYTHONPATH'}
    with tempfile.TemporaryDirectory(prefix='ssv-review-refusal-') as tmp:
        value = execute(code, dict(env, TMPDIR=tmp, TMP=tmp, TEMP=tmp, CUDA_VISIBLE_DEVICES=''), tmp, 120)
        if value.returncode == 0 or 'live mode is disabled' not in value.stderr:
            raise ValueError('notebook failed to reject live execution: ' + value.stderr[-1000:])
        if {p.name for p in Path(tmp).iterdir()} != {'cell.py'}:
            raise ValueError('rejected notebook leaked extracted source')
    from research.grounded_action_v1.engine import restore_game_mount
    from research.stagnation_supervision_v1.closed_loop import bridge as B, evaluate as EV
    # Hold temporary outputs only; no model calls, GPUs, or network. A single group exercises all three arms.
    with tempfile.TemporaryDirectory(prefix='ssv-notebook-rehearsal-') as tmp:
        work = Path(tmp)
        games = restore_game_mount(work / 'games')
        (work / 'working').mkdir()
        short = dict(env, SSV_REHEARSAL='1', CUDA_VISIBLE_DEVICES='', TMPDIR=tmp,
                     SSV_REHEARSAL_GAMES=str(games), SSV_REHEARSAL_WORKING=str(work / 'working'),
                     SSV_REHEARSAL_SECONDS='1500', SSV_REHEARSAL_GROUPS='b1-ar25', SSV_REHEARSAL_ACTIONS='12')
        value = execute(code.replace(MODE_LINE, "MODE='rehearsal'\n"), short, tmp, 180)
        if value.returncode != 0:
            raise ValueError('packaged CPU rehearsal failed: ' + value.stderr[-1500:])
        spec = B.session_spec(__import__('research.stagnation_supervision_v1.closed_loop.runner',
                                        fromlist=['protocol']).protocol(), '1')
        spec = {**spec, 'schedule': [s for s in spec['schedule'] if s['pair_id'] == 'b1-ar25'],
                'limits': {**spec['limits'], 'actions_per_episode': 12}}
        output = work / 'working/stagnation-supervision-v1'
        from research.stagnation_supervision_v1.closed_loop.target_evaluate import evaluate_target
        evaluation = evaluate_target(output, spec, mode='rehearsal', session='1', internal_seconds=1500)
        outer = json.loads((output / 'control/outer.json').read_bytes())
        if not evaluation['technically_complete'] or evaluation['problems']:
            raise ValueError('packaged trajectory replay failed: ' + str(evaluation['problems']))
        if not all(outer.get(k) is True for k in ('process_groups_exited', 'independent_gpu_cleanup_verified', 'scratch_removed')):
            raise ValueError('packaged rehearsal cleanup incomplete')
        if any(p.name.startswith('stagnation-supervision-source-') for p in work.iterdir()):
            raise ValueError('packaged rehearsal leaked source')
    receipt = {'status': 'cpu_package_verified_pending_independent_review',
               'scope': lock['scope'], 'review_lock_sha256': hashlib.sha256((folder / 'review-source-lock.json').read_bytes()).hexdigest(),
               'source_bindings_verified': len(payload), 'all_packaged_python_compiled': True,
               'gpu_disabled': True, 'live_execution_rejected': True, 'source_removed': True,
               'scripted_notebook_rehearsal_episodes': 3, 'independent_trajectory_replay': True, 'independent_lifecycle_replay': True,
               'process_gpu_scratch_cleanup_verified': True, 'gpu_runs': 0, 'authorized_seconds': 0}
    destination = ROOT / 'reports/stagnation_supervision_v1_package_review_r4.json'
    if destination.exists() and json.loads(destination.read_bytes()) != receipt:
        raise ValueError('current package review differs from retained receipt')
    if record:
        with destination.open('x', encoding='utf-8') as stream:
            json.dump(receipt, stream, indent=2)
            stream.write('\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, required=True)
    parser.add_argument('--record', action='store_true', help='retain a new write-once review receipt')
    args = parser.parse_args()
    print(json.dumps(review(args.folder, record=args.record), indent=2))
