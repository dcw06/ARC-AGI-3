"""Does telling the agent how it is scored change what it does at the turns where it wasted an action?

In the saved 6 November run, 188 of 2,467 actions changed nothing on the board. The agent's prompt never
said that actions cost anything. This test goes back to saved turns from every game that had such an
action and asks again, once with the request exactly as sent and once with the scoring rule added to the
system prompt (switch state_objective). Nothing else differs, and no game is touched.

Positions, drawn with a fixed seed before anything is sent:
    wasted   up to 3 turns per game where the saved action changed nothing
    useful   the same number per game where the saved action changed the board (and did not end the level
             or the game): a guard against the rule changing play everywhere

    prepare <out_dir>                 build and freeze the requests (no network, no model)
    send <out_dir> --send | --dry-run one model call per request on the Claude subscription, or a canned reply
    score <out_dir>                   apply the rule that send wrote to plan.json before its first call

Usage (project environment): probe_test.py prepare|send|score <out_dir>
"""
import copy
import hashlib
import json
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'research'))
from research.claude_arc_v1 import config as C, policy  # noqa: E402
from research.recovery_v1 import measures, traces  # noqa: E402
from research.action_waste_v1.measure import region  # noqa: E402

CONTROL = ROOT / 'config/claude_arc_v1.opus55_competition.json'
SAVED = ROOT / '.cache/claude_arc_runs/opus55-competition-20261106T054112Z/events.jsonl'
SEED, PER_GAME = 20261115, 3
ARMS = {'control': {}, 'objective': {'state_objective': True}}
TEST_WORDS = re.compile(r'\btest(s|ed|ing)?\b|will show|shows? (whether|which)|see whether|to see if', re.I)
RULE = {
    'outcome': 'at wasted positions, the share of valid replies that choose the saved no-effect action again '
               '(the same action; for a click, any cell of the same connected single-colour region), by arm',
    'changes_the_decision_if': 'the share with the scoring rule is at least 0.20 below the share without it',
    'no_headroom_if': 'the share without it is below 0.30',
    'guard': 'at useful positions, the share choosing the saved action again; a drop of more than 0.20 with the '
             'rule means it changes play in general, not only wasted actions',
    'unresolved_if': 'more than 10 replies are invalid',
    'valid_reply': 'JSON with a legal action for that board',
    'secondary': 'share of replies whose tentative notes announce a test; per-game counts',
    'cannot_show': 'fewer actions overall or more levels completed: a reply that avoids the known no-effect '
                   'action may pick another action whose effect is not known here',
    'min_difference': 0.20, 'min_control': 0.30, 'max_guard_drop': 0.20, 'max_invalid': 10}


def saved_requests():
    """{game: {turn: request as first sent}} from the saved run."""
    out = {}
    with SAVED.open() as handle:
        for line in handle:
            if '"kind":"model_entered"' in line:
                event = json.loads(line)
                if not event.get('attempt'):
                    out.setdefault(event['game_id'], {})[event['action_index']] = event['request']
    return out


def positions():
    """The drawn turns: [{'id', 'game', 'turn', 'kind', 'saved_action', 'target'}], fixed by SEED."""
    rng, rows = random.Random(SEED), []
    for game, trace in sorted(traces.load_events().items()):
        keys = measures.keys(trace, measures.counter_mask(trace))
        before, state, wasted, useful = trace['initial'], 'NOT_FINISHED', [], []
        for i, step in enumerate(trace['steps']):
            if step['a'] != 'RESET' and state != 'GAME_OVER':
                action = {'action_id': int(step['a'][6:]),
                          'action_data': {'x': step['x'], 'y': step['y']} if step['a'] == 'ACTION6' else {}}
                target = None
                if step['a'] == 'ACTION6' and before.ndim == 2:
                    colour, first = region(before, step['x'], step['y'])
                    target = {'colour': colour, 'first_cell': list(first)}
                row = {'game': game, 'turn': i, 'saved_action': action, 'target': target}
                ordinary = step['state'] == 'NOT_FINISHED' and step['lc'] == (trace['steps'][i - 1]['lc'] if i else 0)
                if ordinary and keys[i + 1] == keys[i]:
                    wasted.append(row)
                elif ordinary:
                    useful.append(row)
            before, state = step['frame'], step['state']
        take = min(PER_GAME, len(wasted), len(useful))
        for kind, pool in (('wasted', wasted), ('useful', useful)):
            for row in sorted(rng.sample(pool, take), key=lambda r: r['turn']):
                rows.append({'id': '%s-t%d-%s' % (game.split('-')[0], row['turn'] + 1, kind), 'kind': kind, **row})
    return rows


