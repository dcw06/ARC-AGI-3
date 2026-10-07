"""Synthetic competing-explanation challenges; development-only, never game evidence."""
import copy
import hashlib
import json
from pathlib import Path

from research.feedback_action_v1 import environments as ENV
from research.feedback_action_v1 import evidence as ACTION_EFFECT
from research.transition_evidence_v2 import transition as TRANSITIONS

VERSION = 'feedback_action_v1_competing_explanations'
OUTPUT = Path(__file__).with_name('competing_explanations_v1.json')


class _ClickWorld(ENV.Environment):
    legal_actions = (1, 6)
    report_actions = True

    def __init__(self, hypothesis):
        self.hypothesis = hypothesis
        super().__init__()

    def level_frame(self):
        grid = ENV.blank()
        grid[5][5] = ENV.TARGET
        grid[3][3] = ENV.DECOY
        return grid

    def reset_level(self):
        self.frame = self.level_frame()

    def step(self, action):
        accepted = ((self.hypothesis == 'wrong_position' and action['action_id'] == 6 and
                     (action['action_data'].get('x'), action['action_data'].get('y')) == (5, 5)) or
                    (self.hypothesis == 'wrong_action_type' and action['action_id'] == 1 and
                     (action['action_data'].get('x'), action['action_data'].get('y')) == (3, 3)))
        if accepted:
            self.complete_level()
        return [copy.deepcopy(self.frame)]


class _MovementWorld(ENV.Environment):
    legal_actions = (1, 2, 3, 4)
    report_actions = True
    MOVES = ENV.PushToGoal.MOVES

    def __init__(self, hypothesis):
        self.hypothesis = hypothesis
        self.pos = (3, 3)
        super().__init__()

    def level_frame(self):
        grid = ENV.blank()
        grid[2][3] = ENV.WALL
        grid[self.pos[1]][self.pos[0]] = ENV.PLAYER
        return grid

    def reset_level(self):
        self.pos = (3, 3)
        self.frame = self.level_frame()

    def step(self, action):
        if self.hypothesis == 'movement_unavailable':
            return [copy.deepcopy(self.frame)]
        dx, dy = self.MOVES[action['action_id']]
        x, y = self.pos[0] + dx, self.pos[1] + dy
        if self.frame[y][x] != ENV.WALL:
            self.pos = (x, y)
            self.frame = self.level_frame()
        return [copy.deepcopy(self.frame)]


class _NoEffectSwitch(ENV.DelayedSwitch):
    def step(self, action):
        return [copy.deepcopy(self.frame)]


class _LevelShiftWorld(ENV.Environment):
    legal_actions = (1, 2, 3, 4)
    report_actions = True
    MOVES = ENV.PushToGoal.MOVES
    win_levels = 3

    def __init__(self, hypothesis):
        self.hypothesis = hypothesis
        self.pos = (1, 1)
        self.first_level_uses = 0
        super().__init__()

    def level_frame(self):
        grid = ENV.blank(background=self.levels)
        grid[self.pos[1]][self.pos[0]] = ENV.PLAYER
        return grid

    def reset_level(self):
        self.pos = (1, 1)
        self.first_level_uses = 0
        self.frame = self.level_frame()

    def step(self, action):
        action_id = action['action_id']
        if self.levels == 0:
            self.first_level_uses += 1
            if self.first_level_uses == 2:
                self.complete_level()
            else:
                dx, dy = self.MOVES[action_id]
                x, y = self.pos[0] + dx, self.pos[1] + dy
                if self.frame[y][x] != ENV.WALL:
                    self.pos = (x, y)
                    self.frame = self.level_frame()
            return [copy.deepcopy(self.frame)]

        useful_action = 4 if self.hypothesis == 'rule_persists' else 2
        if action_id == useful_action:
            self.complete_level()
        else:
            dx, dy = self.MOVES[action_id]
            x, y = self.pos[0] + dx, self.pos[1] + dy
            if self.frame[y][x] != ENV.WALL:
                self.pos = (x, y)
                self.frame = self.level_frame()
        return [copy.deepcopy(self.frame)]


