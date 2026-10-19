"""Independent whole-run mutations; all model/game/provider data are synthetic."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from research.initial_geometry_assistance_v1.live_io import sha, write_new
from research.feedback_summary_probe_live_v1.live_evaluation import audit_study, evaluate
from research.feedback_summary_probe_live_v1.live_runtime import SCOPE
from tests.feedback_summary_live_fixture import create, protocol_patches
from tests.test_feedback_probe_audit_v1 import ScriptEngine


class ProbeLiveEvaluationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.inputs, cls.output, _ = create(cls.temp.name)

    def copy(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)/'copy'
        shutil.copytree(self.output, root)
        return root

    def content(self, output):
        with ExitStack() as stack:
            protocol_patches(stack)
            return audit_study(output, self.inputs, token_audit=lambda _: 100,
                               replay_factory=lambda cp, variant: ScriptEngine(cp))

    def test_full_transport_native_counts_and_replay_are_required(self):
        result = self.content(self.output)
        self.assertEqual((result['generations'], result['prefix_dispatches'], result['continuation_dispatches'],
                          result['offline_actions_including_bootstraps'], result['local_scorecards']),
                         (81, 36, 64, 116, 16))
        self.assertFalse(result['lifecycle_certified'])
        self.assertFalse(result['outcome_claim_permitted'])

    def test_missing_recognition_reply_and_changed_prompt_are_rejected(self):
        for mode in ('missing_recognition', 'prompt', 'usage', 'admission_kind'):
            with self.subTest(mode=mode):
                output = self.copy()
                events = [json.loads(x) for x in (output/'transport.jsonl').read_text().splitlines()]
                index = next(i for i, x in enumerate(events) if x.get('kind') == 'HTTP_request' and
                             x['id'].endswith('/recognition'))
                if mode == 'missing_recognition':
                    del events[index:index+3]
                elif mode == 'prompt':
                    events[index]['body']['messages'][0]['content'] = 'changed request'
                elif mode == 'admission_kind':
                    events[index+1]['request_kind'] = 'policy'
                else:
                    reply = json.loads(events[index+2]['raw'])
                    reply['usage'].update(completion_tokens=True, total_tokens=101)
                    events[index+2]['raw'] = json.dumps(reply)
                (output/'transport.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
                with self.assertRaises(ValueError):
                    self.content(output)

    def test_false_totals_and_missing_condition_are_rejected(self):
        for field, value in [('dispatch_attempts', 0), ('closed_scorecards', 0), ('continuations', [])]:
            with self.subTest(field=field):
                output = self.copy()
                worker = json.loads((output/'worker-result.json').read_bytes())
                worker[field] = value
                (output/'worker-result.json').write_text(json.dumps(worker))
                with self.assertRaises(ValueError):
                    self.content(output)

    def lifecycle(self, output):
        review = output.parent/'review'
        review.mkdir(exist_ok=True)
        write_new(review/'review-lock.json', {'SYNTHETIC_TEST_ONLY': True})
        pin = sha(review/'review-lock.json')
        lock = {'input_manifest_sha256': sha(self.inputs/'manifest.json'), 'source_inventory_sha256': 'a'*64,
                'game_receipt_sha256': 'b'*64, 'kernel_id': 'daichongwei06/unit-test'}
        from research.initial_geometry_assistance_v1.game_wheels import GAME_WHEEL_SOURCE
        group = {'ownership': 'registered', 'groups_absent': True, 'error': None,
                 'interrupted': [], 'remaining_members': []}
        cleanup = {'groups_absent': True, 'error': None, 'interrupted': [], 'groups': [group]}
        for name in ('worker-config.json', 'vllm.log', 'worker.log'):
            (output/name).write_text('{}')
        result = {'review_lock_sha256': pin, 'scope': SCOPE, 'error': None, 'worker_exit': 0,
                  'temporary_and_source_removed': True, 'lifecycle_finalized': False,
                  'source_inventory_sha256': 'a'*64, 'attempt_id': 'synthetic',
                  'process_cleanup': cleanup, 'final_process_cleanup': deepcopy(cleanup),
                  'GPU_cleanup': {'gpu_cleanup_verified': True, 'gpu_processes': 0},
                  'GPU': {'name': 'SYNTHETIC RTX PRO 6000'},
                  'game_wheels': {'source': GAME_WHEEL_SOURCE, 'wheel_count': 31,
                                  'game_environment_receipt_sha256': 'b'*64},
                  'evidence_sha256': {p.relative_to(output).as_posix(): sha(p)
                                      for p in output.rglob('*') if p.is_file()}}
        write_new(output/'provisional-result.json', result)
        witness = {'error': None, 'elapsed_seconds': 50, 'provisional_result_sha256': sha(output/'provisional-result.json'),
                   'provider_COMPLETE_and_exact_return_marker_required': True}
        write_new(output/'return-witness.json', witness)
        (output/'provider.log').write_text('FEEDBACK_SUMMARY_PROBE_RETURNED '+sha(output/'return-witness.json')+'\n')
        write_new(output/'provider-notebook.ipynb', {'SYNTHETIC_TEST_ONLY': True})
        write_new(output/'provider-saved-snapshot.json', {'source': {'SYNTHETIC_TEST_ONLY': True}})
        provider = {'status': 'COMPLETE', 'kernel_id': lock['kernel_id'], 'version': 2,
                    'log_sha256': sha(output/'provider.log'), 'submitted_source_sha256': sha(output/'provider-notebook.ipynb'),
                    'saved_snapshot_sha256': sha(output/'provider-saved-snapshot.json')}
        return review/'review-lock.json', lock, pin, provider

    def live(self, output, review, lock, pin, provider):
        with ExitStack() as stack:
            protocol_patches(stack)
            stack.enter_context(patch('research.feedback_summary_probe_live_v1.live_operator.verify_review', return_value=(lock, pin)))
            stack.enter_context(patch('research.feedback_summary_probe_live_v1.live_operator.validate_saved',
                                      return_value={'authority': {'attempt_id': 'synthetic'}}))
            return evaluate(output, self.inputs, review, provider, token_audit=lambda _: 100,
                            replay_factory=lambda cp, variant: ScriptEngine(cp))

    def test_witness_alone_cannot_promote_incomplete_provider_run(self):
        output = self.copy()
        review, lock, pin, provider = self.lifecycle(output)
        valid = self.live(output, review, lock, pin, provider)
        self.assertTrue(valid['technically_complete'])  # synthetic dependencies only
        for field, value in [('status', 'ERROR'), ('kernel_id', 'other/target'), ('version', True),
                             ('log_sha256', '0'*64), ('saved_snapshot_sha256', '0'*64)]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.live(output, review, lock, pin, dict(provider, **{field: value}))

    def test_late_witness_cleanup_uncertainty_and_stale_evidence_refuse(self):
        for mode in ('late', 'uncertain', 'stale', 'missing_finalization'):
            with self.subTest(mode=mode):
                output = self.copy()
                review, lock, pin, provider = self.lifecycle(output)
                if mode == 'late':
                    path = output/'return-witness.json'
                    value = json.loads(path.read_bytes()); value['elapsed_seconds'] = 3300.01
                    path.write_text(json.dumps(value))
                elif mode == 'uncertain':
                    path = output/'provisional-result.json'
                    value = json.loads(path.read_bytes()); value['process_cleanup']['groups'][0]['ownership'] = 'uncertain'
                    path.write_text(json.dumps(value))
                elif mode == 'stale':
                    (output/'worker-result.json').write_text('{}')
                else:
                    (output/'return-witness.json').unlink()
                with self.assertRaises((ValueError, FileNotFoundError)):
                    self.live(output, review, lock, pin, provider)
