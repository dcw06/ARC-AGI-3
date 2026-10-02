"""progress_subgoal_v1 runner (GPU-disabled): derivation from the reviewed WS3 stack, adapters, live refusal, request
enumeration for the exact token audit, and one connected CPU rehearsal with the fake server."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from research.progress_subgoal_v1 import derive as D, probes as P, questions as Q

ROOT = Path(__file__).resolve().parents[1]
STAND_IN = P.rehearsal_set()


class Derivation(unittest.TestCase):
    def test_derived_files_match_the_derivation(self):
        self.assertEqual(D.stale(), [])

    def test_ws3_sources_are_unchanged_since_the_derivation(self):
        self.assertEqual(D.source_hashes(), D.SOURCE_SHA256)
        self.assertEqual(set(D.SOURCE_SHA256), set(D.SOURCES.values()))

    def test_every_substitution_is_counted_and_no_ws3_runtime_reference_remains(self):
        for target, text in D.derive().items():
            banner, body = text.split('\n', 1)
            self.assertTrue(banner.startswith('# Derived from '), target)  # the banner names its WS3 source
            for residue in ('research.ws3_questionnaire_v1', 'research/ws3_questionnaire_v1', 'WS3Q_'):
                self.assertNotIn(residue, body, target)

    def test_reused_objects_are_the_reviewed_ones(self):
        from research.evidence_comprehension_v1 import service as SV1, transport as T1
        from research.evidence_comprehension_v2 import evidence as E2, schedule as S2
        from research.progress_subgoal_v1 import evidence as E, schedule as S, service as SV, transport as T
        self.assertIs(S.call_order, S2.call_order)
        self.assertIs(T.CancellableTransport, T1.CancellableTransport)
        self.assertIs(E.RunEvidence, E2.RunEvidence)
        self.assertTrue(issubclass(SV.QuestionnaireService, SV1.QuestionnaireService))


class Adapters(unittest.TestCase):
    def test_runner_shape_and_reviewed_schedule_phases(self):
        from research.progress_subgoal_v1.schedule import call_order
        order = call_order(STAND_IN)
        self.assertEqual(list(dict.fromkeys(o[0] for o in order)),
                         ['withheld_pass_1', 'withheld_pass_2', 'development_pass_1'])
        self.assertEqual({p['partition'] for p in STAND_IN['probes']}, {'withheld', 'development'})
        self.assertEqual(len(order), 5852)

    def test_call_ceiling_and_allow_list_match_the_schedule(self):
        from research.action_effect_history_v1.service import request_hash
        from research.progress_subgoal_v1 import authority, service
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'set.json'
            digest = P.write_rehearsal_set(path)
            env = {P.REHEARSAL_ENV: str(path), 'PSV1_REHEARSAL': '1', 'CUDA_VISIBLE_DEVICES': ''}
            with mock.patch.dict(os.environ, env):
                allowed, served, ceiling = service.frozen_requests()
        contexts = {c['context_id']: c for c in STAND_IN['contexts']}
        self.assertEqual(set(allowed), {request_hash(P.build_request(contexts[p['context_id']], p))
                                        for p in STAND_IN['probes']})
        self.assertEqual((served, ceiling), (digest, 5852))
        self.assertEqual(authority.LIMITS['maximum_questionnaire_calls'], ceiling)
        self.assertEqual((authority.LIMITS['automatic_retries'], authority.LIMITS['maximum_attempts']), (0, 1))

    def test_requests_have_the_reviewed_stack_shape(self):
        from research.transition_evidence_v1 import questionnaire as WQ
        mine = next(P.scheduled_requests(STAND_IN))['request']
        ws3 = WQ.build_request({}, {'family': 'progress_status', 'question': 'q'})
        self.assertEqual(set(mine), set(ws3))
        for key in ('model', 'temperature', 'seed', 'max_tokens', 'chat_template_kwargs'):
            self.assertEqual(mine[key], ws3[key], key)

    def test_rehearsal_probe_set_never_reaches_live(self):
        with mock.patch.dict(os.environ, {P.REHEARSAL_ENV: '/tmp/x.json', 'PSV1_REHEARSAL': '', 'CUDA_VISIBLE_DEVICES': ''}):
            with self.assertRaises(PermissionError):
                P.load_frozen()
        with mock.patch.dict(os.environ, {P.REHEARSAL_ENV: '/tmp/x.json', 'PSV1_REHEARSAL': '1',
                                          'CUDA_VISIBLE_DEVICES': '0'}):
            with self.assertRaises(PermissionError):
                P.load_frozen()
        self.assertFalse(P.FROZEN_PATH.exists())  # nothing is frozen

    def test_live_mode_is_refused_without_review_approvals_and_reservation(self):
        from research.progress_subgoal_v1 import authority
        with self.assertRaises(PermissionError):
            authority.require()
        with mock.patch.dict(os.environ, {'PSV1_REHEARSAL': '', 'CUDA_VISIBLE_DEVICES': ''}):
            with self.assertRaises(PermissionError):
                authority.rehearsal_gate()


class TokenAuditEnumeration(unittest.TestCase):
    def test_every_scheduled_request_once_in_call_order(self):
        rows = list(P.scheduled_requests(STAND_IN))
        self.assertEqual(len(rows), sum(len(b['probe_ids']) for b in STAND_IN['schedule']))
        self.assertEqual([r['index'] for r in rows], list(range(len(rows))))
        from research.progress_subgoal_v1.schedule import call_order
        self.assertEqual([(r['phase'], r['pass_id'], r['probe_id']) for r in rows], call_order(STAND_IN))
        for r in rows[::97]:
            self.assertEqual([m['role'] for m in r['messages']], ['system', 'user'])
            self.assertEqual((r['max_tokens'], r['chat_template_kwargs']), (32, {'enable_thinking': False}))
            self.assertEqual(r['messages'][0]['content'], Q.SYSTEM_PROMPTS[r['condition']])
        # a question asked in both passes has one request
        by_probe = {}
        for r in rows:
            by_probe.setdefault(r['probe_id'], set()).add(r['request_sha256'])
        self.assertTrue(all(len(v) == 1 for v in by_probe.values()))


class TokenAuditFunction(unittest.TestCase):
    def test_audit_runs_with_a_tokenizer_interface(self):
        from research.action_effect_history_v1.rehearsal import FixtureTokenizer
        from research.progress_subgoal_v1 import token_audit

        class Tok(FixtureTokenizer):
            def encode(self, text, add_special_tokens=False):
                return list(text)
        report = token_audit.audit(Tok(), STAND_IN)
        s = report['summary']
        self.assertEqual(s['scheduled_calls'], 5852)
        self.assertEqual(s['distinct_requests'], len(STAND_IN['probes']))
        self.assertEqual(set(s['by_phase']), {'withheld_pass_1', 'withheld_pass_2', 'development_pass_1'})
        self.assertEqual(len(report['requests']), 5852)


@unittest.skipUnless(os.environ.get('PSV1_CONNECTED') == '1', 'connected rehearsal: set PSV1_CONNECTED=1 (~4 min)')
class ConnectedRehearsal(unittest.TestCase):
    """launcher -> supervisor -> worker -> host -> fake server over HTTP -> runner -> independent evaluator."""

    def test_normal_run_scores_only_retained_responses(self):
        from research.progress_subgoal_v1.evaluate_run import evaluate_output
        from research.progress_subgoal_v1.evidence import forge, load_unverified_calls
        from research.progress_subgoal_v1.rehearse_run import rehearse
        base = Path.home() / 'psv1-rehearsal-tests'
        base.mkdir(exist_ok=True)
        workdir = Path(tempfile.mkdtemp(dir=base))
        receipt, output = rehearse('none', 900, workdir)
        value = evaluate_output(output, mode='rehearsal', rehearsal_seconds=900)
        self.assertTrue(value['technically_complete'], value['lifecycle_errors'])
        self.assertEqual(value['run']['counts'], {'answered': 5852})
        self.assertEqual(value['gate_status'], 'complete')
        self.assertEqual(set(value['gate']), set(Q.PRIMARY_CONDITIONS))
        arm = Q.PRIMARY_CONDITIONS[0]
        family = value['analysis']['families'][arm]['progress_status']
        # the fake server's scripted invalid answers fail validity, as they should
        self.assertEqual(value['analysis']['validity'][arm]['all_responses']['status'], 'fails')
        # changing one retained answer changes the independent score: nothing else is scored
        frozen, _ = P.load_frozen()
        probes = {p['probe_id']: p for p in frozen['probes']}
        calls = load_unverified_calls(output / 'worker/run')
        flip = next(c for c in calls if c['phase'] == 'withheld_pass_1' and probes[c['probe_id']]['condition'] == arm
                    and probes[c['probe_id']]['family'] == 'progress_status' and c['response'].startswith('{')
                    and int(hashlib.sha256(c['probe_id'].encode()).hexdigest(), 16) % 100 >= 12
                    and json.loads(c['response']) == {'answer': probes[c['probe_id']]['key']})
        wrong = 'unknown' if probes[flip['probe_id']]['key'] == 'confirmed' else 'confirmed'
        copy = workdir / 'copy'
        shutil.copytree(output, copy)
        forge(copy / 'worker/run', f"calls/{flip['index']:05d}.json",
              lambda v: v.update(response=json.dumps({'answer': wrong})))
        changed = evaluate_output(copy, mode='rehearsal', rehearsal_seconds=900)
        self.assertEqual(changed['analysis']['families'][arm]['progress_status']['correct'], family['correct'] - 1)
        # an interrupted write: recovered, never technically complete, never eligible
        interrupted = workdir / 'interrupted'
        shutil.copytree(output, interrupted)
        (interrupted / 'worker/run/manifest.json.tmp').write_bytes(b'{"partial')
        result = evaluate_output(interrupted, mode='rehearsal', rehearsal_seconds=900)
        self.assertTrue(result['run_evidence']['recovered'])
        self.assertEqual((result['technically_complete'], result['gate_status']), (False, 'incomplete'))
        self.assertEqual(set(result['gate'].values()), {'incomplete'})


if __name__ == '__main__':
    unittest.main()
