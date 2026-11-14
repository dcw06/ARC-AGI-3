"""Count actions whose outcome was already recorded earlier in the same game of a saved stateless run.

An action is a "repeat" when the same action (and click cell) was taken earlier from a board with exactly
the same cells. The agent saw only its last `window` transitions, so a repeat is split by whether an earlier
occurrence was still visible or only in older history. This is a floor on memory-recoverable waste: it only
catches exact board matches, and a matching board does not prove the hidden game state matched.

Usage: audit_repeats.py <events.jsonl> <out.json> [window=8]
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from complete_evidence_v1 import records  # noqa: E402


def audit(events_path, window=8):
    games = records.load_run(events_path)
    rows = []
    for game, data in sorted(games.items()):
        recs = data['records']
        seen_pair, seen_board = defaultdict(list), defaultdict(list)
        c = defaultdict(int)
        for i, rec in enumerate(recs):
            action = rec['action']
            board = rec['before_frame_id']
            changed = any(f.shape != rec['before_frame'].shape or not np.array_equal(f, rec['before_frame'])
                          for f in rec['response_frames'])
            level_up = rec['level_after'] > rec['level_observed']
            if action['id'] != 'RESET':
                c['actions'] += 1
                c['no_change'] += not changed
                key = (board, action['id'], action['x'], action['y'])
                earlier = seen_pair[key]
                if i >= window:
                    c['decisions_with_older_history'] += 1
                if earlier:
                    visible = earlier[-1] >= i - window
                    prev = recs[earlier[-1]]
                    same = (len(prev['response_frame_ids']) == len(rec['response_frame_ids'])
                            and prev['response_frame_ids'] == rec['response_frame_ids'])
                    after_reset = prev['reset_id'] != rec['reset_id'] or prev['level_observed'] != rec['level_observed']
                    tag = 'visible' if visible else 'older'
                    c['repeat_' + tag] += 1
                    c['repeat_%s_same_outcome' % tag] += same
                    c['repeat_%s_no_change' % tag] += (not changed)
                    c['repeat_%s_after_reset' % tag] += after_reset
                    if not visible and not changed and same:
                        c['older_known_no_effect'] += 1
                boards_before = seen_board[board]
                if boards_before and boards_before[-1] < i - window:
                    c['board_revisit_older'] += 1
                seen_pair[key].append(i)
            else:
                c['resets'] += 1
            seen_board[board].append(i)
            c['level_ups'] += level_up
        c = dict(c)
        c.update(game=game.split('-')[0], levels_completed=recs[-1]['level_after'],
                 final_state=recs[-1]['state_after'], records=len(recs),
                 last_level_up_event=max([r['event_seq'] for r in recs if r['level_after'] > r['level_observed']],
                                         default=0))
        rows.append(c)
    return rows


if __name__ == '__main__':
    window = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    rows = audit(sys.argv[1], window)
    keys = ['actions', 'no_change', 'repeat_visible', 'repeat_visible_no_change', 'repeat_older',
            'repeat_older_same_outcome', 'repeat_older_no_change', 'repeat_older_after_reset',
            'older_known_no_effect', 'board_revisit_older', 'resets']
    total = {k: sum(r.get(k, 0) for r in rows) for k in keys}
    Path(sys.argv[2]).write_text(json.dumps({'window': window, 'events': sys.argv[1], 'total': total,
                                             'games': rows}, indent=1))
    print('game lvls lastUp ' + ' '.join(k[:14] for k in keys))
    for r in rows:
        print(r['game'], r['levels_completed'], r['last_level_up_event'], *[r.get(k, 0) for k in keys])
    print('TOTAL', total)
