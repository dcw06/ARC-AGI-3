"""Local Phase 4 checks: no model inference or target certification."""
import json
from pathlib import Path
import queue
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from agent.action_journal import LiveTransactionJournal, TransactionKind, JournalTransitionError
from agent.scheduler import FairInferenceQueue, QueuedInferenceExecutor, InferenceQueueError
from agent.watchdog import DeadlineWatchdog
from evaluation.phase4 import ROOT, CONTRACT, run_synthetic, validate_contract


class Phase4Tests(unittest.TestCase):
    def test_contract_and_synthetic_smoke_are_not_certification(self):
        value = validate_contract()
        self.assertEqual(value["budget"]["authorized_accelerator_hours"], 0)
        report = run_synthetic(requests_per_client=2)
        self.assertEqual(report["completed_requests"], 220)
        self.assertTrue(report["smoke_passed"])
        self.assertFalse(report["local_load_passed"])
        self.assertFalse(report["target_gpu_certified"])
        self.assertIsNone(report["C_admit"])

    def test_contract_mutation_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            value = json.loads((ROOT / CONTRACT).read_text())
            value["bindings"] = {}
            (root / CONTRACT).write_text(json.dumps(value))
            (root / "config/phase4_contract_lock.json").write_bytes(
                (ROOT / "config/phase4_contract_lock.json").read_bytes())
            with self.assertRaisesRegex(ValueError, "contract drift"):
                validate_contract(root)

    def test_110_fifo_and_capacity_rejection(self):
        q = FairInferenceQueue(maxsize=110)
        seen = []
        for index in range(110):
            q.submit(str(index), 0, "state", lambda index=index: seen.append(index))
        with self.assertRaises(queue.Full):
            q.submit("overflow", 0, "state", lambda: self.fail("overflow executed"))
        for _ in range(110):
            q.service_one()
        self.assertEqual(seen, list(range(110)))
        self.assertEqual(q.max_observed_size, 110)

    def test_stale_aged_and_canceled_requests_never_execute(self):
        for fault in ("stale", "aged", "cancel"):
            with self.subTest(fault=fault):
                q = FairInferenceQueue()
                request = q.submit("opaque", 0, "state", lambda: self.fail("invalid request executed"))
                if fault == "stale":
                    q.cancel_client("opaque")
                elif fault == "aged":
                    request.submitted_monotonic -= 301
                else:
                    request.canceled.set()
                q.service_one()
                self.assertTrue(request.canceled.is_set())

    def test_timeout_returns_no_late_result_and_service_can_close(self):
        entered, release, finished = threading.Event(), threading.Event(), threading.Event()
        def blocked():
            entered.set()
            release.wait(2)
            finished.set()
            return "late"
        executor = QueuedInferenceExecutor(worker_count=1)
        try:
            with self.assertRaises(InferenceQueueError):
                executor.execute(client_id="opaque", generation=0, state_hash="s",
                                 callback=blocked, timeout_seconds=.05)
            self.assertTrue(entered.is_set())
        finally:
            release.set()
            executor.close()
        self.assertTrue(finished.is_set())
        with self.assertRaises(InferenceQueueError):
            executor.execute(client_id="opaque", generation=1, state_hash="s", callback=lambda: 1)

    def test_callback_storage_and_model_errors_surface_without_retry(self):
        with QueuedInferenceExecutor(worker_count=1) as executor:
            for error in (OSError("storage"), TimeoutError("inference")):
                calls = []
                def fail():
                    calls.append(1)
                    raise error
                with self.assertRaises(type(error)):
                    executor.execute(client_id="opaque", generation=0, state_hash="s", callback=fail)
                self.assertEqual(len(calls), 1)

    def test_full_T0_journal_denies_new_transaction(self):
        journal = LiveTransactionJournal("p4", capacity=4)
        for _ in range(4):
            journal.prepare(TransactionKind.ACTION)
        with self.assertRaises(JournalTransitionError):
            journal.prepare(TransactionKind.ACTION)

    def test_admission_cutoff_includes_startup_and_preserves_reserve(self):
        watchdog = DeadlineWatchdog(27540, 600, started_monotonic=100)
        with patch("agent.watchdog.time.monotonic", return_value=100 + 26939.99):
            self.assertFalse(watchdog.stop_admission)
        with patch("agent.watchdog.time.monotonic", return_value=100 + 26940):
            self.assertTrue(watchdog.stop_admission)
            self.assertFalse(watchdog.expired)
        with patch("agent.watchdog.time.monotonic", return_value=100 + 27540):
            self.assertTrue(watchdog.expired)


if __name__ == "__main__":
    unittest.main()
