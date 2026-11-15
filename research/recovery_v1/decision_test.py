"""One-decision test: asked at a saved position, does the model choose to reset, and at the right positions?

The positions are the turns of the saved November 6 run at which the level-action signal (1.0x the human
baseline) first fires on a level. On half of them the level was later completed by the same run, so a
reset there would have thrown away an attempt that worked; on the other half it never was.

Each position gives two requests, built offline exactly as the controller would build them after
repeating the saved actions:
    not_asked   reset allowed, no recovery check
    asked       reset allowed, recovery check due
Sending a request several times shows how often the model resets. No game is touched: the reply is
parsed and recorded, and no action is sent anywhere.

    prepare <out_dir>                     build and freeze the requests (no network, no model)
    send <out_dir> --repeats N --send     send them through the Claude subscription. NOT run without --send;
                                          it makes positions x 2 x N model calls.
    send <out_dir> --repeats N --dry-run  exercise the same path with a canned reply instead of a model

Usage (project environment): decision_test.py prepare|send <out_dir> [options]
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'research'))
from research.claude_arc_v1 import config as C, policy  # noqa: E402
from research.recovery_v1 import measures as M, simulate_checks, traces  # noqa: E402
from research.recovery_v1.preview_pilot import first_request, load_saved  # noqa: E402

CONTROL = ROOT / 'config/claude_arc_v1.opus55_competition.json'
BASELINES = ROOT / 'reports/arc_agi3_loss_audit/data/headroom.json'
SAVED = '.cache/claude_arc_runs/opus55-competition-20261106T054112Z/events.jsonl'
RATIO = 1.0
ARMS = {'not_asked': {'model_may_reset': True},
        'asked': {'model_may_reset': True, 'stall_level_ratio': RATIO}}

# Scoring, fixed before any reply exists (send writes it to plan.json first).
# continue_is_right: the saved run completed the level within 1 to 7 more actions, or (bp35) the simulator
# shows the position on a shortest path, 24 actions from a win. unverified: the level was never completed
# and nothing tells us whether the position could still be won.
GROUPS = {'continue_is_right': ['lp85-L4', 'ka59-L1', 'sc25-L3', 'tr87-L1', 'vc33-L1', 'bp35-L2'],
          'unverified': ['su15-L3', 'cd82-L3', 'lf52-L2', 'tn36-L1']}
RULE = {'outcome': 'share of valid replies in the asked arm that choose reset (action 0), by group',
        'discriminates_if': 'reset share where continue is right is at most 0.20, and the unverified share '
                            'is at least 0.30 higher',
        'otherwise': 'the check does not discriminate at these positions',
        'unresolved_if': 'more than 10 of the 100 replies are invalid (error, or a reply the controller would reject)',
        'max_reset_where_continue_is_right': 0.20, 'min_difference': 0.30, 'max_invalid': 10,
        'secondary': 'the same shares in the not_asked arm; reasons given; per-position counts'}


def positions():
    """The first turn on each level at which the level signal fires in the saved run, and what followed."""
    data = json.loads(BASELINES.read_text())
    baselines = {g.split('-')[0]: v['baseline'] for g, v in data['meta'].items()}
    _, trigger = simulate_checks.trigger('level', stall_level_ratio=RATIO, level_baselines=baselines)
    rows = []
    for game, trace in traces.load_events().items():
        seen = set()
        done = trace['steps'][-1]['lc'] + (trace['steps'][-1]['state'] == 'WIN')
        for index, _, level in simulate_checks.simulate(trace, trigger):
            if level in seen:
                continue
            seen.add(level)
            finished = next((i for i, s in enumerate(trace['steps']) if s['lc'] > level), None)
            rows.append({'game': game, 'level': level + 1, 'actions_before': index,
                         'human_baseline': baselines[game.split('-')[0]][level],
                         'level_completed_later': level < done,
                         'actions_until_completed': None if finished is None else finished + 1 - index,
                         'resets_before_completion': sum(s['a'] == 'RESET' for s in trace['steps'][index:finished])
                         if finished is not None else None})
    return rows, baselines


def prepare(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    rows, baselines = positions()
    control = json.loads(CONTROL.read_text())
    saved = load_saved(ROOT / SAVED, {r['game'].split('-')[0] for r in rows})
    requests = []
    for row in rows:
        short = row['game'].split('-')[0]
        for arm, switches in ARMS.items():
            value = {**control, 'mode': 'online', 'games': [short], 'resume_events': SAVED,
                     'resume_actions': row['actions_before'], 'max_actions_per_game': row['actions_before'] + 1,
                     **switches}
            if switches.get('stall_level_ratio'):
                value['level_baselines'] = {short: baselines[short]}
            request = first_request(C.Config(**value), saved, row['game'])
            evidence = json.loads(request['messages'][1]['content'])['evidence']
            if ('recovery_check' in evidence) != (arm == 'asked'):
                raise ValueError('the check is not where it should be: %s %s' % (short, arm))
            raw = json.dumps(request, sort_keys=True).encode()
            requests.append({'id': '%s-L%d-%s' % (short, row['level'], arm), 'arm': arm, **row,
                             'config': value, 'sha256': hashlib.sha256(raw).hexdigest(), 'request': request})
    (out_dir / 'requests.json').write_text(json.dumps(requests, indent=1) + '\n')
    manifest = [{k: v for k, v in r.items() if k not in ('request', 'config')} for r in requests]
    (out_dir / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
    return manifest


def send(out_dir, repeats, dry_run):
    import time
    from research.claude_arc_v1.backends import Budget, BudgetExceeded, ClaudeCodeBackend
    raw = (out_dir / 'requests.json').read_bytes()
    requests = json.loads(raw)
    target = out_dir / ('replies_dry_run.jsonl' if dry_run else 'replies.jsonl')
    if target.exists():
        raise SystemExit('replies already exist: ' + str(target))
    if not dry_run:
        # The plan is on disk before the first call is made.
        (out_dir / 'plan.json').write_text(json.dumps({
            'written_before_sending': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'requests_sha256': hashlib.sha256(raw).hexdigest(), 'requests': len(requests), 'repeats': repeats,
            'model_calls': len(requests) * repeats, 'retries': 0, 'groups': GROUPS, 'rule': RULE}, indent=1) + '\n')
    stopped, failures = False, 0
    with target.open('x') as handle:
        for item in requests:
            if stopped:
                break
            c = C.Config(**{**item['config'], 'live_enabled': True, 'max_model_calls': repeats})
            backend = None if dry_run else ClaudeCodeBackend(c, Budget(c))
            check = 'recovery_check' in json.loads(item['request']['messages'][1]['content'])['evidence']
            context = {'check': check, 'offer': None, 'may_reset': True, 'baseline': item['human_baseline'],
                       'reset_pays_back': True}
            for n in range(repeats):
                record = {'id': item['id'], 'repeat': n, 'request_sha256': item['sha256']}
                began = time.time()
                try:
                    if dry_run:
                        reply = {'action': {'action_id': 0, 'action_data': {}}, 'hypotheses': []}
                        if check:
                            reply['recovery'] = {'choice': 'reset', 'reason': 'canned reply'}
                        content = json.dumps(reply)
                    else:
                        content = backend.complete(item['request']).content
                        record['backend'] = backend.last_record
                    value = C.strict_json(content)
                    record.update(content=content, action_id=value['action']['action_id'],
                                  reset=value['action']['action_id'] == 0, recovery=value.get('recovery'))
                    # The same checks the controller applies, without a game: shape, keys, agreement.
                    record['problem'] = shape_problem(c, value, context)
                except Exception as exc:
                    record.update(error=type(exc).__name__, detail=str(exc)[:300])
                    if not dry_run:
                        record['backend'] = backend.last_record
                    failures += 1
                    # A plan limit or login problem would fail every later call too, and three failures in a
                    # row point to a fault in the path itself: stop the whole test instead of spending calls.
                    stopped = isinstance(exc, (BudgetExceeded, PermissionError)) or failures >= 3
                else:
                    failures = 0
                record['seconds'] = round(time.time() - began, 1)
                handle.write(json.dumps(record) + '\n')
                handle.flush()
                print(record['id'], n, record.get('action_id'), (record.get('recovery') or {}).get('choice'),
                      record.get('problem') or record.get('error') or '', record['seconds'], flush=True)
                if stopped:
                    break
    return target


def score(out_dir, name='replies.jsonl'):
    """Apply the rule in plan.json to the replies. Writes scores.json."""
    rows = [json.loads(line) for line in (out_dir / name).read_text().splitlines()]
    group_of = {key: group for group, keys in GROUPS.items() for key in keys}
    table, invalid = {}, 0
    for row in rows:
        position, arm = row['id'].rsplit('-', 1)
        cell = table.setdefault(position, {'group': group_of[position]}).setdefault(arm, {'valid': 0, 'reset': 0, 'invalid': 0})
        if row.get('error') or row.get('problem'):
            cell['invalid'] += 1
            invalid += 1
        else:
            cell['valid'] += 1
            cell['reset'] += bool(row['reset'])
    shares = {}
    for arm in ARMS:
        for group in GROUPS:
            cells = [v[arm] for v in table.values() if v['group'] == group and arm in v]
            valid, reset = sum(c['valid'] for c in cells), sum(c['reset'] for c in cells)
            shares[arm + ':' + group] = {'valid': valid, 'reset': reset, 'share': round(reset / valid, 3) if valid else None}
    right, unknown = shares['asked:continue_is_right']['share'], shares['asked:unverified']['share']
    if invalid > RULE['max_invalid'] or right is None or unknown is None:
        reading = 'unresolved'
    elif right <= RULE['max_reset_where_continue_is_right'] and unknown - right >= RULE['min_difference']:
        reading = 'discriminates'
    else:
        reading = 'does not discriminate'
    result = {'replies': len(rows), 'invalid': invalid, 'shares': shares, 'reading': reading, 'by_position': table}
    (out_dir / 'scores.json').write_text(json.dumps(result, indent=1) + '\n')
    return result


def shape_problem(c, value, context):
    """Why the controller would reject this reply, or None. Legality against the board is not checked here."""
    expected = {'action', 'hypotheses'} | ({'recovery'} if context['check'] else set())
    extra = set(value) - expected - {'recovery'}
    if extra or expected - set(value):
        return 'keys differ from the contract'
    if context['check']:
        answer = value['recovery']
        if not isinstance(answer, dict) or answer.get('choice') not in ('continue', 'reset'):
            return 'recovery answer malformed'
        if (answer['choice'] == 'reset') != (value['action']['action_id'] == 0):
            return 'recovery.choice and the action disagree'
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=('prepare', 'send', 'score'))
    parser.add_argument('out_dir', type=Path)
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--send', action='store_true', help='really call the model')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    if args.command == 'prepare':
        for row in prepare(args.out_dir):
            print(row['id'], 'after', row['actions_before'], 'actions; completed later:', row['level_completed_later'],
                  row['actions_until_completed'], row['sha256'][:12])
        return 0
    if args.command == 'score':
        print(json.dumps(score(args.out_dir), indent=1))
        return 0
    if args.send == args.dry_run:
        raise SystemExit('choose exactly one of --send (calls the model) and --dry-run')
    print('wrote', send(args.out_dir, args.repeats, args.dry_run))
    return 0


if __name__ == '__main__':
    sys.exit(main())
