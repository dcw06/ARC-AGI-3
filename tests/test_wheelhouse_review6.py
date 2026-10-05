"""Regressions for the review of f1dd4c2/fae8157/f4392cf: the strict Record A build-eligibility rule, the upstream
licence texts (sources and hashes) carried into the bundle plan, and the artifact-specific proposed dispositions
kept apart from the human-owned decisions."""
import csv
import hashlib
import io
import json
import tarfile
import unittest
from pathlib import Path

from scripts import gather_upstream_licenses as G
from scripts import plan_wheelhouse_r2_bundle as P
from scripts import propose_wheelhouse_dispositions as Q

ROOT = Path(__file__).resolve().parents[1]
ROWS = [{'artifact': 'a-1.0-py3-none-any.whl', 'sha256': 'a' * 64}, {'artifact': 'b-1.0-py3-none-any.whl',
                                                                     'sha256': 'b' * 64}]


def decision(row, **overrides):
    d = {'artifact': row['artifact'], 'sha256': row['sha256'], 'redistribution_decision': 'approved',
         'rationale': 'MIT; notices shipped', 'required_notices': 'LICENSE', 'conditions': '',
         'conditions_satisfied': '', 'resolved_questions': '', 'resolver': 'reviewer', 'decided_on': '2026-10-04',
         'worksheet_revision': 'r3', 'evidence_sha256': 'e' * 64}
    d.update(overrides)
    return {k: d[k] for k in P.DECISION_FIELDS}


CURRENT = {r['artifact']: 'e' * 64 for r in ROWS}  # the evidence digests of the latest worksheet (synthetic)


class BuildEligibility(unittest.TestCase):
    def blockers(self, *overrides):
        return P.bundle_eligibility(ROWS, [decision(r, **o) for r, o in zip(ROWS, overrides)], CURRENT)

    def test_fully_approved_is_eligible(self):
        self.assertEqual(self.blockers({}, {}), [])

    def test_conditions_all_documented_as_satisfied_is_eligible(self):
        self.assertEqual(self.blockers({}, {'redistribution_decision': 'approved_with_conditions',
                                            'conditions': 'ship LICENSE | cite source',
                                            'conditions_satisfied': 'LICENSES/b/LICENSE | README line 12'}), [])

    def test_unresolved_restricted_and_excluded_block(self):
        for value in ('unresolved', 'restricted', 'excluded'):
            with self.subTest(value=value):
                found = self.blockers({}, {'redistribution_decision': value})
                self.assertEqual(len(found), 1)
                self.assertIn('blocks the bundle', found[0])

    def test_unsatisfied_or_missing_conditions_block(self):
        cases = [{'conditions': 'ship LICENSE | cite source', 'conditions_satisfied': 'LICENSES/b/LICENSE'},
                 {'conditions': 'ship LICENSE | cite source', 'conditions_satisfied': 'LICENSES/b/LICENSE | '},
                 {'conditions': '', 'conditions_satisfied': ''}]
        for case in cases:
            with self.subTest(case=case):
                self.assertTrue(self.blockers({}, dict(case, redistribution_decision='approved_with_conditions')))

    def test_approved_with_listed_conditions_blocks(self):
        self.assertTrue(self.blockers({}, {'conditions': 'cite source'}))

    def test_rationale_reviewer_and_date_are_required(self):
        for override in ({'rationale': ''}, {'resolver': ' '}, {'decided_on': ''}, {'decided_on': '4 Oct 2026'}):
            with self.subTest(override=override):
                self.assertTrue(self.blockers({}, override))

    def test_stale_hash_and_missing_rows_block(self):
        self.assertTrue(self.blockers({}, {'sha256': 'c' * 64}))
        self.assertTrue(P.bundle_eligibility(ROWS, [decision(ROWS[0])], CURRENT))

    def test_a_decision_counts_only_on_the_current_evidence(self):
        """Review gap on cca0551: approvals without provenance, or made on since-changed evidence, must block."""
        for override in ({'evidence_sha256': ''}, {'evidence_sha256': 'f' * 64}, {'worksheet_revision': '',
                                                                                  'evidence_sha256': ''}):
            with self.subTest(override=override):
                found = self.blockers({}, override)
                self.assertEqual(len(found), 1)
                self.assertIn('not made on the current evidence', found[0])

    def test_old_column_layout_is_a_decision_problem(self):
        old = [{k: v for k, v in decision(r).items() if k not in ('conditions', 'conditions_satisfied')}
               for r in ROWS]
        self.assertTrue(any('columns' in x for x in P.check_decisions(ROWS, old)))

    def test_committed_draft_is_consistent_but_not_eligible(self):
        decisions = P.read_decisions(P.DECISIONS_CSV)
        with P.INVENTORY_CSV.open(encoding='utf-8', newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(P.check_decisions(rows, decisions), [])  # an unresolved draft is not a planning error
        self.assertEqual(len(P.bundle_eligibility(rows, decisions)), len(rows))
        plan = json.loads(P.PLAN_JSON.read_text(encoding='utf-8'))
        self.assertFalse(plan['build_eligibility']['eligible'])
        self.assertIn('unresolved, restricted and excluded block', plan['build_rule'])


class UpstreamLicences(unittest.TestCase):
    def setUp(self):
        self.index = json.loads(P.UPSTREAM_INDEX.read_text(encoding='utf-8'))
        self.plan = json.loads(P.PLAN_JSON.read_text(encoding='utf-8'))

    def test_every_wheel_without_a_licence_has_hashed_sourced_upstream_text(self):
        with P.INVENTORY_CSV.open(encoding='utf-8', newline='') as stream:
            missing = {r['artifact'] for r in csv.DictReader(stream) if r['licence_documents'] == 'none in wheel'}
        self.assertEqual(len(missing), 9)
        by_artifact = {e['artifact']: e for e in self.index}
        self.assertEqual(set(by_artifact), missing)
        for artifact in missing:
            entry = by_artifact[artifact]
            self.assertTrue(entry['found'] and entry['source']['url'].startswith('https://'))
            self.assertRegex(entry['source']['sha256'], '^[0-9a-f]{64}$')
            for f in entry['files']:
                data = (P.UPSTREAM_DIR / f['path']).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), f['sha256'])

    def test_plan_carries_each_upstream_text_the_index_and_notices(self):
        paths = {f['path']: f for f in self.plan['files']}
        for e in self.index:
            for f in e['files']:
                entry = paths[f"LICENSES/{e['artifact']}/UPSTREAM/{Path(f['path']).name}"]
                self.assertEqual(entry['sha256'], f['sha256'])
        self.assertEqual(paths['LICENSES/upstream-sources.json']['sha256'],
                         hashlib.sha256(P.UPSTREAM_INDEX.read_bytes()).hexdigest())
        self.assertIn('NOTICES.md', paths)
        self.assertEqual(self.plan['upstream_licence_documents'], sum(len(e['files']) for e in self.index))

    def test_supervisor_terms_not_only_its_copyright_lines(self):
        entry = next(e for e in self.index if e['artifact'].startswith('supervisor-'))
        self.assertIn('LICENSES.txt', {Path(f['member']).name for f in entry['files']})

    def test_embedded_header_and_named_extra_members(self):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w:gz') as t:
            for name, body in (('pkg-1.0/mod.py', b'#####\n# Copyright X\n# Redistribution permitted\n#####\nimport os\n'),
                               ('pkg-1.0/LICENSES.txt', b'terms'), ('pkg-1.0/code.py', b'print(1)\n')):
                info = tarfile.TarInfo(name)
                info.size = len(body)
                t.addfile(info, io.BytesIO(body))
        data = buffer.getvalue()
        member, header = G.embedded_header(data, 'pkg-1.0.tar.gz', 'mod.py')
        self.assertEqual((member, header), ('pkg-1.0/mod.py', b'#####\n# Copyright X\n# Redistribution permitted\n#####\n'))
        self.assertEqual(G.sdist_members(data, 'pkg-1.0.tar.gz'), [])
        self.assertEqual(G.sdist_members(data, 'pkg-1.0.tar.gz', ['LICENSES.txt']), [('pkg-1.0/LICENSES.txt', b'terms')])


