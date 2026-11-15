"""Does remembering a game over stop the agent from dying the same way again? bp35, level 2, saved positions.

In the saved 6 November run the agent died three times on bp35 level 2, each time by rising into a spike.
After each death it wrote a rule about it, and about twenty actions later the rule had faded from its
notes: the fatal action had left the 8-action history. This test goes back to the two turns where it then
died again and asks, several times over, what it does there under five inputs:

    none          the request exactly as sent on 6 November
    irrelevant    plus ordinary earlier actions with their boards (a control for added length)
    evidence      plus the earlier game-over actions, each with the board before and after
                  (switch pin_game_overs)
    lesson        plus the lesson written after each earlier game over: a general rule and how to
                  recognise the danger elsewhere, kept by the controller (switch game_over_lessons)
    lesson_check  the same, and the reply must check its action against the lessons (switch lesson_check)

The lessons are not written by me. Stage 1 goes back to the turn after each earlier game over and asks
the model for the lesson, as the fixed harness would have; the first valid reply is the lesson used.

Each reply's action is then played on the local copy of the real game from the saved position, to see
whether it ends in GAME_OVER. No live game is touched and no action is sent anywhere.

    lessons <out_dir> --send | --dry-run        stage 1: ask for the lessons (2 turns x 3 replies)
    prepare <out_dir>                           build and freeze the stage 2 requests
    send <out_dir> --repeats N --send|--dry-run stage 2: positions x 5 inputs x N model calls
    score <out_dir>                             play each reply's action on the local game, apply the rule

Usage (project environment): death_test.py lessons|prepare|send|score <out_dir> [options]
"""
import argparse
import copy
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from arcengine import GameState

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'research'))
from agent.action import ActionDecision  # noqa: E402
from agent.state import Observation  # noqa: E402
from research.claude_arc_v1 import config as C, policy  # noqa: E402
from research.memory_fix_v1 import bp35_local  # noqa: E402

CONTROL = ROOT / 'config/claude_arc_v1.opus55_competition.json'
SAVED = ROOT / '.cache/claude_arc_runs/opus55-competition-20261106T054112Z/events.jsonl'
GAME = bp35_local.GAME_ID
# Turn = number of actions already taken. At these two turns the saved run chose a fatal action after it
# had already died on this level; the lists are the earlier fatal transitions at that point.
FATAL_TURNS = {47: [23], 77: [23, 48]}
# Earlier fatal transition -> the turn on which its lesson is written (the first model turn after the reset).
LESSON_TURNS = {23: 24, 48: 49}
LESSON_SAMPLES = 3
ARMS = {'none': {}, 'irrelevant': {}, 'evidence': {'pin_game_overs': 3},
        'lesson': {'game_over_lessons': True}, 'lesson_check': {'game_over_lessons': True, 'lesson_check': True}}
OTHER_NOTE = ('evidence.earlier_actions keeps some earlier actions on this level, each with the board before it '
              'and the board it produced.')
RULE = {'outcome': 'share of valid replies whose action ends in GAME_OVER when played on the local game, by input, '
                   'over both positions',
        'works_if': 'the share with an added memory is at least 0.30 below the share with none and at least 0.30 '
                    'below the share with irrelevant',
        'no_headroom_if': 'the share with none is below 0.30',
        'unresolved_if': 'more than 8 replies are invalid',
        'valid_reply': 'one the controller would accept (its own parse), so its action could have been sent',
        'min_difference': 0.30, 'min_none': 0.30, 'max_invalid': 8}


def base_config(**extra):
    return C.Config(**{**json.loads(CONTROL.read_text()), 'mode': 'online', 'games': ['bp35'], **extra})


def observation(value):
    return Observation(value['game_id'], tuple(np.asarray(f, dtype=np.uint8) for f in value['frames']),
                       GameState[value['state']], value['levels_completed'], value['win_levels'], 'saved-guid',
                       tuple(value['available_actions']), value['full_reset'])


def saved_traffic():
    """({turn: the model's accepted reply}, {turn: the request sent}) for bp35 in the saved run."""
    replies, sent, pending = {}, {}, None
    with SAVED.open() as handle:
        for line in handle:
            if GAME not in line:
                continue
            event = json.loads(line)
            if event.get('game_id') != GAME:
                continue
            if event['kind'] == 'model_entered':
                pending = event['action_index']
                if not event.get('attempt'):
                    sent[pending] = event['request']
            elif event['kind'] == 'model_returned':
                replies[pending] = json.loads(event['content'])
    return replies, sent


