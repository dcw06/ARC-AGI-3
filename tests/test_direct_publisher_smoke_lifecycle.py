"""CPU regressions for review findings on 9073068; no provider or GPU work."""
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import shutil
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from certification.direct_publisher_smoke_v1 import run as R, server as S
from certification.direct_publisher_smoke_v1.binding import load_protocol
from certification.direct_publisher_smoke_v1.evidence import Evidence


class StartupOwnership(unittest.TestCase):
    def interrupt(self, boundary, *, signal_interrupt=True):
        original_spawn, original_group = subprocess.Popen, os.getpgid
        child = None
        previous = signal.getsignal(signal.SIGALRM)

        def raise_cutoff(*_):
            raise TimeoutError('cutoff at startup ownership boundary')

        def cutoff():
            if signal_interrupt:
                signal.raise_signal(signal.SIGALRM)
            else:
                raise_cutoff()

        def spawn(*args, **kwargs):
            nonlocal child
            child = original_spawn(*args, **kwargs)
            if boundary == 'before_assignment':
                cutoff()
            return child

        def register(pid):
            if boundary == 'before_group_registration':
                cutoff()
            return original_group(pid)

        with tempfile.TemporaryDirectory() as folder:
            model = S.ModelServer([sys.executable, '-c', 'import time; time.sleep(30)'], {},
                                  Path(folder) / 'server.log', '127.0.0.1', 1)
            signal.signal(signal.SIGALRM, raise_cutoff)
            try:
                with patch.object(S.subprocess, 'Popen', spawn), patch.object(S.os, 'getpgid', register):
                    with self.assertRaises(TimeoutError):
                        model.start()
                receipt = model.stop(time.monotonic() + 1, 0.1, 0.1)
                alive = child.poll() is None
                if signal_interrupt:
                    self.assertFalse(alive, receipt)
                    self.assertTrue(receipt['groups_absent'], receipt)
                    self.assertIsNotNone(model.process)
                    self.assertEqual(model.pgid, child.pid)
                else:
                    # An exception inside Popen can hide a child. Never claim absence from a missing handle.
                    self.assertFalse(receipt['groups_absent'], receipt)
                    self.assertEqual(receipt['ownership'], 'uncertain')
                    if boundary == 'before_group_registration':
                        self.assertFalse(alive, receipt)
            finally:
                signal.signal(signal.SIGALRM, previous)
                if child is not None:
                    if child.poll() is None:
                        os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=5)
                if hasattr(model, '_log'):
                    model._log.close()

    def test_original_reproduction_interrupt_before_assignment(self):
        self.interrupt('before_assignment')

    def test_interrupt_before_group_registration(self):
        self.interrupt('before_group_registration')

    def test_unknown_spawn_outcome_never_reports_absence(self):
        self.interrupt('before_assignment', signal_interrupt=False)

    def test_uncertain_group_registration_still_attempts_emergency_termination(self):
        self.interrupt('before_group_registration', signal_interrupt=False)

    def test_definitely_never_spawned_reports_absence(self):
        model = S.ModelServer([], {}, Path('/unused'), '127.0.0.1', 1)
        receipt = model.stop(time.monotonic() + 1, 0.1, 0.1)
        self.assertTrue(receipt['groups_absent'])
        self.assertEqual(receipt['ownership'], 'never_spawned')

    def test_child_still_handles_sigterm_after_protected_start(self):
        with tempfile.TemporaryDirectory() as folder:
            model = S.ModelServer([sys.executable, '-c', 'import time; time.sleep(30)'], {},
                                  Path(folder) / 'server.log', '127.0.0.1', 1)
            try:
                model.start()
                receipt = model.stop(time.monotonic() + 1, 0.3, 0.3)
                self.assertTrue(receipt['groups_absent'])
                self.assertTrue(receipt['sigterm_sent'])
                self.assertFalse(receipt['sigkill_sent'])
            finally:
                if model.process and model.process.poll() is None:
                    os.killpg(model.process.pid, signal.SIGKILL)
                    model.process.wait(timeout=5)

    def test_emergency_sigkill_still_runs_after_cleanup_deadline(self):
        with tempfile.TemporaryDirectory() as folder:
            ready = Path(folder) / 'ready'
            code = ('import signal,time,pathlib; signal.signal(signal.SIGTERM,signal.SIG_IGN); '
                    f'pathlib.Path({str(ready)!r}).touch(); time.sleep(30)')
            model = S.ModelServer([sys.executable, '-c', code], {}, Path(folder) / 'log', '127.0.0.1', 1)
            try:
                model.start()
                ceiling = time.monotonic() + 3
                while not ready.exists() and time.monotonic() < ceiling:
                    time.sleep(0.01)
                self.assertTrue(ready.exists())
                receipt = model.stop(time.monotonic() - 1, 0.1, 0.3)
                self.assertTrue(receipt['sigkill_sent'])
                self.assertTrue(receipt['groups_absent'])
            finally:
                if model.process and model.process.poll() is None:
                    os.killpg(model.process.pid, signal.SIGKILL)
                    model.process.wait(timeout=5)


