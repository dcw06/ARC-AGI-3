"""Synthetic runtime contracts. No model weights, GPU, provider or network."""
from contextlib import nullcontext
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from certification.phase4_multimodal_preflight_v3.images import png
from research.object_discovery_boundaries_v1 import inference as I, supervisor as S, deployment as D
from research.object_discovery_boundaries_v1.prepare import request_for, requests_for
from research.object_identification_v1.mount_check import canonical


class Generation(unittest.TestCase):
    def requests(self):
        return [{'case_id': f'board-{i:02d}'} for i in range(1, 7)]

    def test_native_wiring_preserves_raw_before_invalid_decode(self):
        class Tensor:
            def __init__(self, ids): self.ids = ids
            def __getitem__(self, key): return self
            def to(self, *args): return self
            def tolist(self): return self.ids
        seen, raw = {}, []
        def generate(**kwargs):
            seen.update(kwargs)
            return SimpleNamespace(sequences=Tensor([1, 2, 3, 70, 99]))
        model = SimpleNamespace(generate=generate, generation_config=SimpleNamespace(eos_token_id=99))
        processor = SimpleNamespace(post_process_image_text_to_text=lambda *a, **k: ['native output'])
        torch = SimpleNamespace(bfloat16='bf16', inference_mode=nullcontext,
            autocast=lambda *a, **k: nullcontext(), cuda=SimpleNamespace(synchronize=lambda: None))
        with patch.object(I, 'prepare_prompt_inputs', return_value=({'input_ids': Tensor([1, 2, 3])}, {}, ['native'])), \
                patch.object(I, 'decode_generation', side_effect=ValueError('unfinished point')):
            result = I.native_generate(model, processor, None, {'prompt': 'generic'}, 10**15,
                torch, ['deadline'], raw_sink=lambda row: raw.append(dict(row)))
        self.assertEqual(result['generated_token_ids'], [70, 99])
        self.assertFalse(result['decode_valid'])
        self.assertIn('unfinished point', result['decode_error'])
        self.assertEqual(len(raw), 1)
        self.assertNotIn('decode_error', raw[0])
        self.assertEqual((seen['max_new_tokens'], seen['do_sample'], seen['num_beams']), (4096, False, 1))
        self.assertEqual(seen['logits_processor'], ['native'])
        self.assertEqual(seen['stopping_criteria'], ['deadline'])

    def test_six_admissions_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, calls = Path(tmp)/'calls', []
            summary = I.execute_cases(self.requests(), lambda r, d: calls.append(r) or {}, out, 1000, now=lambda: 0)
            self.assertEqual(len(calls), 6)
            self.assertEqual(summary['generation_requests'], 6)
            self.assertEqual(len(list(out.glob('*-admission.json'))), 6)
            with self.assertRaises(FileExistsError):
                I.execute_cases(self.requests(), lambda *a: self.fail('retried'), out, 1000, now=lambda: 0)

    def test_failed_generation_keeps_admission_without_retry(self):
        calls = []
        def fail(*args):
            calls.append(1)
            raise TimeoutError('stuck')
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'calls'
            with self.assertRaises(TimeoutError): I.execute_cases(self.requests(), fail, out, 1000, now=lambda: 0)
            self.assertEqual(calls, [1])
            self.assertTrue((out/'board-01-admission.json').exists())
            self.assertFalse((out/'worker.json').exists())

    def test_admission_write_can_close_generation(self):
        times = iter([0, 0, 900, 900])
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(TimeoutError):
            I.execute_cases(self.requests(), lambda *a: self.fail('late call'), Path(tmp)/'calls', 1000,
                now=lambda: next(times))

    def test_case_finalization_overrun_refuses_summary(self):
        times = iter([0, 0, 0, 0, 181, 181])
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'calls'
            with self.assertRaises(TimeoutError):
                I.execute_cases(self.requests(), lambda *a: {}, out, 1000, now=lambda: next(times))
            self.assertTrue((out/'board-01.json').exists())
            self.assertFalse((out/'worker.json').exists())

    def test_wrong_count_or_order_never_generates(self):
        for rows in ([], self.requests()[:5], self.requests()[::-1]):
            with self.assertRaises(ValueError):
                I.execute_cases(rows, lambda *a: self.fail('call'), 'unused', 1000)


