"""Decision worksheet revisions: every issued revision stays under its own lock and is bound to its parent; each
returned worksheet is validated against its own revision; entries on rows whose evidence changed in a later
revision cannot be imported from the earlier one (fail closed if a comparison is missing or unbound); carried
entries are reconfirmed where the evidence changed; recorded decisions on changed rows are flagged. All writes go to
temporary copies."""
import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import plan_wheelhouse_r2_bundle as P
from scripts import wheelhouse_decision_worksheet as W
from scripts import wheelhouse_worksheet_revision as R


class Issued(unittest.TestCase):
    def setUp(self):
        self.revisions = W.revisions()
        self.latest = W.latest_revision()

    def rows(self, n):
        return W.read_csv(self.revisions[n]['csv'])

    def lock(self, n):
        return json.loads(self.revisions[n]['lock'].read_text())

    def test_at_least_two_revisions_each_unchanged_under_its_own_lock(self):
        self.assertGreaterEqual(self.latest, 2)
        for n in self.revisions:
            with self.subTest(revision=n):
                self.assertEqual(W.sha256(self.revisions[n]['csv']), self.lock(n)['worksheet_sha256'])
                self.assertEqual({r['artifact']: W.row_digest(r, self.revisions[n]['context']) for r in self.rows(n)},
                                 self.lock(n)['context_sha256'])
        self.assertNotIn('worksheet_revision', self.rows(1)[0])

    def test_each_later_revision_is_blank_and_bound_to_its_parent(self):
        for n in range(2, self.latest + 1):
            with self.subTest(revision=n):
                rows, lock = self.rows(n), self.lock(n)
                self.assertEqual(len(rows), 174)
                self.assertEqual({r['worksheet_revision'] for r in rows}, {f'r{n}'})
                self.assertEqual(list(rows[0]), W.columns(n))
                self.assertTrue(all(not r[k] for r in rows for k in list(W.REVIEWER) + W.columns(n)[-2:]))
                self.assertEqual(lock['parent'], {'revision': n - 1, 'worksheet_sha256': self.lock(n - 1)['worksheet_sha256'],
                                                  'lock_sha256': W.sha256(self.revisions[n - 1]['lock'])})

    def test_the_latest_revision_is_derived_from_the_current_evidence(self):
        for name, digest in self.lock(self.latest)['evidence_packs'].items():
            self.assertEqual(W.sha256(R.EVIDENCE / name), digest, name)

    def test_own_nvidia_licence_rows_lose_the_toolkit_question_after_r1(self):
        for n in self.revisions:
            for r in self.rows(n):
                if r['distribution'] in ('cuda_python', 'cuda_bindings'):
                    self.assertEqual(R.NVIDIA_GENERIC in r['additional_obligations'], n == 1, (n, r['distribution']))

    def test_each_comparison_matches_the_rows_it_compares(self):
        for n in range(2, self.latest + 1):
            with self.subTest(comparison=f'r{n - 1}->r{n}'):
                summary = json.loads(W.comparison_files(n)['json'].read_text())
                before = {r['artifact']: r for r in self.rows(n - 1)}
                changed = {c['artifact'] for c in summary['rows'] if c['changed_fields']}
                self.assertEqual(summary['rows_changed'], len(changed))
                for r in self.rows(n):
                    old = before[r['artifact']]
                    differs = any(old.get(f, '') != r.get(f, '') for f in R.COMPARED)
                    self.assertEqual(differs, r['artifact'] in changed, r['artifact'])


