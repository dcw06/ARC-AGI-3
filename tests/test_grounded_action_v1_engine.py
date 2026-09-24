"""Archive-backed CPU development integration, never a model/GPU test."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from research.grounded_action_v1.replay import evaluate
from scripts.replay_grounded_action_v1_archive import run as replay_archive
from scripts.inspect_phase4_perception_stage_a_v1 import decoded_rgb_identity
from scripts.review_grounded_action_v1_notebook import review as review_notebook
from scripts.review_grounded_action_v1_launch_notebook import review as review_launch_notebook

ROOT = Path(__file__).resolve().parents[1]


class GroundedActionEngineTests(unittest.TestCase):
    def test_committed_cpu_archive_replays_and_rejects_journal_tamper(self):
        import zipfile
        result = replay_archive()
        self.assertEqual((result['calls'], result['dispatches'], result['level_deltas']), (12, 4, [0, 0]))
        with zipfile.ZipFile(ROOT / 'evidence/perception-stage-b-v1-local-engine.zip') as bundle:
            record = json.loads(bundle.read('run.json'))
        record['episodes'][0]['steps'][0]['receipt']['journal']['prepared_fields']['action_id'] = 7
        with self.assertRaisesRegex(ValueError, 'journal'):
            evaluate(record)
        with zipfile.ZipFile(ROOT / 'evidence/perception-stage-b-v1-local-engine.zip') as bundle:
            record = json.loads(bundle.read('run.json'))
        record['episodes'][0]['cleanup']['scorecard_receipt']['total_actions'] = 99
        with self.assertRaisesRegex(ValueError, 'scorecard totals'):
            evaluate(record)

    def test_reencoded_png_with_equal_rgb_is_accepted_as_visual_identity(self):
        from PIL import Image
        import io
        raw = (ROOT / 'reports/perception_stage_a_v1/P1_text.png').read_bytes()
        with Image.open(io.BytesIO(raw)) as image:
            out = io.BytesIO()
            image.save(out, format='PNG', compress_level=9)
        self.assertEqual(decoded_rgb_identity(raw), decoded_rgb_identity(out.getvalue()))

    def test_gpu_disabled_notebook_unpacks_and_rejects_tampering(self):
        from shutil import copyfile
        source = ROOT / 'notebooks/phase4-grounded-action-v1-review-r5'
        self.assertEqual(review_notebook(source, compare_checkout=False)['status'],
                         'review_snapshot_verified_no_launch_authority')
        for revision in ('r1', 'r2', 'r3', 'r4', 'r5'):
            historical = ROOT / ('notebooks/phase4-grounded-action-v1-review-' + revision)
            self.assertEqual(review_notebook(historical, compare_checkout=False)['status'],
                             'review_snapshot_verified_no_launch_authority')
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            for name in ('profile.ipynb', 'kernel-metadata.json', 'review-source-lock.json'):
                copyfile(source / name, target / name)
            metadata = json.loads((target / 'kernel-metadata.json').read_bytes())
            metadata['enable_gpu'] = True
            (target / 'kernel-metadata.json').write_text(json.dumps(metadata))
            with self.assertRaises(ValueError):
                review_notebook(target, compare_checkout=False)

    def test_target_launch_review_unpacks_and_rejects_unapproved_execution(self):
        from research.grounded_action_v1.authority import REVIEW, REQUIRED_SOURCE
        source = ROOT / 'notebooks/phase4-grounded-action-v1-launch-r9'
        self.assertEqual((ROOT / REVIEW).resolve(),
                         (source / 'review-source-lock.json').resolve())
        result = review_launch_notebook(source)
        self.assertTrue(result['unapproved_execution_rejected'])
        for revision in ('r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7', 'r8'):
            historical = ROOT / ('notebooks/phase4-grounded-action-v1-launch-' + revision)
            self.assertTrue(review_launch_notebook(historical, compare_checkout=False)
                            ['unapproved_execution_rejected'])
        lock = json.loads((source / 'review-source-lock.json').read_bytes())
        self.assertTrue(REQUIRED_SOURCE <= set(lock['bindings']))
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            for name in ('profile.ipynb', 'kernel-metadata.json', 'review-source-lock.json'):
                (target / name).write_bytes((source / name).read_bytes())
            metadata = json.loads((target / 'kernel-metadata.json').read_bytes())
            metadata['enable_gpu'] = True
            (target / 'kernel-metadata.json').write_text(json.dumps(metadata))
            with self.assertRaises(ValueError):
                review_launch_notebook(target)

    @unittest.skipUnless(os.name == 'posix' and importlib.util.find_spec('arc_agi'),
                         'requires Linux CPU development engine')
    def test_archive_restoration_produces_isolated_equal_starts(self):
        from research.grounded_action_v1.engine import DevelopmentAdapter, restore_game_mount, verified_game_mount
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = restore_game_mount(root / 'restored')
            games = verified_game_mount(source, root / 'staged')
            adapters = [DevelopmentAdapter(arm, games, root / 'recordings') for arm in ('control', 'target')]
            try:
                observations = [adapter.bootstrap() for adapter in adapters]
                self.assertEqual(observations[0].canonical_hash, observations[1].canonical_hash)
                self.assertTrue(all(o.full_reset for o in observations))
                self.assertNotEqual(adapters[0].card, adapters[1].card)
            finally:
                receipts = [adapter.close() for adapter in adapters]
            self.assertTrue(all(r['closed'] for r in receipts))

    @unittest.skipUnless(os.name == 'posix' and importlib.util.find_spec('arc_agi'),
                         'requires Linux CPU development engine')
    def test_external_monitor_failure_kills_worker_and_removes_games(self):
        from scripts.run_grounded_action_v1_engine_local import supervise
        with tempfile.TemporaryDirectory() as folder:
            monitor = supervise(Path(folder) / 'limited.json', seconds=90, evidence_limit=65536)
            self.assertEqual(monitor['status'], 'failed')
            self.assertIn('evidence limit', monitor['error'])
            self.assertTrue(monitor['temporary_games_removed'])
            self.assertTrue(monitor['process_group_exited'])

    @unittest.skipUnless(os.name == 'posix', 'POSIX process groups required')
    def test_cleanup_kills_descendant_after_leader_exits(self):
        from scripts.run_grounded_action_v1_engine_local import group_exited, terminate_group
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / 'descendant-ready'
            code = (
                'import os,signal,sys,time,pathlib\n'
                'if os.fork(): sys.exit(0)\n'
                'signal.signal(signal.SIGTERM,signal.SIG_IGN)\n'
                'pathlib.Path(sys.argv[1]).write_text(str(os.getpid()))\n'
                'while True: time.sleep(1)\n'
            )
            process = subprocess.Popen([sys.executable, '-c', code, str(marker)], start_new_session=True,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                process.wait(timeout=5)
                limit = time.monotonic() + 5
                while not marker.exists() and time.monotonic() < limit:
                    time.sleep(.02)
                self.assertTrue(marker.exists(), 'descendant did not start')
                self.assertFalse(group_exited(process.pid), 'descendant must survive leader')
                self.assertTrue(terminate_group(process, grace=.2, verification_seconds=2))
                self.assertTrue(group_exited(process.pid))
            finally:
                if not group_exited(process.pid):
                    os.killpg(process.pid, 9)


if __name__ == '__main__':
    unittest.main()
