"""Observe every DFS move; reassess on stalls regardless of prior confidence."""
from collections import deque
from copy import deepcopy
import json
import time
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.policy import check_observation
from research.ls20_knn_path_v1.geometry import context, player
from research.verified_feedback_v1.flow import AdmissionClosed
from .planner import Terrain, dfs, terrain_digest, DIRECTIONS
from .policy import color_request, probe_request, parse_assessment, parse

ACTION_CAP = 24
PROBE_CAP = 8
REASSESSMENT_CAP = 2
MODEL_CALL_CAP = 11  # Initial assessment + two reassessments + eight probes.
STALL_THRESHOLD = 2


def run_episode(initial, engine, sink, *, assessment=None, complete=None,
                deadline, now=time.monotonic, action_cap=ACTION_CAP):
    """CPU-capable controller; a supplied complete callback enables bounded VLM calls.

    With no callback, use a supplied retained color judgment or the kNN vote.
    A stall needing new VLM evidence then stops instead of fabricating an answer.
    The caller owns process cleanup and the full lifecycle deadline; this result
    intentionally never certifies a GPU attempt or claims model-only navigation.
    """
    check_observation(initial)
    if type(action_cap) is not int or not 1 <= action_cap <= ACTION_CAP:
        raise ValueError('action cap must be 1 through 24')
    geometry = context(initial['grid'], initial['grid'])
    target = geometry['target_cross']['center']
    events = sink
    current = None; history = []; assessments = []
    calls = probes = reassessments = blocks = checks = 0
    reason = error = failure = active = None
    terrain = None; route = deque(); blocked = set(); visits = {}
    pending = None

    def emit(kind, **values): events(deepcopy(dict(kind=kind, **values)))
    def check():
        nonlocal checks
        checks += 1
        overrun = now()-deadline
        if overrun >= 0:
            emit('admission_stop', check_index=checks, overrun_seconds=overrun)
            raise AdmissionClosed('DFS new-work admission closed')
    def center(observation): return tuple(player(observation['grid'])['center'])
    def model(body, purpose):
        nonlocal calls
        if complete is None: raise ValueError('model callback unavailable')
        if calls >= MODEL_CALL_CAP: raise ValueError('model request cap exceeded')
        check(); emit('model_request', index=calls, purpose=purpose, body=body, request_sha256=digest(body)); check()
        text = complete(deepcopy(body)); calls += 1
        emit('model_response', index=calls-1, purpose=purpose, text=text); check()
        return text
    def record_color(value, source, trigger):
        nonlocal active, terrain, route
        active = parse_assessment(json.dumps(value))
        assessments.append(dict(answer=deepcopy(active), source=source, trigger=trigger, after_actions=len(history)))
        emit('color_assessment', **assessments[-1])
        route.clear(); terrain = None
        if active['path_color_id'] is not None:
            terrain = Terrain(initial['grid'], active['path_color_id'])
            terrain.observe(current['grid'])

    try:
        check(); emit('bootstrap_intent', seed=0); check()
        current = check_observation(engine.bootstrap())
        if current != initial: raise ValueError('engine start differs from supplied initial observation')
        visits[center(current)] = 1
        emit('initial', observation=current)
        if assessment is not None:
            record_color(assessment, 'supplied_color_assessment', 'initial')
        elif complete is not None:
            record_color(parse_assessment(model(color_request(initial, current, history, 'initial', None), 'initial_color')),
                         'model', 'initial')
        else:
            record_color(dict(path_color_id=geometry['initial_floor_estimate']['predicted_color_id']), 'initial_k4', 'initial')
        while True:
            position = center(current)
            # Preserve observed final progress even if admission closes after the move.
            if list(position) == target: reason = 'cross_reached'; break
            if current['levels_completed'] > 0 or current['state'] == 'WIN': reason = 'first_level_complete'; break
            if current['state'] == 'GAME_OVER': reason = 'game_over'; break
            if len(history) >= action_cap: reason = 'action_cap'; break
            check()
            if pending is not None:
                emit('reassessment_trigger', reason=pending, after_actions=len(history), consecutive_blocked=blocks,
                     previous_assessment=active)
                if complete is None: reason = 'reassessment_required'; break
                if reassessments >= REASSESSMENT_CAP: reason = 'reassessment_cap'; break
                trigger = pending; reassessments += 1; pending = None
                record_color(parse_assessment(model(color_request(initial, current, history, trigger, active), 'color_reassessment')),
                             'model', trigger)
                blocks = 0
            mode = 'DFS'
            if active['path_color_id'] is None:
                if complete is None: reason = 'path_color_unresolved'; break
                if probes >= PROBE_CAP:
                    if reassessments >= REASSESSMENT_CAP: reason = 'path_color_unresolved'; break
                    pending = 'exploration_budget_used'; continue
                body = probe_request(initial, current, history, active)
                answer = parse(model(body, 'color_probe'), current['legal_actions'])
                action = answer['action_id']; probes += 1; mode = 'VLM_color_probe'
            else:
                if route and (terrain.edge(position, route[0]) is None or (position, route[0]) in blocked):
                    route.clear()
                if not route:
                    plan = dfs(terrain, position, blocked=blocked, check=check)
                    emit('plan', after_actions=len(history), plan=plan, terrain_sha256=terrain_digest(terrain),
                         blocked_edges=[[list(p), a] for p, a in sorted(blocked)])
                    if plan['status'] != 'route':
                        if plan['status'] == 'search_cap': reason = 'search_cap'; break
                        if reassessments >= REASSESSMENT_CAP: reason = 'no_route'; break
                        pending = 'no_route'; continue
                    if len(plan['action_ids']) > action_cap-len(history): reason = 'route_exceeds_action_budget'; break
                    route.extend(plan['action_ids'])
                action = route.popleft()
            if action not in current['legal_actions']: raise ValueError('planned action not legal')
            dx, dy = DIRECTIONS[action]
            predicted = (position[0]+dx, position[1]+dy)
            command = dict(action_id=action, action_data={})
            check(); emit('dispatch_intent', step=len(history), mode=mode, action=command,
                          before_sha256=digest(current), expected_center=list(predicted)); check()
            after = check_observation(engine.dispatch(deepcopy(command)))
            actual = center(after)
            record = dict(step=len(history), before=deepcopy(current), after=deepcopy(after), action=command,
                          predicted_visible_change='unknown')
            emit('transition', record=record, transition_sha256=digest(record), mode=mode,
                 actual_displacement=[actual[0]-position[0], actual[1]-position[1]])
            history.append(record); current = after
            if terrain is not None: terrain.observe(after['grid'])
            if actual == position:
                blocked.add((position, action)); route.clear(); blocks += 1
                emit('blocked_edge', center=list(position), action_id=action, consecutive_blocked=blocks)
                if blocks >= STALL_THRESHOLD: pending = 'repeated_blocked_moves'
            elif actual != predicted:
                reason = 'unexpected_displacement'; error = 'observed motion differs from the five-cell movement contract'; break
            else:
                blocks = 0; visits[actual] = visits.get(actual, 0)+1
                if visits[actual] >= 3:
                    route.clear(); pending = 'repeated_position_cycle'
    except AdmissionClosed: reason = 'deadline'
    except BaseException as exc: reason, error, failure = 'exception', type(exc).__name__+': '+str(exc), exc
    try: emit('closed', receipt=engine.close())
    except BaseException as exc: reason, error, failure = 'exception', type(exc).__name__+': '+str(exc), exc
    result = dict(reason=reason, error=error, cross_reached=bool(current and list(center(current)) == target),
                  level1_passed=bool(current and current['levels_completed'] > 0), final_observation=current,
                  model_calls=calls, new_dispatches=len(history), offline_actions_including_reset=1+len(history),
                  color_assessments=assessments, reassessments=reassessments, exploration_actions=probes,
                  blocked_edges=[[list(p), a] for p, a in sorted(blocked)],
                  navigation_controller='DFS with observed feedback; VLM only for colors/probes',
                  lifecycle_certified=False)
    emit('summary', **result)
    if failure is not None: raise failure
    return result
