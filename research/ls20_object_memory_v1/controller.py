"""Remember actual object encounters, seek fresh instances, then finish ls20 levels.

Palette, player/cross recognition, five-cell controls and pattern/destination
rules are supplied conventions. Unknown objects have no invented functions.
"""
from copy import deepcopy
import time

from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.policy import check_observation
from research.ls20_knn_path_v1.geometry import player, neighbors
from research.ls20_dfs_v1.planner import DIRECTIONS, terrain_digest
from research.ls20_pattern_goal_v1.patterns import locate_panels, read_panel, compare_patterns
from research.verified_feedback_v1.flow import AdmissionClosed
from .objects import discover
from .memory import EncounterMemory
from .terrain import ObjectTerrain
from .search import iddfs


def contains(obj, center):
    x0,y0,x1,y1 = obj['bbox']
    return x0 <= center[0] <= x1 and y0 <= center[1] <= y1


def floor_evidence(grid, objects, known_colors):
    """Retain the raw k=4 vote; qualify any transfer of traversed-color evidence."""
    sprite = player(grid)
    occupied_player={tuple(p) for p in sprite['cells']}
    excluded = occupied_player | {tuple(p) for o in objects if o.get('visible',True)
                                  or occupied_player & {tuple(p) for p in o['cells']} for p in o['cells']}
    samples = [(x,y,v) for y,row in enumerate(grid[:60]) for x,v in enumerate(row) if (x,y) not in excluded]
    estimate = neighbors(samples, sprite['center'])
    proposed = estimate['predicted_color_id']
    # These roles are supplied palette conventions, not inferred from color.
    reserved = {0,1,4,5,9,12}
    selected, source = proposed, 'current_k4'
    if proposed is None or proposed in reserved:
        tied = {int(c) for c,n in estimate['votes'].items() if n == max(estimate['votes'].values())}
        candidates=tied-reserved
        if proposed in reserved:
            # A dead end can place three nearest cells in a known wall and
            # only one on the traversed floor. Do not relabel the wall vote.
            # Permit prior evidence only if exactly one sampled color is a
            # viable floor under the supplied palette conventions.
            candidates={int(c) for c in estimate['votes']}-reserved
            if len(candidates)!=1:
                return dict(color_id=None, source='unresolved', estimate=estimate)
        transferred = sorted(set(known_colors) & candidates)
        if len(transferred) != 1:
            return dict(color_id=None, source='unresolved', estimate=estimate)
        selected, source = transferred[0], 'previously_traversed_color_hypothesis'
    return dict(color_id=selected, source=source, estimate=estimate)


