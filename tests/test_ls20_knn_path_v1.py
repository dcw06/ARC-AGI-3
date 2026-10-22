"""No model or provider calls: visible geometry, abstention, actions and replay."""
from copy import deepcopy
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from research.initial_geometry_assistance_v1.geometry import digest
from research.ls20_knn_path_v1.geometry import context, neighbors, player
from research.ls20_knn_path_v1.policy import assess_request, make_request, parse_assessment, ASSESS_SYSTEM
from research.ls20_knn_path_v1.flow import run_episode


def observation(center=(36, 47)):
    grid = [[3]*64 for _ in range(64)]
    for x, y, c in ((21, 31, 0), (20, 32, 1), (21, 32, 0), (22, 32, 0), (21, 33, 1)):
        grid[y][x] = c
    x, y = center
    for b in range(y-2, y+3):
        for a in range(x-2, x+3): grid[b][a] = 12 if b < y else 9
    return dict(grid=grid, legal_actions=[1, 2, 3, 4], state='NOT_FINISHED', levels_completed=0)


def answer(action):
    return json.dumps(dict(action_id=action, action_data={}, predicted_visible_change='unknown'))


class Engine:
    def __init__(self, effect=lambda _: None): self.center=[36,47]; self.effect=effect; self.actions=[]; self.closed=False
    def bootstrap(self): self.effect('bootstrap'); return observation()
    def dispatch(self, action):
        self.effect('dispatch'); self.actions.append(deepcopy(action))
        dx,dy={1:(0,-5),2:(0,5),3:(-5,0),4:(5,0)}[action['action_id']]
        x,y=self.center
        self.center=[min(56,max(6,x+dx)),min(52,max(7,y+dy))]
        return observation(self.center)
    def close(self):
        self.effect('close'); self.closed=True
        return dict(closed=True,local_scorecard_opened=True,local_scorecard_closed=True,online_calls=0)


class Geometry(unittest.TestCase):
    def test_k4_prediction_excludes_entire_initial_sprite(self):
        value=context(observation()['grid'],observation()['grid'])
        self.assertEqual(value['initial_player']['center'],[36,47])
        self.assertEqual(value['target_cross']['center'],[21,32])
        vote=value['initial_floor_estimate']
        self.assertEqual((vote['k'],vote['predicted_color_id'],vote['vote_fraction']),(4,3,1.0))
        excluded={tuple(p) for p in value['initial_player']['cells']+value['target_cross']['cells']}
        self.assertTrue(all((r['x'],r['y']) not in excluded for r in vote['neighbors']))
        self.assertNotIn(12,[r['color_id'] for r in vote['neighbors']])

    def test_even_k_vote_tie_abstains(self):
        for colors in ([3,3,4,4],[1,2,3,4]):
            samples=[(x,y,c) for (x,y),c in zip(((5,4),(4,5),(6,5),(5,6)),colors)]
            vote=neighbors(samples,[5,5])
            self.assertIsNone(vote['predicted_color_id']);self.assertTrue(vote['tied'])

    def test_three_to_one_and_two_to_one_to_one_are_pluralities(self):
        for colors in ([3,3,3,4],[3,3,4,5]):
            self.assertEqual(neighbors([(i,0,c) for i,c in enumerate(colors)],[0,0])['predicted_color_id'],3)

    def test_distance_ties_reproducible_and_samples_strict(self):
        samples=[(3,2,3),(2,3,4),(4,3,3),(3,4,4),(10,10,5)]
        self.assertEqual(neighbors(samples,[3,3]),neighbors(list(reversed(samples)),[3,3]))
        for samples,query in ((samples,[True,3]),(samples[:3],[3,3]),(samples+samples[:1],[3,3])):
            with self.assertRaises(ValueError):neighbors(samples,query)

    def test_current_sprite_pixels_never_enter_training(self):
        first=context(observation()['grid'],observation()['grid'])
        later=context(observation()['grid'],observation((31,47))['grid'])
        self.assertEqual(first['initial_grid_sha256'],later['initial_grid_sha256'])
        self.assertEqual(later['current_floor_estimate']['query'],[31,47])
        self.assertEqual(later['current_floor_estimate']['predicted_color_id'],3)
        self.assertEqual(later['current_floor_estimate']['neighbors'][0]['squared_distance'],0)

    def test_cross_arrival_is_exact_center_not_adjacency(self):
        self.assertFalse(context(observation()['grid'],observation((26,32))['grid'])['cross_reached'])
        self.assertTrue(context(observation()['grid'],observation((21,32))['grid'])['cross_reached'])

    def test_missing_or_extra_geometry_refuses(self):
        g=observation()['grid'];g[45][34]=3
        with self.assertRaises(ValueError):player(g)
        g=observation()['grid'];g[10][10]=12
        with self.assertRaises(ValueError):player(g)


