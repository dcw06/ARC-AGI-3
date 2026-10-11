"""Track 3 runtime v2 r2: regressions for the lessons of Tracks 1, 2 and 4, the amendment-S1 self-review, the
preregistered suggestion-following measure and the two-session pooled evaluation. CPU only; no model, GPU, provider
or real approval; synthetic authority trees and rehearsal evidence live in temporary directories."""
import ast
from contextlib import nullcontext
import copy
import hashlib
import inspect
import json
import os
from pathlib import Path
import random
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from research.stagnation_supervision_runtime_v2 import authority as A, pooled as P, selfreview as SR
from tests import ssv_runtime_v2_fixtures as FX
from tests.test_stagnation_supervision_v1_outcomes import CLICK, SPEC, T2, chain, loop_then, move, new_states

LINUX = sys.platform == 'linux'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@unittest.skipUnless(LINUX, 'real POSIX process-group ownership')
class StartupOwnership(unittest.TestCase):
    """3aeeb65: an interruption during spawn, registration or log-thread startup still kills the owned group and
    retains a cleanup receipt; an uncertain spawn never claims that the groups are absent."""

    def exercise(self, point):
        from research.stagnation_supervision_runtime_v2 import launch
        child = None
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)

            def spawn(*args, **kwargs):
                nonlocal child
                child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'],
                                         start_new_session=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                if point == 'before_assignment':
                    os.kill(os.getpid(), signal.SIGINT)
                elif point == 'uncertain':
                    raise KeyboardInterrupt('spawn returned no ownership handle')
                elif point == 'registration':
                    class Handle:
                        signaled = False

                        @property
                        def pid(self):
                            if not self.signaled:
                                self.signaled = True
                                os.kill(os.getpid(), signal.SIGINT)
                            return child.pid

                        def __getattr__(self, name):
                            return getattr(child, name)
                    return Handle()
                return child

            def interrupted_start(_thread):
                raise KeyboardInterrupt('thread startup')

            try:
                with mock.patch.object(launch.threading.Thread, 'start', interrupted_start) if point == 'thread' else nullcontext():
                    with self.assertRaises(KeyboardInterrupt):
                        launch.run_supervisor(output, output, sys.executable, sys.executable, output,
                                              started=time.monotonic(), mode='rehearsal', internal_seconds=60,
                                              session='1', spawn=spawn)
                receipt = output / 'control/first-cell-supervisor-cleanup.json'
                self.assertTrue(receipt.is_file(), 'startup interruption must retain a cleanup receipt')
                value = json.loads(receipt.read_bytes())
                self.assertIn('checked_monotonic', value)
                if point == 'uncertain':
                    self.assertIs(value['groups_absent'], False)
                    self.assertEqual(value['ownership'], 'uncertain')
                else:
                    self.assertIsNotNone(child.poll(), 'owned supervisor survived interruption')
                    self.assertTrue(value['groups_absent'])
                    self.assertEqual(value['ownership'], 'registered')
            finally:
                if child is not None:
                    if child.poll() is None:
                        os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=5)
                    child.stdout.close()

    def test_thread_start_interruption_cleans_real_child(self):
        self.exercise('thread')

    def test_signal_before_assignment_is_deferred_until_registration(self):
        self.exercise('before_assignment')

    def test_uncertain_spawn_never_claims_group_absence(self):
        self.exercise('uncertain')

    def test_signal_before_group_registration_cleans_real_child(self):
        self.exercise('registration')


PASSING = {'status': 'study_complete_pending_independent_evaluation', 'first_cell_cleanup_verified': True}


