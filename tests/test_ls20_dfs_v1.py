"""DFS, physical-footprint safety, confident stalls, unknown probes and replay."""
from copy import deepcopy
import json
import unittest
from research.initial_geometry_assistance_v1.geometry import digest
from research.ls20_dfs_v1.planner import Terrain, dfs
from research.ls20_dfs_v1.controller import run_episode
from research.ls20_dfs_v1.audit import audit_episode
from tests.test_ls20_knn_path_v1 import observation, Engine, answer


class Planning(unittest.TestCase):
    def test_initial_image_only_route_ends_at_cross(self):
        terrain=Terrain(observation()['grid'],3)
        route=dfs(terrain,[36,47])
        self.assertEqual(route['status'],'route');self.assertEqual(route['centers'][0],[36,47])
        self.assertEqual(route['centers'][-1],[21,32])
        self.assertEqual(len(route['centers']),len(route['action_ids'])+1)
        self.assertEqual(len({tuple(p) for p in route['centers']}),len(route['centers']))
        for center,action,after in zip(route['centers'],route['action_ids'],route['centers'][1:]):
            self.assertEqual(list(terrain.edge(tuple(center),action)),after)

    def test_goal_already_reached_is_empty_path(self):
        route=dfs(Terrain(observation()['grid'],3),[21,32])
        self.assertEqual(route['status'],'route');self.assertEqual(route['action_ids'],[])

    def test_full_footprint_rejects_center_only_clearance(self):
        terrain=Terrain(observation()['grid'],3)
        terrain.grid[40][38]=4  # Off-center at the upward destination footprint.
        self.assertEqual(terrain.grid[42][36],3)
        self.assertIsNone(terrain.edge((36,47),1))

    def test_intermediate_swept_footprint_cannot_jump_wall(self):
        terrain=Terrain(observation()['grid'],3)
        terrain.grid[44][36]=4  # Destination is y42, but y44 belongs to its footprint.
        self.assertIsNone(terrain.edge((36,47),1))
        # Five-cell stride with 5x5 footprint covers the intervening corridor.
        terrain.grid[44][36]=3;terrain.grid[46][38]=4
        self.assertTrue(terrain.clear((36,42)))
        self.assertIsNone(terrain.edge((36,47),1))

    def test_blacklist_prevents_same_blocked_edge_and_search_terminates(self):
        terrain=Terrain(observation()['grid'],3)
        route=dfs(terrain,[36,47],blocked={((36,47),1)})
        self.assertNotEqual(route['action_ids'][0],1)
        terrain.grid=[[4]*64 for _ in range(64)]
        result=dfs(terrain,[36,47]);self.assertEqual(result['status'],'no_route')
        self.assertEqual(result['visited_nodes'],1)

    def test_node_cap_and_strict_types(self):
        terrain=Terrain(observation()['grid'],3)
        self.assertEqual(dfs(terrain,[36,47],max_nodes=1)['status'],'search_cap')
        for color in (True,None,16):
            with self.assertRaises(ValueError):Terrain(observation()['grid'],color)
        for cap in (True,0,4097):
            with self.assertRaises(ValueError):dfs(terrain,[36,47],max_nodes=cap)

    def test_search_checks_deadline_without_any_real_dispatch(self):
        def expired():raise TimeoutError('search deadline')
        with self.assertRaises(TimeoutError):dfs(Terrain(observation()['grid'],3),[36,47],check=expired)

    def test_new_visible_cells_replace_inferred_start_floor(self):
        terrain=Terrain(observation()['grid'],3)
        after=observation((31,47));after['grid'][47][36]=4
        terrain.observe(after['grid'])
        self.assertEqual(terrain.grid[47][36],4)
        self.assertEqual(terrain.grid[47][31],3)  # Current sprite does not become floor.


class BlockedEngine(Engine):
    def __init__(self,blocks=2):super().__init__();self.remaining=blocks;self.attempts=[]
    def dispatch(self,action):
        self.attempts.append((tuple(self.center),action['action_id']))
        if self.remaining:
            self.remaining-=1;return observation(self.center)
        return super().dispatch(action)


