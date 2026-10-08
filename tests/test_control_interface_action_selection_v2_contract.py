"""Shared-contract isolation, independent formatting/legality scores and historical preservation."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from research.control_interface_action_selection_v1 import probe as BASE
from research.control_interface_action_selection_v2 import probe as P, binding as B, runtime_controls as C
from tests.test_control_interface_action_selection_v2 import records, response, SERVED

ROOT = Path(__file__).resolve().parents[1]


class ContractChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = P.load_cases(ROOT)

    def test_same_contract_follows_unchanged_observation_in_both_arms(self):
        for case in self.cases:
            bodies = [P.request_for(case, arm, SERVED) for arm in P.ARMS]
            for body in bodies:
                content = body['messages'][1]['content']
                payload = P.loads(content)
                self.assertEqual(payload['output_contract'], P.OUTPUT_CONTRACT)
                self.assertGreater(content.index('"output_contract":'), content.index('"observation":'))
                self.assertEqual(body['response_format'], {'type': 'json_object'})
            self.assertEqual(bodies[0]['messages'][0], bodies[1]['messages'][0])
        self.assertIn('JSON integer', P.SYSTEM)
        self.assertNotEqual(P.SYSTEM, BASE.SYSTEM)
        self.assertEqual(P.load_cases(ROOT), BASE.load_cases(ROOT))

    def test_format_does_not_enforce_legality_or_argument_correctness(self):
        illegal = P.validate('{"action":{"action_id":6,"action_data":{"x":3,"y":17}}}', [1])
        self.assertTrue(illegal['format_valid'])
        self.assertFalse(illegal['legal_id'])
        self.assertFalse(illegal['valid'])
        arguments = P.validate('{"action":{"action_id":1,"action_data":{"x":3}}}', [1])
        self.assertTrue(arguments['format_valid'])
        self.assertTrue(arguments['legal_id'])
        self.assertFalse(arguments['arguments'])
        self.assertFalse(arguments['valid'])

    def test_strings_flat_shape_and_template_placeholders_are_not_repaired(self):
        for raw in ['{"action":"ACTION6","action_data":{"x":3,"y":17}}',
                    '{"action":{"action_id":"6","action_data":{"x":3,"y":17}}}',
                    P.OUTPUT_CONTRACT['template']]:
            scored = P.validate(raw, [6])
            self.assertFalse(scored['format_valid'])
            self.assertFalse(scored['valid'])

    def test_conditional_legality_and_argument_denominators_are_explicit(self):
        rows = records(self.cases)
        target = next(r for r in rows if r['arm'] == 'reference')
        target['response'] = response('{"action":{"action_id":0,"action_data":{}}}')
        target['response_sha256'] = hashlib.sha256(target['response'].encode()).hexdigest()
        target['validation'] = {'valid': True, 'legal_id': True}
        scored = P.score(self.cases, rows, SERVED)
        arm = scored['arms']['reference']
        self.assertEqual(arm['legality_given_format_per_response'], {'numerator': 59, 'denominator': 60, 'fraction': 59 / 60})
        self.assertEqual(arm['arguments_given_format_and_legal_per_response']['denominator'], 59)
        self.assertEqual(arm['valid_both_passes'], 29)
        self.assertEqual(arm['format_valid_both_passes'], 30)
        self.assertEqual(scored['paired_contexts']['improved'], 1)

    def test_no_formatted_responses_yields_none_not_a_legality_rate(self):
        rows = records(self.cases)
        for r in rows:
            r['response'] = response('{"action":"ACTION1","action_data":{}}')
            r['response_sha256'] = hashlib.sha256(r['response'].encode()).hexdigest()
        scored = P.score(self.cases, rows, SERVED)
        for arm in P.ARMS:
            self.assertEqual(scored['arms'][arm]['legality_given_format_per_response'],
                             {'numerator': 0, 'denominator': 0, 'fraction': None})
        self.assertEqual(scored['paired_contexts']['neither_valid'], 30)

    def test_step_diagnostics_retain_15_contexts_each(self):
        scored = P.score(self.cases, records(self.cases), SERVED)
        self.assertEqual(set(scored['by_step']), {'0', '10'})
        for step in scored['by_step'].values():
            self.assertEqual(step['contexts'], 15)
            for arm in P.ARMS:
                self.assertEqual(step['arms'][arm], {'valid_both_passes': 15, 'format_valid_both_passes': 15})

    def test_contract_drift_or_v1_authority_is_rejected(self):
        protocol = B.load_protocol(ROOT)
        protocol['experiment']['shared_output_contract_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'output contract drift'):
            C.validate_protocol(ROOT, protocol)
        self.assertNotEqual(B.SCOPE, 'control-interface-action-selection-v1')
        with self.assertRaises(B.LiveRefused):
            B.require_live(ROOT)

    def test_all_baseline_package_bytes_remain_unchanged(self):
        record = json.loads((ROOT / P.PACKAGE / 'derivation.json').read_bytes())
        for name, digest in record['baseline_bindings'].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)
        from scripts.derive_control_interface_v2_tests import build
        self.assertEqual((ROOT / 'tests/test_control_interface_action_selection_v2.py').read_bytes(), build())


if __name__ == '__main__':
    unittest.main()