class Returned(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        shutil.copy(P.DECISIONS_CSV, self.tmp / 'decisions.csv')
        for name, value in (('DECISIONS_CSV', self.tmp / 'decisions.csv'), ('PREVIEW_JSON', self.tmp / 'p.json'),
                            ('PREVIEW_MD', self.tmp / 'p.md')):
            patcher = mock.patch.object(W, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.latest = W.latest_revision()
        changes = W.evidence_changes(1)
        self.changed = sorted(changes)[0]
        self.unchanged = next(r['artifact'] for r in W.read_csv(W.WORKSHEET) if r['artifact'] not in changes)

    def write(self, rows, columns):
        path = self.tmp / f'w{len(list(self.tmp.iterdir()))}.csv'
        with path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=columns, lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
        return path

    @staticmethod
    def entry(**extra):
        base = {'reviewer_decision': 'approved', 'reviewer_rationale': 'licence text verified',
                'reviewer_required_notices': 'LICENSE', 'reviewer_name': 'reviewer', 'reviewer_date': '2026-10-06'}
        base.update(extra)
        return base

    def filled(self, revision, entries):
        rows = [dict(r) for r in W.read_csv(W.revision_files(revision)['csv'])]
        for r in rows:
            r.update(entries.get(r['artifact'], {}))
        return self.write(rows, W.columns(revision))

    def test_each_revision_validates_against_its_own_lock(self):
        for n in W.revisions():
            with self.subTest(revision=n):
                (preview, _), errors = W.validate(self.filled(n, {}))
                self.assertEqual((errors, preview['warnings'], preview['worksheet_revision']), ([], [], n))
        rows = W.read_csv(W.revision_files(self.latest)['csv'])
        rows[0]['worksheet_revision'] = 'r1'
        result, errors = W.validate(self.write(rows, W.columns(self.latest)))
        self.assertIsNone(result)
        self.assertIn('mixed', errors[0])

    def test_entries_on_rows_changed_later_cannot_be_imported(self):
        """Review P1 on 42c2b4c: an earlier revision's entry must not bypass the later reconfirmation."""
        for n in range(1, self.latest):
            later = W.evidence_changes(n)
            if not later:
                continue
            target = sorted(later)[0]
            with self.subTest(revision=n):
                path = self.filled(n, {target: self.entry()})
                (preview, _), errors = W.validate(path)
                self.assertEqual(len(errors), 1)
                self.assertIn(f'not importable from r{n}', errors[0])
                digest = W.write_preview(preview)
                before = W.DECISIONS_CSV.read_bytes()
                with self.assertRaises(SystemExit):
                    W.do_import(path, digest)
                self.assertEqual(W.DECISIONS_CSV.read_bytes(), before)

    def test_unchanged_r1_rows_and_unresolved_entries_remain_importable(self):
        path = self.filled(1, {self.unchanged: self.entry(), self.changed: {'reviewer_decision': 'unresolved'}})
        (preview, _), errors = W.validate(path)
        self.assertEqual(errors, [])
        by_artifact = {c['artifact']: c for c in preview['changes']}
        self.assertEqual(by_artifact[self.unchanged]['affected_by_newer_evidence'], [])
        self.assertEqual(by_artifact[self.unchanged]['worksheet_revision'], 1)

    def test_approving_every_r1_row_never_makes_the_bundle_eligible(self):
        """The reviewer's reproduction: every row approved on r1 -> one error per changed row, nothing importable."""
        everything = {r['artifact']: self.entry() for r in W.read_csv(W.WORKSHEET)}
        (preview, _), errors = W.validate(self.filled(1, everything))
        self.assertEqual(len([e for e in errors if 'not importable from r1' in e]), len(W.evidence_changes(1)))
        self.assertFalse(preview['build_eligible_after'])

    def test_validation_fails_closed_without_bound_comparisons(self):
        path = self.filled(1, {})
        original = W.comparison_files
        missing = {'json': self.tmp / 'missing.json', 'md': self.tmp / 'missing.md'}
        with mock.patch.object(W, 'comparison_files', lambda n: missing if n == 2 else original(n)):
            result, errors = W.validate(path)
        self.assertIsNone(result)
        self.assertIn('comparison is missing', errors[0])
        stale = self.tmp / 'stale.json'
        data = json.loads(original(2)['json'].read_text())
        stale.write_text(json.dumps(dict(data, r2_worksheet_sha256='0' * 64)))
        with mock.patch.object(W, 'comparison_files',
                               lambda n: {'json': stale, 'md': stale} if n == 2 else original(n)):
            result, errors = W.validate(path)
        self.assertIsNone(result)
        self.assertIn('not bound', errors[0])

    def test_carried_entries_need_reconfirmation_only_where_evidence_changed(self):
        returned = self.filled(1, {self.changed: self.entry(), self.unchanged: self.entry()})
        out = self.tmp / 'carried.csv'
        summary = R.carry_forward(returned, out)
        self.assertEqual(summary, {'carried': 2, 'from': 'r1', 'to': f'r{self.latest}',
                                   'require_reconfirmation': [self.changed]})
        _, errors = W.validate(out)
        self.assertEqual(len(errors), 1)
        self.assertIn(self.changed, errors[0])
        self.assertIn('reconfirm', errors[0])
        rows = W.read_csv(out)
        for r in rows:
            if r['artifact'] == self.changed:
                r[W.reconfirm_column(self.latest)] = 'yes'
        (preview, _), errors = W.validate(self.write(rows, W.columns(self.latest)))
        self.assertEqual(errors, [])
        self.assertEqual({c['carried_from'] for c in preview['changes']}, {'r1'})
        with self.assertRaises(FileExistsError):
            R.carry_forward(returned, out)

    def test_a_recorded_decision_on_a_changed_row_is_flagged(self):
        rows = P.read_decisions(W.DECISIONS_CSV)
        for row in rows:
            if row['artifact'] == self.changed:
                row.update(redistribution_decision='approved', rationale='earlier', resolver='r',
                           decided_on='2026-10-01')
        W.DECISIONS_CSV.write_bytes(W.decisions_bytes(rows))
        (preview, _), _ = W.validate(self.filled(self.latest, {}))
        self.assertTrue(any('changed since r1' in w and self.changed in w for w in preview['warnings']))


if __name__ == '__main__':
    unittest.main()
