"""One row per bp35 level-2 run: what the plan in reports/action_waste_v1/level2_run/plan.json asks for.

Read from each run's event log; no model, no game. "Changed nothing" and "in a loop" are the measures of
measure.py (boards only, step counter ignored). The 17 repeated level-1 actions are left out.

Usage (analysis or project environment): level2_table.py <out.json> <run folder>...
"""
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research'))
from recovery_v1 import measures, traces  # noqa: E402
from action_waste_v1.measure import loop_erased  # noqa: E402

LEVEL_ONE = 17
TEST_WORDS = re.compile(r'\btest(s|ed|ing)?\b|will show|shows? (whether|which)|see whether|to see if', re.I)


def row(folder):
    folder = Path(folder)
    events = [json.loads(line) for line in (folder / 'events.jsonl').read_text().splitlines()]
    config = next(e['config'] for e in events if e['kind'] == 'configuration')
    trace = next(iter(traces.load_events(folder / 'events.jsonl', source=folder.name).values()))
    keys = measures.keys(trace, measures.counter_mask(trace))
    steps = trace['steps']
    level_two = [i for i in range(LEVEL_ONE, len(steps)) if (steps[i - 1]['lc'] if i else 0) == 1]
    chosen = [i for i in level_two if steps[i]['a'] != 'RESET']
    nothing = [i for i in chosen if steps[i]['state'] == 'NOT_FINISHED' and keys[i + 1] == keys[i]]
    loops = sum(a['n'] - loop_erased([keys[a['first']]] + [keys[i + 1] for i in range(a['first'], a['last'] + 1)])
                for a in measures.attempts(trace) if a['level'] == 1 and a['n'])
    tests = sum(bool(TEST_WORDS.search(' '.join(h[1] for h in (steps[i]['notes'] or ()) if h[2] == 'tentative')))
                for i in chosen)
    usage = [e['metadata']['usage'] for e in events if e['kind'] == 'model_returned']
    out = [int(u['output_tokens']) for u in usage]
    return {'run': folder.name,
            'set_up': ('scoring rule' if config.get('state_objective') else
                       'lessons and check' if config.get('game_over_lessons') else 'unchanged'),
            'level_2_solved': any(steps[i]['lc'] >= 2 for i in level_two),
            'actions_on_level_2': len(level_two),
            'game_overs': sum(steps[i]['state'] == 'GAME_OVER' for i in level_two),
            'changed_nothing': len(nothing), 'changed_nothing_at': [i - LEVEL_ONE + 1 for i in nothing],
            'in_a_loop': int(loops), 'turns': len(chosen), 'turns_announcing_a_test': tests,
            'model_calls': len(usage), 'output_tokens': sum(out),
            'output_per_call_median': round(statistics.median(out)) if out else None}


if __name__ == '__main__':
    rows = [row(path) for path in sys.argv[2:]]
    Path(sys.argv[1]).write_text(json.dumps({'runs': rows}, indent=1) + '\n')
    for r in rows:
        print(json.dumps(r))
