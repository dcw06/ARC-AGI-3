"""Pending or explicitly unsatisfied text is never condition-satisfaction evidence: one rule shared by worksheet
validation, import previews and bundle eligibility. Regressions use the reviewer-returned r4 workbook retained in
reports/reviewer_submissions/r4_2026-10-06/ (the original 45 PENDING satisfaction entries, of which 37 passed the
old individual eligibility check, and the corrected return). Offline; every write goes to temporary copies."""
import csv
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import plan_wheelhouse_r2_bundle as P
from scripts import wheelhouse_decision_worksheet as W
from scripts.xlsx_values import read_sheets

ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / 'reports/reviewer_submissions/r4_2026-10-06'
CORRECTED = SUBMISSION / 'returned_r4.csv'
WORKBOOK = SUBMISSION / 'conditional_approvals.xlsx'
MOVED = '\n\nPending fulfilment note (moved from reviewer_conditions_satisfied on 2026-10-06): '


def corrected_rows():
    with CORRECTED.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def original_rows():
    """The returned rows as originally submitted: each moved PENDING statement back in the satisfaction field."""
    rows = []
    for row in corrected_rows():
        row = dict(row)
        if MOVED in row['reviewer_conditions']:
            conditions, statement = row['reviewer_conditions'].split(MOVED)
            row.update(reviewer_conditions=conditions, reviewer_conditions_satisfied=statement)
        rows.append(row)
    return rows


def pending_artifacts():
    return [r['artifact'] for r in corrected_rows() if MOVED in r['reviewer_conditions']]


def old_rule_passes(conditions_text, satisfied_text):
    """The defective rule: any non-empty entry per condition counted as satisfied."""
    conditions, satisfied = P.split_conditions(conditions_text), P.split_conditions(satisfied_text)
    return bool(conditions) and len(satisfied) == len(conditions) and all(satisfied)


def decision_from(row, current):
    return {'artifact': row['artifact'], 'sha256': row['sha256'],
            'redistribution_decision': row['reviewer_decision'] or 'unresolved',
            'rationale': row['reviewer_rationale'], 'required_notices': row['reviewer_required_notices'],
            'conditions': row['reviewer_conditions'], 'conditions_satisfied': row['reviewer_conditions_satisfied'],
            'resolved_questions': row['reviewer_resolved_questions'], 'resolver': row['reviewer_name'] or 'reviewer',
            'decided_on': row['reviewer_date'] or '2026-10-06', 'worksheet_revision': 'r4',
            'evidence_sha256': current[row['artifact']]}


def individually_eligible(row, current):
    """Eligibility of one decision on its own (provenance on the current evidence, so only conditions can block)."""
    return not P.bundle_eligibility([{'artifact': row['artifact'], 'sha256': row['sha256']}],
                                    [decision_from(row, current)], current)


class Rule(unittest.TestCase):
    def test_pending_unsatisfied_and_placeholder_text_is_not_evidence(self):
        for text in ('PENDING — not audited', 'pending review', 'Status: Pending.', 'TBD', 'todo: ship NOTICE',
                     'n/a', 'N/A', '-', '—', '?', 'not yet verified', 'condition not met', 'Not satisfied',
                     'sign-off remains required', 'still required', 'no evidence supplied', 'awaiting upstream reply',
                     'to be confirmed by counsel', 'unverified copy of LICENSE', 'in progress', '', '   '):
            with self.subTest(text=text):
                self.assertIsNotNone(P.satisfaction_problem(text))

    def test_documented_fulfilment_is_evidence(self):
        for text in ('LICENSES/x/NOTICE included in the bundle',
                     'Evidence records the required licence document(s) inside the reviewed wheel: '
                     'pkg-1.0.dist-info/licenses/LICENSE (sha256 0123456789ab).',
                     'README line 14 states where the corresponding source is available'):
            with self.subTest(text=text):
                self.assertIsNone(P.satisfaction_problem(text))

    def test_every_populated_entry_in_the_corrected_return_is_accepted(self):
        populated = [r for r in corrected_rows() if r['reviewer_conditions_satisfied'].strip()]
        self.assertEqual(len(populated), 107)
        for r in populated:
            statuses, surplus = P.condition_status(r['reviewer_conditions'], r['reviewer_conditions_satisfied'])
            self.assertEqual(surplus, [])
            self.assertTrue(all(s['satisfied'] for s in statuses), r['artifact'])


