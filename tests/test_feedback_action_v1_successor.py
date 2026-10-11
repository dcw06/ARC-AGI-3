"""Feedback-action v1 successor runtime v1: runtime binding, derivations, import closure, owner gates, the live gate
and the review snapshot (CPU only; no model, no GPU, no provider)."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

from research.feedback_action_v1 import adapter as AD, derive, derive_runtime as DR
from research.feedback_action_v1.live import binding as B, notebook as N, owner_gates as G, policy as P, runtime as RT

ROOT = Path(__file__).resolve().parents[1]
# The experiment's science files, byte for byte as at the track head 687acc8: the successor changes runtime only.
SCIENCE = {'research/feedback_action_v1/adapter.py': '26a84909f6786dce8e9e66d5a509a3eac75537a68fdfa416d927431fd5a84f5d',
           'research/feedback_action_v1/evidence.py': '8d095ba78c716a7bf33bea8e3dee719ed745eb74a51fddf413a45eb57c241698',
           'research/feedback_action_v1/evaluate.py': '019c18044a1606eb915f19d3c93dc6d71488bd22a013f6c6fac583aeee0eb719',
           'research/feedback_action_v1/live/protocol.json':
               'd5c244faa25e92ce0f0d3eb132f19eb0a661a1ee9f76edbab85ebbb614e991f4',
           'research/feedback_action_v1/live/fake_server.py':
               'd80eb516f43e528d29d4474fd8b49a7264f8579518a0964c9ee0dea00d80b8a0'}
VERIFIED_PROTOCOL_BLOB = '6061cbebb3f21ccd3ca698049f439b0546968f2f'  # control-interface v2 protocol.json at 5a21dd3
REVIEW = ROOT / 'notebooks/feedback-action-v1-review-r7'  # six-gap lifecycle and independent replay repair
RETAINED_REVIEW_LOCKS = {1: '4b5b7a0648c968c2ec497e0ba963e2cee42ad4f87c0ec6c204efbd0d7bedf0b5',  # history, unchanged
                         2: '9ebbc968f91e5f10b0627a617254ab7c52bb38954021e10b631d77244dd06468',
                         3: '180c33ee895b5af2aca4032b8d5f9f878dbaa57fabdb32a1e1e5b612ed2f415d',
                         4: 'f0a5ad977b95d66fac91d0ddc482f3c02afe0b44bc3d8e954260796908817090',
                         5: 'a32893cb63be0381e835770ac600f03e8760c94b1094f9dc52ed9eaba6e7c98d',
                         6: '97ec8e1cb1bd898baa16761f22aef20e90ce95b5d31f21d47e4c71eee3d1768a'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_blob(blob):
    try:
        return subprocess.run(['git', 'cat-file', 'blob', blob], cwd=ROOT, capture_output=True, check=True,
                              timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return None


class ScienceUnchanged(unittest.TestCase):
    def test_prompts_arms_schemas_schedule_scoring_are_byte_identical(self):
        for name, digest in SCIENCE.items():
            self.assertEqual(sha(ROOT / name), digest, name)

    def test_recorded_owner_gates_change_exactly_the_candidate_schema_and_f5(self):
        # Owner decisions of October 10, 2026, frozen in reports/feedback_action_v1_protocol_v2_frozen.md.
        gates = G.load()
        self.assertEqual((gates['free_text_format']['decision'], gates['f5_early_abort']['decision']),
                         ('ascii_only', 'denominator_floor_10'))
        self.assertEqual(gates['owner_response']['freeze'], 'Yes, freeze with the fix (Recommended)')
        for legal in ([6], [1, 2, 3, 4], [1, 2, 3, 4, 6, 7]):
            gated = G.candidate_response_format(legal)['json_schema']['schema']
            committed = AD.candidate_response_format(legal)['json_schema']['schema']
            for name in G.FREE_TEXT:  # the only difference: the pattern on the two free-text fields
                field = gated['properties']['hypothesis_test']['properties'][name]
                self.assertEqual(field.pop('pattern'), G.ASCII_PATTERN)
            self.assertEqual(gated, committed)
        spec = P.session_spec(1)
        self.assertEqual(spec['limits']['session_abort']['dispatch_denominator_floor'], 10)
        baseline = AD.build_request({'legal_actions': [1, 2]}, {}, 'baseline')
        self.assertIs(G.gate_request(baseline), baseline)  # the baseline is unchanged


class RuntimeBinding(unittest.TestCase):
    def setUp(self):
        self.runtime = RT.load(ROOT)

    def test_bound_to_the_verified_runtime(self):
        data = git_blob(VERIFIED_PROTOCOL_BLOB)
        if data is None:
            self.skipTest('the verified runtime protocol object is not in this clone')
        self.assertEqual(hashlib.sha256(data).hexdigest(), self.runtime['verified_runtime_source']['protocol_sha256'])
        verified = json.loads(data)
        for key in ('dataset', 'bundle', 'kaggle_image', 'runtime', 'sampling'):
            self.assertEqual(self.runtime[key], verified[key], key)
        self.assertEqual(self.runtime['competition']['ref'], verified['competition']['ref'])
        model = {k: v for k, v in verified['model'].items()}
        self.assertEqual(self.runtime['model'], model)  # placeholders exactly as the reference package keeps them
        for key in ('argv', 'env', 'host', 'port', 'kill_grace_seconds', 'terminate_grace_seconds', 'log_retained_bytes',
                    'served_model_name'):
            self.assertEqual(self.runtime['server'][key], verified['server'][key], key)

    def test_private_bindings_stay_placeholders(self):
        self.assertEqual(RT.unresolved(self.runtime), ['kernel_id', 'model.kaggle_source', 'model.mounted_path'])

    def test_prefix_caching_disabled_exactly_once(self):
        argv = self.runtime['server']['argv']
        self.assertEqual((argv.count('--no-enable-prefix-caching'), argv.count('--enable-prefix-caching')), (1, 0))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in (RT.RUNTIME, self.runtime['game']['manifest'], self.runtime['game']['requirements'],
                         'certification/direct_publisher_smoke_v1/preflight.py'):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, root / name)
            bad = copy.deepcopy(self.runtime)
            bad['server']['argv'][bad['server']['argv'].index('--no-enable-prefix-caching')] = '--enable-prefix-caching'
            (root / RT.RUNTIME).write_text(json.dumps(bad))
            with self.assertRaises(RT.RuntimeBindingError):
                RT.load(root)

    def test_installation_never_inherits_the_notebook_matplotlib_backend(self):
        # Session 1, attempt 1 (October 11, 2026): Kaggle's MPLBACKEND reached the game interpreter's package checks.
        from unittest import mock
        seen = []

        def fake_install(bundle, venv, runtime, deadline, log, python=None, environment=None, requirements=None,
                         processes=None):
            seen.append(dict(environment or {}))
            return {'passed': True, 'python': str(venv / 'bin' / 'python')}
        kaggle = {'MPLBACKEND': 'module://matplotlib_inline.backend_inline'}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict('os.environ', kaggle), \
                mock.patch('certification.direct_publisher_smoke_v1.install.install', fake_install), \
                mock.patch('certification.direct_publisher_smoke_v1.install.verify_bundle', lambda *a, **k: {}), \
                mock.patch.object(RT, 'verify_game_wheels', lambda *a, **k: {}), \
                mock.patch.object(RT, 'import_check', lambda *a, **k: {}):
            RT.prepare(ROOT, Path(tmp), Path(tmp) / 'bundle', Path(tmp) / 'competition', time.monotonic() + 60, None)
        self.assertEqual(len(seen), 2)  # the model and the game interpreter
        self.assertEqual([e['MPLBACKEND'] for e in seen], ['Agg', 'Agg'])

    def test_game_lock_is_exactly_the_frozen_competition_wheels(self):
        pins = RT.game_lock(ROOT, self.runtime)
        self.assertEqual(len(pins), 31)
        self.assertEqual({n: v for n, (v, _) in pins.items() if n in ('arc-agi', 'arcengine', 'numpy', 'pydantic',
                                                                      'requests', 'python-dotenv')},
                         {'arc-agi': '0.9.8', 'arcengine': '0.9.3', 'numpy': '2.4.4', 'pydantic': '2.13.2',
                          'requests': '2.33.1', 'python-dotenv': '1.2.2'})

    def test_competition_mount_layouts(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with self.assertRaises(RT.RuntimeBindingError):
                RT.competition_mount('arc-prize-2026-arc-agi-3', base)
            (base / 'competitions/arc-prize-2026-arc-agi-3').mkdir(parents=True)
            self.assertEqual(RT.competition_mount('arc-prize-2026-arc-agi-3', base).name, 'arc-prize-2026-arc-agi-3')
            (base / 'arc-prize-2026-arc-agi-3').mkdir()
            with self.assertRaises(RT.RuntimeBindingError):  # two real directories: ambiguous
                RT.competition_mount('arc-prize-2026-arc-agi-3', base)

    def test_server_log_must_confirm_prefix_caching_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'server.log'
            log.write_text("non-default args: {'enable_prefix_caching': False, 'max_model_len': 65536}\n")
            self.assertTrue(RT.verify_cache_disabled(log)['disabled'])
            log.write_text("non-default args: {'enable_prefix_caching': True}\n")
            with self.assertRaises(ValueError):
                RT.verify_cache_disabled(log)
            log.write_text('no configuration line\n')
            with self.assertRaises(ValueError):
                RT.verify_cache_disabled(log)

    def test_lifecycle_agrees_with_the_experiment_protocol(self):
        protocol = B.load_protocol(ROOT)
        frozen = json.loads((ROOT / 'research/feedback_action_v1/live/protocol.json').read_bytes())['limits']
        self.assertEqual((protocol['limits']['internal_seconds'], protocol['limits']['cleanup_reserve_seconds'],
                          protocol['limits']['pair_admission_seconds'], protocol['limits']['maximum_policy_calls'],
                          protocol['limits']['authorized_seconds']),
                         (frozen['internal_seconds'], frozen['cleanup_reserve_seconds'],
                          frozen['pair_admission_seconds'], frozen['maximum_policy_calls'],
                          frozen['provider_timeout_seconds']))


class Derivations(unittest.TestCase):
    def test_harness_derived_from_action_effect_history_v1(self):
        self.assertEqual(derive.stale(), [])

    def test_gate_notebook_launch_derived_from_the_verified_runtime(self):
        try:
            self.assertEqual(DR.stale(), [])
        except DR.SourceUnavailable as exc:
            self.skipTest(str(exc))

    def test_verified_controller_files_are_byte_identical(self):
        self.assertEqual(DR.verbatim_problems(), [])
        record = json.loads((ROOT / 'research/feedback_action_v1/live/derivation.json').read_bytes())
        self.assertEqual(record['verified_runtime']['gpu_run_review_lock_sha256'], DR.GPU_RUN_REVIEW_LOCK)
        self.assertEqual(set(record['verbatim']), set(DR.VERBATIM))

    def test_outdated_bindings_are_gone_from_the_live_path(self):
        names, _ = RT.closure(sum(RT.ENTRIES.values(), []), ROOT)
        live = [n for n in names if n.startswith(('research/feedback_action_v1/', 'scripts/feedback_action_v1'))]
        outdated = ('phase4_integrated_v2.prepare', 'target_install_probe_r5', 'operational_primary',
                    'artifact_contract', '--enable-prefix-caching', 'MODEL_CHECK', 'arc3-vllm-h100-wheelhouse-v3',
                    '/kaggle/input/models/', 'verify_wheelhouses', '< 450')
        for name in live:
            text = (ROOT / name).read_text(encoding='utf-8')
            for token in outdated:
                if token == '--enable-prefix-caching' and name.endswith('runtime.py'):
                    continue  # the runtime module names the flag only to refuse it
                self.assertNotIn(token, text, f'{name}: {token}')


class ImportClosure(unittest.TestCase):
    def test_first_cell_is_standard_library_only(self):
        self.assertEqual(RT.closure(RT.ENTRIES['first_cell'], ROOT, lazy=False)[1], [])

    def test_interpreters_never_import_the_other_side(self):
        self.assertFalse({'torch', 'vllm', 'transformers', 'xgrammar'} & set(RT.role_modules('game')))
        self.assertFalse({'arc_agi', 'arcengine'} & set(RT.role_modules('model')))

    def test_every_embedded_file_exists_and_is_regular(self):
        names = N.source_names(ROOT)
        self.assertTrue(set(RT.DATA_FILES) <= set(names))
        for name in names:
            self.assertTrue((ROOT / name).is_file() and not (ROOT / name).is_symlink(), name)

    def test_first_cell_modules_import_here(self):
        if sys.platform != 'linux':
            self.skipTest('the runtime (process groups, fcntl, prctl) is Linux-only')
        code = 'import importlib,sys,json\nfor m in json.loads(sys.argv[1]): importlib.import_module(m)\nprint("ok")'
        result = subprocess.run([sys.executable, '-c', code, json.dumps(RT.role_modules('first_cell'))], cwd=ROOT,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.stdout.strip(), 'ok', result.stderr[-800:])


class OwnerGateOptions(unittest.TestCase):
    """Both options of each gate, built from explicit records (the owner recorded the recommended ones)."""

    def recorded(self, free_text=None, f5=None):
        gates = copy.deepcopy(G.load())
        gates['free_text_format']['decision'], gates['f5_early_abort']['decision'] = free_text, f5
        return gates

    def test_ascii_only_schema_keeps_the_bound_inside_the_pattern(self):
        gates = self.recorded(free_text='ascii_only')
        schema = G.candidate_response_format([1, 6], gates)['json_schema']['schema']
        for name in G.FREE_TEXT:
            field = schema['properties']['hypothesis_test']['properties'][name]
            self.assertEqual((field['pattern'], field['maxLength']), ('^[ !#-\\[\\]-~]{0,240}$', 240))
        block = {'hypothesis': 'ok', 'if_different': 'café'}
        self.assertIn('if_different', G.free_text_problem(block, gates))
        self.assertIsNone(G.free_text_problem({'hypothesis': 'a ~ b', 'if_different': 'x'}, gates))
        self.assertIsNone(G.free_text_problem(block, self.recorded()))  # the committed option: no check
        self.assertIn('if_different', G.free_text_problem(block))  # the recorded decision: checked

    def test_f5_floor_option(self):
        self.assertEqual(G.dispatch_denominator_floor(self.recorded()), 0)  # the committed rule
        self.assertEqual(G.dispatch_denominator_floor(), 10)  # the recorded decision
        gates = self.recorded(f5='denominator_floor_10')
        from research.feedback_action_v1.live import runner as RN
        spec = G.apply(RN.protocol(), gates)
        self.assertEqual(spec['limits']['session_abort']['dispatch_denominator_floor'], 10)
        self.assertNotIn('dispatch_denominator_floor', RN.protocol()['limits']['session_abort'])  # copy, not edit

    def test_invalid_decision_values_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            gates = self.recorded()
            gates['f5_early_abort']['decision'] = 'something_else'
            path = Path(tmp) / 'owner_gates.json'
            path.write_text(json.dumps(gates))
            with self.assertRaises(ValueError):
                G.load(path)


class LiveGate(unittest.TestCase):
    def test_live_path_refuses_in_this_checkout(self):
        with self.assertRaises(B.LiveRefused) as caught:
            B.require_live(ROOT)
        reasons = ' '.join(caught.exception.reasons)
        self.assertIn('unresolved placeholders: kernel_id, model.kaggle_source, model.mounted_path', reasons)
        self.assertIn('authorization', reasons)
        from research.feedback_action_v1.live import authority
        with self.assertRaises(PermissionError):
            authority.require(ROOT)

    def test_launch_tooling_refuses_and_writes_nothing(self):
        from research.feedback_action_v1.live import launch
        with self.assertRaises(B.LiveRefused):
            N.launch_artifacts(ROOT)
        with self.assertRaises((B.LiveRefused, launch.LaunchRefused, PermissionError)):
            launch.claim(ROOT)
        for name in (B.CLAIM, B.RECEIPT, B.SOURCE, B.COMPUTE, B.EXECUTION, B.RESERVATION):
            self.assertFalse((ROOT / name).exists(), name)

    def test_no_approval_authorization_or_reservation_record_exists(self):
        for name in (B.SOURCE, B.COMPUTE, B.EXECUTION, B.RESERVATION, B.CLAIM, B.RECEIPT, B.ACCOUNT, B.PERMISSION,
                     B.BYTES):
            self.assertFalse((ROOT / name).exists(), name)

    def test_session_two_requires_an_evaluated_permitting_session_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evaluation = {'mode': 'live', 'attempt_id': 'fa1-session1-fixture', 'evaluation': {
                'session': 1, 'session_2_permitted': True}}
            path = root / 'reports/feedback_action_v1/session1_evaluation.json'
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(evaluation))
            link = {'attempt_id': 'fa1-session1-fixture', 'evaluation': 'reports/feedback_action_v1/session1_evaluation.json',
                    'evaluation_sha256': sha(path)}
            self.assertEqual(B.check_session_one(root, {'session': 2, 'session_1': link})['attempt_id'],
                             'fa1-session1-fixture')
            for change in ({'session_2_permitted': False}, {'session': 2}):
                path.write_text(json.dumps({**evaluation, 'evaluation': {**evaluation['evaluation'], **change}}))
                with self.assertRaises(ValueError):
                    B.check_session_one(root, {'session': 2, 'session_1': dict(link, evaluation_sha256=sha(path))})
            with self.assertRaises(ValueError):  # a drifted evaluation
                B.check_session_one(root, {'session': 2, 'session_1': link})


class ServerGroupCleanup(unittest.TestCase):
    def test_supervisor_stops_a_recorded_server_group_that_ignores_sigterm(self):
        if sys.platform != 'linux':
            self.skipTest('process groups are Linux-only here')
        from research.feedback_action_v1.live import supervisor as S
        with tempfile.TemporaryDirectory() as tmp:
            process = subprocess.Popen([sys.executable, '-c', 'import signal,time;signal.signal(signal.SIGTERM,'
                                        'signal.SIG_IGN);time.sleep(120)'], start_new_session=True)
            try:
                time.sleep(.5)
                (Path(tmp) / 'worker').mkdir()
                (Path(tmp) / 'worker/model-server.json').write_text(json.dumps({'pgid': process.pid}))
                report, errors = {}, []
                self.assertTrue(S.stop_model_server(tmp, errors, report))
                self.assertEqual((errors, report['model_server_group']['signalled_by_supervisor']),
                                 ([], ['SIGTERM', 'SIGKILL']))
            finally:
                process.kill()
                process.wait(timeout=5)

    def test_an_unsafe_record_is_never_signalled(self):
        from research.feedback_action_v1.live import supervisor as S
        import os
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'worker').mkdir()
            for pgid in (0, 1, -5, 'x', os.getpgrp()):
                (Path(tmp) / 'worker/model-server.json').write_text(json.dumps({'pgid': pgid}))
                report, errors = {}, []
                self.assertFalse(S.stop_model_server(tmp, errors, report))
                self.assertTrue(errors)


class ReviewSnapshot(unittest.TestCase):
    def setUp(self):
        if not REVIEW.is_dir():
            self.skipTest('review snapshot not built')

    def test_snapshot_binds_every_embedded_source_and_reproduces(self):
        lock = json.loads((REVIEW / 'review-source-lock.json').read_bytes())
        self.assertEqual((lock['scope'], lock['gpu_enabled']), ('feedback-action-v1', False))
        self.assertEqual(set(lock['bindings']), set(N.source_names(ROOT)))
        self.assertEqual(set(lock['review_documents']), set(B.REVIEW_REQUIRED))
        B.check_sources(ROOT, (REVIEW / 'review-source-lock.json').relative_to(ROOT).as_posix())
        with tempfile.TemporaryDirectory() as tmp:
            rebuilt = N.build_review(Path(tmp) / 'r', ROOT)
            self.assertEqual(rebuilt['artifacts'], lock['artifacts'])
            for name in ('profile.ipynb', 'kernel-metadata.json', 'review-source-lock.json'):
                self.assertEqual((Path(tmp) / 'r' / name).read_bytes(), (REVIEW / name).read_bytes(), name)

    def test_newest_revision_and_retained_history(self):
        locks = sorted(ROOT.glob(B.REVIEW_GLOB), key=lambda p: int(p.parent.name.rsplit('-r', 1)[1]))
        self.assertEqual(locks[-1].parent, REVIEW)
        for revision, digest in RETAINED_REVIEW_LOCKS.items():
            lock = ROOT / f'notebooks/feedback-action-v1-review-r{revision}/review-source-lock.json'
            self.assertEqual(hashlib.sha256(lock.read_bytes()).hexdigest(), digest)
            if revision == 1:  # r1 bound no review documents (the defect the freeze revision fixes)
                self.assertNotIn('review_documents', json.loads(lock.read_bytes()))
            with self.assertRaisesRegex(ValueError, 'drift|review documents incomplete'):
                B.check_sources(ROOT, lock.relative_to(ROOT).as_posix())  # superseded locks no longer match

    def test_review_documents_are_verified_and_drift_is_refused(self):
        from research.feedback_action_v1 import live_evaluation as LE
        record, problems = LE.review_lock_status(ROOT)
        self.assertEqual((problems, record['review_lock']), ([], (REVIEW / 'review-source-lock.json').relative_to(
            ROOT).as_posix()))
        lock_name = (REVIEW / 'review-source-lock.json').relative_to(ROOT).as_posix()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock = json.loads((ROOT / lock_name).read_bytes())
            folder = str(Path(lock_name).parent)
            for name in (lock_name, *[f'{folder}/{a}' for a in lock['artifacts']], *lock['bindings'],
                         *lock['review_documents']):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, root / name)
            B.check_sources(root, lock_name)
            path = root / 'research/feedback_action_v1/live_evaluation.py'
            path.write_bytes(path.read_bytes() + b'\n# drift\n')
            with self.assertRaisesRegex(ValueError, 'review document drift'):
                B.check_sources(root, lock_name)
            B.check_sources(root, lock_name, review_documents=False)  # the in-payload gate skips them
            record, problems = LE.review_lock_status(root)
            self.assertIsNone(record)
            self.assertIn('review document drift', problems[0])

    def test_a_deleted_source_and_its_binding_are_refused_by_the_gate(self):
        # Review P2 (second): the inventory is anchored to the reviewed notebook's embedded bindings, and a missing
        # repository module is an error; deleting a file together with its lock entry is refused either way.
        lock_name = (REVIEW / 'review-source-lock.json').relative_to(ROOT).as_posix()
        policy = 'research/feedback_action_v1/live/policy.py'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock = json.loads((ROOT / lock_name).read_bytes())
            folder = str(Path(lock_name).parent)
            for name in (lock_name, *[f'{folder}/{a}' for a in lock['artifacts']], *lock['bindings'],
                         *lock['review_documents']):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, root / name)
            B.check_sources(root, lock_name)  # the copy is the reviewed checkout
            del lock['bindings'][policy]
            (root / policy).unlink()
            (root / lock_name).write_text(json.dumps(lock, indent=1, sort_keys=True) + '\n')
            with self.assertRaisesRegex(ValueError, 'embedded inventory|missing'):
                B.check_sources(root, lock_name)
            with self.assertRaisesRegex(ValueError, 'repository modules imported but missing: .*live.policy'):
                N.source_names(root)

    def test_closure_refuses_missing_repository_modules_but_not_attribute_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'pkg').mkdir()
            (root / 'pkg/__init__.py').write_text('THING = 1\n')
            (root / 'pkg/a.py').write_text('from pkg import THING\nfrom pkg.b import helper\n')
            with self.assertRaisesRegex(ValueError, 'repository modules imported but missing: pkg.b'):
                RT.closure(['pkg.a'], root)
            (root / 'pkg/b.py').write_text('def helper():\n    return 1\n')
            files, external = RT.closure(['pkg.a'], root)
            self.assertEqual(files, ['pkg/__init__.py', 'pkg/a.py', 'pkg/b.py'])  # THING is an attribute, not a module

    def test_evaluator_review_check_imports_no_runner_policy_or_adapter(self):
        code = ('import sys\nfrom research.feedback_action_v1 import live_evaluation as LE\n'
                'record, problems = LE.review_lock_status()\n'
                'bad = sorted(m for m in sys.modules if m.endswith(("live.runner", "live.policy", "adapter")))\n'
                'print(problems, bad)')
        result = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.stdout.strip(), '[] []', result.stderr[-800:])

    def test_metadata_is_gpu_disabled_and_pinned(self):
        metadata = json.loads((REVIEW / 'kernel-metadata.json').read_bytes())
        self.assertEqual((metadata['enable_gpu'], metadata['enable_internet'], metadata['is_private']),
                         (False, False, True))
        runtime = RT.load(ROOT)
        self.assertEqual(metadata['docker_image'], runtime['kaggle_image']['docker_image'])
        self.assertEqual(metadata['competition_sources'], ['arc-prize-2026-arc-agi-3'])
        self.assertTrue(metadata['id'].startswith('REPLACE_WITH_'))
        notebook = json.loads((REVIEW / 'profile.ipynb').read_bytes())
        self.assertEqual(notebook['cells'][1]['source'].count("MODE = 'live'\n"), 1)


if __name__ == '__main__':
    unittest.main()
