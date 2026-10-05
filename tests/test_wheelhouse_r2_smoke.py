"""Wheelhouse R2 smoke test v1: the live gate (placeholders, reviewed sources, approvals, Record C, reservation) with
fixtures, the request ledger and clock, evidence classes, pinned settings, the launch package and two scripted
CPU rehearsals. No GPU, model, upload or reservation is involved."""
import copy
import hashlib
import json
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from certification.wheelhouse_r2_smoke_v1 import binding as B
from certification.wheelhouse_r2_smoke_v1 import launch as L
from certification.wheelhouse_r2_smoke_v1 import notebook as N
from certification.wheelhouse_r2_smoke_v1.accounting import Clock, Ledger, RequestRefused
from certification.wheelhouse_r2_smoke_v1.client import CASES, body_for, metrics, png
from certification.wheelhouse_r2_smoke_v1.evidence import Evidence
from certification.wheelhouse_r2_smoke_v1.rehearsal import scenario
from certification.wheelhouse_r2_smoke_v1.run import run

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = B.load_protocol(ROOT)


def put(root, name, value):
    path = Path(root) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n', encoding='utf-8')


class FixtureRoot:
    """A temporary root with the package, a resolved fixture dataset binding, a review lock, source approval,
    Record C compute authorization, execution lock and reservation that together satisfy the gate."""

    def __init__(self, test, resolve=True, authorize=True):
        self.root = Path(tempfile.mkdtemp(prefix='smoke-gate-'))
        test.addCleanup(shutil.rmtree, self.root)
        shutil.copytree(ROOT / B.PACKAGE, self.root / B.PACKAGE, ignore=shutil.ignore_patterns('__pycache__'))
        protocol = copy.deepcopy(PROTOCOL)
        if resolve:
            protocol['dataset'] = {'ref': 'team/arc3-vllm-0.19.0-cu128-wheelhouse-r2', 'version': '1',
                                   'sha256sums_sha256': 'a' * 64, 'bundle_manifest_sha256': 'b' * 64}
        put(self.root, B.PROTOCOL, protocol)
        self.protocol = protocol
        N.build_review(self.root / 'notebooks/wheelhouse-r2-smoke-v1-review-r1', root=self.root)
        if authorize:
            self.authorize()

    def sha(self, name):
        return hashlib.sha256((self.root / name).read_bytes()).hexdigest()

    def authorize(self, **compute_overrides):
        lock = B.review_lock(self.root)
        common = {'status': 'approved', 'scope': B.SCOPE, 'review_lock_sha256': self.sha(lock),
                  'user_response': 'fixture approval (test only)', 'approved_at': '2026-10-04T00:00:00+00:00'}
        put(self.root, B.SOURCE, dict(common, approval_kind='source'))
        compute = dict(common, approval_kind='compute', source_approval_sha256=self.sha(B.SOURCE),
                       protocol_sha256=self.sha(B.PROTOCOL), dataset=self.protocol['dataset'],
                       **{k: self.protocol['limits'][k] for k in B.COMPUTE_LIMITS})
        compute.update(compute_overrides)
        put(self.root, B.COMPUTE, compute)
        execution = {'scope': B.SCOPE, 'attempt_id': 'r2s-fixture0001', 'review_lock': lock,
                     'review_sha256': self.sha(lock), 'source_approval_sha256': self.sha(B.SOURCE),
                     'compute_approval_sha256': self.sha(B.COMPUTE)}
        put(self.root, B.EXECUTION, execution)
        put(self.root, B.RESERVATION, {'status': 'reserved', 'attempt_id': execution['attempt_id'],
                                       'execution_sha256': hashlib.sha256(
                                           json.dumps(execution, sort_keys=True, indent=2).encode() + b'\n'
                                       ).hexdigest(), 'events': ['reserve']})
        put(self.root, B.CLAIM, {'status': 'claimed', 'attempt_id': execution['attempt_id'],
                                 'execution_sha256': self.sha(B.EXECUTION), 'reservation_sha256': self.sha(B.RESERVATION),
                                 'claimed_at': '2026-10-04T00:00:00+00:00'})


