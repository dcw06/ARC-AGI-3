import copy
import contextlib
import io
from dataclasses import replace
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agent.diagnostics import canonical_sha256
from agent.evidence import EvidenceStore
from evaluation.phase2_sequences import SequenceRecorder, validate_sequences
from evaluation.phase2_budget import summarize, append_event, read_ledger
from evaluation.phase2_evidence_gate import resolve_admission
from evaluation.phase2_reproduction import sha, compare_runs
from scripts.phase2_supervisor import supervise
from scripts.build_phase2_diagnostic_notebook_v2 import build
from tests.test_phase2_diagnostics import observation
from tests import test_phase2_execution, test_phase2

ROOT = Path(__file__).resolve().parents[1]


class SequenceTests(unittest.TestCase):
    def test_v2_observer_does_not_change_model_requests_or_actions(self):
        from tests import test_phase2_diagnostics as fixtures
        fixtures.Phase2DiagnosticTests.setUpClass()
        test = fixtures.Phase2DiagnosticTests()
        with patch.object(fixtures,"TransitionDiagnosticRecorder",SequenceRecorder):
            test.test_diagnostics_do_not_change_policy_requests_or_actions()

    def recorder(self, fail_capture=False):
        import numpy as np
        from agent.action import ActionDecision
        before = observation()
        after = replace(before, frames=(np.zeros_like(before.latest_frame), before.latest_frame))
        recorder = SequenceRecorder(game_id=before.game_id, treatment_id="E1S-R",seed=1,run_id="fixture",capacity=80)
        recorder.begin_transition(before,iteration=1)
        recorder.note_decision(ActionDecision(1))
        evidence = EvidenceStore().record_transition(before,after,action_id=1,transition_id="t1")
        if fail_capture:
            with patch("evaluation.phase2_sequences.PackedFrameSequence.pack", side_effect=OSError("fixture")):
                recorder.finish_acknowledged(before,after,evidence)
        else:
            recorder.finish_acknowledged(before,after,evidence)
        return recorder

    def test_intermediate_only_cue_roundtrips_without_parent_bundle_changes(self):
        import base64
        from agent.evidence import PackedFrameSequence
        recorder = self.recorder()
        sidecar = recorder.sequence_bundle()
        self.assertEqual(validate_sequences(sidecar,recorder.bundle()), {"fixture/t1"})
        sequence = PackedFrameSequence.from_blob(base64.b64decode(sidecar["sequences"][0]["blob_base64"]))
        self.assertEqual(len(sequence.frames),2)
        self.assertNotEqual(sequence.frames[0].content_sha256,sequence.frames[1].content_sha256)
        self.assertNotIn("sequences",recorder.bundle())

    def test_capacity_omission_is_explicit_and_replayable(self):
        with patch("evaluation.phase2_sequences.MAX_SEQUENCE_BYTES",1):
            recorder = self.recorder()
        self.assertEqual(recorder.sequence_bundle()["sequences"][0]["availability"],"omitted_capacity")
        self.assertEqual(validate_sequences(recorder.sequence_bundle(),recorder.bundle()),set())

    def test_corruption_rejected_even_when_sidecar_rehashed(self):
        recorder = self.recorder()
        sidecar = recorder.sequence_bundle()
        sidecar["sequences"][0]["sequence_sha256"] = "0"*64
        sidecar["sha256"] = canonical_sha256({k:v for k,v in sidecar.items() if k != "sha256"})
        with self.assertRaises(ValueError):
            validate_sequences(sidecar,recorder.bundle())

    def test_capture_failure_does_not_erase_parent_transition(self):
        recorder = self.recorder(fail_capture=True)
        self.assertEqual(recorder.sequence_bundle()["sequences"][0]["availability"],"capture_error")
        self.assertEqual(len(recorder.bundle()["records"]),1)
        self.assertTrue(recorder.bundle()["capture_errors"])
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/"bundle.json"
            recorder.write(target)
            self.assertTrue(Path(str(target)+".sequences").is_file())
            self.assertEqual(json.loads(target.read_text()),recorder.bundle())


