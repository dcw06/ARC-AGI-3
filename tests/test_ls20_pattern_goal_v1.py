"""Synthetic visible-game checks; no engine internals or model/provider calls."""
from copy import deepcopy
import json
import unittest

from research.initial_geometry_assistance_v1.geometry import digest
from research.ls20_knn_path_v1.geometry import player
from research.ls20_pattern_goal_v1.audit import audit_episode
from research.ls20_pattern_goal_v1.controller import run_episode
from research.ls20_pattern_goal_v1.patterns import compare_patterns, locate_panels, read_panel
from research.ls20_pattern_goal_v1.terrain import SceneTerrain
from tests.test_ls20_pattern_recognition_v1 import ASYMMETRIC, panel, rotate


START=(36,47)
CROSS=(21,32)
DESTINATION=(36,12)
REFERENCE_BBOX=(3,43,12,52)
DESTINATION_BBOX=(33,9,39,15)
DIRECTIONS={1:(0,-5),2:(0,5),3:(-5,0),4:(5,0)}


def glyph(turns):
    value=deepcopy(ASYMMETRIC)
    for _ in range(turns%4):value=rotate(value)
    return value


def make_observation(center=START, *, reference_turns=0, target_turns=1, completed=False,
                     destination_turns=None, extra_panel=False):
    grid=[[3]*64 for _ in range(64)]
    for x,y,color in ((21,31,0),(20,32,1),(21,32,0),(22,32,0),(21,33,1)):
        grid[y][x]=color
    panel(grid,glyph(reference_turns),left=3,top=43,scale=2,margin=2)
    panel(grid,glyph(target_turns if destination_turns is None else destination_turns),
          left=33,top=9,margin=2)
    if extra_panel:panel(grid,ASYMMETRIC,left=50,top=40,margin=1)
    if completed:
        # The next level is allowed to replace every previously recognized object.
        grid=[[4]*64 for _ in range(64)]
    else:
        x,y=center
        for b in range(y-2,y+3):
            for a in range(x-2,x+3):grid[b][a]=12 if b<y else 9
    return dict(grid=grid,legal_actions=[1,2,3,4],state='NOT_FINISHED',
                levels_completed=int(completed))


class VisibleEngine:
    """Small disclosed fixture with observable movement and contact effects."""
    def __init__(self, *, turns=1, rotate_on_contact=True, blocked_moves=0,
                 destination_changes=False, finish=True):
        self.turns=turns;self.reference_turns=0;self.center=START
        self.rotate_on_contact=rotate_on_contact;self.blocked_moves=blocked_moves
        self.destination_changes=destination_changes;self.finish=finish
        self.actions=[];self.closed=False;self.completed=False;self.contacts=0

    def observation(self):
        return make_observation(self.center,reference_turns=self.reference_turns,target_turns=self.turns,
            completed=self.completed,destination_turns=(self.turns+1)%4
            if self.destination_changes and self.actions else None)

    def bootstrap(self):return self.observation()

    def dispatch(self,command):
        if self.completed:raise AssertionError('no action after completed level')
        if command['action_id'] not in DIRECTIONS or command['action_data']:
            raise AssertionError('single directional action required')
        self.actions.append(deepcopy(command))
        if self.blocked_moves:
            self.blocked_moves-=1;return self.observation()
        dx,dy=DIRECTIONS[command['action_id']]
        old=self.center;self.center=(old[0]+dx,old[1]+dy)
        if not (2<=self.center[0]<62 and 2<=self.center[1]<58):
            raise AssertionError('fixture moved outside playable bounds')
        if self.center==CROSS and old!=CROSS:
            self.contacts+=1
            if self.rotate_on_contact:self.reference_turns=(self.reference_turns+1)%4
        if self.finish and self.center==DESTINATION and self.reference_turns==self.turns:
            self.completed=True
        return self.observation()

    def close(self):
        self.closed=True
        return dict(closed=True,local_scorecard_opened=True,local_scorecard_closed=True,online_calls=0)


