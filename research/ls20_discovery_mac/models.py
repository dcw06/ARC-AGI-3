"""Conservative M2 prototype. No W1/W2 replacement or invented engine semantics."""
from collections import deque
from copy import deepcopy
from .memory import digest
from .object_effects import object_effects
from .scene import extract_scene


def state_key(observation):
    # Visible-state abstraction; hidden context may falsify it. Never claims Markov sufficiency.
    return digest({k: observation[k] for k in ('state', 'levels_completed', 'legal_actions')} |
                  {'grid': observation['frames'][-1]})


def current(snapshot):
    for t in reversed(snapshot['transitions']):
        if t['outcome']['status'] == 'acknowledged':
            return t['outcome']['post']
    return snapshot['initial']


def check_action(action, observation):
    if type(action) is not dict or set(action) != {'action_id', 'action_data'}:
        raise ValueError('invalid action fields')
    n, data = action['action_id'], action['action_data']
    if type(n) is not int or n not in observation['legal_actions'] or type(data) is not dict:
        raise ValueError('illegal action')
    if n == 6:
        if set(data) != {'x', 'y'} or any(type(v) is not int or not 0 <= v <= 63 for v in data.values()):
            raise ValueError('native x/y required')
    elif data:
        raise ValueError('nonclick actions require empty data')


def fit(snapshot):
    """Rebuild from observed transitions only. No forecast is inserted into memory.

    Edge candidates are exact visible-state transitions. Two independent dispatch
    records support an edge heuristically. Any competing observed outcome retires
    the state/action scope for this segment; more repeats cannot erase it.
    Translation candidates are appearance-scoped suggestions for W1, not simulator rules.
    """
    segment = snapshot['observations'][-1]['segment']
    edges, translations = {}, {}
    before = snapshot['initial']
    obs_by_id = {o['id']: o for o in snapshot['observations']}
    for t in snapshot['transitions']:
        if t['outcome']['status'] != 'acknowledged':
            continue
        after = t['outcome']['post']
        same_segment = (t['segment'] == segment and
                        obs_by_id[t['after_observation_id']]['segment'] == segment)
        if same_segment:
            ref = dict(episode_id=snapshot['episode_id'], segment=segment, transition_id=t['id'])
            scope = digest([state_key(before), t['action']])
            edge = edges.setdefault(scope, dict(id=scope, before=state_key(before),
                action=t['action'], outcomes={}, status='tentative'))
            target = state_key(after)
            edge['outcomes'].setdefault(target, []).append(ref)
            # Multiple returned frames are retained elsewhere; avoid treating transient
            # intermediate displacements as separate action-sized movement evidence.
            if len(after['frames']) == 1:
                effects = object_effects(before['frames'][-1], after['frames'][-1])
                for c in effects['candidates']:
                    if not c['unique_within_candidates'] or c['kind'] not in ('translation_candidate', 'unchanged_mask'):
                        continue
                    key = digest([t['action'], before['state'], c['appearance']])
                    model = translations.setdefault(key, dict(id=key, action=t['action'],
                        state=before['state'], appearance=c['appearance'], outcomes={}, status='tentative'))
                    delta = digest(c['displacement'])
                    model['outcomes'].setdefault(delta, dict(displacement=c['displacement'], evidence=[]))['evidence'].append(ref)
        before = after
    for edge in edges.values():
        edge['status'] = ('contradicted' if len(edge['outcomes']) > 1 else
                          'supported' if len(next(iter(edge['outcomes'].values()))) >= 2 else 'tentative')
    for model in translations.values():
        model['status'] = ('contradicted' if len(model['outcomes']) > 1 else
                           'supported' if len(next(iter(model['outcomes'].values()))['evidence']) >= 2 else 'tentative')
    return deepcopy(dict(version='mac_candidate_models_v1', segment=segment,
                         edges=list(edges.values()), translation_candidates=list(translations.values()),
                         unknown_alternative=True, confidence_kind='uncalibrated_heuristic'))


def predict(snapshot, action):
    if snapshot['suspended']:
        raise ValueError('unknown dispatch outcome: predictions suspended')
    before = current(snapshot)
    check_action(action, before)
    models = fit(snapshot)
    edge = next((e for e in models['edges'] if e['before'] == state_key(before) and e['action'] == action), None)
    supported = edge is not None and edge['status'] == 'supported'
    object_predictions = []
    for region in extract_scene(before['frames'][-1], 'before')['regions']:
        appearance = dict(color=region['color'], shape=region['shape'])
        for model in models['translation_candidates']:
            if (model['status'] == 'supported' and model['action'] == action and
                    model['state'] == before['state'] and model['appearance'] == appearance):
                object_predictions.append(dict(before_region_id=region['id'], model_id=model['id'],
                    displacement=next(iter(model['outcomes'].values()))['displacement'],
                    identity_conditional=True))
    return dict(version='mac_m2_prediction_v1', episode_id=snapshot['episode_id'],
        snapshot_sha256=digest(snapshot), step=len(snapshot['transitions']), action=deepcopy(action),
        model_id=edge['id'] if edge else None,
        predicted_state=next(iter(edge['outcomes'])) if supported else None,
        status='supported_prediction' if supported else 'unknown', unknown_alternative=True,
        object_predictions=object_predictions)


def plan(snapshot, objective, *, horizon=4, max_expansions=100):
    """BFS over supported observed edges, with a host-supplied diagnostic goal.

    No geometric rollout or assumption that a newly observed color is traversable.
    Returns an action prefix, but execution must replan after ONE action.
    """
    if snapshot['suspended']:
        raise ValueError('suspended episode')
    if (type(horizon) is not int or not 0 <= horizon <= 32 or
            type(max_expansions) is not int or not 1 <= max_expansions <= 10000):
        raise ValueError('invalid planning bounds')
    if (type(objective) is not dict or set(objective) != {'kind', 'state_key'} or
            objective['kind'] != 'supplied_diagnostic_goal' or type(objective['state_key']) is not str
            or len(objective['state_key']) != 64 or any(c not in '0123456789abcdef' for c in objective['state_key'])):
        raise ValueError('explicit supplied diagnostic goal required')
    models = fit(snapshot)
    start = state_key(current(snapshot))
    queue, seen, expansions = deque([(start, [], [])]), {start}, 0
    status, actions, ids = 'request_probe', [], []
    while queue:
        node, prefix, path_ids = queue.popleft()
        if node == objective['state_key']:
            status, actions, ids = 'goal_reached' if not prefix else 'plan_found', prefix, path_ids
            break
        if len(prefix) >= horizon:
            continue
        if expansions >= max_expansions:
            status = 'budget_exhausted'
            break
        expansions += 1
        for edge in models['edges']:
            if edge['before'] != node or edge['status'] != 'supported':
                continue
            target = next(iter(edge['outcomes']))
            if target not in seen:
                seen.add(target)
                queue.append((target, prefix+[edge['action']], path_ids+[edge['id']]))
    return deepcopy(dict(version='mac_bounded_plan_v1', snapshot_sha256=digest(snapshot),
        objective=objective, status=status, actions=actions, model_ids=ids,
        expansions=expansions, horizon=horizon, max_expansions=max_expansions,
        execute_prefix_length=min(1, len(actions)), rollout_kind='imagined_from_observed_edges'))
