"""Test the object ledger on ls20 (the game it was designed on) and on three games never looked at while
building it: tr87, cd82 and g50t. Local game files, no ARC service, no scorecard.

Each run first repeats the saved 6 November actions up to the start of the level that run stopped on (no
model call; every observation must hash to the saved one), then plays 100 new actions with its own choices.

    control   the 6 November harness, unchanged
    ledger    every memory layer (lessons after a game over and after an action that changed nothing, the
              check of each action against them) plus the object ledger

    held_out_runs.py check                       no model call
    held_out_runs.py game <game id> <stamp> --send    the four runs of one game, one after another
    held_out_runs.py summary <out.json> <stamp>

Usage (project environment), from the repository root. Set ARC_CLAUDE_TOKEN_FILE to put the runs on the
second subscription.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'research'))
from research.claude_arc_v1 import config as C  # noqa: E402
from research.claude_arc_v1.things import Inventory  # noqa: E402
from research.action_waste_v1 import level_runs as L  # noqa: E402
from research.action_waste_v1.local_game import check_against_saved_run  # noqa: E402

# game -> saved actions repeated before play (the level the 6 November run stopped on begins there)
GAMES = {'ls20-9607627b': 60, 'tr87-cd924810': 61, 'cd82-fb555c5d': 35, 'g50t-5849a774': 39}
DESIGNED_ON, HELD_OUT = ('ls20',), ('tr87', 'cd82', 'g50t')
# which arm goes first alternates between games, so neither arm always runs earlier
ORDER = {'ls20-9607627b': ('control', 'ledger'), 'tr87-cd924810': ('ledger', 'control'),
         'cd82-fb555c5d': ('control', 'ledger'), 'g50t-5849a774': ('ledger', 'control')}
NEW_ACTIONS, REPEATS = 100, 2


def settings(game, arm):
    start = GAMES[game]
    return C.Config(**{**json.loads(L.CONTROL.read_text()), 'mode': 'online', 'games': [game.split('-')[0]],
                       'resume_events': L.SAVED, 'resume_actions': start,
                       'max_actions_per_game': start + NEW_ACTIONS, 'max_model_calls': NEW_ACTIONS + 80, **L.ARMS[arm]})


def name_of(game, arm, n, stamp):
    return 'ledger-%s-%s-%d-%s' % (game.split('-')[0], arm, n, stamp)


def check():
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    for game, start in GAMES.items():
        prefix = game.split('-')[0]
        differs, total = check_against_saved_run(game)
        print(game, '| local game against the saved run:', total, 'actions, observations that differ:', differs or 'none')
        backend = L.SavedReplies(settings(game, 'control'), game, start)
        played = L.play(game, 'control', 'ledger-check-%s-control-%s' % (prefix, stamp), backend, settings(game, 'control'))
        events = [json.loads(line) for line in (L.RUNS / played['run'] / 'events.jsonl').read_text().splitlines()]
        mine = [e['action'] for e in events if e['kind'] == 'transition']
        saved = []
        with (ROOT / L.SAVED).open() as handle:
            for line in handle:
                if game in line and '"kind":"transition"' in line:
                    saved.append(json.loads(line)['action'])
        print('   control from action %d with the saved replies: %d actions, equal to the saved run: %s'
              % (start, len(mine), mine == saved[:len(mine)]))
        first = L.SavedReplies(settings(game, 'ledger'), game, start, stop_after=0)
        L.play(game, 'ledger', 'ledger-check-%s-ledger-%s' % (prefix, stamp), first, settings(game, 'ledger'))
        mine, theirs = first.requests[0], backend.requests[0]
        with_it, without = json.loads(mine['messages'][1]['content']), json.loads(theirs['messages'][1]['content'])
        things = with_it['evidence'].pop('things', {'looks': []})
        same_rest = (with_it['evidence'] == without['evidence']
                     and with_it['procedure'][:len(without['procedure'])] == without['procedure'])
        print('   ledger arm, first request: system prompt equal %s, the rest of the evidence equal %s, looks listed %d, '
              'untouched things %d' % (mine['messages'][0]['content'] == theirs['messages'][0]['content'], same_rest,
                                       len(things['looks']),
                                       sum(bool(i.get('untouched')) for look in things['looks'] for i in look['instances'])))


def game_batch(game, stamp):
    for n in range(1, REPEATS + 1):
        for arm in ORDER[game]:
            out = L.play(game, arm, name_of(game, arm, n, stamp), config=settings(game, arm))
            if out['problems']:
                print('stopped: the last run ended with a problem', flush=True)
                return


def touched(folder, start):
    """What the run left untouched, measured the same way for both arms: the controller's inventory run over
    the run's own frames, from the start of play."""
    from recovery_v1 import measures, traces
    trace = next(iter(traces.load_events(Path(folder) / 'events.jsonl', source=Path(folder).name).values()))
    mask = measures.counter_mask(trace)
    events = [json.loads(line) for line in (Path(folder) / 'events.jsonl').read_text().splitlines()]
    steps = [e for e in events if e['kind'] == 'transition']
    inventory, rows = Inventory(), []

    def close(board, solved, level):
        by_look = {}
        for thing in inventory.rows(board):
            by_look.setdefault(thing['letter'], []).append(bool(thing['changed_at'] or thing['beside_change_at']))
        things = sum(len(v) for v in by_look.values())
        rows.append({'level': level, 'solved': solved, 'things': things,
                     'untouched': sum(not t for v in by_look.values() for t in v),
                     'kinds_wholly_untouched': sum(not any(v) for v in by_look.values()),
                     'twins_ignored': sum(any(v) and not all(v) for v in by_look.values())})

    import numpy as np
    for i in range(start, len(steps)):
        step = steps[i]
        before = np.asarray(step['before']['frames'][-1], dtype=np.uint8)
        action = step['action']
        if action['action_id'] != 0:
            click = (action['action_data']['x'], action['action_data']['y']) if action['action_id'] == 6 else None
            inventory.observe(before, [np.asarray(f, dtype=np.uint8) for f in step['after']['frames']],
                              't%d' % (i + 1), click=click, ignore=mask)
        if step['after']['levels_completed'] > step['before']['levels_completed']:
            close(before, True, step['before']['levels_completed'] + 1)
            inventory.new_level()
    last = steps[-1]
    close(np.asarray(last['after']['frames'][-1], dtype=np.uint8), False, last['after']['levels_completed'] + 1)
    return rows


