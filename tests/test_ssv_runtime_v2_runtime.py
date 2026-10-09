"""Track 3 runtime v2: mounts, model binding, installer guards, review packaging, extracted-payload imports and a
connected CPU rehearsal replayed by the runtime v2 target evaluator and study report. No model, GPU or provider."""
import base64
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from research.stagnation_supervision_runtime_v2 import authority as A, model_binding as M, mounts as MO
from research.stagnation_supervision_runtime_v2 import publisher_host as H
from research.stagnation_supervision_runtime_v2.notebook import build_review, review_notebook
from tests import ssv_runtime_v2_fixtures as FX

ROOT = A.ROOT


class Mounts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def competition(self, layout):
        mount = self.base / layout
        for name in ('arc_agi_3_wheels', 'environment_files'):
            (mount / name).mkdir(parents=True)
        return mount

    def test_competition_mount_accepts_either_layout_and_refuses_ambiguity(self):
        mount = self.competition('competitions/arc-prize-2026-arc-agi-3')
        self.assertEqual(MO.competition_mount(ROOT, inputs=self.base), mount)
        (self.base / 'arc-prize-2026-arc-agi-3').symlink_to(mount, target_is_directory=True)
        self.assertEqual(MO.competition_mount(ROOT, inputs=self.base), mount)  # alias to the other layout
        (self.base / 'arc-prize-2026-arc-agi-3').unlink()
        self.competition('arc-prize-2026-arc-agi-3')
        with self.assertRaises(MO.MountRefused):
            MO.competition_mount(ROOT, inputs=self.base)

    def test_competition_mount_refuses_missing_layouts_and_broken_aliases(self):
        with self.assertRaises(MO.MountRefused):
            MO.competition_mount(ROOT, inputs=self.base)
        (self.base / 'competitions').mkdir()
        (self.base / 'competitions/arc-prize-2026-arc-agi-3').symlink_to(self.base / 'nowhere', target_is_directory=True)
        with self.assertRaises(MO.MountRefused):
            MO.competition_mount(ROOT, inputs=self.base)
        (self.base / 'competitions/arc-prize-2026-arc-agi-3').unlink()
        (self.base / 'competitions/arc-prize-2026-arc-agi-3/environment_files').mkdir(parents=True)
        with self.assertRaises(MO.MountRefused):
            MO.competition_mount(ROOT, inputs=self.base)  # arc_agi_3_wheels missing

    def test_wheel_mount_is_the_verified_runtime_rule(self):
        for layout in ('datasets/driessmit1/arc3-vllm-h100-wheelhouse-v3', 'arc3-vllm-h100-wheelhouse-v3'):
            (self.base / layout).mkdir(parents=True)
        with self.assertRaises(H.HostMismatch):
            MO.wheelhouse_mount(ROOT, inputs=self.base)  # two layouts: ambiguous
        (self.base / 'arc3-vllm-h100-wheelhouse-v3').rmdir()
        self.assertEqual(MO.wheelhouse_mount(ROOT, inputs=self.base),
                         self.base / 'datasets/driessmit1/arc3-vllm-h100-wheelhouse-v3')


class ModelBinding(unittest.TestCase):
    def primary(self):
        from certification.phase4_integrated_v2.model_process import load_operational_primary
        return load_operational_primary(ROOT)

    def test_placeholders_refuse_before_any_hashing(self):
        with self.assertRaises(H.HostMismatch):
            M.bind_primary(ROOT, self.primary())

    def test_resolved_binding_replaces_only_location_and_tree_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            FX.source_tree(root)
            FX.resolved_protocol(root)
            base = root / 'input'
            (base / 'datasets/synthetic-owner/qwen-snapshot').mkdir(parents=True)
            protocol = json.loads((root / A.PROTOCOL).read_bytes())
            protocol['model']['mounted_path'] = str(base / 'datasets/synthetic-owner/qwen-snapshot')
            (root / A.PROTOCOL).write_text(json.dumps(protocol), encoding='utf-8')
            with mock.patch.object(H, 'INPUT_ROOT', base):
                original = self.primary()
                bound = M.bind_primary(root, original)
            self.assertEqual(bound.model_path, base / 'datasets/synthetic-owner/qwen-snapshot')
            self.assertEqual(bound.model_tree_sha256, 'b480ad92cda91474084c795d2ff64b07a6c477909b22d2784d24abf8fb4ef7df')
            self.assertEqual(replace(bound, model_path=original.model_path, model_tree_sha256=original.model_tree_sha256),
                             original)

    def test_layout_or_identity_drift_refuses(self):
        primary = self.primary()
        for change in ({'shard_count': 5}, {'required_files': ('config.json',)}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                M.bind_primary(ROOT, replace(primary, **change))


class Installer(unittest.TestCase):
    def test_installation_time_override_is_rehearsal_only(self):
        from research.stagnation_supervision_runtime_v2.prepare import prepare
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'SSV_REHEARSAL': ''}):
            with self.assertRaises(PermissionError):
                prepare(Path(tmp) / 's', Path(tmp) / 'o', tmp, tmp, {}, 0.0, root=ROOT, install_seconds=1800)

    def test_old_wheelhouse_layout_is_refused_before_installation(self):
        """The R4/R6 layout (SHA256SUMS of 179 entries plus wheelhouse-manifest.json) is not the verified mount."""
        from research.stagnation_supervision_runtime_v2.publisher_install import verify_bundle
        protocol = json.loads((ROOT / A.PROTOCOL).read_bytes())
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'wheelhouse-manifest.json').write_text('{}')
            (Path(tmp) / 'SHA256SUMS').write_text('')
            with self.assertRaises(ValueError):
                verify_bundle(tmp, protocol['dataset'], protocol['bundle'])

    def test_launch_refuses_staged_inputs_in_live_mode(self):
        from research.stagnation_supervision_runtime_v2.launch import run
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PermissionError):
                run(Path(tmp) / 'out', tmp, started=0.0, mode='live', session='1', staged_inputs=tmp)
            self.assertFalse((Path(tmp) / 'out').exists())


