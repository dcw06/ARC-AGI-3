"""Compare visible patterns, interact at the cross, then DFS to the destination."""
from collections import deque
from copy import deepcopy
import json
import time
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.policy import check_observation
from research.ls20_knn_path_v1.geometry import context, player
from research.ls20_dfs_v1.planner import dfs, DIRECTIONS, terrain_digest
from research.verified_feedback_v1.flow import AdmissionClosed
from .patterns import locate_panels, read_panel, compare_patterns
from .terrain import SceneTerrain
from .policy import color_request, probe_request, parse_assessment, parse

ACTION_CAP=40
PROBE_CAP=8
REASSESSMENT_CAP=2
MODEL_CALL_CAP=11
CROSS_CONTACT_CAP=4


def run_episode(initial, engine, sink, *, assessment=None, complete=None,
                deadline, now=time.monotonic, action_cap=ACTION_CAP):
    check_observation(initial)
    if type(action_cap) is not int or not 1<=action_cap<=ACTION_CAP:raise ValueError('action cap must be1 through40')
    initial_geometry=context(initial['grid'],initial['grid'])
    panels=locate_panels(initial['grid'])
    destination=panels['destination'];reference=panels['reference']
    dleft,dtop,dright,dbottom=destination['bbox']
    destination_crop_sha256=digest([row[dleft:dright+1] for row in initial['grid'][dtop:dbottom+1]])
    goal=destination['center']
    if any(int(v)!=v for v in goal):raise ValueError('destination center must lie on native cells')
    goal=[int(v) for v in goal]
    start=initial_geometry['initial_player']['center'];cross=initial_geometry['target_cross']['center']
    if any((goal[i]-start[i])%5 for i in range(2)):raise ValueError('destination is off the observed movement lattice')
    current=None;history=[];assessments=[];comparisons=[]
    calls=probes=reassessments=blocks=checks=contacts=0
    active=terrain=reason=error=failure=pending=None
    route=deque();blocked=set();visits={};last_state=last_phase=None

    def emit(kind,**values):sink(deepcopy(dict(kind=kind,**values)))
    def check():
        nonlocal checks
        checks+=1;overrun=now()-deadline
        if overrun>=0:
            emit('admission_stop',check_index=checks,overrun_seconds=overrun)
            raise AdmissionClosed('pattern-goal admission closed')
    def center(obs):return tuple(player(obs['grid'])['center'])
    def model(body,purpose):
        nonlocal calls
        if complete is None or calls>=MODEL_CALL_CAP:raise ValueError('bounded model callback unavailable')
        check();emit('model_request',index=calls,purpose=purpose,body=body,request_sha256=digest(body));check()
        text=complete(deepcopy(body));calls+=1
        emit('model_response',index=calls-1,purpose=purpose,text=text);check();return text
    def color(value,source,trigger):
        nonlocal active,terrain
        active=parse_assessment(json.dumps(value))
        record=dict(answer=active,source=source,trigger=trigger,after_actions=len(history))
        assessments.append(deepcopy(record));emit('color_assessment',**record);route.clear()
        if active['path_color_id'] is not None:
            if terrain is None:terrain=SceneTerrain(initial['grid'],active['path_color_id'],destination)
            else:terrain.set_color(active['path_color_id'])
            terrain.observe(current['grid'])

    try:
        check();emit('bootstrap_intent',seed=0);check()
        current=check_observation(engine.bootstrap())
        if current!=initial:raise ValueError('engine initial observation differs')
        emit('initial',observation=current,panels=panels)
        if assessment is not None:color(assessment,'supplied_color_assessment','initial')
        elif complete is not None:
            color(parse_assessment(model(color_request(initial,current,history,'initial',None),'initial_color')),'model','initial')
        else:color(dict(path_color_id=initial_geometry['initial_floor_estimate']['predicted_color_id']),'initial_k4','initial')
        while True:
            # A completed level can replace every object. Check the counter first.
            if current['levels_completed']>initial['levels_completed']:
                reason='first_level_complete';break
            if current['state']=='WIN':reason='win_without_level_increment';break
            if current['state']=='GAME_OVER':reason='game_over';break
            if len(history)>=action_cap:reason='action_cap';break
            check();position=center(current)
            live_reference=read_panel(current['grid'],reference['bbox'])
            comparison=compare_patterns(live_reference,destination)
            record=dict(after_actions=len(history),reference_pattern=live_reference['pattern'],
                        destination_pattern=destination['pattern'],**comparison)
            comparisons.append(deepcopy(record));emit('pattern_comparison',**record)
            if not comparison['clockwise_quarter_turns']:
                reason='pattern_not_rotationally_equivalent';break
            left,top,right,bottom=destination['bbox']
            sprite={tuple(p) for p in player(current['grid'])['cells']}
            overlay={(x,y) for y in range(top,bottom+1) for x in range(left,right+1)}
            if not sprite&overlay and (read_panel(current['grid'],destination['bbox'])['pattern']!=destination['pattern'] or
                    digest([row[left:right+1] for row in current['grid'][top:bottom+1]])!=destination_crop_sha256):
                reason='destination_pattern_changed';break
            if pending is not None:
                emit('reassessment_trigger',reason=pending,after_actions=len(history),previous_assessment=active)
                if complete is None:reason='reassessment_required';break
                if reassessments>=REASSESSMENT_CAP:reason='reassessment_cap';break
                trigger=pending;pending=None;reassessments+=1
                color(parse_assessment(model(color_request(initial,current,history,trigger,active),'color_reassessment')),'model',trigger)
                blocks=0
            phase='explore_colors';predicted=None
            if active['path_color_id'] is None:
                if complete is None:reason='path_color_unresolved';break
                if probes>=PROBE_CAP:
                    if reassessments>=REASSESSMENT_CAP:reason='path_color_unresolved';break
                    pending='exploration_budget_used';continue
                answer=parse(model(probe_request(initial,current,history,active,blocked),'color_probe'),current['legal_actions'])
                action=answer['action_id'];probes+=1
                if (position,action) in blocked:
                    emit('probe_refused',center=list(position),action_id=action,reason='previously_blocked_edge')
                    pending='repeated_blocked_probe';continue
            else:
                terrain.observe(current['grid'])
                if comparison['matched']:
                    phase='navigate_destination';next_goal=goal
                elif contacts>=CROSS_CONTACT_CAP:
                    reason='cross_contact_cap';break
                elif list(position)==cross:
                    phase='leave_cross'
                    candidates=[]
                    for a in DIRECTIONS:
                        neighbor=terrain.edge(position,a)
                        if neighbor is not None and (position,a) not in blocked:candidates.append((a,neighbor))
                    if not candidates:pending='no_cross_exit';continue
                    next_goal=list(min(candidates)[1])
                else:phase='navigate_cross';next_goal=cross
                terrain.set_goal(next_goal,patterns_match=comparison['matched'])
                state=digest(dict(topology=terrain.topology_sha256(),reference_pattern=live_reference['pattern']))
                if state!=last_state:
                    route.clear();blocked.clear();visits.clear();last_state=state
                phase_key=(phase,tuple(next_goal))
                if phase_key!=last_phase:route.clear();last_phase=phase_key
                if position==tuple(next_goal) and phase=='navigate_destination':
                    reason='destination_reached_without_completion';break
                if route and (terrain.edge(position,route[0]) is None or (position,route[0]) in blocked):route.clear()
                if not route:
                    plan=dfs(terrain,position,blocked=blocked,check=check)
                    emit('plan',after_actions=len(history),phase=phase,goal=next_goal,patterns_match=comparison['matched'],
                         plan=plan,terrain_sha256=terrain_digest(terrain),blocked_edges=[[list(p),a] for p,a in sorted(blocked)])
                    if plan['status']!='route':
                        if plan['status']=='search_cap':reason='search_cap';break
                        if reassessments>=REASSESSMENT_CAP:reason='no_route';break
                        pending='no_route';continue
                    if len(plan['action_ids'])>action_cap-len(history):reason='route_exceeds_action_budget';break
                    if phase=='leave_cross' and len(history)+len(plan['action_ids'])+1>action_cap:
                        reason='insufficient_cross_reentry_budget';break
                    route.extend(plan['action_ids'])
                if not route:raise ValueError('empty route before goal confirmation')
                action=route.popleft()
            if action not in current['legal_actions']:raise ValueError('planned action is not legal')
            dx,dy=DIRECTIONS[action];predicted=(position[0]+dx,position[1]+dy)
            command=dict(action_id=action,action_data={})
            check();emit('dispatch_intent',step=len(history),phase=phase,action=command,
                         before_sha256=digest(current),expected_center=list(predicted));check()
            after=check_observation(engine.dispatch(deepcopy(command)))
            finished=after['levels_completed']>initial['levels_completed'] or after['state'] in ('WIN','GAME_OVER')
            actual=None if finished else center(after)
            transition=dict(step=len(history),before=deepcopy(current),after=deepcopy(after),action=command,
                            predicted_visible_change='unknown')
            emit('transition',record=transition,transition_sha256=digest(transition),phase=phase,
                 actual_displacement=None if actual is None else [actual[0]-position[0],actual[1]-position[1]])
            history.append(transition);current=after
            if finished:continue
            if actual==position:
                blocked.add((position,action));route.clear();blocks+=1
                emit('blocked_edge',center=list(position),action_id=action,consecutive_blocked=blocks)
                if blocks>=2:pending='repeated_blocked_moves'
            elif actual!=predicted:
                reason='unexpected_displacement';error='movement differs from five-cell contract';break
            else:
                blocks=0
                if list(actual)==cross:
                    contacts+=1;emit('cross_contact',after_actions=len(history),contact=contacts)
                key=(actual,phase,digest(live_reference['pattern']));visits[key]=visits.get(key,0)+1
                if visits[key]>=3:pending='repeated_position_cycle';route.clear()
    except AdmissionClosed:reason='deadline'
    except BaseException as exc:reason,error,failure='exception',type(exc).__name__+': '+str(exc),exc
    try:emit('closed',receipt=engine.close())
    except BaseException as exc:reason,error,failure='exception',type(exc).__name__+': '+str(exc),exc
    result=dict(reason=reason,error=error,level1_passed=bool(current and current['levels_completed']>initial['levels_completed']),
        final_observation=current,new_dispatches=len(history),offline_actions_including_reset=1+len(history),
        model_calls=calls,color_assessments=assessments,reassessments=reassessments,exploration_actions=probes,
        cross_contacts=contacts,pattern_comparisons=comparisons,destination_center=goal,
        navigation_controller='Visible pattern matching plus DFS; VLM color/probe recovery only',lifecycle_certified=False)
    emit('summary',**result)
    if failure is not None:raise failure
    return result
