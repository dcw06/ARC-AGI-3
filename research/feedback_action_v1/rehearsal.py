"""CPU rehearsals of the closed loop with scripted model outputs (no model inference of any kind).

The loop is: observe -> evidence view (shared, from transition_evidence_v1) -> adapter request -> scripted model ->
adapter parse -> dispatch if and only if the action is valid -> raw transition. Only the adapter differs between
arms. Scripted outputs exercise plumbing and the evaluator; they say nothing about how a model would behave.

Budgets (all retained in the trajectory, with the stop reason):
- max_actions: dispatched actions; max_decisions: model calls (invalid outputs consume a call, never an action);
- max_completion_tokens: a call is made only if the remaining budget covers the request's max_tokens, so the
  budget is never exceeded. Scripted token counts are declared by the script, not measured by a tokenizer.
"""
import json

from research.feedback_action_v1 import adapter as AD, environments as ENV, evaluate as EV, evidence as E

VERSION = 'feedback_action_v1_rehearsal'
A = ENV.action


def observation(obs, legal):
    """A minimal stand-in for the existing observation pipeline (synthetic environments only)."""
    frame = obs['frames'][-1]
    return {'current_grid': frame, 'grid_shape': [len(frame), len(frame[0])], 'legal_actions': list(legal),
            'levels_completed': obs['levels_completed'], 'state': obs['state']}


def run(env_name, arm, model, budget, env_kwargs=None):
    env = ENV.ENVIRONMENTS[env_name](**(env_kwargs or {}))
    raws, steps, spent, stop = [], [], 0, None
    while stop is None:
        if env.state != 'NOT_FINISHED':
            stop = 'terminal_' + env.state
        elif len(raws) >= budget['max_actions']:
            stop = 'action_budget'
        elif len(steps) >= budget['max_decisions']:
            stop = 'decision_budget'
        if stop:
            break
        obs = env.observe()
        frame = obs['frames'][-1]
        request = AD.build_request(observation(obs, env.legal_actions), E.view(raws, frame), arm)
        limit = budget.get('max_completion_tokens')
        if limit is not None and limit - spent < request['max_tokens']:
            stop = 'completion_budget'
            break
        response = model(request)
        spent += response.get('completion_tokens') or 0
        decision = AD.parse(response, list(env.legal_actions), arm)
        size, base = AD.size(request), AD.size(AD.strip_procedure(request))
        step = {'raws_before': len(raws), 'legal_actions': list(env.legal_actions), 'current_frame': frame,
                'response': response, 'prompt_chars': size['system_chars'] + size['user_chars'],
                'treatment_chars': sum(size.values()) - sum(base.values()), 'adapter_decision': decision,
                'dispatched_index': None}
        if decision['action'] is not None:
            raws.append(env.dispatch(decision['action'], proposal=decision['action']))
            step['dispatched_index'] = len(raws) - 1
        steps.append(step)
    return {'version': VERSION, 'arm': arm, 'environment': env_name, 'budget': budget, 'raws': raws,
            'steps': steps, 'stop_reason': stop}


# ---- scripted models

def block(hypothesis, status, supporting=(), conflicting=(), visual='final_frame_differs', level=False, region=None,
          if_different='a different result would make the hypothesis less likely'):
    return {'hypothesis': hypothesis, 'status': status, 'supporting': [dict(c) for c in supporting],
            'conflicting': [dict(c) for c in conflicting],
            'prediction': {'visual_effect': visual, 'level_completed': level, 'changed_region_xyxy': region},
            'if_different': if_different}


def cite(ref, claim):
    return {'ref': ref, 'claim': claim}


def content(arm, action, procedure=None):
    if arm == 'baseline':
        return json.dumps({'action': action})
    return json.dumps({'hypothesis_test': procedure, 'action': action})