def policy_at(turn, config, first, steps, replies, lessons=()):
    """The policy as it stood after `turn` saved actions, and the board it faces. Lessons can be seeded."""
    agent = policy.Policy(config)
    before = observation(first)
    for index in range(turn):
        action, value = steps[index]
        after = observation(value)
        decision = ActionDecision(action['action_id'], dict(action['action_data']), source='controller_resume')
        answer = replies.get(index) or {'action': action, 'hypotheses': list(agent.hypotheses)}
        agent.observe(before, decision, after, answer)
        before = after
    agent.lessons = list(lessons)
    return agent, before


def record(steps, first, number):
    """Transition t<number> with the board before it and the board it produced."""
    before = first if number == 1 else steps[number - 2][1]
    action, after = steps[number - 1]
    rows = lambda value: policy.hex_rows(np.asarray(value['frames'][-1]))
    return {'transition_id': 't%d' % number, 'action': action, 'frames_returned': len(after['frames']),
            'before': {'observation_id': 'o%d' % (number - 1), 'final_frame': rows(before)},
            'after': {'observation_id': 'o%d' % number, 'state': after['state'], 'final_frame': rows(after)}}


def with_block(request, key, value, note):
    out = copy.deepcopy(request)
    payload = json.loads(out['messages'][1]['content'])
    payload['evidence'][key] = value
    payload['procedure'].append(note)
    out['messages'][1]['content'] = json.dumps(payload, separators=(',', ':'), allow_nan=False)
    return out


def call(config, request, dry_reply=None):
    """One model call through the subscription backend, or a canned reply. Returns (content, record)."""
    if dry_reply is not None:
        return json.dumps(dry_reply), {'outcome': 'canned'}
    from research.claude_arc_v1.backends import Budget, ClaudeCodeBackend
    live = C.Config(**{**config.public(), 'live_enabled': True, 'max_model_calls': 1})
    backend = ClaudeCodeBackend(live, Budget(live))
    return backend.complete(request).content, backend.last_record


def lessons_stage(out_dir, dry_run):
    """Stage 1: on the turn after each earlier game over, ask for the lesson as the fixed harness would."""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / ('lessons_dry_run.json' if dry_run else 'lessons.json')
    if target.exists():
        raise SystemExit('lessons already exist: ' + str(target))
    first, steps = bp35_local.saved_run()
    replies, _ = saved_traffic()
    config = base_config(game_over_lessons=True, lesson_check=True)
    chosen, log = [], []
    for fatal, turn in LESSON_TURNS.items():
        agent, board = policy_at(turn, config, first, steps, replies, chosen)
        request = agent.request(board)
        if agent.lesson_due() != 't%d' % fatal:
            raise SystemExit('no lesson is due at turn %d' % turn)
        picked = None
        for sample in range(LESSON_SAMPLES):
            canned = None
            if dry_run:
                canned = {'action': steps[turn][0], 'hypotheses': [],
                          'game_over_lesson': {'rule': 'canned rule %d' % fatal, 'applies_when': 'canned'}}
                if chosen:
                    canned['lesson_check'] = 'canned'
            row = {'after': 't%d' % fatal, 'turn': turn, 'sample': sample}
            try:
                content, row['backend'] = call(config, request, canned)
                _, value = agent.parse(content, board)          # the controller's own check
                row.update(content=content, lesson=value['game_over_lesson'])
                if picked is None:                              # fixed beforehand: the first valid reply is used
                    picked = {'after': 't%d' % fatal, 'level': board.levels_completed + 1, **value['game_over_lesson']}
            except Exception as exc:
                row.update(error=type(exc).__name__, detail=str(exc)[:300])
            log.append(row)
            print(row['after'], sample, json.dumps(row.get('lesson') or row.get('detail')), flush=True)
        if picked is None:
            raise SystemExit('no valid lesson at turn %d' % turn)
        chosen.append(picked)
    (out_dir / ('lessons_replies_dry_run.jsonl' if dry_run else 'lessons_replies.jsonl')).write_text(
        ''.join(json.dumps(row) + '\n' for row in log))
    target.write_text(json.dumps(chosen, indent=1) + '\n')
    return chosen


