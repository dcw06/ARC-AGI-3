"""Decision worksheet r2: r1 preserved under its own lock; r2 bound to r1 and the evidence packs; each returned
worksheet validated against its own revision; r1 entries on changed rows flagged; carried entries reconfirmed where
the evidence changed; recorded decisions on changed rows flagged. All writes go to temporary copies."""
import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import plan_wheelhouse_r2_bundle as P
from scripts import wheelhouse_decision_worksheet as W
from scripts import wheelhouse_worksheet_r2 as R


class Revisions(unittest.TestCase):
    def setUp(self):
        self.r1 = W.read_csv(W.WORKSHEET)
        self.r2 = W.read_csv(W.WORKSHEET_R2)
        self.lock1 = json.loads(W.LOCK.read_text())
        self.lock2 = json.loads(W.LOCK_R2.read_text())
        self.comparison = json.loads(W.COMPARISON_JSON.read_text())

    def test_r1_is_unchanged_under_its_own_lock(self):
        self.assertEqual(W.sha256(W.WORKSHEET), self.lock1['worksheet_sha256'])
        self.assertNotIn('worksheet_revision', self.r1[0])
        self.assertEqual(self.lock2['parent'], {'revision': 1, 'worksheet_sha256': self.lock1['worksheet_sha256'],
                                                'lock_sha256': W.sha256(W.LOCK)})

    def test_r2_is_blank_and_bound_to_the_evidence(self):
        self.assertEqual(len(self.r2), 174)
        self.assertEqual({r['worksheet_revision'] for r in self.r2}, {'r2'})
        self.assertTrue(all(not r[k] for r in self.r2 for k in list(W.REVIEWER) + W.CARRY))
        self.assertEqual(W.sha256(W.WORKSHEET_R2), self.lock2['worksheet_sha256'])
        for name, digest in self.lock2['evidence_packs'].items():
            self.assertEqual(W.sha256(R.EVIDENCE / name), digest, name)
        self.assertEqual({r['artifact']: W.row_digest(r, W.CONTEXT_R2) for r in self.r2},
                         self.lock2['context_sha256'])

    def test_own_nvidia_licence_rows_lose_the_toolkit_question(self):
        for rows, expected in ((self.r1, True), (self.r2, False)):
            for r in rows:
                if r['distribution'] in ('cuda_python', 'cuda_bindings'):
                    self.assertEqual(R.NVIDIA_GENERIC in r['additional_obligations'], expected, r['distribution'])

    def test_comparison_lists_every_changed_row(self):
        changed = {c['artifact'] for c in self.comparison['rows'] if c['changed_fields']}
        self.assertEqual(self.comparison['rows_changed'], len(changed))
        by1 = {r['artifact']: r for r in self.r1}
        for r in self.r2:
            differs = any(by1[r['artifact']][f] != r[f] for f in W.CONTEXT) or bool(r['evidence_checks'])
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
        changes = W.evidence_changes()
        self.changed = next(a for a in sorted(changes))
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

    def filled(self, source, columns, entries):
        rows = [dict(r) for r in W.read_csv(source)]
        for r in rows:
            r.update(entries.get(r['artifact'], {}))
        return self.write(rows, columns)

    def test_each_revision_validates_against_its_own_lock(self):
        for source, columns, revision in ((W.WORKSHEET, W.COLUMNS, 1), (W.WORKSHEET_R2, W.COLUMNS_R2, 2)):
            (preview, _), errors = W.validate(self.filled(source, columns, {}))
            self.assertEqual((errors, preview['warnings'], preview['worksheet_revision']), ([], [], revision))
        rows = W.read_csv(W.WORKSHEET_R2)
        rows[0]['worksheet_revision'] = 'r1'
        result, errors = W.validate(self.write(rows, W.COLUMNS_R2))
        self.assertIsNone(result)
        self.assertIn('mixed', errors[0])

    def test_r1_entries_on_changed_rows_are_flagged_not_reinterpreted(self):
        path = self.filled(W.WORKSHEET, W.COLUMNS, {self.changed: self.entry(), self.unchanged: self.entry()})
        (preview, _), errors = W.validate(path)
        self.assertEqual(errors, [])
        flagged = [w for w in preview['warnings'] if 'decided on r1 evidence' in w]
        self.assertEqual(len(flagged), 1)
        self.assertIn(self.changed, flagged[0])
        by_artifact = {c['artifact']: c for c in preview['changes']}
        self.assertTrue(by_artifact[self.changed]['affected_by_newer_evidence'])
        self.assertEqual(by_artifact[self.unchanged]['affected_by_newer_evidence'], [])
        self.assertEqual(by_artifact[self.changed]['worksheet_revision'], 1)

    def test_carried_entries_need_reconfirmation_only_where_evidence_changed(self):
        returned = self.filled(W.WORKSHEET, W.COLUMNS, {self.changed: self.entry(), self.unchanged: self.entry()})
        out = self.tmp / 'carried.csv'
        summary = R.carry_forward(returned, out)
        self.assertEqual(summary, {'carried': 2, 'require_reconfirmation': [self.changed]})
        _, errors = W.validate(out)
        self.assertEqual(len(errors), 1)
        self.assertIn(self.changed, errors[0])
        self.assertIn('reconfirm', errors[0])
        rows = W.read_csv(out)
        for r in rows:
            if r['artifact'] == self.changed:
                r['reviewer_reconfirmed_for_r2'] = 'yes'
        (preview, _), errors = W.validate(self.write(rows, W.COLUMNS_R2))
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
        (preview, _), _ = W.validate(self.filled(W.WORKSHEET_R2, W.COLUMNS_R2, {}))
        self.assertTrue(any('predates evidence changed in r2' in w and self.changed in w for w in preview['warnings']))


if __name__ == '__main__':
    unittest.main()
