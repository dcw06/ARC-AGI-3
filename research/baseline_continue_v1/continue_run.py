"""Continue the 6 November run past its 100-action cap, game by game, with the same harness.

The 6 November run (research/claude_arc_v1, Claude Opus 5.5, effort high, Claude subscription) stopped
every game after 100 actions. This plays chosen games on from their 101st action up to a per-game cap
(reports/arc_skill_opus5_v1/action_caps_astra.json):

  - each game first repeats its saved actions on the local copy of the game, with no model call;
    every returned observation must hash to the saved one, and the saved replies rebuild the agent's
    history and notes exactly (research/claude_arc_v1/resume.py);
  - from the next action the unchanged controller, policy and backend play with the control settings of
    config/claude_arc_v1.opus55_competition.json (every later study switch off);
  - games run one after another, as on 6 November; nothing is carried from one game to the next.

No ARC service is called and there is no scorecard: the counts come from the run's own event log.

    continue_run.py check <game>...    no model call: replays the saved actions and compares, turn by
                                       turn, the request this code builds with the request sent before
    continue_run.py run <game>...      plays on; one call per new action on the Claude subscription
    continue_run.py status             progress of the newest batch

A game that an earlier continuation left unfinished can be picked up where it stopped:

    --extend <game>=<earlier run folder>   continue from the end of that run instead of from action 100
    --resets <n>                           level resets allowed in the extended games (the harness's own
                                           limit is 10 per game; this is the one rule an extension changes)

Usage (project environment), from anywhere: .venv/bin/python -m research.baseline_continue_v1.continue_run ...
"""
import hashlib
import importlib.metadata
import json
import os
import shutil
import signal
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def load_harness():
    """Import the harness once, when a command needs it. `status` must work without it: a running batch
    keeps the code it loaded at its start, while the files on disk may be mid-edit by other work."""
    global ActionDecision, audit, C, resume, run, Budget, ClaudeCodeBackend, Policy, LocalGames
    from agent.action import ActionDecision
    from research.claude_arc_v1 import audit, config as C, resume, run
    from research.claude_arc_v1.backends import Budget, ClaudeCodeBackend
    from research.claude_arc_v1.policy import Policy
    from research.baseline_continue_v1.local_games import LocalGames


CONTROL = ROOT / 'config/claude_arc_v1.opus55_competition.json'
SAVED_RUN = '.cache/claude_arc_runs/opus55-competition-20261106T054112Z'
SAVED = SAVED_RUN + '/events.jsonl'
CAPS = ROOT / 'reports/arc_skill_opus5_v1/action_caps_astra.json'
RUNS = ROOT / '.cache/claude_arc_runs'
DONE = 100            # actions each game had used when the 6 November run stopped it
ENDED_NORMALLY = ('action_cap', 'win', 'game_over')
KEPT = ('initial_observation', 'model_entered', 'model_returned', 'transition')


def full_ids():
    summary = json.loads((ROOT / SAVED_RUN / 'summary.json').read_text())
    return {g.split('-', 1)[0]: g for g in summary['selected_games']}


def caps():
    return {g['game']: g['action_cap'] for g in json.loads(CAPS.read_text())['games']}


def kind_of(line):
    return line.split('"kind":"', 1)[1].split('"', 1)[0] if '"kind":"' in line else ''