def prepare(out_dir, lessons_name='lessons.json'):
    lessons = json.loads((out_dir / lessons_name).read_text())
    first, steps = bp35_local.saved_run()
    _, _, mismatches = bp35_local.replay([a for a, _ in steps], [o for _, o in steps])
    if mismatches:
        raise SystemExit('the local game does not reproduce the saved run at steps %s' % mismatches)
    replies, sent = saved_traffic()
    requests = []
    for turn, deaths in FATAL_TURNS.items():
        earlier = [l for l in lessons if int(l['after'][1:]) in deaths]
        if len(earlier) != len(deaths):
            raise SystemExit('a lesson is missing for turn %d' % turn)
        built = {}
        for arm, switches in ARMS.items():
            config = base_config(**switches)
            agent, board = policy_at(turn, config, first, steps, replies,
                                     earlier if switches.get('game_over_lessons') else ())
            built[arm] = agent.request(board)
        if built['none'] != sent[turn]:
            raise SystemExit('the rebuilt request at turn %d is not the one sent on 6 November' % turn)
        pinned = json.loads(built['evidence']['messages'][1]['content'])['evidence']['game_overs']
        if pinned != [record(steps, first, d) for d in deaths]:
            raise SystemExit('the pinned records at turn %d are not the saved boards of %s' % (turn, deaths))
        # An ordinary action three before each fatal one: same attempt, not a reset, not a game over.
        others = [record(steps, first, d - 3) for d in deaths]
        if any(r['after']['state'] != 'NOT_FINISHED' or r['action']['action_id'] == 0 for r in others):
            raise SystemExit('the irrelevant records are not ordinary actions')
        built['irrelevant'] = with_block(built['none'], 'earlier_actions', others, OTHER_NOTE)
        for arm in ARMS:
            raw = json.dumps(built[arm], sort_keys=True).encode()
            requests.append({'id': 'turn%d-%s' % (turn, arm), 'turn': turn, 'arm': arm, 'switches': ARMS[arm],
                             'earlier_game_overs': ['t%d' % d for d in deaths],
                             'action_the_saved_run_chose': steps[turn][0],
                             'characters': sum(len(m['content']) for m in built[arm]['messages']),
                             'sha256': hashlib.sha256(raw).hexdigest(), 'request': built[arm]})
    (out_dir / 'requests.json').write_text(json.dumps(requests, indent=1) + '\n')
    manifest = [{k: v for k, v in r.items() if k != 'request'} for r in requests]
    (out_dir / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
    return manifest


def send(out_dir, repeats, dry_run):
    from research.claude_arc_v1.backends import BudgetExceeded
    raw = (out_dir / 'requests.json').read_bytes()
    requests = json.loads(raw)
    target = out_dir / ('replies_dry_run.jsonl' if dry_run else 'replies.jsonl')
    if target.exists():
        raise SystemExit('replies already exist: ' + str(target))
    lessons = json.loads((out_dir / 'lessons.json').read_text())
    first, steps = bp35_local.saved_run()
    replies, _ = saved_traffic()
    judges = {}
    for item in requests:        # the controller's own parse decides whether a reply could have been acted on
        earlier = [l for l in lessons if l['after'] in item['earlier_game_overs']]
        config = base_config(**item['switches'])
        judges[item['id']] = (config,) + policy_at(item['turn'], config, first, steps, replies,
                                                   earlier if item['switches'].get('game_over_lessons') else ())
    if not dry_run:
        (out_dir / 'plan.json').write_text(json.dumps({
            'written_before_sending': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'requests_sha256': hashlib.sha256(raw).hexdigest(), 'requests': len(requests), 'repeats': repeats,
            'model_calls': len(requests) * repeats, 'retries': 0, 'rule': RULE}, indent=1) + '\n')
    stopped, failures = False, 0
    with target.open('x') as handle:
        for n in range(repeats):                       # inputs are interleaved, so drift over time hits all alike
            for item in requests:
                if stopped:
                    break
                config, agent, board = judges[item['id']]
                row = {'id': item['id'], 'repeat': n, 'request_sha256': item['sha256']}
                began = time.time()
                try:
                    canned = None
                    if dry_run:
                        canned = {'action': item['action_the_saved_run_chose'], 'hypotheses': []}
                        if item['switches'].get('lesson_check'):
                            canned['lesson_check'] = 'canned'
                    content, row['backend'] = call(config, item['request'], canned)
                    row['content'] = content
                    failures = 0
                    try:
                        decision, value = agent.parse(content, board)
                        row['action'] = value['action']
                        row['lesson_check'] = value.get('lesson_check')
                    except ValueError as exc:
                        row['problem'] = str(exc)[:300]
                except Exception as exc:
                    row.update(error=type(exc).__name__, detail=str(exc)[:300])
                    failures += 1
                    stopped = isinstance(exc, (BudgetExceeded, PermissionError)) or failures >= 3
                row['seconds'] = round(time.time() - began, 1)
                handle.write(json.dumps(row) + '\n')
                handle.flush()
                print(row['id'], n, json.dumps(row.get('action')), row.get('problem') or row.get('error') or '',
                      row['seconds'], flush=True)
    return target


def score(out_dir, name='replies.jsonl'):
    rows = [json.loads(line) for line in (out_dir / name).read_text().splitlines()]
    first, steps = bp35_local.saved_run()
    saved_actions = [a for a, _ in steps]
    played = {}

    def outcome(turn, action):
        key = (turn, json.dumps(action, sort_keys=True))
        if key not in played:
            _, result, _ = bp35_local.replay(saved_actions[:turn] + [action])
            played[key] = result.state.name
        return played[key]
    table, invalid = {}, 0
    for row in rows:
        turn, arm = row['id'].split('-', 1)
        cell = table.setdefault(row['id'], {'turn': int(turn[4:]), 'arm': arm, 'valid': 0, 'game_over': 0,
                                            'invalid': 0, 'actions': {}})
        if 'action' not in row:
            cell['invalid'] += 1
            invalid += 1
            continue
        state = outcome(cell['turn'], row['action'])
        row['state_on_local_game'] = state
        cell['valid'] += 1
        cell['game_over'] += state == 'GAME_OVER'
        label = json.dumps(row['action'], sort_keys=True) + ' -> ' + state
        cell['actions'][label] = cell['actions'].get(label, 0) + 1
    arms = {}
    for arm in ARMS:
        cells = [c for c in table.values() if c['arm'] == arm]
        valid, dead = sum(c['valid'] for c in cells), sum(c['game_over'] for c in cells)
        arms[arm] = {'valid': valid, 'game_over': dead, 'share': round(dead / valid, 3) if valid else None}
    none, other = arms['none']['share'], arms['irrelevant']['share']
    reading = {}
    for arm in ('evidence', 'lesson', 'lesson_check'):
        share = arms[arm]['share']
        if invalid > RULE['max_invalid'] or None in (none, other, share):
            reading[arm] = 'unresolved'
        elif none < RULE['min_none']:
            reading[arm] = 'no headroom'
        elif none - share >= RULE['min_difference'] and other - share >= RULE['min_difference']:
            reading[arm] = 'works at these positions'
        else:
            reading[arm] = 'no clear effect at these positions'
    result = {'replies': len(rows), 'invalid': invalid, 'by_input': arms, 'reading': reading, 'by_request': table}
    (out_dir / 'scores.json').write_text(json.dumps(result, indent=1) + '\n')
    (out_dir / (name.replace('.jsonl', '') + '_scored.jsonl')).write_text(
        ''.join(json.dumps({k: v for k, v in row.items() if k != 'backend'}) + '\n' for row in rows))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=('lessons', 'prepare', 'send', 'score'))
    parser.add_argument('out_dir', type=Path)
    parser.add_argument('--repeats', type=int, default=8)
    parser.add_argument('--send', action='store_true', help='really call the model')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--lessons-file', default='lessons.json')
    args = parser.parse_args(argv)
    if args.command == 'prepare':
        for row in prepare(args.out_dir, args.lessons_file):
            print(row['id'], 'earlier game overs', row['earlier_game_overs'], 'characters', row['characters'], row['sha256'][:12])
        return 0
    if args.command == 'score':
        result = score(args.out_dir)
        print(json.dumps({k: result[k] for k in ('replies', 'invalid', 'by_input', 'reading')}, indent=1))
        return 0
    if args.send == args.dry_run:
        raise SystemExit('choose exactly one of --send (calls the model) and --dry-run')
    if args.command == 'lessons':
        print(json.dumps(lessons_stage(args.out_dir, args.dry_run), indent=1))
    else:
        print('wrote', send(args.out_dir, args.repeats, args.dry_run))
    return 0


if __name__ == '__main__':
    sys.exit(main())