class LiveGate(unittest.TestCase):
    def refused(self, root):
        with self.assertRaises(B.LiveRefused) as caught:
            B.require_live(root)
        return ' | '.join(caught.exception.reasons)

    def test_this_checkout_refuses_on_placeholders_and_missing_authorization(self):
        reasons = self.refused(ROOT)
        for path in ('dataset.ref', 'dataset.version', 'dataset.sha256sums_sha256', 'dataset.bundle_manifest_sha256'):
            self.assertIn(path, reasons)
        self.assertIn('authorization', reasons)

    def test_complete_fixture_authorization_opens_the_gate(self):
        fixture = FixtureRoot(self)
        protocol, execution = B.require_live(fixture.root)
        self.assertEqual(execution['attempt_id'], 'r2s-fixture0001')

    def test_placeholders_refuse_even_with_every_approval(self):
        fixture = FixtureRoot(self, resolve=False)
        self.assertIn('unresolved placeholders', self.refused(fixture.root))

    def test_each_missing_or_mismatched_condition_refuses(self):
        cases = {
            'source drift': lambda f: (f.root / B.PACKAGE / 'run.py').write_text('# altered\n'),
            'no source approval': lambda f: (f.root / B.SOURCE).unlink(),
            'no compute authorization': lambda f: (f.root / B.COMPUTE).unlink(),
            'compute limit differs': lambda f: f.authorize(maximum_model_requests=13),
            'compute seconds differ': lambda f: f.authorize(authorized_seconds=7200),
            'compute not bound to the dataset': lambda f: f.authorize(dataset=dict(f.protocol['dataset'], version='2')),
            'compute not bound to the protocol': lambda f: f.authorize(protocol_sha256='0' * 64),
            'no reservation': lambda f: (f.root / B.RESERVATION).unlink(),
            'consumed reservation': lambda f: put(f.root, B.RESERVATION, dict(
                json.loads((f.root / B.RESERVATION).read_text()), events=['reserve', 'consume'])),
            'unbound execution lock': lambda f: put(f.root, B.EXECUTION, dict(
                json.loads((f.root / B.EXECUTION).read_text()), compute_approval_sha256='0' * 64)),
        }
        for label, damage in cases.items():
            with self.subTest(case=label):
                fixture = FixtureRoot(self)
                damage(fixture)
                self.assertIn('authorization', self.refused(fixture.root))

    def test_consume_marks_the_attempt_once_per_session_only(self):
        """The notebook marker is a session-local guard; it cannot see other sessions (documented limit)."""
        fixture = FixtureRoot(self)
        first, second = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, first)
        self.addCleanup(shutil.rmtree, second)
        B.consume(fixture.root, first)
        with self.assertRaises(FileExistsError):
            B.consume(fixture.root, first)
        B.consume(fixture.root, second)  # another session: not preventable offline; see DurableAccounting
        marker = json.loads(next(second.glob('.*.consumed.json')).read_text())
        self.assertEqual(marker['scope'], 'this provider session only')

    def test_missing_or_unbound_launch_claim_refuses(self):
        fixture = FixtureRoot(self)
        (fixture.root / B.CLAIM).unlink()
        self.assertIn('launch_claim.json', self.refused(fixture.root))
        fixture = FixtureRoot(self)
        claim = json.loads((fixture.root / B.CLAIM).read_text())
        put(fixture.root, B.CLAIM, dict(claim, reservation_sha256='0' * 64))
        self.assertIn('launch claim', self.refused(fixture.root))

    def test_launch_package_refuses_here_and_binds_everything_when_authorized(self):
        with self.assertRaises(B.LiveRefused):
            N.launch_artifacts(ROOT)
        fixture = FixtureRoot(self)
        artifacts = N.launch_artifacts(fixture.root)
        metadata = json.loads(artifacts['kernel-metadata.json'])
        self.assertTrue(metadata['enable_gpu'])
        self.assertEqual(metadata['dataset_sources'], [fixture.protocol['dataset']['ref']])
        lock = json.loads(artifacts['launch-package-lock.json'])
        self.assertEqual(lock['attempt_id'], 'r2s-fixture0001')
        self.assertEqual(set(lock['sidecars']), {B.review_lock(fixture.root), B.SOURCE, B.COMPUTE, B.EXECUTION,
                                                 B.RESERVATION, B.CLAIM})
        self.assertIn("authority sidecar drift", json.loads(artifacts['profile.ipynb'])['cells'][1]['source'])

    def test_review_notebook_is_gpu_disabled_without_a_dataset_while_unresolved(self):
        notebook, metadata, bindings, pending = N.review_notebook(ROOT)
        self.assertFalse(metadata['enable_gpu'])
        self.assertEqual(metadata['dataset_sources'], [])
        self.assertEqual(len(pending), 4)
        self.assertEqual(set(bindings), set(N.source_names(ROOT)))

    def test_live_run_requires_gpu_queries(self):
        with self.assertRaises(ValueError):
            run('live', PROTOCOL, Path(tempfile.mkdtemp()) / 'out', time.monotonic(), bundle='x', workdir='y')


