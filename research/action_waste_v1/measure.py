"""Where actions go that could not have helped: measured on saved play, every game, no model calls.

Everything is judged from returned boards only (step-counter cells ignored, see recovery_v1.measures).
No game source is read and nothing here knows what any object in any game means.

Per action chosen by the agent:

  no effect        the board after equals the board before
  known no effect  no effect, and the same action from the same board had already been seen to do nothing
                   earlier in the game ("same action" for a click: the same cell, or, in the wider reading,
                   any cell of the same connected single-colour region)
  known fatal      the same action from the same board had already ended the game
  colour no effect a click with no effect on a cell whose colour had been clicked at least twice before in
                   this game and never changed anything
  loop             actions inside a cycle: the attempt later stood on a board it had already stood on, so
                   everything between the two visits bought no progress (includes every no-effect action)
  retrace excess   after a failed attempt, the actions the next attempt needed to get back to the furthest
                   board it regained, minus the shortest route to that board through transitions already
                   observed on the level

`same pair, other result` counts repeats of a (board, action) pair whose result differed from the earlier
one. Each is a case where "we already know what this does" would have been wrong.

Usage (analysis environment): measure.py <out.json>
"""
import json
import sys
from collections import deque
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research'))
from recovery_v1 import measures, traces  # noqa: E402

LEVEL2 = sorted((ROOT / '.cache/claude_arc_runs').glob('bp35-l2-*-20261115T014800Z'))
FIELDS = ('actions', 'no_effect', 'known_no_effect', 'known_no_effect_region', 'known_fatal', 'clicks',
          'click_no_effect', 'colour_no_effect', 'loop', 'retrace', 'retrace_excess', 'same_pair',
          'same_pair_other_result')


def region(frame, x, y):
    """The connected single-colour region holding (x, y), named by its colour and its first cell."""
    colour, seen, todo = frame[y, x], {(x, y)}, deque([(x, y)])
    while todo:
        cx, cy = todo.popleft()
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if 0 <= nx < frame.shape[1] and 0 <= ny < frame.shape[0] and (nx, ny) not in seen and frame[ny, nx] == colour:
                seen.add((nx, ny))
                todo.append((nx, ny))
    return int(colour), min(seen, key=lambda c: (c[1], c[0]))


def loop_erased(keys):
    path, where = [], {}
    for key in keys:
        if key in where:
            for dropped in path[where[key] + 1:]:
                del where[dropped]
            del path[where[key] + 1:]
        else:
            where[key] = len(path)
            path.append(key)
    return len(path) - 1


def shortest(edges, start, goal):
    if start == goal:
        return 0
    seen, todo = {start}, deque([(start, 0)])
    while todo:
        node, far = todo.popleft()
        for nxt in edges.get(node, ()):
            if nxt == goal:
                return far + 1
            if nxt not in seen:
                seen.add(nxt)
                todo.append((nxt, far + 1))
    return None