CASES = {
    'ineffective_click': {
        'question': 'Was the ineffective ACTION6 caused by its coordinate or by its action type?',
        'context': 'ACTION6 at (3, 3) returned no observed change. The available actions are ACTION1 and ACTION6.',
        'hypotheses': [
            {'id': 'wrong_position', 'explanation': 'ACTION6 is appropriate, but (3, 3) is the wrong position.'},
            {'id': 'wrong_action_type', 'explanation': 'The tested position may be appropriate, but ACTION6 is the wrong action type.'},
        ],
        'worlds': ('wrong_position', 'wrong_action_type'),
        'history': (ENV.action(6, 3, 3),),
        'probe': (ENV.action(1, 3, 3),),
        'expected': {'wrong_position': ('no_observed_change',),
                     'wrong_action_type': ('level_completed',)},
        'mechanisms': {'wrong_position': 'ACTION6 at (5, 5) completes the objective.',
                       'wrong_action_type': 'ACTION1 at (3, 3) completes the objective.'},
        'supports': {'no_observed_change': ['wrong_position'],
                     'level_completed': ['wrong_action_type']},
        'unknown': 'A single outcome does not rule out a wrong coordinate plus a wrong type, a precondition, or another hidden mechanic.',
        'carried_rule': None,
    },
    'blocked_vs_unavailable': {
        'question': 'Did ACTION1 fail because this direction is blocked, or because movement is unavailable in this state?',
        'context': 'ACTION1 returned no observed change. The visible board shows a wall immediately above the player.',
        'hypotheses': [
            {'id': 'local_obstacle', 'explanation': 'Movement works, but this attempted direction is blocked by the wall.'},
            {'id': 'movement_unavailable', 'explanation': 'Movement controls are available as inputs but currently have no effect.'},
        ],
        'worlds': ('local_obstacle', 'movement_unavailable'),
        'history': (ENV.action(1),),
        'probe': (ENV.action(4),),
        'expected': {'local_obstacle': ('visible_change_without_level',),
                     'movement_unavailable': ('no_observed_change',)},
        'mechanisms': {'local_obstacle': 'ACTION1 is blocked by the wall; other directions move.',
                       'movement_unavailable': 'No directional movement changes the state.'},
        'supports': {'visible_change_without_level': ['local_obstacle'],
                     'no_observed_change': ['movement_unavailable']},
        'unknown': 'A successful alternate move shows that some movement works; it does not prove the wall was the only cause of the first failure.',
        'carried_rule': None,
    },
    'delayed_effect': {
        'question': 'Do two initial no-change observations mean ACTION5 is ineffective, or is its effect delayed?',
        'context': 'ACTION5 was tried once and returned no observed change. The probe repeats it twice, observing after each call.',
        'hypotheses': [
            {'id': 'delayed_effect', 'explanation': 'Three consecutive ACTION5 calls produce a delayed level effect.'},
            {'id': 'no_effect', 'explanation': 'ACTION5 has no effect in this state.'},
        ],
        'worlds': ('delayed_effect', 'no_effect'),
        'history': (ENV.action(5),),
        'probe': (ENV.action(5), ENV.action(5)),
        'expected': {'delayed_effect': ('no_observed_change', 'level_completed'),
                     'no_effect': ('no_observed_change', 'no_observed_change')},
        'mechanisms': {'delayed_effect': 'The third consecutive ACTION5 completes a level.',
                       'no_effect': 'ACTION5 never changes this environment.'},
        'supports': {"['no_observed_change', 'level_completed']": ['delayed_effect'],
                     "['no_observed_change', 'no_observed_change']": ['no_effect']},
        'unknown': 'Two further no-change outcomes only rule out the listed three-call delay; longer delays or hidden preconditions remain possible.',
        'carried_rule': None,
    },
    'level_rule_shift': {
        'question': 'Should a rule that worked in the prior level be reused after a level boundary?',
        'context': 'Two ACTION4 uses changed the first board and completed level 1. The action-effect window resets at the level boundary.',
        'hypotheses': [
            {'id': 'rule_persists', 'explanation': 'ACTION4 remains the useful action in the new level.'},
            {'id': 'rule_invalidated', 'explanation': 'The old rule was level-specific and no longer predicts progress.'},
        ],
        'worlds': ('rule_persists', 'rule_invalidated'),
        'history': (ENV.action(4), ENV.action(4)),
        'probe': (ENV.action(4),),
        'expected': {'rule_persists': ('level_completed',),
                     'rule_invalidated': ('visible_change_without_level',)},
        'mechanisms': {'rule_persists': 'ACTION4 completes the next level.',
                       'rule_invalidated': 'ACTION2 completes the next level; ACTION4 only moves the player.'},
        'supports': {'level_completed': ['rule_persists'],
                     'visible_change_without_level': ['rule_invalidated']},
        'unknown': 'A changed frame is not proof of objective progress or learning; the new rule still needs prediction and revision checks.',
        'carried_rule': 'Provisional note from level 1: two ACTION4 uses completed the objective. Revalidate after this boundary.',
    },
}