class BudgetTests(unittest.TestCase):
    def test_unknown_and_failed_attempts_are_not_free(self):
        events = [{"kind":"reserve","attempt_id":"a","seconds":7200},
                  {"kind":"discover","attempt_id":"failed-install","seconds":1000}]
        result = summarize(events)
        self.assertEqual(result["charged_or_reserved_seconds"],8200)
        self.assertFalse(result["new_execution_allowed"])
        with self.assertRaises(ValueError):
            summarize(events + [events[0]])
        self.assertTrue(summarize([{"kind":"discover","attempt_id":"overrun","seconds":30000}])["over_budget"])

    def test_append_preserves_history_and_rejects_unfunded_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory)/"ledger.json"
            initial = {"schema_version":1,"events":[{"kind":"reserve","attempt_id":"a","seconds":7200}]}
            ledger.write_text(json.dumps(initial))
            with self.assertRaises(ValueError):
                append_event(ledger,{"kind":"reserve","attempt_id":"b","seconds":7200})
            self.assertEqual(json.loads(ledger.read_text()),initial)
            evidence = Path(directory)/"cost.json"
            evidence.write_text(json.dumps({"attempt_id":"a","charged_accelerator_seconds":100,
                                "scope":"all_accelerator_time_including_setup_and_failures"}))
            append_event(ledger,{"kind":"reconcile","attempt_id":"a","seconds":100,
                         "evidence_path":str(evidence),"evidence_sha256":sha(evidence)})
            self.assertEqual(json.loads(ledger.read_text())["events"][0],initial["events"][0])
            self.assertEqual(read_ledger(ledger)["charged_or_reserved_seconds"],100)
            evidence.write_text("changed")
            with self.assertRaises(ValueError):
                read_ledger(ledger)

    def test_installation_failure_and_timeout_leave_cost_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(subprocess.CalledProcessError):
                supervise([sys.executable,"-c","raise SystemExit(3)"],directory,2)
            self.assertEqual(json.loads((Path(directory)/"notebook-cost.json").read_text())["status"],"failed")
            with self.assertRaises(TimeoutError):
                supervise([sys.executable,"-c","import time; time.sleep(20)"],directory,0.1)
            self.assertEqual(json.loads((Path(directory)/"notebook-cost.json").read_text())["status"],"timed_out")


class AdmissionTests(unittest.TestCase):
    def test_resolves_real_files_rejects_missing_refs_and_never_auto_attributes(self):
        lock = json.loads((ROOT/"notebooks/phase2-cd82/execution-lock.json").read_text())
        helper = test_phase2_execution.ExecutionTests()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in lock["sources"]:
                target = root/name
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ROOT/name,target)
            def write(name,value):
                path = root/name
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(json.dumps(value))
                return {"path":name,"sha256":sha(path)}
            envelopes = [helper.envelope("fixture-a",lock),helper.envelope("fixture-b",lock)]
            refs = [write(f"runs/{i}.json",envelope) for i,envelope in enumerate(envelopes)]
            report = compare_runs(root,[root/r["path"] for r in refs],lock)
            self.assertFalse(report["admission_passed"])
            test_phase2.Phase2ContractTests.setUpClass()
            record = test_phase2.Phase2ContractTests().failure_record()
            record["failure_signature_sha256"] = report["runs"][0]["trajectory_sha256"]
            record["candidate_treatment"] = "E3"
            record["diagnosis"]["missing_capability"] = "durable_scratch_rejected_hypothesis_memory"
            record["diagnosis"]["evidence_refs"] = []
            for reproduction,envelope,run in zip(record["reproductions"],envelopes,report["runs"]):
                transition_id = envelope["bundle"]["records"][0]["transition"]["transition_id"]
                reproduction.update(run_id=run["run_id"],evidence_sha256=run["file_sha256"],
                    failure_signature_sha256=run["trajectory_sha256"],transition_ids=[transition_id],
                    game_id=envelope["game_id"],seed=envelope["seed"])
                record["diagnosis"]["evidence_refs"].append(run["run_id"]+"/"+transition_id)
            review = {"status":"reviewed_single_capability","reviewer":"synthetic test reviewer",
                "rationale":"fixture only, not a real capability attribution", "failure_id":record["failure_id"],
                "missing_capabilities":[record["diagnosis"]["missing_capability"]],
                "run_sha256s":sorted(r["file_sha256"] for r in report["runs"]),
                "evidence_refs":record["diagnosis"]["evidence_refs"],
                "excluded_alternative_causes":record["diagnosis"]["excluded_alternative_causes"]}
            entry = {"lock":write("lock.json",lock),"runs":refs,"attribution_review":write("review.json",review)}
            write("config/phase2_admission_index.json",{"schema_version":1,"failures":{record["failure_id"]:entry}})
            self.assertTrue(resolve_admission(record,root)["failure_reproduced"])
            bad = copy.deepcopy(record)
            bad["reproductions"][0]["evidence_sha256"] = "a"*64
            with self.assertRaises(ValueError):
                resolve_admission(bad,root)
            (root/"review.json").unlink()
            with self.assertRaises(ValueError):
                resolve_admission(record,root)

    def test_v2_build_preserves_live_lock(self):
        path = ROOT/"notebooks/phase2-cd82/execution-lock.json"
        before = path.read_bytes()
        notebook,extension = build()
        self.assertEqual(before,path.read_bytes())
        self.assertEqual(extension["policy_delta"],"none")
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                compile(cell["source"],"v2-notebook","exec")

    def test_integrity_report_does_not_exit_success_for_unreproduced_failure(self):
        from scripts import validate_phase2_reproduction as cli
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copyfile(ROOT/"notebooks/phase2-cd82/execution-lock.json",root/"execution-lock.json")
            (root/"execution.json").write_text(json.dumps({"status":"complete","runs":["a.json","b.json"]}))
            (root/"notebook-cost.json").write_text(json.dumps({"elapsed_seconds":1}))
            with patch.object(cli,"compare_runs",return_value={"failure_reproduced":False}), contextlib.redirect_stdout(io.StringIO()):
                with patch.object(sys,"argv",["validator",str(root)]):
                    self.assertEqual(cli.main(),2)
                with patch.object(sys,"argv",["validator",str(root),"--report-only"]):
                    self.assertEqual(cli.main(),0)