class Packaging(unittest.TestCase):
    def test_review_notebook_is_private_offline_gpu_disabled_and_pinned(self):
        notebook, metadata, bindings, pending, inventory = review_notebook(ROOT, 9)
        self.assertEqual((metadata['enable_gpu'], metadata['enable_tpu'], metadata['enable_internet'], metadata['is_private']),
                         (False, False, False, True))
        self.assertEqual(metadata['competition_sources'], ['arc-prize-2026-arc-agi-3'])
        self.assertEqual(metadata['dataset_sources'], ['REPLACE_WITH_MODEL_OWNER/REPLACE_WITH_MODEL_DATASET/1'])
        self.assertEqual(metadata['model_sources'], [])
        self.assertEqual(metadata['docker_image_pinning_type'], 'original')
        self.assertTrue(pending)
        code = notebook['cells'][1]['source']
        self.assertEqual(code.count("MODE = 'live'\n"), 1)
        self.assertEqual(code.count("SESSION = '1'\n"), 1)
        self.assertEqual(set(bindings), set(inventory['files']))
        self.assertLess(len(json.dumps(notebook)), 900000)

    def test_extracted_payload_imports_every_top_level_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'review'
            lock = build_review(folder, root=ROOT, revision=9)
            from scripts.stagnation_supervision_runtime_v2_package import extract
            with mock.patch('scripts.stagnation_supervision_runtime_v2_package.ROOT', ROOT):
                _, _, payload = extract(folder)
            source = Path(tmp) / 'source'
            for name, data in payload.items():
                (source / name).parent.mkdir(parents=True, exist_ok=True)
                (source / name).write_bytes(data)
            modules = sorted(n[:-3].replace('/', '.').removesuffix('.__init__') for n in payload if n.endswith('.py'))
            code = ('import importlib, sys\nsys.path.insert(0, sys.argv[1])\nbad = {}\n'
                    'for name in sys.argv[2:]:\n    try:\n        importlib.import_module(name)\n'
                    '    except Exception as exc:\n        bad[name] = repr(exc)[:200]\nprint(bad)\n')
            value = subprocess.run([sys.executable, '-I', '-c', code, str(source), *modules], capture_output=True,
                                   text=True, timeout=300, cwd=tmp)
            self.assertEqual(value.returncode, 0, value.stderr[-1500:])
            self.assertEqual(value.stdout.strip(), '{}')
            self.assertEqual(len(payload), len(lock['bindings']))
            gate = ('import sys, json\nsys.path.insert(0, sys.argv[1])\n'
                    'from research.stagnation_supervision_runtime_v2 import authority as A\n'
                    'A.load_protocol(sys.argv[1])\n'
                    'try:\n    A.require_live(sys.argv[1])\nexcept A.LiveRefused as exc:\n    print(json.dumps(exc.reasons))\n')
            value = subprocess.run([sys.executable, '-I', '-c', gate, str(source)], capture_output=True, text=True,
                                   timeout=120, cwd=tmp)
            self.assertEqual(value.returncode, 0, value.stderr[-1500:])
            self.assertEqual(json.loads(value.stdout), [
                'unresolved placeholders: kernel_ids.1, kernel_ids.2, model.kaggle_source, model.mounted_path',
                'authorization: ValueError: no review source lock'])


