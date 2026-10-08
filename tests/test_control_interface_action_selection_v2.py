# Derived by scripts/derive_control_interface_v2_tests.py; additional scientific tests are separate.
"""Scientific isolation, independent scoring, bounded request admission and real HTTP fixture regressions."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.control_interface_action_selection_v2 import binding as B, notebook as N, probe as P
from research.control_interface_action_selection_v2 import runtime_controls as C
from certification.direct_publisher_smoke_v1.accounting import Clock, Ledger, RequestRefused

ROOT = Path(__file__).resolve().parents[1]
SERVED = 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8'


def response(content, finish='stop', model=SERVED):
    return json.dumps({'model': model, 'choices': [{'finish_reason': finish, 'message': {'content': content}}],
                      'usage': {'prompt_tokens': 100, 'completion_tokens': 24}})


def records(cases):
    by_id = {c['case_id']: c for c in cases}
    rows = []
    for item in P.schedule(cases):
        case = by_id[item['case_id']]
        k = case['observation']['legal_actions'][0]
        content = json.dumps({'action': {'action_id': k, 'action_data': {'x': 1, 'y': 2} if k == 6 else {}}})
        raw = response(content)
        rows.append({**item, 'http_status': 200, 'response': raw, 'response_sha256': hashlib.sha256(raw.encode()).hexdigest(),
                     'request_sha256': P.digest(P.request_for(case, item['arm'], SERVED))})
    return rows


def gated_fixture(root):
    """Fabricated authority in a disposable test directory; never a real approval or reservation."""
    def put(name, value):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((json.dumps(value, sort_keys=True, indent=2) + '\n').encode())
    def sha(name):
        return B.sha256(root / name)
    for name in N.source_names(ROOT):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / name).read_bytes())
    protocol = B.load_protocol(ROOT)
    protocol['kernel_id'] = 'fixture/paired'
    protocol['model'].update(kaggle_source='fixture/paired-model/1', mounted_path='/kaggle/input/paired-model')
    put(B.PROTOCOL, protocol)
    N.build_review(root / 'notebooks/control-interface-action-selection-v2-review-r1', root=root)
    lock = B.review_lock(root)
    dataset = {k: protocol['dataset'][k] for k in ('ref', 'version')}
    provider, facts = 'private/fixture-provider.json', 'private/fixture-assessment.json'
    put(provider, {'authenticated_account': 'fixture', 'dataset_attachments': [dict(dataset, attachment_confirmed=True)]})
    put(B.ACCOUNT, {'status': 'verified', 'scope': B.SCOPE, 'dataset': dataset, 'consuming_account': 'fixture',
                   'verified_at': 'fixture-only', 'provider_evidence': provider, 'provider_evidence_sha256': sha(provider)})
    put(facts, {'consuming_account': 'fixture', 'dataset': dataset, **{k: 'fabricated fixture only' for k in
        ('licence_holder', 'recipients_and_roles', 'access_controls', 'publication_intent', 'applicable_agreements',
         'output_and_payload_handling', 'licence_evidence')}})
    put(B.PERMISSION, {'status': 'approved', 'approval_kind': 'direct_consumption_permission', 'scope': B.SCOPE,
        'dataset': protocol['dataset'], 'review_lock_sha256': sha(lock), 'protocol_sha256': sha(B.PROTOCOL),
        'trusted_artifacts_sha256': protocol['bundle']['approved_manifest_sha256'],
        'requirements_lock_sha256': protocol['bundle']['requirements_lock_sha256'],
        'permission_outcome': 'permitted_for_reviewed_use', 'outstanding_conditions': [],
        'reviewer_response': 'fabricated fixture only', 'reviewed_at': 'fixture-only',
        'use_assessment': facts, 'use_assessment_sha256': sha(facts)})
    put(B.BYTES, {'integrity_passed': True, 'wheel_bytes_verified': 174, 'dataset_ref': dataset['ref'], 'requested_version': 1,
                 'trusted_artifacts_sha256': protocol['bundle']['approved_manifest_sha256'],
                 'installation_requirements_sha256': protocol['bundle']['requirements_lock_sha256']})
    common = {'status': 'approved', 'scope': B.SCOPE, 'review_lock_sha256': sha(lock), 'approved_at': 'fixture-only',
              'user_response': 'fabricated fixture only', 'evidence_bindings': {n: sha(n) for n in B.evidence_names(root)}}
    put(B.SOURCE, dict(common, approval_kind='source'))
    put(B.COMPUTE, dict(common, approval_kind='compute', source_approval_sha256=sha(B.SOURCE),
        protocol_sha256=sha(B.PROTOCOL), dataset=protocol['dataset'], **{k: protocol['limits'][k] for k in B.COMPUTE_LIMITS}))
    execution = {'scope': B.SCOPE, 'attempt_id': 'cia-fixture0001', 'review_lock': lock, 'review_sha256': sha(lock),
                 'source_approval_sha256': sha(B.SOURCE), 'compute_approval_sha256': sha(B.COMPUTE)}
    put(B.EXECUTION, execution)
    put(B.RESERVATION, {'status': 'reserved', 'attempt_id': execution['attempt_id'], 'execution_sha256': sha(B.EXECUTION), 'events': ['reserve']})
    put(B.CLAIM, {'status': 'claimed', 'attempt_id': execution['attempt_id'], 'execution_sha256': sha(B.EXECUTION),
                  'reservation_sha256': sha(B.RESERVATION), 'claimed_at': 'fixture-only'})
    return put


class ScientificChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = P.load_cases(ROOT)

    def test_only_treatment_field_changes(self):
        for case in self.cases:
            a, b = (P.request_for(case, arm, SERVED) for arm in P.ARMS)
            reference = P.loads(a['messages'][1]['content'])
            candidate = P.loads(b['messages'][1]['content'])
            self.assertEqual(candidate['observation'].pop(P.FIELD), P.control_metadata(reference['observation']['legal_actions']))
            self.assertEqual(reference, candidate)
            b['messages'][1]['content'] = a['messages'][1]['content']
            self.assertEqual(a, b)
            self.assertEqual(a['response_format'], {'type': 'json_object'})

    def test_v3_metadata_matches_exactly(self):
        from research.evidence_comprehension_v3.representation import control_metadata
        for case in self.cases:
            legal = case['observation']['legal_actions']
            self.assertEqual(P.control_metadata(legal), control_metadata(legal))

    def test_counterbalanced_complete_schedule(self):
        plan = P.schedule(self.cases)
        self.assertEqual(len(plan), 120)
        self.assertEqual([(r['case_id'], r['arm']) for r in plan[60:]],
                         list(reversed([(r['case_id'], r['arm']) for r in plan[:60]])))
        self.assertEqual(len({(r['case_id'], r['arm'], r['pass_number']) for r in plan}), 120)

    def test_reference_can_choose_illegal_action_despite_json_mode(self):
        self.assertFalse(P.validate('{"action":{"action_id":0,"action_data":{}}}', [1, 6])['valid'])

    def test_coordinate_and_simple_rules_reject_bool_extra_keys_and_bad_shapes(self):
        for value in [{'action': {'action_id': True, 'action_data': {}}},
                      {'action': {'action_id': 1, 'action_data': {'x': 0}}},
                      {'action': {'action_id': 6, 'action_data': {'x': 64, 'y': 0}}},
                      {'action': {'action_id': 6, 'action_data': {'x': 0, 'y': False}}},
                      {'action': {'action_id': 6, 'action_data': {}}},
                      {'action': {'action_id': 1, 'action_data': {}}, 'rationale': 'extra'}]:
            self.assertFalse(P.validate(json.dumps(value), [1, 6])['valid'])
        self.assertTrue(P.validate('{"action":{"action_id":6,"action_data":{"x":0,"y":63}}}', [6])['valid'])

    def test_duplicate_keys_and_nonfinite_rejected(self):
        for raw in ['{"action":{"action_id":0,"action_id":1,"action_data":{}}}', '{"action":NaN}']:
            self.assertFalse(P.validate(raw, [1])['valid'])

    def test_independent_scorer_ignores_forged_validity(self):
        rows = records(self.cases)
        rows[0]['response'] = response('{"action":{"action_id":0,"action_data":{}}}')
        rows[0]['response_sha256'] = hashlib.sha256(rows[0]['response'].encode()).hexdigest()
        rows[0]['validation'] = {'valid': True}
        score = P.score(self.cases, rows, SERVED)
        self.assertEqual(score['paired_contexts']['improved'], 1)
        self.assertEqual(score['arms']['reference']['valid_both_passes'], 29)
        self.assertEqual(score['decision'], 'development_diagnostic_only_no_policy_promotion')

    def test_missing_duplicate_reordered_and_tampered_records_are_incomplete(self):
        rows = records(self.cases)
        variants = [rows[:-1], [rows[0]] + rows[:-1], list(reversed(rows))]
        tampered = copy.deepcopy(rows)
        tampered[0]['request_sha256'] = '0' * 64
        variants.append(tampered)
        tampered = copy.deepcopy(rows)
        tampered[0]['response'] += ' '
        variants.append(tampered)
        for rows in variants:
            with self.assertRaises(ValueError):
                P.score(self.cases, rows, SERVED)

    def test_truncation_transport_model_and_usage_fail_technical_check(self):
        for raw in [response('{}', finish='length'), response('{}', model='wrong'), '{}',
                    response('{}').replace('"prompt_tokens": 100', '"prompt_tokens": 60001')]:
            with self.assertRaises(ValueError):
                P.completion(raw, SERVED)

    def test_complete_scoring_and_game_clusters(self):
        score = P.score(self.cases, records(self.cases), SERVED)
        self.assertEqual(score['paired_contexts']['both_valid'], 30)
        self.assertEqual(len(score['by_game']), 15)
        self.assertEqual(score['game_actions'], 0)


class RuntimeChecks(unittest.TestCase):
    def test_extracted_notebook_default_verifier_loads_all_trusted_inputs(self):
        from scripts.check_control_interface_embedded_inputs import check
        notebook, metadata, bindings, pending = N.review_notebook(ROOT)
        result = check(notebook, package='research.control_interface_action_selection_v2')
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['trusted_wheels'], 174)
        self.assertFalse(result['gpu_used'])

    def test_source_gate_requires_shared_proposal_binding(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            notebook, metadata, bindings, pending = N.review_notebook(ROOT)
            lock = {'scope': B.SCOPE, 'gpu_enabled': False, 'bindings': dict(bindings)}
            lock['bindings'].pop('certification/direct_publisher_smoke_v1/proposal.json', None)
            for name in lock['bindings']:
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes((ROOT / name).read_bytes())
            p = root / 'notebooks/lock.json'
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(lock))
            with self.assertRaisesRegex(ValueError, 'reviewed sources incomplete'):
                B.check_sources(root, 'notebooks/lock.json')

    def test_complete_new_scope_gate_and_notebook_binding_in_fabricated_fixture(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            gated_fixture(root)
            protocol, execution = B.require_live(root)
            self.assertEqual(protocol['limits']['maximum_model_requests'], 131)
            artifacts = N.launch_artifacts(root)
            metadata = json.loads(artifacts['kernel-metadata.json'])
            self.assertTrue(metadata['enable_gpu'])  # artifacts only; nothing is submitted or run
            self.assertTrue(metadata['is_private'])
            self.assertEqual(metadata['machine_shape'], 'NvidiaRtxPro6000')
            notebook = json.loads(artifacts['profile.ipynb'])
            self.assertIn('research.control_interface_action_selection_v2.run', notebook['cells'][1]['source'])
            self.assertIn('fixture/paired-model/1', metadata['dataset_sources'])

    def test_prior_scope_or_twelve_request_authority_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            put = gated_fixture(root)
            compute = B.read_json(root, B.COMPUTE)
            for fields in ({'scope': 'direct-publisher-smoke-v1'}, {'maximum_model_requests': 12}):
                put(B.COMPUTE, {**compute, **fields})
                with self.assertRaises(B.LiveRefused):
                    B.require_live(root)

    def test_new_scope_consume_guard_refuses_second_session_local_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            gated_fixture(root)
            working = root / 'working'
            working.mkdir()
            B.consume(root, working)
            with self.assertRaises(FileExistsError):
                B.consume(root, working)

    def test_old_smoke_authority_cannot_authorize_new_scope(self):
        with self.assertRaises(B.LiveRefused) as caught:
            B.require_live(ROOT)
        self.assertIn('authorization:', str(caught.exception))
        self.assertNotEqual(B.SCOPE, 'direct-publisher-smoke-v1')

    def test_complete_import_closure_and_source_drift(self):
        with tempfile.TemporaryDirectory() as folder:
            lock = N.build_review(Path(folder) / 'review', root=ROOT)
        common = 'certification/direct_publisher_smoke_v1/install.py'
        self.assertIn(common, lock['bindings'])
        self.assertIn(P.PACKAGE + '/token-audit.json', lock['bindings'])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, digest in lock['bindings'].items():
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes((ROOT / name).read_bytes())
            p = root / 'notebooks/lock.json'
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps(lock))
            B.check_sources(root, 'notebooks/lock.json')
            (root / common).write_text('# changed')
            with self.assertRaisesRegex(ValueError, 'source drift'):
                B.check_sources(root, 'notebooks/lock.json')

    def test_request_cap_and_no_repeat_or_unplanned_request(self):
        protocol = B.load_protocol(ROOT)
        clock = Clock(protocol['limits'], 0, now=lambda: 1)
        ledger = Ledger(protocol['requests'], 131, clock)
        for item in protocol['requests']:
            for _ in range(item.get('max_issues', 1)):
                ledger.admit(item['id'])
        self.assertEqual(len(ledger.entries), 131)
        for item in ('E000', 'NOT_PLANNED'):
            with self.assertRaises(RequestRefused):
                ledger.admit(item)

    def test_cache_config_missing_enabled_or_conflicting_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'server.log'
            for text in ['', 'enable_prefix_caching=True', "enable_prefix_caching=False\nenable_prefix_caching': True"]:
                p.write_text(text)
                with self.assertRaises(ValueError):
                    C.verify_cache_disabled(p)
            p.write_text("enable_prefix_caching': False\nenable_prefix_caching=False")
            self.assertTrue(C.verify_cache_disabled(p)['disabled'])

    def test_phase_overrun_retains_response_and_restores_cleanup_clock(self):
        protocol = B.load_protocol(ROOT)
        elapsed = [0]
        clock = Clock(protocol['limits'], 0, now=lambda: elapsed[0])
        original = clock.limits
        class Client:
            served = SERVED
            def call(self, request_id, body):
                elapsed[0] = 1501
                return 200, response('{}').encode()
        from research.control_interface_action_selection_v2.evidence import Evidence
        with tempfile.TemporaryDirectory() as folder:
            evidence = Evidence(Path(folder) / 'evidence', 'rehearsal')
            with self.assertRaisesRegex(TimeoutError, 'phase deadline after response'):
                P.run_cases(ROOT, Client(), evidence, clock)
            partial = json.loads((evidence.folder / 'action-selection/answers/E000.json').read_bytes())
            self.assertEqual(partial['status'], 'received')
        self.assertIs(clock.limits, original)
        self.assertEqual(clock.cleanup_deadline(), 3420)

    def test_frozen_derivation_reproduces(self):
        from scripts.build_control_interface_action_selection_v2 import build
        for name, data in build(ROOT).items():
            self.assertEqual((ROOT / name).read_bytes(), data, name)

    def test_uncertain_submission_is_consumed_and_cannot_be_retried(self):
        from research.control_interface_action_selection_v2 import launch as L
        class Backend:
            calls = 0
            def push(self, folder):
                self.calls += 1
                raise TimeoutError('simulated uncertain response')
        artifacts = {'kernel-metadata.json': b'{"id":"fixture/paired"}',
                     'launch-package-lock.json': b'{"attempt_id":"cia-fixture0001"}'}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            package = root / 'launch'
            package.mkdir()
            for name, data in artifacts.items():
                (package / name).write_bytes(data)
            backend = Backend()
            with patch.object(L, 'launch_artifacts', return_value=artifacts):
                with self.assertRaises(TimeoutError):
                    L.submit(root, package, backend)
                receipt = json.loads((root / B.RECEIPT).read_bytes())
                self.assertEqual(receipt['status'], 'submission_uncertain')
                with self.assertRaises(L.LaunchRefused):
                    L.submit(root, package, backend)
            self.assertEqual(backend.calls, 1)


class FullHttpRehearsal(unittest.TestCase):
    def check_scenario(self, fault):
        from research.control_interface_action_selection_v2.rehearsal import scenario
        with tempfile.TemporaryDirectory() as folder:
            result = scenario(ROOT, Path(folder) / 'attempt', fault)
            self.assertTrue(result['cleanup_verified'], result.get('cleanup'))
            self.assertTrue(result['lifecycle_deadline']['met'])
            self.assertEqual(result['evidence_class'], 'scripted_cpu_rehearsal')
            self.assertFalse(result['gpu_compatibility_evidence'])
            self.assertLessEqual(result['ledger']['issued'], 131)
            return result

    def test_nominal_complete_http_plan(self):
        result = self.check_scenario('none')
        self.assertTrue(result['passed'], result.get('error'))
        self.assertEqual(result['action_selection']['research_responses'], 120)

    def test_semantic_invalid_is_measured_not_repaired_or_retried(self):
        result = self.check_scenario('semantic_invalid')
        self.assertTrue(result['passed'], result.get('error'))
        self.assertEqual(result['action_selection']['paired_contexts']['neither_valid'], 30)

    def test_truncated_response_fails_and_cleans_up(self):
        result = self.check_scenario('truncated')
        self.assertFalse(result['passed'])
        self.assertEqual(result['failed_stage'], 'action_selection')
        self.assertEqual(result['ledger']['issued'], 8)

    def test_timeout_fails_and_cleans_up_without_retry(self):
        result = self.check_scenario('timeout')
        self.assertFalse(result['passed'])
        self.assertEqual(result['failed_stage'], 'action_selection')
        self.assertEqual(result['ledger']['issued'], 8)


if __name__ == '__main__':
    unittest.main()
