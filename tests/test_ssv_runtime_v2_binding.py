"""Track 3 runtime v2: derivation, runtime bindings, unchanged science, historical preservation and payload closure.
CPU only; no provider, model or GPU."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from research.stagnation_supervision_runtime_v2 import authority as A, closure as C, model_binding as M
from scripts import derive_stagnation_supervision_runtime_v2 as DERIVE

ROOT = A.ROOT
PROTOCOL = json.loads((ROOT / A.PROTOCOL).read_bytes())
RECORD = json.loads((ROOT / 'research/stagnation_supervision_runtime_v2/derivation.json').read_bytes())
R4 = json.loads((ROOT / 'notebooks/stagnation-supervision-v1-review-r4/review-source-lock.json').read_bytes())


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Derivation(unittest.TestCase):
    def test_every_derived_file_inverts_exactly_to_its_recorded_source(self):
        self.assertEqual(len(RECORD['files']), 14)
        for row in RECORD['files']:
            with self.subTest(row['derived']):
                data = (ROOT / row['derived']).read_bytes()
                self.assertEqual(sha(data), row['derived_sha256'])
                self.assertTrue(DERIVE.inverse_check(data, row))

    def test_track3_sources_rederive_byte_for_byte_from_the_local_tree(self):
        for name, (path, replacements) in DERIVE.TRACK3.items():
            with self.subTest(name):
                source = (ROOT / path).read_bytes()
                row = next(r for r in RECORD['files'] if r['derived'].endswith('/' + name))
                self.assertEqual(sha(source), row['source_sha256'])
                header = DERIVE.HEADER.format(path=path, commit=DERIVE.TRACK3_COMMIT[:7]).encode()
                self.assertEqual(header + DERIVE.apply(source, replacements), (ROOT / row['derived']).read_bytes())

    def test_reference_sources_are_the_verified_runtime_commit(self):
        self.assertEqual(RECORD['reference']['commit'], '5a21dd339d22ec6e13307722b42dcef0882f6829')
        rows = [r for r in RECORD['files'] if r['source_branch'] == 'wheelhouse-replacement-audit']
        self.assertEqual({r['source_path'].split('/')[1] for r in rows}, {'direct_publisher_smoke_v1'})
        data = [r for r in rows if r['kind'] == 'data']
        self.assertEqual({Path(r['derived']).name for r in data},
                         {'proposal.json', 'trusted_manifest.json', 'trusted_requirements.lock'})
        lock = ROOT / 'research/stagnation_supervision_runtime_v2/trusted_requirements.lock'
        self.assertEqual(sha(lock.read_bytes()), PROTOCOL['bundle']['requirements_lock_sha256'])

    def test_derived_lifecycle_modules_only_rebind_runtime_paths(self):
        allowed = re.compile(r'(stagnation_supervision_runtime_v2|stagnation_supervision_v1\.closed_loop|parents\[2\]|'
                             r'model_binding|bind_primary|mounts|staged_inputs|install_seconds|installation|'
                             r'runtime_binding|stagnation-supervision-v1-runtime-v2|SESSION_LIMITS|'
                             r'target_evaluation_runtime_v2|dependency_trees_removed|notebook interpreter|'
                             r'rehearsal-only|SSV_RUNTIME_V2|runtime v2|LIVE_INTERNAL_SECONDS|import prepare)')
        for row in RECORD['files']:
            for old, new, _ in row['replacements']:
                with self.subTest(row['derived'], old=old[:60]):
                    self.assertRegex(new, allowed)


class Protocol(unittest.TestCase):
    def test_placeholders_are_exactly_the_private_bindings(self):
        self.assertEqual(sorted(A.unresolved(PROTOCOL)),
                         ['kernel_ids.1', 'kernel_ids.2', 'model.kaggle_source', 'model.mounted_path'])
        self.assertEqual(PROTOCOL['model']['kaggle_source'], 'REPLACE_WITH_MODEL_OWNER/REPLACE_WITH_MODEL_DATASET/1')
        self.assertEqual(PROTOCOL['model']['mounted_path'], 'REPLACE_WITH_VERIFIED_MODEL_MOUNT')

    def test_verified_runtime_bindings(self):
        self.assertEqual(PROTOCOL['dataset']['ref'], 'driessmit1/arc3-vllm-h100-wheelhouse-v3')
        self.assertIs(type(PROTOCOL['dataset']['version']), int)
        self.assertEqual(PROTOCOL['dataset']['version'], 1)
        self.assertEqual(PROTOCOL['bundle'], {'approved_manifest_sha256': '3691cb8854df4d8ff10e42ca9957fddb9a8ae0362064e7b31b3205891af0d546',
                                              'requirements_lock_sha256': 'ba80d35062245421daf1cae65474281952cc0c44fb46e11cf7f68d0ece496406',
                                              'wheel_count': 174})
        self.assertRegex(PROTOCOL['kaggle_image']['docker_image'], r'^gcr\.io/kaggle-private-byod/python@sha256:[0-9a-f]{64}$')
        self.assertEqual(PROTOCOL['kaggle_image']['docker_image_pinning_type'], 'original')
        self.assertEqual(PROTOCOL['runtime']['python'], '3.12')
        self.assertEqual(PROTOCOL['runtime']['model']['packages'],
                         {'numpy': '2.2.6', 'torch': '2.10.0', 'transformers': '4.57.6', 'vllm': '0.19.0'})
        self.assertEqual(PROTOCOL['machine_shape'], 'NvidiaRtxPro6000')
        self.assertEqual(PROTOCOL['competition']['ref'], 'arc-prize-2026-arc-agi-3')
        self.assertIn('ssv1-r5-session1-reservation-001', PROTOCOL['consumed_attempts'])

    def test_model_snapshot_inventory_reproduces_the_pinned_tree_and_keeps_the_frozen_tokenizer(self):
        self.assertEqual(M.expected_artifact(ROOT), {'tree_sha256': 'b480ad92cda91474084c795d2ff64b07a6c477909b22d2784d24abf8fb4ef7df',
                                                      'file_count': 20, 'bytes': 32268935715})
        files = {r['path']: r for r in PROTOCOL['model']['files']}
        tokenizer = json.loads((ROOT / 'certification/phase4_integrated_v2/tokenizer_manifest.json').read_bytes())
        for name, info in tokenizer['files'].items():
            self.assertEqual((files[name]['sha256'], files[name]['bytes']), (info['sha256'], info['bytes']))
        primary = json.loads((ROOT / 'config/operational_primary.yaml').read_bytes())['primary']
        self.assertEqual(primary['model_binding']['revision'], PROTOCOL['model']['revision'])
        self.assertNotEqual(primary['model_artifact']['tree_sha256'], PROTOCOL['model']['tree_sha256'])  # container changed

    def test_effective_server_command_equals_the_verified_runtime(self):
        spec = json.loads((ROOT / 'config/m0_launch_spec_q3vl30.json').read_bytes())
        from research.stagnation_supervision_v1.closed_loop.server_config import cache_disabled_argv
        self.assertEqual(cache_disabled_argv(spec['argv']), PROTOCOL['server']['argv'])
        self.assertEqual(spec['env'], PROTOCOL['server']['env'])

    def test_frozen_r4_lifecycle_limits_are_kept(self):
        self.assertEqual(PROTOCOL['limits']['installation_seconds'], 450)
        self.assertEqual(PROTOCOL['limits']['model_startup_ceiling_seconds'], 900)
        from research.stagnation_supervision_runtime_v2.supervisor import LIVE_INTERNAL_SECONDS
        self.assertEqual(LIVE_INTERNAL_SECONDS, {s: v['internal_seconds'] for s, v in A.SESSION_LIMITS.items()})
        self.assertEqual({s: v['authorized_seconds'] for s, v in A.SESSION_LIMITS.items()}, {'1': 5400, '2': 4800})


class Science(unittest.TestCase):
    def test_bound_science_files_are_unchanged(self):
        protocol = A.load_protocol(ROOT)  # raises on any drift
        for name, digest in protocol['science']['files'].items():
            self.assertEqual(sha((ROOT / name).read_bytes()), digest)
        for name in ('research/stagnation_supervision_v1/trigger_spec.json',
                     'research/stagnation_supervision_v1/closed_loop/protocol.json'):
            self.assertIn(name, protocol['science']['files'])

    def test_every_shared_payload_file_is_byte_identical_to_r4(self):
        files = C.closure(ROOT)['files']
        shared = [n for n in files if n in R4['bindings']]
        self.assertGreater(len(shared), 100)
        drift = [n for n in shared if sha((ROOT / n).read_bytes()) != R4['bindings'][n]]
        self.assertEqual(drift, [])
        new = sorted(n for n in files if n not in R4['bindings'])
        self.assertTrue(all(n.startswith('research/stagnation_supervision_runtime_v2/') or n in (
            'certification/phase4_integrated_v2/protocol.json', 'reports/stagnation_supervision_v1_ls20_decision.json',
            'reports/stagnation_supervision_v1_protocol_v2.md', 'reports/stagnation_supervision_v1_token_audit.json',
            # archive locks named by the frozen replay script that the frozen evaluator loads
            'reports/action_effect_history_v1_archive.json', 'reports/perception_stage_b_r8_archive.json',
            'reports/ws3_transition_replay_v1.json')
                            for n in new), new)

    def test_frozen_study_configuration_is_reconfirmed(self):
        study = json.loads((ROOT / 'research/stagnation_supervision_v1/closed_loop/protocol.json').read_bytes())
        self.assertEqual([c['game_id'] for c in study['cases']],
                         ['ar25-0c556536', 'wa30-ee6fef47', 'ls20-9607627b', 's5i5-18d95033'])
        self.assertEqual(study['arms'], ['continuation', 'periodic', 'triggered'])
        self.assertEqual(study['limits']['actions_per_episode'], 40)
        self.assertNotIn('restart', json.dumps(study['stop_reasons']))
        trigger = json.loads((ROOT / 'research/stagnation_supervision_v1/trigger_spec.json').read_bytes())
        self.assertEqual({k: v for k, v in trigger['params'].items() if v is not None},
                         {'state_action_recurrence': 2, 'tiny_effect_repeat': 10})


class Preservation(unittest.TestCase):
    def test_every_historical_track3_file_is_byte_identical_to_the_base_commit(self):
        record = json.loads((ROOT / 'reports/stagnation_supervision_runtime_v2_historical_preservation.json').read_bytes())
        self.assertEqual(record['base_commit'], 'bc19919dace8dd919bf5617174534526783c159d')
        self.assertGreaterEqual(len(record['files']), 200)
        for required in ('reports/stagnation_supervision_v1_r5_session1_authority/submission-claim.json',
                         'reports/stagnation_supervision_v1_r5_session1_authority/quota-after-cancellation.json',
                         'notebooks/stagnation-supervision-v1-r6-session1-launch/profile.ipynb',
                         'notebooks/stagnation-supervision-v1-preparation-r7/review-source-lock.json',
                         'research/stagnation_supervision_v1/trigger_spec.json'):
            self.assertIn(required, record['files'])
        changed = [n for n, d in record['files'].items() if sha((ROOT / n).read_bytes()) != d]
        self.assertEqual(changed, [])

    def test_no_successor_file_lives_where_historical_inventories_glob(self):
        for directory in ('agent', 'certification', 'evaluation', 'research/stagnation_supervision_v1',
                          'research/transition_evidence_v1', 'research/transition_evidence_v2',
                          'research/action_effect_history_v1', 'research/action_effect_v1', 'research/grounded_action_v1'):
            self.assertFalse(any('runtime_v2' in p.name for p in (ROOT / directory).rglob('*')), directory)
        self.assertFalse(list((ROOT / 'tests').glob('test_stagnation_supervision_v1*runtime*')))


class Closure(unittest.TestCase):
    def test_static_closure_is_complete_and_excludes_other_scopes(self):
        value = C.closure(ROOT)
        self.assertEqual(value['unresolved_project_imports'], [])
        self.assertEqual(value['missing_data'], [])
        self.assertTrue(A.REQUIRED_SOURCE <= set(value['files']))
        self.assertFalse(set(C.EXCLUDED) & set(value['files']))
        self.assertTrue(set(value['third_party']) <= {'arc_agi', 'arcengine', 'matplotlib', 'numpy', 'requests',
                                                      'transformers', 'urllib3'})
        science = json.loads((ROOT / A.PROTOCOL).read_bytes())['science']['files']
        self.assertTrue(set(science) <= set(value['files']))  # the gate re-hashes them in the extracted source
        self.assertFalse(any('approval' in n or 'claim' in n or 'reservation' in n for n in value['files']))
        for name in value['code']:
            compile((ROOT / name).read_bytes(), name, 'exec')

    def test_notebook_interpreter_closure_has_no_game_or_model_package(self):
        code = '''import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('arcengine', 'arc_agi', 'numpy', 'torch', 'vllm', 'transformers', 'requests', 'pydantic'):
            raise ModuleNotFoundError('not in the notebook image: ' + fullname)
sys.meta_path.insert(0, Block())
sys.path.insert(0, sys.argv[1])
import research.stagnation_supervision_runtime_v2.launch as L, research.stagnation_supervision_runtime_v2.prepare
import research.stagnation_supervision_runtime_v2.mounts, research.stagnation_supervision_runtime_v2.authority as A
import certification.phase4_integrated_v2.game_assets, certification.phase4_integrated_v2.dependencies
try:
    L.run(__import__('pathlib').Path(sys.argv[2]) / 'out', __import__('pathlib').Path(sys.argv[2]), started=__import__('time').monotonic(), mode='live', session='1')
except A.LiveRefused as exc:
    print('refused')
'''
        with tempfile.TemporaryDirectory() as tmp:
            value = subprocess.run([sys.executable, '-I', '-c', code, str(ROOT), tmp], capture_output=True, text=True,
                                   timeout=60)
            self.assertEqual(value.returncode, 0, value.stderr[-1500:])
            self.assertEqual(value.stdout.strip(), 'refused')
            self.assertFalse((Path(tmp) / 'out').exists())

    def test_model_host_closure_has_no_game_package(self):
        code = '''import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('arcengine', 'arc_agi'):
            raise ModuleNotFoundError('game dependency prohibited: ' + fullname)
sys.meta_path.insert(0, Block())
sys.path.insert(0, sys.argv[1])
import research.stagnation_supervision_runtime_v2.host, research.stagnation_supervision_runtime_v2.model_binding
'''
        value = subprocess.run([sys.executable, '-I', '-c', code, str(ROOT)], capture_output=True, text=True, timeout=60)
        self.assertEqual(value.returncode, 0, value.stderr[-1500:])


if __name__ == '__main__':
    unittest.main()