def summary(folder):
    folder = Path(folder)
    row = L.summary(folder)
    events = [json.loads(line) for line in (folder / 'events.jsonl').read_text().splitlines()]
    notes, checks, body = [], 0, None
    for event in events:
        if event['kind'] == 'model_entered':
            body = json.loads(event['request']['messages'][1]['content'])
            index = event['action_index']
        elif event['kind'] == 'model_returned':
            reply = json.loads(event['content'])
            if 'thing_check' in body['output_contract']:
                checks += bool(reply.get('thing_check'))
                if reply.get('thing_note'):
                    notes.append({'at_action': index + 1 - row['started_after_action'], **reply['thing_note']})
    levels = touched(folder, row['started_after_action'])
    row.update({'thing_notes': notes, 'thing_checks_written': checks, 'things_by_level': levels,
                'open_level_things': levels[-1]['things'], 'open_level_untouched': levels[-1]['untouched'],
                'open_level_twins_ignored': levels[-1]['twins_ignored']})
    return row


if __name__ == '__main__':
    command = sys.argv[1]
    if command == 'check':
        check()
    elif command == 'game' and len(sys.argv) == 5 and sys.argv[4] == '--send':
        game_batch(sys.argv[2], sys.argv[3])
    elif command == 'summary':
        rows = [summary(L.RUNS / name_of(game, arm, n, sys.argv[3])) for game in GAMES for arm in ('control', 'ledger')
                for n in range(1, REPEATS + 1) if (L.RUNS / name_of(game, arm, n, sys.argv[3]) / 'events.jsonl').exists()]
        Path(sys.argv[2]).write_text(json.dumps({'runs': rows}, indent=1) + '\n')
        for row in rows:
            print(json.dumps({k: v for k, v in row.items() if k not in ('lessons', 'game_over_lessons', 'thing_notes', 'things_by_level')}))
    else:
        raise SystemExit(__doc__)