class LifecycleDeadline(unittest.TestCase):
    def exercise(self, *, slow_stop=False, gpu_delay=False, evidence_delay=False, cleanup_delay=False,
                 publication_delay=False, cleanup_failure=False, evidence_failure=False, via_live_entry=False,
                 publication_failure=False):
        protocol = copy.deepcopy(load_protocol())
        protocol['limits'].update(internal_seconds=0.15, admission_cutoff_seconds=0.1,
                                  cleanup_reserve_seconds=0.05)

        class Server:
            def __init__(self, *a):
                pass
            def start(self):
                return 1
            def wait_ready(self, deadline):
                return 0
            def stop(self, *a):
                if slow_stop:
                    time.sleep(0.2)
                return {'groups_absent': True}

        class Client:
            def __init__(self, *a):
                pass
            def call(self, request_id):
                return 200, json.dumps({'data': [{'id': protocol['server']['served_model_name']}]}).encode()
            def completion(self, *a):
                return {'content': 'READY'}
            def stream_then_cancel(self, *a):
                return {'cancelled': True}
            def idle_after_cancel(self, *a):
                return {'idle': True}

        original_finalize = Evidence.finalize
        def finalize(instance, result):
            if evidence_delay or (publication_delay and result.get('passed')):
                time.sleep(0.2)
            if evidence_failure:
                raise OSError('scripted evidence failure')
            value = original_finalize(instance, result)
            if publication_failure and result.get('passed'):
                raise OSError('scripted failure after writing passing result')
            return value

        def gpu_cleanup(*a):
            if gpu_delay:
                time.sleep(0.2)
            return {'gpu_cleanup_verified': True}

        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            def remove_environment():
                if cleanup_delay:
                    time.sleep(0.2)
                if cleanup_failure:
                    raise OSError('scripted environment removal failure')
                (base / 'work').rmdir()

            with patch.object(R.host, 'host_facts', return_value={}), \
                 patch.object(R, 'verify_bundle', return_value={}), \
                 patch.object(R, 'install', return_value={'python': sys.executable}), \
                 patch.object(R, 'ModelServer', Server), patch.object(R, 'Client', Client), \
                 patch.object(R.host, 'gpu_facts', return_value={'uuid': 'fixture-gpu'}), \
                 patch.object(R.host, 'gpu_sample', return_value={}), \
                 patch.object(R.host, 'gpu_cleanup', side_effect=gpu_cleanup), \
                 patch.object(Evidence, 'finalize', finalize):
                kwargs = {} if slow_stop else {'on_environment_cleanup': remove_environment}
                if gpu_delay:
                    kwargs['gpu_query'] = lambda *a: []
                if via_live_entry:
                    source = base / 'source'
                    source.mkdir()
                    original_run = R.run
                    def scripted_run(mode, *args, **options):
                        # Exercise the live entrypoint's callbacks with the scripted control code only.
                        return original_run('rehearsal', *args, **options)
                    def remove_source():
                        if cleanup_delay:
                            time.sleep(0.2)
                        shutil.rmtree(source)
                    from certification.direct_publisher_smoke_v1 import binding
                    with patch.object(binding, 'require_live', return_value=(protocol, {'attempt_id': 'fixture'})), \
                         patch.object(R.host, 'dataset_mount', return_value=base / 'bundle'), \
                         patch.object(R.host, 'verify_model', return_value={}), \
                         patch.object(R, 'run', scripted_run):
                        result = R.live_main(source, base / 'evidence', time.monotonic(), base,
                                             on_source_cleanup=remove_source)
                    self.assertFalse(source.exists())
                    self.assertFalse(list(base.glob('direct-publisher-smoke-*')))
                    return result, False
                if evidence_failure or publication_failure:
                    with self.assertRaises(OSError):
                        R.run('rehearsal', protocol, base / 'evidence', time.monotonic(),
                              bundle=base / 'bundle', workdir=base / 'work', model_check=lambda c: {}, **kwargs)
                    if publication_failure:
                        retained = json.loads((base / 'evidence/result.json').read_bytes())
                        self.assertFalse(retained['passed'])
                        self.assertFalse(retained['gpu_compatibility_evidence'])
                    return
                result = R.run('rehearsal', protocol, base / 'evidence', time.monotonic(),
                               bundle=base / 'bundle', workdir=base / 'work', model_check=lambda c: {}, **kwargs)
            retained = json.loads((base / 'evidence/result.json').read_bytes())
            self.assertEqual(result, retained)
            manifest = json.loads((base / 'evidence/evidence-manifest.json').read_bytes())
            import hashlib
            for name, digest in manifest['files'].items():
                self.assertEqual(hashlib.sha256((base / 'evidence' / name).read_bytes()).hexdigest(), digest)
            return result, base.joinpath('work').exists()

    def failed(self, **kwargs):
        result, _ = self.exercise(**kwargs)
        self.assertFalse(result['passed'], result)
        self.assertFalse(result['gpu_compatibility_evidence'])
        self.assertFalse(result['lifecycle_deadline']['met'])
        self.assertGreaterEqual(result['elapsed_seconds'], result['limits']['internal_seconds'])

    def test_original_reproduction_cleanup_overrun(self):
        result, _ = self.exercise(slow_stop=True)
        self.assertFalse(result['passed'], result)

    def test_gpu_cleanup_overrun(self):
        self.failed(gpu_delay=True)

    def test_evidence_finalization_overrun(self):
        self.failed(evidence_delay=True)

    def test_environment_removal_overrun(self):
        self.failed(cleanup_delay=True)

    def test_final_publication_overrun_is_downgraded_and_rehashed(self):
        self.failed(publication_delay=True)

    def test_environment_removal_failure_is_failed(self):
        result, exists = self.exercise(cleanup_failure=True)
        self.assertFalse(result['passed'])
        self.assertTrue(exists)
        self.assertFalse(result['cleanup']['environment']['removed'])

    def test_success_requires_environment_removed_and_final_check(self):
        result, exists = self.exercise()
        self.assertTrue(result['passed'], result)
        self.assertFalse(exists)
        self.assertTrue(result['lifecycle_deadline']['met'])
        self.assertTrue(result['cleanup']['environment']['removed'])

    def test_evidence_write_failure_cannot_return_success(self):
        self.exercise(evidence_failure=True)

    def test_partially_published_success_is_replaced_with_failure(self):
        self.exercise(publication_failure=True)

    def test_live_entry_removes_environment_and_source_before_success(self):
        result, _ = self.exercise(via_live_entry=True)
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['cleanup']['environment']['details'],
                         {'temporary_environment_removed': True, 'embedded_source_removed': True})

    def test_live_entry_source_removal_overrun_fails(self):
        self.failed(via_live_entry=True, cleanup_delay=True)