class Requests(unittest.TestCase):
    def test_color_response_strict_and_unknown_allowed(self):
        for value in (3,None,0,15):self.assertEqual(parse_assessment(json.dumps({'path_color_id':value})),{'path_color_id':value})
        for text in ('{}','{"path_color_id":true}','{"path_color_id":16}','{"path_color_id":3,"path_color_id":4}',
                     '{"path_color_id":3,"action_id":1}','{"path_color_id":NaN}'):
            with self.subTest(text=text),self.assertRaises(ValueError):parse_assessment(text)

    def test_estimate_and_vlm_judgment_are_separate(self):
        body=make_request(observation(),observation(),[],'Navigate to the cross',{'path_color_id':4})
        meta=json.loads(body['messages'][1]['content'][1]['text'])
        self.assertEqual(meta['path_assessment']['path_color_id'],4)
        self.assertEqual(meta['geometry_and_knn']['initial_floor_estimate']['predicted_color_id'],3)
        self.assertNotIn('expected_action_ids',json.dumps(body))

    def test_reassessment_contains_observed_movement_not_future_frames(self):
        before=observation();after=observation((31,47))
        history=[dict(step=0,before=before,after=after,action=dict(action_id=3,action_data={}))]
        body=assess_request(before,'Navigate to the cross',after,history)
        meta=json.loads(body['messages'][1]['content'][1]['text'])
        self.assertEqual(meta['probes'][0]['displacement'],[-5,0])
        self.assertTrue(meta['probes'][0]['moved'])


class Episode(unittest.TestCase):
    def test_assess_then_six_uncorrected_actions_reach_cross(self):
        actions=iter([3,3,3,1,1,1]);engine=Engine();requests=[]
        def complete(body):
            requests.append(body)
            return '{"path_color_id":3}' if body['messages'][0]['content']==ASSESS_SYSTEM else answer(next(actions))
        result=run_episode(observation(),'Navigate to the cross',engine,complete,lambda _:None,deadline=10,now=lambda:0)
        self.assertEqual(result['reason'],'cross_reached');self.assertTrue(result['cross_reached'])
        self.assertFalse(result['level1_passed']);self.assertEqual(result['model_calls'],7);self.assertTrue(engine.closed)
        self.assertEqual([a['action_id'] for a in engine.actions],[3,3,3,1,1,1])

    def test_uncertain_explores_eight_then_reassesses_and_navigates(self):
        engine=Engine();actions=iter([4,3]*4+[3,3,3,1,1,1]);modes=[];assessments=[]
        def complete(body):
            if body['messages'][0]['content']==ASSESS_SYSTEM:
                assessments.append(True);return '{"path_color_id":null}' if len(assessments)==1 else '{"path_color_id":3}'
            modes.append(json.loads(body['messages'][1]['content'][1]['text'])['mode'])
            return answer(next(actions))
        result=run_episode(observation(),'Navigate to the cross',engine,complete,lambda _:None,deadline=10,now=lambda:0)
        self.assertTrue(result['cross_reached']);self.assertEqual(len(assessments),2)
        self.assertEqual(modes[:8],['explore_colors']*8);self.assertEqual(modes[8:],['navigate_to_cross']*6)
        self.assertEqual(result['assessment_history'],[{'path_color_id':None},{'path_color_id':3}])

    def test_persistent_uncertainty_is_not_replaced_by_knn_color(self):
        engine=Engine();calls=[]
        def complete(body):
            calls.append(body);return '{"path_color_id":null}' if body['messages'][0]['content']==ASSESS_SYSTEM else answer(4)
        result=run_episode(observation(),'Navigate to the cross',engine,complete,lambda _:None,deadline=10,now=lambda:0)
        self.assertEqual(result['path_assessment'],{'path_color_id':None});self.assertFalse(result['cross_reached'])
        self.assertEqual((len(engine.actions),result['model_calls']),(24,26))

    def test_invalid_assessment_never_dispatches(self):
        engine=Engine()
        result=run_episode(observation(),'Navigate',engine,lambda _: '{}',lambda _:None,deadline=10,now=lambda:0)
        self.assertEqual(result['reason'],'invalid_assessment');self.assertFalse(engine.actions);self.assertTrue(engine.closed)

    def test_late_assessment_never_dispatches(self):
        engine=Engine();clock=[0]
        def complete(_):clock[0]=10;return '{"path_color_id":3}'
        result=run_episode(observation(),'Navigate',engine,complete,lambda _:None,deadline=10,now=lambda:clock[0])
        self.assertEqual(result['reason'],'deadline');self.assertFalse(engine.actions);self.assertTrue(engine.closed)

    def test_late_final_move_keeps_cross_arrival(self):
        engine=Engine();actions=iter([3,3,3,1,1,1]);clock=[0]
        def sink(event):
            if event['kind']=='transition' and event['record']['step']==5:clock[0]=10
        result=run_episode(observation(),'Navigate',engine,lambda b:'{"path_color_id":3}' if b['messages'][0]['content']==ASSESS_SYSTEM else answer(next(actions)),sink,deadline=10,now=lambda:clock[0])
        self.assertEqual(result['reason'],'cross_reached');self.assertTrue(result['cross_reached'])


