import copy,json,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
from certification.phase4_closed_loop_v1.evidence import EvidenceStore
from certification.phase4_closed_loop_v1.worker import run_cases
from certification.phase4_closed_loop_v1.fixtures import ScriptedService,adapter_factory
from certification.phase4_closed_loop_v1.trajectory import evaluate_trajectories
from certification.phase4_closed_loop_v1.contract import protocol
from certification.phase4_closed_loop_v1.response_evidence import ResponseValidationError,capture
from certification.phase4_closed_loop_v1.pilot import run

class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.store=EvidenceStore(self.root,'worker');self.start=time.monotonic()
        (self.root/'control').mkdir()
        self.service=ScriptedService()
    def tearDown(self):self.temp.cleanup()
    def execute(self,**kwargs):
        return run_cases(self.service,self.store,kwargs.pop('factory',adapter_factory),
            started=self.start,deadline=self.start+100,cancel=self.root/'control/cancel.json',live=False,**kwargs)
    def state(self):return json.loads((self.root/'worker/state.json').read_text())

    def test_fresh_history_isolated_episodes_and_progress(self):
        state=self.execute();result=evaluate_trajectories(state,self.root/'worker',seconds=120)
        self.assertEqual(len(result['pairs']),15);self.assertEqual(state['requests_started'],90)
        for ep in state['episodes']:
            self.assertEqual(ep['terminal_reason'],'win')
            steps=[json.loads((self.root/'worker'/n).read_text()) for n in ep['steps']]
            payloads=[json.loads(s['request']['messages'][1]['content'])['observation'] for s in steps]
            self.assertEqual([p['history_compaction']['total_transitions'] for p in payloads],[0,1,2])
            self.assertNotEqual(payloads[0]['current_grid'],payloads[1]['current_grid'])
        for ep in result['episodes']:self.assertEqual(ep['level_delta'],1)
        # Independent negative mutations, including a self-consistent altered response/action.
        for mutator in (lambda s:s['episodes'].pop(),
                        lambda s:s['episodes'][1].update(initial_observation=s['episodes'][0]['final_observation']),
                        lambda s:s['episodes'][0].update(client_closed=False),
                        lambda s:s['episodes'][0]['scorecard_receipt'].update(card_id='wrong'),
                        lambda s:s.update(requests_started=89)):
            changed=copy.deepcopy(state);mutator(changed)
            with self.assertRaises((ValueError,KeyError)):evaluate_trajectories(changed,self.root/'worker',seconds=120)
        path=self.root/'worker'/state['episodes'][0]['steps'][0];original=path.read_text();step=json.loads(original)
        for change in (lambda s:s['audit'].update(server_prompt_tokens=11),
                       lambda s:s.update(request_sha256='wrong'),
                       lambda s:s['action'].update(action_id=6,action_data={'x':1,'y':1}),
                       lambda s:s.update(post=s['pre']),
                       lambda s:s.update(ack_seconds=101),
                       lambda s:s['request']['messages'][0].update(content='altered')):
            bad=copy.deepcopy(step);change(bad);path.write_text(json.dumps(bad))
            with self.assertRaises((ValueError,KeyError)):evaluate_trajectories(state,self.root/'worker',seconds=120)
        path.write_text(original)
        observation=self.root/'worker'/step['post'];value=json.loads(observation.read_text());value['levels_completed']=999
        observation.write_text(json.dumps(value))
        with self.assertRaises(ValueError):evaluate_trajectories(state,self.root/'worker',seconds=120)

    def test_token_failure_retained_and_never_dispatched(self):
        def fail(request):
            evidence=capture('{"action":{"action_id":1,"action_data":{}}}',{'request_sha256':'observed',
                'tokenizer_prompt_tokens':10,'server_prompt_tokens':11,'server_completion_tokens':29})
            raise ResponseValidationError('mismatch',evidence)
        with patch.object(self.service,'complete',side_effect=fail) as call,self.assertRaises(ResponseValidationError):self.execute()
        state=self.state();self.assertEqual(call.call_count,1);self.assertEqual(state['dispatch_attempts'],0)
        ep=state['episodes'][0];self.assertTrue(ep['client_closed']);self.assertIsNotNone(ep['scorecard_receipt'])
        step=json.loads((self.root/'worker'/ep['steps'][0]).read_text())
        self.assertEqual(step['audit']['server_prompt_tokens'],11);self.assertIn('response_sha256',step)

    def test_evidence_exhaustion_no_dispatch_or_retry(self):
        from certification.phase4_closed_loop_v1 import evidence
        with patch.dict(evidence.LIMITS,worker=4500),self.assertRaises(ValueError):self.execute()
        self.assertEqual(len(self.service.audit_records),0)

    def test_cancellation_and_late_response_retained(self):
        original=self.service.complete
        def late(request):
            result=original(request);(self.root/'control/cancel.json').touch();return result
        with patch.object(self.service,'complete',side_effect=late),self.assertRaises(TimeoutError):self.execute()
        state=self.state();self.assertEqual(state['dispatch_attempts'],0)
        step=json.loads((self.root/'worker'/state['episodes'][0]['steps'][0]).read_text())
        self.assertIn('response_content',step)

    def test_actual_deadline_before_start(self):
        with self.assertRaises(TimeoutError):self.execute(clock=lambda:self.start+101)
        self.assertEqual(self.state()['requests_started'],0)

    def test_scorecard_cleanup_failure_stops_all_later_episodes(self):
        def factory(row):
            adapter=adapter_factory(row)
            adapter.close_scorecard=lambda:(_ for _ in ()).throw(RuntimeError('injected cleanup'))
            return adapter
        with self.assertRaises(RuntimeError):self.execute(factory=factory)
        self.assertEqual(len(self.state()['episodes']),1);self.assertEqual(self.state()['status'],'failed')

    def test_initial_pair_mismatch_stops_without_second_arm_action(self):
        def factory(row):
            adapter=adapter_factory(row)
            if row['arm']=='no_concrete_examples':
                original=adapter.arcade.make
                def make(*a,**kw):
                    env=original(*a,**kw);env.observation_space.frame[0][:]=9;return env
                adapter.arcade.make=make
            return adapter
        with self.assertRaisesRegex(ValueError,'paired initial'):self.execute(factory=factory)
        self.assertEqual(self.state()['requests_started'],3)

    def test_full_twenty_action_cap_and_repeat_metrics(self):
        def factory(row):
            adapter=adapter_factory(row);original=adapter.arcade.make
            def make(*a,**kw):
                env=original(*a,**kw);env.step=lambda *a,**kw:env.observation_space;return env
            adapter.arcade.make=make;return adapter
        # Count/metric regression uses a fixed clock; deadline enforcement has
        # separate tests and must not make this I/O-heavy case host-speed dependent.
        state=self.execute(factory=factory,clock=lambda:self.start+1)
        result=evaluate_trajectories(state,self.root/'worker',seconds=120)
        self.assertEqual(state['requests_started'],600);self.assertEqual(state['dispatch_attempts'],600)
        for ep in result['episodes']:
            self.assertEqual(ep['longest_streak'],20);self.assertEqual(ep['adjacent_repeats'],19)
            self.assertEqual(ep['canonical_change_rate'],0);self.assertEqual(ep['level_delta'],0)

    def test_live_authority_absent_before_side_effects(self):
        with patch('subprocess.Popen') as proc,self.assertRaises(PermissionError):run(self.root/'out',self.root,mode='live')
        proc.assert_not_called();self.assertFalse((self.root/'out').exists())

    def test_supervised_faults_and_cleanup(self):
        for fault in ('worker','monitor','evidence','cancel'):
            report,result=run(self.root/fault,self.root,seconds=12,reserve=6,fault=fault)
            self.assertFalse(result['passed']);self.assertTrue(report['scratch_removed']);self.assertTrue(report['cleanup_verified'])

if __name__=='__main__':unittest.main()
