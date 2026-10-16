"""Synthetic inference-contract/admission/gating tests; no pretrained weights or GPU."""
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from research.object_identification_v1 import inference as I, supervisor as S, replay as R


class DriverEnvironment(unittest.TestCase):
    def test_only_absolute_library_paths_survive_and_other_host_variables_do_not(self):
        path = str(Path(tempfile.gettempdir()).resolve())
        host = {'LD_LIBRARY_PATH': os.pathsep.join([path, '', '.', 'relative', path]),
                'PYTHONPATH': 'host-packages', 'LD_PRELOAD': 'unreviewed-library', 'KAGGLE_API_TOKEN': 'synthetic-secret'}
        env = S.subprocess_environment(host)
        self.assertEqual(env['LD_LIBRARY_PATH'], path)
        for key in ('PYTHONPATH', 'LD_PRELOAD', 'KAGGLE_API_TOKEN'):
            self.assertNotIn(key, env)
        self.assertEqual(env['MPLBACKEND'], 'Agg')
        self.assertEqual(env['PIP_NO_INDEX'], '1')
        self.assertNotIn('LD_LIBRARY_PATH', S.subprocess_environment({}))

    def test_invalid_driver_path_is_refused(self):
        for value in (True, 'x\0y', 'x\ny', 'a'*16385, os.pathsep.join(['.']*65)):
            with self.subTest(value=str(value)[:20]), self.assertRaises(ValueError):
                S.subprocess_environment({'LD_LIBRARY_PATH': value})

    @unittest.skipUnless(sys.platform == 'linux' and shutil.which('cc'), 'Linux CPU shared-library compiler required')
    def test_stripped_loader_fails_but_preserved_driver_path_loads_CPU_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/'fixture.c'
            source.write_text('int probe(void) { return 42; }\n')
            subprocess.run([shutil.which('cc'), '-shared', '-fPIC', str(source), '-o', str(root/'libinternvl_driver_fixture.so')],
                           check=True, capture_output=True, timeout=20)
            program = 'import ctypes; assert ctypes.CDLL("libinternvl_driver_fixture.so").probe() == 42'
            baseline = subprocess.run([sys.executable, '-I', '-c', program], env={'PATH': os.defpath},
                                      capture_output=True, text=True, timeout=10)
            corrected = subprocess.run([sys.executable, '-I', '-c', program],
                                      env=S.subprocess_environment({'LD_LIBRARY_PATH': tmp}),
                                      capture_output=True, text=True, timeout=10)
            self.assertNotEqual(baseline.returncode, 0)
            self.assertIn('cannot open shared object', baseline.stderr)
            self.assertEqual(corrected.returncode, 0, corrected.stderr)

    @unittest.skipUnless(sys.platform == 'linux', 'Linux supervisor signals required')
    def test_real_query_receives_driver_path_and_failure_keeps_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seen = []
            def command(argv, log, deadline, env, phase):
                seen.append(dict(env))
                raise RuntimeError('synthetic NVML unavailable')
            registry = SimpleNamespace(command=command, stop=lambda deadline: {
                'groups_absent': True, 'error': None, 'interrupted': [], 'groups': []})
            with patch.dict(S.os.environ, {'LD_LIBRARY_PATH': tmp, 'PYTHONPATH': 'not-forwarded'}), \
                    patch.object(S, 'InstallationProcesses', return_value=registry), \
                    patch.object(S.shutil, 'which', return_value='/opt/bin/nvidia-smi'), \
                    patch.object(S.signal, 'setitimer'), patch.object(S, 'finish', side_effect=lambda result, *args: result):
                result = S._execute(root, {}, {'review_lock_sha256': 'synthetic'}, 'synthetic', root,
                                    root/'output', time.monotonic())
            self.assertEqual(len(seen), 1)
            self.assertEqual(seen[0]['LD_LIBRARY_PATH'], tmp)
            self.assertNotIn('PYTHONPATH', seen[0])
            diagnostic = json.loads((root/'output/driver-loader.json').read_bytes())
            self.assertEqual(diagnostic['driver_search_paths'], [tmp])
            self.assertFalse(diagnostic['driver_load_tested_by_this_record'])
            self.assertEqual(result['status'], 'inference_incomplete')
            self.assertIn('GPU cleanup not verified', result['cleanup_error'])
            self.assertNotIn('gpu_cleanup_verified', result)


