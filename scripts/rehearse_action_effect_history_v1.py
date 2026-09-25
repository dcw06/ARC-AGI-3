"""Connected-path CPU rehearsal: launcher -> supervisor -> worker -> host -> bridge -> runner (scripted model)."""
import argparse
import json
import os
from pathlib import Path
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def rehearse(fault='none', seconds=2400, workdir=None, root=ROOT):
    from research.grounded_action_v1.engine import restore_game_mount
    workdir = Path(workdir or tempfile.mkdtemp(prefix='aeh-rehearsal-'))
    games = restore_game_mount(workdir / 'games')
    os.environ.update(AEH_REHEARSAL='1', CUDA_VISIBLE_DEVICES='', AEH_REHEARSAL_GAMES=str(games))
    from scripts.action_effect_history_v1_launch import run
    started = time.monotonic()
    receipt = run(workdir / 'working' / 'action-effect-history-v1', workdir / 'working', started=started, root=root,
                  mode='rehearsal', internal_seconds=seconds, fault=fault)
    return receipt, workdir / 'working' / 'action-effect-history-v1'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fault', default='none')
    parser.add_argument('--seconds', type=int, default=2400)
    args = parser.parse_args()
    base = Path.home() / 'aeh-rehearsal'
    base.mkdir(exist_ok=True)
    receipt, output = rehearse(args.fault, args.seconds, tempfile.mkdtemp(dir=base))
    outer = json.loads((output / 'control/outer.json').read_bytes()) if (output / 'control/outer.json').exists() else None
    print(json.dumps({'receipt': receipt, 'outer_status': outer and outer['status'], 'outer_error': outer and outer['error'],
                      'run_evidence': outer and outer.get('run_evidence'), 'output': str(output)}, indent=1))
    if not outer or outer['status'] != 'study_complete_pending_independent_evaluation':
        for name in ('worker/failure.json', 'worker/host-status.json', 'worker/worker-result.json', 'monitor/failure.json'):
            if (output / name).exists():
                print('==', name, (output / name).read_text()[:1500])
        for log in sorted((output / 'logs').glob('*.json')):
            print('== log', log.name, log.read_text(errors='replace')[-2500:])
