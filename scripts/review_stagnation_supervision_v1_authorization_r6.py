"""Read-only unpacked R6 review: authority tests and CPU notebook lifecycle, no live calls."""
import base64
import json
import os
from pathlib import Path
import tempfile
from scripts import prepare_stagnation_supervision_v1_authorization_r6 as P


def verify(folder):
    folder = Path(folder)
    lock = json.loads((folder / 'review-source-lock.json').read_bytes())
    for name, digest in lock['artifacts'].items():
        if Path(name).name != name or P.sha((folder / name).read_bytes()) != digest:
            raise ValueError('artifact drift')
    for name, digest in lock['review_documents'].items():
        if P.sha((P.ROOT / name).read_bytes()) != digest:
            raise ValueError('review document drift')
    payload, expected, notebook, metadata = P.candidate()
    if (json.loads((folder / 'source-review.json').read_bytes()) != expected
            or json.loads((folder / 'profile.ipynb').read_bytes()) != notebook
            or json.loads((folder / 'kernel-metadata.json').read_bytes()) != metadata
            or lock['source_review_sha256'] != P.sha(P.raw(expected))
            or lock['parent_review_sha256'] != expected['parent_review_sha256']
            or lock['authorized_seconds'] != 0 or lock['gpu_launch_authorized'] is not False):
        raise ValueError('R6 differs from exact reviewed R4 overlay')
    for name, value in payload.items():
        if name.endswith('.py'):
            compile(value, name, 'exec')
    return lock, notebook, payload, expected


def extract(root, payload, source):
    for name, value in {**payload, P.REVIEW: P.raw(source)}.items():
        path = Path(root) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)


def review():
    from scripts.review_stagnation_supervision_v1_notebook_r4 import execute
    from research.grounded_action_v1.engine import restore_game_mount
    from research.stagnation_supervision_v1.closed_loop import bridge as B, runner
    from research.stagnation_supervision_v1.closed_loop.target_evaluate import evaluate_target
    import unittest
    suite = unittest.defaultTestLoader.discover(str(P.ROOT / 'tests'), 'test_ssv_authorization_r6.py')
    tests = unittest.TextTestRunner(verbosity=2).run(suite)
    if not tests.wasSuccessful():
        raise ValueError('R6 authority tests failed')
    lock, notebook, payload, source = verify(P.OUT)
    code = notebook['cells'][1]['source']
    env = {k: v for k, v in os.environ.items() if not k.startswith(('SSV_', 'AEH_')) and k != 'PYTHONPATH'}
    env['CUDA_VISIBLE_DEVICES'] = ''
    with tempfile.TemporaryDirectory() as tmp:
        result = execute(code, dict(env, TMPDIR=tmp, TMP=tmp, TEMP=tmp), tmp, 120)
        if result.returncode == 0 or 'valid preserved session-1 reservation required' not in result.stderr:
            raise ValueError('unauthorized notebook did not fail closed: ' + result.stderr[-1000:])
        if {p.name for p in Path(tmp).iterdir()} != {'cell.py'}:
            raise ValueError('unauthorized notebook left extracted source')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp); games = restore_game_mount(root / 'games')
        working = root / 'working'; working.mkdir()
        short = dict(env, SSV_REHEARSAL='1', TMPDIR=tmp, TMP=tmp, TEMP=tmp,
                     SSV_REHEARSAL_GAMES=str(games), SSV_REHEARSAL_WORKING=str(working),
                     SSV_REHEARSAL_SECONDS='1500', SSV_REHEARSAL_GROUPS='b1-ar25', SSV_REHEARSAL_ACTIONS='12')
        result = execute(code.replace("MODE='live'\n", "MODE='rehearsal'\n"), short, tmp, 180)
        if result.returncode:
            raise ValueError('packaged CPU rehearsal: ' + result.stderr[-1200:])
        spec = B.session_spec(runner.protocol(), '1')
        spec = {**spec, 'schedule': [s for s in spec['schedule'] if s['pair_id'] == 'b1-ar25'],
                'limits': {**spec['limits'], 'actions_per_episode': 12}}
        evaluation = evaluate_target(working / 'stagnation-supervision-v1', spec,
                                      mode='rehearsal', session='1', internal_seconds=1500)
        if not evaluation['technically_complete']:
            raise ValueError(str(evaluation['problems']))
        if any(p.name.startswith('stagnation-supervision-source-') for p in root.iterdir()):
            raise ValueError('rehearsal source cleanup')
    receipt = {'status': 'locally_reviewed_pending_explicit_approvals', 'authority_tests': tests.testsRun,
               'source_review_sha256': lock['source_review_sha256'],
               'package_lock_sha256': P.sha((P.OUT / 'review-source-lock.json').read_bytes()),
               'source_bindings': len(payload), 'unapproved_entry_rejected': True,
               'packaged_cpu_replay_and_lifecycle_passed': True, 'historical_r4_preserved': True,
               'gpu_calls': 0, 'reservations_created': 0, 'authorized_seconds': 0,
               'real_gpu_timing_measured': False, 'second_qualified_control_available': False}
    path = P.ROOT / 'reports/stagnation_supervision_v1_authorization_checks_r6.json'
    if path.exists():
        if json.loads(path.read_bytes()) != receipt:
            raise ValueError('review receipt drift')
    else:
        path.write_bytes(P.raw(receipt))
    return receipt


if __name__ == '__main__':
    print(json.dumps(review(), indent=2))