class Episode(unittest.TestCase):
    def run_case(self,engine,**kwargs):
        events=[]
        result=run_episode(engine.observation(),engine,events.append,deadline=10,now=lambda:0,**kwargs)
        return result,events

    def test_rotates_once_then_reaches_destination_and_stops_on_new_level(self):
        engine=VisibleEngine();result,events=self.run_case(engine)
        self.assertTrue(result['level1_passed']);self.assertEqual(result['reason'],'first_level_complete')
        self.assertEqual(result['cross_contacts'],1);self.assertEqual(engine.contacts,1)
        self.assertEqual(engine.center,DESTINATION);self.assertTrue(engine.closed)
        self.assertEqual(result['new_dispatches'],len(engine.actions))
        self.assertEqual(result['offline_actions_including_reset'],1+len(engine.actions))
        self.assertFalse(result['lifecycle_certified'])
        with self.assertRaises(ValueError):player(result['final_observation']['grid'])
        phases=[e['phase'] for e in events if e['kind']=='dispatch_intent']
        self.assertIn('navigate_cross',phases);self.assertIn('navigate_destination',phases)

    def test_three_rotations_require_leaving_and_reentering_cross(self):
        engine=VisibleEngine(turns=3);result,events=self.run_case(engine)
        self.assertTrue(result['level1_passed']);self.assertEqual(result['cross_contacts'],3)
        self.assertEqual(engine.contacts,3)
        leaving=[e for e in events if e['kind']=='dispatch_intent' and e['phase']=='leave_cross']
        self.assertEqual(len(leaving),2)
        comparisons=result['pattern_comparisons']
        self.assertEqual(comparisons[0]['clockwise_quarter_turns'],[3])
        self.assertTrue(comparisons[-1]['matched'])

    def test_initial_alignment_routes_directly_to_destination_without_cross(self):
        engine=VisibleEngine(turns=0);result,events=self.run_case(engine)
        self.assertTrue(result['level1_passed']);self.assertEqual(result['cross_contacts'],0)
        self.assertTrue(all(e['phase']=='navigate_destination' for e in events if e['kind']=='dispatch_intent'))

    def test_unchanged_reference_stops_after_bounded_cross_contacts(self):
        engine=VisibleEngine(rotate_on_contact=False);result,_=self.run_case(engine)
        self.assertFalse(result['level1_passed'])
        self.assertIn(result['reason'],('cross_contact_cap','reassessment_required'))
        self.assertGreaterEqual(result['cross_contacts'],2);self.assertLessEqual(result['cross_contacts'],4)
        self.assertLessEqual(result['new_dispatches'],40)
        self.assertTrue(engine.closed)

    def test_destination_contact_without_engine_progress_is_not_success(self):
        engine=VisibleEngine(turns=0,finish=False);result,_=self.run_case(engine)
        self.assertEqual(result['reason'],'destination_reached_without_completion')
        self.assertFalse(result['level1_passed']);self.assertTrue(engine.closed)

    def test_observed_destination_mutation_refuses_before_further_actions(self):
        engine=VisibleEngine(destination_changes=True);result,_=self.run_case(engine)
        self.assertEqual(result['reason'],'destination_pattern_changed')
        self.assertFalse(result['level1_passed']);self.assertEqual(result['new_dispatches'],1)

    def test_shifted_destination_with_same_normalized_pattern_refuses(self):
        class ShiftedDestination(VisibleEngine):
            def observation(self):
                observed=super().observation()
                if self.actions:
                    grid=observed['grid']
                    for y in range(9,16):
                        for x in range(33,40):grid[y][x]=5
                    for y,row in enumerate(glyph(self.turns)):
                        for x,value in enumerate(row):grid[11+y][36+x]=9 if value else 5
                return observed
        engine=ShiftedDestination()
        initial=engine.observation()
        result,_=self.run_case(engine)
        old=read_panel(initial['grid'],DESTINATION_BBOX)
        changed=read_panel(engine.observation()['grid'],DESTINATION_BBOX)
        self.assertTrue(compare_patterns(old,changed)['matched'])
        self.assertEqual(result['reason'],'destination_pattern_changed')
        self.assertEqual(result['new_dispatches'],1)

    def test_ambiguous_destination_discovery_refuses_before_bootstrap(self):
        engine=VisibleEngine();initial=make_observation(extra_panel=True)
        with self.assertRaises(ValueError):
            run_episode(initial,engine,lambda _:None,deadline=10,now=lambda:0)
        self.assertFalse(engine.actions)

    def test_off_lattice_destination_refuses(self):
        initial=make_observation();grid=initial['grid']
        for y in range(9,16):
            for x in range(33,40):grid[y][x]=3
        panel(grid,rotate(ASYMMETRIC),left=34,top=9,margin=2)
        with self.assertRaises(ValueError):
            run_episode(initial,VisibleEngine(),lambda _:None,deadline=10,now=lambda:0)

    def test_route_budget_refuses_without_partial_route_dispatch(self):
        engine=VisibleEngine();result,_=self.run_case(engine,action_cap=1)
        self.assertEqual(result['reason'],'route_exceeds_action_budget');self.assertFalse(engine.actions)

    def test_cross_reentry_reserves_return_move(self):
        baseline=VisibleEngine();_,events=self.run_case(baseline)
        contact=next(e['after_actions'] for e in events if e['kind']=='cross_contact')
        engine=VisibleEngine(turns=2);result,_=self.run_case(engine,action_cap=contact+1)
        self.assertEqual(result['reason'],'insufficient_cross_reentry_budget')
        self.assertEqual(result['new_dispatches'],contact);self.assertEqual(engine.center,CROSS)

    def test_two_blocked_moves_trigger_color_reassessment_even_when_confident(self):
        engine=VisibleEngine(blocked_moves=2);requests=[]
        def complete(body):requests.append(body);return '{"path_color_id":3}'
        result,events=self.run_case(engine,assessment={'path_color_id':3},complete=complete)
        self.assertTrue(result['level1_passed']);self.assertEqual(result['reassessments'],1)
        self.assertEqual(len(requests),1);self.assertIn('repeated_blocked_moves',json.dumps(requests[0]))
        self.assertEqual(len([e for e in events if e['kind']=='blocked_edge']),2)

    def test_stall_without_callback_stops_without_fabricating_color(self):
        engine=VisibleEngine(blocked_moves=2);result,_=self.run_case(engine,assessment={'path_color_id':3})
        self.assertEqual(result['reason'],'reassessment_required')
        self.assertEqual(result['new_dispatches'],2);self.assertEqual(result['model_calls'],0)

    def test_late_observed_level_completion_is_retained_without_new_work(self):
        engine=VisibleEngine();events=[];clock=[0]
        def sink(event):
            events.append(event)
            if event['kind']=='transition' and event['record']['after']['levels_completed']:
                clock[0]=10
        result=run_episode(engine.observation(),engine,sink,deadline=10,now=lambda:clock[0])
        self.assertTrue(result['level1_passed']);self.assertEqual(result['reason'],'first_level_complete')
        self.assertFalse(result['lifecycle_certified'])
        self.assertFalse(any(e['kind']=='admission_stop' for e in events))


