"""Connected-path CPU rehearsals: launcher -> supervisor -> worker -> host -> bridge -> runner -> evaluator."""
import json,os,subprocess,tempfile,unittest
from pathlib import Path
from scripts.rehearse_action_effect_history_v1 import rehearse
from scripts.evaluate_action_effect_history_v1 import evaluate_output

BASE=Path.home()/'aeh-rehearsal-tests'

def run_fault(fault):
    BASE.mkdir(exist_ok=True)
    receipt,output=rehearse(fault,2400,tempfile.mkdtemp(dir=BASE))
    outer=json.loads((output/'control/outer.json').read_bytes())
    return receipt,output,outer

class ConnectedRehearsals(unittest.TestCase):
    def assert_cleaned(self,outer,output):
        self.assertTrue(outer['process_groups_exited']);self.assertTrue(outer['independent_gpu_cleanup_verified'])
        self.assertTrue(outer['scratch_removed'])
        first=json.loads((output/'control/first-cell-supervisor-cleanup.json').read_bytes())
        self.assertEqual(first['errors'],[]);self.assertTrue(all(v is True for v in first['groups'].values()))

    def test_normal_completion_and_unchanged_instrumentation(self):
        receipt,output,outer=run_fault('none')
        self.assertEqual(receipt['study_status'],'study_complete_pending_independent_evaluation');self.assert_cleaned(outer,output)
        value=evaluate_output(output,mode='rehearsal')
        self.assertTrue(value['technically_complete'],value['lifecycle_errors']);self.assertTrue(value['evaluation']['replay_passed'])
        self.assertTrue(value['evaluation']['all_six_pairs_complete'])
        # The same scripted model run in-process, without supervisor, bridge or monitor.
        from research.action_effect_history_v1 import runner
        from research.action_effect_history_v1.engine import DevelopmentAdapter
        from research.action_effect_history_v1.service import HistoryModelService
        from research.action_effect_history_v1.rehearsal import ScriptedTransport,FixtureTokenizer
        from research.grounded_action_v1.engine import restore_game_mount
        os.environ.update(AEH_REHEARSAL='1',CUDA_VISIBLE_DEVICES='')
        with tempfile.TemporaryDirectory(dir=BASE) as tmp:
            games=restore_game_mount(Path(tmp)/'games')
            service=HistoryModelService('rehearsal',ScriptedTransport(),tokenizer=FixtureTokenizer(),check_versions=False)
            service.startup_canary()
            class Direct:
                def complete(self,request):
                    result,audit=service.complete(request)
                    return {'content':result.content,'tokenizer_prompt_tokens':audit['tokenizer_prompt_tokens'],
                            'server_prompt_tokens':audit['server_prompt_tokens'],
                            'server_completion_tokens':audit['server_completion_tokens'],'finish_reason':audit['finish_reason']}
            direct=runner.run(Path(tmp)/'run',Direct(),lambda g,a,e:DevelopmentAdapter(g,a,e,games,Path(tmp)/'rec'))
        connected=runner.load(output/'worker/run')
        shape=lambda rep:[(e['episode_id'],[c['request_sha256'] for c in e['calls']],[s['action'] for s in e['steps']]) for e in rep['episodes']]
        self.assertEqual(shape(connected),shape(direct))  # instrumentation leaves requests and actions unchanged

    def test_failures_clean_up_and_keep_honest_evidence(self):
        cases={'model_startup':(None,'failed'),'transport':('technical_failure','failed'),
               'monitor_exit':(None,'failed'),'cancel':('canceled','failed'),'storage':(None,'failed'),
               'surviving_child':('complete','study_complete_pending_independent_evaluation'),
               'invalid_history':('complete','study_complete_pending_independent_evaluation')}
        for fault,(run_status,study) in cases.items():
            with self.subTest(fault=fault):
                receipt,output,outer=run_fault(fault)
                self.assertEqual(receipt['study_status'],study,outer['error']);self.assert_cleaned(outer,output)
                value=evaluate_output(output,mode='rehearsal')
                if study=='failed':
                    self.assertFalse(value['technically_complete'])
                    if run_status is None:self.assertNotEqual(value['run_evidence'].get('run_status'),'complete')
                if run_status is not None and value['run_evidence']['verified']:
                    self.assertEqual(value['run_evidence']['run_status'],run_status)
                if fault=='storage':self.assertFalse(value['run_evidence']['verified'])  # interrupted checkpoint detected
                if fault=='invalid_history':
                    self.assertTrue(value['evaluation']['replay_passed'])
                    self.assertIn('invalid_outputs',value['evaluation']['arm_specific_reliability_differences'])
                    self.assertEqual(value['evaluation']['behaviour_result'],'candidate_worse')
                if fault=='surviving_child':
                    left=subprocess.run(['pgrep','-f','time.sleep\\(600\\)'],capture_output=True,text=True).stdout.strip()
                    self.assertEqual(left,'')

if __name__=='__main__':unittest.main()
