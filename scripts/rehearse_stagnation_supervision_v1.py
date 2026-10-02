# Derived from scripts/rehearse_action_effect_history_v1.py by scripts/derive_stagnation_supervision_v1.py; edit the derivation, not this file.
"""Connected-path CPU rehearsal: launcher -> supervisor -> worker -> host -> bridge -> runner (scripted model)."""
import argparse
import json
import os
from pathlib import Path
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def rehearse(fault='none', seconds=2400, workdir=None, root=ROOT, session='1'):
    from research.grounded_action_v1.engine import restore_game_mount
    workdir = Path(workdir or tempfile.mkdtemp(prefix='ssv-rehearsal-'))
    games = restore_game_mount(workdir / 'games')
    os.environ.update(SSV_REHEARSAL='1', CUDA_VISIBLE_DEVICES='', SSV_REHEARSAL_GAMES=str(games))
    from scripts.stagnation_supervision_v1_launch import run
    started = time.monotonic()
    receipt = run(workdir / 'working' / 'stagnation-supervision-v1', workdir / 'working', started=started, root=root,
                  mode='rehearsal', internal_seconds=seconds, fault=fault, session=session)
    return receipt, workdir / 'working' / 'stagnation-supervision-v1'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fault', default='none')
    parser.add_argument('--seconds', type=int, default=2400)
    parser.add_argument('--session', choices=('1', '2'), default='1')
    args = parser.parse_args()
    base = Path.home() / 'ssv-rehearsal'
    base.mkdir(exist_ok=True)
    receipt, output = rehearse(args.fault, args.seconds, tempfile.mkdtemp(dir=base), session=args.session)
    outer = json.loads((output / 'control/outer.json').read_bytes()) if (output / 'control/outer.json').exists() else None
    print(json.dumps({'receipt': receipt, 'outer_status': outer and outer['status'], 'outer_error': outer and outer['error'],
                      'run_evidence': outer and outer.get('run_evidence'), 'output': str(output)}, indent=1))
    if not outer or outer['status'] != 'study_complete_pending_independent_evaluation':
        for name in ('worker/failure.json', 'worker/host-status.json', 'worker/worker-result.json', 'monitor/failure.json'):
            if (output / name).exists():
                print('==', name, (output / name).read_text()[:1500])
        for log in sorted((output / 'logs').glob('*.json')):
            print('== log', log.name, log.read_text(errors='replace')[-2500:])
