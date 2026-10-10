"""Track 2 Stage 1 successor packages on the verified runtime: derivation, scientific invariance, request plan, live
gate, notebooks and the import closure (CPU only; no GPU, provider call, approval or reservation)."""
import copy
import functools
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from research.evidence_memory_v1 import protocol as P, stage1 as ST, tokens as TK
from research.evidence_memory_v1.run import schedule as S, score as SC
from research.evidence_memory_v1.successor import plan as PL

ROOT = Path(__file__).resolve().parents[1]
FOUND = TK.locate()
BUILDER = 'scripts/build_evidence_memory_v1_sessions.py'
SESSIONS = {label: importlib.import_module(spec['module'] + '.binding') for label, spec in PL.SESSIONS.items()}
NOTEBOOKS = {label: importlib.import_module(spec['module'] + '.notebook') for label, spec in PL.SESSIONS.items()}
# The public checkout holds the development stand-ins. In the owner's private checkout the packages hold withheld
# sets: tests that compare against stand-in numbers, or that would read withheld truths, are skipped there.
STAND_INS = all(PL.load_frozen(ROOT, spec['package'])[0]['case_source'] == 'development_stand_in'
                for spec in PL.SESSIONS.values())
# Review snapshots: r5 makes the recall decoding schema the exact enum of the eight valid answers (owner decision,
# October 10, 2026); r4 binds the owner's withheld-seed commitment (gate 1) and the holder rule in the frozen
# protocol's section 5; r3 adds the review-document check to the repository-side gates and the live evaluation; r2
# binds the frozen protocol (reports/evidence_memory_v1_protocol_v2_frozen.md); r1 (the draft). r1 and r2 are
# kept byte-identical as history, at the lock hashes recorded when they were built (r3 too).
# Whether the owner has committed the withheld seed (gate 1); before that the commitment is a placeholder.
SEED_COMMITTED = (json.loads((ROOT / 'research/evidence_memory_v1/successor/seed-commitment.json').read_bytes())
                  ['withheld_seed_sha256'] != PL.SEED_PLACEHOLDER)
LATEST_REVIEW_REVISION = 5
RETAINED_REVIEW_LOCKS = {'A': {1: '5539e1266c5fd6ccad5881878a9b5699b822dd7d97b82e3ff9f02ea2e7246b41',
                               2: '750ea373200bd89a9ee15a325cf11265bceb0b90cd5e5ba94a8d56c2ba1f4dd9',
                               3: 'fbad29c7f48f35025d849d6faee35de35368daae001a5356a16ecc58aaca669a',
                               4: 'c6c89b3af1d6203e6b14cbd358f78c1b0706766f14314955dfe17f1050dba7d4'},
                         'B': {1: 'fb94736b47c2aee8d3b98f07fc912a8f8f3f2b12c4e24bd158f1504c671fe39f',
                               2: '372963785c0526cb523eb374a7ae52b1d071fd83e955c556b7b594a8d35212b8',
                               3: '84407411a1e054284adffb52a09d15561883b9aa1010c76442c463687e2601b6',
                               4: 'f9a480b81d97689070dcdb09aa45864c5636e4a52020962fdd36113d0c247832'}}


