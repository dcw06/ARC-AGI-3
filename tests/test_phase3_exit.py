"""Fail-closed regression tests for the conditional Phase 3 exit."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation.h1_guardrail import DRAFT_PATH, validate_inactive_guardrail
from scripts.validate_phase3 import validate

ROOT = Path(__file__).resolve().parents[1]


class Phase3ExitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.record = json.loads((ROOT / "config/phase3_decision.json").read_text())
        paths = set(self.record["bindings"]) | {
            DRAFT_PATH, "config/phase3_decision.json", "config/holdout_ledger.yaml",
            "config/phase3_preparation.json", "config/experiment_registry.yaml",
            "config/success_criteria.yaml",
        }
        for name in paths:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_bytes())

    def write(self, name, value):
        (self.root / name).write_text(json.dumps(value))

    def test_actual_exit_validates_existing_phase2_evidence_without_mutations(self):
        paths = [ROOT / "config/holdout_ledger.yaml", ROOT / "config/operational_primary.yaml",
                 ROOT / "config/phase2_compute_ledger.json"]
        before = [path.read_bytes() for path in paths]
        result = validate(ROOT, require_exit=True)
        self.assertTrue(result["phase3_complete"])
        self.assertIsNone(result["H1"]["result"])
        self.assertEqual(before, [path.read_bytes() for path in paths])

    def test_draft_is_not_an_executable_or_frozen_protocol(self):
        draft = validate_inactive_guardrail(self.root, self.record)
        self.assertIsNone(draft["candidate_binding"]["architecture_id"])
        self.assertEqual(draft["compute_contract"]["authorized_accelerator_hours"], 0)
        self.assertFalse((self.root / draft["immutable_freeze_and_reservation"]["frozen_artifact_path"]).exists())

    def test_candidate_activation_or_parent_substitution_invalidates_closure(self):
        for updates in ({"admitted_treatments": ["E5"]}, {"selected_policy": "E6-DISC"}):
            with self.subTest(updates=updates):
                with self.assertRaises(ValueError):
                    validate_inactive_guardrail(self.root, {**self.record, **updates})

    def test_no_veto_and_execution_claims_cannot_masquerade_as_no_candidate(self):
        for key, value in (("result", "NO_VETO"), ("consumed", True),
                           ("reserved", True), ("executed", True),
                           ("positive_performance_claim", True)):
            record = copy.deepcopy(self.record)
            record["H1"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_inactive_guardrail(self.root, record)

    def test_holdout_reservation_or_frozen_artifact_blocks_no_candidate_exit(self):
        ledger_path = "config/holdout_ledger.yaml"
        ledger = json.loads((self.root / ledger_path).read_text())
        ledger["consumption_events"].append({"type": "reservation", "partition": "H1"})
        self.write(ledger_path, ledger)
        record = copy.deepcopy(self.record)
        record["H1"]["ledger_sha256_at_closure"] = hashlib.sha256((self.root / ledger_path).read_bytes()).hexdigest()
        with self.assertRaises(ValueError):
            validate_inactive_guardrail(self.root, record)
        (self.root / ledger_path).write_bytes((ROOT / ledger_path).read_bytes())
        self.write("config/h1_architecture_guardrail_protocol_frozen.yaml", {})
        with self.assertRaises(ValueError):
            validate_inactive_guardrail(self.root, self.record)

    def test_draft_mutation_and_compute_authorization_are_rejected(self):
        draft = json.loads((self.root / DRAFT_PATH).read_text())
        draft["compute_contract"]["authorized_accelerator_hours"] = 2
        self.write(DRAFT_PATH, draft)
        with self.assertRaises(ValueError):
            validate_inactive_guardrail(self.root, self.record)
        record = copy.deepcopy(self.record)
        record["H1"]["protocol_sha256"] = hashlib.sha256((self.root / DRAFT_PATH).read_bytes()).hexdigest()
        with self.assertRaises(ValueError):
            validate_inactive_guardrail(self.root, record)

    def test_registry_cannot_claim_completion_with_pending_or_activated_review(self):
        registry = json.loads((self.root / "config/experiment_registry.yaml").read_text())
        registry["phase_3_review"]["admitted_treatments"] = ["E5"]
        self.write("config/experiment_registry.yaml", registry)
        with patch("scripts.validate_phase3.validate_phase2"), self.assertRaises(ValueError):
            validate(self.root, require_exit=True)

    def test_bound_evidence_drift_blocks_exit(self):
        self.write("config/phase2_closure.json", {})
        with patch("scripts.validate_phase3.validate_phase2"), self.assertRaises(ValueError):
            validate(self.root, require_exit=True)

    def test_required_binding_inventory_cannot_be_removed(self):
        for bindings in ({}, {k:v for k,v in self.record["bindings"].items()
                              if k != "reports/phase2_cd82_evidence_review.md"}):
            record = copy.deepcopy(self.record)
            record["bindings"] = bindings
            self.write("config/phase3_decision.json", record)
            with patch("scripts.validate_phase3.validate_phase2"), self.assertRaises(ValueError):
                validate(self.root, require_exit=True)

    def test_phase2_requires_review_reference_hash_and_file(self):
        from scripts.validate_phase2_exit import validate as phase2
        name = "config/phase2_closure.json"
        closure = json.loads((self.root / name).read_text())
        for field in ("evidence_review", "evidence_review_sha256"):
            changed = dict(closure)
            changed.pop(field)
            self.write(name, changed)
            with patch("scripts.validate_phase2_exit.validate_contract"), self.assertRaises(ValueError):
                phase2(self.root)
        self.write(name, closure)
        (self.root / closure["evidence_review"]).unlink()
        with patch("scripts.validate_phase2_exit.validate_contract"), self.assertRaises(OSError):
            phase2(self.root)
