"""Portable historical evidence remains valid while current eligibility changes."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.phase23_evidence import ARCHIVE, DESCRIPTOR, historical, restore, validate_snapshot

ROOT = Path(__file__).resolve().parents[1]


class HistoricalClosureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = restore(ROOT / ARCHIVE, ROOT / DESCRIPTOR,
                            Path(self.temporary.name) / "checkout")
        for name in (ARCHIVE, DESCRIPTOR):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / name).read_bytes())

    def change_json(self, name, update):
        path = self.root / name
        value = json.loads(path.read_text())
        update(value)
        path.write_text(json.dumps(value))

    def assert_current_rejected_history_valid(self):
        with self.assertRaises(ValueError):
            validate_snapshot(self.root)
        self.assertTrue(historical(self.root)["historical_completion"])

    def test_later_phase_and_policy_changes_do_not_rewrite_history(self):
        self.change_json("config/experiment_registry.yaml", lambda v: v.update(current_phase="phase_4"))
        self.assert_current_rejected_history_valid()
        path = self.root / "agent/e1_policy.py"
        path.write_text(path.read_text() + "\n# later authorized development\n")
        self.assert_current_rejected_history_valid()

    def test_later_h1_or_h2_events_preserve_prior_closure(self):
        original = (self.root / "config/holdout_ledger.yaml").read_bytes()
        for partition in ("H1", "H2"):
            with self.subTest(partition=partition):
                (self.root / "config/holdout_ledger.yaml").write_bytes(original)
                self.change_json("config/holdout_ledger.yaml", lambda v: v["consumption_events"].append(
                    {"partition": partition, "type": "consumption", "run_id": "later-run"}))
                self.assert_current_rejected_history_valid()

    def test_second_checkout_cannot_read_original_project(self):
        # A filesystem audit hook simulates loss of the original project without
        # moving user files. The installed Python/dependencies are still available.
        code = '''import sys, pathlib, runpy
original = pathlib.Path(sys.argv[1]).resolve()
snapshot = pathlib.Path(sys.argv[2]).resolve()
def audit(event, args):
    if event == "open" and isinstance(args[0], (str, bytes)):
        path = pathlib.Path(args[0]).resolve()
        if path.is_relative_to(original):
            relative = path.relative_to(original)
            if relative.parts[0] not in {".venv", ".uv-python"}:
                raise PermissionError("original project unavailable: " + str(path))
sys.addaudithook(audit)
sys.argv = [str(snapshot / "scripts/validate_phase3.py"), "--current", "--require-exit"]
runpy.run_path(sys.argv[0], run_name="__main__")
'''
        result = subprocess.run([sys.executable, "-I", "-c", code, str(ROOT), str(self.root)],
                                cwd=self.root, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_local_accounting_evidence_does_not_fall_back(self):
        (self.root / "reports/phase2_runtime_owner_confirmation.json").unlink()
        # The original file still exists; current validation must nevertheless fail.
        with self.assertRaises(ValueError):
            validate_snapshot(self.root)

    def test_corrupt_or_missing_archive_rejected(self):
        path = self.root / ARCHIVE
        path.write_bytes(path.read_bytes() + b"corrupt")
        with self.assertRaises(ValueError):
            historical(self.root)
        path.unlink()
        with self.assertRaises(OSError):
            historical(self.root)

    def test_restore_never_overwrites_existing_checkout(self):
        with self.assertRaises(ValueError):
            restore(ROOT / ARCHIVE, ROOT / DESCRIPTOR, self.root)