def prepare(out_dir):
    base = json.loads(CONTROL.read_text())
    sent, requests = saved_requests(), []
    for row in positions():
        saved = sent[row['game']][row['turn']]
        settings = {**base, 'mode': 'online', 'games': [row['game'].split('-')[0]]}
        if saved['messages'][0]['content'] != policy.system_prompt(C.Config(**settings)):
            raise SystemExit('saved system prompt is not the control prompt: ' + row['id'])
        for arm, switches in ARMS.items():
            request = copy.deepcopy(saved)
            c = C.Config(**{**settings, **switches})
            request['messages'][0]['content'] = policy.system_prompt(c)
            body = json.dumps(request, sort_keys=True, separators=(',', ':')).encode()
            requests.append({'id': row['id'] + '-' + arm, 'position': row['id'], 'arm': arm, 'kind': row['kind'],
                             'game': row['game'], 'turn': row['turn'], 'saved_action': row['saved_action'],
                             'target': row['target'], 'config': c.public(), 'request': request,
                             'sha256': hashlib.sha256(body).hexdigest()})
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'requests.json').write_text(json.dumps(requests, separators=(',', ':')) + '\n')
    manifest = [{k: r[k] for k in ('id', 'kind', 'arm', 'game', 'turn', 'saved_action', 'target', 'sha256')}
                for r in requests]
    (out_dir / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
    return requests


def board_of(request):
    """The current board in a request, as rows of colour numbers, and its legal actions."""
    current = json.loads(request['messages'][1]['content'])['evidence']['current']
    rows = [[int(ch, 16) for ch in line.split('|', 1)[1].replace(' ', '')] for line in current['final_frame']]
    return rows, current['available_actions']


def problem(value, legal):
    try:
        action = value['action']
        if action['action_id'] not in legal or action['action_id'] == 0:
            return 'action is not legal here'
        if action['action_id'] == 6:
            x, y = action['action_data']['x'], action['action_data']['y']
            if type(x) is not int or type(y) is not int or not (0 <= x < 64 and 0 <= y < 64):
                return 'click outside the board'
        if not isinstance(value['hypotheses'], list):
            return 'no hypothesis list'
    except Exception as exc:
        return 'bad shape: ' + type(exc).__name__
    return None


def send(out_dir, dry_run):
    from research.claude_arc_v1.backends import Budget, BudgetExceeded, ClaudeCodeBackend
    raw = (out_dir / 'requests.json').read_bytes()
    requests = json.loads(raw)
    target = out_dir / ('replies_dry_run.jsonl' if dry_run else 'replies.jsonl')
    if target.exists():
        raise SystemExit('replies already exist: ' + str(target))
    if not dry_run:
        (out_dir / 'plan.json').write_text(json.dumps({     # on disk before the first call
            'written_before_sending': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'requests_sha256': hashlib.sha256(raw).hexdigest(), 'model_calls': len(requests), 'retries': 0,
            'seed': SEED, 'positions_per_game_and_kind': PER_GAME, 'rule': RULE}, indent=1) + '\n')
    failures = 0
    with target.open('x') as handle:
        for item in requests:
            c = C.Config(**{**item['config'], 'live_enabled': True, 'max_model_calls': 1})
            record = {'id': item['id'], 'request_sha256': item['sha256']}
            began = time.time()
            try:
                if dry_run:
                    content = json.dumps({'action': item['saved_action'], 'hypotheses': []})
                else:
                    backend = ClaudeCodeBackend(c, Budget(c))
                    try:
                        content = backend.complete(item['request']).content
                    finally:
                        record['backend'] = backend.last_record
                value = C.strict_json(content)
                record.update(content=content, action=value.get('action'),
                              problem=problem(value, board_of(item['request'])[1]))
                failures = 0
            except Exception as exc:
                record.update(error=type(exc).__name__, detail=str(exc)[:300])
                failures += 1
                if isinstance(exc, (BudgetExceeded, PermissionError)) or failures >= 3:
                    handle.write(json.dumps(record) + '\n')
                    raise SystemExit('stopped: ' + record['error'])     # a fault in the path, not in one reply
            record['seconds'] = round(time.time() - began, 1)
            handle.write(json.dumps(record) + '\n')
            handle.flush()
            print(record['id'], json.dumps(record.get('action')), record.get('problem') or record.get('error') or '',
                  record['seconds'], flush=True)
    return target


def same_choice(item, action):
    saved = item['saved_action']
    if action['action_id'] != saved['action_id']:
        return False
    if saved['action_id'] != 6:
        return True
    import numpy as np
    rows, _ = board_of(item['request'])
    colour, first = region(np.asarray(rows), action['action_data']['x'], action['action_data']['y'])
    return item['target'] is not None and [colour, list(first)] == [item['target']['colour'], item['target']['first_cell']]


def score(out_dir, name='replies.jsonl'):
    requests = {r['id']: r for r in json.loads((out_dir / 'requests.json').read_text())}
    cells, invalid, games = {}, 0, {}
    for line in (out_dir / name).read_text().splitlines():
        reply = json.loads(line)
        item = requests[reply['id']]
        if reply.get('error') or reply.get('problem'):
            invalid += 1
            continue
        value = json.loads(reply['content'])
        again = same_choice(item, value['action'])
        notes = ' '.join(h.get('statement', '') for h in value['hypotheses'] if h.get('status') == 'tentative')
        cell = cells.setdefault((item['kind'], item['arm']), {'valid': 0, 'saved_action_again': 0, 'announces_a_test': 0})
        cell['valid'] += 1
        cell['saved_action_again'] += again
        cell['announces_a_test'] += bool(TEST_WORDS.search(notes))
        if item['kind'] == 'wasted':
            game = games.setdefault(item['game'].split('-')[0], {'control': [0, 0], 'objective': [0, 0]})
            game[item['arm']][0] += again
            game[item['arm']][1] += 1
    share = lambda kind, arm: (cells[(kind, arm)]['saved_action_again'] / cells[(kind, arm)]['valid']
                               if cells.get((kind, arm), {}).get('valid') else None)
    wc, wo, uc, uo = share('wasted', 'control'), share('wasted', 'objective'), share('useful', 'control'), share('useful', 'objective')
    if invalid > RULE['max_invalid'] or None in (wc, wo, uc, uo):
        verdict = 'unresolved'
    elif wc < RULE['min_control']:
        verdict = 'no headroom: without the rule the model seldom repeats the saved no-effect action'
    elif wc - wo >= RULE['min_difference']:
        verdict = ('changes the decision at wasted turns' if uc - uo <= RULE['max_guard_drop']
                   else 'changes play in general, not only at wasted turns')
    else:
        verdict = 'does not change the decision at wasted turns'
    result = {'verdict': verdict, 'invalid': invalid,
              'cells': {'%s/%s' % key: value for key, value in sorted(cells.items())},
              'wasted_saved_action_again_by_game': games, 'rule': RULE}
    (out_dir / ('scores_dry_run.json' if 'dry' in name else 'scores.json')).write_text(json.dumps(result, indent=1) + '\n')
    return result


if __name__ == '__main__':
    command, folder = sys.argv[1], Path(sys.argv[2])
    if command == 'prepare':
        built = prepare(folder)
        by = {}
        for r in built:
            by[(r['kind'], r['arm'])] = by.get((r['kind'], r['arm']), 0) + 1
        print('requests', len(built), by, 'games', len({r['game'] for r in built}))
    elif command == 'send' and sys.argv[3] in ('--send', '--dry-run'):
        send(folder, sys.argv[3] == '--dry-run')
    elif command == 'score':
        print(json.dumps(score(folder, sys.argv[3] if len(sys.argv) > 3 else 'replies.jsonl'), indent=1))
    else:
        raise SystemExit(__doc__)
