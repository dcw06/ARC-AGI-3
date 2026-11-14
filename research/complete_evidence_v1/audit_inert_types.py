"""Loose upper view of memory-recoverable wasted actions in a saved stateless run.

An action "did nothing" as in audit_repeats_masked (board unchanged apart from estimated counter cells).
Its type is the action ID, plus the colour of the clicked cell for ACTION6. A did-nothing action counts as
"type known inert from older history" when, within the same level and attempt, that type had been tried
at least once before, never did anything, and its latest earlier try was older than the visible window.
"Type known inert, visible" is the same with the latest earlier try still visible.
This over-counts memory value: a type that did nothing twice may still be worth trying in a new place.

Usage: audit_inert_types.py <events.jsonl> <out.json> [window=8] [tick=2]
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from complete_evidence_v1 import records  # noqa: E402


def audit(events_path, window=8, tick=2):
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
        history = defaultdict(list)  # (level, reset, type) -> [(index, did_nothing)]
        c = Counter()
        for i, r in enumerate(recs):
            a = r['action']
            if a['id'] == 'RESET':
                continue
            before, final = r['before_frame'], r['response_frames'][-1]
            if final.shape == before.shape == shape:
                nothing = not ((final != before) & ~mask).any() and r['level_after'] == r['level_observed']
            else:
                nothing = False
            kind = (a['id'], int(before[a['y'], a['x']]) if a['x'] is not None and before.shape == shape else None)
            key = (r['level_observed'], r['reset_id'], kind)
            earlier = history[key]
            c['actions'] += 1
            c['did_nothing'] += nothing
            if nothing and earlier and all(n for _, n in earlier):
                c['inert_type_visible' if earlier[-1][0] >= i - window else 'inert_type_older'] += 1
            elif nothing and not earlier:
                c['did_nothing_first_try_of_type'] += 1
            elif nothing:
                c['did_nothing_type_sometimes_works'] += 1
            history[key].append((i, nothing))
        c = dict(c)
        c.update(game=game.split('-')[0], levels_completed=recs[-1]['level_after'])
        rows.append(c)
    return rows


if __name__ == '__main__':
    window = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    tick = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    rows = audit(sys.argv[1], window, tick)
    keys = ['actions', 'did_nothing', 'did_nothing_first_try_of_type', 'did_nothing_type_sometimes_works',
            'inert_type_visible', 'inert_type_older']
    total = {k: sum(r.get(k, 0) for r in rows) for k in keys}
    Path(sys.argv[2]).write_text(json.dumps({'window': window, 'tick': tick, 'events': sys.argv[1],
                                             'total': total, 'games': rows}, indent=1))
    print('game lvls | actions nothing first_try sometimes_works inert_visible inert_older')
    for r in rows:
        if r.get('did_nothing', 0) >= 5:
            print(r['game'], r['levels_completed'], '|', *[r.get(k, 0) for k in keys])
    print('TOTAL', total)
