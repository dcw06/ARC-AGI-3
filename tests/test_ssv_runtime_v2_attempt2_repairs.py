"""r6 repairs after session-1 attempt 2 and its independent review (CPU only; real POSIX processes; no GPU/provider).

1. procfs: /proc group probes with ps-equivalent coverage, a hard budget, a census, never a partial or zero result.
2. launch cleanup: a failed cleanup query can no longer skip the recovery of detached children (reproduced P1).
3. ownership cleanup: failed checks still SIGKILL every recovered owned group; absence is never certified.
4. monitor warm-up: a failed warm-up names its probe and elapsed time; a /proc census reaches the failure receipt.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

LINUX = sys.platform == 'linux'


def wait_until(predicate, seconds=10):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        if predicate():
            return True
        time.sleep(.05)
    return predicate()


def kill_group(pgid):
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


@unittest.skipUnless(LINUX, '/proc')
class ProcfsProbes(unittest.TestCase):
    def spawn_group(self, extra_session_child=True):
        code = ('import subprocess, sys, time\n'
                'kids = [subprocess.Popen([sys.executable, "-c", "import time; x = bytearray(4 << 20); time.sleep(60)"])'
                ' for _ in range(2)]\n'
                + ('other = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)\n'
                   'print(other.pid, flush=True)\n' if extra_session_child else 'print(0, flush=True)\n')
                + 'time.sleep(60)\n')
        leader = subprocess.Popen([sys.executable, '-c', code], start_new_session=True, stdout=subprocess.PIPE, text=True)
        other = int(leader.stdout.readline())
        self.addCleanup(lambda: (kill_group(leader.pid), other and kill_group(other), leader.wait(timeout=5)))
        from research.stagnation_supervision_runtime_v2 import procfs
        self.assertTrue(wait_until(lambda: procfs.scan(leader.pid, 2)[1]['members'] == 3))
        return leader, other

    def test_group_rss_matches_ps_and_covers_every_member(self):
        from research.stagnation_supervision_runtime_v2 import procfs
        leader, other = self.spawn_group()

        def reference():
            result = subprocess.run(['ps', '-axo', 'pgid=,rss='], capture_output=True, text=True, check=True)
            return sum(int(parts[1]) * 1024 for line in result.stdout.splitlines()
                       if len(parts := line.split()) == 2 and int(parts[0]) == leader.pid)
        readings = []

        def steady():  # compare once the children have finished starting and allocating
            readings.append(procfs.group_rss(leader.pid))
            return len(readings) > 2 and readings[-1][0] == readings[-2][0] == readings[-3][0]
        self.assertTrue(wait_until(steady))
        value, census = readings[-1]
        self.assertEqual(census['members'], 3)  # the leader and both children, not the other session
        self.assertGreater(value, 8 << 20)
        self.assertLess(abs(value - reference()), 1 << 20)
        self.assertNotIn('names', json.dumps(census))

    def test_a_scan_over_budget_raises_with_a_census_and_never_returns_zero(self):
        from research.stagnation_supervision_runtime_v2 import procfs
        leader, _ = self.spawn_group(extra_session_child=False)

        def slow(pid):
            time.sleep(.05)
            return procfs.read_stat(pid)
        with self.assertRaises(procfs.ScanBudgetExceeded) as caught:
            procfs.group_rss(leader.pid, .01, read=slow)
        census = caught.exception.census
        self.assertGreaterEqual(census['stat_reads'], 1)
        self.assertGreater(census['slowest_read_seconds'], .04)
        self.assertGreater(census['elapsed_seconds'], .01)
        self.assertEqual(set(census), {'budget_seconds', 'entries', 'stat_reads', 'vanished', 'members', 'member_states',
                                       'slowest_read_seconds', 'list_seconds', 'elapsed_seconds'})

    def test_zombies_are_not_live_members(self):
        from research.stagnation_supervision_runtime_v2 import procfs
        leader = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], start_new_session=True)
        self.addCleanup(lambda: (kill_group(leader.pid), leader.poll() is None or True))
        self.assertTrue(wait_until(lambda: procfs.group_live(leader.pid)))
        os.kill(leader.pid, signal.SIGKILL)
        self.assertTrue(wait_until(lambda: not procfs.group_live(leader.pid)))  # an unreaped zombie remains
        self.assertEqual(procfs.scan(leader.pid, 2)[1]['member_states'], {'Z': 1})
        leader.wait(timeout=5)

    def test_command_names_with_spaces_and_parentheses_parse(self):
        from research.stagnation_supervision_runtime_v2 import procfs
        code = 'open("/proc/self/comm", "w").write("a) (b c"); import time; time.sleep(60)'
        child = subprocess.Popen([sys.executable, '-c', code], start_new_session=True)
        self.addCleanup(lambda: (kill_group(child.pid), child.wait(timeout=5)))
        self.assertTrue(wait_until(lambda: open(f'/proc/{child.pid}/comm').read().startswith('a) (b')))
        state, group, pages = procfs.read_stat(child.pid)
        self.assertEqual((group, state in 'RS'), (child.pid, True))
        self.assertGreater(pages, 0)


FAKE_SUPERVISOR = r'''
import json, os, subprocess, sys, time
control = os.path.join(sys.argv[1], 'control')
os.makedirs(control, exist_ok=True)
nonce, started, kids = 'n' * 64, 1.0, {}
for role, ignore in (('worker', True), ('monitor', False)):
    code = ('import signal, time\n' + ('signal.signal(signal.SIGTERM, signal.SIG_IGN)\n' if ignore else '')
            + 'time.sleep(120)\n')
    kids[role] = subprocess.Popen([sys.executable, '-c', code], start_new_session=True).pid
    with open(os.path.join(control, 'ownership-' + role + '.json'), 'w') as stream:
        json.dump({'role': role, 'pgid': kids[role], 'supervisor_pgid': os.getpgrp(), 'first_cell_monotonic': started,
                   'nonce': nonce}, stream)
with open(os.path.join(control, 'ownership.json'), 'w') as stream:
    json.dump({'version': 1, 'supervisor_pgid': os.getpgrp(), 'nonce': nonce, 'first_cell_monotonic': started,
               'children': {r: {'state': 'registered', 'pgid': p} for r, p in kids.items()},
               **{r + '_pgid': p for r, p in kids.items()}}, stream)
print(json.dumps(kids), flush=True)
time.sleep(120)
'''


@unittest.skipUnless(LINUX, 'real POSIX process groups')
class LaunchCleanupFaults(unittest.TestCase):
    """The reviewer's reproduction: the first cleanup query timing out, or every query timing out, used to leave the
    detached worker and monitor groups unsignalled."""

    def exercise(self, fault):
        from research.stagnation_supervision_runtime_v2 import launch, procfs
        real = launch._group_exited
        calls = []

        def checked(pgid):
            calls.append(pgid)
            if fault == 'every' or (fault == 'first' and len(calls) == 1):
                raise subprocess.TimeoutExpired(['ps'], 1)
            return real(pgid)
        kids = {}
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'out'
            output.mkdir()

            def spawn(command, **kwargs):
                process = subprocess.Popen([sys.executable, '-c', FAKE_SUPERVISOR, str(output)], **kwargs)
                kids.update(json.loads(process.stdout.readline()))
                return process
            try:
                with mock.patch.object(launch, '_group_exited', checked):
                    with self.assertRaises(TimeoutError):  # the forced first-cell deadline; cleanup ran in finally
                        launch.run_supervisor(output, output, sys.executable, sys.executable, output,
                                              started=time.monotonic(), mode='rehearsal', internal_seconds=7,
                                              session='1', spawn=spawn)
                receipt = json.loads((output / 'control/first-cell-supervisor-cleanup.json').read_bytes())
                for role, pgid in kids.items():
                    self.assertTrue(wait_until(lambda: not procfs.group_live(pgid)), f'{role} group survived ({fault})')
                return receipt, kids
            finally:
                for pgid in kids.values():
                    kill_group(pgid)

    def test_first_cleanup_query_timing_out_still_recovers_and_stops_children(self):
        receipt, kids = self.exercise('first')
        self.assertEqual({str(p) for p in kids.values()} <= set(receipt['groups']), True)
        self.assertIs(receipt['child_ownership_verified'], True)
        # The supervisor group was SIGKILLed and then verified gone by a later check, so absence is reported as
        # verified; the failed query stays in `errors`, which alone withholds first-cell cleanup certification
        # (launch: verified only with no errors; target evaluator: cleanup errors must be empty).
        self.assertIs(receipt['groups_absent'], True)
        self.assertTrue(any('supervisor group stop' in e for e in receipt['errors']))

    def test_every_cleanup_query_timing_out_still_kills_every_owned_group(self):
        receipt, kids = self.exercise('every')
        self.assertEqual({str(p) for p in kids.values()} <= set(receipt['groups']), True)
        self.assertIs(receipt['groups_absent'], False)
        self.assertFalse(any(v is True for v in receipt['groups'].values()))

    def test_children_that_ignore_sigterm_are_killed_and_clean_cleanup_is_certified(self):
        receipt, kids = self.exercise('none')
        self.assertEqual(len(receipt['groups']), 3)
        self.assertTrue(all(v is True for v in receipt['groups'].values()))
        self.assertIs(receipt['groups_absent'], True)
        self.assertEqual(receipt['errors'], [])


@unittest.skipUnless(LINUX, 'real POSIX process groups')
class OwnershipCleanupFaults(unittest.TestCase):
    def test_failed_checks_still_kill_recovered_groups_and_never_certify(self):
        from research.stagnation_supervision_runtime_v2 import launch, ownership, procfs
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            owners = ownership.ChildOwners(output, 1.0, 'n' * 64)
            kids = {}
            try:
                for role in ownership.ROLES:
                    code = 'import signal, time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\ntime.sleep(120)\n'
                    kids[role] = subprocess.Popen([sys.executable, '-c', code], start_new_session=True).pid
                    (output / 'control').mkdir(exist_ok=True)
                    (output / 'control' / f'ownership-{role}.json').write_text(json.dumps(
                        {'role': role, 'pgid': kids[role], 'supervisor_pgid': os.getpgrp(), 'first_cell_monotonic': 1.0,
                         'nonce': 'n' * 64}), encoding='utf-8')
                    owners.journal['children'][role] = {'state': 'registered', 'pgid': kids[role]}
                    owners.journal[role + '_pgid'] = kids[role]
                owners.save()  # no Popen handles: recovery from the durable records alone

                def broken(pgid):
                    raise subprocess.TimeoutExpired(['ps'], 1)
                with mock.patch.object(launch, '_group_exited', broken):
                    absent, errors = owners.stop()
                self.assertFalse(absent)
                self.assertTrue(errors)
                for pgid in kids.values():
                    self.assertTrue(wait_until(lambda: not procfs.group_live(pgid)))
            finally:
                for pgid in kids.values():
                    kill_group(pgid)

    def test_no_payload_module_uses_a_ps_subprocess_for_cleanup_or_rss(self):
        from research.stagnation_supervision_runtime_v2 import authority as A
        payload = A.payload_inventory(A.ROOT)
        self.assertNotIn('scripts/run_grounded_action_v1_engine_local.py', payload)
        for name in ('launch.py', 'ownership.py', 'resources.py', 'supervisor.py', 'monitor.py', 'procfs.py'):
            text = (A.ROOT / 'research/stagnation_supervision_runtime_v2' / name).read_text(encoding='utf-8')
            self.assertNotIn("'ps'", text, name)
            self.assertNotIn('group_rss_bytes', text, name)


FIXTURE = {'uuid': 'GPU-REHEARSAL-INJECTED', 'name': 'RTX PRO 6000 (injected rehearsal)', 'total_bytes': 96 * 1024**3,
           'used_bytes': 1}


@unittest.skipUnless(LINUX, 'evidence store uses fcntl')
class WarmupDiagnostics(unittest.TestCase):
    def observe(self, failure):
        from certification.phase4_integrated_v2.monitor import VRAM
        from research.stagnation_supervision_runtime_v2 import monitor, procfs
        now = [100.0]

        class Probes:
            def __init__(self, *args):
                pass

            def bind(self):
                return {'gpu_uuid': FIXTURE['uuid'], 'max_used_vram_bytes': VRAM, 'initial_telemetry': FIXTURE}

            def sample(self, uuid):
                now[0] += .012
                return dict(FIXTURE)

            def rss(self, pid):
                now[0] += 1.0
                if failure == 'timeout':
                    raise subprocess.TimeoutExpired(['ps', '-axo', 'pgid=,rss='], 1)
                raise procfs.ScanBudgetExceeded('/proc scan exceeded 0.4 s (stat reads)', {
                    'budget_seconds': .4, 'entries': 312, 'stat_reads': 40, 'vanished': 0, 'members': 1,
                    'member_states': {'S': 1}, 'slowest_read_seconds': .9123456789, 'list_seconds': .001,
                    'elapsed_seconds': 1.0000001})

            def scratch_bytes(self):
                return 0

            def gpu_pids(self):
                return []
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(monitor, 'probes_for', return_value=Probes):
            root = Path(tmp)
            result = monitor.observe(7, root, root, started=0, deadline=4000, stop=root / 'stop', nonce='w',
                                     mode='rehearsal', clock=lambda: now[0], sleep=lambda s: None)
            raw = (root / 'monitor/failure.json').read_bytes()
        return result, json.loads(raw), len(raw)

    def test_a_subprocess_timeout_in_the_warm_up_names_the_probe(self):
        result, receipt, _ = self.observe('timeout')
        self.assertEqual(result['status'], 'failed')
        self.assertIn('TimeoutExpired', receipt['error'])
        self.assertEqual(receipt['diagnostics']['phase'], 'warmup_rss')
        self.assertEqual(set(receipt['diagnostics']['warmup_probe_seconds']), {'gpu', 'rss'})
        self.assertAlmostEqual(receipt['diagnostics']['warmup_probe_seconds']['rss'], 1.0, places=3)

    def test_a_proc_scan_over_budget_carries_its_census_within_the_receipt_limit(self):
        _, receipt, size = self.observe('budget')
        self.assertEqual(receipt['diagnostics']['phase'], 'warmup_rss')
        census = receipt['diagnostics']['rss_census']
        self.assertEqual((census['entries'], census['stat_reads'], census['slowest_read_seconds']), (312, 40, .912346))
        self.assertLessEqual(size, 2048)


@unittest.skipUnless(LINUX, '/proc')
class ResourceProbe(unittest.TestCase):
    def test_rehearsal_and_live_rss_use_proc_and_keep_the_census(self):
        from research.stagnation_supervision_runtime_v2 import procfs, resources
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], start_new_session=True)
        self.addCleanup(lambda: (kill_group(child.pid), child.wait(timeout=5)))
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'SSV_REHEARSAL': '1', 'CUDA_VISIBLE_DEVICES': ''}):
            probes = resources.RehearsalProbes(child.pid, tmp)
            self.assertTrue(wait_until(lambda: probes.rss(child.pid) > 0))
            self.assertEqual(probes.last_rss_census['members'], 1)
            census = {'elapsed_seconds': 9.0}
            with mock.patch.object(procfs, 'scan', side_effect=procfs.ScanBudgetExceeded('over', census)):
                with self.assertRaises(procfs.ScanBudgetExceeded):
                    probes.rss(child.pid)
            self.assertIs(probes.last_rss_census, census)
            with self.assertRaises(ValueError):
                probes.rss(os.getpid())  # bound to the owned worker only


if __name__ == '__main__':
    unittest.main()
