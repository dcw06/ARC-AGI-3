"""Connected-path CPU rehearsal of one feedback-action v1 session (no model, no GPU, no provider):
first cell -> supervisor -> worker (+ gated exec) -> monitor -> model host -> bridge -> runner -> real offline engine.

The interpreters default to the current one; FA1_REHEARSAL_GAME_PYTHON / FA1_REHEARSAL_MODEL_PYTHON select the
installed game and model interpreters, FA1_REHEARSAL_TOKENIZER the pinned tokenizer and FA1_REHEARSAL_GRAMMAR=1 the
pinned guided-decoding grammar check (see live/rehearsal.py). Scripted completions say nothing about model behaviour.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def stage(workdir):
    """The development games: staged from a replica competition mount by the live staging code (standard library
    only) when FA1_REHEARSAL_COMPETITION names one, else restored from the committed development archive."""
    competition = os.environ.get('FA1_REHEARSAL_COMPETITION')
    if competition:
        from certification.phase4_integrated_v2.game_assets import stage_games
        manifest = json.loads((ROOT / 'reports/phase4_v2_offline_package.json').read_bytes())
        return stage_games(Path(competition) / 'environment_files', Path(workdir) / 'games', manifest)
    from research.grounded_action_v1.engine import restore_game_mount
    return restore_game_mount(Path(workdir) / 'games')


def rehearse(fault='none', seconds=2400, workdir=None, root=ROOT, session=1):
    workdir = Path(workdir or tempfile.mkdtemp(prefix='fa1-rehearsal-'))
    games = stage(workdir)
    os.environ.update(FA1_REHEARSAL='1', CUDA_VISIBLE_DEVICES='', FA1_REHEARSAL_GAMES=str(games))
    from scripts.feedback_action_v1_launch import run
    started = time.monotonic()
    output = workdir / 'working' / 'feedback-action-v1'
    receipt = run(output, workdir / 'working', started=started, root=root, mode='rehearsal', internal_seconds=seconds,
                  fault=fault, session=session)
    return receipt, output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fault', default='none')
    parser.add_argument('--seconds', type=int, default=2400)
    parser.add_argument('--session', type=int, default=1)
    args = parser.parse_args()
    base = Path.home() / 'fa1-rehearsal'
    base.mkdir(exist_ok=True)
    receipt, output = rehearse(args.fault, args.seconds, tempfile.mkdtemp(dir=base), session=args.session)
    outer = json.loads((output / 'control/outer.json').read_bytes()) if (output / 'control/outer.json').exists() else None
    from scripts.evaluate_feedback_action_v1 import evaluate_output
    value = evaluate_output(output, mode='rehearsal', rehearsal_seconds=args.seconds) if outer else None
    print(json.dumps({'receipt': receipt, 'outer_status': outer and outer['status'], 'outer_error': outer and outer['error'],
                      'run_evidence': outer and outer.get('run_evidence'), 'output': str(output),
                      'technically_complete': value and value['technically_complete'],
                      'lifecycle_errors': value and value['lifecycle_errors'],
                      'evaluation': value and value['evaluation'] and {
                          k: value['evaluation'][k] for k in ('replay_passed', 'technical_validity', 'failure_rules',
                                                              'carried_statements', 'problems', 'session_2_permitted')}},
                     indent=1, default=str))
    if not outer or outer['status'] != 'study_complete_pending_independent_evaluation':
        for name in ('worker/failure.json', 'worker/host-status.json', 'worker/worker-result.json', 'monitor/failure.json'):
            if (output / name).exists():
                print('==', name, (output / name).read_text()[:1500])
        for log in sorted((output / 'logs').glob('*.json')):
            print('== log', log.name, log.read_text(errors='replace')[-2500:])
