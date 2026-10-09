"""The independent evaluator: scores only retained replies with the unchanged scorer, and never lets interrupted,
tampered or inconsistent evidence produce a complete verdict (CPU only; synthetic evidence, scripted answers)."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from research.progress_subgoal_v1.evaluate_run import score_call
from research.progress_subgoal_v1.score import analyze
from scripts.evaluate_progress_subgoal_v1_runtime2 import evaluate_output
from tests import psv1r2_fixtures as FX

ROOT = Path(__file__).resolve().parents[1]


def offline(policy='scripted', count=None, drop=()):
    frozen, _, rows, _, _ = FX.schedule()
    probes = {p['probe_id']: p for p in frozen['probes']}
    passes = {'pass_1': {}, 'pass_2': {}}
    for n, ((_, _, pass_id, probe_id, _), (content, finish)) in enumerate(zip(rows, FX.scripted_contents(policy))):
        if (count is not None and n >= count) or n in drop:
            continue
        passes[pass_id][probe_id] = score_call(probes[probe_id], {'finish_reason': finish, 'response': content})
    return analyze(frozen['probes'], {k: v for k, v in passes.items() if v}, 'withheld')


class Evaluator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = FX.declared_protocol()
        cls.base = Path(tempfile.mkdtemp(prefix='psv1r2-evaluator-'))
        cls.complete = FX.write_evidence(cls.base / 'complete', cls.protocol)
        cls.value = evaluate_output(cls.complete, mode='rehearsal', root=ROOT, protocol=cls.protocol)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base, ignore_errors=True)

    def evaluate(self, name, **kwargs):
        folder = FX.write_evidence(self.base / name, self.protocol, **kwargs)
        return evaluate_output(folder, mode='rehearsal', root=ROOT, protocol=self.protocol)

    def mutate(self, name, change):
        folder = self.base / name
        shutil.copytree(self.complete, folder)
        change(folder)
        return evaluate_output(folder, mode='rehearsal', root=ROOT, protocol=self.protocol)

    def test_complete_evidence_reproduces_the_offline_scores(self):
        self.assertTrue(self.value['technically_complete'], (self.value['lifecycle_errors'], self.value['call_errors']))
        self.assertEqual(self.value['gate_status'], 'complete')
        self.assertEqual(self.value['analysis'], offline())
        self.assertEqual(set(self.value['gate']), {'raw_plus_computed_record', 'raw_plus_computed_record_plus_safeguard'})

    def test_oracle_answers_are_eligible_through_the_same_path(self):
        value = self.evaluate('oracle', policy='oracle')
        self.assertTrue(value['technically_complete'])
        self.assertEqual(set(value['gate'].values()), {'eligible_for_memory_or_supervision'})
        self.assertEqual(value['analysis'], offline('oracle'))

    def test_interrupted_schedule_cannot_be_complete(self):
        # Stopped at the admission cutoff inside pass 2: the evidence is consistent, the verdict is incomplete.
        value = self.evaluate('cut', count=4000, stop_reason='admission_cutoff')
        self.assertEqual(value['call_errors'], [])
        self.assertFalse(value['technically_complete'])
        self.assertEqual(value['gate_status'], 'incomplete')
        self.assertEqual(set(value['gate'].values()), {'incomplete'})
        self.assertEqual(value['analysis']['completeness']['primary'], 'incomplete')

    def test_never_finalized_or_unmanifested_evidence_is_never_complete(self):
        def unfinalized(folder):
            index = json.loads((folder / 'questionnaire/run.json').read_bytes())
            FX.put(folder, 'questionnaire/run.json', dict(index, status='running'))
            FX.finalize(folder)
        value = self.mutate('running', unfinalized)
        self.assertFalse(value['technically_complete'])
        self.assertEqual(set(value['gate'].values()), {'incomplete'})
        value = self.mutate('no-manifest', lambda f: (f / 'evidence-manifest.json').unlink())
        self.assertFalse(value['technically_complete'])
        self.assertFalse(value['evidence']['manifest_verified'])
        self.assertEqual(set(value['gate'].values()), {'incomplete'})

    def test_an_interrupted_call_is_not_a_final_record(self):
        def intent(folder):
            path = folder / 'questionnaire/calls/05851.json'
            record = json.loads(path.read_bytes())
            FX.put(folder, 'questionnaire/calls/05851.json',
                   {k: v for k, v in record.items() if k not in ('response', 'response_sha256', 'http_status',
                                                                  'returned_at')} | {'status': 'intent'})
            FX.finalize(folder)
        value = self.mutate('intent', intent)
        self.assertFalse(value['technically_complete'])
        self.assertTrue(any('not a final call status' in e for e in value['call_errors']))

    def test_tampering_and_inconsistency_are_call_errors(self):
        def edit(n, **fields):
            def change(folder):
                name = f'questionnaire/calls/{n:05d}.json'
                record = json.loads((folder / name).read_bytes())
                record.update(fields)
                FX.put(folder, name, record)
                FX.finalize(folder)
            return change
        raw = json.loads(json.loads((self.complete / 'questionnaire/calls/00010.json').read_bytes())['response'])
        forged = json.dumps(dict(raw, usage=dict(raw['usage'], prompt_tokens=raw['usage']['prompt_tokens'] + 1)))
        long = json.dumps(dict(raw, choices=[dict(raw['choices'][0], finish_reason='length')],
                               usage=dict(raw['usage'], completion_tokens=5)))
        other = json.dumps(dict(raw, model='another-model'))
        cases = {'response hash': edit(10, response=forged),
                 'token audit': edit(10, response=forged, response_sha256=hashlib.sha256(forged.encode()).hexdigest()),
                 'length finish': edit(10, response=long, response_sha256=hashlib.sha256(long.encode()).hexdigest()),
                 'served model': edit(10, response=other, response_sha256=hashlib.sha256(other.encode()).hexdigest()),
                 'request hash': edit(11, request_sha256='0' * 64),
                 'scheduled call': edit(12, probe_id='development:x'),
                 'timestamps': edit(13, started_at=0.0),
                 'admission': edit(14, started_at=1195.0, returned_at=1195.1)}
        for label, change in cases.items():
            value = self.mutate('tamper-' + label.replace(' ', '-'), change)
            self.assertFalse(value['technically_complete'], label)
            self.assertTrue(value['call_errors'], label)
            self.assertIsNone(value['analysis'], label)

    def test_a_timed_out_call_needs_its_own_idle_measurements(self):
        def timeout(records, idle):
            records[20] = {k: v for k, v in records[20].items() if k not in ('response', 'response_sha256', 'http_status')}
            records[20].update(status='timed_out', idle_verification=idle, cancellation_timing={
                'torn_down_after_seconds': 2.0, 'ended_after_seconds': 2.1, 'inference_deadline_after_seconds': 2.0,
                'verify_deadline_after_seconds': 6.0})
            return records
        good = {'idle': True, 'running': 0, 'waiting': 0, 'aborted_total': 1, 'waited_seconds': 0.05,
                'window_seconds': 4.0, 'reads': 1}
        value = self.evaluate('timeout-ok', records_hook=lambda r: timeout(r, good))
        self.assertEqual(value['call_errors'], [])
        self.assertEqual(value['run']['counts'], {'answered': 5851, 'timed_out': 1})
        self.assertEqual(value['gate_status'], 'incomplete')  # an unknown outcome is a missing answer, never scored
        self.assertFalse(value['technically_complete'])
        busy = dict(good, running=1, idle=True)  # a recorded flag is never trusted
        value = self.evaluate('timeout-busy', records_hook=lambda r: timeout(r, busy))
        self.assertTrue(any('not shown idle' in e for e in value['call_errors']))

    def test_lifecycle_and_ledger_must_hold(self):
        def failed(result):
            return dict(result, passed=False, verdict_status='failed', failed_stage='cleanup', error='not verified')
        value = self.evaluate('lifecycle', result_hook=failed)
        self.assertFalse(value['lifecycle_passed'])
        self.assertFalse(value['technically_complete'])

        def unplanned(result):
            result = copy.deepcopy(result)
            result['ledger']['entries'].append({'id': 'Q00000', 'kind': 'questionnaire'})
            result['ledger']['issued'] += 1
            return result
        value = self.evaluate('ledger', result_hook=unplanned)
        self.assertFalse(value['lifecycle_passed'])

        def limits(result):
            return dict(result, limits=dict(result['limits'], admission_cutoff_seconds=3120))
        value = self.evaluate('limits', result_hook=limits)
        self.assertTrue(any('limits' in e for e in value['lifecycle_errors']))

    def test_collected_answers_with_failed_post_run_checks_qualify_no_arm(self):
        # Frozen protocol v2 §9: every answer retained, but the cancellation probes after the questionnaire were
        # refused at the admission cutoff. The attempt fails; the scores stay descriptive; no arm qualifies.
        def refused(result):
            return dict(result, passed=False, verdict_status='failed', failed_stage='cancellation_C1',
                        error='request refused: admission cutoff reached')
        value = self.evaluate('post-run-refused', policy='oracle', result_hook=refused)
        self.assertEqual(value['call_errors'], [])
        self.assertFalse(value['lifecycle_passed'])
        self.assertTrue(value['questionnaire_collected'])
        self.assertEqual(value['gate_status'], 'complete')
        self.assertFalse(value['technically_complete'])
        self.assertEqual(value['attempt_verdict'], 'failed_technically_incomplete')
        self.assertEqual(value['analysis'], offline('oracle'))
        self.assertEqual(set(value['descriptive_readiness'].values()), {'eligible_for_memory_or_supervision'})
        self.assertEqual(set(value['gate'].values()), {'incomplete'})

    def test_attempt_verdict_and_collection_on_complete_and_cut_runs(self):
        self.assertEqual(self.value['attempt_verdict'], 'technically_complete')
        self.assertTrue(self.value['questionnaire_collected'])
        self.assertEqual(self.value['gate'], self.value['descriptive_readiness'])
        value = self.evaluate('cut-verdict', count=4000, stop_reason='admission_cutoff')
        self.assertFalse(value['questionnaire_collected'])
        self.assertEqual(value['attempt_verdict'], 'failed_technically_incomplete')

    def test_invalid_answers_stay_a_reliability_failure_not_an_over_claim(self):
        # Replace every valid answer to an over-claim gate member with malformed output.
        from research.progress_subgoal_v1 import questions as Q
        frozen, _, rows, _, audit = FX.schedule()
        probes = {p['probe_id']: p for p in frozen['probes']}

        def malformed(records):
            for record in records:
                probe = probes[record['probe_id']]
                if any(Q.gate_member(g, probe) for g in Q.OVER_CLAIM_GATES):
                    raw = FX.reply('{"answer": "maybe"}', 'stop', record['audit_prompt_tokens'])
                    record.update(response=raw, response_sha256=hashlib.sha256(raw.encode()).hexdigest())
            return records
        value = self.evaluate('invalid-gates', records_hook=malformed)
        self.assertEqual(value['call_errors'], [])
        for arm, gates in value['analysis']['over_claims'].items():
            for gate, row in gates.items():
                self.assertEqual(row['status'], 'insufficient_valid_opportunities', (arm, gate))
                self.assertEqual(row['over_claim_contexts'], 0, (arm, gate))
                self.assertGreater(row['invalid_member_responses'], 0, (arm, gate))
            validity = value['analysis']['validity'][arm]
            self.assertNotEqual(validity['gate_member_responses']['status'], 'passes')
            self.assertEqual(value['gate'][arm], 'not_eligible')


if __name__ == '__main__':
    unittest.main()
