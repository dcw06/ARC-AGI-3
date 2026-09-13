from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from evaluation.phase2_contract import (
    Phase2ContractError,
    REGISTERED_TREATMENTS,
    canonical_sha256,
    file_sha256,
    validate_contract,
    validate_failure_record,
    validate_treatment_manifest,
)


ROOT = Path(__file__).resolve().parents[1]


class Phase2ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = validate_contract(ROOT)
        cls.contract_sha256 = file_sha256(ROOT / "config/phase2_contract.yaml")

    def failure_record(self) -> dict:
        signature = "a" * 64
        parent = self.contract["parent_policy"]
        return {
            "schema_version": 1,
            "record_type": "phase2_failure",
            "failure_id": "P2F-0001-inter-action-loss",
            "status": "admitted",
            "created_at": "2026-09-13T00:00:00+08:00",
            "taxonomy_id": "inter_action_event_loss",
            "candidate_treatment": "E2a",
            "parent": {
                "policy_id": "E1S-R",
                "frozen": True,
                "operational_config_sha256": parent["operational_config_sha256"],
                "feature_manifest_sha256": parent["feature_manifest_sha256"],
            },
            "development_case": {
                "game_id": "ar25-0c556536",
                "seed": 104729,
            },
            "failure_signature_sha256": signature,
            "diagnosis": {
                "missing_capability": "advanced_inter_action_evidence",
                "action_relevance": "The omitted event distinguishes the next legal action.",
                "excluded_alternative_causes": [
                    "model_protocol_invalidity",
                    "resource_or_queue_failure",
                    "environment_or_transport_failure",
                ],
                "evidence_availability": "exact",
                "evidence_refs": ["transition:17:T3"],
            },
            "consequence": "no_progress_within_frozen_action_window",
            "reproductions": [
                {
                    "run_id": run_id,
                    "game_id": "ar25-0c556536",
                    "seed": 104729,
                    "failure_signature_sha256": signature,
                    "parent_only": True,
                    "policy_visible_evidence_only": True,
                    "evaluator_or_holdout_access": False,
                    "transition_ids": ["transition:17"],
                    "evidence_sha256": evidence,
                }
                for run_id, evidence in (("parent-B1", "b" * 64), ("parent-B2", "c" * 64))
            ],
            "admission": {
                "decision": "passed",
                "evaluated_at": "2026-09-13T01:00:00+08:00",
                "contract_sha256": self.contract_sha256,
                "thresholds_frozen_before_review": True,
                "reasons": ["two matching parent-only reproductions"],
            },
        }

    def treatment_manifest(self, failure: dict) -> dict:
        parent = self.contract["parent_policy"]
        disabled = self.contract["feature_boundary"]["features_that_must_remain_disabled"]
        return {
            "schema_version": 1,
            "record_type": "phase2_treatment_manifest",
            "manifest_id": "P2T-E2a-v1",
            "treatment_id": "E2a",
            "status": "admitted_frozen",
            "contract_sha256": self.contract_sha256,
            "failure_record": {
                "failure_id": failure["failure_id"],
                "record_sha256": canonical_sha256(failure),
                "admission_decision": "passed",
            },
            "parent": {
                "policy_id": "E1S-R",
                "frozen": True,
                "operational_config_sha256": parent["operational_config_sha256"],
                "feature_manifest_sha256": parent["feature_manifest_sha256"],
            },
            "feature_delta": {
                "enabled_feature": "advanced_inter_action_evidence",
                "enabled": True,
                "changed_parent_fields": ["advanced_inter_action_evidence"],
                "disabled_features": disabled,
            },
            "comparison": {
                "execution_mode": "shared_resource_whole_run",
                "game_seed_pairs_sha256": self.contract["development_game_seed_pairs_sha256"],
                "parent_arm": "E1S-R",
                "treatment_arm": "E2a",
                "paired_run_blocks": 2,
                "block_orders": ["parent_then_treatment", "treatment_then_parent"],
                "randomization_unit": "paired_complete_workload_run_block",
                "uncertainty_unit": "paired_complete_workload_run_block",
                "per_game_results": "diagnostic_only_never_independent_resamples",
            },
            "compute_allocation": {
                "target_accelerator": "NvidiaRtxPro6000",
                "maximum_accelerator_hours": 4.0,
                "complete_workload_runs": 4,
                "maximum_game_plays": 60,
                "maximum_actions_per_game": 80,
                "maximum_model_requests": 4800,
                "scored_submissions": 0,
            },
            "decision_rules": {
                "frozen_before_implementation": True,
                "contract_sha256": self.contract_sha256,
                "primary_delta_min_official_RHAE_percent": 0.10,
                "catastrophic_tail_regression_percent": -0.10,
                "reliability_noninferiority_margin_percent": -0.02,
                "familywise_alpha": 0.10,
                "sample_rule": "fixed_two_paired_complete_workload_blocks_no_early_positive_stop",
            },
            "activation": {
                "sequence_position": 1,
                "sequential_predecessor_finalized": True,
                "activated_at": "2026-09-13T02:00:00+08:00",
            },
        }

    def test_contract_freezes_cap_parent_games_compute_and_inactive_state(self) -> None:
        registry = json.loads((ROOT / "config/experiment_registry.yaml").read_text())
        activation = registry["phase_2_activation"]
        self.assertEqual(activation["maximum_activated_treatments"], 2)
        self.assertEqual(activation["evaluation_order"], "strictly_sequential")
        self.assertEqual(activation["activated_treatments"], [])
        self.assertEqual(set(activation["registered_treatments"]), set(REGISTERED_TREATMENTS))
        self.assertEqual(self.contract["parent_policy"]["cell_id"], "E1S-R")
        self.assertEqual(len(self.contract["development_game_seed_pairs"]), 15)
        self.assertEqual(self.contract["compute_allowance"]["maximum_family_accelerator_hours"], 8.0)
        for treatment_id in REGISTERED_TREATMENTS:
            self.assertEqual(
                registry["treatments"][treatment_id]["status"],
                "inactive_pending_reproduced_failure_admission",
            )

    def test_failure_and_manifest_schemas_are_closed_and_registered(self) -> None:
        failure_schema = json.loads((ROOT / "config/phase2_failure_record_schema.json").read_text())
        treatment_schema = json.loads((ROOT / "config/phase2_treatment_manifest_schema.json").read_text())
        self.assertFalse(failure_schema["additionalProperties"])
        self.assertFalse(treatment_schema["additionalProperties"])
        self.assertEqual(
            set(failure_schema["properties"]["candidate_treatment"]["enum"]),
            set(REGISTERED_TREATMENTS),
        )
        self.assertEqual(
            set(treatment_schema["properties"]["treatment_id"]["enum"]),
            set(REGISTERED_TREATMENTS),
        )

    def test_structural_fixture_cannot_masquerade_as_admitted_evidence(self) -> None:
        failure = self.failure_record()
        validate_failure_record(
            failure,
            self.contract,
            contract_sha256=self.contract_sha256,
            require_admitted=False,
        )
        with self.assertRaisesRegex(Phase2ContractError, "unverified admission evidence"):
            validate_failure_record(failure, self.contract, contract_sha256=self.contract_sha256, require_admitted=True)
        with self.assertRaisesRegex(Phase2ContractError, "unverified admission evidence"):
            validate_treatment_manifest(self.treatment_manifest(failure), failure, self.contract,
                                        contract_sha256=self.contract_sha256)

    def test_unregistered_treatment_is_rejected(self) -> None:
        failure = self.failure_record()
        manifest = self.treatment_manifest(failure)
        manifest["treatment_id"] = "E5"
        with self.assertRaisesRegex(Phase2ContractError, "unregistered"):
            validate_treatment_manifest(
                manifest,
                failure,
                self.contract,
                contract_sha256=self.contract_sha256,
            )

    def test_feature_leakage_is_rejected(self) -> None:
        failure = self.failure_record()
        manifest = self.treatment_manifest(failure)
        manifest["feature_delta"]["changed_parent_fields"] = [
            "advanced_inter_action_evidence",
            "typed_competing_hypotheses",
        ]
        with self.assertRaisesRegex(Phase2ContractError, "feature leakage"):
            validate_treatment_manifest(
                manifest,
                failure,
                self.contract,
                contract_sha256=self.contract_sha256,
            )

    def test_retrospective_threshold_is_rejected(self) -> None:
        failure = self.failure_record()
        manifest = self.treatment_manifest(failure)
        manifest["decision_rules"]["primary_delta_min_official_RHAE_percent"] = 0.0
        with self.assertRaisesRegex(Phase2ContractError, "retrospective"):
            validate_treatment_manifest(
                manifest,
                failure,
                self.contract,
                contract_sha256=self.contract_sha256,
            )

    def test_experiment_without_exact_frozen_parent_is_rejected(self) -> None:
        failure = self.failure_record()
        manifest = self.treatment_manifest(failure)
        manifest["parent"]["frozen"] = False
        with self.assertRaisesRegex(Phase2ContractError, "frozen parent"):
            validate_treatment_manifest(
                manifest,
                failure,
                self.contract,
                contract_sha256=self.contract_sha256,
            )

    def test_unreproduced_failure_cannot_admit_treatment(self) -> None:
        failure = self.failure_record()
        failure["reproductions"] = failure["reproductions"][:1]
        with self.assertRaisesRegex(Phase2ContractError, "not reproduced enough"):
            validate_failure_record(
                failure,
                self.contract,
                contract_sha256=self.contract_sha256,
                require_admitted=True,
            )

    def test_retrospective_failure_gate_is_rejected(self) -> None:
        failure = self.failure_record()
        failure["admission"]["contract_sha256"] = "0" * 64
        with self.assertRaisesRegex(Phase2ContractError, "retrospective"):
            validate_failure_record(
                failure,
                self.contract,
                contract_sha256=self.contract_sha256,
                require_admitted=True,
            )


if __name__ == "__main__":
    unittest.main()
