"""Model-server process lifecycle: own process group, TCP-only readiness within the startup ceiling, and group
termination (SIGTERM, then SIGKILL) with verification that no member of the group remains."""
import os
import signal
import socket
import subprocess
import time
from pathlib import Path


class StartupFailed(RuntimeError):
    pass


def argv_for(server, python, model_path, port):
    values = {'{python}': str(python), '{model_path}': str(model_path), '{port}': str(port)}
    return [values.get(item, item) for item in server['argv']]


def group_members(pgid, proc=Path('/proc')):
    """PIDs whose process group is `pgid` (Linux /proc scan; zombies included until reaped)."""
    members = []
    for entry in proc.iterdir() if proc.is_dir() else []:
        if entry.name.isdigit():
            try:
                fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
            except (OSError, IndexError):
                continue
            if int(fields[2]) == pgid:
                members.append(int(entry.name))
    return sorted(members)


class ModelServer:
    def __init__(self, argv, env, log, host, port):
        self.argv, self.env, self.log_path, self.host, self.port = argv, env, Path(log), host, port
        self.process = self.pgid = None
        self.events = []

    def start(self):
        env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV')}
        env.update(self.env)
        self._log = self.log_path.open('ab')
        self.process = subprocess.Popen(self.argv, env=env, stdout=self._log, stderr=subprocess.STDOUT,
                                        stdin=subprocess.DEVNULL, start_new_session=True)
        self.pgid = os.getpgid(self.process.pid)
        self.events.append({'event': 'started', 'pid': self.process.pid, 'pgid': self.pgid})
        return self.process.pid

    def wait_ready(self, deadline, interval=1.0):
        """Poll a TCP connection (no HTTP request) until the port accepts, the process exits, or the deadline."""
        begin = time.monotonic()
        while True:
            if self.process.poll() is not None:
                raise StartupFailed(f'model server exited with {self.process.returncode} before readiness')
            try:
                with socket.create_connection((self.host, self.port), timeout=1):
                    self.events.append({'event': 'ready', 'seconds': round(time.monotonic() - begin, 3)})
                    return time.monotonic() - begin
            except OSError:
                pass
            if time.monotonic() >= deadline:
                raise StartupFailed('model startup ceiling reached before readiness')
            time.sleep(min(interval, max(0.0, deadline - time.monotonic())))

    def stop(self, deadline, terminate_grace, kill_grace):
        """Terminate the whole group and verify it is gone; returns a receipt and never raises. The SIGKILL
        escalation and the reap run in `finally` blocks: an interruption during the SIGTERM grace (for example a
        stray alarm) is recorded and cannot skip the kill. The kill phase keeps its own grace even if the SIGTERM
        phase used up the shared deadline."""
        receipt = {'pgid': self.pgid, 'sigterm_sent': False, 'sigkill_sent': False, 'groups_absent': False,
                   'remaining_members': None, 'interrupted': [], 'error': None}
        if self.process is None:
            receipt['groups_absent'] = True
            return receipt

        def wait(until):
            while time.monotonic() < until and self._group_alive():
                time.sleep(0.1)
        try:
            try:
                if self._group_alive():
                    os.killpg(self.pgid, signal.SIGTERM)
                    receipt['sigterm_sent'] = True
                    wait(min(time.monotonic() + terminate_grace, deadline))
            except ProcessLookupError:
                pass
            except BaseException as exc:  # noqa: B036 - must not bypass escalation
                receipt['interrupted'].append(f'sigterm phase: {type(exc).__name__}: {str(exc)[:120]}')
            finally:
                for attempt in range(2):  # retried once if the kill phase itself is interrupted
                    try:
                        if self._group_alive():
                            os.killpg(self.pgid, signal.SIGKILL)
                            receipt['sigkill_sent'] = True
                            wait(time.monotonic() + kill_grace)
                        break
                    except ProcessLookupError:
                        break
                    except BaseException as exc:  # noqa: B036
                        receipt['interrupted'].append(f'sigkill phase: {type(exc).__name__}: {str(exc)[:120]}')
        finally:
            try:
                self.process.poll()
                remaining = group_members(self.pgid)
                receipt['remaining_members'] = remaining
                receipt['groups_absent'] = not remaining and not self._group_alive()
                receipt['exit_code'] = self.process.returncode
            except BaseException as exc:  # noqa: B036
                receipt['error'] = f'{type(exc).__name__}: {str(exc)[:256]}'
            try:
                self._log.close()
            except OSError:
                pass
        self.events.append({'event': 'stopped', **{k: receipt[k] for k in ('sigterm_sent', 'sigkill_sent',
                                                                        'groups_absent', 'interrupted')}})
        return receipt

    def _group_alive(self):
        self.process.poll()  # reap the leader if it exited
        try:
            os.killpg(self.pgid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return bool(group_members(self.pgid))