class ConnectedRehearsal(unittest.TestCase):
    def test_short_connected_rehearsal_replays_and_keeps_quantities_separate(self):
        from research.grounded_action_v1.engine import restore_game_mount
        from research.stagnation_supervision_v1.closed_loop import bridge as B
        from research.stagnation_supervision_runtime_v2.launch import run
        from research.stagnation_supervision_runtime_v2.report import study_report
        with tempfile.TemporaryDirectory(prefix='ssv-rt2-connected-') as tmp:
            work = Path(tmp)
            games = restore_game_mount(work / 'games')
            env = {'SSV_REHEARSAL': '1', 'CUDA_VISIBLE_DEVICES': '', 'SSV_REHEARSAL_GAMES': str(games),
                   'SSV_REHEARSAL_GROUPS': 'b1-ls20', 'SSV_REHEARSAL_ACTIONS': '12'}
            with mock.patch.dict(os.environ, env):
                import time
                receipt = run(work / 'working/out', work / 'working', started=time.monotonic(), mode='rehearsal',
                              internal_seconds=1500, session='1')
                spec = B.session_run_spec('1', 'rehearsal')
            self.assertEqual((receipt['error'], receipt['study_status'], receipt['installation']),
                             (None, 'study_complete_pending_independent_evaluation', 'none'))
            report = study_report(work / 'working/out', spec, mode='rehearsal', session='1', internal_seconds=1500)
        self.assertTrue(report['technically_complete'], report['problems'])
        self.assertFalse(report['target_accepted'])  # rehearsal evidence never certifies the target
        endpoints = report['endpoints']
        self.assertEqual(set(endpoints), {'behavioural_recovery', 'state_novelty_in_windows', 'completed_levels',
                                          'false_interruptions', 'false_interruptions_calls', 'realised_cost'})
        self.assertEqual(endpoints['false_interruptions']['triggered']['eligible_controls'], ['wa30'])
        self.assertEqual(endpoints['false_interruptions']['triggered']['status'], 'not_certifiable_minimum_not_met')
        self.assertIn('ls20', endpoints['false_interruptions']['triggered']['excluded_exploratory_or_unvalidated_games'])
        episodes = report['ls20_display_and_oscillation']['episodes']
        self.assertEqual(sorted(e['arm'] for e in episodes), ['continuation', 'periodic', 'triggered'])
        for episode in episodes:
            self.assertIn('scope', episode)
            self.assertEqual(episode['completed_levels'], 0)


    def test_successor_stack_fault_matrix_retains_failures_and_cleans_up(self):
        from research.grounded_action_v1.engine import restore_game_mount
        from research.stagnation_supervision_v1.closed_loop import bridge as B
        from research.stagnation_supervision_runtime_v2.launch import run
        from research.stagnation_supervision_runtime_v2.target_evaluate import evaluate_target
        import time
        for fault, completes in (('transport', False), ('model_startup', False), ('monitor_exit', False),
                                 ('storage', False), ('surviving_child', True), ('reflection_invalid', True)):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory(prefix='ssv-rt2-fault-') as tmp:
                work = Path(tmp)
                games = restore_game_mount(work / 'games')
                env = {'SSV_REHEARSAL': '1', 'CUDA_VISIBLE_DEVICES': '', 'SSV_REHEARSAL_GAMES': str(games),
                       'SSV_REHEARSAL_GROUPS': 'b1-ar25', 'SSV_REHEARSAL_ACTIONS': '12'}
                with mock.patch.dict(os.environ, env):
                    receipt = run(work / 'working/out', work / 'working', started=time.monotonic(), mode='rehearsal',
                                  internal_seconds=1500, session='1', fault=fault)
                    spec = B.session_run_spec('1', 'rehearsal')
                evaluation = evaluate_target(work / 'working/out', spec, mode='rehearsal', session='1', internal_seconds=1500)
                outer = json.loads((work / 'working/out/control/outer.json').read_bytes())
                self.assertEqual(outer['fault'], fault)
                self.assertTrue(receipt['first_cell_cleanup_verified'], receipt.get('error'))
                self.assertTrue(outer['process_groups_exited'] and outer['independent_gpu_cleanup_verified'])
                self.assertTrue(outer['scratch_removed'])
                done = receipt['study_status'] == 'study_complete_pending_independent_evaluation'
                self.assertEqual(done, completes, receipt)
                self.assertEqual(evaluation['technically_complete'], completes, evaluation['problems'][:3])


if __name__ == '__main__':
    unittest.main()