def run_levels(initial, engine, sink, *, deadline, now=time.monotonic, max_levels=3,
               action_cap=384, per_level_cap=128, memory=None):
    check_observation(initial)
    for value, upper in ((max_levels,10),(action_cap,960),(per_level_cap,192)):
        if type(value) is not int or not 1 <= value <= upper:
            raise ValueError('strict positive level/action limits required')
    store = EncounterMemory() if memory is None else EncounterMemory.from_snapshot(deepcopy(memory))
    # A memory archive is reusable knowledge, never authority to claim a visit
    # in this new run. Each fresh bootstrap receives a new deterministic scope.
    run_scope = digest(dict(initial=initial, prior_memory=store.snapshot()))
    current = None
    reason = error = failure = None
    history, levels, known_colors = [], [], set()
    checks = 0
    scene = None

    def emit(kind, **values):
        sink(deepcopy(dict(kind=kind, **values)))

    def check():
        nonlocal checks
        checks += 1
        overrun = now()-deadline
        if overrun >= 0:
            emit('admission_stop', check_index=checks, overrun_seconds=overrun)
            raise AdmissionClosed('multi-level work admission closed')

    def checkpoint(trigger):
        snapshot = store.snapshot()
        emit('memory_checkpoint', trigger=trigger, memory=snapshot, memory_sha256=digest(snapshot))

    def inventory(obs, level_key, color, panels=None):
        items = discover(obs['grid'], color)
        if panels:
            # Partial player occlusion cannot turn a frozen panel's remaining
            # blue pixels into newly discovered, independent objects.
            frozen = [p['bbox'] for p in panels.values()]
            items = [o for o in items if not (o['kind']=='unknown' and any(
                not (o['bbox'][2]<b[0] or o['bbox'][0]>b[2] or o['bbox'][3]<b[1] or o['bbox'][1]>b[3]) for b in frozen))]
        return store.observe(level_key, items, digest(obs))

    def start_level(obs):
        panels = locate_panels(obs['grid'])
        level_key = f"{run_scope}/level:{obs['levels_completed']}:{digest(obs['grid'])}"
        # Discovery needs a floor convention; exclude the earlier successful
        # color first, then retain the exact current k=4 evidence separately.
        provisional = next(iter(sorted(known_colors)), 3)
        landmarks = [o for o in discover(obs['grid'],provisional) if o['kind']!='unknown']
        evidence = floor_evidence(obs['grid'], landmarks, known_colors)
        if evidence['color_id'] is None:
            raise ValueError('path color unresolved; new model/probe evidence required')
        color = evidence['color_id']
        objects = inventory(obs, level_key, color, panels)
        start = player(obs['grid'])['center']
        terrain = ObjectTerrain(obs['grid'],color,objects)
        dest = panels['destination']
        x0,y0,x1,y1 = dest['bbox']
        value = dict(key=level_key, initial=deepcopy(obs), panels=panels, objects=objects,
            color=color, terrain=terrain, start=tuple(start), started_after=len(history),
            blocked=set(), deferred={}, target=None, contacts=0, visits={}, topology=None, relocations=0,
            route=[], route_goal=None,
            destination_crop=digest([r[x0:x1+1] for r in obs['grid'][y0:y1+1]]))
        emit('level_start', level_key=level_key, observation=obs, objects=objects, color_evidence=evidence)
        checkpoint('level_start')
        return value

    try:
        check(); emit('bootstrap_intent', seed=0); check()
        current = check_observation(engine.bootstrap())
        if current != initial:
            raise ValueError('engine initial observation differs')
        emit('initial', observation=current)
        while True:
            gained = current['levels_completed']-initial['levels_completed']
            if gained >= max_levels:
                reason='requested_levels_complete'; break
            if current['state'] in ('WIN','GAME_OVER'):
                reason='engine_'+current['state'].lower(); break
            if len(history) >= action_cap:
                reason='action_cap'; break
            check()
            if scene is None:
                scene = start_level(current)
            local_count = len(history)-scene['started_after']
            if local_count >= per_level_cap:
                reason='per_level_action_cap'; break
            position = tuple(player(current['grid'])['center'])
            previous_objects = store.objects(scene['key'])
            for obj in previous_objects:
                if not contains(obj,position):
                    store.release(scene['key'],obj['id'])
            panels = scene['panels']
            live_reference = read_panel(current['grid'],panels['reference']['bbox'])
            comparison = compare_patterns(live_reference,panels['destination'])
            emit('pattern_comparison', level_key=scene['key'], after_actions=len(history),
                 reference_pattern=live_reference['pattern'], **comparison)
            if not comparison['clockwise_quarter_turns']:
                reason='pattern_not_rotationally_equivalent'; break
            dest = panels['destination']; x0,y0,x1,y1 = dest['bbox']
            sprite_cells={tuple(p) for p in player(current['grid'])['cells']}
            destination_cells={(x,y) for y in range(y0,y1+1) for x in range(x0,x1+1)}
            if not sprite_cells & destination_cells and scene['destination_crop'] != digest([r[x0:x1+1] for r in current['grid'][y0:y1+1]]):
                reason='destination_pattern_changed'; break
            color_info = floor_evidence(current['grid'],previous_objects,known_colors | {scene['color']})
            if color_info['color_id'] is None:
                reason='path_color_unresolved'; break
            if color_info['color_id'] != scene['color']:
                emit('floor_hypothesis_changed', level_key=scene['key'], before=scene['color'], evidence=color_info)
                scene['color'] = color_info['color_id']; scene['terrain'].set_color(scene['color']); scene['target']=None
            objects = inventory(current,scene['key'],scene['color'],scene['panels'])
            scene['objects'] = objects
            terrain = scene['terrain']; terrain.update(current['grid'],objects)
            # Use observed alignment for every candidate overlay, never a
            # remembered orientation from an earlier board.
            terrain.set_goal(position, patterns_match=comparison['matched'])
            topology = digest(dict(terrain=terrain.topology_sha256(), reference=live_reference['pattern']))
            if topology != scene['topology']:
                scene['blocked'].clear(); scene['deferred'].clear(); scene['visits'].clear(); scene['target']=None
                scene['route']=[]; scene['route_goal']=None
                scene['topology']=topology
            candidates = [o for o in store.priorities(scene['key']) if o['targetability'] and o['kind']!='reference'
                and (o['visible'] or sprite_cells & {tuple(p) for p in o['cells']})
                and all(type(v) is int for v in o['center'])
                and all((o['center'][i]-scene['start'][i])%5==0 for i in (0,1))
                and not (o['kind']=='destination' and not comparison['matched'])]
            fresh = [o for o in candidates if o['encounter_count']==0 and not contains(o,position)
                     and scene['deferred'].get(o['id'])!=topology]
            fresh.sort(key=lambda o:(abs(o['center'][0]-position[0])+abs(o['center'][1]-position[1]),o['id']))
            if scene['target'] is not None:
                selected = next((o for o in fresh if o['id']==scene['target']),None)
                ordered = ([selected] if selected is not None else [])+[o for o in fresh if selected is None or o['id']!=selected['id']]
            else:
                ordered = fresh
            needed = 'destination' if comparison['matched'] else 'cross'
            if scene['contacts'] < 8 or needed!='cross':
                ordered += [o for o in candidates if o['kind']==needed and o['id'] not in {p['id'] for p in ordered}]
            chosen = plan = None
            phase = 'seek_new_object'
            for obj in ordered:
                if scene['deferred'].get(obj['id'])==topology:
                    continue
                if contains(obj,position):
                    if obj['kind']=='destination':
                        reason='destination_reached_without_completion'; break
                    # A known control can need another real entry; reserve the
                    # exit and return, rather than generating duplicate contact.
                    if action_cap-len(history)<2 or per_level_cap-local_count<2:
                        reason='insufficient_reentry_budget'; break
                    exits = [(a,p) for a in DIRECTIONS if (p:=terrain.edge(position,a)) is not None
                             and (position,a) not in scene['blocked']]
                    if not exits:
                        scene['deferred'][obj['id']]=topology; continue
                    a,p = min(exits)
                    plan=dict(status='route',action_ids=[a],centers=[list(position),list(p)],expanded_nodes=0,visited_nodes=2)
                    phase='leave_known_object'
                else:
                    terrain.set_goal(obj['center'],patterns_match=comparison['matched'])
                    if (scene['route_goal']==obj['id'] and scene['route'] and
                            terrain.edge(position,scene['route'][0]) is not None and
                            (position,scene['route'][0]) not in scene['blocked']):
                        centers=[list(position)]
                        for a in scene['route']:
                            dx,dy=DIRECTIONS[a]; p=centers[-1]
                            centers.append([p[0]+dx,p[1]+dy])
                        plan=dict(status='route',action_ids=scene['route'][:],centers=centers,
                                  expanded_nodes=0,visited_nodes=len(centers),retained_DFS_suffix=True)
                    else:
                        plan=iddfs(terrain,position,blocked=scene['blocked'],check=check,
                                   max_depth=min(96,action_cap-len(history),per_level_cap-local_count))
                    if plan['status']!='route':
                        scene['deferred'][obj['id']]=topology
                        emit('object_deferred',level_key=scene['key'],object_id=obj['id'],reason=plan['status'],topology_sha256=topology)
                        continue
                    phase='seek_new_object' if obj['encounter_count']==0 else 'revisit_required_control'
                if len(plan['action_ids'])>min(action_cap-len(history),per_level_cap-local_count):
                    scene['deferred'][obj['id']]=topology
                    emit('object_deferred',level_key=scene['key'],object_id=obj['id'],reason='route_exceeds_remaining_budget',topology_sha256=topology)
                    continue
                chosen=obj; break
            if reason:
                break
            if chosen is None:
                reason='cross_contact_cap' if scene['contacts']>=8 and needed=='cross' else 'no_reachable_object_or_required_control'
                break
            scene['target']=None if phase=='leave_known_object' else chosen['id']
            scene['route_goal']=chosen['id'] if phase!='leave_known_object' else None
            scene['route']=plan['action_ids'][1:] if phase!='leave_known_object' else []
            emit('plan',level_key=scene['key'],goal_object_id=chosen['id'],goal_kind=chosen['kind'],phase=phase,
                 plan=plan,terrain_sha256=terrain_digest(terrain),new_object=chosen['encounter_count']==0)
            action=plan['action_ids'][0]
            if action not in current['legal_actions']:
                raise ValueError('planned action is not legal')
            command=dict(action_id=action,action_data={})
            dx,dy=DIRECTIONS[action]; expected=(position[0]+dx,position[1]+dy)
            before=current
            check(); emit('dispatch_intent',step=len(history),level_key=scene['key'],phase=phase,
                         goal_object_id=chosen['id'],action=command,before_sha256=digest(before)); check()
            after=check_observation(engine.dispatch(deepcopy(command)))
            record=dict(step=len(history),before=deepcopy(before),after=deepcopy(after),action=command)
            history.append(record); current=after
            emit('transition',record=record,transition_sha256=digest(record),phase=phase,goal_object_id=chosen['id'])
            if after['levels_completed'] < before['levels_completed'] or after['levels_completed'] > before['levels_completed']+1:
                raise ValueError('unexpected engine level-counter transition')
            if after['levels_completed']>before['levels_completed']:
                completed=dict(level_key=scene['key'],before=before['levels_completed'],after=after['levels_completed'],
                    actions=len(history)-scene['started_after'],goal_object_id=chosen['id'],before_sha256=digest(before),after_sha256=digest(after))
                levels.append(completed); emit('level_complete',**completed)
                # Counter advancement proves completion, but a replacement
                # image cannot independently certify a hidden final overlap.
                checkpoint('engine_level_complete'); scene=None; continue
            if after['state'] in ('WIN','GAME_OVER'):
                continue
            actual=tuple(player(after['grid'])['center'])
            if actual==position:
                scene['blocked'].add((position,action));scene['target']=None
                scene['route']=[];scene['route_goal']=None
                emit('blocked_edge',level_key=scene['key'],center=list(position),action_id=action)
                continue
            if actual!=expected:
                # The real engine can relocate the player without a reset RPC.
                # Retain the actual transition, but never credit the intended
                # target or infer why it happened. Bound such recoveries.
                scene['relocations']+=1
                emit('observed_relocation',level_key=scene['key'],expected_center=list(expected),
                     actual_center=list(actual),before_sha256=digest(before),after_sha256=digest(after),
                     relocation_count=scene['relocations'],
                     visible_yellow_cells_before=sum(v==11 for row in before['grid'][60:] for v in row),
                     visible_yellow_cells_after=sum(v==11 for row in after['grid'][60:] for v in row))
                checkpoint('observed_relocation')
                scene['target']=None;scene['route']=[];scene['route_goal']=None
                scene['blocked'].clear();scene['deferred'].clear();scene['visits'].clear();scene['topology']=None
                if scene['relocations']>=3:
                    reason='relocation_cap';break
                continue
            known_colors.add(scene['color'])
            after_color=floor_evidence(after['grid'],objects,known_colors)
            after_objects=inventory(after,scene['key'],after_color['color_id'] if after_color['color_id'] is not None else scene['color'],scene['panels'])
            try:
                after_pattern=read_panel(after['grid'],panels['reference']['bbox'])['pattern']
            except ValueError:
                after_pattern=None
            for obj in after_objects:
                if not obj['targetability'] or obj['kind']=='reference' or not contains(obj,actual):
                    continue
                if not {tuple(p) for p in player(after['grid'])['cells']} & {tuple(p) for p in obj['cells']}:
                    continue
                prior=next((o for o in objects if o['id']==obj['id']),None)
                if not obj['visible'] and not (prior and prior['visible']):
                    continue
                encounter=store.record_encounter(scene['key'],obj['id'],digest(before),digest(after),
                    pattern_changes=dict(before=live_reference['pattern'],after=after_pattern),
                    floor_changes=dict(before=scene['color'],after_evidence=floor_evidence(after['grid'],after_objects,known_colors),
                        visible_yellow_cells_before=sum(v==11 for row in before['grid'][60:] for v in row),
                        visible_yellow_cells_after=sum(v==11 for row in after['grid'][60:] for v in row)))
                if encounter is not None:
                    emit('encounter',receipt=encounter)
                    if obj['kind']=='cross':scene['contacts']+=1
                    checkpoint('observed_object_entry')
                    scene['target']=None
                    scene['route']=[];scene['route_goal']=None
            # Bounded failure instead of indefinitely alternating known routes.
            state=(actual,live_reference['pattern'].__repr__(),chosen['id'])
            scene['visits'][state]=scene['visits'].get(state,0)+1
            if scene['visits'][state]>=4:
                reason='repeated_state_cycle'; break
    except AdmissionClosed:
        reason='deadline'
    except BaseException as exc:
        reason,error,failure='exception',type(exc).__name__+': '+str(exc),exc
    try:
        emit('closed',receipt=engine.close())
    except BaseException as exc:
        reason,error,failure='exception',type(exc).__name__+': '+str(exc),exc
    gained=0 if current is None else current['levels_completed']-initial['levels_completed']
    result=dict(reason=reason,error=error,success=gained>=max_levels,levels_completed=None if current is None else current['levels_completed'],
        levels_gained=gained,level_summaries=levels,new_dispatches=len(history),offline_actions_including_reset=1+len(history),
        model_calls=0,memory=store.snapshot(),final_observation=current,lifecycle_certified=False,
        qualification='Supplied-rule visible-object memory and DFS; not unaided VLM solving.')
    emit('summary',**result)
    if failure is not None:
        raise failure
    return result
