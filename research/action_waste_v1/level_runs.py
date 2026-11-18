"""Play vc33, s5i5 and su15 on their local game files with and without the no-effect lesson layer.

Each run starts where most of that game's actions that changed nothing were, in the saved 6 November run:

    vc33   the start of the game (8 of its 14 were the first 8 actions)
    s5i5   the start of level 3, after 41 saved actions (all 20 were on level 3, which it did not solve)
    su15   the start of level 3, after 30 saved actions (16 of 21 were on level 3, which it did not solve)

A run that starts at a later level first repeats the saved actions with no model call (every observation
must hash to the saved one), so the agent begins with the saved board and notes. It then plays 100 new
actions with its own choices. No ARC service, no scorecard.

    control   the 6 November harness, unchanged
    lessons   plus no_effect_lessons (the agent decides when to explain, after 1 to 4 further actions)
              and lesson_check

    level_runs.py check                          no model call: the local games against the saved run, the
                                                 control from each start against the saved play, and the
                                                 first request of the lessons arm
    level_runs.py batch <stamp> --send           all twelve runs, one at a time
    level_runs.py summary <out.json> <stamp>     per-run numbers from the runs of a batch

Usage (project environment), from the repository root.
"""
import json
import re
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'research'))
from agent.e1_policy import CompletionResult  # noqa: E402
from research.claude_arc_v1 import audit, config as C, policy, run  # noqa: E402
from research.claude_arc_v1.backends import Budget, ClaudeCodeBackend  # noqa: E402
from research.action_waste_v1.local_game import LocalGame, check_against_saved_run  # noqa: E402

CONTROL = ROOT / 'config/claude_arc_v1.opus55_competition.json'
SAVED = '.cache/claude_arc_runs/opus55-competition-20261106T054112Z/events.jsonl'
RUNS = ROOT / '.cache/claude_arc_runs'
GAMES = {'vc33-5430563c': 0, 's5i5-18d95033': 41, 'su15-1944f8ab': 30}     # saved actions repeated before play
NEW_ACTIONS = 100
ARMS = {'control': {}, 'lessons': {'no_effect_lessons': True, 'no_effect_wait': 4, 'lesson_check': True},
        # every memory layer together: lessons after a game over as well (used by ls20_level3.py)
        'memory': {'no_effect_lessons': True, 'no_effect_wait': 4, 'lesson_check': True, 'game_over_lessons': True},
        # the memory layers plus the object ledger (used by object_ledger_v1/held_out_runs.py)
        'ledger': {'no_effect_lessons': True, 'no_effect_wait': 4, 'lesson_check': True, 'game_over_lessons': True,
                   'object_ledger': True}}
REPEATS = 2
TEST_WORDS = re.compile(r'\btest(s|ed|ing)?\b|will show|shows? (whether|which)|see whether|to see if', re.I)


def settings(game, arm):
    start = GAMES[game]
    resume = {'resume_events': SAVED, 'resume_actions': start} if start else {}
    return C.Config(**{**json.loads(CONTROL.read_text()), 'mode': 'online', 'games': [game.split('-')[0]], **resume,
                       'max_actions_per_game': start + NEW_ACTIONS,
                       # one call per new action, with room for replies the controller sends back
                       'max_model_calls': NEW_ACTIONS + 80, **ARMS[arm]})


def name_of(game, arm, n, stamp):
    return 'waste-%s-%s-%d-%s' % (game.split('-')[0], arm, n, stamp)


class SavedReplies:
    """Stands in for the model: answers with what the model said on 6 November, from the start on."""

    def __init__(self, config, game, start, stop_after=None):
        self.config, self.budget, self.last_record, self.requests = config, Budget(config), None, []
        self.replies, self.stop_after, pending = [], stop_after, None
        with (ROOT / SAVED).open() as handle:
            for line in handle:
                if game not in line or '"kind":"model_' not in line:
                    continue
                event = json.loads(line)
                if event.get('game_id') != game:
                    continue
                if event['kind'] == 'model_entered':
                    pending = event['action_index']
                elif event['kind'] == 'model_returned' and pending >= start:
                    self.replies.append(event['content'])

    def complete(self, request):
        reserved = self.budget.reserve()
        self.requests.append(request)
        if not self.replies or (self.stop_after is not None and len(self.requests) > self.stop_after):
            raise KeyboardInterrupt()      # the saved run ends here, or the check has seen enough
        self.budget.settle(reserved, 10, 10)
        self.last_record = {'outcome': 'saved_reply'}
        return CompletionResult(self.replies.pop(0), 10, 10, 0)


