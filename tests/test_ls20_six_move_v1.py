"""CPU-only instruction-following contracts; no actual model/provider calls."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.initial_geometry_assistance_v1.geometry import digest
from research.ls20_six_move_v1.flow import run_episode
from research.ls20_six_move_v1.policy import make_request,parse
from research.ls20_six_move_v1.live_runtime import SCOPE,check_authority
from research.ls20_six_move_v1.live_worker import request_plan,study,canary,MODEL
from research.ls20_six_move_v1.audit import audit_study
from research.ls20_six_move_v1.live_contract import verify_inputs
from research.initial_geometry_assistance_v1.live_io import sha

def initial():return dict(grid=[[5]*64 for _ in range(64)],legal_actions=[1,2,3,4],state='NOT_FINISHED',levels_completed=0)
def answer(action=1):return json.dumps(dict(action_id=action,action_data={},predicted_visible_change='unknown'))

class Engine:
    def __init__(self,finish=2,effect=lambda _:None,fail=False):self.count=0;self.finish=finish;self.effect=effect;self.closed=False;self.fail=fail
    def bootstrap(self):self.effect('bootstrap');return initial()
    def dispatch(self,action):
        if self.fail:raise TimeoutError('engine transport failure')
        self.effect('dispatch');self.count+=1;obs=initial();obs['grid'][0][0]=self.count%16
        if self.count==self.finish:obs['levels_completed']=1
        return obs
    def close(self):
        self.effect('close');self.closed=True
        return dict(closed=True,local_scorecard_opened=True,local_scorecard_closed=True,online_calls=0)

class Episode(unittest.TestCase):
    def test_full_directional_actions_not_fixed_candidate_choice(self):
        body=make_request(initial(),initial(),[],'Synthetic controls and rules')
        self.assertEqual(body['max_tokens'],256)
        self.assertNotIn('candidate_choice_v1',json.dumps(body))
        self.assertNotIn('initial_objects',json.dumps(body))
        self.assertEqual(body['messages'][1]['content'][0]['text'],'Synthetic controls and rules')

    def test_images_are_exact_448_board_pngs(self):
        from research.recent_feedback_v1.interface import image_grid
        body=make_request(initial(),initial(),[],'Synthetic controls and rules')
        for item in body['messages'][1]['content']:
            if item['type']=='image_url':self.assertEqual(image_grid(item['image_url']['url']),tuple(map(tuple,initial()['grid'])))

    def test_click_reset_extra_field_and_noninteger_refuse(self):
        for text in ('{}',answer(0),answer(6),answer(True),answer(1).replace('"unknown"','"unknown", "extra": true')):
            with self.subTest(text=text),self.assertRaises(ValueError):parse(text,[1,2,3,4])

    def test_stop_immediately_after_first_completed_level(self):
        engine=Engine();events=[]
        result=run_episode(initial(),'Synthetic rules',engine,lambda _:answer(),events.append,deadline=10,now=lambda:0)
        self.assertTrue(result['level1_passed']);self.assertEqual(engine.count,2);self.assertTrue(engine.closed)
        self.assertEqual(result['reason'],'first_level_complete')

    def test_matching_images_or_text_do_not_create_success(self):
        engine=Engine(finish=999)
        result=run_episode(initial(),'Synthetic rules',engine,lambda _:answer(),lambda _:None,deadline=10,now=lambda:0)
        self.assertFalse(result['level1_passed']);self.assertEqual(engine.count,6);self.assertEqual(result['reason'],'action_cap')

    def test_invalid_answer_stops_without_repair(self):
        engine=Engine();calls=[]
        def complete(_):calls.append(True);return '{}'
        result=run_episode(initial(),'Synthetic rules',engine,complete,lambda _:None,deadline=10,now=lambda:0)
        self.assertEqual(result['reason'],'invalid_answer');self.assertEqual(len(calls),1);self.assertEqual(engine.count,0);self.assertTrue(engine.closed)

    def test_late_answer_never_dispatches(self):
        engine=Engine();clock=[0]
        def complete(_):clock[0]=10;return answer()
        result=run_episode(initial(),'Synthetic rules',engine,complete,lambda _:None,deadline=10,now=lambda:clock[0])
        self.assertEqual(result['reason'],'deadline');self.assertEqual(engine.count,0);self.assertTrue(engine.closed)

    def test_late_final_action_keeps_observed_completion(self):
        engine=Engine(finish=1);clock=[0]
        def sink(event):
            if event['kind']=='transition':clock[0]=10
        result=run_episode(initial(),'Synthetic rules',engine,lambda _:answer(),sink,deadline=10,now=lambda:clock[0])
        self.assertTrue(result['level1_passed']);self.assertEqual(result['reason'],'first_level_complete')

    def test_transport_timeout_is_not_graceful_admission_stop(self):
        engine=Engine(fail=True)
        with self.assertRaisesRegex(TimeoutError,'transport failure'):
            run_episode(initial(),'Synthetic rules',engine,lambda _:answer(),lambda _:None,deadline=10,now=lambda:0)
        self.assertTrue(engine.closed)

    def test_request_history_uses_only_observed_actions(self):
        records=[];engine=Engine()
        run_episode(initial(),'Synthetic rules',engine,lambda _:answer(4),records.append,deadline=10,now=lambda:0)
        bodies=[e['body'] for e in records if e['kind']=='request']
        self.assertEqual(json.loads(bodies[0]['messages'][1]['content'][1]['text'])['executed_actions'],[])
        self.assertEqual(json.loads(bodies[1]['messages'][1]['content'][1]['text'])['executed_actions'],[dict(action_id=4,action_data={})])

    def test_scope_and_missing_authority_refuse(self):
        self.assertEqual((SCOPE['generations'],SCOPE['offline_engine_actions'],SCOPE['local_scorecards']),(7,7,1))
        self.assertEqual(len(request_plan()),7)
        with self.assertRaises(PermissionError):check_authority(None,'0'*64)

class WorkerReplay(unittest.TestCase):
    def test_inputs_bind_instructions_board_and_exact_inventory(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'initial.json').write_text(json.dumps(initial()))
            (root/'instructions.txt').write_text('Synthetic rules')
            frozen=dict(initial_observation_sha256=digest(initial()),instructions_sha256=sha(root/'instructions.txt'))
            import research.ls20_six_move_v1.live_contract as contract
            manifest=dict(schema='ls20_six_move_inputs_v1',protocol_sha256=sha(Path(contract.__file__).with_name('live_protocol.json')),
                          files={n:sha(root/n) for n in ('initial.json','instructions.txt')})
            (root/'manifest.json').write_text(json.dumps(manifest));pin=sha(root/'manifest.json')
            with patch.object(contract,'protocol',return_value=frozen):
                verify_inputs(root,pin)
                (root/'route.txt').write_text('not allowed')
                with self.assertRaises(ValueError):verify_inputs(root,pin)
                (root/'route.txt').unlink()
                (root/'instructions.txt').write_text('Altered rules')
                with self.assertRaises(ValueError):verify_inputs(root,pin)
                manifest['files']['instructions.txt']=sha(root/'instructions.txt')
                (root/'manifest.json').write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):verify_inputs(root,sha(root/'manifest.json'))

    def test_replay_rejects_changed_reply_prompt_and_false_success(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);inputs=root/'inputs';output=root/'output';inputs.mkdir();output.mkdir()
            (inputs/'initial.json').write_text(json.dumps(initial()))
            (inputs/'instructions.txt').write_text('Synthetic rules')
            (inputs/'manifest.json').write_text('{}')
            def call(client,identity,body):
                _,entry=client.ledger.admit(identity);entry.update(outcome='http_200',seconds=0.01)
                return 200,json.dumps(dict(model=MODEL,choices=[dict(message=dict(role='assistant',content='ok' if body==canary() else answer()),finish_reason='stop')],
                    usage=dict(prompt_tokens=100,completion_tokens=10,total_tokens=110))).encode()
            import time
            with patch('research.ls20_six_move_v1.live_worker.verify_inputs'),patch('research.ls20_six_move_v1.audit.verify_inputs'),patch(
                'research.ls20_six_move_v1.live_worker.Client.call',new=call):
                study(dict(inputs=str(inputs),input_manifest_sha256='synthetic',port=1,started=time.monotonic()),output,
                    token_audit=lambda _:100,engine_factory=lambda effect:Engine(effect=effect))
                replay=lambda:audit_study(output,inputs,token_audit=lambda _:100,replay_factory=lambda:Engine())
                result=replay();self.assertTrue(result['level1_passed']);self.assertEqual(result['generations'],3)
                for filename,mutate in (('worker-result.json',lambda v:v['episodes'][0].update(level1_passed=False)),
                                       ('worker-result.json',lambda v:v['ledger']['by_kind'].update(policy=0))):
                    path=output/filename;original=path.read_bytes();value=json.loads(original);mutate(value);path.write_text(json.dumps(value))
                    with self.assertRaises(ValueError):replay()
                    path.write_bytes(original)
                path=output/'ls20-six-move.jsonl';original=path.read_bytes()
                for kind in ('request','response'):
                    events=[json.loads(line) for line in original.splitlines()]
                    event=next(e for e in events if e['kind']==kind)
                    if kind=='request':event['body']['messages'][0]['content']='changed';event['request_sha256']=digest(event['body'])
                    else:event['text']=answer(4)
                    path.write_text(''.join(json.dumps(e)+'\n' for e in events))
                    with self.assertRaises(ValueError):replay()
                    path.write_bytes(original)


class ExplicitRoute(unittest.TestCase):
    def test_model_actions_are_not_replaced_by_requested_route(self):
        engine=Engine(finish=999);executed=[];dispatch=engine.dispatch
        def capture(action):executed.append(action['action_id']);return dispatch(action)
        engine.dispatch=capture
        result=run_episode(initial(),'Left three times then up three times',engine,lambda _:answer(4),lambda _:None,deadline=10,now=lambda:0)
        self.assertEqual(executed,[4]*6)
        self.assertEqual(result['reason'],'action_cap')
        self.assertEqual(result['new_dispatches'],6)

    def test_correct_sequence_stops_after_six_without_a_seventh_reply(self):
        sequence=iter([3,3,3,1,1,1]);engine=Engine(finish=999);events=[]
        result=run_episode(initial(),'Left three times then up three times',engine,lambda _:answer(next(sequence)),events.append,deadline=10,now=lambda:0)
        self.assertEqual([e['action']['action_id'] for e in events if e['kind']=='dispatch_intent'],[3,3,3,1,1,1])
        self.assertEqual((result['model_calls'],result['new_dispatches']),(6,6))
        requests=[e['body'] for e in events if e['kind']=='request']
        self.assertTrue(all(r['messages'][1]['content'][0]['text']=='Left three times then up three times' for r in requests))
        self.assertTrue(all('required_action_id' not in json.dumps(r) for r in requests))

    def test_audit_scores_commands_separately_from_reference_execution(self):
        import time
        import research.ls20_six_move_v1.live_contract as contract
        from contextlib import ExitStack
        for actions in ([3,3,3,1,1,1],[4,4,4,4,4,4]):
            with self.subTest(actions=actions),tempfile.TemporaryDirectory() as folder,ExitStack() as stack:
                root=Path(folder);inputs=root/'inputs';output=root/'output';inputs.mkdir();output.mkdir()
                (inputs/'initial.json').write_text(json.dumps(initial()));(inputs/'instructions.txt').write_text('Synthetic six-move instruction');(inputs/'manifest.json').write_text('{}')
                reference=Engine(finish=999);reference.bootstrap()
                hashes=[digest(reference.dispatch(dict(action_id=a,action_data={}))) for a in [3,3,3,1,1,1]]
                frozen=dict(expected_action_ids=[3,3,3,1,1,1],expected_observation_sha256_by_step=hashes)
                stack.enter_context(patch('research.ls20_six_move_v1.live_worker.verify_inputs'))
                stack.enter_context(patch('research.ls20_six_move_v1.audit.verify_inputs'))
                stack.enter_context(patch.object(contract,'protocol',return_value=frozen))
                position=iter(actions)
                def call(client,identity,body):
                    _,entry=client.ledger.admit(identity);entry.update(outcome='http_200',seconds=0.01)
                    return 200,json.dumps(dict(model=MODEL,choices=[dict(message=dict(role='assistant',content='ok' if body==canary() else answer(next(position))),finish_reason='stop')],usage=dict(prompt_tokens=100,completion_tokens=10,total_tokens=110))).encode()
                stack.enter_context(patch('research.ls20_six_move_v1.live_worker.Client.call',new=call))
                study(dict(inputs=str(inputs),input_manifest_sha256='synthetic',port=1,started=time.monotonic()),output,token_audit=lambda _:100,engine_factory=lambda effect:Engine(finish=999,effect=effect))
                result=audit_study(output,inputs,token_audit=lambda _:100,replay_factory=lambda:Engine(finish=999))
                self.assertTrue(result['route_was_supplied'])
                self.assertEqual(result['executed_action_ids'],actions)
                self.assertEqual(result['command_following_success'],actions==[3,3,3,1,1,1])
                self.assertEqual(result['reference_execution_match'],actions==[3,3,3,1,1,1])
                self.assertFalse(result['level1_passed'])

if __name__=='__main__':unittest.main()
