"""progress_subgoal_v1 frozen decision rules: the committed file keeps its pinned hash and the code still applies it."""
import hashlib
import json
import unittest

from research.progress_subgoal_v1 import rules as R


class FrozenRules(unittest.TestCase):
    def test_file_has_its_pinned_hash(self):
        self.assertEqual(hashlib.sha256(R.FROZEN.read_bytes()).hexdigest(), R.RULES_SHA256)

    def test_code_applies_exactly_the_frozen_rules(self):
        self.assertEqual(R.encode(R.snapshot()), R.FROZEN.read_bytes())

    def test_third_arm_rule_covers_an_unavailable_ws3_result(self):
        rule = json.loads(R.FROZEN.read_bytes())['third_arm_rule']
        self.assertEqual(rule['otherwise'], 'keep_two_arms')
        self.assertIn('WS3 v1 has not run or its result is unavailable', rule['otherwise_explicitly_includes'])

    def test_package_limits_match_the_runtime_authority(self):
        from research.progress_subgoal_v1 import authority, schedule
        limits = json.loads(R.FROZEN.read_bytes())['package_limits']
        self.assertEqual(limits['maximum_reservation_seconds_per_session'], authority.LIMITS['authorized_seconds'])
        self.assertEqual(limits['internal_seconds'], authority.LIMITS['internal_seconds'])
        self.assertEqual(limits['automatic_retries'], authority.LIMITS['automatic_retries'])
        self.assertEqual(limits['maximum_attempts'], authority.LIMITS['maximum_attempts'])
        self.assertEqual((limits['admission_cutoff_seconds'], limits['cleanup_reserve_seconds']),
                         (schedule.ADMISSION_CUTOFF_SECONDS, schedule.CLEANUP_RESERVE_SECONDS))


if __name__ == '__main__':
    unittest.main()
