"""Prove from the logs alone that a continued run sent what the 6 November code would have sent.

The harness files on disk can change while a long run is in flight (other studies add switches), and a
run keeps the code it loaded at its start. So this check does not trust the files on disk. It takes
research/claude_arc_v1 and agent exactly as committed in 38f41e9, confirms that they are the files the
6 November run recorded, and then, for a continued run:

  - rebuilds the policy's state turn by turn from the logged observations, actions and replies
    (the replies to the repeated actions come from the log the run repeated, the later ones from the
    continued run's own log);
  - at every turn where the continued run called the model, compares the logged request with the
    request the 6 November code builds from that state.

No model call, no game engine.

    verify_requests.py <run folder>...       (works on a run that is still in progress)

Usage (project environment): .venv/bin/python research/baseline_continue_v1/verify_requests.py ...
"""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMIT = '38f41e9'
SAVED = ROOT / '.cache/claude_arc_runs/opus55-competition-20261106T054112Z/events.jsonl'
CONTROL = ROOT / 'config/claude_arc_v1.opus55_competition.json'


def november_code():
    """Write the committed harness to a temporary folder; return it after checking it against the 6 Nov log."""
    folder = Path(tempfile.mkdtemp(prefix='nov6-code-'))
    names = subprocess.run(['git', 'ls-tree', '-r', '--name-only', COMMIT, '--', 'research/claude_arc_v1', 'agent'],
                           cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    for name in names:
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.run(['git', 'show', '%s:%s' % (COMMIT, name)], cwd=ROOT,
                                          capture_output=True, check=True).stdout)
    with SAVED.open(encoding='utf-8') as handle:
        bound = json.loads(handle.readline())
    if bound['kind'] != 'source_bindings':
        raise ValueError('the 6 November log does not start with its source bindings')
    wrong = [name for name, digest in bound['files_sha256'].items()
             if hashlib.sha256((folder / name).read_bytes()).hexdigest() != digest]
    if wrong:
        raise ValueError('commit %s is not the code of the 6 November run: %s' % (COMMIT, ', '.join(wrong)))
    if hashlib.sha256(CONTROL.read_bytes()).hexdigest() != bound['config_sha256']:
        raise ValueError('the control config file has changed since 6 November')
    return folder


def saved_answers(events, game, count):
    """The accepted reply for each of the game's first `count` saved actions (None where the controller
    reset the level), from the log the run repeated: the 6 November log, or a merged log for an extension."""
    answers, pending = [], None
    with (ROOT / events).open(encoding='utf-8') as handle:
        for line in handle:
            if game not in line or len(answers) >= count:
                continue
            if '"kind":"model_returned"' in line:
                event = json.loads(line)
                if event.get('game_id') == game:
                    pending = event['content']
            elif '"kind":"transition"' in line:
                event = json.loads(line)
                if event.get('game_id') == game:
                    answers.append(pending)
                    pending = None
    return answers


def verify(folder, C, P, Observation, ActionDecision, GameState, np):
    def observation(value):
        return Observation(value['game_id'], tuple(np.asarray(f, dtype=np.uint8) for f in value['frames']),
                           GameState[value['state']], value['levels_completed'], value['win_levels'], 'verify',
                           tuple(value['available_actions']), value['full_reset'])

    policy = saved = game = config = None
    requests, reply, index = {}, None, 0
    compared, differ, retried = 0, [], 0
    with (Path(folder) / 'events.jsonl').open(encoding='utf-8') as handle:
        for line in handle:
            if not line.endswith('\n'):
                break                        # a line still being written by a run in progress
            kind = line.split('"kind":"', 1)[1].split('"', 1)[0]
            if kind == 'configuration':
                config = json.loads(line)['config']
                # the 6 November code knows only the 6 November settings; the game list is not in any request
                policy = P.Policy(C.Config(**{**json.loads(CONTROL.read_text()), 'mode': 'online',
                                              'games': list(config['games'])}))
            elif kind == 'model_entered':
                event = json.loads(line)
                if event.get('attempt'):
                    retried += 1
                else:
                    requests[event['action_index']] = event['request']
            elif kind == 'model_returned':
                reply = json.loads(line)['content']
            elif kind == 'transition':
                event = json.loads(line)
                if saved is None:
                    game = event['game_id']
                    saved = saved_answers(config['resume_events'], game, config['resume_actions'])
                before, after = observation(event['before']), observation(event['after'])
                if index in requests:
                    compared += 1
                    if policy.request(before) != requests[index]:
                        differ.append(index + 1)
                content = saved[index] if index < len(saved) else reply
                answer = C.strict_json(content) if content is not None else {
                    'action': event['action'], 'hypotheses': list(policy.hypotheses)}
                decision = ActionDecision(event['action']['action_id'], dict(event['action']['action_data']), source='verify')
                policy.observe(before, decision, after, answer)
                reply, index = None, index + 1
    return {'run': Path(folder).name, 'game': game, 'actions_in_log': index, 'new_actions': max(0, index - len(saved or [])),
            'requests_compared': compared, 'requests_that_differ_from_6_nov_code': differ,
            'retries_not_compared': retried, 'same_as_6_november_code': not differ and compared > 0}


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    code = november_code()
    sys.path.insert(0, str(code))            # the committed harness, not the files on disk
    import numpy
    from arcengine import GameState as State
    from agent.action import ActionDecision as Decision
    from agent.state import Observation as Seen
    from research.claude_arc_v1 import config as november_config, policy as november_policy
    if not Path(november_policy.__file__).is_relative_to(code):
        raise SystemExit('the committed harness was not the one imported')
    good = True
    for run_folder in sys.argv[1:]:
        result = verify(run_folder, november_config, november_policy, Seen, Decision, State, numpy)
        good = good and result['same_as_6_november_code']
        print(json.dumps(result))
    sys.exit(0 if good else 1)