class PixelTool(unittest.TestCase):
    def setUp(self):
        self.grid = [[0]*64 for _ in range(64)]
        self.grid[3][2:4] = [1, 2]
        self.raw = png(self.grid, cell=7)
        self.request = request_for('board-01', self.raw)

    def test_visible_color_only_keeps_duplicates_and_does_not_merge_multicolor(self):
        result = I.attach_masks(dict(decode_valid=True, points=[{'cell_xy': [2, 3]}]*2), self.raw, self.request)
        self.assertEqual([r['cells'] for r in result['objects']], [[[2, 3]], [[2, 3]]])
        self.assertTrue(all(r['semantic_object_boundary_certified'] is False for r in result['objects']))

    def test_background_prediction_is_not_filtered_using_references(self):
        result = I.attach_masks(dict(decode_valid=True, points=[{'cell_xy': [0, 0]}]), self.raw, self.request)
        self.assertEqual(len(result['objects'][0]['cells']), 4094)

    def test_invalid_decoder_cannot_supply_masks(self):
        result = I.attach_masks(dict(decode_valid=False, points=[{'cell_xy': [2, 3]}]), self.raw, self.request)
        self.assertEqual(result['objects'], [])
        with self.assertRaisesRegex(ValueError, 'explicit native'):
            I.attach_masks(dict(decode_valid=1, points=[]), self.raw, self.request)

    def test_changed_grid_is_refused(self):
        self.grid[0][0] = 4
        with self.assertRaisesRegex(ValueError, 'grid differs'):
            I.attach_masks(dict(decode_valid=True, points=[]), png(self.grid, cell=7), self.request)


class RuntimeGuards(unittest.TestCase):
    def test_dependency_lock_is_the_completed_tests_unchanged_lock(self):
        original = Path(I.__file__).resolve().parents[1]/'molmopoint_identification_v1/runtime_requirements.lock'
        self.assertEqual(S.runtime_requirements(), original.read_bytes())

    def test_no_authority_stops_before_execution(self):
        self.assertEqual((S.SCOPE['generation_requests'], S.SCOPE['max_tokens_per_generation'],
                          S.SCOPE['max_generated_tokens']), (6, 4096, 24576))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'review-lock.json').write_bytes(canonical({'artifacts': {}}))
            (root/'protocol.json').write_bytes(canonical({'scope': S.SCOPE, 'live_runs_enabled': False}))
            with patch.object(S, '_execute', side_effect=AssertionError('GPU queried')):
                with self.assertRaisesRegex(SystemExit, 'REVIEW ONLY'): S.run(root)

    def test_notebook_bootstrap_refuses_before_extraction(self):
        with self.assertRaisesRegex(SystemExit, 'APPROVAL REQUIRED'):
            exec(compile(D.bootstrap(b'{}'), '<review-only>', 'exec'), {'AUTHORITY': None})

    def test_late_receipt_and_interruption_leave_no_witness(self):
        for final_time, error in ((60.1, RuntimeError), (KeyboardInterrupt(), KeyboardInterrupt)):
            with tempfile.TemporaryDirectory() as tmp:
                with patch.object(S.time, 'monotonic', side_effect=[59.9, final_time]):
                    with self.assertRaises(error):
                        S.finish({'status': 'provisional_complete'}, tmp, 0, 60)
                self.assertTrue((Path(tmp)/'result.json').exists())
                self.assertFalse((Path(tmp)/'completion-witness.json').exists())

    def test_staging_exposes_seven_files_and_rejects_cued_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); mount = root/'mount'; mount.mkdir(); rows = []; requests = []
            def add(name, raw):
                (mount/name).write_bytes(raw)
                rows.append(dict(name=name, bytes=len(raw), sha256=I.sha(raw)))
            image = png([[0]*64 for _ in range(64)], cell=7)
            for i in range(1, 7):
                case = f'board-{i:02d}'; add(case+'.png', image); requests.append(request_for(case, image))
            add('requests.jsonl', b''.join(canonical(r) for r in requests))
            add('runtime.whl', b'synthetic installation input')
            receipt = S.stage_agent_inputs(mount, root/'staged', rows, lambda: None)
            self.assertEqual(receipt['files_checked'], 7)
            self.assertEqual(len(requests_for(root/'staged')), 6)
            self.assertFalse((root/'staged/runtime.whl').exists())
            with self.assertRaisesRegex(ValueError, 'seven distinct'):
                S.stage_agent_inputs(mount, root/'duplicate', [rows[0]]+rows, lambda: None)
            requests[0]['prompt'] = 'Point to the human-labelled target.'
            raw = b''.join(canonical(r) for r in requests)
            (mount/'requests.jsonl').write_bytes(raw)
            rows[6].update(bytes=len(raw), sha256=I.sha(raw))
            with self.assertRaisesRegex(ValueError, 'contract differs'):
                S.stage_agent_inputs(mount, root/'cued', rows, lambda: None)


if __name__ == '__main__': unittest.main()
