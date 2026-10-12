"""Bounded /proc process-group probes for Track 3 runtime v2 (hand-written; Linux; standard library; no subprocess).

Session-1 attempts 1 and 2 failed before readiness because the monitor's memory probe ran `ps -axo pgid=,rss=` as a
subprocess, which exceeded the frozen telemetry budget on the target (5.45 s once, then its own 1-s timeout); the
cleanup paths used the same kind of `ps` scan. These probes read /proc directly instead:
  group_rss(pgid, budget)   resident memory of every process whose process group is `pgid`: the same coverage as
                            `ps -axo pgid=,rss=` (all members, not only the leader or the leader's descendants);
  group_live(pgid, budget)  whether any non-zombie member remains (the rule of the ps-based group_exited).
A scan lists /proc once and reads only /proc/<pid>/stat for each process: one small read, never cmdline, environ,
status or maps (which take the target process's memory lock).

The budget is a hard bound on the caller's wait (r7, second review): the scan runs in a worker thread and the caller
waits at most `budget` seconds on a lock the worker releases, so a listing or read that stalls inside the kernel cannot
hold the caller, and cleanup still reaches its SIGKILL fallback. A stalled worker is abandoned; it can only finish into
a result nobody reads. The worker is started with the low-level `_thread` primitive (r8), so the probe does not
depend on `threading.Thread` (whose start an interrupted logging thread must not disable); if no thread can be
created at all, the probe raises and the caller fails closed. A scan that exceeds its budget raises ScanBudgetExceeded with a snapshot of the census; it never returns a
partial, estimated or zero result. The census holds counts and timings only (never process names, command lines or
identifiers of other processes). The worker changes only its own private state and, after each step, publishes a
new census by replacing one reference; a published census is never modified, so the caller's snapshot is always one
coherent publication (r9, third review), with no lock held during a read that may block. `members` always equals the
sum of `member_states`, and `complete` and `phase` say whether, and where, the scan stopped.
"""
import _thread
import os
import time

PAGE_BYTES = os.sysconf('SC_PAGE_SIZE') if hasattr(os, 'sysconf') else 4096
RSS_BUDGET_SECONDS = .4    # leaves room inside the frozen 1-s sampling gap (0.5-s interval plus the other probes)
GROUP_BUDGET_SECONDS = 2.0  # cleanup checks (the ps-based check allowed 2 s)


class ScanBudgetExceeded(TimeoutError):
    def __init__(self, message, census):
        super().__init__(message)
        self.census = census


def read_stat(pid):
    """(state, process group, resident pages) from /proc/<pid>/stat, or None if the process is gone."""
    try:
        with open(f'/proc/{pid}/stat', 'rb') as stream:
            data = stream.read(4096)
    except (FileNotFoundError, ProcessLookupError):
        return None
    fields = data[data.rindex(b')') + 2:].split()  # the command name may contain spaces or parentheses
    return fields[0].decode('ascii', 'replace'), int(fields[2]), int(fields[21])


def _observe_member(state, member_state):
    """Record one observed member in the worker's private state (published afterwards, never partially)."""
    state['member_states'][member_state] = state['member_states'].get(member_state, 0) + 1
    state['members'] += 1


def _publication(state):
    return {**state, 'member_states': dict(state['member_states'])}  # a fresh object; never modified afterwards


def scan(pgid, budget, *, clock=time.monotonic, read=None, listdir=None):
    """[(state, resident pages)] for every member of process group `pgid`, and the census; the caller never waits
    longer than `budget` seconds (plus thread scheduling)."""
    if type(pgid) is not int or pgid <= 0:
        raise ValueError('invalid process group')
    if not (type(budget) in (int, float) and budget > 0):
        raise ValueError('invalid budget')
    read = read or read_stat  # looked up at call time, so tests can substitute the module's reader
    listdir = listdir or os.listdir
    began = clock()
    state = {'budget_seconds': budget, 'phase': 'listing', 'complete': False, 'entries': None, 'stat_reads': 0,
             'reads_started': 0, 'vanished': 0, 'members': 0, 'member_states': {}, 'slowest_read_seconds': 0.0,
             'list_seconds': None, 'elapsed_seconds': None}
    published = [_publication(state)]  # replaced, never mutated; one reference assignment publishes a whole census
    outcome = {}
    finished = _thread.allocate_lock()
    finished.acquire()

    def work():
        try:
            names = [name for name in listdir('/proc') if name.isdigit()]
            state.update(entries=len(names), list_seconds=clock() - began, phase='stat reads')
            published[0] = _publication(state)
            members = []
            for name in names:
                if clock() - began > budget:
                    return
                state['reads_started'] += 1
                published[0] = _publication(state)  # a stalled read shows as reads_started > stat_reads
                started = clock()
                row = read(int(name))
                state['slowest_read_seconds'] = max(state['slowest_read_seconds'], clock() - started)
                state['stat_reads'] += 1
                if row is None:
                    state['vanished'] += 1
                else:
                    member_state, group, pages = row
                    if group == pgid:
                        members.append((member_state, pages))
                        _observe_member(state, member_state)
                published[0] = _publication(state)
            state.update(phase='complete', complete=True)
            published[0] = _publication(state)
            outcome['members'] = members
        except BaseException as exc:  # handed to the caller, never swallowed
            outcome['error'] = exc
        finally:
            finished.release()

    _thread.start_new_thread(work, ())  # raises if no thread can be created: the caller fails closed
    done = finished.acquire(timeout=budget)
    if 'error' in outcome:
        raise outcome['error']
    snapshot = dict(published[0])  # one coherent publication
    snapshot['member_states'] = dict(snapshot['member_states'])
    snapshot['elapsed_seconds'] = clock() - began
    if not done or 'members' not in outcome or snapshot['elapsed_seconds'] > budget:
        snapshot['stalled'] = not done and (snapshot['entries'] is None or snapshot['reads_started'] > snapshot['stat_reads'])
        raise ScanBudgetExceeded(f"/proc scan exceeded {budget} s ({snapshot['phase']})", snapshot)
    snapshot['stalled'] = False
    return outcome['members'], snapshot


def group_rss(pgid, budget=RSS_BUDGET_SECONDS, **kwargs):
    """(resident bytes of the whole group, census); raises instead of returning a partial value."""
    members, census = scan(pgid, budget, **kwargs)
    return sum(pages for _, pages in members) * PAGE_BYTES, census


def group_live(pgid, budget=GROUP_BUDGET_SECONDS, **kwargs):
    """True while any non-zombie member remains (a reparented zombie may keep the group id until init reaps it)."""
    members, _ = scan(pgid, budget, **kwargs)
    return any(state != 'Z' for state, _ in members)
