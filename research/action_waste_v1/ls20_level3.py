"""Play ls20 level 3 from its start on the local game file, unchanged and with every memory layer on.

Each run first repeats the 60 saved actions of the 6 November run that solved levels 1 and 2 (no model
call; every observation must hash to the saved one), so the agent starts level 3 with the saved board and
notes. It then plays with its own choices until level 3 is solved or 65 new actions are used. On
6 November the agent spent 40 actions on this level without solving it before the run's cap.

    control   the 6 November harness, unchanged
    memory    game_over_lessons, no_effect_lessons (the agent decides when to explain, after 1 to 4
              further actions) and lesson_check

    ls20_level3.py check                      no model call
    ls20_level3.py batch <stamp> --send       four runs, one at a time
    ls20_level3.py summary <out.json> <stamp>

Usage (project environment), from the repository root.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'research'))
from research.claude_arc_v1 import config as C  # noqa: E402
from research.action_waste_v1 import level_runs as L  # noqa: E402
from research.action_waste_v1.local_game import check_against_saved_run  # noqa: E402

GAME = 'ls20-9607627b'
START = 60          # the saved run completed level 2 with its 60th action
CAP = 65
ARMS = ('control', 'memory')
REPEATS = 2


def settings(arm):
    return C.Config(**{**json.loads(L.CONTROL.read_text()), 'mode': 'online', 'games': ['ls20'],
                       'resume_events': L.SAVED, 'resume_actions': START,
                       'max_actions_per_game': START + CAP, 'stop_after_levels': 3,
                       'max_model_calls': CAP + 60, **L.ARMS[arm]})


def check():
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    differs, total = check_against_saved_run(GAME)
    print(GAME, '| local game against the saved run:', total, 'actions, observations that differ:', differs or 'none')
    backend = L.SavedReplies(settings('control'), GAME, START)
    played = L.play(GAME, 'control', 'waste-check-ls20-control-%s' % stamp, backend, settings('control'))
    events = [json.loads(line) for line in (L.RUNS / played['run'] / 'events.jsonl').read_text().splitlines()]
    mine = [e['action'] for e in events if e['kind'] == 'transition']
    saved = []
    with (ROOT / L.SAVED).open() as handle:
        for line in handle:
            if GAME in line and '"kind":"transition"' in line:
                saved.append(json.loads(line)['action'])
    print('   control from action %d with the saved replies: %d actions, equal to the saved run: %s; level 3 start: '
          'levels completed %s' % (START, len(mine), mine == saved[:len(mine)],
                                   [e['after']['levels_completed'] for e in events if e['kind'] == 'transition'][START - 1]))
    first = L.SavedReplies(settings('memory'), GAME, START, stop_after=0)
    L.play(GAME, 'memory', 'waste-check-ls20-memory-%s' % stamp, first, settings('memory'))
    mine, theirs = first.requests[0], backend.requests[0]
    body = json.loads(mine['messages'][1]['content'])
    print('   memory arm, first request: system prompt equal to control %s, user message equal to control %s, '
          'extra evidence %s' % (mine['messages'][0]['content'] == theirs['messages'][0]['content'],
                                 mine['messages'][1]['content'] == theirs['messages'][1]['content'],
                                 sorted(set(body['evidence']) - {'current', 'history', 'history_omitted', 'hypotheses'}) or 'none'))


def batch(stamp):
    for n in range(1, REPEATS + 1):
        for arm in ARMS:
            out = L.play(GAME, arm, L.name_of(GAME, arm, n, stamp), config=settings(arm))
            if out['problems']:
                print('batch stopped: the last run ended with a problem', flush=True)
                return


if __name__ == '__main__':
    command = sys.argv[1]
    if command == 'check':
        check()
    elif command == 'batch' and len(sys.argv) == 4 and sys.argv[3] == '--send':
        batch(sys.argv[2])
    elif command == 'summary':
        rows = [L.summary(L.RUNS / L.name_of(GAME, arm, n, sys.argv[3])) for arm in ARMS for n in range(1, REPEATS + 1)
                if (L.RUNS / L.name_of(GAME, arm, n, sys.argv[3]) / 'events.jsonl').exists()]
        Path(sys.argv[2]).write_text(json.dumps({'runs': rows}, indent=1) + '\n')
        for row in rows:
            print(json.dumps({k: v for k, v in row.items() if k not in ('lessons', 'game_over_lessons')}))
    else:
        raise SystemExit(__doc__)