def merged_log(game, earlier):
    """One log holding a game's whole earlier play: what the earlier run repeated, then what it played.

    resume.py reads a saved run from one file and refuses a run that was itself continued. An earlier
    continuation's log holds only its own replies, so the two are joined: the configuration and the
    game's first N actions from the file the earlier run repeated, then every later action from the
    earlier run's own log. Lines are copied unchanged. Returns (path, actions in it).
    """
    earlier = Path(earlier)
    with (earlier / 'events.jsonl').open(encoding='utf-8') as handle:
        config = next(json.loads(line)['config'] for line in handle if kind_of(line) == 'configuration')
    source, repeated = ROOT / config['resume_events'], config['resume_actions']
    out = RUNS / ('merged-from-%s.jsonl' % earlier.name)
    lines, actions, have_configuration = [], 0, False
    with source.open(encoding='utf-8') as handle:
        for line in handle:
            kind = kind_of(line)
            if kind == 'configuration' and not have_configuration:
                lines.append(line)
                have_configuration = True
            elif kind in KEPT and game in line and json.loads(line).get('game_id') == game and actions < repeated:
                lines.append(line)
                actions += kind == 'transition'
    if actions != repeated:
        raise ValueError('the earlier run repeated %d actions but its source holds %d' % (repeated, actions))
    seen = 0
    with (earlier / 'events.jsonl').open(encoding='utf-8') as handle:
        for line in handle:
            kind = kind_of(line)
            if kind == 'transition':
                seen += 1
            if seen > repeated or (seen == repeated and kind != 'transition'):
                # after the last repeated action: this run's own turns
                if kind in ('model_entered', 'model_returned', 'transition'):
                    lines.append(line)
                    actions += kind == 'transition'
    out.write_text(''.join(lines), encoding='utf-8')
    return str(out.relative_to(ROOT)), actions


def sources(names, extend, resets):
    """{name: where its earlier play is, how many actions, and the reset allowance (None = the harness's)}."""
    ids, plan = full_ids(), {}
    for name in names:
        if name in extend:
            events, done = merged_log(ids[name], ROOT / extend[name])
            plan[name] = {'events': events, 'done': done, 'resets': resets, 'extends': extend[name]}
        else:
            plan[name] = {'events': SAVED, 'done': DONE, 'resets': None}
    return plan