@unittest.skipUnless(LINUX, 'evidence store uses fcntl')
class Finalization(unittest.TestCase):
    """3aeeb65 and cfda982: source removal and the final writes are charged to the first-cell clock; a durable
    barrier keeps every receipt provisional until the bounded finalization transaction completes."""

    def run_launch(self, clock, *, source_cleanup=None, save=None, unlink=None):
        from research.stagnation_supervision_runtime_v2 import launch
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        output = Path(tmp) / 'output'
        patches = [mock.patch.object(launch.time, 'monotonic', lambda: clock[0]),
                   mock.patch.object(launch, 'run_supervisor', return_value=dict(PASSING)),
                   mock.patch('research.stagnation_supervision_runtime_v2.authority.rehearsal_gate')]
        if save is not None:
            patches.append(mock.patch.object(launch.EvidenceStore, 'save', save))
        if unlink is not None:
            patches.append(mock.patch.object(Path, 'unlink', unlink))
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        try:
            result = launch.run(output, tmp, started=0, mode='rehearsal', internal_seconds=60, session='1',
                                source_cleanup=source_cleanup)
        except BaseException:
            result = None
        cost = output / 'control/notebook-cost.json'
        saved = json.loads(cost.read_bytes()) if cost.exists() else {}
        return result, saved, (output / 'control/finalization-pending.json').exists()

    def test_clean_finalization_certifies_and_removes_the_barrier(self):
        removed = []
        result, saved, pending = self.run_launch([10.0], source_cleanup=lambda: removed.append(True))
        self.assertIsNone(result['error'])
        self.assertEqual((saved['lifecycle_finalized'], saved['extracted_source_removed'], saved['finalization_guard_version']),
                         (True, True, 1))
        self.assertFalse(pending)
        self.assertEqual(removed, [True])

    def test_source_removal_crossing_the_deadline_is_charged(self):
        clock = [59.9]
        result, saved, pending = self.run_launch(clock, source_cleanup=lambda: clock.__setitem__(0, 60.1))
        self.assertIsNotNone(result['error'])
        self.assertTrue(result['extracted_source_removed'])
        self.assertFalse(saved['lifecycle_finalized'])
        self.assertTrue(pending)

    def test_failed_source_removal_fails_finalization(self):
        def fail():
            raise OSError('busy')
        result, saved, pending = self.run_launch([10.0], source_cleanup=fail)
        self.assertEqual(saved['extracted_source_removed'], False)
        self.assertIn('source cleanup', saved['error'])
        self.assertTrue(pending)

    def interrupted(self, fault):
        from research.stagnation_supervision_runtime_v2 import launch
        clock, original, injected = [59.9], launch.EvidenceStore.save, []

        def save(store, name, value, **kwargs):
            if injected and fault == 'storage_failure':
                raise OSError('failure recording unavailable')
            result = original(store, name, value, **kwargs)
            if name == 'notebook-cost.json' and value.get('lifecycle_finalized') is True and not injected:
                injected.append(True)
                clock[0] = 60.1
                if fault == 'signal':
                    os.kill(os.getpid(), signal.SIGINT)
                elif fault == 'system_exit':
                    raise SystemExit('after certification replace')
                else:
                    raise KeyboardInterrupt('after certification replace')
            return result

        result, saved, pending = self.run_launch(clock, source_cleanup=lambda: None, save=save)
        self.assertTrue(injected)
        if result is not None:
            self.assertIsNotNone(result['error'])
        self.assertTrue(pending or saved.get('error') is not None or saved.get('lifecycle_finalized') is not True,
                        'interrupted over-budget certification retained a passing receipt')

    def test_keyboard_interrupt_after_certification_write(self):
        self.interrupted('interrupt')

    def test_system_exit_after_certification_write(self):
        self.interrupted('system_exit')

    def test_failed_emergency_write_keeps_the_barrier(self):
        self.interrupted('storage_failure')

    def test_signal_after_certification_write(self):
        self.interrupted('signal')

    def test_barrier_removal_crossing_the_deadline_revokes_certification(self):
        clock, original = [59.9], Path.unlink

        def unlink(path, *args, **kwargs):
            result = original(path, *args, **kwargs)
            if path.name == 'finalization-pending.json':
                clock[0] = 60.1
            return result
        result, saved, pending = self.run_launch(clock, unlink=unlink)
        self.assertIsNotNone(result['error'])
        self.assertFalse(result['lifecycle_finalized'])
        self.assertTrue(pending)

    def test_only_the_extracted_payload_is_ever_removed(self):
        from research.stagnation_supervision_runtime_v2 import launch
        seen = []

        def fake_run(*args, **kwargs):
            seen.append(kwargs.get('source_cleanup'))
            return {'error': None, 'study_status': PASSING['status']}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(launch, 'run', fake_run), \
                mock.patch.dict(os.environ, {'SSV_REHEARSAL_WORKING': tmp}):
            checkout = Path(tmp) / 'checkout'
            checkout.mkdir()
            launch.notebook_entry(checkout, 0.0, 'rehearsal', '1')
            self.assertIsNone(seen[-1])
            extracted = Path(tempfile.mkdtemp(prefix='stagnation-supervision-runtime-v2-source-', dir=tmp))
            launch.notebook_entry(extracted, 0.0, 'rehearsal', '1')
            seen[-1]()
            self.assertFalse(extracted.exists())
            self.assertTrue(checkout.exists())
        self.assertIn('source_cleanup=remove_source)', inspect.getsource(launch.notebook_entry))


