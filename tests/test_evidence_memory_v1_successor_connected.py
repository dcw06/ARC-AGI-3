"""Connected CPU rehearsals of both successor session packages through the verified lifecycle, and the registered
pooled analysis end to end (POSIX only).

Each rehearsal installs fixture wheels into a real virtual environment from a fixture publisher mount, verifies a
fixture model tree, starts the scripted stub (research/evidence_memory_v1/successor/stub.py) as an owned process
group, runs the startup and inference probes, the full Stage 1 study phase over real HTTP through the counted
client, the cancellation probes, cleanup and evidence finalization. The independent successor evaluator then checks
the retained output. None of this is GPU, model or throughput evidence.
"""
import copy
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from research.evidence_memory_v1.successor import plan as PL

ROOT = Path(__file__).resolve().parents[1]
HAS_PIP = os.name == 'posix' and subprocess.run([sys.executable, '-m', 'pip', '--version'],
                                                capture_output=True).returncode == 0
# Rehearsals run on the development stand-ins only (never on a withheld set in a private checkout).
STAND_INS = all(PL.load_frozen(ROOT, spec['package'])[0]['case_source'] == 'development_stand_in'
                for spec in PL.SESSIONS.values())
OUTCOME_WORDS = ('accuracy', 'contrast', 'primary_endpoint', 'correct_truth', 'correct_package', '"correct"',
                 'unsupported', 'abstain', 'memory_preserves', 'stability', 'conclusions')


def rehearsal(label):
    return importlib.import_module(PL.SESSIONS[label]['module'] + '.rehearsal')


def session_order_reasons(evaluation):
    """Session B's launch-tooling check (successor/session_order.py) applied to a real evaluator record, retained at
    its fixed path in a disposable checkout with session A's protocol."""
    from research.evidence_memory_v1.successor import session_order
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        protocol = PL.SESSIONS['A']['package'] + '/protocol.json'
        for name, data in ((session_order.RECORD, (json.dumps(evaluation, indent=1) + '\n').encode()),
                           (protocol, (ROOT / protocol).read_bytes())):
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_bytes(data)
        return session_order.record_reasons(root)


def run(label, folder, fault, latency=0.0):
    """One connected rehearsal and its independent evaluation (harness-declared rehearsal limits)."""
    from research.evidence_memory_v1.successor.evaluate import evaluate_output
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    result = rehearsal(label).scenario(ROOT, Path(folder) / f'{label}-{fault}', fault, latency=latency)
    output = Path(folder) / f'{label}-{fault}' / 'evidence'
    evaluation = evaluate_output(output, label, mode='rehearsal', rehearsal_limits=rehearsal(label).rehearsal_limits(ROOT))
    return result, evaluation, output


@unittest.skipUnless(HAS_PIP and STAND_INS, 'connected rehearsals need POSIX, an interpreter with pip (fixture venv '
                     'install) and the development stand-ins')
class SessionsAndPooledAnalysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.mkdtemp(prefix='em1-successor-connected-')
        cls.runs = {label: run(label, cls.folder, 'package_reader') for label in sorted(PL.SESSIONS)}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.folder, ignore_errors=True)

    def sessions(self, labels=('A', 'B'), **kwargs):
        from research.evidence_memory_v1.successor import final
        return [final.evaluate_session(label, self.runs[label][2], mode='rehearsal',
                                       rehearsal_limits=rehearsal(label).rehearsal_limits(ROOT), **kwargs)
                for label in labels]

    def test_1_both_sessions_complete_the_verified_lifecycle_and_qualify_technically(self):
        for label, (result, evaluation, output) in self.runs.items():
            scheduled = PL.load_frozen(ROOT, PL.SESSIONS[label]['package'])[0]
            n = sum(len(b['probe_ids']) for b in scheduled['schedule'])
            self.assertTrue(result['passed'], result.get('error'))
            self.assertTrue(result['cleanup_verified'] and result['lifecycle_deadline']['met'])
            self.assertEqual(result['evidence_class'], 'scripted_cpu_rehearsal')
            self.assertFalse(result['gpu_compatibility_evidence'])
            self.assertTrue(result['stages']['gpu'].startswith('not_exercised'))
            probes = result['ledger']['by_kind']
            self.assertIn(probes['cancellation_probe'], (3, 4))  # C2 reads /metrics once or twice
            self.assertEqual(result['ledger']['issued'], 7 + probes['cancellation_probe'] + 1 + 2 * n)
            self.assertEqual((probes['study_completion'], probes['study_metrics']), (n, n + 1))
            self.assertEqual(result['ledger']['refusals'], [])
            self.assertEqual(result['study']['counts'], {'answered': n})
            self.assertTrue(evaluation['technically_complete'], evaluation['lifecycle_errors'] + evaluation['call_errors'])
            self.assertEqual(evaluation['analysis']['technical_status'], 'session_technically_valid')
            self.assertTrue(evaluation['analysis']['invalid_by_pass']['pass_2']['rule_met'])
        # Session B's launch tooling reads this evaluator's real output: a complete, valid rehearsal of A is refused
        # only because it is a rehearsal of the development stand-in, never for its shape.
        reasons = session_order_reasons(self.runs['A'][1])
        self.assertEqual(len(reasons), 2, reasons)
        self.assertIn('not live', reasons[0])
        self.assertIn('not withheld', reasons[1])

    def test_2_a_session_reports_only_its_technical_status(self):
        for label, (result, evaluation, output) in self.runs.items():
            for name, value in (('result.json', json.loads((output / 'result.json').read_bytes())),
                                ('summary.json', json.loads((output / 'study/summary.json').read_bytes())),
                                ('evaluation', evaluation)):
                text = json.dumps(value)
                self.assertFalse([w for w in OUTCOME_WORDS if w in text], (label, name))

    def test_3_the_pooled_analysis_reproduces_the_availability_ceilings_end_to_end(self):
        from research.evidence_memory_v1.run import final as RF
        from research.evidence_memory_v1.successor import final
        sessions = self.sessions()
        pooled = final.pooled_analysis(sessions, require_withheld=False, resamples=200)
        self.assertEqual(pooled['status'], 'analysed', pooled.get('reasons'))
        self.assertEqual(pooled['case_source'], 'development_stand_in')
        primary = {arm: round(v['estimate'], 2) for arm, v in pooled['analysis']['primary_endpoint'].items()}
        self.assertEqual(primary, {'recent_raw': 0.0, 'state_keyed_raw': 0.9, 'memory': 0.9})
        self.assertEqual(pooled['analysis']['reference_full_history']['estimate'], 1.0)
        self.assertEqual(pooled['verdict'], 'memory_preserves_access_not_shown_over_retrieval')
        self.assertEqual(pooled['stability']['identical'], pooled['stability']['repeated_questions'])
        direct = RF.pooled_analysis(sessions, final.registered_binding(), require_withheld=False, resamples=200)
        self.assertEqual(direct, pooled)

    def test_4_the_pooled_analysis_refuses_anything_less_than_two_qualified_live_sessions(self):
        from research.evidence_memory_v1.successor import final
        sessions = self.sessions()
        cases = {'one session': [sessions[0]], 'duplicated': [sessions[0], copy.deepcopy(sessions[0])],
                 'swapped labels': [dict(sessions[0], label='B'), dict(sessions[1], label='A')]}
        for name, given in cases.items():
            result = final.pooled_analysis(given, require_withheld=False, resamples=50)
            self.assertEqual(result['status'], 'refused', name)
            self.assertNotIn('analysis', result)
        strict = final.pooled_analysis(sessions, resamples=50)  # the default: withheld and live only
        self.assertEqual(strict['status'], 'refused')
        self.assertTrue(any('not withheld' in r for r in strict['reasons']))
        self.assertTrue(any("not live" in r for r in strict['reasons']))
        from research.evidence_memory_v1.successor.evaluate import evaluate_output
        as_live = evaluate_output(self.runs['A'][2], 'A', mode='live')
        self.assertFalse(as_live['technically_complete'])
        self.assertTrue(any('evidence class' in e for e in as_live['lifecycle_errors']))

    def test_6_a_missing_mandatory_probe_is_never_technically_complete(self):
        # The review's reproductions: C3, then separately I4, removed from the ledger, the request results and the
        # stage details, with the evidence manifest updated to match. Neither may evaluate as technically complete.
        import hashlib
        from research.evidence_memory_v1.successor.evaluate import evaluate_output
        stage_of = {'C3': 'cancellation_C3_responsive', 'I4': 'inference_I4'}
        for request_id in ('C3', 'I4'):
            altered = Path(self.folder) / f'A-without-{request_id}'
            shutil.copytree(self.runs['A'][2], altered)
            result = json.loads((altered / 'result.json').read_bytes())
            entries = [e for e in result['ledger']['entries'] if e['id'] != request_id]
            for n, entry in enumerate(entries, 1):
                entry['sequence'] = n
            result['ledger'].update(entries=entries, issued=len(entries))
            result['requests'].pop(request_id)
            result['stages'].pop(stage_of[request_id])
            (altered / 'result.json').write_bytes((json.dumps(result, indent=1, sort_keys=True) + '\n').encode())
            manifest = json.loads((altered / 'evidence-manifest.json').read_bytes())
            manifest['files']['result.json'] = hashlib.sha256((altered / 'result.json').read_bytes()).hexdigest()
            (altered / 'evidence-manifest.json').write_bytes((json.dumps(manifest, indent=1, sort_keys=True) + '\n').encode())
            evaluation = evaluate_output(altered, 'A', mode='rehearsal', rehearsal_limits=rehearsal('A').rehearsal_limits(ROOT))
            self.assertFalse(evaluation['technically_complete'], request_id)
            self.assertFalse(evaluation['lifecycle_passed'], request_id)
            self.assertIn('mandatory runtime probe missing from the ledger: ' + request_id, evaluation['lifecycle_errors'])
            self.assertFalse([e for e in evaluation['lifecycle_errors'] if 'evidence manifest' in e], request_id)

    def test_5_an_altered_session_is_refused_and_its_earlier_evaluation_cannot_be_reused(self):
        from research.evidence_memory_v1.successor import final
        earlier = self.sessions(('B',))[0]
        altered = Path(self.folder) / 'B-altered'
        shutil.copytree(self.runs['B'][2], altered)
        calls = altered / 'study/run/calls.jsonl'
        lines = calls.read_bytes().splitlines(keepends=True)
        row = json.loads(lines[3])
        row['response'] += ' '  # one retained response changes by one byte (still valid JSON)
        lines[3] = (json.dumps(row, sort_keys=True, separators=(',', ':')) + '\n').encode()
        calls.write_bytes(b''.join(lines))
        reevaluated = final.evaluate_session('B', altered, mode='rehearsal',
                                             rehearsal_limits=rehearsal('B').rehearsal_limits(ROOT))
        self.assertFalse(reevaluated['technical']['technically_complete'])
        a = self.sessions(('A',))[0]
        self.assertEqual(final.pooled_analysis([a, reevaluated], require_withheld=False, resamples=50)['status'], 'refused')
        frozen_bytes = (ROOT / PL.SESSIONS['B']['package'] / 'probes.json').read_bytes()
        stale = dict(earlier, inputs=final.inputs_digest(altered, frozen_bytes))  # the old success, new inputs
        result = final.pooled_analysis([a, stale], require_withheld=False, resamples=50)
        self.assertEqual(result['status'], 'refused')
        self.assertTrue(any('not bound to the inputs' in r for r in result['reasons']))


