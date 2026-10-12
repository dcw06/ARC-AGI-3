"""Scored-only process cleanup adapter; frozen study implementations stay intact."""
from contextlib import contextmanager
import os
import signal
import threading
import time

from research.stagnation_supervision_runtime_v2 import procfs, publisher_install
from research.stagnation_supervision_runtime_v2.publisher_process import ModelServer as StudyModelServer, defer_startup_signals


class ModelServer(StudyModelServer):
    probe_seconds = .1

    def _reap(self):
        if self.process.poll() is None or self.pgid is None:
            return
        until = time.monotonic() + self.probe_seconds
        while time.monotonic() < until:
            try:
                pid, _ = os.waitpid(-self.pgid, os.WNOHANG)
            except ChildProcessError:
                return
            if not pid:
                return
            self.reaped_descendants.append(pid)

    def _group_alive(self):
        self._reap()
        return procfs.group_live(self.pgid, budget=self.probe_seconds)

    def stop(self, deadline, terminate_grace, kill_grace):
        receipt = {'groups_absent':False, 'error':None, 'interrupted':[]}
        try:
            with defer_startup_signals():
                receipt = self._stop(deadline, terminate_grace, kill_grace)
        except BaseException as exc:
            receipt['groups_absent'] = False
            receipt['error'] = receipt['error'] or 'cleanup interrupted'
            receipt['interrupted'].append(type(exc).__name__ + ': ' + str(exc)[:120])
            if hasattr(self, '_absence_receipt'):
                self._absence_receipt = dict(receipt)
        return receipt

    def _stop(self, deadline, terminate_grace, kill_grace):
        if hasattr(self, '_absence_receipt'):
            return dict(self._absence_receipt)  # never signal a reused numeric PGID
        receipt = dict(pgid=self.pgid, ownership=self.ownership, sigterm_sent=False,
                       sigkill_sent=False, groups_absent=False, remaining_members=None,
                       interrupted=[], error=None)
        if self.process is None:
            receipt['groups_absent'] = self.ownership == 'never_spawned'
            if not receipt['groups_absent']:
                receipt['error'] = 'spawn ownership uncertain; no child handle'
            if hasattr(self, '_log'):
                self._log.close()
            return receipt
        self.pgid = self.pgid or self.process.pid  # start_new_session=True
        receipt['pgid'] = self.pgid
        if self.pgid != self.process.pid or self.pgid == os.getpgrp():
            receipt['error'] = 'unsafe process group; refusing to signal'
            if hasattr(self, '_log'):
                self._log.close()
            return receipt

        def problem(exc):
            receipt['interrupted'].append(type(exc).__name__ + ': ' + str(exc)[:120])
            receipt['error'] = receipt['error'] or 'cleanup probe or termination failed'

        def send(signum, key):
            try:
                os.killpg(self.pgid, signum)
                receipt[key] = True
            except ProcessLookupError:
                pass

        observed_absent = False

        def wait(until):
            nonlocal observed_absent
            while time.monotonic() < until:
                if not self._group_alive():
                    self._reap()
                    observed_absent = self.process.returncode is not None
                    return
                time.sleep(min(.02, max(0, until-time.monotonic())))

        try:
            try:
                # No census is allowed to delay the first termination signal.
                send(signal.SIGTERM, 'sigterm_sent')
                wait(min(deadline, time.monotonic()+terminate_grace))
            except BaseException as exc:
                problem(exc)
            finally:
                # Escalation does not depend on a successful census or remaining
                # lifecycle time. Emergency killing remains possible on overrun.
                try:
                    if not observed_absent:
                        send(signal.SIGKILL, 'sigkill_sent')
                        wait(time.monotonic()+kill_grace)
                except BaseException as exc:
                    problem(exc)
            try:
                absent = observed_absent or not self._group_alive()
                if absent:
                    self._reap()
                receipt['groups_absent'] = (absent and self.ownership == 'registered'
                                           and self.process.returncode is not None and receipt['error'] is None)
                receipt['exit_code'] = self.process.returncode
                receipt['reaped_descendants'] = sorted(self.reaped_descendants)
                if self.ownership != 'registered':
                    receipt['error'] = 'spawn ownership uncertain; emergency termination attempted'
                if absent:
                    # Retain a failed receipt too: observed absence is terminal,
                    # while a probe error still prevents successful certification.
                    self._absence_receipt = dict(receipt)
            except BaseException as exc:
                problem(exc)
        finally:
            if hasattr(self, '_log'):
                self._log.close()
        return receipt


@contextmanager
def bounded_installation_processes():
    """Select this owner for the unchanged split installer's commands.

    Installation is synchronous on the main thread, before server/worker startup.
    Only its process factory is adapted, and restored even on interruption; no
    frozen installer source or installation requirements are edited.
    """
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError('split installation must run on the main thread')
    original = publisher_install.ModelServer
    try:
        publisher_install.ModelServer = ModelServer
        yield
    finally:
        publisher_install.ModelServer = original