@unittest.skipUnless(LINUX, 'installer evidence uses fcntl')
class InstallationBackend(unittest.TestCase):
    """b75c78b: Kaggle's inline MPLBACKEND never reaches an installed interpreter's checks."""

    def test_model_install_and_checks_run_with_agg(self):
        from research.stagnation_supervision_runtime_v2 import prepare as PR
        seen = {}

        def fake_install(bundle, venv, runtime, deadline, log, python=None, environment=None, processes=None, **kw):
            seen['install'] = dict(environment or {})
            return {'python': str(venv / 'bin/python'), 'install_seconds': 1}

        def fake_run(argv, log, deadline, env, label, processes):
            seen.setdefault('run', []).append(dict(env))

        class Stop(Exception):
            pass

        def headless(*args, **kwargs):
            raise Stop('stop after the model interpreter')
        kaggle = {'MPLBACKEND': 'module://matplotlib_inline.backend_inline'}
        rt = 'research.stagnation_supervision_runtime_v2.publisher_install.'
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, kaggle), \
                mock.patch(rt + 'install', fake_install), mock.patch(rt + '_run', fake_run), \
                mock.patch(rt + 'verify_bundle', return_value={}), \
                mock.patch('certification.phase4_v6.target_install_probe_r3.verify_torch_contract', return_value={}), \
                mock.patch('certification.phase4_v6.clean_environment.verify_environment_wheels', return_value={}), \
                mock.patch('certification.phase4_v6.headless_environment.HeadlessEnvironment', headless):
            with self.assertRaises(Stop):
                PR.prepare(Path(tmp) / 'scratch', Path(tmp) / 'out', tmp, tmp, {}, time.monotonic(), root=A.ROOT)
        self.assertEqual(seen['install']['MPLBACKEND'], 'Agg')
        self.assertEqual([e['MPLBACKEND'] for e in seen['run']], ['Agg'])

    def test_game_interpreter_environment_uses_agg(self):
        from certification.phase4_v6.headless_environment import HeadlessEnvironment
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {'MPLBACKEND': 'module://matplotlib_inline.backend_inline'}):
            self.assertEqual(HeadlessEnvironment(Path(tmp) / 's', Path(tmp) / 'o').env['MPLBACKEND'], 'Agg')


def session1_record(**changes):
    return {'version': 'stagnation_supervision_runtime_v2_study_report_v2', 'mode': 'live', 'session': '1',
            'technically_complete': True, 'target_accepted': True, 'synthetic': True,
            'review_lock': {'lock': 'synthetic', 'sha256': '0' * 64, 'verified': True}, **changes}