class Terrain(unittest.TestCase):
    def terrain(self):
        initial=make_observation();destination=locate_panels(initial['grid'])['destination']
        return initial,destination,SceneTerrain(initial['grid'],3,destination)

    def test_destination_overlay_requires_match_and_preserves_other_regions(self):
        initial,destination,terrain=self.terrain()
        self.assertFalse(terrain.clear(DESTINATION))
        terrain.set_goal(DESTINATION,patterns_match=False)
        self.assertFalse(terrain.clear(DESTINATION))
        terrain.set_goal(DESTINATION,patterns_match=True)
        self.assertTrue(terrain.clear(DESTINATION))
        for y in range(43,53):
            for x in range(3,13):self.assertEqual(terrain.grid[y][x],initial['grid'][y][x])
        terrain.set_goal(CROSS,patterns_match=False)
        self.assertFalse(terrain.clear(DESTINATION))

    def test_newly_uncovered_floor_survives_goal_and_color_changes(self):
        initial,destination,terrain=self.terrain()
        after=make_observation((31,47));after['grid'][47][36]=4
        terrain.observe(after['grid'])
        self.assertNotIn((36,47),terrain.assumed);self.assertEqual(terrain.observed[47][36],4)
        terrain.set_goal(DESTINATION,patterns_match=True);terrain.set_goal(CROSS,patterns_match=False)
        terrain.set_color(4);terrain.set_color(3)
        self.assertEqual(terrain.observed[47][36],4);self.assertEqual(terrain.grid[47][36],4)
        self.assertEqual(terrain.grid[47][31],3)

    def test_goal_flags_and_color_types_are_strict(self):
        _,_,terrain=self.terrain()
        for value in (0,1,None,'yes'):
            with self.assertRaises(ValueError):terrain.set_goal(DESTINATION,patterns_match=value)
        for value in (True,None,16):
            with self.assertRaises(ValueError):terrain.set_color(value)