class InferenceContract(unittest.TestCase):
    def inputs(self, root):
        requests = []
        for index in range(1, 7):
            case = f'board-{index:02d}'
            raw = b'synthetic-image-'+case.encode()
            (root/(case+'.png')).write_bytes(raw)
            requests.append({'case_id': case, 'image': 'inputs/'+case+'.png', 'image_sha256': I.digest(raw),
                'prompt': I.PROMPT, 'model': I.MODEL, 'model_revision': I.MODEL_REVISION,
                'max_tokens': 4096, 'temperature': 0, 'stream': False})
        (root/'requests.jsonl').write_bytes(b''.join(I.canonical(row) for row in requests))
        return requests

    def test_requests_reconstructed_even_if_a_mutated_row_has_a_fresh_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            expected = self.inputs(root)
            self.assertEqual(I.requests_for(root), expected)
            for field, wrong in [('prompt', 'leaked answer'), ('model', 'different-model'),
                                 ('max_tokens', 8192), ('temperature', False), ('stream', 0),
                                 ('image', '../references/answers.json')]:
                altered = json.loads(json.dumps(expected))
                altered[0][field] = wrong
                (root/'requests.jsonl').write_bytes(b''.join(I.canonical(row) for row in altered))
                with self.subTest(field=field), self.assertRaises(ValueError):
                    I.requests_for(root)

    def test_raw_continuation_whitespace_is_kept_and_token_caps_are_strict(self):
        tokenizer = SimpleNamespace(decode=lambda ids, skip_special_tokens: '  {bad json}\n')
        class Tokenizer:
            def __len__(self): return 100
            decode = staticmethod(tokenizer.decode)
        tokenizer = Tokenizer()
        output = I.completion(tokenizer, [3, 4, 9], 9)
        self.assertEqual(output['content'], '  {bad json}\n')
        self.assertEqual(output['finish_reason'], 'stop')
        self.assertEqual(I.completion(tokenizer, [3]*4096, 9)['finish_reason'], 'length')
        for ids in ([], [True, 9], [3]*4097, [100, 9], [3, 4]):
            with self.subTest(ids_length=len(ids)), self.assertRaises(ValueError):
                I.completion(tokenizer, ids, 9)

    def test_no_generation_after_admission_closes_during_journal_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            requests = self.inputs(root)
            now = [0]
            def fsync(_): now[0] = 900
            with patch.object(I.os, 'fsync', side_effect=fsync), patch('builtins.print'):
                with patch.object(I, 'digest', wraps=I.digest):
                    generate = unittest.mock.Mock()
                    with self.assertRaisesRegex(TimeoutError, 'journal'):
                        I.execute_cases(requests, generate, root/'out', 1000, now=lambda: now[0])
                    generate.assert_not_called()
            self.assertEqual(len((root/'out/calls.jsonl').read_bytes().splitlines()), 1)

    def test_interruption_preserves_one_counted_admission_and_never_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            requests = self.inputs(root)
            calls = []
            def interrupted(request, until):
                calls.append(request['case_id'])
                raise KeyboardInterrupt()
            with self.assertRaises(KeyboardInterrupt):
                I.execute_cases(requests, interrupted, root/'out', 1000, now=lambda: 0)
            self.assertEqual(calls, ['board-01'])
            self.assertEqual(len((root/'out/calls.jsonl').read_bytes().splitlines()), 1)
            self.assertEqual((root/'out/responses.jsonl').read_bytes(), b'')

    def test_six_outputs_keep_the_existing_scorer_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            requests = self.inputs(root)
            def generate(request, until):
                return {'content': '  {invalid}\n', 'finish_reason': 'stop',
                        'generated_token_ids': [3, 9], 'completion_tokens': 2}
            result = I.execute_cases(requests, generate, root/'out', 1000, now=lambda: 0)
            self.assertEqual(result['generation_requests'], 6)
            rows = [json.loads(row) for row in (root/'out/responses.jsonl').read_bytes().splitlines()]
            self.assertEqual(len(rows), 6)
            self.assertEqual(set(rows[0]), {'case_id', 'model', 'model_revision', 'request_sha256',
                                            'content', 'finish_reason'})
            self.assertEqual(rows[0]['content'], '  {invalid}\n')
            with self.assertRaises(FileExistsError):
                I.execute_cases(requests, generate, root/'out', 1000, now=lambda: 0)

    def test_independent_replay_refuses_changed_template_tokens_counters_and_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            requests = self.inputs(root)
            def generate(request, until):
                return {'content': '  {}\n', 'finish_reason': 'stop', 'generated_token_ids': [3, 9],
                    'completion_tokens': 2, 'raw_text_with_special_tokens': '  {}\nEND',
                    'rendered_prompt': 'system USER '+request['prompt']+' ASSISTANT',
                    'prompt_token_ids': [1, 3, 4], 'prompt_tokens': 3, 'eos_token_id': 9,
                    'image_context_tokens': 256, 'image_sha256': request['image_sha256'],
                    'generation_seconds': 1, 'generation_parameters': {
                        'max_new_tokens': 4096, 'do_sample': False, 'num_beams': 1}}
            out = root/'out'
            I.execute_cases(requests, generate, out, 1000, now=lambda: 0)
            (out/'worker.json').write_bytes(I.canonical({'generation_requests': 6, 'study_requests': 6,
                'game_actions': 0, 'network_attempts': 0, 'pretrained_weights_loaded': True, 'execution_device': 'cuda'}))
            def rebuild(prompt): return 'system USER '+prompt+' ASSISTANT', [1, 3, 4], 9
            def decode(ids, eos):
                if ids != [3, 9]: raise ValueError('fixture token change')
                return {'content': '  {}\n', 'finish_reason': 'stop', 'generated_token_ids': [3, 9],
                        'completion_tokens': 2, 'raw_text_with_special_tokens': '  {}\nEND'}
            self.assertTrue(R.audit(out, requests, rebuild, decode)['request_and_token_replay_passed'])
            path = out/'board-01.json'
            original = path.read_bytes()
            for field, wrong in [('rendered_prompt', 'different system'), ('prompt_token_ids', [True, 3, 4]),
                                 ('completion_tokens', True), ('content', 'repaired JSON'),
                                 ('generated_token_ids', [4, 9]), ('generation_seconds', True)]:
                changed = json.loads(original)
                changed[field] = wrong
                path.write_bytes(I.canonical(changed))
                with self.subTest(field=field), self.assertRaises(ValueError):
                    R.audit(out, requests, rebuild, decode)
            path.write_bytes(original)
            summary = json.loads((out/'worker.json').read_bytes())
            summary['generation_requests'] = 0
            (out/'worker.json').write_bytes(I.canonical(summary))
            with self.assertRaisesRegex(ValueError, 'summary'):
                R.audit(out, requests, rebuild, decode)