class TransportReplay(unittest.TestCase):
    def test_full_worker_audit_reconstructs_knn_assessment_and_actions(self):
        from research.ls20_knn_path_v1.live_worker import study,canary,MODEL,request_plan
        from research.ls20_knn_path_v1.audit import audit_study
        from research.ls20_knn_path_v1.live_runtime import SCOPE,check_authority
        self.assertEqual(len(request_plan()),27)
        self.assertEqual((SCOPE['generations'],SCOPE['offline_engine_actions']),(27,25))
        with self.assertRaises(PermissionError):check_authority(None,'0'*64)
        for uncertain in (False,True):
            with self.subTest(uncertain=uncertain),tempfile.TemporaryDirectory() as folder,ExitStack() as stack:
                root=Path(folder);inputs=root/'inputs';output=root/'output';inputs.mkdir();output.mkdir()
                (inputs/'initial.json').write_text(json.dumps(observation()));(inputs/'instructions.txt').write_text('Navigate to the cross');(inputs/'manifest.json').write_text('{}')
                stack.enter_context(patch('research.ls20_knn_path_v1.live_worker.verify_inputs'))
                stack.enter_context(patch('research.ls20_knn_path_v1.audit.verify_inputs'))
                actions=iter(([4,3]*4 if uncertain else [])+[3,3,3,1,1,1]);assessments=[]
                def call(client,identity,body):
                    _,entry=client.ledger.admit(identity);entry.update(outcome='http_200',seconds=0.01)
                    if body==canary():text='ok'
                    elif body['messages'][0]['content']==ASSESS_SYSTEM:
                        assessments.append(True);text='{"path_color_id":null}' if uncertain and len(assessments)==1 else '{"path_color_id":3}'
                    else:text=answer(next(actions))
                    return 200,json.dumps(dict(model=MODEL,choices=[dict(message=dict(role='assistant',content=text),finish_reason='stop')],usage=dict(prompt_tokens=100,completion_tokens=10,total_tokens=110))).encode()
                stack.enter_context(patch('research.ls20_knn_path_v1.live_worker.Client.call',new=call))
                study(dict(inputs=str(inputs),input_manifest_sha256='synthetic',port=1,started=time.monotonic()),output,token_audit=lambda _:100,engine_factory=lambda effect:Engine(effect))
                audit=lambda:audit_study(output,inputs,token_audit=lambda _:100,replay_factory=Engine)
                result=audit();self.assertTrue(result['cross_reached']);self.assertFalse(result['level1_passed'])
                self.assertEqual(result['assessment_generations'],2 if uncertain else 1)
                path=output/'ls20-knn-path.jsonl';original=path.read_bytes()
                events=[json.loads(line) for line in original.splitlines()];req=next(e for e in events if e['kind']=='request')
                req['body']['messages'][0]['content']='Changed color instruction';req['request_sha256']=digest(req['body'])
                path.write_text(''.join(json.dumps(e)+'\n' for e in events))
                with self.assertRaises(ValueError):audit()
                path.write_bytes(original)
                worker=output/'worker-result.json';raw=worker.read_bytes();value=json.loads(raw);value['episodes'][0]['cross_reached']=False;worker.write_text(json.dumps(value))
                with self.assertRaises(ValueError):audit()
                worker.write_bytes(raw)


if __name__=='__main__':unittest.main()
