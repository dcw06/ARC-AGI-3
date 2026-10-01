"""Decision-boundary fixtures (synthetic diagnostics; development material only).

Each fixture is a short scripted action sequence in a synthetic environment with a known mechanism, ending at a
decision point. The fixture keeps the raw transitions (contract input format), the legal actions and the current
frame. Expectations are written by hand from the construction (what the script did, in which state), not taken from
the evaluator; tests check the evaluator against them.

Rules:
- `source` is 'synthetic' for every fixture here. Synthetic fixtures may state the known mechanism and the actions
  that make progress, for scoring. A 'real_game' fixture must never carry `progress_keys`: real-game fixtures must
  not assume one uniquely correct next action (`check_rules`). No real-game fixture exists yet.
- Expectations and mechanisms are evaluator-only and stored apart from the raw evidence.
"""
import hashlib
import json
from pathlib import Path

from research.feedback_action_v1 import environments as ENV

VERSION = 'feedback_action_v1_fixtures'
OUTPUT = Path(__file__).with_name('fixtures.json')
A = ENV.action

# name: (environment, constructor kwargs, actions, probes {key: expected status}, extra evaluator-only facts)
SPECS = {
    'exact_repeat_no_change_same_state': (
        'push_to_goal', {}, [A(1)],
        {(1,): 'no_change_same_state', (2,): 'untested', (3,): 'untested', (4,): 'untested'},
        {'note': 'ACTION1 into the wall changed nothing, and the agent is still in that state'}),
    'same_action_other_coordinate': (
        'clicker', {}, [A(6, 1, 1)],
        {(6, 1, 1): 'no_change_same_state', (6, 5, 5): 'untested', (6, 2, 5): 'untested'},
        {'note': 'only the exact coordinate was tested; other coordinates of ACTION6 are untested'}),
    'tested_in_other_state': (
        'push_to_goal', {}, [A(1), A(2)],
        {(1,): 'tested_other_state', (2,): 'tested_other_state', (3,): 'untested', (4,): 'untested'},
        {'note': 'ACTION1 changed nothing in the starting state; the agent has since moved'}),
    'failed_dispatch': (
        'push_to_goal', {'faults': {0: 'failed'}}, [A(4)],
        {(4,): 'failed_only', (1,): 'untested'},
        {'note': 'the dispatch failed: ACTION4 is untested, not ineffective'}),
    'unknown_outcome': (
        'push_to_goal', {'faults': {0: 'outcome_unknown'}}, [A(2)],
        {(2,): 'outcome_unknown_only', (1,): 'untested'},
        {'note': 'ACTION2 executed (the marker moved) but its result was never returned'}),
    'changed_then_reverted': (
        'clicker', {}, [A(6, 2, 5)],
        {(6, 2, 5): 'transient_same_state', (6, 5, 5): 'untested'},
        {'note': 'the decoy flashed and returned: something visibly happened'}),
    'necessary_repeat': (
        'delayed_switch', {}, [A(5), A(5)],
        {(5,): 'no_change_same_state', (1,): 'untested'},
        {'progress_keys': [[5]],
         'note': 'a third ACTION5 completes the level: here an exact repeat after no observed change is necessary'}),
    'contradicts_hypothesis': (
        'push_to_goal', {}, [A(1)],
        {(1,): 'no_change_same_state', (2,): 'untested'},
        {'prior_prediction': {'about': 'T0', 'visual_effect': 'final_frame_differs', 'level_completed': False,
                              'changed_region_xyxy': None},
         'contradiction_ref': 'T0',
         'note': 'the previous decision predicted that ACTION1 changes the final frame; it changed nothing'}),
    'after_level_boundary': (
        'delayed_switch', {}, [A(1), A(5), A(5), A(5)],
        {(1,): 'untested', (5,): 'untested'},
        {'shown_refs': [], 'note': 'a level was completed: earlier transitions are outside the shown window'}),
    'after_reset_boundary': (
        'push_to_goal', {'move_limit': 2}, [A(2), A(4)],
        {(2,): 'untested', (4,): 'untested'},
        {'shown_refs': [], 'note': 'the environment reset the level: earlier transitions are outside the window'}),
}


def key_text(key):
    return ','.join(str(v) for v in key)


def build(name):
    env_name, kwargs, actions, probes, extra = SPECS[name]
    env = ENV.ENVIRONMENTS[env_name](**kwargs)
    raws = [env.dispatch(a) for a in actions]
    current = env.observe()
    fixture = {'id': f'fa1-{name}', 'source': 'synthetic', 'partition': 'development', 'environment': env_name,
               'raws': raws, 'legal_actions': list(env.legal_actions), 'current_frame': current['frames'][-1]}
    evaluator = {'mechanism': env.mechanism, 'expected_status': {key_text(k): v for k, v in probes.items()}, **extra}
    return fixture, evaluator


def check_rules(fixture, evaluator):
    problems = []
    if fixture['source'] not in ('synthetic', 'real_game'):
        problems.append('unknown source')
    if fixture['source'] == 'real_game' and 'progress_keys' in evaluator:
        problems.append('a real-game fixture must not assume a uniquely correct next action')
    if fixture['partition'] != 'development':
        problems.append('development material only')
    return problems


def generate():
    fixtures, evaluator_only = [], {}
    for name in SPECS:
        fixture, evaluator = build(name)
        fixtures.append(fixture)
        evaluator_only[fixture['id']] = evaluator
    return {'version': VERSION, 'fixtures': fixtures, 'evaluator_only': evaluator_only}


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    raw = encode(generate())
    if parser.parse_args().check:
        if OUTPUT.read_bytes() != raw:
            raise SystemExit('frozen fixtures differ from a fresh generation')
        print('fixtures match:', hashlib.sha256(raw).hexdigest())
    else:
        OUTPUT.write_bytes(raw)
        print('wrote', OUTPUT.name, hashlib.sha256(raw).hexdigest(), len(raw))