class Scripted:
    """plan(step, observation, view, arm) -> a response dict, or (action, procedure) to serialize for the arm."""

    def __init__(self, arm, plan, tokens=None):
        self.arm, self.plan, self.tokens, self.calls = arm, plan, tokens, 0

    def __call__(self, request):
        payload = json.loads(request['messages'][1]['content'])['observation']
        out = self.plan(self.calls, payload, payload[E.FIELD], self.arm)
        self.calls += 1
        if isinstance(out, tuple):
            text = content(self.arm, *out)
            out = {'content': text, 'finish_reason': 'stop'}
        out.setdefault('completion_tokens', self.tokens if self.tokens is not None else (len(out['content']) + 3) // 4)
        return out


def latest(view, action_id):
    refs = [e for e in view['entries'] if e['action_id'] == action_id]
    return refs[-1] if refs else None


def plan_invalid(step, obs, view, arm):
    good = block('ACTION2 moves the marker', 'new')
    return [{'content': 'ACTION2 please'},
            (A(7), good),
            {'content': content(arm, A(2), good)[:20], 'finish_reason': 'length'},
            (A(2), {**good, 'prediction': {'visual_effect': 'moves'}} if arm == 'candidate' else None),
            (A(2), good)][step]


def plan_references(step, obs, view, arm):
    h = 'ACTION2 moves the marker down'
    return [(A(2), block(h, 'new', supporting=[cite('T0', 'final_frame_differs')])),       # not yet observed
            (A(2), block(h, 'retained', supporting=[cite('T9', 'final_frame_differs')])),  # invented
            (A(2), {**block(h, 'retained'), 'supporting': [{'claim': 'final_frame_differs'}]}),  # missing ref
            (A(4), block(h, 'retained', supporting=[cite('T1', 'final_frame_differs'),
                                                    cite('T0', 'no_observed_change')]))][step]


def plan_delayed(step, obs, view, arm):
    last = latest(view, 5)
    if last is None:
        return A(5), block('ACTION5 has an effect', 'new', visual='final_frame_differs')
    support = [cite(last['ref'], 'no_observed_change'), cite(last['ref'], 'same_state_as_now')]
    return A(5), block('ACTION5 accumulates an invisible effect', 'retained', supporting=support,
                       visual='final_frame_differs', level=True)


def plan_unknown(step, obs, view, arm):
    h = 'ACTION2 moves the marker down'
    return [(A(2), block(h, 'new')),
            (A(2), block(h, 'retained', supporting=[cite('T0', 'final_frame_differs')])),
            (A(3), block(h, 'retained', conflicting=[cite('T1', 'no_observed_change')])),  # unknown read as no change
            (A(4), block(h, 'retained', supporting=[cite('T1', 'outcome_unknown')])),
            (A(4), block(h, 'retained', supporting=[cite('T3', 'dispatch_failed')]))][step]


def plan_boundaries(step, obs, view, arm):
    h = 'moving the marker changes the frame'
    actions = [A(2), A(2), A(2), A(4), A(4), A(2)]
    refs = [[], [cite('T0', 'final_frame_differs')], [cite('T1', 'final_frame_differs')],
            [cite('T1', 'final_frame_differs')],                         # before the reset: not shown
            [cite('T3', 'final_frame_differs')], [cite('T4', 'level_completed')]]  # before the level: not shown
    return actions[step], block(h, 'new' if step == 0 else 'retained', supporting=refs[step])


def plan_budget(step, obs, view, arm):
    return A(2), block('ACTION2 moves the marker down', 'new' if step == 0 else 'retained')


def plan_all_invalid(step, obs, view, arm):
    return {'content': '{"action": '}


def plan_revised(step, obs, view, arm):
    if step == 0:
        return A(1), block('ACTION1 moves the marker up', 'new', visual='final_frame_differs')
    return A(2), block('ACTION1 is blocked here; ACTION2 moves the marker', 'revised',
                       conflicting=[cite('T0', 'no_observed_change'), cite('T0', 'same_state_as_now')])


def plan_ignored(step, obs, view, arm):
    return A(1), block('ACTION1 moves the marker up', 'new' if step == 0 else 'retained', visual='final_frame_differs')


def plan_clicker(step, obs, view, arm):
    clicks = [A(6, 1, 1), A(6, 1, 1), A(6, 2, 5), A(6, 5, 5)]
    blocks = [block('clicking (1,1) changes it', 'new', region=[1, 1, 1, 1]),
              block('clicking (1,1) changes it', 'retained', supporting=[cite('T0', 'no_observed_change')]),
              block('only coloured cells respond', 'revised', conflicting=[cite('T0', 'no_observed_change')],
                    visual='changed_then_returned', region=[2, 5, 2, 5]),
              block('only coloured cells respond', 'retained', supporting=[cite('T2', 'changed_then_returned')],
                    level=True)]
    return clicks[step], blocks[step]


BOTH = ('baseline', 'candidate')
SCENARIOS = {
    # name: (environment, env kwargs, plan, arms, budget, declared tokens per call)
    'invalid_structured_output': ('push_to_goal', {}, plan_invalid, BOTH, {'max_actions': 4, 'max_decisions': 5}, None),
    'missing_and_invented_references': ('push_to_goal', {}, plan_references, ('candidate',),
                                        {'max_actions': 4, 'max_decisions': 4}, None),
    'delayed_effect': ('delayed_switch', {}, plan_delayed, BOTH, {'max_actions': 12, 'max_decisions': 12}, None),
    'unknown_dispatch_outcome': ('push_to_goal', {'faults': {1: 'outcome_unknown', 3: 'failed'}}, plan_unknown,
                                 ('candidate',), {'max_actions': 5, 'max_decisions': 5}, None),
    'reset_and_level_boundaries': ('push_to_goal', {'move_limit': 3}, plan_boundaries, ('candidate',),
                                   {'max_actions': 6, 'max_decisions': 6}, None),
    'action_budget_exhausted': ('push_to_goal', {}, plan_budget, BOTH, {'max_actions': 2, 'max_decisions': 10}, None),
    'completion_budget_exhausted': ('push_to_goal', {}, plan_budget, ('candidate',),
                                    {'max_actions': 10, 'max_decisions': 10, 'max_completion_tokens': 1500}, 300),
    'decision_budget_exhausted_all_invalid': ('push_to_goal', {}, plan_all_invalid, BOTH,
                                              {'max_actions': 10, 'max_decisions': 3}, None),
    'contradiction_revised': ('push_to_goal', {}, plan_revised, ('candidate',), {'max_actions': 2, 'max_decisions': 2},
                              None),
    'contradiction_ignored': ('push_to_goal', {}, plan_ignored, ('candidate',), {'max_actions': 2, 'max_decisions': 2},
                              None),
    'coordinate_actions': ('clicker', {}, plan_clicker, BOTH, {'max_actions': 4, 'max_decisions': 4}, None),
}


def rehearse():
    """Every scenario, every arm: trajectories and independent evaluations. Failures are retained, not filtered."""
    out = {}
    for name, (env_name, kwargs, plan, arms, budget, tokens) in SCENARIOS.items():
        for arm in arms:
            trajectory = run(env_name, arm, Scripted(arm, plan, tokens), budget, kwargs)
            out[(name, arm)] = (trajectory, EV.evaluate_trajectory(trajectory))
    return out


def summary(results=None):
    results = results or rehearse()
    return {f'{name}/{arm}': evaluation['metrics'] for (name, arm), (_, evaluation) in results.items()}


if __name__ == '__main__':
    print(json.dumps(summary(), indent=1, sort_keys=True))
