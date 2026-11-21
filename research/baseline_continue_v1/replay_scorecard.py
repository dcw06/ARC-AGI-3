"""One official ARC scorecard for the extended baseline, made by replaying its recorded actions.

The extended baseline (reports/baseline_continue_v1) was played on local copies of the games, so no
scorecard exists for it. This sends every recorded action of all 25 games to the ARC service, in one
competition-mode scorecard, with no model call:

  - a game's actions come from its last continuation log (all actions, the first 100 included), or from
    the 6 November log for the games that were not continued;
  - after every action the observation the service returns must hash to the recorded one; at the first
    difference, or any transport error, that game stops and its remaining actions are not sent
    (competition mode allows one start per game, so there is no retry);
  - the scorecard is closed once, and what the service returns at close is saved.

    replay_scorecard.py expect     offline: the score the service should give, from the recorded per-level
                                   counts and ARC's scoring rule (the rule is first checked against the
                                   6 November scorecard)
    replay_scorecard.py dry        offline: the same replay against the local game copies
    replay_scorecard.py inventory  read-only call: does the service still offer the recorded game versions?
    replay_scorecard.py send --confirm-online-arc     the live replay

  --finished-only   (expect, dry, send) leave out the log of a game that a continuation is playing right
                    now; that game is taken from its last finished run. Without it, `send` refuses while a
                    continuation is running.

Usage (project environment), from anywhere: .venv/bin/python -m research.baseline_continue_v1.replay_scorecard ...
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
SAVED_RUN = ROOT / '.cache/claude_arc_runs/opus55-competition-20261106T054112Z'
RUNS = ROOT / '.cache/claude_arc_runs'
CONTROL = ROOT / 'config/claude_arc_v1.opus55_competition.json'
TAGS = ['claude-arc-v1', 'hypotheses', 'competition', 'replay-of-recorded-actions', 'baseline-continue-v1']
MIN_SECONDS_PER_ACTION = 0.12        # at most about 500 requests a minute


def saved_summary():
    return json.loads((SAVED_RUN / 'summary.json').read_text())


def in_play():
    """Run folders of games a continuation is playing right now (their batch has not recorded a result)."""
    out = set()
    for path in RUNS.glob('baseline-continue-2*.json'):
        state = json.loads(path.read_text())
        if not state['finished']:
            out.update(entry['folder'] for entry in state['games'] if entry['status'] != 'ended')
    return out


def recorded(skip=()):
    """{game id: {'source', 'first', 'steps': [{'action', 'after', 'levels', 'state'}]}} for all 25 games, in
    the 6 November order. Run folders named in `skip` are left out."""
    order = saved_summary()['selected_games']
    out = {}
    for game in order:
        name = game.split('-', 1)[0]
        best = None
        for folder in sorted(RUNS.glob('baseline-continue-%s-2*' % name)):
            if str(folder.relative_to(ROOT)) in skip:
                continue
            first, steps = None, []
            with (folder / 'events.jsonl').open(encoding='utf-8') as handle:
                for line in handle:
                    if not line.endswith('\n'):
                        break
                    if '"kind":"initial_observation"' in line:
                        first = json.loads(line)['observation']['observation_sha256']
                    elif '"kind":"transition"' in line:
                        event = json.loads(line)
                        steps.append({'action': event['action'], 'after': event['after']['observation_sha256'],
                                      'before_levels': event['before']['levels_completed'],
                                      'levels': event['after']['levels_completed'], 'state': event['after']['state']})
            if best is None or len(steps) > len(best['steps']):
                best = {'source': str(folder.relative_to(ROOT)), 'first': first, 'steps': steps}
        if best is not None:
            out[game] = best
    missing = [g for g in order if g not in out]
    if missing:
        found = {g: {'source': str(SAVED_RUN.relative_to(ROOT)), 'first': None, 'steps': []} for g in missing}
        with (SAVED_RUN / 'events.jsonl').open(encoding='utf-8') as handle:
            for line in handle:
                if '"kind":"initial_observation"' in line or '"kind":"transition"' in line:
                    event = json.loads(line)
                    game = event.get('game_id')
                    if game not in found:
                        continue
                    if event['kind'] == 'initial_observation':
                        found[game]['first'] = event['observation']['observation_sha256']
                    else:
                        found[game]['steps'].append({'action': event['action'],
                                                     'after': event['after']['observation_sha256'],
                                                     'before_levels': event['before']['levels_completed'],
                                                     'levels': event['after']['levels_completed'],
                                                     'state': event['after']['state']})
        out.update(found)
    return {g: out[g] for g in order}


def level_actions(steps, level_count):
    """Actions used on each level, and how many levels were completed."""
    used = [0] * level_count
    for step in steps:
        if step['before_levels'] < level_count:
            used[step['before_levels']] += 1
    return used, (steps[-1]['levels'] if steps else 0)


def game_score(used, human, completed):
    """ARC's rule as the 6 November scorecard shows it: a completed level scores 100 (H / A) squared, capped
    at 115; levels are weighted 1, 2, 3, ...; the game cannot score more than the weight share of its
    completed levels."""
    weights = range(1, len(human) + 1)
    total = sum(weights)
    levels = [min(115.0, 100.0 * (human[i] / used[i]) ** 2) if i < completed and used[i] else 0.0
              for i in range(len(human))]
    weighted = sum(w * s for w, s in zip(weights, levels)) / total
    ceiling = 100.0 * sum(w for i, w in enumerate(weights) if i < completed) / total
    return min(weighted, ceiling), levels


def expect(plan=None):
    """The score the service should report. Returns (card score, per-game rows)."""
    official = saved_summary()['official_scorecard']
    wrong = []
    human = {}
    for env in official['environments']:
        run = env['runs'][0]
        human[env['id']] = run['level_baseline_actions']
        mine, _ = game_score(run['level_actions'], run['level_baseline_actions'], run['levels_completed'])
        if abs(mine - env['score']) > 1e-6:
            wrong.append(env['id'])
    print('scoring rule against the 6 November scorecard: %d of %d games reproduced%s' % (
        len(official['environments']) - len(wrong), len(official['environments']), ' | not: ' + ', '.join(wrong) if wrong else ''))
    plan = plan or recorded()
    rows = []
    for game, saved in plan.items():
        used, completed = level_actions(saved['steps'], len(human[game]))
        score, _ = game_score(used, human[game], completed)
        rows.append({'game': game, 'actions': len(saved['steps']), 'levels_completed': completed,
                     'levels': len(human[game]), 'score': score, 'level_actions': used, 'source': saved['source'],
                     'resets': sum(1 for s in saved['steps'] if s['action']['action_id'] == 0)})
    card = sum(r['score'] for r in rows) / len(rows)
    return card, rows


def replay(adapter, plan, log, pace):
    """Send every recorded action. Returns per-game results. One scorecard, opened and closed here."""
    from agent.action import ActionDecision
    results, card, closed = [], None, None
    inventory = adapter.list_game_ids()
    absent = [g for g in plan if g not in inventory]
    if absent:
        raise SystemExit('these game versions are not offered by the service, nothing was sent: ' + ', '.join(absent))
    card = adapter.open_scorecard(tags=TAGS)
    log({'event': 'scorecard_opened', 'card_id': card})
    print('scorecard opened:', card, flush=True)
    try:
        for game, saved in plan.items():
            row = {'game': game, 'recorded_actions': len(saved['steps']), 'sent': 0, 'matched': 0, 'stopped': None}
            results.append(row)
            client = None
            began = time.monotonic()
            try:
                client = adapter.bootstrap(game)
                if client.observation.canonical_hash != saved['first']:
                    row['stopped'] = 'the first board differs from the recorded one'
                    continue
                for index, step in enumerate(saved['steps']):
                    tick = time.monotonic()
                    decision = ActionDecision(step['action']['action_id'], dict(step['action']['action_data']),
                                              source='recorded_replay')
                    after = adapter.dispatch(client, decision)
                    row['sent'] += 1
                    if after.canonical_hash != step['after']:
                        row['stopped'] = 'observation differs from the recorded one at action %d' % (index + 1)
                        break
                    row['matched'] += 1
                    wait = pace - (time.monotonic() - tick)
                    if wait > 0:
                        time.sleep(wait)
            except KeyboardInterrupt:
                row['stopped'] = 'interrupted'
                raise
            except Exception as exc:
                row['stopped'] = '%s: %s' % (type(exc).__name__, str(exc)[:200])
            finally:
                if client is not None:
                    adapter.finalize_client(client)
                row['seconds'] = round(time.monotonic() - began, 1)
                log({'event': 'game', **row})
                print('  %-14s sent %4d of %4d, matched %4d, %s' % (
                    game, row['sent'], row['recorded_actions'], row['matched'], row['stopped'] or 'complete'), flush=True)
    finally:
        try:
            closed = adapter.close_scorecard()
            log({'event': 'scorecard_closed', 'result': closed})
        except Exception as exc:
            log({'event': 'scorecard_close_failed', 'error': '%s: %s' % (type(exc).__name__, str(exc)[:200])})
    return card, closed, results


def live_adapter():
    """The harness's own ARC adapter, in competition mode with the 6 November settings."""
    key = os.environ.get('ARC_API_KEY') or next(
        (line.split('=', 1)[1].strip() for line in (ROOT / '.env').read_text().splitlines()
         if line.startswith('ARC_API_KEY=')), '')
    if not key or any(c in key for c in '\r\n'):
        raise SystemExit('ARC_API_KEY is missing')
    from research.claude_arc_v1.arc import make_adapter
    from research.claude_arc_v1.config import Config
    config = Config.load(str(CONTROL))
    started = time.monotonic()
    return make_adapter(config, key, lambda: 6 * 3600 - (time.monotonic() - started))


