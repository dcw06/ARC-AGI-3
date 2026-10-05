"""Decision worksheet: generated blank and separate from the decisions file; returned worksheets are validated
(artifact bindings, required fields, conditions, conflicts) and imported only through the exact confirmed preview.
All writes in these tests go to temporary copies."""
import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import plan_wheelhouse_r2_bundle as P
from scripts import wheelhouse_decision_worksheet as W

ROOT = Path(__file__).resolve().parents[1]


class Generated(unittest.TestCase):
    def setUp(self):
        self.rows = W.read_csv(W.WORKSHEET)
        self.inventory = W.read_csv(W.INVENTORY_CSV)

    def test_one_blank_row_per_artifact_bound_to_its_hash(self):
        self.assertEqual(sorted((r['artifact'], r['sha256']) for r in self.rows),
                         sorted((r['artifact'], r['sha256']) for r in self.inventory))
        self.assertTrue(all(not r[k] for r in self.rows for k in W.REVIEWER))
        self.assertEqual(list(self.rows[0]), W.COLUMNS)

    def test_priority_nvidia_rows_come_first_and_are_flagged(self):
        self.assertEqual([r['distribution'] for r in self.rows[:4]], list(W.PRIORITY))
        for r in self.rows[:4]:
            self.assertIn('PRIORITY', r['additional_obligations'])
            self.assertIn('QUALIFIED REVIEW REQUIRED', r['additional_obligations'])
            self.assertIn('NVIDIA terms', r['additional_obligations'])

    def test_no_approval_is_prefilled(self):
        self.assertNotIn('approved', {r['proposed_disposition'] for r in self.rows})
        self.assertEqual({r['redistribution_decision'] for r in P.read_decisions(P.DECISIONS_CSV)}, {'unresolved'})

    def test_lock_binds_the_inputs(self):
        lock = json.loads(W.LOCK.read_text())
        self.assertEqual(lock['worksheet_sha256'], W.sha256(W.WORKSHEET))
        self.assertEqual(lock['inventory_sha256'], W.sha256(W.INVENTORY_CSV))
        self.assertEqual(len(lock['context_sha256']), 174)

    def test_never_overwritten(self):
        with self.assertRaises(SystemExit):
            W.generate()


