"""Connected-path CPU rehearsals: launcher -> supervisor -> worker -> host -> fake server over HTTP -> runner -> evaluator.

Covers the review of r3: caching verified off from the running server; timeouts cancel server-side
work (and a server that ignores cancellation stops the run); interruptions in both gate passes keep
evidence and report an incomplete gate with the cleanup reserve untouched; cleanup, logging and
storage failures stay bounded by the shared deadline; the evaluator scores only retained responses.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

from research.evidence_comprehension_v1.evidence import MANIFEST, encode
from scripts.evaluate_evidence_comprehension_v1 import evaluate_output
from scripts.rehearse_evidence_comprehension_v1 import rehearse

BASE = Path.home() / 'ecv-rehearsal-tests'
REHEARSAL_SECONDS = 480
CUTOFF_REHEARSAL_SECONDS = 420  # admission cutoff at 120 s
RESERVE = 300


def run_fault(fault, seconds=REHEARSAL_SECONDS):
    BASE.mkdir(exist_ok=True)
    receipt, output = rehearse(fault, seconds, tempfile.mkdtemp(dir=BASE))
    outer = json.loads((output / 'control/outer.json').read_bytes())
    return receipt, output, outer, evaluate_output(output, mode='rehearsal', rehearsal_seconds=seconds)


def calls(output):
    return [json.loads(p.read_bytes()) for p in sorted((output / 'worker/run/calls').glob('*.json'))]


def rewrite(output, name, mutate):
    """Change one retained run file and re-hash it into the manifest (a consistent forgery)."""
    folder = output / 'worker/run'
    path = folder / name
    value = json.loads(path.read_bytes())
    mutate(value)
    raw = encode(value)
    path.write_bytes(raw)
    manifest = json.loads((folder / MANIFEST).read_bytes())
    manifest['files'][name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    (folder / MANIFEST).write_bytes(encode(manifest))


class Rehearsals(unittest.TestCase):
    def assert_cleaned_and_bounded(self, receipt, outer, output, seconds):
        self.assertTrue(outer['process_groups_exited'])
        self.assertTrue(outer['independent_gpu_cleanup_verified'])
        self.assertTrue(outer['scratch_removed'])
        first = json.loads((output / 'control/first-cell-supervisor-cleanup.json').read_bytes())
        self.assertEqual(first['errors'], [])
        self.assertTrue(first['groups'] and all(v is True for v in first['groups'].values()))
        self.assertLess(receipt['elapsed_seconds'], seconds - RESERVE)  # never reaches the cleanup reserve

    def test_normal_run_and_scores_come_only_from_retained_responses(self):
        receipt, output, outer, value = run_fault('none')
        self.assert_cleaned_and_bounded(receipt, outer, output, REHEARSAL_SECONDS)
        self.assertTrue(value['technically_complete'], value['lifecycle_errors'])
        self.assertEqual(value['gate_status'], 'complete')
        self.assertEqual(value['run']['counts'], {'answered': 1308})
        config = json.loads((output / 'worker/server-config.json').read_bytes())
        self.assertTrue(config['after_canary']['prefix_caching_disabled_verified'])
        baseline = value['analysis']['both_correct']['evidence_only/recall_action']['correct']
        retained = calls(output)
        work = Path(tempfile.mkdtemp(dir=BASE))
        try:
            # 1. Changing a retained response changes the evaluator's score: nothing else is scored.
            copy = work / 'responses'
            shutil.copytree(output, copy)
            probes = {p['probe_id']: p for p in json.loads(
                Path('research/evidence_comprehension_v1/probes.json').read_bytes())['probes']}
            flip = next(c for c in retained if c['phase'] == 'gate_pass_1'
                        and probes[c['probe_id']]['family'] == 'recall_action' and c['response'].startswith('{')
                        and json.loads(c['response']) == {'answer': probes[c['probe_id']]['key']})
            wrong = 'not_shown' if probes[flip['probe_id']]['key'] != 'not_shown' else {'action_id': 1, 'action_data': {}}
            rewrite(copy, f'calls/{flip["index"]:05d}.json', lambda v: v.update(response=json.dumps({'answer': wrong})))
            changed = evaluate_output(copy, mode='rehearsal', rehearsal_seconds=REHEARSAL_SECONDS)
            self.assertEqual(changed['analysis']['both_correct']['evidence_only/recall_action']['correct'], baseline - 1)
            # 2. A forged request hash, an out-of-order call and broken token parity are rejected.
            for name, mutate, reason in (
                    ('hash', lambda v: v.update(request_sha256='0' * 64), 'request hash'),
                    ('order', lambda v: v.update(probe_id=retained[1]['probe_id']), 'not the scheduled call'),
                    ('parity', lambda v: v.update(server_prompt_tokens=v['server_prompt_tokens'] + 1), 'tokenizer parity')):
                forged = work / name
                shutil.copytree(output, forged)
                rewrite(forged, 'calls/00000.json', mutate)
                result = evaluate_output(forged, mode='rehearsal', rehearsal_seconds=REHEARSAL_SECONDS)
                self.assertFalse(result['technically_complete'], name)
                self.assertTrue(any(reason in e for e in result['call_errors']), (name, result['call_errors']))
                self.assertIsNone(result['analysis'])  # nothing is scored from evidence that fails binding
            # 2b. Review of r1: impossible metadata and timing are rejected, even when re-hashed into the manifest.
            answered = next(c for c in retained if c['finish_reason'] == 'stop')
            name = f'calls/{answered["index"]:05d}.json'

            def drop(*keys):
                return lambda v: [v.pop(k) for k in keys]
            for label, mutate, reason in (
                    ('negative prompt', lambda v: v.update(server_prompt_tokens=-1, tokenizer_prompt_tokens=-1), 'prompt tokens'),
                    ('negative completion', lambda v: v.update(server_completion_tokens=-5), 'completion tokens'),
                    ('missing completion and finish', drop('server_completion_tokens', 'finish_reason'), 'completion tokens'),
                    ('length below the cap', lambda v: v.update(finish_reason='length'), 'length finish'),
                    ('unknown finish', lambda v: v.update(finish_reason='abort'), 'finish reason'),
                    ('after the deadline', lambda v: v.update(started_at=3290.0, returned_at=3350.0), 'admission'),
                    ('reversed timestamps', lambda v: v.update(returned_at=v['started_at'] - 1), 'timestamps'),
                    ('non-finite timestamp', lambda v: v.update(returned_at=None), 'timestamps'),
                    ('forged cache counters', lambda v: v['cache_check'].update(prefix_cache_queries_total=999,
                                                                               prefix_cache_hits_total=999,
                                                                               prefix_caching_disabled_verified=True),
                     'cache counters'),
                    ('missing cache check', drop('cache_check'), 'cache counters'),
                    ('stale prompt counter', lambda v: v['cache_check'].update(prompt_tokens_total=1), 'did not advance'),
                    ('late host answer', lambda v: v['host_timing'].update(answered_after_seconds=999.0), 'host timing')):
                with self.subTest(mutation=label):
                    forged = work / label.replace(' ', '-')
                    shutil.copytree(output, forged)
                    rewrite(forged, name, mutate)
                    result = evaluate_output(forged, mode='rehearsal', rehearsal_seconds=REHEARSAL_SECONDS)
                    self.assertTrue(result['run_evidence']['verified'], label)  # consistent hashes...
                    self.assertTrue(any(reason in e for e in result['call_errors']), (label, result['call_errors']))
                    self.assertFalse(result['technically_complete'], label)  # ...but rejected
                    self.assertIsNone(result['analysis'])
            # 2c. Review of r1: a forged server record claiming verification with 999 queries is rejected.
            forged = work / 'server-config'
            shutil.copytree(output, forged)
            config = json.loads((forged / 'worker/server-config.json').read_bytes())
            config['after_canary'].update(prefix_cache_queries_total=999, prefix_cache_hits_total=999,
                                          prefix_caching_disabled_verified=True)
            (forged / 'worker/server-config.json').write_text(json.dumps(config))
            result = evaluate_output(forged, mode='rehearsal', rehearsal_seconds=REHEARSAL_SECONDS)
            self.assertTrue(any('server configuration' in e for e in result['lifecycle_errors']))
            self.assertFalse(result['technically_complete'])
            # 2d. Truncated answers are accepted as evidence but always scored invalid, never parsed.
            truncated_calls = [c for c in retained if c['finish_reason'] == 'length']
            self.assertTrue(truncated_calls)
            from scripts.evaluate_evidence_comprehension_v1 import score_call
            for c in truncated_calls:
                self.assertEqual(c['server_completion_tokens'], __import__(
                    'research.evidence_comprehension_v1.probes', fromlist=['MAX_TOKENS']).MAX_TOKENS[probes[c['probe_id']]['family']])
                row = score_call(probes[c['probe_id']], c)
                self.assertEqual((row['valid'], row['correct']), (False, False))
            # 3. A run whose second pass lost its retained calls is incomplete, never a pass.
            truncated = work / 'truncated'
            shutil.copytree(output, truncated)
            folder = truncated / 'worker/run'
            manifest = json.loads((folder / MANIFEST).read_bytes())
            for c in retained[454:]:
                name = f'calls/{c["index"]:05d}.json'
                (folder / name).unlink()
                del manifest['files'][name]
            (folder / MANIFEST).write_bytes(encode(manifest))
            rewrite(truncated, 'run.json', lambda v: v.update(calls_recorded=454))
            result = evaluate_output(truncated, mode='rehearsal', rehearsal_seconds=REHEARSAL_SECONDS)
            self.assertEqual(result['gate_status'], 'incomplete')
            self.assertEqual(set(result['gate'].values()), {'incomplete'})
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def test_instrumentation_leaves_requests_and_answers_unchanged(self):
        receipt, output, outer, value = run_fault('none')
        os.environ.update(ECV_REHEARSAL='1', CUDA_VISIBLE_DEVICES='')
        from research.action_effect_history_v1.rehearsal import FixtureTokenizer
        from research.evidence_comprehension_v1 import runner
        from research.evidence_comprehension_v1.fake_server import FakeVLLM
        from research.evidence_comprehension_v1.service import QuestionnaireService
        from research.evidence_comprehension_v1.transport import CancellableTransport, read_metrics, verify_idle
        server = FakeVLLM().start()
        try:
            service = QuestionnaireService(FixtureTokenizer(), CancellableTransport(server.base_url, 2),
                                           metrics=lambda deadline: read_metrics(server.base_url, deadline),
                                           verify_idle=lambda deadline: verify_idle(server.base_url, deadline),
                                           timeout_seconds=2.0, verify_seconds=3.0)
            service.launch = {'rehearsal_fake_server': True}
            service.startup_canary()

            class Direct:
                def complete(self, request, deadline=None):
                    result, audit = service.complete(request)
                    return {'content': result.content, 'tokenizer_prompt_tokens': audit['tokenizer_prompt_tokens'],
                            'server_prompt_tokens': audit['server_prompt_tokens'],
                            'server_completion_tokens': audit['server_completion_tokens'],
                            'finish_reason': audit['finish_reason']}
            with tempfile.TemporaryDirectory(dir=BASE) as tmp:
                runner.run(Path(tmp) / 'run', Direct(), started=time.monotonic(), kind='direct', cutoff_seconds=3000,
                           bound_seconds=10)
                direct = [json.loads(p.read_bytes()) for p in sorted((Path(tmp) / 'run/calls').glob('*.json'))]
        finally:
            server.close()
        shape = lambda rows: [(c['probe_id'], c['request_sha256'], c['status'], c.get('response')) for c in rows]  # noqa: E731
        self.assertEqual(shape(calls(output)), shape(direct))

    def test_deadline_interruption_in_each_gate_pass(self):
        for fault, phase in (('slow_gate_pass_1', 'gate_pass_1'), ('slow_gate_pass_2', 'gate_pass_2')):
            with self.subTest(fault=fault):
                receipt, output, outer, value = run_fault(fault, CUTOFF_REHEARSAL_SECONDS)
                self.assert_cleaned_and_bounded(receipt, outer, output, CUTOFF_REHEARSAL_SECONDS)
                self.assertEqual(receipt['study_status'], 'study_ended_pending_independent_evaluation')
                self.assertTrue(value['lifecycle_passed'], value['lifecycle_errors'])
                self.assertTrue(value['run_evidence']['verified'])
                self.assertEqual((value['run']['stop_reason'], value['run']['phase_reached']), ('admission_cutoff', phase))
                self.assertEqual(value['gate_status'], 'incomplete')
                self.assertEqual(set(value['gate'].values()), {'incomplete'})
                self.assertFalse(value['technically_complete'])
                cutoff = CUTOFF_REHEARSAL_SECONDS - RESERVE
                self.assertLessEqual(max(c['returned_at'] for c in calls(output)), cutoff)  # reserve untouched

    def test_timeout_cancels_server_side_work(self):
        receipt, output, outer, value = run_fault('hang_once')
        self.assert_cleaned_and_bounded(receipt, outer, output, REHEARSAL_SECONDS)
        self.assertEqual(value['run']['counts'].get('timed_out'), 1)
        cancellations = json.loads((output / 'worker/cancellations.json').read_bytes())
        self.assertEqual(len(cancellations), 1)
        self.assertTrue(cancellations[0]['idle'])
        self.assertEqual(cancellations[0]['idle_verification']['aborted_total'], 1)
        self.assertEqual(value['call_errors'], [])
        self.assertEqual(value['gate_status'], 'incomplete')  # the cancelled question has no answer
        timed = next(c for c in calls(output) if c['status'] == 'timed_out')
        family = next(p['family'] for p in json.loads(Path('research/evidence_comprehension_v1/probes.json').read_bytes())
                      ['probes'] if p['probe_id'] == timed['probe_id'])
        self.assertEqual(value['gate'][family], 'incomplete')
        # Without the host's verified cancellation record, the timed-out call is rejected.
        work = Path(tempfile.mkdtemp(dir=BASE))
        try:
            shutil.copytree(output, work / 'x')
            (work / 'x/worker/cancellations.json').write_text('[]')
            result = evaluate_output(work / 'x', mode='rehearsal', rehearsal_seconds=REHEARSAL_SECONDS)
            self.assertTrue(any('without a retained server-side cancellation' in e for e in result['call_errors']))
            # Review of r1: the idle verdict is recomputed from its measurements, not read from a flag.
            for label, mutate in (('still running', lambda r: r['idle_verification'].update(running=1.0)),
                                  ('waited past the window', lambda r: r['idle_verification'].update(waited_seconds=99.0)),
                                  ('ended after the deadline', lambda r: r['timing'].update(ended_after_seconds=99.0))):
                with self.subTest(cancellation=label):
                    target = work / label.replace(' ', '-')
                    shutil.copytree(output, target)
                    record = json.loads((target / 'worker/cancellations.json').read_bytes())
                    mutate(record[0])
                    record[0]['idle'] = True
                    (target / 'worker/cancellations.json').write_text(json.dumps(record))
                    result = evaluate_output(target, mode='rehearsal', rehearsal_seconds=REHEARSAL_SECONDS)
                    self.assertTrue(result['call_errors'], label)
                    self.assertFalse(result['technically_complete'], label)
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def test_slow_abort_within_the_window_is_verified(self):
        receipt, output, outer, value = run_fault('slow_abort')
        self.assert_cleaned_and_bounded(receipt, outer, output, REHEARSAL_SECONDS)
        record = json.loads((output / 'worker/cancellations.json').read_bytes())[0]
        self.assertTrue(record['idle'])
        self.assertGreaterEqual(record['idle_verification']['waited_seconds'], 0.9)
        self.assertEqual(value['call_errors'], [])
        self.assertEqual(value['run']['counts'].get('timed_out'), 1)

    def test_late_abort_trickling_metrics_and_late_replies_stop_within_the_bound(self):
        from research.evidence_comprehension_v1 import schedule
        bound = 2.0 + schedule.TEARDOWN_SECONDS + 3.0 + schedule.BRIDGE_MARGIN_SECONDS  # rehearsal timing
        for fault in ('late_abort', 'trickle_metrics', 'late_reply'):
            with self.subTest(fault=fault):
                receipt, output, outer, value = run_fault(fault)
                self.assert_cleaned_and_bounded(receipt, outer, output, REHEARSAL_SECONDS)
                self.assertEqual(receipt['study_status'], 'failed')
                self.assertEqual(value['run']['stop_reason'], 'transport_failure')
                self.assertEqual(value['gate_status'], 'incomplete')
                self.assertEqual(value['call_errors'], [])
                last = calls(output)[-1]
                self.assertLessEqual(last['returned_at'] - last['started_at'], bound + 0.5)
                if fault != 'late_reply':
                    record = json.loads((output / 'worker/cancellations.json').read_bytes())[0]
                    self.assertFalse(record['idle'])
                    self.assertLessEqual(record['timing']['ended_after_seconds'],
                                         record['timing']['verify_deadline_after_seconds'] + 0.05)

    def test_server_that_ignores_cancellation_stops_the_run(self):
        receipt, output, outer, value = run_fault('no_abort')
        self.assert_cleaned_and_bounded(receipt, outer, output, REHEARSAL_SECONDS)
        self.assertEqual(receipt['study_status'], 'failed')
        cancellations = json.loads((output / 'worker/cancellations.json').read_bytes())
        self.assertFalse(cancellations[0]['idle'])
        self.assertEqual(value['run']['stop_reason'], 'transport_failure')
        self.assertEqual(value['gate_status'], 'incomplete')

    def test_prefix_caching_enabled_is_refused_before_any_question(self):
        receipt, output, outer, value = run_fault('prefix_cache_enabled')
        self.assert_cleaned_and_bounded(receipt, outer, output, REHEARSAL_SECONDS)
        self.assertEqual(receipt['study_status'], 'failed')
        self.assertFalse((output / 'worker/run').exists())
        failure = json.loads((output / 'worker/failure.json').read_bytes()) if (output / 'worker/failure.json').exists() else {}
        self.assertIn('prefix caching', json.dumps(failure) + (output / 'worker/host-status.json').read_text())
        self.assertEqual(value['gate_status'], 'incomplete')

    def test_failures_are_bounded_cleaned_and_keep_honest_evidence(self):
        cases = {'http_error': ('transport_failure', True), 'storage': ('storage_exhausted', True),
                 'cancel': ('canceled', True), 'monitor_exit': ('canceled', True), 'model_startup': (None, False),
                 'log_flood': (None, False)}
        for fault, (stop, evidence) in cases.items():
            with self.subTest(fault=fault):
                receipt, output, outer, value = run_fault(fault)
                self.assert_cleaned_and_bounded(receipt, outer, output, REHEARSAL_SECONDS)
                self.assertEqual(receipt['study_status'], 'failed')
                self.assertFalse(value['technically_complete'])
                self.assertEqual(value['gate_status'], 'incomplete')
                self.assertEqual(value['run_evidence']['verified'], evidence)
                if evidence:
                    self.assertEqual(value['run']['stop_reason'], stop)
                    self.assertEqual(value['call_errors'], [])

    def test_surviving_child_is_cleaned_up(self):
        receipt, output, outer, value = run_fault('surviving_child')
        self.assert_cleaned_and_bounded(receipt, outer, output, REHEARSAL_SECONDS)
        self.assertTrue(value['technically_complete'])
        left = subprocess.run(['pgrep', '-f', 'time.sleep\\(600\\)'], capture_output=True, text=True).stdout.strip()
        self.assertEqual(left, '')


if __name__ == '__main__':
    unittest.main()