def _environment(case_id, hypothesis_id):
    if case_id == 'ineffective_click':
        return _ClickWorld(hypothesis_id)
    if case_id == 'blocked_vs_unavailable':
        return _MovementWorld(hypothesis_id)
    if case_id == 'delayed_effect':
        return ENV.DelayedSwitch() if hypothesis_id == 'delayed_effect' else _NoEffectSwitch()
    if case_id == 'level_rule_shift':
        return _LevelShiftWorld(hypothesis_id)
    raise KeyError(case_id)


def _dispatch(env, actions, case_id):
    raws = [env.dispatch(copy.deepcopy(action)) for action in actions]
    for raw in raws:
        raw['identity']['episode_id'] = f'challenge-{case_id}'
    return raws


def outcome_class(raw):
    """Classify a probe from transition evidence, not from a hidden mechanism label."""
    if raw['outcome']['status'] != 'acknowledged':
        return 'indeterminate'
    before = raw['before']['levels_completed']
    after = raw['outcome']['after']['levels_completed']
    if after > before:
        return 'level_completed'
    visual = TRANSITIONS.build(raw)['measurements']['visual_effect']['status']
    if visual in ('final_frame_differs', 'changed_then_returned'):
        return 'visible_change_without_level'
    if visual == 'no_observed_change':
        return 'no_observed_change'
    return 'indeterminate'


def run_world(case_id, hypothesis_id):
    case = CASES[case_id]
    env = _environment(case_id, hypothesis_id)
    history = _dispatch(env, case['history'], case_id)
    current = env.observe()
    action_effect_view = ACTION_EFFECT.view(history, current['frames'][-1])
    probe_raws = _dispatch(env, case['probe'], case_id)
    return {'history': history, 'current': current, 'action_effect_view': action_effect_view,
            'probe_raws': probe_raws, 'outcomes': [outcome_class(raw) for raw in probe_raws]}


def _public(case_id, case, run):
    current = run['current']
    return {
        'case_id': case_id,
        'question': case['question'],
        'context': case['context'],
        'current_observation': {'frame': current['frames'][-1], 'levels_completed': current['levels_completed'],
                                'state': current['state'],
                                'available_actions': current.get('available_actions', 'absent')},
        'action_effect_history': run['action_effect_view'],
        'carried_rule': case['carried_rule'],
        'hypotheses': copy.deepcopy(case['hypotheses']),
        'probe_plan': [{'action': copy.deepcopy(action), 'observe_after': True} for action in case['probe']],
        'budget': {'probe_actions': len(case['probe']), 'model_calls': len(case['probe'])},
    }


def generate():
    fixtures = []
    for case_id, case in CASES.items():
        runs = {hypothesis_id: run_world(case_id, hypothesis_id) for hypothesis_id in case['worlds']}
        reference = runs[case['worlds'][0]]
        for hypothesis_id, run in runs.items():
            if not TRANSITIONS.same(reference['history'], run['history']):
                raise ValueError(f'{case_id}/{hypothesis_id}: hypotheses have different observed raw histories')
            if not TRANSITIONS.same(reference['action_effect_view'], run['action_effect_view']):
                raise ValueError(f'{case_id}/{hypothesis_id}: hypothesis is visible before the probe')
            if run['outcomes'] != list(case['expected'][hypothesis_id]):
                raise ValueError(f'{case_id}/{hypothesis_id}: engine outcomes differ from the independent answer key')
        fixtures.append({
            'id': f'fa1-ce-{case_id}',
            'source': 'synthetic',
            'partition': 'development',
            'raws': reference['history'],
            'public': _public(case_id, case, reference),
            'evaluator_only': {
                'mechanisms': copy.deepcopy(case['mechanisms']),
                'expected_outcomes': {key: list(value) for key, value in case['expected'].items()},
                'outcome_supports': copy.deepcopy(case['supports']),
                'remaining_unknown': case['unknown'],
            },
        })
    return {'version': VERSION, 'fixtures': fixtures}


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    data = encode(generate())
    digest = hashlib.sha256(data).hexdigest()
    if parser.parse_args().check:
        if OUTPUT.read_bytes() != data:
            raise SystemExit('competing-explanation fixtures differ from a fresh generation')
        print('fixtures match:', digest)
    else:
        OUTPUT.write_bytes(data)
        print('wrote', OUTPUT.name, digest, len(data))