class FakeTime:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class Accounting(unittest.TestCase):
    def setUp(self):
        self.time = FakeTime()
        self.clock = Clock(PROTOCOL['limits'], self.time.t, self.time)

    def test_plan_worst_case_is_within_the_cap(self):
        worst = sum(item.get('max_issues', 1) for item in PROTOCOL['requests'])
        self.assertLessEqual(worst, PROTOCOL['limits']['maximum_model_requests'])
        kinds = {item['kind'] for item in PROTOCOL['requests']}
        self.assertEqual(kinds, {'startup_probe', 'inference', 'cancellation_probe'})

    def test_only_planned_requests_once_each_and_never_above_the_cap(self):
        ledger = Ledger(PROTOCOL['requests'], 12, self.clock)
        ledger.admit('S1')
        for bad in ('S1', 'X9'):
            with self.assertRaises(RequestRefused):
                ledger.admit(bad)
        ledger.admit('C2')
        ledger.admit('C2')
        with self.assertRaises(RequestRefused):
            ledger.admit('C2')
        self.assertEqual(len(ledger.refusals), 3)

    def test_a_plan_above_the_cap_is_rejected(self):
        with self.assertRaises(ValueError):
            Ledger(PROTOCOL['requests'], 10, self.clock)
        tight = Ledger(PROTOCOL['requests'][:2], 2, self.clock)
        tight.admit('S1')
        tight.admit('S2')
        self.assertEqual(tight.summary()['issued'], 2)

    def test_admission_cutoff_and_internal_deadline(self):
        ledger = Ledger(PROTOCOL['requests'], 12, self.clock)
        self.time.t += PROTOCOL['limits']['admission_cutoff_seconds']
        with self.assertRaises(RequestRefused):
            ledger.admit('S1')
        self.assertLessEqual(self.clock.phase_deadline(900), self.clock.started + 3120)
        self.time.t = self.clock.started + PROTOCOL['limits']['internal_seconds']
        with self.assertRaises(TimeoutError):
            self.clock.check('anything')

    def test_limits_are_consistent(self):
        limits = PROTOCOL['limits']
        self.assertEqual(limits['admission_cutoff_seconds'],
                         limits['internal_seconds'] - limits['cleanup_reserve_seconds'])
        self.assertLess(limits['internal_seconds'], limits['authorized_seconds'])
        self.assertEqual((limits['maximum_attempts'], limits['automatic_retries']), (1, 0))


class EvidenceClass(unittest.TestCase):
    def test_a_rehearsal_cannot_claim_gpu_evidence(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder)
        final = Evidence(folder / 'e', 'rehearsal').finalize(
            {'passed': True, 'gpu_compatibility_evidence': True, 'evidence_class': 'gpu_runtime_compatibility'})
        self.assertEqual(final['evidence_class'], 'scripted_cpu_rehearsal')
        self.assertFalse(final['gpu_compatibility_evidence'])
        manifest = json.loads((folder / 'e/evidence-manifest.json').read_text())
        self.assertIn('result.json', manifest['files'])

    def test_live_evidence_only_when_passed(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder)
        self.assertFalse(Evidence(folder / 'a', 'live').finalize({'passed': False})['gpu_compatibility_evidence'])
        self.assertTrue(Evidence(folder / 'b', 'live').finalize({'passed': True})['gpu_compatibility_evidence'])


