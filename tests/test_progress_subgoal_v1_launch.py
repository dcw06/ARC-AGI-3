"""progress_subgoal_v1 launcher: invalid provider attachments fail the attempt even with HTTP 200 (review of bc0c1b9).

Every case runs the real approval -> reservation -> package -> launch path in a temporary copy of the frozen review
snapshot with a fake provider backend; nothing is uploaded."""
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest

from research.progress_subgoal_v1 import authority as auth
from scripts import progress_subgoal_v1_package as package

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ('invalid_dataset_sources', 'invalid_model_sources', 'invalid_competition_sources', 'invalid_kernel_sources')


class Backend:
    def __init__(self, response):
        self.response, self.calls = response, 0

    def quota(self):
        return dict(total_time_allowed=7200, time_used=0, time_reserved=0)

    def push(self, folder):
        self.calls += 1
        return self.response


def ok(**extra):
    """An HTTP-200 provider response; attachment fields default to empty lists (accepted)."""
    value = dict(url='https://example.invalid/kernel', version_number=1, error=None, **{f: [] for f in FIELDS})
    value.update(extra)
    return SimpleNamespace(**value)


class AttachmentErrors(unittest.TestCase):
    def test_classification(self):
        present, rejected = package.attachment_errors(ok())
        self.assertEqual(rejected, [])
        self.assertEqual({k for k in present if k in FIELDS}, set(FIELDS))
        for field in FIELDS:
            self.assertEqual(package.attachment_errors(ok(**{field: ['x/y']}))[1], [field])
        self.assertEqual(package.attachment_errors(ok(invalidFutureSources=['z']))[1], ['invalidFutureSources'])
        self.assertEqual(package.attachment_errors(ok(invalid_dataset_sources='bad'))[1], ['invalid_dataset_sources'])
        self.assertEqual(package.attachment_errors({'url': 'u', 'invalidModelSources': ['m']})[1], ['invalidModelSources'])
        self.assertEqual(package.attachment_errors({'url': 'u', 'invalidModelSources': []})[1], [])
        no_fields = SimpleNamespace(url='u', version_number=1, error=None)  # a field the provider omitted is not an error
        self.assertEqual(package.attachment_errors(no_fields), ({}, []))


class LaunchPath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = json.loads((ROOT / auth.REVIEW).read_bytes())
        cls.names = list(cls.review['bindings']) + [str(Path(auth.REVIEW).parent / n) for n in
                                                    ('review-source-lock.json', 'profile.ipynb', 'kernel-metadata.json')]

    def launch(self, response):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        root = Path(tmp) / 'repo'
        for name in self.names:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        review_sha = package.digest(root, auth.REVIEW)
        for kind in ('source', 'compute'):
            package.record_approval(root, kind, 'TEST FIXTURE ONLY', review_sha)
        package.reserve(root)
        package.package(root)
        backend = Backend(response)
        receipt = package.launch(root, backend)
        self.assertEqual(backend.calls, 1)
        # whatever the provider said, the attempt is consumed and is never retried
        self.assertTrue(receipt['attempt_consumed'])
        self.assertFalse(receipt['automatic_retry_authorized'])
        self.assertEqual(json.loads((root / auth.RESERVATION).read_bytes())['status'], 'consumed')
        self.assertEqual(json.loads((root / package.RECEIPT).read_bytes()), receipt)
        with self.assertRaises(PermissionError):
            package.launch(root, Backend(ok()))
        return receipt

    def test_each_rejected_attachment_fails_with_http_200(self):
        for field in FIELDS + ('invalidFutureSources',):
            with self.subTest(field=field):
                receipt = self.launch(ok(**{field: ['owner/rejected']}))
                self.assertEqual(receipt['status'], 'provider_rejected_attachments_no_retry')
                self.assertIn(field, receipt['error'])  # the CLI exits non-zero when the receipt has an error
                self.assertEqual(receipt['provider_attachment_errors'][field], ['owner/rejected'])
                self.assertEqual(receipt['url'], 'https://example.invalid/kernel')

    def test_no_attachment_error_is_accepted_and_every_field_is_retained(self):
        receipt = self.launch(ok())
        self.assertEqual((receipt['status'], receipt['error']), ('provider_response_received', None))
        self.assertEqual({k: v for k, v in receipt['provider_attachment_errors'].items() if k in FIELDS},
                         {f: [] for f in FIELDS})

    def test_a_response_without_a_url_needs_reconciliation(self):
        receipt = self.launch(ok(url=None))
        self.assertEqual(receipt['status'], 'provider_result_requires_reconciliation_no_retry')
        self.assertTrue(receipt['error'])

    def test_cli_exits_non_zero_on_a_rejected_attachment(self):
        source = (ROOT / 'scripts/progress_subgoal_v1_package.py').read_text(encoding='utf-8')
        self.assertIn("        if receipt.get('error'):\n            raise SystemExit(1)", source)


if __name__ == '__main__':
    unittest.main()