def builder():
    spec = importlib.util.spec_from_file_location('em1_builder', ROOT / BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_blob(revision, path):
    try:
        return subprocess.run(['git', 'show', f'{revision}:{path}'], cwd=ROOT, capture_output=True, check=True,
                              timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return None


class Derivation(unittest.TestCase):
    def test_the_committed_packages_are_exactly_the_derivation(self):
        for name, data in builder().build().items():
            self.assertEqual((ROOT / name).read_bytes(), data, name)

    def test_vendored_verified_runtime_is_byte_identical_to_its_record(self):
        b = builder()
        self.assertEqual(b.SOURCES['basis_commit'], b.BASIS_COMMIT)
        for origin, digest in b.REFERENCE_SHA256.items():
            self.assertEqual(hashlib.sha256(b.vendored(origin)).hexdigest(), digest, origin)
        self.assertEqual(len([o for o in b.REFERENCE_SHA256 if o.startswith(b.SHARED + '/')]), 18)

    def test_vendored_verified_runtime_equals_the_basis_commit(self):
        b = builder()
        if git_blob(b.BASIS_COMMIT, b.SHARED + '/run.py') is None:
            self.skipTest('the basis commit is not available in this clone')
        for origin in b.REFERENCE_SHA256:
            self.assertEqual(git_blob(b.BASIS_COMMIT, origin), b.vendored(origin), origin)

    def test_reused_track2_sources_are_unchanged_from_the_baseline(self):
        # Unchanged except the owner's protocol-freeze amendments, each applied exactly to the baseline file.
        b = builder()
        if git_blob(b.TRACK2_BASELINE, 'research/evidence_memory_v1/stage1.py') is None:
            self.skipTest('the Track 2 baseline commit is not available in this clone')
        self.assertEqual(set(b.FREEZE_AMENDMENTS), {'research/evidence_memory_v1/stage1.py',
                                                    'research/evidence_memory_v1/protocol.py'})
        for path in b.TRACK2_REUSED:
            baseline = git_blob(b.TRACK2_BASELINE, path)
            expected = b.amended(path, baseline) if path in b.FREEZE_AMENDMENTS else baseline
            self.assertEqual(expected, (ROOT / path).read_bytes(), path)
            if path in b.FREEZE_AMENDMENTS:
                self.assertEqual(b.baseline_of(path), baseline, path)

    def test_no_file_of_the_track2_baseline_was_modified_or_removed(self):
        b = builder()
        if git_blob(b.TRACK2_BASELINE, 'research/evidence_memory_v1/stage1.py') is None:
            self.skipTest('the Track 2 baseline commit is not available in this clone')
        listing = subprocess.run(['git', 'diff', '--name-status', '--no-renames', b.TRACK2_BASELINE], cwd=ROOT,
                                 capture_output=True, text=True, check=True, timeout=60).stdout
        changed = [line for line in listing.splitlines() if line and not line.startswith('A\t')]
        # The successor only adds files; the protocol freeze modifies exactly the amended modules and the two test
        # files covering those decisions. Every other earlier artifact (protocol drafts, the run package, its
        # stand-in, reports, the Linux verification record) is byte-identical.
        self.assertEqual(sorted(changed), sorted(f'M\t{p}' for p in (*b.FREEZE_AMENDMENTS, *b.FREEZE_AMENDED_TESTS)))
        for label, spec in PL.SESSIONS.items():
            derivation = json.loads((ROOT / spec['package'] / 'derivation.json').read_bytes())
            self.assertEqual(derivation['baseline_files_modified'],
                             sorted([*b.FREEZE_AMENDMENTS, *b.FREEZE_AMENDED_TESTS]))
            for path, record in derivation['track2_amended_at_protocol_freeze'].items():
                self.assertEqual(record['baseline_sha256'],
                                 hashlib.sha256(git_blob(b.TRACK2_BASELINE, path)).hexdigest(), path)

    def test_every_derived_source_names_its_origin_and_no_reference_name_remains(self):
        for label, spec in PL.SESSIONS.items():
            derivation = json.loads((ROOT / spec['package'] / 'derivation.json').read_bytes())
            self.assertFalse(derivation['scientific_configuration_changed'])
            for target, origin in derivation['derived'].items():
                text = (ROOT / target).read_text(encoding='utf-8')
                self.assertTrue(text.startswith('# Derived by ' + BUILDER + ' from ' + origin), target)
                for residue in ('control_interface', 'control-interface', 'action_selection'):
                    self.assertNotIn(residue, text.split('\n', 1)[1], target)


class ScientificConfigurationUnchanged(unittest.TestCase):
    def test_protocol_binds_the_reviewed_prompts_arms_budgets_schedule_and_stop_rules(self):
        for label, binding in SESSIONS.items():
            protocol = binding.load_protocol(ROOT)
            e = protocol['experiment']
            self.assertEqual(e['system_sha256'], hashlib.sha256(P.SYSTEM.encode()).hexdigest())
            self.assertEqual((e['arms'], e['primary_arms'], e['reference_arm']),
                             (list(ST.ARM_ORDER), list(P.ARMS), P.REFERENCE))
            self.assertEqual((e['max_tokens'], e['temperature'], e['request_seed']), (64, 0, 0))
            self.assertEqual(protocol['sampling'], {'seed': 0, 'temperature': 0})
            self.assertEqual(e['per_call_seconds'], {'timeout': S.PER_CALL_TIMEOUT_SECONDS, 'teardown': S.TEARDOWN_SECONDS,
                                                     'verify': S.CANCELLATION_VERIFY_SECONDS,
                                                     'bound': S.PER_CALL_BOUND_SECONDS})
            self.assertEqual((e['max_consecutive_timeouts'], e['invalid_rate_max']), (2, 0.02))
            limits = protocol['limits']
            self.assertEqual({k: limits[k] for k in ('authorized_seconds', 'internal_seconds', 'admission_cutoff_seconds',
                                                     'cleanup_reserve_seconds', 'maximum_attempts', 'automatic_retries')},
                             {'authorized_seconds': 3600, 'internal_seconds': 3300, 'admission_cutoff_seconds': 3000,
                              'cleanup_reserve_seconds': 300, 'maximum_attempts': 1, 'automatic_retries': 0})
            self.assertEqual(limits['admission_cutoff_seconds'], S.ADMISSION_CUTOFF_SECONDS)
            self.assertEqual(e['groups'], list(ST.SESSIONS[label]))
            self.assertEqual(e['passes']['pass_1'], 2592)
            if STAND_INS:  # the repeat groups are drawn from the frozen set's seed
                self.assertEqual(e['passes']['pass_2'], {'A': 304, 'B': 240}[label])
                self.assertEqual(e['scheduled_calls'], {'A': 2896, 'B': 2832}[label])
            argv = protocol['server']['argv']
            self.assertEqual(argv.count('--no-enable-prefix-caching'), 1)
            self.assertNotIn('--enable-prefix-caching', argv)

    @unittest.skipUnless(STAND_INS, 'the packages hold withheld sets')
    def test_session_a_stand_in_is_the_reviewed_run_package_stand_in(self):
        self.assertEqual((ROOT / PL.SESSIONS['A']['package'] / 'probes.json').read_bytes(), ST.RUN_PROBES.read_bytes())

    @unittest.skipUnless(FOUND and STAND_INS, 'needs the pinned tokenizer files and the development stand-ins')
    def test_session_frozen_sets_are_fresh_builds_with_the_reviewed_seed_and_repeat(self):
        tokenizer = TK.Tokenizer(FOUND)
        for label, spec in PL.SESSIONS.items():
            raw = (ROOT / spec['package'] / 'probes.json').read_bytes()
            self.assertEqual(raw, ST.encode(ST.build(label, tokenizer=tokenizer)), label)
            frozen = json.loads(raw)
            self.assertEqual(frozen['seed_sha256'], hashlib.sha256(b'evidence-memory-v1-development').hexdigest())
            self.assertEqual([tuple(fg) for fg in frozen['repeat_groups']],
                             [fg for fg in ST.repeat_groups('evidence-memory-v1-development') if fg[1] in ST.SESSIONS[label]])

    def test_requests_are_the_reviewed_requests_and_the_audit_binds_them(self):
        for label, spec in PL.SESSIONS.items():
            frozen, digest = PL.load_frozen(ROOT, spec['package'])
            audit = json.loads((ROOT / spec['package'] / 'token-audit.json').read_bytes())
            counts = PL.validate_audit(audit, frozen, digest)
            contexts = {c['context_id']: c for c in frozen['contexts']}
            probes = {p['probe_id']: p for p in frozen['probes']}
            for row in audit['requests'][::97]:
                probe = probes[row['probe_id']]
                request = ST.build_request(contexts[probe['context_id']], probe)
                self.assertEqual(row['request_sha256'], PL.request_sha256(request))
                self.assertEqual(request['max_tokens'], 64)
                self.assertTrue(request['response_format']['json_schema']['strict'])
            self.assertEqual(audit['tokenizer'], PL.PINNED_TOKENIZER)
            if STAND_INS:
                self.assertEqual(max(counts.values()), {'A': 1247, 'B': 1249}[label])

    def test_tampered_audit_or_frozen_set_is_refused(self):
        frozen, digest = PL.load_frozen(ROOT, PL.SESSIONS['A']['package'])
        audit = json.loads((ROOT / PL.SESSIONS['A']['package'] / 'token-audit.json').read_bytes())
        for change in ('count', 'parity', 'order', 'passed', 'frozen'):
            bad = copy.deepcopy(audit)
            if change == 'count':
                bad['requests'][5]['prompt_tokens'] = bad['requests'][5]['pure_python_prompt_tokens'] = 70000
            elif change == 'parity':
                bad['requests'][5]['pure_python_prompt_tokens'] += 1
            elif change == 'order':
                bad['requests'][4], bad['requests'][5] = bad['requests'][5], bad['requests'][4]
            elif change == 'passed':
                bad['passed'] = False
            else:
                bad['frozen_set_sha256'] = '0' * 64
            with self.assertRaises(ValueError, msg=change):
                PL.validate_audit(bad, frozen, digest)


@unittest.skipUnless(STAND_INS, 'stand-in numbers; never computed on withheld truths')
class Distinguishability(unittest.TestCase):
    """Writer fidelity, selection and reading stay separately measurable in the pooled analysis."""

    @classmethod
    def setUpClass(cls):
        cls.frozen = {label: PL.load_frozen(ROOT, spec['package'])[0] for label, spec in PL.SESSIONS.items()}

    def pooled(self, answer):
        rows = []
        for frozen in self.frozen.values():
            passes = {'pass_1': {p['probe_id']: SC.score(p, answer(p)) for p in frozen['probes']}}
            rows += SC.rows_by_pass(frozen, passes)['pass_1']
        return P.analyze_rows({arm: [r for r in rows if r['arm'] == arm] for arm in SC.ARMS}, resamples=200)

    @staticmethod
    def package_reader(probe):
        package = probe['package']
        return json.dumps({'values': package} if probe['kind'] == 'recall' else
                          {'choice': package[0] if package else probe['question']['candidates'][0]})

    def test_an_exact_package_reader_reproduces_the_availability_ceilings(self):
        result = self.pooled(self.package_reader)
        primary = {arm: result['primary_endpoint'][arm]['estimate'] for arm in P.ARMS}
        self.assertEqual({arm: round(v, 2) for arm, v in primary.items()},
                         {'recent_raw': 0.0, 'state_keyed_raw': 0.9, 'memory': 0.9})
        self.assertEqual(result['reference_full_history']['estimate'], 1.0)
        restricted = result['contrasts']['memory_vs_state_keyed_raw_evidence_in_both']
        self.assertEqual((restricted['eligible_questions'], restricted['excluded_questions']), (144, 24))
        self.assertEqual(result['primary_endpoint']['memory']['questions'], 168)
        for arm in P.ARMS:  # an exact reader reads every package perfectly: selection, not reading, limits access
            self.assertEqual(result['diagnostics'][arm]['reading_accuracy_package_has_evidence'][0], 1.0)
        self.assertEqual(result['conclusions']['verdict'], 'memory_preserves_access_not_shown_over_retrieval')

    def test_a_misreading_reader_lowers_reading_accuracy_without_changing_availability(self):
        def misread(probe):
            if (probe['arm'] == 'memory' and probe['kind'] == 'recall' and probe['package'] != ['no_evidence']
                    and int(hashlib.sha256(probe['probe_id'].encode()).hexdigest(), 16) % 5 == 0):
                wrong = [v for v in P.VALUES if v not in probe['package']][:1] or ['no_evidence']
                return json.dumps({'values': wrong})
            return self.package_reader(probe)
        exact, noisy = self.pooled(self.package_reader), self.pooled(misread)
        reading = noisy['diagnostics']['memory']['reading_accuracy_package_has_evidence'][0]
        self.assertLess(reading, 0.9)
        self.assertEqual(noisy['diagnostics']['state_keyed_raw'], exact['diagnostics']['state_keyed_raw'])
        restricted = noisy['contrasts']['memory_vs_state_keyed_raw_evidence_in_both']
        self.assertEqual((restricted['eligible_questions'], restricted['excluded_questions']), (144, 24))
        self.assertLess(restricted['estimate'], 0)  # a representation-specific reading loss, at equal availability

    def test_invalid_answers_are_judged_separately_in_each_pass(self):
        frozen = self.frozen['B']
        probes = {p['probe_id']: p for p in frozen['probes']}
        passes = {block['pass']: {i: SC.score(probes[i], json.dumps(probes[i]['key'])) for i in block['probe_ids']}
                  for block in frozen['schedule']}
        self.assertEqual(SC.technical(frozen, passes)['technical_status'], 'session_technically_valid')
        repeat = frozen['schedule'][1]['probe_ids']
        for i in [i for i in repeat if probes[i]['arm'] == 'memory'][:2]:
            passes['pass_2'][i] = SC.score(probes[i], 'not json')
        report = SC.technical(frozen, passes)
        self.assertTrue(report['invalid_by_pass']['pass_1']['rule_met'])
        self.assertFalse(report['invalid_by_pass']['pass_2']['by_arm']['memory']['rule_met'])
        self.assertEqual(report['technical_status'], 'session_technically_invalid_outputs')
        self.assertNotIn('correct', json.dumps(report))


class RequestPlan(unittest.TestCase):
    def test_plan_keeps_the_verified_probes_and_counts_every_study_request(self):
        b = builder()
        reference = json.loads(b.vendored(b.V2 + '/protocol.json'))['requests']
        prefix, suffix = PL.split_reference(reference)
        for label, binding in SESSIONS.items():
            protocol = binding.load_protocol(ROOT)
            plan, n = protocol['requests'], protocol['experiment']['scheduled_calls']
            self.assertEqual(plan[:7], prefix)
            self.assertEqual(plan[-3:], suffix)
            self.assertEqual(len({r['id'] for r in plan}), len(plan))
            self.assertEqual(PL.idle_reads(), 65)
            verified = sum(r.get('max_issues', 1) for r in prefix + suffix)  # S1-S3, I1-I4, C1, C2 (twice), C3
            self.assertEqual(verified, 11)
            self.assertEqual(protocol['limits']['maximum_model_requests'], verified + 1 + n * (1 + 1 + 65))
            self.assertEqual([r['id'] for r in plan[7:11]], ['K0000', 'Q00000', 'M00000', 'V00000'])

    def test_ledger_admits_only_the_plan_and_stops_at_the_cutoff(self):
        from certification.direct_publisher_smoke_v1.accounting import Clock, Ledger, RequestRefused
        protocol = SESSIONS['B'].load_protocol(ROOT)
        elapsed = [1]
        clock = Clock(protocol['limits'], 0, now=lambda: elapsed[0])
        ledger = Ledger(protocol['requests'], protocol['limits']['maximum_model_requests'], clock)
        ledger.admit('Q00000')
        for item in ('Q00000', 'Q02832', 'E000', 'NOT_PLANNED'):
            with self.assertRaises(RequestRefused):
                ledger.admit(item)
        for _ in range(65):
            ledger.admit('V00001')
        with self.assertRaises(RequestRefused):
            ledger.admit('V00001')
        elapsed[0] = 3000
        with self.assertRaises(RequestRefused):
            ledger.admit('Q00002')


def fabricated_session_a_evaluation():
    """A fabricated technically complete, live, withheld session-A evaluation in the shape successor/evaluate.py
    writes, over the committed stand-in set with every key answer (fixture only; never a real record or result)."""
    return copy.deepcopy(_fabricated_session_a_evaluation())


@functools.lru_cache(maxsize=1)
def _fabricated_session_a_evaluation():
    package = PL.SESSIONS['A']['package']
    frozen, _ = PL.load_frozen(ROOT, package)
    protocol = json.loads((ROOT / package / 'protocol.json').read_bytes())
    probes = {p['probe_id']: p for p in frozen['probes']}
    passes = {block['pass']: {i: SC.score(probes[i], json.dumps(probes[i]['key'])) for i in block['probe_ids']}
              for block in frozen['schedule']}
    technical = dict(SC.technical(frozen, passes), case_source='withheld')
    calls = sum(len(b['probe_ids']) for b in frozen['schedule'])
    return {'fixture': 'fabricated for tests only; not an evaluation of any run', 'mode': 'live', 'session': 'A',
            'package': package, 'frozen_set_sha256': protocol['experiment']['frozen_set_sha256'],
            'case_source': 'withheld', 'limits': protocol['limits'], 'lifecycle_passed': True, 'lifecycle_errors': [],
            'run_evidence': {'verified': True, 'recovered': False}, 'call_errors': [],
            'run': {'status': 'complete', 'stop_reason': None, 'calls_recorded': calls, 'scheduled_calls': calls},
            'gate_status': 'complete', 'gate': {'questionnaire': technical['technical_status']},
            'analysis': technical, 'technically_complete': True, 'exact_provider_billed_seconds': None,
            'phase4_complete': False}


def put_session_a_record(root, record):
    """Retain a (fabricated) session-A evaluation at the fixed path in a fixture checkout; returns its SHA-256."""
    from research.evidence_memory_v1.successor import session_order
    data = (json.dumps(record, indent=1) + '\n').encode() if isinstance(record, dict) else record
    path = root / session_order.RECORD
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def gated_fixture(root, label='A', session_a_record=True, named=None):
    """Fabricated authority in a disposable directory; never a real approval, reservation or claim. Returns the
    writer and the patches that enable the live path for this fixture only (LIVE_ENABLED, withheld-set check).
    For session B it also retains a session-A evaluation (True: a fabricated technically complete one; a dict or
    bytes: that record; False: none) and names `named`, or the retained record's SHA-256, in the fabricated compute
    authorization (nothing is named when there is neither)."""
    B, N = SESSIONS[label], NOTEBOOKS[label]

    def put(name, value):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((json.dumps(value, sort_keys=True, indent=2) + '\n').encode())

    def sha(name):
        return B.sha256(root / name)
    for name in N.source_names(ROOT) + list(N.REVIEW_DOCUMENTS) + [PL.SESSIONS['A']['package'] + '/protocol.json']:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / name).read_bytes())
    order = {}
    if label == 'B':
        record = fabricated_session_a_evaluation() if session_a_record is True else session_a_record
        digest = put_session_a_record(root, record) if record is not False else None
        if (named or digest) is not None:
            order['session_a_technical_evaluation_sha256'] = named or digest
    protocol = json.loads((ROOT / B.PROTOCOL).read_bytes())
    protocol['kernel_id'] = 'fixture/em1'
    protocol['model'].update(kaggle_source='fixture/em-model/1', mounted_path='/kaggle/input/em-model')
    protocol['experiment']['withheld_seed_sha256'] = 'f' * 64
    put(B.PROTOCOL, protocol)
    N.build_review(root / f"notebooks/{PL.SESSIONS[label]['scope']}-review-r1", root=root)
    lock = B.review_lock(root)
    dataset = {k: protocol['dataset'][k] for k in ('ref', 'version')}
    provider, facts = 'private/fixture-provider.json', 'private/fixture-assessment.json'
    put(provider, {'authenticated_account': 'fixture', 'dataset_attachments': [dict(dataset, attachment_confirmed=True)]})
    put(B.ACCOUNT, {'status': 'verified', 'scope': B.SCOPE, 'dataset': dataset, 'consuming_account': 'fixture',
                    'verified_at': 'fixture-only', 'provider_evidence': provider, 'provider_evidence_sha256': sha(provider)})
    put(facts, {'consuming_account': 'fixture', 'dataset': dataset, **{k: 'fabricated fixture only' for k in (
        'licence_holder', 'recipients_and_roles', 'access_controls', 'publication_intent', 'applicable_agreements',
        'output_and_payload_handling', 'licence_evidence')}})
    put(B.PERMISSION, {'status': 'approved', 'approval_kind': 'direct_consumption_permission', 'scope': B.SCOPE,
                       'dataset': protocol['dataset'], 'review_lock_sha256': sha(lock), 'protocol_sha256': sha(B.PROTOCOL),
                       'trusted_artifacts_sha256': protocol['bundle']['approved_manifest_sha256'],
                       'requirements_lock_sha256': protocol['bundle']['requirements_lock_sha256'],
                       'permission_outcome': 'permitted_for_reviewed_use', 'outstanding_conditions': [],
                       'reviewer_response': 'fabricated fixture only', 'reviewed_at': 'fixture-only',
                       'use_assessment': facts, 'use_assessment_sha256': sha(facts)})
    put(B.BYTES, {'integrity_passed': True, 'wheel_bytes_verified': 174, 'dataset_ref': dataset['ref'],
                  'requested_version': 1, 'trusted_artifacts_sha256': protocol['bundle']['approved_manifest_sha256'],
                  'installation_requirements_sha256': protocol['bundle']['requirements_lock_sha256']})
    common = {'status': 'approved', 'scope': B.SCOPE, 'review_lock_sha256': sha(lock), 'approved_at': 'fixture-only',
              'user_response': 'fabricated fixture only', 'evidence_bindings': {n: sha(n) for n in B.evidence_names(root)}}
    put(B.SOURCE, dict(common, approval_kind='source'))
    put(B.COMPUTE, dict(common, approval_kind='compute', source_approval_sha256=sha(B.SOURCE),
                        protocol_sha256=sha(B.PROTOCOL), dataset=protocol['dataset'],
                        **{k: protocol['limits'][k] for k in B.COMPUTE_LIMITS}, **order))
    execution = {'scope': B.SCOPE, 'attempt_id': PL.SESSIONS[label]['attempt'] + '-fixture0001', 'review_lock': lock,
                 'review_sha256': sha(lock), 'source_approval_sha256': sha(B.SOURCE),
                 'compute_approval_sha256': sha(B.COMPUTE)}
    put(B.EXECUTION, execution)
    put(B.RESERVATION, {'status': 'reserved', 'attempt_id': execution['attempt_id'], 'execution_sha256': sha(B.EXECUTION),
                        'events': ['reserve']})
    put(B.CLAIM, {'status': 'claimed', 'attempt_id': execution['attempt_id'], 'execution_sha256': sha(B.EXECUTION),
                  'reservation_sha256': sha(B.RESERVATION), 'claimed_at': 'fixture-only'})
    controls = importlib.import_module(PL.SESSIONS[label]['module'] + '.runtime_controls')
    return put, [patch.object(B, 'LIVE_ENABLED', True),
                 patch.object(controls, 'live_frozen_set_reasons', lambda root, protocol: [])]