def one(trace):
    mask = measures.counter_mask(trace)
    keys = measures.keys(trace, mask)
    steps = trace['steps']
    row = dict.fromkeys(FIELDS, 0)
    pairs, regions, colours = {}, {}, {}
    before, state = trace['initial'], 'NOT_FINISHED'
    for i, step in enumerate(steps):
        if step['a'] != 'RESET' and state != 'GAME_OVER':
            row['actions'] += 1
            unchanged = keys[i + 1] == keys[i] and step['state'] == 'NOT_FINISHED'
            result = (keys[i + 1], step['state'])
            pair = (keys[i], step['a'], step['x'], step['y'])
            click = step['a'] == 'ACTION6' and step['x'] is not None and before.ndim == 2
            known = pair in pairs
            same_result = known and pairs[pair] == result
            row['no_effect'] += unchanged
            row['same_pair'] += known
            row['same_pair_other_result'] += known and not same_result
            row['known_no_effect'] += unchanged and same_result
            row['known_fatal'] += known and pairs[pair][1] == 'GAME_OVER'
            pairs.setdefault(pair, result)
            if click:
                row['clicks'] += 1
                row['click_no_effect'] += unchanged
                where = (keys[i], region(before, step['x'], step['y']))
                row['known_no_effect_region'] += unchanged and regions.get(where) is True
                regions.setdefault(where, unchanged)
                tried = colours.setdefault(int(before[step['y'], step['x']]), [0, 0])
                row['colour_no_effect'] += unchanged and tried[0] >= 2 and tried[1] == 0
                tried[0] += 1
                tried[1] += not unchanged
            else:
                row['known_no_effect_region'] += unchanged and same_result
        before, state = step['frame'], step['state']

    attempts = measures.attempts(trace)
    edges, level_of = {}, None
    for n, attempt in enumerate(attempts):
        ks = [keys[attempt['first']]] + [keys[i + 1] for i in range(attempt['first'], attempt['last'] + 1)]
        row['loop'] += attempt['n'] - loop_erased(ks) if attempt['n'] else 0
        if level_of != attempt['level']:
            edges, level_of = {}, attempt['level']
        previous = attempts[n - 1] if n else None
        if previous and previous['level'] == attempt['level'] and previous['outcome'] in ('game_over', 'abandoned'):
            earlier = [keys[previous['first']]] + [keys[i + 1] for i in range(previous['first'], previous['last'] + 1)]
            first_at = {}
            for j, key in enumerate(ks):
                first_at.setdefault(key, j)
            reached = [j for j, key in enumerate(earlier) if key in first_at]
            if reached and ks[0] == earlier[0]:
                goal = earlier[max(reached)]
                best = shortest(edges, ks[0], goal)
                row['retrace'] += first_at[goal]
                if best is not None:
                    row['retrace_excess'] += max(0, first_at[goal] - best)
        for a, b in zip(ks, ks[1:]):
            edges.setdefault(a, set()).add(b)
    return row


def table(all_traces):
    by_source = {}
    for (source, game), trace in sorted(all_traces.items()):
        by_source.setdefault(source, {})[game.split('-')[0]] = {k: int(v) for k, v in one(trace).items()}
    out = {}
    for source, games in by_source.items():
        total = {k: sum(g[k] for g in games.values()) for k in FIELDS}
        total['games'] = len(games)
        for field in ('no_effect', 'known_no_effect', 'known_no_effect_region', 'colour_no_effect', 'loop'):
            total['games_with_' + field] = sum(g[field] > 0 for g in games.values())
        out[source] = {'total': total, 'games': games}
    return out


def main(out_path):
    everything = {('opus55-ours-6nov', game): trace for game, trace in traces.load_events().items()}
    everything.update(traces.load_recordings())
    for folder in LEVEL2:
        loaded = traces.load_events(folder / 'events.jsonl', source=folder.name)
        everything.update({(folder.name.replace('-20261115T014800Z', ''), game): t for game, t in loaded.items()})
    result = table(everything)
    Path(out_path).write_text(json.dumps(result, indent=1) + '\n')
    return result


if __name__ == '__main__':
    for source, block in main(sys.argv[1]).items():
        t = block['total']
        print('%-28s games %2d actions %5d | no effect %4d (%4.1f%%, %2d games) known %3d region %3d (%d games) | '
              'known fatal %d | clicks %4d no-effect %3d colour %3d | loop %4d (%4.1f%%) | retrace %3d excess %3d | '
              'same pair %3d other result %2d' % (
                  source, t['games'], t['actions'], t['no_effect'], 100 * t['no_effect'] / max(1, t['actions']),
                  t['games_with_no_effect'], t['known_no_effect'], t['known_no_effect_region'],
                  t['games_with_known_no_effect_region'], t['known_fatal'], t['clicks'], t['click_no_effect'],
                  t['colour_no_effect'], t['loop'], 100 * t['loop'] / max(1, t['actions']), t['retrace'],
                  t['retrace_excess'], t['same_pair'], t['same_pair_other_result']))