class ProposedDispositions(unittest.TestCase):
    def setUp(self):
        with Q.OUT_CSV.open(encoding='utf-8', newline='') as stream:
            self.proposals = list(csv.DictReader(stream))
        with P.INVENTORY_CSV.open(encoding='utf-8', newline='') as stream:
            self.rows = list(csv.DictReader(stream))

    def test_keyed_by_artifact_and_hash_and_never_plainly_approved(self):
        self.assertEqual([(p['artifact'], p['sha256']) for p in self.proposals],
                         [(r['artifact'], r['sha256']) for r in self.rows])
        self.assertTrue({p['proposed_disposition'] for p in self.proposals} <= Q.PROPOSED_VALUES)

    def test_every_flagged_artifact_has_a_specific_proposal(self):
        for p in self.proposals:
            with self.subTest(artifact=p['artifact']):
                self.assertEqual(p['batch'], '1' if p['flags'] else '2')
                self.assertTrue(p['rationale'] and p['questions_for_reviewer'])
                if p['proposed_disposition'] == 'likely_not_distributable':
                    self.assertTrue(p['alternative_if_not_cleared'])

    def test_a_flagged_artifact_without_a_proposal_is_reported(self):
        row = dict(self.rows[0], artifact='zz-1.0-py3-none-any.whl', distribution='zz', flags='declared_copyleft')
        _, problems = Q.build([row], [])
        self.assertTrue(any('no proposal' in x for x in problems))

    def test_the_generator_does_not_write_the_decisions_file(self):
        paths = [v for v in vars(Q).values() if isinstance(v, Path)]
        self.assertNotIn(P.DECISIONS_CSV, paths)
        self.assertNotIn('DECISIONS', ''.join(vars(Q)))


if __name__ == '__main__':
    unittest.main()
