"""POST-HOC descriptive inspection of the Tier B probe result (Track 3). Written after the probe ran.

The probe's criterion (frozen before the run) selected ls20. Its per-step change counts were all exactly 52 while
the scripted actions rotated 1, 2, 3, 4, which prompted this inspection. It changes nothing: the probe result,
its criterion and the selection stand as recorded, and no further policy or candidate is run.

For each probe step it reports where the changed cells lie: the cells in the bottom rows (y >= 60) and the bounding
box of the rest, and whether the frame outside the bottom rows equals one already seen in the episode. This is a
description for the reviewer, not a criterion and not a mask in any detector.

Run once: python -m research.stagnation_supervision_v1.tier_b_inspection
"""
import json
from pathlib import Path
import tempfile

from research.stagnation_supervision_v1 import tier_b_probe as P
from research.transition_evidence_v1 import transition as T1

RESULTS = P.ROOT / 'reports/stagnation_supervision_v1_tier_b_inspection.json'
BOTTOM_ROWS_FROM = 60


def raws_for(game_id):
    captured = {}
    history = P.T2.history

    def keep(raws, *args):
        captured['raws'] = raws
        return history(raws, *args)
    P.T2.history = keep
    try:
        from research.grounded_action_v1.engine import restore_game_mount
        with tempfile.TemporaryDirectory() as folder:
            games = restore_game_mount(Path(folder) / 'games')
            P.probe(game_id, games, Path(folder) / 'rec', P.environment_check_module().scripted)
    finally:
        P.T2.history = history
    return captured['raws']


def inspect(raws):
    steps, seen_upper = [], set()
    for raw in raws:
        pre = raw['before']['frames'][-1]
        seen_upper.add(json.dumps(pre[:BOTTOM_ROWS_FROM]))
        post = raw['outcome']['after']['frames'][-1]
        cells = T1.compare(pre, post)[1]
        bottom = [c for c in cells if c[1] >= BOTTOM_ROWS_FROM]
        rest = [c for c in cells if c[1] < BOTTOM_ROWS_FROM]
        upper = json.dumps(post[:BOTTOM_ROWS_FROM])
        steps.append({'step': raw['identity']['action_index'], 'action_id': raw['dispatched']['action_id'],
                      'changed_cells': len(cells), 'changed_in_bottom_rows': len(bottom),
                      'rest_bbox_xyxy': ([min(c[0] for c in rest), min(c[1] for c in rest),
                                          max(c[0] for c in rest), max(c[1] for c in rest)] if rest else None),
                      'frame_above_bottom_rows_seen_before': upper in seen_upper})
        seen_upper.add(upper)
    return steps


def run():
    probe = json.loads(P.RESULTS.read_text(encoding='utf-8'))
    game = probe['selected']
    steps = inspect(raws_for(game))
    return {'version': 'stagnation_supervision_v1_tier_b_inspection', 'post_hoc': True, 'game_id': game,
            'note': 'descriptive only; the frozen probe result and selection are unchanged', 'steps': steps,
            'steps_with_bottom_row_change': sum(s['changed_in_bottom_rows'] > 0 for s in steps),
            'steps_whose_frame_above_bottom_rows_was_seen_before':
                sum(s['frame_above_bottom_rows_seen_before'] for s in steps)}


if __name__ == '__main__':
    if RESULTS.exists():
        raise SystemExit('refusing to overwrite the write-once result: ' + str(RESULTS))
    result = run()
    RESULTS.write_text(json.dumps(result, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'steps'}))