def settings(name, cap, source, resumed=None):
    resumed = source['done'] if resumed is None else resumed
    new = cap - resumed
    extra = {} if source['resets'] is None else {'resets_per_game': source['resets']}
    return C.Config(**{**json.loads(CONTROL.read_text()), 'mode': 'online', 'games': [name],
                       'resume_events': source['events'], 'resume_actions': resumed, 'max_actions_per_game': cap,
                       # one call per new action, with room for replies the controller sends back
                       'max_model_calls': new + new // 4 + 40, **extra})


@contextmanager
def reset_rule(source):
    """resume.py refuses a saved run whose reset allowance differs from the new run's. An extension raises
    the allowance on purpose (it is not shown to the model and changes no request), so that one comparison
    is lifted while an extended game is loaded and played. Every other setting must still match."""
    kept = resume.MUST_MATCH
    if source['resets'] is not None:
        resume.MUST_MATCH = tuple(n for n in kept if n != 'resets_per_game')
    try:
        yield
    finally:
        resume.MUST_MATCH = kept


def saved_requests(events, game):
    """{action_index: first request sent for that action} for one game, from a saved log."""
    out = {}
    with (ROOT / events).open(encoding='utf-8') as handle:
        for line in handle:
            if kind_of(line) != 'model_entered' or game not in line:
                continue
            event = json.loads(line)
            if event.get('game_id') == game and not event.get('attempt'):
                out.setdefault(event['action_index'], event['request'])
    return out


class FirstRequest:
    """Stands in for the model: keeps the first request the controller builds, then ends the run."""

    def __init__(self, config):
        self.config, self.budget, self.last_record, self.request = config, Budget(config), None, None

    def complete(self, request):
        self.budget.reserve()
        self.request = request
        raise KeyboardInterrupt()


def check(names, plan):
    """No model call. Returns True when every game can be continued exactly."""
    ids, limit = full_ids(), caps()
    all_good = True
    for name in names:
        game, source = ids[name], plan[name]
        requests = saved_requests(source['events'], game)
        config = settings(name, limit[name], source)
        with reset_rule(source):
            saved = resume.load(source['events'], [game], source['done'], config)[game]
        world, policy = LocalGames([game]), Policy(config)
        client = world.bootstrap(game)
        first_ok = client.observation.canonical_hash == saved['initial_sha256']
        boards, asked, differ = [], 0, []
        for index, item in enumerate(saved['actions']):
            before = client.observation
            if item['answer'] is not None:
                asked += 1
                if policy.request(before) != requests.get(index):
                    differ.append(index + 1)
            decision = ActionDecision(item['action']['action_id'], dict(item['action']['action_data']),
                                      source='controller_resume')
            answer = item['answer'] or {'action': item['action'], 'hypotheses': list(policy.hypotheses)}
            after = world.dispatch(client, decision)
            if after.canonical_hash != item['after_sha256']:
                boards.append(index + 1)
            policy.observe(before, decision, after, answer)
        # The controller's own path: repeat the saved actions up to the last turn that had a model call,
        # let the controller build that turn's request, and compare it with the one sent then.
        last = max(requests)
        probe = FirstRequest(settings(name, limit[name], source, resumed=last))
        folder = Path(tempfile.mkdtemp(prefix='continue-check-')) / 'run'
        try:
            with reset_rule(source):
                run.evaluate(probe.config, probe, LocalGames([game]), run.Evidence(folder))
        finally:
            shutil.rmtree(folder.parent, ignore_errors=True)
        controller_ok = probe.request == requests[last]
        good = first_ok and not boards and not differ and controller_ok
        all_good = all_good and good
        end = client.observation
        print(json.dumps({'game': game, 'can_continue_exactly': good, 'saved_actions_replayed': len(saved['actions']),
                          'first_board_equal': first_ok, 'boards_that_differ': boards,
                          'turns_with_a_model_call': asked, 'requests_that_differ': differ,
                          'controller_request_after_resume_equal': controller_ok, 'compared_at_action': last + 1,
                          'after_saved_actions': {'state': end.state.name, 'levels_completed': end.levels_completed,
                                                  'of': end.win_levels,
                                                  'resets_used': sum(1 for a in saved['actions'] if a['answer'] is None)},
                          'cap': limit[name], 'new_actions': limit[name] - source['done'],
                          'resets_allowed': config.resets_per_game, 'continues_from': source['events']}))
    return all_good


def per_level(folder):
    """Actions, game overs and completion per level, from the run's event log (saved actions included)."""
    levels = {}
    with (Path(folder) / 'events.jsonl').open(encoding='utf-8') as handle:
        for line in handle:
            if '"kind":"transition"' not in line:
                continue
            event = json.loads(line)
            level = event['before']['levels_completed'] + 1
            row = levels.setdefault(level, {'level': level, 'actions': 0, 'game_overs': 0, 'resets': 0, 'completed': False})
            row['actions'] += 1
            row['resets'] += event['action']['action_id'] == 0
            row['game_overs'] += event['after']['state'] == 'GAME_OVER' and event['before']['state'] != 'GAME_OVER'
            row['completed'] = row['completed'] or event['after']['levels_completed'] > event['before']['levels_completed']
    return [levels[k] for k in sorted(levels)]


def play(names, plan, stamp):
    ids, limit = full_ids(), caps()
    batch = RUNS / ('baseline-continue-%s.json' % stamp)
    state = {'started': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'games_planned': list(names), 'games': [], 'finished': False}

    def save():
        batch.write_text(json.dumps(state, indent=1) + '\n')
    save()
    for name in names:
        game, cap, source = ids[name], limit[name], plan[name]
        config = settings(name, cap, source)
        folder = RUNS / ('baseline-continue-%s-%s' % (name, stamp))
        entry = {'game': game, 'folder': str(folder.relative_to(ROOT)), 'cap': cap, 'status': 'running',
                 'continues_from': source['events'], 'saved_actions': source['done'],
                 'resets_allowed': config.resets_per_game}
        state['games'].append(entry)
        save()
        backend = ClaudeCodeBackend(config, Budget(config))
        evidence = run.Evidence(folder)
        files = list((ROOT / 'agent').glob('*.py')) + list((ROOT / 'research/claude_arc_v1').glob('*.py')) \
            + list(Path(__file__).parent.glob('*.py'))
        evidence.write('source_bindings',
                       files_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)},
                       config_sha256=hashlib.sha256(CONTROL.read_bytes()).hexdigest(),
                       packages={p: importlib.metadata.version(p) for p in ('arc-agi', 'arcengine', 'numpy', 'requests')})
        evidence.write('backend_binding', backend='claude_code', cli_version='.'.join(map(str, backend.version)),
                       cli_sha256=hashlib.sha256(Path(backend.executable).resolve().read_bytes()).hexdigest())
        began = time.time()
        try:
            with reset_rule(source):
                result = run.evaluate(config, backend, LocalGames([game]), evidence)
        finally:
            evidence.close()
        row = result['games'][0] if result['games'] else {}
        try:
            audit.audit(folder)
            audited = 'passes'
        except Exception as exc:
            audited = 'fails: %s' % str(exc)[:200]
        entry.update(status='ended', minutes=round((time.time() - began) / 60, 1), problems=result['problems'],
                     stop_reason=row.get('stop_reason'), actions=row.get('actions_acknowledged'),
                     repeated_saved_actions=row.get('resumed_actions'), levels_completed=row.get('levels_completed'),
                     final_state=row.get('final_state'), level_resets=row.get('level_resets'),
                     model_calls=result['budget'].get('model_calls_attempted'), audit=audited, levels=per_level(folder))
        save()
        print(json.dumps({k: v for k, v in entry.items() if k != 'levels'}), flush=True)
        if row.get('stop_reason') not in ENDED_NORMALLY:
            # A plan limit, login problem, timeout or interruption would end every later game the same way.
            state['stopped_early'] = 'after %s: %s' % (name, row.get('stop_reason'))
            break
    state['finished'] = True
    state['ended'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    save()
    return state


def status():
    batches = sorted(RUNS.glob('baseline-continue-2*.json'))
    if not batches:
        print('no batch yet')
        return
    states = [(path, json.loads(path.read_text())) for path in batches]
    # the newest batch, and any older one still running (two batches can run side by side)
    shown = [item for item in states[:-1] if not item[1]['finished']] + states[-1:]
    for path, state in shown:
        print('batch', path.name, '| started', state['started'], '| finished' if state['finished'] else '| running',
              '|', state.get('stopped_early', ''))
        for entry in state['games']:
            if entry['status'] == 'ended':
                print('  %-14s ended: %s  actions %s of cap %s  levels %s  resets %s  %s min  audit %s' % (
                    entry['game'], entry['stop_reason'], entry['actions'], entry['cap'], entry['levels_completed'],
                    entry['level_resets'], entry['minutes'], entry['audit']))
            else:
                done = level = 0
                with (ROOT / entry['folder'] / 'events.jsonl').open(encoding='utf-8') as handle:
                    for line in handle:
                        if '"kind":"transition"' in line:
                            done += 1
                            last = line
                if done:
                    level = json.loads(last)['after']['levels_completed']
                print('  %-14s running: action %d of cap %d, %d levels completed' % (entry['game'], done, entry['cap'], level))
        waiting = [n for n in state['games_planned'] if n not in {e['game'].split('-', 1)[0] for e in state['games']}]
        if waiting and not state['finished']:
            print('  waiting:', ', '.join(waiting))


def arguments(values):
    """(names, {name: earlier run folder}, resets) from the command line after the command word."""
    names, extend, resets, values = [], {}, None, list(values)
    while values:
        value = values.pop(0)
        if value == '--extend':
            name, folder = values.pop(0).split('=', 1)
            extend[name] = folder
        elif value == '--resets':
            resets = int(values.pop(0))
        else:
            names.append(value)
    if extend and resets is None:
        raise SystemExit('--extend needs --resets <n>')
    if any(name not in names for name in extend):
        raise SystemExit('an extended game must also be listed among the games to run')
    return names, extend, resets


if __name__ == '__main__':
    os.chdir(ROOT)
    command = sys.argv[1] if len(sys.argv) > 1 else ''
    if command == 'status':
        status()
    elif command in ('check', 'run'):
        names, extend, resets = arguments(sys.argv[2:])
        if not names or any(n not in full_ids() or n not in caps() for n in names):
            raise SystemExit(__doc__)
        load_harness()
        plan = sources(names, extend, resets)
        if command == 'check':
            sys.exit(0 if check(names, plan) else 1)
        signal.signal(signal.SIGHUP, signal.SIG_IGN)       # closing the terminal must not end an overnight run

        def interrupted(signum, frame):
            raise KeyboardInterrupt()
        signal.signal(signal.SIGTERM, interrupted)         # lets the controller write its summary first
        outcome = play(names, plan, time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
        sys.exit(0 if 'stopped_early' not in outcome else 1)
    else:
        raise SystemExit(__doc__)