class LiveGate(unittest.TestCase):
    def test_this_checkout_refuses_every_session_for_every_independent_reason(self):
        for label, B in SESSIONS.items():
            with self.assertRaises(B.LiveRefused) as caught:
                B.require_live(ROOT)
            reasons = ' | '.join(caught.exception.reasons)
            expected_reasons = ['LIVE_ENABLED is False']
            if STAND_INS:  # the public checkout: placeholders and the stand-in refuse independently
                expected_reasons += ['unresolved placeholders', 'kernel_id', 'model.kaggle_source',
                                     'model.mounted_path', "case source is 'development_stand_in'",
                                     'committed withheld seed']
                if not SEED_COMMITTED:
                    expected_reasons.append('experiment.withheld_seed_sha256')
                else:  # the committed seed is no longer a placeholder; the stand-in still refuses
                    self.assertNotIn('experiment.withheld_seed_sha256', reasons, label)
            for expected in expected_reasons:
                self.assertIn(expected, reasons, label)
            self.assertFalse(B.LIVE_ENABLED)

    def test_refusal_reads_no_approval_while_live_is_disabled(self):
        B = SESSIONS['A']
        with patch.object(B, 'check_sources') as sources, patch.object(B, 'check_approvals') as approvals, \
                patch.object(B, 'check_evidence') as evidence, patch.object(B, 'check_reservation') as reservation:
            with self.assertRaises(B.LiveRefused):
                B.require_live(ROOT)
        for mock in (sources, approvals, evidence, reservation):
            mock.assert_not_called()

    def test_complete_fabricated_authority_passes_only_with_live_enabled_and_a_withheld_set(self):
        for label in PL.SESSIONS:
            B, N = SESSIONS[label], NOTEBOOKS[label]
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                put, patches = gated_fixture(root, label)
                for p in patches:
                    p.start()
                try:
                    protocol, execution = B.require_live(root)
                    artifacts = N.launch_artifacts(root)
                finally:
                    for p in reversed(patches):
                        p.stop()
                metadata = json.loads(artifacts['kernel-metadata.json'])
                self.assertTrue(metadata['enable_gpu'] and metadata['is_private'])  # artifacts only; nothing submitted
                self.assertEqual(metadata['machine_shape'], 'NvidiaRtxPro6000')
                self.assertIn('fixture/em-model/1', metadata['dataset_sources'])
                self.assertIn(f"{protocol['dataset']['ref']}/{protocol['dataset']['version']}", metadata['dataset_sources'])
                self.assertEqual(metadata['competition_sources'], ['arc-prize-2026-arc-agi-3'])
                self.assertIn(PL.SESSIONS[label]['module'] + '.run', json.loads(artifacts['profile.ipynb'])['cells'][1]['source'])
                controls = importlib.import_module(PL.SESSIONS[label]['module'] + '.runtime_controls')
                for live_enabled, frozen_ok in ((False, True), (True, False)):  # either gate alone still refuses
                    patches = [patch.object(B, 'LIVE_ENABLED', live_enabled)]
                    if frozen_ok:
                        patches.append(patch.object(controls, 'live_frozen_set_reasons', lambda root, protocol: []))
                    for p in patches:
                        p.start()
                    try:
                        with self.assertRaises(B.LiveRefused):
                            B.require_live(root)
                    finally:
                        for p in reversed(patches):
                            p.stop()

    def test_review_document_drift_refused_before_launch_and_before_evaluation(self):
        from research.evidence_memory_v1.successor import evaluate as EV
        for label in PL.SESSIONS:
            B, N = SESSIONS[label], NOTEBOOKS[label]
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                put, patches = gated_fixture(root, label)
                lock = B.review_lock(root)
                bound = B.read_json(root, lock)['bindings']
                self.assertLessEqual(set(B.REVIEW_REQUIRED), set(B.read_json(root, lock)['review_documents']))
                self.assertEqual(EV.review_errors(root, label)[0], [])
                self.assertTrue(all(t not in bound for t in B.REVIEW_REQUIRED))  # review documents only
                for p in patches:
                    p.start()
                try:
                    B.require_live(root)
                    for target in B.REVIEW_REQUIRED:
                        original = (root / target).read_bytes()
                        (root / target).write_bytes(original + b'\n')
                        with self.assertRaises(B.LiveRefused) as caught:
                            B.require_live(root)
                        self.assertIn('review document drift: ' + target, str(caught.exception))
                        with self.assertRaisesRegex(Exception, 'review document drift'):
                            N.launch_artifacts(root)
                        self.assertTrue(any('review document drift' in e for e in EV.review_errors(root, label)[0]))
                        B.require_live(root, review_documents=False)  # the runtime payload never carries them
                        (root / target).write_bytes(original)
                    B.require_live(root)
                    value = B.read_json(root, lock)
                    del value['review_documents']['research/evidence_memory_v1/successor/evaluate.py']
                    (root / lock).write_bytes(json.dumps(value).encode())
                    with self.assertRaisesRegex(B.LiveRefused, 'review documents incomplete'):
                        B.require_live(root)
                finally:
                    for p in reversed(patches):
                        p.stop()

    def test_one_session_authority_cannot_run_the_other(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            put, patches = gated_fixture(root, 'A')
            B = SESSIONS['B']
            controls = importlib.import_module(PL.SESSIONS['B']['module'] + '.runtime_controls')
            with patch.object(B, 'LIVE_ENABLED', True), patch.object(controls, 'live_frozen_set_reasons',
                                                                     lambda root, protocol: []):
                with self.assertRaises(B.LiveRefused):
                    B.require_live(root)

    @unittest.skipUnless(os.name == 'posix', 'the reviewed run evidence is POSIX-only (fcntl)')
    def test_the_study_phase_refuses_the_development_stand_in_live(self):
        from research.evidence_memory_v1.successor.study import run_study

        class Evidence:
            mode, folder = 'live', Path('unused')

        with self.assertRaisesRegex(PermissionError, 'not withheld'):
            run_study(ROOT, PL.SESSIONS['A']['package'], None, Evidence(), None)

    def test_live_frozen_set_check_accepts_only_the_committed_withheld_set(self):
        protocol = SESSIONS['A'].load_protocol(ROOT)
        frozen, digest = PL.load_frozen(ROOT, PL.SESSIONS['A']['package'])
        self.assertTrue(PL.live_frozen_set_reasons(ROOT, protocol, PL.SESSIONS['A']['package']))
        fake = copy.deepcopy(protocol)
        fake['experiment'].update(case_source='withheld', withheld_seed_sha256=frozen['seed_sha256'])
        with patch.object(PL, 'load_frozen', return_value=({**frozen, 'case_source': 'withheld'}, digest)):
            self.assertEqual(PL.live_frozen_set_reasons(ROOT, fake, PL.SESSIONS['A']['package']), [])
            fake['experiment']['withheld_seed_sha256'] = '0' * 64
            self.assertTrue(PL.live_frozen_set_reasons(ROOT, fake, PL.SESSIONS['A']['package']))


class Notebooks(unittest.TestCase):
    def test_review_notebooks_are_gpu_disabled_pinned_and_bound(self):
        for label, N in NOTEBOOKS.items():
            notebook, metadata, bindings, pending = N.review_notebook(ROOT)
            self.assertFalse(metadata['enable_gpu'] or metadata['enable_internet'] or metadata['enable_tpu'])
            self.assertTrue(metadata['is_private'])
            self.assertEqual(metadata['docker_image_pinning_type'], 'original')
            self.assertEqual(metadata['dataset_sources'], ['REPLACE_WITH_MODEL_OWNER/REPLACE_WITH_MODEL_DATASET/1'])
            self.assertEqual(metadata['competition_sources'], ['arc-prize-2026-arc-agi-3'])
            if SEED_COMMITTED:
                self.assertNotIn('experiment.withheld_seed_sha256', pending)
            else:
                self.assertIn('experiment.withheld_seed_sha256', pending)
            for name in PL.STUDY_SOURCES + ('certification/direct_publisher_smoke_v1/install.py',
                                            'certification/direct_publisher_smoke_v1/proposal.json',
                                            PL.SESSIONS[label]['package'] + '/probes.json',
                                            PL.SESSIONS[label]['package'] + '/token-audit.json'):
                self.assertIn(name, bindings)
            self.assertLess(len(N.encode(notebook)), N.SIZE_GUARD)

    def test_source_gate_requires_the_study_closure(self):
        B, N = SESSIONS['A'], NOTEBOOKS['A']
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, _, bindings, _ = N.review_notebook(ROOT)
            for missing in ('research/evidence_memory_v1/successor/service.py',
                            'certification/direct_publisher_smoke_v1/proposal.json'):
                lock = {'scope': B.SCOPE, 'gpu_enabled': False, 'bindings': {k: v for k, v in bindings.items() if k != missing}}
                for name in lock['bindings']:
                    p = root / name
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes((ROOT / name).read_bytes())
                (root / 'notebooks').mkdir(exist_ok=True)
                (root / 'notebooks/lock.json').write_text(json.dumps(lock))
                with self.assertRaisesRegex(ValueError, 'reviewed sources incomplete'):
                    B.check_sources(root, 'notebooks/lock.json')

    @unittest.skipUnless(os.name == 'posix', 'the live closure imports POSIX modules (fcntl)')
    def test_extracted_payload_imports_the_live_path_and_loads_default_verifier_inputs(self):
        for label, spec in PL.SESSIONS.items():
            checker = importlib.import_module(f"scripts.check_{spec['module'].split('.')[-1]}_embedded_inputs")
            notebook, _, bindings, _ = NOTEBOOKS[label].review_notebook(ROOT)
            result = checker.check(notebook, package=spec['module'])
            self.assertTrue(result['passed'], result)
            self.assertEqual(result['trusted_wheels'], 174)
            self.assertEqual(result['modules_outside_payload'], [])
            loaded = set(result['live_modules_imported'])
            self.assertTrue({'research/evidence_memory_v1/successor/study.py', spec['package'] + '/run.py'} <= loaded)
            self.assertTrue(loaded <= set(bindings), loaded - set(bindings))

    @unittest.skipUnless(os.name == 'posix', 'review snapshots are built and reproduced on Linux')
    def test_frozen_review_snapshots_reproduce_and_their_checks_refused_at_the_gate(self):
        # The latest snapshot (r2, the frozen protocol) reproduces from this checkout; r1 (the draft) is kept
        # byte-identical as history, with its receipt.
        for label, spec in PL.SESSIONS.items():
            revision = int(SESSIONS[label].review_lock(ROOT).split('-review-r')[1].split('/')[0])
            self.assertEqual(revision, LATEST_REVIEW_REVISION)
            for n in range(1, revision + 1):
                frozen = ROOT / 'notebooks' / f"{spec['scope']}-review-r{n}"
                lock_raw = (frozen / 'review-source-lock.json').read_bytes()
                lock = json.loads(lock_raw)
                self.assertEqual(lock['status'], 'review_snapshot_not_approved_not_compute_authority')
                self.assertFalse(lock['gpu_enabled'])
                for artifact, digest in lock['artifacts'].items():
                    self.assertEqual(hashlib.sha256((frozen / artifact).read_bytes()).hexdigest(), digest, artifact)
                receipt = json.loads((ROOT / f"reports/{spec['module'].split('.')[-1]}_review_check_r{n}.json")
                                     .read_bytes())
                self.assertTrue(receipt['passed'] and receipt['refused_at_live_gate'])
                self.assertFalse(receipt['nvidia_smi_called'])
                self.assertEqual(receipt['review_lock_sha256'], hashlib.sha256(lock_raw).hexdigest())
                if n in RETAINED_REVIEW_LOCKS[label]:
                    self.assertEqual(hashlib.sha256(lock_raw).hexdigest(), RETAINED_REVIEW_LOCKS[label][n])
                if n == revision:
                    with tempfile.TemporaryDirectory() as folder:
                        NOTEBOOKS[label].build_review(Path(folder) / 'review', root=ROOT)
                        for name in ('profile.ipynb', 'kernel-metadata.json', 'review-source-lock.json'):
                            self.assertEqual((frozen / name).read_bytes(),
                                             (Path(folder) / 'review' / name).read_bytes(), name)

    def test_the_frozen_protocol_and_review_documents_are_bound(self):
        b = builder()
        for label, spec in PL.SESSIONS.items():
            protocol = SESSIONS[label].load_protocol(ROOT)
            self.assertEqual(protocol['protocol_document'], b.PROTOCOL_DOCUMENT)
            self.assertEqual(b.PROTOCOL_DOCUMENT, 'reports/evidence_memory_v1_protocol_v2_frozen.md')
            self.assertTrue((ROOT / b.PROTOCOL_DOCUMENT).is_file())
            documents = NOTEBOOKS[label].REVIEW_DOCUMENTS
            self.assertEqual(documents, b.review_documents(b.Session(label)))
            for required in (b.PROTOCOL_DOCUMENT, 'scripts/check_evidence_memory_v1_structured_outputs.py',
                             'reports/evidence_memory_v1_successor/structured_outputs_check_r3.json'):
                self.assertIn(required, documents)
            lock = json.loads((ROOT / SESSIONS[label].review_lock(ROOT)).read_bytes())
            self.assertEqual(sorted(lock['review_documents']), sorted(documents))
            for name, digest in lock['review_documents'].items():
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)
            # the draft protocol is history: kept, never bound as the protocol of record
            self.assertNotIn('reports/evidence_memory_v1_protocol_v2.md', documents)
        receipt = json.loads((ROOT / 'reports/evidence_memory_v1_successor/structured_outputs_check_r3.json')
                             .read_bytes())
        self.assertTrue(receipt['passed'] and receipt['all_track2_schemas_accepted'])
        self.assertEqual(receipt['schemas']['recall']['request_schema'], ST.response_schema('recall'))
        self.assertEqual(receipt['schemas']['decision']['request_schema'], ST.response_schema('decision'))
        self.assertEqual(receipt['decoder_admitted_invalid_answers'], [])
        self.assertTrue(receipt['recall_exhaustive']['decoder_admits_exactly_the_canonical_answers'])
        self.assertTrue(receipt['recall_exhaustive']['every_admitted_answer_scores_valid'])


if __name__ == '__main__':
    unittest.main()