class Replay(unittest.TestCase):
    def evidence(self):
        events=[];engine=VisibleEngine()
        initial=engine.observation()
        result=run_episode(initial,engine,events.append,deadline=10,now=lambda:0)
        return initial,events,result

    def test_reconstructs_full_success_including_new_level_without_model(self):
        initial,events,result=self.evidence()
        replay=audit_episode(initial,events,VisibleEngine,model_enabled=False)
        self.assertTrue(replay['content_replay_verified']);self.assertEqual(replay['result'],result)
        self.assertEqual(replay['new_model_generations'],0);self.assertFalse(replay['lifecycle_certified'])

    def test_mutated_patterns_plans_transitions_or_success_refuse(self):
        initial,events,_=self.evidence()
        for kind in ('pattern_comparison','plan','transition','summary'):
            changed=deepcopy(events);event=next(e for e in changed if e['kind']==kind)
            if kind=='pattern_comparison':event['matched']=not event['matched']
            elif kind=='plan':event['goal'][0]+=5
            elif kind=='transition':
                event['record']['after']['levels_completed']=1
                event['transition_sha256']=digest(event['record'])
            else:event['level1_passed']=False
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                audit_episode(initial,changed,VisibleEngine,model_enabled=False)

    def test_stale_initial_or_different_game_behavior_refuses(self):
        initial,events,_=self.evidence()
        changed=deepcopy(initial);changed['grid'][0][0]=4
        with self.assertRaises(ValueError):audit_episode(changed,events,VisibleEngine,model_enabled=False)
        with self.assertRaises(ValueError):
            audit_episode(initial,events,lambda:VisibleEngine(rotate_on_contact=False),model_enabled=False)

    def test_rebuilds_reassessment_request_and_reuses_reply_without_inference(self):
        initial=make_observation();events=[]
        result=run_episode(initial,VisibleEngine(blocked_moves=2),events.append,assessment={'path_color_id':3},
            complete=lambda _:'{"path_color_id":3}',deadline=10,now=lambda:0)
        replay=audit_episode(initial,events,lambda:VisibleEngine(blocked_moves=2),assessment={'path_color_id':3})
        self.assertEqual(replay['result'],result);self.assertEqual(replay['model_replies_reused'],1)
        changed=deepcopy(events);request=next(e for e in changed if e['kind']=='model_request')
        request['body']['messages'][0]['content']='Changed';request['request_sha256']=digest(request['body'])
        with self.assertRaises(ValueError):
            audit_episode(initial,changed,lambda:VisibleEngine(blocked_moves=2),assessment={'path_color_id':3})

    def test_partial_deadline_episode_replays_and_retains_observed_action(self):
        initial=make_observation();events=[];clock=[0]
        def sink(event):
            events.append(event)
            if event['kind']=='transition':clock[0]=10
        result=run_episode(initial,VisibleEngine(),sink,deadline=10,now=lambda:clock[0])
        self.assertEqual(result['reason'],'deadline');self.assertEqual(result['new_dispatches'],1)
        replay=audit_episode(initial,events,VisibleEngine,model_enabled=False)
        self.assertEqual(replay['result'],result)


if __name__=='__main__':unittest.main()