class GateR2(unittest.TestCase):
    """Review documents bound and verified; the inventory anchored to the reviewed notebook; the in-payload gate
    skips only what the payload cannot contain; a session-2 attempt binds an accepted session-1 evaluation."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = FX.authority_tree(Path(self.temp.name) / 'root')
        self.lock = A.review_lock(self.root)

    def edited_lock(self, change):
        path = self.root / self.lock
        value = json.loads(path.read_bytes())
        change(value)
        path.write_text(json.dumps(value), encoding='utf-8')

    def test_the_lock_binds_the_frozen_protocol_and_the_evaluators(self):
        listed = json.loads((self.root / self.lock).read_bytes())['review_documents']
        for name in ('reports/stagnation_supervision_v1_protocol_v2_frozen.md',
                     'research/stagnation_supervision_runtime_v2/pooled.py',
                     'research/stagnation_supervision_runtime_v2/selfreview.py',
                     'research/stagnation_supervision_runtime_v2/report.py',
                     'research/stagnation_supervision_v1/closed_loop/evaluate.py',
                     'scripts/evaluate_stagnation_supervision_sessions.py',
                     'scripts/replay_transition_evidence_v1.py'):
            self.assertIn(name, listed)
        A.check_sources(self.root, self.lock)

    def test_review_document_listing_and_drift_refuse(self):
        name = 'reports/stagnation_supervision_v1_protocol_v2_frozen.md'
        original = (self.root / self.lock).read_bytes()
        self.edited_lock(lambda v: v['review_documents'].pop(name))
        with self.assertRaisesRegex(ValueError, 'review documents incomplete'):
            A.check_sources(self.root, self.lock)
        (self.root / self.lock).write_bytes(original)
        path = self.root / name
        path.write_bytes(path.read_bytes() + b'\n')
        with self.assertRaisesRegex(ValueError, 'drift'):
            A.check_sources(self.root, self.lock)

    def test_bindings_must_equal_the_reviewed_notebook_inventory(self):
        folder = (self.root / self.lock).parent
        notebook = json.loads((folder / 'profile.ipynb').read_bytes())
        cell = notebook['cells'][1]['source']
        line = next(l for l in cell.splitlines() if l.startswith('    bindings = '))
        embedded = ast.literal_eval(line.split(' = ', 1)[1])
        dropped = sorted(embedded)[0]
        embedded.pop(dropped)
        notebook['cells'][1]['source'] = cell.replace(line, '    bindings = ' + repr(embedded))
        (folder / 'profile.ipynb').write_text(json.dumps(notebook), encoding='utf-8')
        self.edited_lock(lambda v: v['artifacts'].update({'profile.ipynb': sha(folder / 'profile.ipynb')}))
        with self.assertRaisesRegex(ValueError, "embedded inventory"):
            A.check_sources(self.root, self.lock)

    def test_a_deleted_payload_file_with_its_entry_is_refused(self):
        name = 'research/stagnation_supervision_runtime_v2/mounts.py'
        self.edited_lock(lambda v: v['bindings'].pop(name))
        (self.root / name).unlink()
        with self.assertRaises(ValueError):
            A.check_sources(self.root, self.lock)

    def test_in_payload_gate_needs_no_reviewed_notebook_but_the_repository_gate_does(self):
        (self.root / self.lock).parent.joinpath('profile.ipynb').unlink()
        with self.assertRaises(A.LiveRefused):
            A.require_live(self.root)
        self.assertEqual(A.require(self.root)['attempt_id'], FX.ATTEMPT)

    def test_session_two_binds_an_accepted_session_one_evaluation(self):
        from research.stagnation_supervision_runtime_v2.notebook import launch_artifacts
        with tempfile.TemporaryDirectory() as tmp:
            bare = FX.authority_tree(Path(tmp) / 'bare', session='2')
            with self.assertRaisesRegex(A.LiveRefused, 'session 2 requires'):
                A.require_live(bare)
        with tempfile.TemporaryDirectory() as tmp:
            good = FX.authority_tree(Path(tmp) / 'good', session='2', session1_evaluation=session1_record())
            A.require_live(good)
            lock = json.loads(launch_artifacts(good)['launch-package-lock.json'])
            self.assertIn('private/session1-evaluation.json', lock['sidecars'])
        for change in ({'technically_complete': False}, {'target_accepted': False}, {'mode': 'rehearsal'},
                       {'review_lock': {'verified': False}}):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                bad = FX.authority_tree(Path(tmp) / 'bad', session='2', session1_evaluation=session1_record(**change))
                with self.assertRaises(A.LiveRefused):
                    A.require_live(bad)
        with tempfile.TemporaryDirectory() as tmp:
            first = FX.authority_tree(Path(tmp) / 'first', session='1', session1_evaluation=session1_record())
            with self.assertRaisesRegex(A.LiveRefused, 'only a session-2 attempt'):
                A.require_live(first)

    def test_the_evaluator_verifies_the_evaluating_checkout(self):
        from research.stagnation_supervision_runtime_v2.report import checkout_review_lock
        record, problems = checkout_review_lock(self.root)
        self.assertEqual((record['verified'], problems), (True, []))
        path = self.root / 'research/stagnation_supervision_runtime_v2/pooled.py'
        path.write_bytes(path.read_bytes() + b'\n')
        record, problems = checkout_review_lock(self.root)
        self.assertFalse(record['verified'])
        self.assertIn('evaluating checkout review lock', problems[0])


def episode(name, game, arm, records, *, repeat_of=None, delivered=(), first_tests=None, block=1, session='1'):
    return {'episode': name, 'session': session, 'game': game, 'arm': arm, 'records': records, 'block': block,
            'repeat': repeat_of is not None, 'repeat_of': repeat_of, 'delivered': list(delivered),
            'first_tests': first_tests if first_tests is not None else [None] * len(records),
            'reflections': [], 'triggers': [], 'calls': [], 'levels_completed': 0, 'stop_reason': 'action_cap'}


class SuggestionFollowing(unittest.TestCase):
    """§8.1 preregistered descriptive measure."""

    def test_exit_action_is_compared_with_the_first_test_action_in_force(self):
        records = T2.history(loop_then(2, new_states(13)))  # opportunity at 1, exit at 2 with move(0)
        exit_action = move(0)
        cases = ((exit_action, (1, 1, 1, 0)), ({'action_id': 2, 'action_data': {}}, (1, 1, 0, 0)), (None, (1, 0, 0, 1)))
        for test, expected in cases:
            with self.subTest(test=test):
                tests = [None] * len(records)
                tests[2] = test
                result = P.suggestion_following([episode('t', 'ar25', 'triggered', records, first_tests=tests)], SPEC, 40)
                row = result['by_arm']['triggered']['by_game']['ar25']
                self.assertEqual((row['recovered_exits'], row['with_suggestion_in_force'],
                                  row['exit_equals_first_test_action'], row['without_suggestion_in_force']), expected)
        self.assertEqual(result['by_arm']['periodic']['primary_games']['recovered_exits'], 0)


def label_population():
    wa30 = T2.history(chain(new_states(30)))
    ar25 = T2.history(loop_then(30, []))
    ls20 = T2.history(chain(new_states(12) + [(CLICK, None, {})] * 10))
    eps = []
    for arm in ('continuation', 'periodic', 'triggered'):
        for block in (1, 2):
            eps.append(episode(f'b{block}-wa30-{arm}', 'wa30', arm, wa30, block=block, session=str(block),
                               delivered=[9, 19] if arm != 'continuation' else []))
            eps.append(episode(f'b{block}-ar25-{arm}', 'ar25', arm, ar25, block=block, session=str(block),
                               delivered=[5, 9, 15, 19, 25, 29] if arm == 'triggered' else ([9] if arm == 'periodic' else [])))
            eps.append(episode(f'b{block}-ls20-{arm}', 'ls20', arm, ls20, block=block, session=str(block)))
            eps.append(episode(f'b{block}-s5i5-{arm}', 's5i5', arm, ar25, block=block, session=str(block),
                               delivered=[9] if arm != 'continuation' else []))
    eps.append(episode('r1-ar25-continuation', 'ar25', 'continuation', ar25, repeat_of='b1-ar25-continuation'))
    return eps


class SelfReview(unittest.TestCase):
    """Amendment S1 sample: seeded, stratified, order-independent, from decision-point lists only."""

    def setUp(self):
        self.episodes = label_population()
        self.sample = SR.draw(SR.candidates(self.episodes, SPEC, 40))

    def test_draw_is_deterministic_and_order_independent(self):
        shuffled = list(self.episodes)
        random.Random(7).shuffle(shuffled)
        self.assertEqual(SR.draw(SR.candidates(shuffled, SPEC, 40))['sample_sha256'], self.sample['sample_sha256'])
        self.assertNotEqual(SR.draw(SR.candidates(self.episodes, SPEC, 40), seed='another')['sample_sha256'],
                            self.sample['sample_sha256'])

    def test_strata_quotas_exclusions_and_reflection_fill(self):
        strata = self.sample['strata']
        for name in SR.LABEL_STRATA:
            self.assertLessEqual(len(strata[name]['selected']), 20)
        self.assertEqual(len(strata['gate_eligible/LC']['selected']), 20)
        self.assertEqual({i['game'] for i in strata['gate_eligible/LC']['selected']}, {'wa30'})
        self.assertEqual({i['game'] for i in strata['gate_eligible/ST']['selected']}, {'ar25'})
        self.assertEqual({i['game'] for i in strata['ls20/LC']['selected']}, {'ls20'})
        everything = [i for row in strata.values() for i in row['selected']]
        self.assertFalse([i for i in everything if i['game'] == 's5i5' or i['episode'].startswith('r1-')])
        # periodic has 2 (wa30) x 2 + 1 (ar25) x 2 = 6 delivered; triggered (16) fills the remaining 14 of 20
        self.assertEqual((len(strata['reflections/periodic']['selected']),
                          len(strata['reflections/triggered']['selected'])), (6, 14))
        self.assertNotIn('reflections', self.sample['shortfall'])

    def test_annotations_must_be_complete_ordered_and_bound(self):
        record = SR.template(self.sample)
        with self.assertRaises(ValueError):
            SR.validate(self.sample, record)  # every answer still null
        for name, items in record['annotations'].items():
            for item in items:
                for field in SR.FIELDS[self.sample['strata'][name]['kind']]:
                    item[field] = 'yes'
        record['annotations']['gate_eligible/LC'][0]['label_describes_visible_situation'] = 'no'
        summary = SR.validate(self.sample, record)
        self.assertEqual(summary['label_disagreement']['gate_eligible']['disagree'], 1)
        self.assertEqual(summary['label_disagreement']['gate_eligible']['status'],
                         'descriptive only (amendment S1); not label certification')
        reordered = copy.deepcopy(record)
        reordered['annotations']['gate_eligible/LC'].reverse()
        tampered = copy.deepcopy(self.sample)
        tampered['strata']['gate_eligible/LC']['selected'].pop()
        extra = copy.deepcopy(record)
        extra['annotations']['gate_eligible/LC'][0]['arm'] = 'triggered'
        for sample, annotations in ((self.sample, reordered), (tampered, record), (self.sample, extra)):
            with self.assertRaises(ValueError):
                SR.validate(sample, annotations)


@unittest.skipUnless(LINUX, 'connected rehearsal uses the POSIX process tree')
class PooledRehearsal(unittest.TestCase):
    """Two shortened rehearsal sessions (scripted model, offline engine, injected GPU) pooled end to end."""

    @classmethod
    def setUpClass(cls):
        from research.grounded_action_v1.engine import restore_game_mount
        from research.stagnation_supervision_v1.closed_loop import bridge as B
        from research.stagnation_supervision_runtime_v2.launch import run
        from research.stagnation_supervision_runtime_v2.report import study_report
        cls.tmp = tempfile.TemporaryDirectory(prefix='ssv-rt2-pooled-')
        work = Path(cls.tmp.name)
        games = restore_game_mount(work / 'games')
        cls.outputs, cls.records, cls.specs = {}, {}, {}
        for session, groups in (('1', 'b1-ar25,r1-ar25'), ('2', 'b2-ar25')):
            env = {'SSV_REHEARSAL': '1', 'CUDA_VISIBLE_DEVICES': '', 'SSV_REHEARSAL_GAMES': str(games),
                   'SSV_REHEARSAL_GROUPS': groups, 'SSV_REHEARSAL_ACTIONS': '20'}
            with mock.patch.dict(os.environ, env):
                receipt = run(work / f'working{session}/out', work / f'working{session}', started=time.monotonic(),
                              mode='rehearsal', internal_seconds=1500, session=session)
                cls.specs[session] = B.session_run_spec(session, 'rehearsal')
            assert receipt['error'] is None, receipt
            cls.outputs[session] = work / f'working{session}/out'
            report = study_report(cls.outputs[session], cls.specs[session], mode='rehearsal', session=session,
                                  internal_seconds=1500)
            cls.records[session] = work / f'session{session}.json'
            cls.records[session].write_text(json.dumps(report, indent=1, default=str), encoding='utf-8')
        cls.first = json.loads((cls.outputs['1'] / 'control/notebook-cost.json').read_bytes())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def annotations(self, folder):
        from research.stagnation_supervision_v1 import thresholds as S
        trigger = S.load()
        episodes = []
        for s in ('1', '2'):
            episodes += P.session_episodes(self.outputs[s] / 'worker/run', self.specs[s], trigger, s)
        sample = SR.draw(SR.candidates(episodes, trigger, 20), inputs=P.inputs_digest(episodes))
        record = SR.template(sample)
        for name, items in record['annotations'].items():
            for item in items:
                for field in SR.FIELDS[sample['strata'][name]['kind']]:
                    item[field] = 'unclear'
        path = Path(folder) / 'annotations.json'
        path.write_text(json.dumps(record), encoding='utf-8')
        return path, sha(path)

    def pool(self, records=None, annotations=None, digest=None):
        with tempfile.TemporaryDirectory() as tmp:
            path, real = self.annotations(tmp)
            return P.evaluate_sessions(self.outputs, records or self.records, annotations=annotations or path,
                                       annotations_sha256=digest or real, mode='rehearsal', specs=self.specs,
                                       internal_seconds={'1': 1500, '2': 1500})

    def test_rehearsal_receipt_is_finalized(self):
        self.assertEqual((self.first['finalization_guard_version'], self.first['lifecycle_finalized']), (1, True))
        self.assertFalse((self.outputs['1'] / 'control/finalization-pending.json').exists())
        cleanup = json.loads((self.outputs['1'] / 'control/first-cell-supervisor-cleanup.json').read_bytes())
        self.assertEqual((cleanup['ownership'], cleanup['groups_absent']), ('registered', True))

    def test_pooled_evaluation_after_the_self_review(self):
        result = self.pool()
        self.assertEqual(result['problems'], [])
        pooled = result['pooled']
        self.assertEqual(set(pooled['primary']['by_arm']), {'continuation', 'periodic', 'triggered'})
        self.assertEqual(pooled['primary']['by_arm']['continuation']['episodes'], 2)  # the repeat is excluded
        repeats = pooled['reproducibility']['repeats']
        self.assertEqual([r['repeat'] for r in repeats], ['r1-ar25-continuation'])
        self.assertEqual(len(pooled['reproducibility']['block_2_vs_block_1']), 3)
        self.assertEqual(pooled['advancement']['verdict'], 'inconclusive')
        self.assertFalse(pooled['advancement']['conditions']['false_interruptions_within_cap_and_at_most_periodic'])
        for arm in ('periodic', 'triggered'):
            row = pooled['suggestion_following']['by_arm'][arm]['primary_games']
            self.assertEqual(row['recovered_exits'], row['with_suggestion_in_force'] + row['without_suggestion_in_force'])
            self.assertLessEqual(row['exit_equals_first_test_action'], row['with_suggestion_in_force'])
        self.assertEqual(result['self_review']['label_disagreement']['gate_eligible']['disagreement_rate'], None)

    def test_stale_or_edited_session_records_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            edited = Path(tmp) / 'session1.json'
            value = json.loads(self.records['1'].read_bytes())
            value['problems'] = []
            value['endpoints'] = None
            edited.write_text(json.dumps(value), encoding='utf-8')
            result = self.pool(records={'1': edited, '2': self.records['2']})
        self.assertIsNone(result['pooled'])
        self.assertIn('session 1: retained evaluation differs from its recomputation (stale or edited)', result['problems'])

    def test_no_comparison_before_committed_annotations(self):
        result = self.pool(digest='0' * 64)
        self.assertIsNone(result['pooled'])
        self.assertTrue(any('self-review' in p for p in result['problems']))
        with tempfile.TemporaryDirectory() as tmp:
            path, _ = self.annotations(tmp)
            record = json.loads(path.read_bytes())
            items = next(v for v in record['annotations'].values() if v)
            items[0][next(k for k in items[0] if k not in ('key', 'note'))] = None
            path.write_text(json.dumps(record), encoding='utf-8')
            result = self.pool(annotations=path, digest=sha(path))
        self.assertIsNone(result['pooled'])

    def test_target_evaluator_rejects_uncertified_finalization_and_ownership(self):
        from research.stagnation_supervision_runtime_v2.target_evaluate import evaluate_target
        from certification.phase4_integrated_v2.evidence import EvidenceStore
        mutations = (
            ('control', 'notebook-cost.json', lambda v: v.pop('finalization_guard_version'),
             'lifecycle finalization/source removal not certified'),
            ('control', 'notebook-cost.json', lambda v: v.update(lifecycle_finalized=False),
             'lifecycle finalization/source removal not certified'),
            ('control', 'finalization-pending.json', None, 'lifecycle finalization/source removal not certified'),
            ('control', 'first-cell-supervisor-cleanup.json', lambda v: v.update(ownership='uncertain'),
             'first-cell process/log cleanup'),
        )
        for component, name, change, message in mutations:
            with self.subTest(name=name, message=message), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / 'out'
                shutil.copytree(self.outputs['1'], output)
                path = output / component / name
                value = {'scope': 'first_cell_finalization', 'pending': True} if change is None else json.loads(path.read_bytes())
                if change is not None:
                    change(value)
                EvidenceStore(output, component).save(name, value)
                result = evaluate_target(output, self.specs['1'], mode='rehearsal', session='1', internal_seconds=1500)
                self.assertFalse(result['technically_complete'])
                self.assertIn(message, ' '.join(result['problems']))


if __name__ == '__main__':
    unittest.main()