class OriginalWorkbook(unittest.TestCase):
    """The 45 PENDING entries as originally submitted in reviewer_conditions_satisfied."""

    def setUp(self):
        self.current = P.current_evidence()[1]
        self.original = {r['artifact']: r for r in original_rows()}
        self.pending = pending_artifacts()

    def test_reconstruction_matches_the_workbook_records(self):
        self.assertEqual(len(self.pending), 45)
        sheets = read_sheets(WORKBOOK)
        notes = [r for r in sheets['Pending_Condition_Notes'] if r and r[0].strip().isdigit()]
        recorded = {r[1]: r[3] for r in notes}
        self.assertEqual(set(recorded), set(self.pending))
        for artifact in self.pending:
            self.assertEqual(self.original[artifact]['reviewer_conditions_satisfied'], recorded[artifact])
        cases = [r for r in sheets['Validator_Regression_Cases'] if r and r[0].startswith('row_')]
        self.assertEqual(len(cases), 90)
        for case in cases:
            expected = recorded[case[2]] if case[0].endswith('_pending_text') else ''
            self.assertEqual(case[5], expected, case[0])
            self.assertEqual(case[6], '0', case[0])

    def test_the_old_rule_passed_37_of_them(self):
        passed = [a for a in self.pending if old_rule_passes(self.original[a]['reviewer_conditions'],
                                                             self.original[a]['reviewer_conditions_satisfied'])]
        self.assertEqual(len(passed), 37)

    def test_none_of_the_45_is_individually_eligible_now(self):
        for artifact in self.pending:
            with self.subTest(artifact=artifact):
                row = self.original[artifact]
                self.assertEqual(row['reviewer_decision'], 'approved_with_conditions')
                self.assertFalse(individually_eligible(row, self.current))
                blockers = P.bundle_eligibility([{'artifact': artifact, 'sha256': row['sha256']}],
                                                [decision_from(row, self.current)], self.current)
                self.assertIn('not fulfilled', blockers[0])

    def test_every_proposed_regression_case_is_ineligible(self):
        """Validator_Regression_Cases: both the original PENDING text and the corrected blank evidence must fail."""
        cases = [r for r in read_sheets(WORKBOOK)['Validator_Regression_Cases'] if r and r[0].startswith('row_')]
        for case in cases:
            with self.subTest(case=case[0]):
                row = dict(self.original[case[2]], reviewer_decision=case[4], reviewer_conditions_satisfied=case[5])
                self.assertEqual(row['sha256'], case[3])
                self.assertFalse(individually_eligible(row, self.current))


class Returned(unittest.TestCase):
    """Worksheet validation and the import preview, on the original and the corrected return (temporary copies)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        shutil.copy(P.DECISIONS_CSV, self.tmp / 'decisions.csv')
        for name, value in (('DECISIONS_CSV', self.tmp / 'decisions.csv'), ('PREVIEW_JSON', self.tmp / 'p.json'),
                            ('PREVIEW_MD', self.tmp / 'p.md')):
            patcher = mock.patch.object(W, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.assertEqual(W.latest_revision(), 4)

    def write(self, rows):
        path = self.tmp / f'returned-{len(list(self.tmp.iterdir()))}.csv'
        with path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=W.columns(4), lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
        return path

    @staticmethod
    def unmet_warnings(preview):
        return [w for w in preview['warnings'] if 'the build stays blocked until all are' in w]

    def test_original_return_shows_all_52_unmet_conditions(self):
        (preview, _), errors = W.validate(self.write(original_rows()))
        self.assertEqual(errors, [])
        unmet = self.unmet_warnings(preview)
        self.assertEqual(len(unmet), 52)  # the old rule reported 15: the 37 PENDING single-condition rows passed
        pending = set(pending_artifacts())
        self.assertEqual(sum(any(a in w for a in pending) for w in unmet), 45)

    def test_corrected_return_keeps_159_conditional_decisions_and_blocks_67(self):
        before = W.DECISIONS_CSV.read_bytes()
        (preview, resulting), errors = W.validate(CORRECTED)
        self.assertEqual(errors, [])
        self.assertEqual(len(self.unmet_warnings(preview)), 52)
        conditional = [c for c in preview['changes'] if c['to'] == 'approved_with_conditions']
        self.assertEqual((len(preview['changes']), len(conditional)), (159, 159))
        by_artifact = {r['artifact']: r for r in corrected_rows()}
        for change in preview['changes']:  # decisions carried over exactly as returned
            row = by_artifact[change['artifact']]
            self.assertEqual((change['after']['conditions'], change['after']['conditions_satisfied']),
                             (row['reviewer_conditions'], row['reviewer_conditions_satisfied']))
        blockers = P.bundle_eligibility(W.read_csv(W.INVENTORY_CSV), resulting)
        unmet = [b for b in blockers if 'documented as satisfied' in b]
        missing = [b for b in blockers if "decision 'unresolved' blocks the bundle" in b]
        self.assertEqual((len(unmet), len(missing), len(blockers)), (52, 15, 67))
        self.assertFalse(preview['build_eligible_after'])
        self.assertEqual(preview['build_blockers_after'], 67)
        self.assertEqual(W.DECISIONS_CSV.read_bytes(), before)  # validation imports nothing

    def test_preview_marks_pending_conditions_as_not_satisfied(self):
        (preview, _), errors = W.validate(self.write(original_rows()))
        artifact = pending_artifacts()[0]
        change = next(c for c in preview['changes'] if c['artifact'] == artifact)
        self.assertEqual(change['satisfied'], 0)
        self.assertFalse(any(s['satisfied'] for s in change['condition_status']))
        W.write_preview(preview)
        text = W.PREVIEW_MD.read_text(encoding='utf-8')
        section = text.split(f'### `{artifact}`')[1].split('### `')[0]
        self.assertIn('**not satisfied** (states the condition is not fulfilled', section)
        self.assertNotIn('— satisfied: PENDING', section)


if __name__ == '__main__':
    unittest.main()