class Control(unittest.TestCase):
    def test_default_knn_plus_dfs_reaches_cross_without_model_calls(self):
        engine=Engine();events=[]
        result=run_episode(observation(),engine,events.append,deadline=10,now=lambda:0)
        self.assertTrue(result['cross_reached']);self.assertEqual(result['model_calls'],0)
        self.assertFalse(result['level1_passed']);self.assertFalse(result['lifecycle_certified'])
        self.assertTrue(engine.closed)
        self.assertTrue(all(e['mode']=='DFS' for e in events if e['kind']=='dispatch_intent'))

    def test_confident_initial_color_still_reassessed_after_two_blocked_moves(self):
        engine=BlockedEngine();calls=[];events=[]
        def complete(body):calls.append(body);return '{"path_color_id":3}'
        result=run_episode(observation(),engine,events.append,assessment={'path_color_id':3},complete=complete,deadline=10,now=lambda:0)
        self.assertTrue(result['cross_reached']);self.assertEqual(result['reassessments'],1)
        self.assertEqual(len(calls),1)
        self.assertIn('repeated_blocked_moves',json.dumps(calls[0]))
        self.assertEqual(result['color_assessments'][0]['answer'],{'path_color_id':3})
        self.assertEqual(result['color_assessments'][1]['trigger'],'repeated_blocked_moves')
        self.assertEqual(len(engine.attempts),len(set(engine.attempts)))

    def test_stall_without_model_callback_stops_instead_of_inventing_answer(self):
        engine=BlockedEngine()
        result=run_episode(observation(),engine,lambda _:None,assessment={'path_color_id':3},deadline=10,now=lambda:0)
        self.assertEqual(result['reason'],'reassessment_required');self.assertEqual(result['new_dispatches'],2)
        self.assertEqual(result['reassessments'],0);self.assertTrue(engine.closed)

    def test_initial_unknown_is_not_silently_replaced_by_knn(self):
        engine=Engine()
        result=run_episode(observation(),engine,lambda _:None,assessment={'path_color_id':None},deadline=10,now=lambda:0)
        self.assertEqual(result['reason'],'path_color_unresolved');self.assertFalse(engine.actions)

    def test_unknown_after_stall_enters_vlm_probe_then_reassesses(self):
        from research.ls20_dfs_v1.policy import color_request
        from research.ls20_knn_path_v1.policy import ASSESS_SYSTEM
        engine=BlockedEngine();assessments=[];probe_actions=iter([2,4,4,1,1,3,3,2]);events=[]
        def complete(body):
            if body['messages'][0]['content']==ASSESS_SYSTEM:
                assessments.append(body);return '{"path_color_id":null}' if len(assessments)==1 else '{"path_color_id":3}'
            return answer(next(probe_actions))
        result=run_episode(observation(),engine,events.append,assessment={'path_color_id':3},complete=complete,deadline=10,now=lambda:0)
        self.assertEqual(result['exploration_actions'],8);self.assertEqual(result['reassessments'],2)
        self.assertEqual([r['answer'] for r in result['color_assessments']],[{'path_color_id':3},{'path_color_id':None},{'path_color_id':3}])
        self.assertTrue(result['cross_reached']);self.assertLessEqual(result['new_dispatches'],24)

    def test_no_usable_route_triggers_reassessment_even_without_blocked_actions(self):
        engine=Engine();requests=[]
        def complete(body):requests.append(body);return '{"path_color_id":3}'
        result=run_episode(observation(),engine,lambda _:None,assessment={'path_color_id':4},complete=complete,deadline=10,now=lambda:0)
        self.assertTrue(result['cross_reached']);self.assertEqual(result['reassessments'],1)
        self.assertIn('no_route',json.dumps(requests[0]))

    def test_unresolved_reassessment_and_requests_are_bounded(self):
        from research.ls20_knn_path_v1.policy import ASSESS_SYSTEM
        engine=BlockedEngine(99)
        def complete(body):return '{"path_color_id":null}' if body['messages'][0]['content']==ASSESS_SYSTEM else answer(1)
        result=run_episode(observation(),engine,lambda _:None,assessment={'path_color_id':3},complete=complete,deadline=10,now=lambda:0)
        self.assertEqual(result['reason'],'reassessment_cap');self.assertLessEqual(result['model_calls'],11)
        self.assertLessEqual(result['exploration_actions'],8);self.assertLessEqual(result['new_dispatches'],24)

    def test_route_longer_than_remaining_budget_is_not_dispatched(self):
        engine=Engine()
        result=run_episode(observation(),engine,lambda _:None,deadline=10,now=lambda:0,action_cap=1)
        self.assertEqual(result['reason'],'route_exceeds_action_budget');self.assertFalse(engine.actions)

    def test_deadline_during_color_reassessment_prevents_dispatch(self):
        engine=BlockedEngine();clock=[0];events=[]
        def complete(_):clock[0]=10;return '{"path_color_id":3}'
        result=run_episode(observation(),engine,events.append,assessment={'path_color_id':3},complete=complete,deadline=10,now=lambda:clock[0])
        self.assertEqual(result['reason'],'deadline');self.assertEqual(len(engine.attempts),2);self.assertTrue(engine.closed)
        self.assertEqual(sum(e['kind']=='admission_stop' for e in events),1)

    def test_goal_observed_at_cutoff_remains_recorded_without_lifecycle_claim(self):
        engine=Engine();clock=[0]
        def sink(event):
            if event['kind']=='transition' and event['record']['after']==observation((21,32)):clock[0]=10
        result=run_episode(observation(),engine,sink,deadline=10,now=lambda:clock[0])
        self.assertTrue(result['cross_reached']);self.assertFalse(result['lifecycle_certified'])

    def test_unexpected_displacement_stops(self):
        engine=Engine();engine.dispatch=lambda _:observation((35,47))
        result=run_episode(observation(),engine,lambda _:None,deadline=10,now=lambda:0)
        self.assertEqual(result['reason'],'unexpected_displacement');self.assertEqual(result['new_dispatches'],1)


