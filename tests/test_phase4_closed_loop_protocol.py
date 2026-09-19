import json,unittest
from pathlib import Path
from scripts.prepare_phase4_closed_loop import prepare
from scripts.prepare_phase4_prompt_probe import variants

ROOT=Path(__file__).resolve().parents[1]

class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.proposal=json.loads((ROOT/'reports/phase4_action_selection_probe_proposal.json').read_text())
        self.protocol,self.budget=prepare(self.proposal,json.loads((ROOT/'config/e1_feature_manifests.yaml').read_text()))

    def test_pairs_and_order_are_matched(self):
        rows=self.protocol['schedule']
        self.assertEqual(len(rows),30)
        self.assertEqual(len({r['episode_id'] for r in rows}),30)
        for i in range(15):
            a,b=rows[2*i:2*i+2]
            for key in ('game_id','environment_seed','request_seed','max_decisions','max_dispatch_attempts'):
                self.assertEqual(a[key],b[key])
            self.assertEqual({a['arm'],b['arm']},{'baseline','no_concrete_examples'})
            self.assertEqual(a['arm'],'baseline' if i%2==0 else 'no_concrete_examples')

    def test_prompt_change_is_exact_prior_treatment(self):
        for row in self.proposal['cases']:
            if row['arm']!='baseline':continue
            expected=variants(row['request'])
            for arm in self.protocol['prompts']:
                actual=dict(row['request']);actual['messages']=[dict(m) for m in row['request']['messages']]
                actual['messages'][0]['content']=self.protocol['prompts'][arm]['text']
                self.assertEqual(actual,expected[arm])

    def test_budget_arithmetic_and_no_authority(self):
        b=self.budget
        self.assertEqual(sum(r['max_decisions'] for r in self.protocol['schedule']),b['max_policy_calls'])
        self.assertEqual(b['max_total_calls'],b['max_policy_calls']+b['max_canary_calls'])
        self.assertEqual(b['max_total_output_tokens'],b['max_total_calls']*b['max_output_tokens_per_call'])
        self.assertEqual(sum(b['evidence_component_mib'].values()),b['evidence_mib'])
        self.assertEqual(b['absolute_workload_cutoff_seconds']+b['cleanup_reserve_seconds'],b['internal_seconds'])
        self.assertLess(b['internal_seconds'],b['proposed_provider_seconds'])
        self.assertEqual(b['authorized_seconds'],0);self.assertEqual(b['authorized_attempts'],0)
        self.assertIsNone(b['reservation']);self.assertIsNone(self.protocol['source_approval'])
        self.assertEqual(self.protocol['policy_fallbacks'],0)

if __name__=='__main__':unittest.main()