class Returned(unittest.TestCase):
    """Validation and import against temporary copies of the decisions file and preview paths."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        shutil.copy(P.DECISIONS_CSV, self.tmp / 'decisions.csv')
        for name, value in (('DECISIONS_CSV', self.tmp / 'decisions.csv'), ('PREVIEW_JSON', self.tmp / 'p.json'),
                            ('PREVIEW_MD', self.tmp / 'p.md')):
            patcher = mock.patch.object(W, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.rows = W.read_csv(W.WORKSHEET)

    def returned(self, edits=None, rows=None):
        rows = [dict(r) for r in (rows if rows is not None else self.rows)]
        for r in rows:
            r.update((edits or {}).get(r['artifact'], {}))
        path = self.tmp / f'returned-{len(list(self.tmp.iterdir()))}.csv'
        with path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=W.COLUMNS, lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
        return path

    def decide(self, artifact, **fields):
        base = {'reviewer_decision': 'approved', 'reviewer_rationale': 'MIT text verified',
                'reviewer_required_notices': 'LICENSE', 'reviewer_name': 'reviewer', 'reviewer_date': '2026-10-05'}
        base.update(fields)
        return {artifact: base}

    def first(self, tier='conditional'):
        return next(r['artifact'] for r in self.rows if r['priority'] == tier)

    def test_unchanged_worksheet_proposes_nothing(self):
        (preview, _), errors = W.validate(self.returned())
        self.assertEqual((errors, preview['changes'], preview['warnings']), ([], [], []))
        self.assertEqual(preview['counts_after'], {'unresolved': 174})

    def test_a_valid_decision_is_a_proposed_change(self):
        artifact = self.first()
        (preview, resulting), errors = W.validate(self.returned(self.decide(artifact)))
        self.assertEqual(errors, [])
        self.assertEqual([c['artifact'] for c in preview['changes']], [artifact])
        self.assertEqual(preview['counts_after'], {'unresolved': 173, 'approved': 1})
        self.assertFalse(preview['build_eligible_after'])

    def test_required_fields_and_conditions(self):
        artifact = self.first()
        bad = {
            'unknown decision': {'reviewer_decision': 'ok'},
            'no rationale': {'reviewer_rationale': ''},
            'no reviewer': {'reviewer_name': ''},
            'bad date': {'reviewer_date': '5 Oct 2026'},
            'approved with conditions listed': {'reviewer_conditions': 'ship NOTICE'},
            'conditional without conditions': {'reviewer_decision': 'approved_with_conditions'},
            'more satisfactions than conditions': {'reviewer_decision': 'approved_with_conditions',
                                                   'reviewer_conditions': 'ship NOTICE',
                                                   'reviewer_conditions_satisfied': 'a | b'},
        }
        for label, fields in bad.items():
            with self.subTest(case=label):
                _, errors = W.validate(self.returned(self.decide(artifact, **fields)))
                self.assertTrue(errors, label)

    def test_unsatisfied_conditions_are_recorded_but_block_the_build(self):
        artifact = self.first()
        (preview, _), errors = W.validate(self.returned(self.decide(
            artifact, reviewer_decision='approved_with_conditions', reviewer_conditions='ship NOTICE | cite source',
            reviewer_conditions_satisfied='LICENSES/x/NOTICE')))
        self.assertEqual(errors, [])
        self.assertTrue(any('build stays blocked' in w for w in preview['warnings']))

    def test_restricted_is_flagged_as_a_bundle_blocker(self):
        artifact = W.PRIORITY[3]
        name = next(r['artifact'] for r in self.rows if r['distribution'] == artifact)
        (preview, _), errors = W.validate(self.returned(self.decide(
            name, reviewer_decision='restricted', reviewer_rationale='no grant for the compiled files')))
        self.assertEqual(errors, [])
        self.assertTrue(any('blocks the bundle' in w for w in preview['warnings']))

    def test_artifact_binding_and_coverage(self):
        artifact = self.first()
        _, errors = W.validate(self.returned({artifact: {'sha256': '0' * 64}}))
        self.assertTrue(any('artifact binding' in e for e in errors))
        _, errors = W.validate(self.returned(rows=self.rows[1:]))
        self.assertTrue(any(e.startswith('no row for') for e in errors))
        _, errors = W.validate(self.returned(rows=self.rows + self.rows[:1]))
        self.assertTrue(any(e.startswith('duplicate row') for e in errors))
        _, errors = W.validate(self.returned({artifact: {'reviewer_name': 'someone'}}))
        self.assertTrue(any('reviewer_decision is blank' in e for e in errors))

    def test_edited_context_is_reported(self):
        artifact = self.first()
        (preview, _), errors = W.validate(self.returned({artifact: {'proposed_disposition': 'approved'}}))
        self.assertTrue(any('context columns were edited' in w for w in preview['warnings']))

    def test_a_recorded_decision_is_never_replaced(self):
        artifact = self.first()
        rows = P.read_decisions(W.DECISIONS_CSV)
        for row in rows:
            if row['artifact'] == artifact:
                row.update(redistribution_decision='excluded', rationale='earlier decision', resolver='r',
                           decided_on='2026-10-01')
        W.DECISIONS_CSV.write_bytes(W.decisions_bytes(rows))
        _, errors = W.validate(self.returned(self.decide(artifact)))
        self.assertTrue(any('would replace a recorded decision' in e for e in errors))

    def test_import_only_through_the_confirmed_preview(self):
        artifact = self.first()
        path = self.returned(self.decide(artifact))
        with self.assertRaises(SystemExit):  # no preview written yet
            W.do_import(path, '0' * 64)
        (preview, _), errors = W.validate(path)
        digest = W.write_preview(preview)
        before = W.DECISIONS_CSV.read_bytes()
        with self.assertRaises(SystemExit):
            W.do_import(path, '0' * 64)
        self.assertEqual(W.DECISIONS_CSV.read_bytes(), before)
        W.do_import(path, digest)
        imported = {d['artifact']: d for d in P.read_decisions(W.DECISIONS_CSV)}
        self.assertEqual(imported[artifact]['redistribution_decision'], 'approved')
        self.assertEqual(imported[artifact]['resolver'], 'reviewer')
        self.assertEqual(sum(d['redistribution_decision'] == 'unresolved' for d in imported.values()), 173)

    def test_import_refuses_when_validation_fails(self):
        artifact = self.first()
        path = self.returned(self.decide(artifact, reviewer_rationale=''))
        result, errors = W.validate(path)
        digest = W.write_preview(result[0])
        before = W.DECISIONS_CSV.read_bytes()
        with self.assertRaises(SystemExit):
            W.do_import(path, digest)
        self.assertEqual(W.DECISIONS_CSV.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
