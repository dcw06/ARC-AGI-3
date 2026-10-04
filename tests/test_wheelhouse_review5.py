"""Regressions for the review of 6bb20bf/5f74b03: hard-failing unconfirmed termination, preserved human
decisions, a runner that imports its suites, and a non-circular, self-contained bundle specification."""
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import check_wheelhouse_metadata as W
from scripts import download_wheelhouse as D
from scripts import plan_wheelhouse_r2_bundle as P

ROOT = Path(__file__).resolve().parents[1]


class UnconfirmedTermination(unittest.TestCase):
    def test_it_is_not_an_ordinary_fetch_failure(self):
        self.assertFalse(issubclass(W.WorkerNotTerminated, W.FetchError))

    def test_downloader_aborts_without_retrying_or_touching_the_partial_file(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            artifact = {'filename': 'demo-1.0-py3-none-any.whl', 'size': 2, 'sha256': hashlib.sha256(b'ok').hexdigest(),
                        'url': 'https://files.pythonhosted.org/packages/aa/demo-1.0-py3-none-any.whl'}
            dl = D.Downloader(tmp, sleep=lambda s: None)
            partial = tmp / '.partial' / f"{artifact['filename']}.{os.getpid()}.tmp"
            partial.parent.mkdir(parents=True)
            partial.write_bytes(b'possibly still being written')
            calls = []

            def stuck(*args, **kwargs):
                calls.append(1)
                raise W.WorkerNotTerminated('could not confirm termination')
            with mock.patch.object(D, 'run_worker', stuck):
                with self.assertRaises(W.WorkerNotTerminated):
                    dl.fetch(artifact)
            self.assertEqual(len(calls), 1, 'a stuck worker must not be followed by further attempts')
            self.assertEqual(partial.read_bytes(), b'possibly still being written')
            self.assertFalse((tmp / artifact['filename']).exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_metadata_acquisition_aborts_instead_of_recording_unknown(self):
        client = W.Client(budget=5)
        wheel = {'filename': 'demo-1.0-py3-none-any.whl', 'distribution': 'demo', 'sha256': '0' * 64}
        with mock.patch.object(W, 'run_worker', side_effect=W.WorkerNotTerminated('stuck')):
            with self.assertRaises(W.WorkerNotTerminated):
                W.acquire_one(wheel, client, {})


class HumanDecisions(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.patches = [mock.patch.object(P, name, self.tmp / Path(getattr(P, name)).name)
                        for name in ('INVENTORY_CSV', 'DECISIONS_CSV', 'PLAN_JSON', 'PLAN_MD')]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def rows(self):
        with P.DECISIONS_CSV.open(encoding='utf-8', newline='') as stream:
            return list(csv.DictReader(stream))

    def write(self, rows):
        with P.DECISIONS_CSV.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=P.DECISION_FIELDS, lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)

    def test_regeneration_never_erases_a_recorded_decision(self):
        self.assertEqual(P.main(), 0)  # creates the decisions file once
        rows = self.rows()
        rows[0].update(redistribution_decision='approved', rationale='MIT; licence text shipped', decided_on='2026-10-04')
        self.write(rows)
        before = P.DECISIONS_CSV.read_bytes()
        self.assertEqual(P.main(), 0)
        self.assertEqual(P.DECISIONS_CSV.read_bytes(), before)
        plan = json.loads(P.PLAN_JSON.read_text(encoding='utf-8'))
        self.assertEqual(plan['decisions']['counts'], {'approved': 1, 'unresolved': 173})

    def test_stale_or_invalid_decisions_are_refused_and_left_untouched(self):
        self.assertEqual(P.main(), 0)
        for change in (lambda r: r[0].__setitem__('sha256', '0' * 64),
                       lambda r: r[1].__setitem__('redistribution_decision', 'probably fine'),
                       lambda r: r[2].update(redistribution_decision='approved', rationale=''),
                       lambda r: r.pop(3),
                       lambda r: r.append(dict(r[4]))):
            self.write([])
            P.DECISIONS_CSV.unlink()
            P.main()
            rows = self.rows()
            change(rows)
            self.write(rows)
            before = P.DECISIONS_CSV.read_bytes()
            self.assertEqual(P.main(), 1)
            self.assertEqual(P.DECISIONS_CSV.read_bytes(), before)

    def test_the_generated_inventory_holds_no_decision_columns(self):
        P.main()
        with P.INVENTORY_CSV.open(encoding='utf-8', newline='') as stream:
            header = next(csv.reader(stream))
        self.assertFalse({'redistribution_decision', 'rationale', 'resolver'} & set(header))

    def test_the_license_table_command_refuses_to_overwrite(self):
        with mock.patch.object(W, 'LICENSE_TABLE', self.tmp / 'existing.csv'):
            (self.tmp / 'existing.csv').write_text('human edits')
            with self.assertRaises(SystemExit):
                W.main(['license-table'])
            self.assertEqual((self.tmp / 'existing.csv').read_text(), 'human edits')


class Runner(unittest.TestCase):
    def test_the_documented_command_imports_every_suite_without_pythonpath(self):
        env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
        with tempfile.TemporaryDirectory() as elsewhere:
            proc = subprocess.run([sys.executable, str(ROOT / 'scripts/run_wheelhouse_checks.py'), '--list'],
                                  cwd=elsewhere, env=env, capture_output=True, text=True, timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        listed = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(listed['import_failures'], [])
        self.assertGreaterEqual(listed['tests'], 80)


class BundleSpecification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads(P.PLAN_JSON.read_text(encoding='utf-8'))

    def test_checksum_files_do_not_hash_each_other(self):
        c = self.plan['checksum_construction']
        self.assertIn('excludes', ' '.join(f['source'] for f in self.plan['files'] if f['path'] == 'bundle-manifest.json'))
        self.assertIn('never SHA256SUMS', c['bundle-manifest.json'])
        self.assertIn('plus the completed bundle-manifest.json', c['SHA256SUMS'])
        self.assertIn('never itself', c['SHA256SUMS'])
        self.assertIn('SHA256SUMS', c['approval_binds'])
        self.assertEqual(c['order'][1:3], ['write bundle-manifest.json over the payload',
                                           'write SHA256SUMS over the payload and bundle-manifest.json'])

    def test_installation_evidence_is_self_contained(self):
        receipt = json.loads((ROOT / 'reports/wheelhouse_r2_offline_install_check.json').read_text(encoding='utf-8'))
        files = {f['path']: f for f in self.plan['files']}
        for name, digest in receipt['evidence']['files_sha256'].items():
            self.assertEqual(files[f'EVIDENCE/{name}']['sha256'], digest, name)
        self.assertIn('EVIDENCE/offline_install_check.json', files)


if __name__ == '__main__':
    unittest.main()
