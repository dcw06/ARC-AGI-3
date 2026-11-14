"""Repeat audit with step-counter cells ignored.

Most games move a counter on every action, so two boards are never identical and the exact audit sees
nothing. Here the counter is estimated from the run itself: cells changed by actions that changed at most
`tick` cells in total. Those cells are blanked before boards are compared. An action "does nothing" when
the blanked board is the same before and after. A counter also ticks during actions that change other
things, so with `extend` (default 1) a row or column holding three or more such cells is blanked across
their whole span. This is a heuristic: it can blank a real object that only ever moved one cell, and equal
boards still do not prove equal hidden state.

Usage: audit_repeats_masked.py <events.jsonl> <out.json> [window=8] [tick=2] [extend=1]
"""
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from complete_evidence_v1 import records  # noqa: E402


def audit(events_path, window=8, tick=2, extend=True):
    rows = []
    for game, data in sorted(records.load_run(events_path).items()):
        recs = data['records']
        shape = recs[0]['before_frame'].shape
        mask = np.zeros(shape, dtype=bool)
        for r in recs:
            final = r['response_frames'][-1]
            if final.shape == shape == r['before_frame'].shape:
                diff = final != r['before_frame']
                if 0 < diff.sum() <= tick:
                    mask |= diff
        if extend:
            base = mask.copy()
            for line, wide in ((base, mask), (base.T, mask.T)):
                for i, cells in enumerate(line):
                    hit = np.flatnonzero(cells)
                    if hit.size >= 3:
                        wide[i, hit[0]:hit[-1] + 1] = True

        def sig(frame):
            if frame.shape != shape:
                return hashlib.sha1(frame.tobytes()).hexdigest()
            blank = frame.copy()
            blank[mask] = 0
            return hashlib.sha1(blank.tobytes()).hexdigest()

        seen = defaultdict(list)
        boards = defaultdict(list)  # (reset, level, blanked board) -> indices where an action was chosen there
        c = Counter()
        for i, r in enumerate(recs):
            if r['action']['id'] == 'RESET':
                c['controller_resets_excluded'] += 1
                continue
            before, after = sig(r['before_frame']), sig(r['response_frames'][-1])
            place = (r['reset_id'], r['level_observed'], before)
            # Assessable: the agent stood on a board it had already acted from, in this attempt, out of view.
            if boards[place] and boards[place][0] < i - window:
                c['at_board_acted_from_before_out_of_view'] += 1
            boards[place].append(i)
            nothing = before == after and r['level_after'] == r['level_observed']
            c['actions'] += 1
            c['did_nothing'] += nothing
            key = (before, r['action']['id'], r['action']['x'], r['action']['y'])
            earlier = seen[key]
            if earlier:
                prev = recs[earlier[-1]]
                same_attempt = (prev['reset_id'] == r['reset_id'] and prev['level_observed'] == r['level_observed'])
                tag = 'visible' if earlier[-1] >= i - window else 'older'
                c['repeat_' + tag] += 1
                c['repeat_%s_did_nothing' % tag] += nothing
                c['repeat_%s_same_attempt' % tag] += same_attempt
                c['repeat_%s_same_attempt_did_nothing' % tag] += same_attempt and nothing
            seen[key].append(i)
        c = dict(c)
        c.update(game=game.split('-')[0], masked_cells=int(mask.sum()), levels_completed=recs[-1]['level_after'])
        rows.append(c)
    return rows


if __name__ == '__main__':
    window = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    tick = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    extend = bool(int(sys.argv[5])) if len(sys.argv) > 5 else True
    rows = audit(sys.argv[1], window, tick, extend)
    keys = ['actions', 'controller_resets_excluded', 'at_board_acted_from_before_out_of_view', 'did_nothing',
            'repeat_visible', 'repeat_visible_did_nothing', 'repeat_older',
            'repeat_older_did_nothing', 'repeat_older_same_attempt', 'repeat_older_same_attempt_did_nothing']
    total = {k: sum(r.get(k, 0) for r in rows) for k in keys}
    isolated = [r for r in rows if r['masked_cells'] > 0]
    coverage = {
        'records': sum(r.get('actions', 0) + r.get('controller_resets_excluded', 0) for r in rows),
        'eligible_actions_chosen_by_the_model': total['actions'],
        'games_with_a_counter_estimate': len(isolated),
        'actions_in_those_games': sum(r['actions'] for r in isolated),
        'games_without_a_counter_estimate': sorted(r['game'] for r in rows if r['masked_cells'] == 0),
        'actions_in_games_without_a_counter_estimate': sum(r['actions'] for r in rows if r['masked_cells'] == 0),
        'games_with_any_assessable_action': sorted(r['game'] for r in rows if r.get('at_board_acted_from_before_out_of_view')),
        'assessable_actions': total['at_board_acted_from_before_out_of_view'],
        'detected_same_attempt_repeats_out_of_view': total['repeat_older_same_attempt']}
    Path(sys.argv[2]).write_text(json.dumps({'window': window, 'tick': tick, 'extend': extend, 'events': sys.argv[1],
                                             'coverage': coverage, 'total': total, 'games': rows}, indent=1))
    print(json.dumps(coverage, indent=1))
    print('game lvls mask | actions nothing | vis vis_nothing | older older_nothing older_sameAttempt older_sameAttempt_nothing')
    for r in rows:
        print(r['game'], r['levels_completed'], r['masked_cells'], '|', *[r.get(k, 0) for k in keys])
    print('TOTAL', total)
