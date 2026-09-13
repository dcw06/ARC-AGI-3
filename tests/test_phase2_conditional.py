from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from agent.feature_manifest import (
    FeatureManifestError,
    load_e1_feature_manifests,
    validate_e1_proposal,
)
from agent.representation import build_raw_bundle
from agent.state import Observation
from evaluation.phase2_contract import Phase2ContractError
from evaluation.phase2_selection import validate_conditional_implementation


ROOT = Path(__file__).resolve().parents[1]
FEATURES = (
    "advanced_inter_action_evidence",
    "advanced_animation_summary",
    "selective_rich_animation",
    "advanced_correspondence_identity_tracking",
    "durable_scratch_rejected_hypothesis_memory",
    "exact_historical_retrieval_retrodiction",
)


class Phase2ConditionalImplementationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.closure = json.loads(
            (ROOT / "config/phase2_conditional_implementation.yaml").read_text()
        )
        cls.manifest = load_e1_feature_manifests(
            ROOT / "config/e1_feature_manifests.yaml"
        )["E1S-R"]

    def test_no_treatment_implementation_is_the_valid_conditional_exit(self) -> None:
        result = validate_conditional_implementation(ROOT)
        self.assertIsNone(result["selected_treatment"])
        self.assertEqual(result["chunk_2_3_evidence_treatment"]["deterministic_enrichers"], [])
        self.assertFalse(result["chunk_2_4_memory_retrieval"]["E3"]["implemented"])
        self.assertFalse(result["chunk_2_4_memory_retrieval"]["E4"]["implemented"])

    def test_E1_rejects_every_registered_phase2_feature(self) -> None:
        base = {"action": {"action_id": 1, "action_data": {}}}
        for feature in FEATURES:
            with self.subTest(feature=feature), self.assertRaisesRegex(
                FeatureManifestError, "disabled or unknown"
            ):
                validate_e1_proposal(
                    {**base, feature: {}},
                    manifest=self.manifest,
                    legal_actions=[1],
                )

    def test_E1_R_does_not_expose_intermediate_only_cue_or_identity_features(self) -> None:
        observation = Observation.from_value(
            {
                "game_id": "ar25-0c556536",
                "frame": [[[0, 0]], [[0, 2]], [[0, 0]]],
                "state": "NOT_FINISHED",
                "levels_completed": 0,
                "win_levels": 2,
                "guid": "conditional-negative-fixture",
                "full_reset": False,
                "available_actions": [1],
            }
        )
        payload = build_raw_bundle(observation, recent_limit=1).policy_payload()
        visible = json.dumps(payload, sort_keys=True)
        self.assertNotIn("transient", visible)
        self.assertNotIn("identity", visible)
        self.assertNotIn("correspondence", visible)
        self.assertNotIn("advanced_", visible)

    def test_unselected_E2_enricher_claim_is_rejected(self) -> None:
        value = copy.deepcopy(self.closure)
        value["chunk_2_3_evidence_treatment"]["implemented_variant"] = "E2a"
        value["chunk_2_3_evidence_treatment"]["deterministic_enrichers"] = [
            "advanced_inter_action_evidence"
        ]
        with self.assertRaisesRegex(Phase2ContractError, "unselected E2"):
            validate_conditional_implementation(ROOT, value)

    def test_unjustified_E3_store_is_rejected(self) -> None:
        value = copy.deepcopy(self.closure)
        value["chunk_2_4_memory_retrieval"]["E3"]["implemented"] = True
        value["chunk_2_4_memory_retrieval"]["E3"]["stores"] = ["mechanics"]
        with self.assertRaisesRegex(Phase2ContractError, "E3 memory"):
            validate_conditional_implementation(ROOT, value)

    def test_unjustified_E4_schema_is_rejected(self) -> None:
        value = copy.deepcopy(self.closure)
        value["chunk_2_4_memory_retrieval"]["E4"]["implemented"] = True
        value["chunk_2_4_memory_retrieval"]["E4"]["query_schemas"] = ["query-v1"]
        with self.assertRaisesRegex(Phase2ContractError, "E4 retrieval"):
            validate_conditional_implementation(ROOT, value)


if __name__ == "__main__":
    unittest.main()
