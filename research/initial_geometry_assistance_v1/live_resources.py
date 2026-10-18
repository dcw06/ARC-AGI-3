"""Owned groups plus an independent, non-census hard-deadline watchdog."""
import multiprocessing
import os
from pathlib import Path
import signal
import subprocess
import time

from certification.direct_publisher_smoke_v1.install import InstallationProcesses
from certification.direct_publisher_smoke_v1.server import ModelServer, defer_startup_signals


def environment(host=None):
    host = os.environ if host is None else host
    value = host.get('LD_LIBRARY_PATH', '')
    if type(value) is not str or len(value) > 16384 or '\0' in value or '\n' in value:
        raise ValueError('driver loader path contract')
    parts = value.split(os.pathsep)
    if len(parts) > 64:
        raise ValueError('driver loader path inventory')
    paths = list(dict.fromkeys(p for p in parts if p and os.path.isabs(p)))
    env = {'PATH': host.get('PATH', os.defpath), 'PYTHONNOUSERSITE': '1', 'PIP_NO_INDEX': '1',
           'PIP_CONFIG_FILE': os.devnull, 'PIP_DISABLE_PIP_VERSION_CHECK': '1', 'HF_HUB_OFFLINE': '1',
           'TRANSFORMERS_OFFLINE': '1', 'HF_HUB_DISABLE_TELEMETRY': '1', 'MPLBACKEND': 'Agg',
           'TOKENIZERS_PARALLELISM': 'false', 'TRANSFORMERS_NO_TF': '1', 'USE_TF': '0',
           'VLLM_NO_USAGE_STATS': '1', 'CUDA_VISIBLE_DEVICES': '0'}
    if paths:
        env['LD_LIBRARY_PATH'] = os.pathsep.join(paths)
    # No account credentials, home directory or hub tokens enter child interpreters.
    return env


def _watch(parent, deadline, groups, done):
    if not done.wait(max(0, deadline-time.monotonic())):
        # No /proc scan, no Python cleanup callback, no wait for graceful exit.
        for pgid in groups:
            if pgid > 0:
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        try:
            os.kill(parent, signal.SIGKILL)
        except ProcessLookupError:
            pass


class HardDeadline:
    def __init__(self, deadline):
        if os.name != 'posix' or not Path('/proc').is_dir():
            raise ValueError('Linux process ownership required')
        ctx = multiprocessing.get_context('spawn')
        self.groups = ctx.RawArray('q', 64)
        self.done = ctx.Event()
        self.deadline = deadline
        self.process = ctx.Process(target=_watch, args=(os.getpid(), deadline, self.groups, self.done))
        self.process.daemon = False

    def start(self):
        with defer_startup_signals():
            self.process.start()

    def register(self, group):
        if group.pgid is None or group.ownership != 'registered':
            raise ValueError('uncertain ownership cannot be registered as absent')
        for i, value in enumerate(self.groups):
            if value == 0:
                self.groups[i] = group.pgid
                return i
        raise ValueError('owned process inventory full')

    def clear(self, slot, receipt):
        if receipt.get('groups_absent') is not True:
            raise ValueError('cannot forget a live/uncertain group')
        self.groups[slot] = 0

    def close(self):
        if any(self.groups):
            raise ValueError('hard watchdog still owns groups')
        if time.monotonic() >= self.deadline:
            raise TimeoutError('hard deadline reached')
        self.done.set()
        self.process.join(timeout=min(2, self.deadline-time.monotonic()))
        if self.process.is_alive() or self.process.exitcode != 0:
            raise RuntimeError('hard watchdog did not stop cleanly')


class Processes(InstallationProcesses):
    def __init__(self, watchdog):
        super().__init__(terminate_grace=0.2, kill_grace=1)
        self.watchdog = watchdog

    def command(self, argv, log, deadline, env, what):
        if time.monotonic() >= deadline:
            raise TimeoutError(what + ': command admission closed')
        with Path(log).open('ab') as stream:
            stream.write(('\n$ '+' '.join(map(str, argv))+'\n').encode())
            offset = stream.tell()
        entry = None
        # spawn appends its owner before Popen, even if it never returns.
        try:
            entry = self.spawn(argv, log, env, what)
            code = entry['group'].process.wait(timeout=max(0.001, deadline-time.monotonic()))
        finally:
            if entry is not None:
                cleanup = self._stop_group(entry, deadline)
        if not cleanup['groups_absent'] or cleanup.get('interrupted') or time.monotonic() >= deadline:
            raise RuntimeError(what + ': command lifecycle not verified within deadline')
        with Path(log).open('rb') as stream:
            stream.seek(0, os.SEEK_END)
            stream.seek(max(offset, stream.tell()-2*1024*1024))
            text = stream.read().decode('utf-8', errors='replace')
        if code:
            raise RuntimeError(what + ': command exited '+str(code)+': '+text[-300:])
        return subprocess.CompletedProcess(argv, code, stdout=text, stderr='')

    def _stop_group(self, entry, deadline):
        result = super()._stop_group(entry, deadline)
        if result['groups_absent'] and 'watch_slot' in entry:
            self.watchdog.clear(entry.pop('watch_slot'), result)
        return result

    def spawn(self, argv, log, env, what):
        entry = {'phase': what, 'group': ModelServer(argv, env, log, None, None, inherit_env=False)}
        self.groups.append(entry)
        with defer_startup_signals():
            self._adopt_descendants()
            entry['group'].start()
            entry['watch_slot'] = self.watchdog.register(entry['group'])
        return entry
