from dataclasses import asdict, replace
from pathlib import Path
import unittest

from jsonschema import ValidationError
from evaluation.phase3 import (
    Prediction, Transition, Verdict, GUARDS, evaluate, discriminates, support_gate,
    continuation, local_fingerprint, paired_report, validate_fixture,
    validate_preparation, require_execution_closure,
)

ROOT = Path(__file__).resolve().parents[1]


def fixture(i=1, local=1):
    prediction = Prediction(f"p{i}", f"t{i}", i-1, "local", "player", "bound_entity_x", 2, f"e{i}")
    transition = Transition(f"t{i}", i, "local", "player", "bound_entity_x", 2, f"e{i}", True, True,
        local_fingerprint(entity="player", scope="local", relevant_configuration=(local,)), "a"*64)
    return prediction, transition, None


class Phase3Tests(unittest.TestCase):
    def test_preparation_never_authorizes_execution(self):
        config = validate_preparation(ROOT)
        with self.assertRaises(ValueError):
            require_execution_closure(config)
        config.update(parent_manifest_sha256="a"*64, status="active")
        with self.assertRaises(ValueError):
            require_execution_closure(config)

    def test_three_valued_and_precommit(self):
        p, t, _ = fixture()
        self.assertEqual(evaluate(p, t), Verdict.MATCH)
        self.assertEqual(evaluate(p, replace(t, observed=3)), Verdict.MISMATCH)
        for altered in [replace(t, evidence_available=False), replace(t, correspondence_known=False),
                        replace(t, scope="novel"), replace(t, dependency="other"),
                        replace(t, evidence_id="missing"), replace(t, sequence=0)]:
            self.assertEqual(evaluate(p, altered), Verdict.UNKNOWN)
        for altered in [replace(p, required=False), replace(p, kind="changed_cells"),
                        replace(p, kind="timer"), replace(p, expected=True)]:
            self.assertEqual(evaluate(altered, t), Verdict.UNKNOWN)

    def test_discrimination_is_action_relevant(self):
        p, t, _ = fixture()
        rival = replace(p, prediction_id="rival", expected=3)
        self.assertTrue(discriminates(p, rival, t))
        self.assertFalse(discriminates(p, replace(rival, dependency="timer"), t))
        self.assertFalse(discriminates(p, replace(rival, committed_sequence=1), t))

    def gate(self, rows, variant="E6-REPEAT", **kwargs):
        return support_gate(rows, variant=variant, scope="local", dependency="player",
                            kind="bound_entity_x", alternatives_unresolved=kwargs.pop("alternatives", False), **kwargs)

    def test_repeat_diversity_duplicates_and_alternatives(self):
        rows = [fixture(1, 1), fixture(2, 2), fixture(3, 1)]
        self.assertTrue(self.gate(rows))
        self.assertFalse(self.gate(rows, alternatives=True))
        self.assertFalse(self.gate(rows, retired=True))
        self.assertFalse(self.gate([rows[0]]*3))
        self.assertFalse(self.gate([fixture(i, 1) for i in range(1, 4)]))
        self.assertFalse(self.gate(rows, "E6-DISC"))
        p, t, _ = rows[0]
        rows[0] = (p, t, replace(p, prediction_id="rival", expected=3))
        self.assertTrue(self.gate(rows[:2], "E6-DISC"))
        with self.assertRaises(ValueError):
            self.gate(rows, "whichever_gate_passes")

    def test_support_revoked_on_loss_contradiction_scope(self):
        rows = [fixture(1), fixture(2, 2), fixture(3)]
        p, t, rival = rows[-1]
        for bad in [replace(t, evidence_available=False), replace(t, observed=9),
                    replace(t, correspondence_known=False), replace(t, scope="new")]:
            self.assertFalse(self.gate(rows[:2]+[(p, bad, rival)]))
        self.assertFalse(self.gate(rows*22))

    def test_hud_changes_cannot_create_local_diversity(self):
        rows = [fixture(i, 1) for i in range(1, 4)]
        rows = [(p, replace(t, full_state_sha256=str(i)*64), r) for i, (p,t,r) in enumerate(rows)]
        self.assertEqual(len({t.prestate_fingerprint for _,t,_ in rows}), 1)
        self.assertFalse(self.gate(rows))

    def test_controller_guards_and_ambiguity_precedence(self):
        args = dict(e6_enabled=True, unresolved_dispatch=False, predicates={"player": Verdict.MATCH},
                    dependencies={"player"}, guards={k: Verdict.MATCH for k in GUARDS})
        self.assertEqual(continuation(**args), "CONTINUE_ONE_ACTION")
        for verdict in (Verdict.UNKNOWN, Verdict.MISMATCH):
            self.assertEqual(continuation(**{**args, "predicates": {"player": verdict}}), "CANCEL_QUEUE")
            for key in GUARDS:
                self.assertEqual(continuation(**{**args, "guards": {**args["guards"], key: verdict}}), "CANCEL_QUEUE")
        for change in ({"predicates": {}}, {"guards": {}}, {"dependencies": set()}):
            self.assertEqual(continuation(**{**args, **change}), "CANCEL_QUEUE")
        self.assertEqual(continuation(**{**args, "e6_enabled": False}), "SINGLE_ACTION")
        self.assertEqual(continuation(**{**args, "e6_enabled": False, "unresolved_dispatch": True}), "QUARANTINED")

    def test_e1_rejects_new_features_and_bundle_excludes_infrastructure(self):
        from agent.feature_manifest import load_e1_feature_manifests, validate_e1_proposal, FeatureManifestError
        from scripts.build_notebook import bundled_sources
        manifests = load_e1_feature_manifests(ROOT / "config/e1_feature_manifests.yaml")
        for manifest in manifests.values():
            for field in ("hypotheses", "predictions", "queue", "probe", "support_records"):
                with self.assertRaises(FeatureManifestError):
                    validate_e1_proposal({"action": {"action_id": 1, "action_data": {}}, field: []},
                                         manifest=manifest, legal_actions=[1])
        self.assertFalse(any("phase3" in path for path in bundled_sources()))

    def test_schema_bounds_and_extra_fields(self):
        schema = ROOT / "config/phase3_prediction_schema.json"
        value = {"schema_version": 1, "status": "inactive_fixture_only", "hypotheses": [],
                 "predictions": [asdict(fixture()[0])]}
        validate_fixture(value, schema)
        for altered in ({**value, "status": "active"}, {**value, "extra": 1},
                        {**value, "predictions": value["predictions"]*65}):
            with self.assertRaises((ValueError, ValidationError)):
                validate_fixture(altered, schema)
        with self.assertRaises(ValueError):
            validate_fixture({**value, "predictions": value["predictions"]*2}, schema)

    def records(self):
        config = validate_preparation(ROOT)
        bindings = {k+"_sha256": "a"*64 for k in ("parent", "model", "scheduler", "workload", "ceilings", "protocol", "treatment_manifest")}
        return [{**bindings, "pair_id": str(i), "run_id": f"{i}-{arm}", "arm": arm, "order": order,
                 "mode": "shared_resource_whole_run", "complete_workload": True,
                 "cost_scope": "all_work_including_setup_probes_support_and_failures",
                 "metrics": {k: 0 for k in config["metrics"]}}
                for i, order in enumerate(("AB", "BA")) for arm in ("parent", "treatment")]

    def test_paired_report_descriptive_only(self):
        result = paired_report(self.records())
        self.assertEqual(result["pairs"], 2)
        self.assertTrue(result["counterbalanced"])
        self.assertFalse(result["acceptance_claim"])
        self.assertEqual(result["uncertainty_unit"], "paired_complete_workloads")

    def test_paired_report_rejects_mixed_uncharged_and_incomplete(self):
        for change in ({"model_sha256": "b"*64}, {"scheduler_sha256": "b"*64},
                       {"complete_workload": False}, {"cost_scope": "inference_only"},
                       {"mode": "per_transition"}, {"run_id": "0-parent"}):
            rows = self.records()
            rows[-1].update(change)
            with self.assertRaises(ValueError):
                paired_report(rows)
        for rows in ([], self.records()[:-1]):
            with self.assertRaises(ValueError):
                paired_report(rows)
        rows = self.records()
        rows[0]["metrics"]["tokens"] = float("nan")
        with self.assertRaises(ValueError):
            paired_report(rows)


if __name__ == "__main__":
    unittest.main()
