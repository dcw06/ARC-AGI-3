import copy
import unittest
from scripts.analyze_phase4_action_selection import sequence_metrics
from scripts.prepare_phase4_prompt_probe import variants
from certification.phase4_v13.contract_policy import ContractPolicy


class AnalysisTests(unittest.TestCase):
    def test_repetitions_include_data_and_do_not_cross_clients(self):
        a={'action_id':6,'action_data':{'x':12,'y':34}}
        b={'action_id':6,'action_data':{'x':34,'y':12}}
        result=sequence_metrics([a,a,b,b,b,a])
        self.assertEqual(result,{'actions':6,'adjacent_pairs':5,'adjacent_repeats':3,'distinct_actions':2,'longest_identical_run':3})
        self.assertEqual(sequence_metrics([])['longest_identical_run'],0)
        self.assertEqual(sequence_metrics([a])['adjacent_pairs'],0)

    def test_probe_changes_only_system_prompt(self):
        request={'messages':[{'role':'system','content':ContractPolicy._system_prompt(None)},
            {'role':'user','content':'frozen observation'}], 'response_format':{'frozen':True},
            'temperature':0,'seed':0,'max_tokens':128}
        before=copy.deepcopy(request)
        arms=variants(request)
        self.assertEqual(request,before)
        self.assertEqual(arms['baseline'],request)
        self.assertIn('"x":47,"y":9',arms['relocated_example']['messages'][0]['content'])
        self.assertNotIn('"x":12',arms['no_concrete_examples']['messages'][0]['content'])
        for arm in arms.values():
            arm['messages'][0]['content']=request['messages'][0]['content']
            self.assertEqual(arm,request)


if __name__=='__main__':unittest.main()