def table(rows):
    for r in rows:
        print('  %-14s actions %4d  resets %2d  levels %d of %d  expected score %6.2f  (%s)' % (
            r['game'], r['actions'], r['resets'], r['levels_completed'], r['levels'], r['score'], r['source'].split('/')[-1]))


if __name__ == '__main__':
    os.chdir(ROOT)
    command = sys.argv[1] if len(sys.argv) > 1 else ''
    left_out = sorted(in_play()) if '--finished-only' in sys.argv else []
    if left_out:
        print('left out, still in play:', ', '.join(left_out))
    if command == 'expect':
        card, rows = expect(recorded(left_out))
        table(rows)
        print('games %d | actions %d | levels %d of %d | expected card score %.4f' % (
            len(rows), sum(r['actions'] for r in rows), sum(r['levels_completed'] for r in rows),
            sum(r['levels'] for r in rows), card))
    elif command == 'inventory':
        # read-only: does the service still offer the 25 recorded game versions?
        adapter = live_adapter()
        offered = adapter.list_game_ids()
        wanted = saved_summary()['selected_games']
        absent = [g for g in wanted if g not in offered]
        print('service offers %d games | all 25 recorded versions offered: %s%s' % (
            len(offered), not absent, ' | absent: ' + ', '.join(absent) if absent else ''))
        sys.exit(0 if not absent else 1)
    elif command in ('dry', 'send'):
        plan = recorded(left_out)
        expected_card, rows = expect(plan)
        stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
        folder = RUNS / ('baseline-replay-%s-%s' % (command, stamp))
        folder.mkdir(parents=True)
        stream = (folder / 'replay.jsonl').open('w', encoding='utf-8')

        def log(value):
            stream.write(json.dumps(value) + '\n')
            stream.flush()
        if command == 'dry':
            from research.baseline_continue_v1.local_games import LocalGames
            adapter, pace = LocalGames(list(plan)), 0
        else:
            if '--confirm-online-arc' not in sys.argv:
                raise SystemExit('the live replay sends to the ARC service: pass --confirm-online-arc')
            running = [p.name for p in RUNS.glob('baseline-continue-2*.json') if not json.loads(p.read_text())['finished']]
            if running and '--finished-only' not in sys.argv:
                raise SystemExit('a continuation is still running (%s); replay after it ends, or pass '
                                 '--finished-only' % ', '.join(running))
            adapter = live_adapter()
            pace = MIN_SECONDS_PER_ACTION
        card, closed, results = replay(adapter, plan, log, pace)
        complete = all(r['stopped'] is None and r['matched'] == r['recorded_actions'] for r in results)
        manifest = {'command': command, 'card_id': card,
                    'scorecard_url': 'https://arcprize.org/scorecards/' + card if command == 'send' else None,
                    'every_action_matched': complete, 'expected_card_score': expected_card,
                    'official_scorecard': closed, 'games': results, 'expected': rows, 'tags': TAGS,
                    'left_out_still_in_play': left_out}
        (folder / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
        stream.close()
        print('every recorded action matched:', complete, '| actions sent', sum(r['sent'] for r in results),
              '| expected card score %.4f' % expected_card)
        if command == 'send':
            print('scorecard:', manifest['scorecard_url'])
            if isinstance(closed, dict) and 'score' in closed:
                print('official score at close: %.4f | levels %s of %s | actions %s' % (
                    closed['score'], closed.get('total_levels_completed'), closed.get('total_levels'), closed.get('total_actions')))
        print('saved:', folder.relative_to(ROOT))
        sys.exit(0 if complete else 1)
    else:
        raise SystemExit(__doc__)