def play(game, arm, name, backend=None, config=None):
    config = config or settings(game, arm)
    backend = backend or ClaudeCodeBackend(config, Budget(config))
    began = time.time()
    result = run.evaluate(config, backend, LocalGame(game), run.Evidence(RUNS / name))
    row = result['games'][0] if result['games'] else {}
    out = {'run': name, 'game': game, 'arm': arm, 'minutes': round((time.time() - began) / 60, 1),
           'problems': result['problems'], **{k: row.get(k) for k in (
               'actions_acknowledged', 'levels_completed', 'stop_reason', 'level_resets', 'final_state')}}
    print(json.dumps(out), flush=True)
    return out


def check():
    """Everything that can be checked without a model call."""
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    for game, start in GAMES.items():
        differs, total = check_against_saved_run(game)
        print(game, '| local game against the saved run:', total, 'actions, observations that differ:', differs or 'none')
        # the control from this start, fed the saved replies, must replay the saved actions that followed
        backend = SavedReplies(settings(game, 'control'), game, start)
        played = play(game, 'control', 'waste-check-%s-control-%s' % (game.split('-')[0], stamp), backend)
        events = [json.loads(line) for line in (RUNS / played['run'] / 'events.jsonl').read_text().splitlines()]
        mine = [e['action'] for e in events if e['kind'] == 'transition']
        saved = []
        with (ROOT / SAVED).open() as handle:
            for line in handle:
                if game in line and '"kind":"transition"' in line:
                    saved.append(json.loads(line)['action'])
        print('   control from action %d with the saved replies: %d actions, equal to the saved run: %s'
              % (start, len(mine), mine == saved[:len(mine)]))
        # the lessons arm: its first request must differ from the control's only where the layer says so
        first = SavedReplies(settings(game, 'lessons'), game, start, stop_after=0)
        play(game, 'lessons', 'waste-check-%s-lessons-%s' % (game.split('-')[0], stamp), first)
        mine, theirs = first.requests[0], backend.requests[0]
        body = json.loads(mine['messages'][1]['content'])
        print('   lessons arm, first request: system prompt equal to control %s, user message equal to control %s, '
              'case open %s, lessons shown %s' % (
                  mine['messages'][0]['content'] == theirs['messages'][0]['content'],
                  mine['messages'][1]['content'] == theirs['messages'][1]['content'],
                  'no_effect_case' in body['evidence'], 'no_effect_lessons' in body['evidence']))


def batch(stamp):
    """All runs, one at a time, arms alternating. Stops at the first run that ends with a problem."""
    for n in range(1, REPEATS + 1):
        for game in GAMES:
            for arm in ('control', 'lessons'):
                out = play(game, arm, name_of(game, arm, n, stamp))
                if out['problems']:
                    print('batch stopped: the last run ended with a problem', flush=True)
                    return


