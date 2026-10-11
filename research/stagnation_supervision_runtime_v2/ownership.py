"""Recoverable worker/monitor ownership, including supervisor death during startup.

A bootstrap inherits the supervisor's group. Before setsid or exec it durably
publishes its future group id. Outer cleanup first stops the supervisor group,
then scans these fixed recovery records, so no child can detach unseen.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from certification.phase4_integrated_v2.evidence import EvidenceStore
from research.stagnation_supervision_runtime_v2.publisher_process import defer_startup_signals

ROLES = ('worker', 'monitor')


def _read(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 8192:
        raise ValueError('missing or unsafe child ownership record')
    return json.loads(path.read_bytes())


def recovery_inventory(output, supervisor_pid):
    """Call only after stopping the supervisor group, when child creation is frozen.

    Recovery records are used for termination even when the parent journal is
    incomplete. Such uncertainty never certifies groups_absent.
    """
    folder = Path(output) / 'control'
    groups, certain, records = [supervisor_pid], True, {}
    for role in ROLES:
        path = folder / ('ownership-' + role + '.json')
        if path.exists() or path.is_symlink():
            try:
                record = _read(path)
                pid = record['pgid']
                if (record['role'] != role or record['supervisor_pgid'] != supervisor_pid
                        or type(pid) is not int or pid <= 0 or pid in (supervisor_pid, os.getpgrp())):
                    raise ValueError('child ownership identity mismatch')
                records[role] = record
                if pid not in groups:
                    groups.append(pid)
            except (OSError, ValueError, KeyError, TypeError):
                certain = False
    try:
        journal = _read(folder / 'ownership.json')
        if journal.get('version') != 1 or journal.get('supervisor_pgid') != supervisor_pid:
            raise ValueError('supervisor ownership journal missing')
        for role in ROLES:
            state = journal['children'][role]
            if state['state'] == 'never_spawned':
                if role in records or state.get('pgid') is not None:
                    certain = False
            elif state['state'] == 'registered':
                child = records.get(role, {})
                if (child.get('pgid') != state.get('pgid') or child.get('nonce') != journal['nonce']
                        or child.get('first_cell_monotonic') != journal['first_cell_monotonic']
                        or journal.get(role + '_pgid') != state.get('pgid')):
                    certain = False
            else:
                certain = False
    except (OSError, ValueError, KeyError, TypeError):
        certain = False
    return groups, certain


class ChildOwners:
    def __init__(self, output, started, nonce):
        self.output = Path(output)
        self.control = EvidenceStore(output, 'control')
        self.processes = {}
        self.journal = {'version': 1, 'supervisor_pgid': os.getpgrp(), 'nonce': nonce,
                        'first_cell_monotonic': started,
                        'children': {role: {'state': 'never_spawned', 'pgid': None} for role in ROLES}}

    def save(self):
        self.control.save('ownership.json', self.journal)

    def start(self, role, argv, *, spawn, cwd, env, pass_fds):
        with defer_startup_signals():
            state = self.journal['children'][role]
            if state['state'] != 'never_spawned':
                raise ValueError('child launch cannot be retried')
            state['state'] = 'uncertain'
            self.save()  # durable intent before entering process creation
            command = [sys.executable, '-m', __name__, '--owned-exec', role, str(self.output),
                       str(os.getpid()), str(os.getpgrp()), str(self.journal['first_cell_monotonic']),
                       self.journal['nonce'], '--', *argv]
            process = spawn(command, cwd=cwd, env=env, pass_fds=pass_fds, start_new_session=False,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.processes[role] = process
            until = time.monotonic() + 10
            path = self.output / 'control' / ('ownership-' + role + '.json')
            while True:
                if path.exists():
                    record = _read(path)
                    if (record.get('pgid') != process.pid or record.get('role') != role
                            or record.get('supervisor_pgid') != os.getpgrp()
                            or record.get('nonce') != self.journal['nonce']):
                        raise ValueError('unbacked child ownership')
                    try:
                        detached = os.getpgid(process.pid) == process.pid
                    except ProcessLookupError:
                        detached = False
                    if detached:
                        break
                if process.poll() is not None or time.monotonic() >= until:
                    raise RuntimeError('child exited or stalled before ownership registration')
                time.sleep(.01)
            state.update(state='registered', pgid=process.pid)
            self.journal[role + '_pgid'] = process.pid
            self.save()  # recoverable per child, before the next launch or thread startup
            return process

    def stop(self):
        from scripts.run_grounded_action_v1_engine_local import terminate_group, group_exited
        errors = []
        with defer_startup_signals():
            for role in ROLES:
                process = self.processes.get(role)
                if process is not None:
                    try:
                        # A failed bootstrap may still be in our group: terminate its
                        # immediate PID without ever signalling the supervisor itself.
                        if process.poll() is None and os.getpgid(process.pid) != process.pid:
                            process.kill()
                            process.wait(timeout=5)
                        terminate_group(process, grace=.5, verification_seconds=3)
                    except BaseException as exc:
                        errors.append(role + ': ' + type(exc).__name__)
            groups, certain = recovery_inventory(self.output, os.getpgrp())
            # A Popen outcome without a handle can still have a durable child record.
            from research.stagnation_supervision_runtime_v2.launch import _stop_group
            for pgid in groups[1:]:
                try:
                    if not _stop_group(pgid):
                        errors.append('child group remains: ' + str(pgid))
                except BaseException as exc:
                    errors.append('child cleanup: ' + type(exc).__name__)
            absent = certain and not errors and all(group_exited(p) for p in groups[1:])
        return absent, errors


def owned_exec(arguments):
    role, output, parent, parent_group, started, nonce, separator, *command = arguments
    parent, parent_group = int(parent), int(parent_group)
    if role not in ROLES or separator != '--' or not command or os.getppid() != parent or os.getpgrp() != parent_group:
        raise ValueError('invalid owned child bootstrap')
    store = EvidenceStore(output, 'control')
    path = store.save('ownership-' + role + '.json', {
        'role': role, 'pgid': os.getpid(), 'supervisor_pgid': parent_group,
        'first_cell_monotonic': float(started), 'nonce': nonce})
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)  # persist the directory entry before any separately grouped process exists
    finally:
        os.close(fd)
    if os.getppid() != parent:
        raise RuntimeError('supervisor died before child detach')
    os.setsid()
    if os.getppid() != parent:
        raise RuntimeError('supervisor died before child exec')
    os.execvpe(command[0], command, os.environ)


if __name__ == '__main__':
    if sys.argv[1:2] != ['--owned-exec']:
        raise SystemExit('owned bootstrap only')
    owned_exec(sys.argv[2:])