class ReviewGate(unittest.TestCase):
    def test_authority_chain_needs_current_evidence_and_retained_time_amendment(self):
        pin = 'a'*64
        cap = {'review_lock_sha256': pin, 'approved': True, 'accepted_provider_overhead': True,
               'session_timeout_seconds': 3600, 'worker_seconds': 3300, 'provider_full_job_cap_verified': False,
               'owner_amendment_sha256': I.digest(b'synthetic owner amendment')}
        use = {'review_lock_sha256': pin, 'approved': True, 'owner_answer': 'synthetic test approval'}
        source = {'review_lock_sha256': pin, 'approved': True, 'owner_answer': 'synthetic test approval',
                  'scope_evidence_sha256': {'time_policy': I.digest(I.canonical(cap)),
                                            'scoped_use': I.digest(I.canonical(use))}}
        compute = {'review_lock_sha256': pin, 'approved': True, 'owner_answer': 'synthetic test approval',
                   'scope': S.SCOPE, 'source_approval_sha256': I.digest(I.canonical(source))}
        claim = {'review_lock_sha256': pin, 'consumed': True, 'attempt_id': 'synthetic-attempt',
                 'authorization_sha256': I.digest(I.canonical(compute))}
        evidence = {'review_lock_sha256': pin, 'time_policy': cap, 'scoped_use': use,
                    'source_approval': source, 'compute_authorization': compute, 'launch_claim': claim,
                    'retained_evidence': {cap['owner_amendment_sha256']: 'synthetic-amendment.txt',
                        compute['source_approval_sha256']: 'synthetic-source.json',
                        claim['authorization_sha256']: 'synthetic-compute.json'}}
        protocol = {'scope': S.SCOPE, 'live_runs_enabled': True}
        self.assertEqual(S.readiness(protocol, evidence), [])
        evidence['retained_evidence'].pop(cap['owner_amendment_sha256'])
        self.assertTrue(S.readiness(protocol, evidence))
        cap['accepted_provider_overhead'] = False
        self.assertTrue(S.readiness(protocol, evidence))

    def test_disabled_review_refuses_before_process_registry_or_gpu_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = I.canonical({'scope': S.SCOPE, 'live_runs_enabled': False})
            (root/'protocol.json').write_bytes(raw)
            (root/'review-lock.json').write_bytes(I.canonical({'artifacts': {'protocol.json': I.digest(raw)}}))
            with patch.object(S, 'InstallationProcesses') as processes:
                with self.assertRaisesRegex(SystemExit, 'REVIEW ONLY'):
                    S.run(root)
                processes.assert_not_called()
            self.assertFalse((root/'result.json').exists())

    def test_timeout_field_does_not_supply_owner_approval(self):
        for evidence in ({}, {'time_policy': {'approved': True, 'session_timeout_seconds': 3600}},
                         {'review_lock_sha256': 'fake', **{name: {} for name in (
                             'time_policy', 'scoped_use', 'source_approval',
                             'compute_authorization', 'launch_claim')}}):
            with self.subTest(evidence=evidence):
                self.assertTrue(S.readiness({'scope': S.SCOPE, 'live_runs_enabled': True}, evidence))

    @unittest.skipUnless(sys.platform == 'linux', 'Linux worker alarm required')
    def test_lifecycle_alarm_interrupts_stalled_finalization_and_restores_handler(self):
        previous = signal.getsignal(signal.SIGALRM)
        with self.assertRaisesRegex(TimeoutError, 'worker alarm'):
            with S.lifecycle_alarm(time.monotonic()+.03):
                time.sleep(1)
        self.assertEqual(signal.getsignal(signal.SIGALRM), previous)

    def test_artifact_mutation_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'protocol.json').write_bytes(b'changed')
            (root/'review-lock.json').write_bytes(I.canonical({'artifacts': {'protocol.json': I.digest(b'original')}}))
            with self.assertRaisesRegex(ValueError, 'differs'):
                S.verify_packet(root)

    def test_interruption_after_final_receipt_never_writes_witness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(S.time, 'monotonic', side_effect=[3299.9, KeyboardInterrupt()]):
                with self.assertRaises(KeyboardInterrupt):
                    S.finish({'status': 'provisional_complete'}, root, 0, 3300)
            self.assertTrue((root/'result.json').exists())
            self.assertFalse((root/'completion-witness.json').exists())

    def test_slow_final_output_cannot_return_a_passing_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(S.time, 'monotonic', side_effect=[3299.8, 3299.81, 3299.82, 3299.83, 3300.1]), patch('builtins.print'):
                with self.assertRaisesRegex(TimeoutError, 'completion-output'):
                    S.finish({'status': 'provisional_complete'}, tmp, 0, 3300)


if __name__ == '__main__':
    unittest.main()
