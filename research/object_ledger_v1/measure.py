"""Are "things never touched" and "one of a kind used, its twin ignored" general, or only ls20? Saved play, no model.

For every game of a saved run, the controller's own inventory (research/claude_arc_v1/things.py) is run over
the actions, level by level. When a level ends (solved, or the run stops on it), it counts:

  things           things on the board then (objects, not ground; see things.py)
  untouched        of those, things at which nothing ever changed on the level, nor right beside them
  twins ignored    looks with several instances where something happened at one instance and another
                   instance of the same look is untouched

Usage (analysis environment): measure.py <out.json>
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research'))
from recovery_v1 import measures, traces  # noqa: E402
from claude_arc_v1.things import Inventory  # noqa: E402


def one(trace):
    mask = measures.counter_mask(trace)
    inventory, rows = Inventory(), []
    before, level = trace['initial'], 0

    def close(board, solved):
        things = inventory.rows(board)
        by_look = {}
        for thing in things:
            by_look.setdefault(thing['letter'], []).append(bool(thing['changed_at'] or thing['beside_change_at']))
        rows.append({'level': level + 1, 'solved': solved, 'things': len(things),
                     'untouched': sum(not t for ts in by_look.values() for t in ts),
                     'looks': len(by_look),
                     'looks_all_untouched': sum(not any(ts) for ts in by_look.values()),
                     'twins_ignored': sum(any(ts) and not all(ts) for ts in by_look.values()),
                     'view_moved': bool(inventory.view_moved)})

    for i, step in enumerate(trace['steps']):
        click = (step['x'], step['y']) if step['a'] == 'ACTION6' and step['x'] is not None else None
        if step['a'] != 'RESET':
            inventory.observe(before, [step['frame']], 't%d' % (i + 1), click=click, ignore=mask)
        if step['lc'] > level:
            close(before, True)          # the board the level was solved from
            inventory.new_level()
            level = step['lc']
        before = step['frame']
    if trace['steps'] and trace['steps'][-1]['state'] != 'WIN':
        close(before, False)
    return rows


def main(out_path):
    result = {}
    sources = {('opus55-ours-6nov', game): trace for game, trace in traces.load_events().items()}
    sources.update(traces.load_recordings())
    for (source, game), trace in sorted(sources.items()):
        result.setdefault(source, {})[game.split('-')[0]] = one(trace)
    Path(out_path).write_text(json.dumps(result, indent=1) + '\n')
    return result


if __name__ == '__main__':
    for source, games in main(sys.argv[1]).items():
        for solved in (True, False):
            levels = [r for rows in games.values() for r in rows if r['solved'] is solved and not r['view_moved']]
            if not levels:
                continue
            n = len(levels)
            print('%-26s %-10s levels %3d | things per level %5.1f | untouched %5.1f (%2.0f%%) | levels with a twin ignored %3d (%2.0f%%) | '
                  'looks wholly untouched per level %4.1f' % (
                      source, 'solved' if solved else 'not solved', n, sum(r['things'] for r in levels) / n,
                      sum(r['untouched'] for r in levels) / n,
                      100 * sum(r['untouched'] for r in levels) / max(1, sum(r['things'] for r in levels)),
                      sum(r['twins_ignored'] > 0 for r in levels), 100 * sum(r['twins_ignored'] > 0 for r in levels) / n,
                      sum(r['looks_all_untouched'] for r in levels) / n))