class Replay(unittest.TestCase):
    def test_rebuilds_routes_and_all_model_requests_without_inference(self):
        events=[]
        result=run_episode(observation(),BlockedEngine(),events.append,assessment={'path_color_id':3},
            complete=lambda _:'{"path_color_id":3}',deadline=10,now=lambda:0)
        audited=audit_episode(observation(),events,BlockedEngine,assessment={'path_color_id':3})
        self.assertEqual(audited['result'],result);self.assertTrue(audited['content_replay_verified'])
        self.assertEqual(audited['new_model_generations'],0)

    def test_tampered_route_reply_or_false_success_refuses(self):
        events=[]
        run_episode(observation(),BlockedEngine(),events.append,assessment={'path_color_id':3},
            complete=lambda _:'{"path_color_id":3}',deadline=10,now=lambda:0)
        for kind in ('plan','model_request','summary'):
            changed=deepcopy(events);event=next(e for e in changed if e['kind']==kind)
            if kind=='plan':event['plan']['action_ids'][0]=4
            elif kind=='model_request':event['body']['messages'][0]['content']='Changed';event['request_sha256']=digest(event['body'])
            else:event['cross_reached']=False
            with self.subTest(kind=kind),self.assertRaises(ValueError):audit_episode(observation(),changed,BlockedEngine,assessment={'path_color_id':3})

    def test_deadline_with_retained_model_reply_replays(self):
        events=[];clock=[0]
        def complete(_):clock[0]=10;return '{"path_color_id":3}'
        run_episode(observation(),BlockedEngine(),events.append,assessment={'path_color_id':3},complete=complete,deadline=10,now=lambda:clock[0])
        result=audit_episode(observation(),events,BlockedEngine,assessment={'path_color_id':3})
        self.assertEqual(result['result']['reason'],'deadline')


if __name__=='__main__':unittest.main()