def summary(folder):
    """What happened in the new actions of one finished run, read from its event log."""
    from recovery_v1 import measures, traces
    from action_waste_v1.measure import loop_erased
    folder = Path(folder)
    events = [json.loads(line) for line in (folder / 'events.jsonl').read_text().splitlines()]
    config = next(e['config'] for e in events if e['kind'] == 'configuration')
    game = next(e['game_id'] for e in events if e['kind'] == 'initial_observation')
    start = config.get('resume_actions') or 0
    trace = next(iter(traces.load_events(folder / 'events.jsonl', source=folder.name).values()))
    keys = measures.keys(trace, measures.counter_mask(trace))
    steps = trace['steps']
    new = range(start, len(steps))
    chosen = [i for i in new if steps[i]['a'] != 'RESET']
    nothing = [i for i in chosen if steps[i]['state'] == 'NOT_FINISHED' and keys[i + 1] == keys[i]]
    seen, repeats = {}, 0
    for i in range(len(steps)):               # the same action from the same board had already changed nothing
        if steps[i]['a'] == 'RESET':
            continue
        pair = (keys[i], steps[i]['a'], steps[i]['x'], steps[i]['y'])
        flat = steps[i]['state'] == 'NOT_FINISHED' and keys[i + 1] == keys[i]
        repeats += i >= start and flat and seen.get(pair) is True
        seen.setdefault(pair, flat)
    level_at_start = steps[start - 1]['lc'] if start else 0
    per_level, count, level = [], 0, level_at_start
    for i in new:
        count += 1
        if steps[i]['lc'] > level:
            per_level.append(count)
            count, level = 0, steps[i]['lc']
    loops = sum(a['n'] - loop_erased([keys[a['first']]] + [keys[i + 1] for i in range(a['first'], a['last'] + 1)])
                for a in measures.attempts(trace) if a['first'] >= start and a['n'])
    replies, requests, index = {}, {}, None
    usage = []
    for event in events:
        if event['kind'] == 'model_entered':
            index = event['action_index']
            requests[index] = event['request']
        elif event['kind'] == 'model_returned':
            replies[index] = json.loads(event['content'])
            usage.append(int(event['metadata']['usage']['output_tokens']))
    combined, lessons, offered_unasked, cases, after_game_over = [], [], 0, set(), []
    for i, reply in sorted(replies.items()):
        body = json.loads(requests[i]['messages'][1]['content'])
        if reply.get('game_over_lesson') and 'game_over_lesson' in body['output_contract']:
            after_game_over.append({'at_action': i + 1, **reply['game_over_lesson']})
        case = body['evidence'].get('no_effect_case') or {}
        if case:
            cases.add(case['transition_id'])
        if not reply.get('no_effect_lesson'):
            continue
        if 'no_effect_lesson' not in body['output_contract']:
            offered_unasked += 1          # written when no explanation could be given yet: the controller drops it
            continue
        combined.append(len(case['actions_since']))
        lessons.append({'at_action': i + 1, 'explains': case['transition_id'],
                        'also_covers': case['of_those_also_changed_nothing'],
                        'further_actions_combined': combined[-1], **reply['no_effect_lesson']})
    tests = sum(bool(TEST_WORDS.search(' '.join(h[1] for h in (steps[i]['notes'] or ()) if h[2] == 'tentative')))
                for i in chosen)
    try:
        audit.audit(folder)
        audited = 'passes'
    except Exception as exc:
        audited = 'fails: %s' % exc
    final = next((e['summary'] for e in events if e['kind'] == 'summary'), None)
    return {'run': folder.name, 'game': game.split('-')[0],
            'set_up': ('memory layers and object ledger' if config.get('object_ledger')
                       else 'every memory layer' if config.get('no_effect_lessons') and config.get('game_over_lessons')
                       else 'no-effect lessons and check' if config.get('no_effect_lessons') else 'unchanged'),
            'started_after_action': start, 'level_at_start': level_at_start + 1,
            'new_actions': len(new), 'levels_completed_in_new_actions': level - level_at_start,
            'actions_per_completed_level': per_level, 'actions_on_the_open_level': count,
            'changed_nothing': len(nothing), 'changed_nothing_at': [i + 1 for i in nothing],
            'repeats_of_a_known_no_effect_action': int(repeats), 'in_a_loop': int(loops),
            'game_overs': sum(steps[i]['state'] == 'GAME_OVER' for i in new),
            'turns': len(chosen), 'turns_announcing_a_test': tests,
            'cases_opened': len(cases), 'lessons_kept': len(lessons), 'further_actions_combined': combined,
            'lessons_offered_too_early_and_dropped': offered_unasked, 'lessons': lessons,
            'game_over_lessons': after_game_over,
            'checks_written': sum(bool(r.get('lesson_check')) for r in replies.values()),
            'model_calls': len(usage), 'replies_sent_back': sum(e['kind'] == 'model_failed_retrying' for e in events),
            'output_tokens': sum(usage), 'output_per_call_median': round(statistics.median(usage)) if usage else None,
            'stop_reason': final['games'][0]['stop_reason'] if final and final['games'] else None,
            'problems': final['problems'] if final else ['no summary event'], 'audit': audited}


if __name__ == '__main__':
    command = sys.argv[1]
    if command == 'check':
        check()
    elif command == 'batch' and len(sys.argv) == 4 and sys.argv[3] == '--send':
        batch(sys.argv[2])
    elif command == 'summary':
        rows = [summary(RUNS / name_of(game, arm, n, sys.argv[3]))
                for game in GAMES for arm in ('control', 'lessons') for n in range(1, REPEATS + 1)
                if (RUNS / name_of(game, arm, n, sys.argv[3]) / 'events.jsonl').exists()]
        Path(sys.argv[2]).write_text(json.dumps({'runs': rows}, indent=1) + '\n')
        for row in rows:
            print(json.dumps({k: v for k, v in row.items() if k not in ('lessons', 'game_over_lessons')}))
    else:
        raise SystemExit(__doc__)