class PinnedSettings(unittest.TestCase):
    def test_model_and_server_match_the_operational_pins(self):
        primary = json.loads((ROOT / 'config/operational_primary.yaml').read_text())['primary']
        spec = json.loads((ROOT / 'config/m0_launch_spec_q3vl30.json').read_text())
        artifact = primary['model_artifact']
        for key in ('tree_sha256', 'required_files', 'shard_glob', 'shard_count', 'mounted_path'):
            self.assertEqual(PROTOCOL['model'][key], artifact[key])
        self.assertEqual(PROTOCOL['model']['revision'], spec['model_revision'])
        self.assertEqual([a if a != '{port}' else '8000' for a in PROTOCOL['server']['argv']], spec['argv'])
        self.assertEqual(PROTOCOL['server']['env'], spec['env'])
        self.assertEqual(PROTOCOL['sampling'], {'temperature': 0, 'seed': 0})

    def test_runtime_and_lock_match_the_wheelhouse_evidence(self):
        plan = json.loads((ROOT / 'reports/wheelhouse_r2_bundle_plan.json').read_text())
        check = json.loads((ROOT / 'reports/wheelhouse_r2_offline_install_check.json').read_text())
        self.assertEqual(PROTOCOL['bundle']['requirements_lock_sha256'], plan['requirements_lock']['sha256'])
        self.assertEqual(PROTOCOL['bundle']['approved_manifest_sha256'], plan['source_manifest_sha256'])
        modules = check['imports']['modules']
        self.assertEqual({k: modules[k]['version'] for k in modules}, PROTOCOL['runtime']['packages'])
        self.assertEqual(check['imports']['torch_cuda_build'], PROTOCOL['runtime']['torch_cuda_build'])

    def test_request_bodies_carry_the_pinned_sampling(self):
        body = body_for('exact_word', PROTOCOL['server']['served_model_name'], PROTOCOL['sampling'])
        self.assertEqual((body['temperature'], body['seed'], body['model']),
                         (0, 0, 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8'))
        self.assertTrue(png().startswith(b'\x89PNG\r\n\x1a\n'))
        self.assertTrue(all(CASES[c]['max_tokens'] <= 1024 for c in CASES))

    def test_idle_metrics_parsing(self):
        text = ('vllm:num_requests_running{model_name="m"} 0.0\nvllm:num_requests_waiting{model_name="m"} 2.0\n'
                '# HELP other\n')
        self.assertEqual(metrics(text), {'running': 0, 'waiting': 2})


class Rehearsals(unittest.TestCase):
    """Two end-to-end scripted rehearsals (the full set is scripts/wheelhouse_r2_smoke_rehearsal.py)."""

    def setUp(self):
        self.base = tempfile.mkdtemp(prefix='smoke-rehearsal-')
        self.addCleanup(shutil.rmtree, self.base)

    def test_nominal_rehearsal(self):
        summary, result = scenario('nominal', self.base)
        self.assertTrue(summary['as_expected'], summary)
        self.assertLessEqual(result['ledger']['issued'], 12)
        self.assertEqual(result['ledger']['by_kind']['startup_probe'], 3)
        self.assertTrue(result['cleanup']['server']['groups_absent'])
        self.assertTrue((Path(summary['evidence_dir']) / 'evidence-manifest.json').exists())

    def test_request_timeout_still_cleans_up(self):
        summary, result = scenario('request_timeout', self.base)
        self.assertTrue(summary['as_expected'], summary)
        self.assertRegex(result['error'], 'timed out|deadline')
        self.assertEqual(result['failed_stage'], 'startup_probe_S3')
        self.assertTrue(result['cleanup']['server']['groups_absent'])


IGNORES_SIGTERM = ('import signal, time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\ntime.sleep(60)\n')


class CleanupInterruption(unittest.TestCase):
    """Review P1: the cutoff alarm must not be able to bypass SIGKILL escalation during cleanup."""

    def setUp(self):
        import signal
        import sys
        self.signal, self.sys = signal, sys
        self.previous = signal.getsignal(signal.SIGALRM)
        self.addCleanup(signal.signal, signal.SIGALRM, self.previous)
        self.addCleanup(signal.setitimer, signal.ITIMER_REAL, 0)
        self.addCleanup(signal.pthread_sigmask, signal.SIG_UNBLOCK, {signal.SIGALRM})
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)

    def server(self):
        from certification.wheelhouse_r2_smoke_v1.server import ModelServer
        server = ModelServer([self.sys.executable, '-c', IGNORES_SIGTERM], {}, self.folder / 'log', '127.0.0.1', 1)
        server.start()
        time.sleep(0.3)  # let the child install its SIGTERM handler
        return server

    def raise_on_alarm(self, *_):
        raise TimeoutError('cutoff alarm (test)')

    def test_an_alarm_during_the_sigterm_grace_still_reaches_sigkill(self):
        server = self.server()
        self.signal.signal(self.signal.SIGALRM, self.raise_on_alarm)
        self.signal.setitimer(self.signal.ITIMER_REAL, 0.3)  # fires inside the 3-second SIGTERM grace
        receipt = server.stop(time.monotonic() + 10, terminate_grace=3, kill_grace=3)
        self.assertTrue(receipt['sigterm_sent'])
        self.assertTrue(receipt['sigkill_sent'])
        self.assertTrue(receipt['groups_absent'])
        self.assertTrue(any('sigterm phase: TimeoutError' in x for x in receipt['interrupted']))

    def test_entering_cleanup_disarms_and_blocks_the_cutoff(self):
        from certification.wheelhouse_r2_smoke_v1.run import CutoffAlarm
        server = self.server()
        alarm = CutoffAlarm()
        alarm.arm(0.3)
        alarm.enter_cleanup()
        receipt = server.stop(time.monotonic() + 10, terminate_grace=1, kill_grace=3)
        time.sleep(0.4)  # past the original cutoff
        alarm.release()  # a pending alarm is discarded, not raised
        self.assertEqual(receipt['interrupted'], [])
        self.assertTrue(receipt['sigkill_sent'] and receipt['groups_absent'])

    def test_cutoff_during_run_cleanup(self):
        """run(): a real alarm lands during cleanup (transition bypassed): SIGKILL still sent, group gone, run failed.
        With the transition in place, the same alarm cannot interrupt cleanup."""
        from certification.wheelhouse_r2_smoke_v1.run import CutoffAlarm
        base = tempfile.mkdtemp(prefix='smoke-cutoff-')
        self.addCleanup(shutil.rmtree, base)
        self.signal.signal(self.signal.SIGALRM, self.raise_on_alarm)

        def bypassed():  # the cutoff fires 0.5 s into cleanup: inside the stub's 2-second SIGTERM grace
            self.signal.setitimer(self.signal.ITIMER_REAL, 0.5)
        summary, result = scenario('server_ignores_sigterm', base, on_cleanup=bypassed)
        stopped = result['cleanup']['server']
        self.assertTrue(stopped['sigkill_sent'] and stopped['groups_absent'])
        self.assertTrue(stopped['interrupted'])
        self.assertFalse(result['passed'])

        alarm = CutoffAlarm()

        def proper():
            self.signal.setitimer(self.signal.ITIMER_REAL, 0.5)
            alarm.enter_cleanup()
        alarm.previous = self.raise_on_alarm
        summary, result = scenario('server_ignores_sigterm', base, on_cleanup=proper)
        alarm.release()
        self.assertEqual(result['cleanup']['server']['interrupted'], [])
        self.assertTrue(result['passed'], result['error'])


CONFIRMED = {'ref': '/code/' + N.KERNEL_ID, 'url': 'https://www.kaggle.com/code/' + N.KERNEL_ID, 'versionNumber': 1,
             'error': None, 'invalidTags': [], 'invalidDatasetSources': [], 'invalidCompetitionSources': [],
             'invalidKernelSources': [], 'invalidModelSources': []}


class FakeBackend:
    def __init__(self, fail=False, response=CONFIRMED):
        self.fail, self.response, self.pushes = fail, response, 0

    def push(self, folder):
        self.pushes += 1
        if self.fail:
            raise ConnectionError('provider did not answer')
        return self.response


class DurableAccounting(unittest.TestCase):
    """Review P1: once-only accounting must survive a fresh session; it lives launch-side, in the repository."""

    def package(self):
        fixture = FixtureRoot(self)
        folder = Path(tempfile.mkdtemp()) / 'launch'
        self.addCleanup(shutil.rmtree, folder.parent)
        L.write_package(fixture.root, folder)
        return fixture, folder

    def test_a_claim_is_created_once(self):
        fixture = FixtureRoot(self)
        (fixture.root / B.CLAIM).unlink()
        self.assertEqual(L.claim(fixture.root), 'r2s-fixture0001')
        B.require_live(fixture.root)  # the claim the tooling wrote satisfies the gate
        with self.assertRaises(L.LaunchRefused):
            L.claim(fixture.root)

    def test_no_claim_without_valid_approvals(self):
        fixture = FixtureRoot(self)
        (fixture.root / B.CLAIM).unlink()
        (fixture.root / B.COMPUTE).unlink()
        with self.assertRaises(B.LiveRefused):
            L.claim(fixture.root)
        self.assertFalse((fixture.root / B.CLAIM).exists())

    def test_a_submitted_attempt_cannot_be_launched_again_from_any_session(self):
        fixture, folder = self.package()
        backend = FakeBackend()
        L.submit(fixture.root, folder, backend)
        receipt = json.loads((fixture.root / B.RECEIPT).read_text())
        self.assertEqual((receipt['status'], receipt['attempt_id']), ('submitted', 'r2s-fixture0001'))
        fresh = Path(tempfile.mkdtemp()) / 'again'  # a new session/working directory changes nothing
        self.addCleanup(shutil.rmtree, fresh.parent)
        for action in (lambda: L.submit(fixture.root, folder, backend), lambda: L.write_package(fixture.root, fresh),
                       lambda: L.claim(fixture.root)):
            with self.assertRaises(L.LaunchRefused):
                action()
        self.assertEqual(backend.pushes, 1)

    def test_an_uncertain_submission_spends_the_attempt(self):
        fixture, folder = self.package()
        with self.assertRaises(ConnectionError):
            L.submit(fixture.root, folder, FakeBackend(fail=True))
        receipt = json.loads((fixture.root / B.RECEIPT).read_text())
        self.assertEqual(receipt['status'], 'submission_uncertain')
        with self.assertRaises(L.LaunchRefused):
            L.submit(fixture.root, folder, FakeBackend())

    def test_an_interrupted_push_leaves_a_spent_attempt(self):
        fixture, folder = self.package()
        put(fixture.root, B.RECEIPT, {'status': 'submitting', 'attempt_id': 'r2s-fixture0001'})
        with self.assertRaises(L.LaunchRefused):
            L.submit(fixture.root, folder, FakeBackend())

    def test_a_tampered_package_is_not_submitted(self):
        fixture, folder = self.package()
        (folder / 'profile.ipynb').write_bytes(b'{}')
        backend = FakeBackend()
        with self.assertRaises(L.LaunchRefused):
            L.submit(fixture.root, folder, backend)
        self.assertEqual(backend.pushes, 0)
        self.assertFalse((fixture.root / B.RECEIPT).exists())


class ProviderResponses(unittest.TestCase):
    """Review P2 on d494f50: only an unambiguous confirmation of the authorized kernel is recorded as submitted."""

    def submit(self, response):
        fixture = FixtureRoot(self)
        folder = Path(tempfile.mkdtemp()) / 'launch'
        self.addCleanup(shutil.rmtree, folder.parent)
        L.write_package(fixture.root, folder)
        backend = FakeBackend(response=response)
        final = L.submit(fixture.root, folder, backend)
        stored = json.loads((fixture.root / B.RECEIPT).read_text())
        self.assertEqual(final['status'], stored['status'])
        with self.assertRaises(L.LaunchRefused):  # every outcome spends the attempt; no automatic retry
            L.submit(fixture.root, folder, backend)
        self.assertEqual(backend.pushes, 1)
        return stored

    def test_confirmed_submission(self):
        stored = self.submit(CONFIRMED)
        self.assertEqual(stored['status'], 'submitted')
        self.assertNotIn('reconciliation', stored)

    def test_missing_or_ambiguous_confirmation_is_uncertain(self):
        cases = {
            'none': None,
            'empty mapping': {},
            'not a mapping': 'Kernel version 1 successfully pushed',
            'other kernel': dict(CONFIRMED, ref='/code/someone-else/arc3-wheelhouse-r2-smoke-v1'),
            'no reference': {k: v for k, v in CONFIRMED.items() if k != 'ref'},
            'no version': {k: v for k, v in CONFIRMED.items() if k != 'versionNumber'},
            'version zero': dict(CONFIRMED, versionNumber=0),
            'version as text': dict(CONFIRMED, versionNumber='1'),
            'version as bool': dict(CONFIRMED, versionNumber=True),
        }
        for label, response in cases.items():
            with self.subTest(case=label):
                stored = self.submit(response)
                self.assertEqual(stored['status'], 'submission_uncertain', stored['findings'])
                self.assertIn('never relaunch', stored['reconciliation'])

    def test_explicit_provider_rejection_is_recorded_separately(self):
        cases = {
            'invalid dataset sources': {'invalidDatasetSources': ['team/missing']},
            'invalid sources despite a reference': dict(CONFIRMED, invalidModelSources=['qwen-lm/absent']),
            'provider error': dict(CONFIRMED, error='Notebook not found'),
        }
        for label, response in cases.items():
            with self.subTest(case=label):
                stored = self.submit(response)
                self.assertEqual(stored['status'], 'submission_rejected', stored['findings'])

    def test_reference_forms(self):
        for ref in ('/code/' + N.KERNEL_ID, 'code/' + N.KERNEL_ID, N.KERNEL_ID,
                    'https://www.kaggle.com/code/' + N.KERNEL_ID):
            self.assertEqual(L.normalised_ref(ref), N.KERNEL_ID)
        self.assertIsNone(L.normalised_ref('/code/'))


class ScriptedSocketServer:
    """A raw TCP server whose handler controls exactly when bytes are sent."""

    def __init__(self, test, handler):
        import socket
        import threading
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1', 0))
        self.listener.listen(4)
        self.port = self.listener.getsockname()[1]
        self.handler = handler
        test.addCleanup(self.listener.close)
        threading.Thread(target=self.serve, daemon=True).start()

    def serve(self):
        try:
            conn, _ = self.listener.accept()
        except OSError:
            return
        with conn:
            data = b''
            while b'\r\n\r\n' not in data:
                data += conn.recv(65536)
            head, _, rest = data.partition(b'\r\n\r\n')
            length = next((int(x.split(b':')[1]) for x in head.split(b'\r\n') if x.lower().startswith(b'content-length')),
                          0)
            while len(rest) < length:
                rest += conn.recv(65536)
            try:
                self.handler(conn)
            except OSError:
                pass


def trickle(conn, data, interval):
    for i in range(len(data)):
        conn.sendall(data[i:i + 1])
        time.sleep(interval)


CONTENT_LINE = b'data: {"choices": [{"delta": {"content": "1 "}}]}\n\n'


class Deadlines(unittest.TestCase):
    """Review P2: the absolute deadline covers connection, headers and body; late content is rejected."""

    def client(self, port, timeout):
        from certification.wheelhouse_r2_smoke_v1.client import Client
        clock = Clock(PROTOCOL['limits'], time.monotonic())
        plan = [{'id': 'T1', 'kind': 'inference', 'method': 'POST', 'path': '/v1/chat/completions',
                 'timeout_seconds': timeout}]
        return Client('127.0.0.1', port, Ledger(plan, 12, clock), clock, 'served')

    def late(self, handler, timeout, call):
        from certification.wheelhouse_r2_smoke_v1.client import RequestFailed
        server = ScriptedSocketServer(self, handler)
        client = self.client(server.port, timeout)
        begin = time.monotonic()
        with self.assertRaises(RequestFailed) as caught:
            call(client)
        elapsed = time.monotonic() - begin
        self.assertLess(elapsed, timeout + 0.25, f'returned after {elapsed:.3f}s for a {timeout}s deadline')
        self.assertEqual(client.ledger.entries[0]['outcome'], 'failed')
        return str(caught.exception)

    def test_slow_headers(self):
        self.late(lambda c: trickle(c, b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n', 0.05), 0.3,
                  lambda client: client.call('T1', {}))

    def test_slow_body(self):
        body = b'{"padding": "' + b'x' * 60 + b'"}'
        head = b'HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n' % len(body)
        self.late(lambda c: (c.sendall(head), trickle(c, body, 0.02)), 0.3, lambda client: client.call('T1', {}))

    def test_slow_stream_content_is_rejected_when_late(self):
        def handler(conn):
            conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\n\r\n')
            trickle(conn, CONTENT_LINE, 0.007)  # the first full content line completes after ~0.36 s
        self.late(handler, 0.1, lambda client: client.stream_then_cancel('T1', 'stream_then_cancel', {}))

    def test_timely_stream_content_is_accepted(self):
        def handler(conn):
            conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\n\r\n' + CONTENT_LINE)
            time.sleep(1)
        server = ScriptedSocketServer(self, handler)
        result = self.client(server.port, 2).stream_then_cancel('T1', 'stream_then_cancel', {})
        self.assertTrue(result['cancelled'])

    def test_nothing_sent(self):
        self.late(lambda c: time.sleep(2), 0.3, lambda client: client.call('T1', {}))


if __name__ == '__main__':
    unittest.main()