@unittest.skipUnless(HAS_PIP and STAND_INS, 'connected rehearsals need POSIX, an interpreter with pip (fixture venv '
                     'install) and the development stand-ins')
class Faults(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix='em1-successor-fault-')

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def stopped(self, fault, calls_recorded, stop_reason='transport_failure'):
        result, evaluation, output = run('A', self.folder, fault)
        self.assertFalse(result['passed'])
        self.assertEqual(result['failed_stage'], 'study')
        self.assertTrue(result['cleanup_verified'], result['cleanup'])
        self.assertFalse(evaluation['technically_complete'])
        if calls_recorded is not None:
            self.assertEqual((evaluation['run']['calls_recorded'], evaluation['run']['stop_reason']),
                             (calls_recorded, stop_reason))
        return result, evaluation, output

    def test_scripted_invalid_and_truncated_answers_are_measured_not_repaired(self):
        result, evaluation, _ = run('A', self.folder, 'none')
        self.assertTrue(result['passed'], result.get('error'))
        self.assertEqual(evaluation['run']['status'], 'complete')
        self.assertEqual(evaluation['analysis']['technical_status'], 'session_technically_invalid_outputs')
        self.assertFalse(evaluation['analysis']['invalid_by_pass']['pass_1']['rule_met'])

    def test_invalid_answers_only_in_the_repeat_pass_still_invalidate_the_session(self):
        result, evaluation, _ = run('A', self.folder, 'invalid_repeat')
        self.assertTrue(result['passed'], result.get('error'))
        invalid = evaluation['analysis']['invalid_by_pass']
        self.assertTrue(invalid['pass_1']['rule_met'])
        self.assertFalse(invalid['pass_2']['rule_met'])
        self.assertEqual(evaluation['analysis']['technical_status'], 'session_technically_invalid_outputs')
        self.assertIn('session A is not technically valid in every pass', session_order_reasons(evaluation))

    def test_a_timeout_is_cancelled_and_verified_idle_and_leaves_the_session_incomplete(self):
        result, evaluation, output = run('A', self.folder, 'hang_once')
        self.assertTrue(result['passed'], result.get('error'))
        self.assertEqual(evaluation['run']['counts'].get('timed_out'), 1)
        self.assertEqual(evaluation['call_errors'], [])
        cancellations = json.loads((output / 'study/cancellations.json').read_bytes())
        self.assertTrue(cancellations[0]['idle'])
        self.assertEqual(cancellations[0]['idle_verification']['aborted_total'], 1)
        self.assertFalse(evaluation['technically_complete'])
        self.assertEqual(evaluation['analysis']['technical_status'], 'incomplete')
        self.assertGreaterEqual(result['ledger']['by_kind'].get('study_idle_verification', 0), 1)
        self.assertIn('session A is not technically complete', session_order_reasons(evaluation))

    def test_a_server_that_ignores_cancellation_stops_the_study_and_is_still_cleaned_up(self):
        result, evaluation, output = self.stopped('no_abort', 7)
        cancellations = json.loads((output / 'study/cancellations.json').read_bytes())
        self.assertFalse(cancellations[0]['idle'])
        self.assertTrue(result['cleanup']['server']['groups_absent'])

    def test_prefix_caching_in_the_counters_stops_before_any_study_call(self):
        result, evaluation, _ = self.stopped('prefix_cache_enabled', None)
        self.assertNotIn('study_completion', result['ledger']['by_kind'])
        self.assertIn('prefix caching not verified disabled at after_canary', result['error'])

    def test_prefix_caching_appearing_mid_run_stops_at_that_call(self):
        self.stopped('prefix_cache_late', 7)

    def test_a_token_parity_failure_stops_the_study(self):
        result, evaluation, output = self.stopped('token_mismatch', 7)
        last = json.loads((output / 'study/run/calls.jsonl').read_bytes().splitlines()[-1])
        self.assertIn('TokenParityViolation', last['error'])

    def test_a_server_error_stops_the_study(self):
        self.stopped('http_error', 7)

    def test_the_admission_cutoff_truncates_the_session_and_cleanup_keeps_its_reserve(self):
        result, evaluation, _ = run('A', self.folder, 'slow', latency=0.1)
        self.assertTrue(result['passed'], result.get('error'))  # an incomplete session is a reported result
        self.assertEqual(evaluation['run']['stop_reason'], 'admission_cutoff')
        self.assertEqual(evaluation['call_errors'], [])
        recorded = evaluation['run']['calls_recorded']
        frozen = PL.load_frozen(ROOT, PL.SESSIONS['A']['package'])[0]
        self.assertLess(recorded, len(frozen['schedule'][0]['probe_ids']))
        limits = rehearsal('A').rehearsal_limits(ROOT)
        self.assertLess(result['phases'][-1]['began_at'], limits['internal_seconds'])
        self.assertEqual(evaluation['analysis']['technical_status'], 'incomplete')


if __name__ == '__main__':
    unittest.main()
