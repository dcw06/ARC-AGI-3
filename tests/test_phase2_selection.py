from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from evaluation.phase2_contract import Phase2ContractError, REGISTERED_TREATMENTS
from evaluation.phase2_selection import validate_treatment_selection


ROOT = Path(__file__).resolve().parents[1]


class Phase2SelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.selection = json.loads(
            (ROOT / "config/phase2_treatment_selection.yaml").read_text()
        )

    def test_no_justified_treatment_decision_passes(self) -> None:
        result = validate_treatment_selection(ROOT)
        self.assertEqual(result["decision"]["selected_treatment"], None)
        self.assertEqual(result["decision"]["activated_treatments"], [])
        self.assertEqual(result["decision"]["allocated_accelerator_hours"], 0.0)

    def test_all_candidates_have_one_conditional_delta_and_full_plan(self) -> None:
        candidates = self.selection["candidates"]
        self.assertEqual(set(candidates), set(REGISTERED_TREATMENTS))
        for candidate in candidates.values():
            self.assertIsNone(candidate["concrete_reproduced_failure"])
            self.assertEqual(candidate["reproduction_status"], "not_reproduced")
            self.assertEqual(candidate["parent_manifest_ref"], "frozen_parent")
            self.assertTrue(candidate["one_feature_delta"])
            self.assertEqual(candidate["disposition"], "not_admitted")

    def test_closed_selection_schema_accepts_record(self) -> None:
        schema = json.loads(
            (ROOT / "config/phase2_treatment_selection_schema.json").read_text()
        )
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(self.selection)

    def test_cannot_select_without_admitted_reproduced_failure(self) -> None:
        value = copy.deepcopy(self.selection)
        value["status"] = "complete_one_treatment_selected"
        value["decision"]["selected_treatment"] = "E2a"
        value["decision"]["conclusion"] = "one_treatment_selected"
        with self.assertRaisesRegex(Phase2ContractError, "no-evidence exit"):
            validate_treatment_selection(ROOT, value)

    def test_cannot_claim_candidate_reproduction_without_record(self) -> None:
        value = copy.deepcopy(self.selection)
        value["candidates"]["E2a"]["reproduction_status"] = "admitted"
        value["candidates"]["E2a"]["concrete_reproduced_failure"] = "P2F-0001"
        with self.assertRaisesRegex(Phase2ContractError, "lacks a valid failure record"):
            validate_treatment_selection(ROOT, value)

    def test_parent_manifest_drift_is_rejected(self) -> None:
        value = copy.deepcopy(self.selection)
        value["frozen_parent"]["feature_manifest_sha256"] = "0" * 64
        with self.assertRaisesRegex(Phase2ContractError, "exact frozen parent"):
            validate_treatment_selection(ROOT, value)

    def test_second_feature_delta_is_rejected(self) -> None:
        value = copy.deepcopy(self.selection)
        value["candidates"]["E2a"]["one_feature_delta"] = "advanced_animation_summary"
        with self.assertRaisesRegex(Phase2ContractError, "registered feature"):
            validate_treatment_selection(ROOT, value)

    def test_retrospective_metric_change_is_rejected(self) -> None:
        value = copy.deepcopy(self.selection)
        value["prospective_plan"]["success_metric"]["minimum_delta_percent"] = 0.0
        with self.assertRaisesRegex(Phase2ContractError, "retrospectively"):
            validate_treatment_selection(ROOT, value)

    def test_excess_compute_is_rejected(self) -> None:
        value = copy.deepcopy(self.selection)
        value["prospective_plan"]["compute_allocation_if_admitted"][
            "maximum_accelerator_hours"
        ] = 5.0
        with self.assertRaisesRegex(Phase2ContractError, "compute allocation"):
            validate_treatment_selection(ROOT, value)


if __name__ == "__main__":
    unittest.main()
