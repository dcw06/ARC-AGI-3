import copy
import json
import unittest

from evaluation.phase4_workload import ROOT, build_workload, validate_workload


class Phase4WorkloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workload = build_workload()

    def test_reproducible_exact_request_capture(self):
        self.assertEqual(self.workload, build_workload())
        self.assertEqual(len(self.workload["fixtures"]), 9)
        self.assertEqual(sum(len(v["requests"]) for v in self.workload["assignments"]), 8800)
        for fixture in self.workload["fixtures"]:
            request = fixture["request"]
            self.assertEqual(request["seed"], 0)
            self.assertEqual(request["max_tokens"], 128)
            self.assertEqual(request["chat_template_kwargs"], {"enable_thinking": False})
            self.assertIsNone(fixture["prompt_tokens"])
            self.assertNotIn("opaque-fixture-isolation", json.dumps(request))
            self.assertTrue(all(isinstance(m["content"], str) for m in request["messages"]))

    def test_history_compaction_is_real_parent_payload(self):
        fixture = next(f for f in self.workload["fixtures"] if f["fixture_id"] == "grid64-history79")
        payload = json.loads(fixture["request"]["messages"][1]["content"])["observation"]
        self.assertIn("history_compaction", payload)
        self.assertEqual(len(payload["current_grid"]), 64)
        self.assertFalse(self.workload["model_inference"])

    def test_tampering_or_image_path_change_rejected(self):
        value = copy.deepcopy(self.workload)
        value["fixtures"][0]["request"]["messages"][1]["content"] = []
        with self.assertRaises(ValueError):
            validate_workload(value)

    def test_target_draft_binds_workload_without_execution_authority(self):
        protocol = json.loads((ROOT / "config/phase4_target_profile.json").read_text())
        self.assertEqual(protocol["workload_sha256"], self.workload["workload_sha256"])
        self.assertEqual(protocol["sampling"]["requests"], self.workload["total_requests"])
        self.assertEqual(protocol["status"], "draft_not_authorized")
        self.assertFalse(protocol["execution_authorized"])
        self.assertEqual(protocol["authorized_accelerator_hours"], 0)
        self.assertIsNone(protocol["runner_sha256"])


if __name__ == "__main__":
    unittest.main()
