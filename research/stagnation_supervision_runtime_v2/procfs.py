"""Bounded /proc process-group probes for Track 3 runtime v2 (hand-written; Linux; standard library; no subprocess).

Session-1 attempts 1 and 2 failed before readiness because the monitor's memory probe ran `ps -axo pgid=,rss=` as a
subprocess, which exceeded the frozen telemetry budget on the target (5.45 s once, then its own 1-s timeout); the
cleanup paths used the same kind of `ps` scan. These probes read /proc directly instead:
  group_rss(pgid, budget)   resident memory of every process whose process group is `pgid`: the same coverage as
                            `ps -axo pgid=,rss=` (all members, not only the leader or the leader's descendants);
  group_live(pgid, budget)  whether any non-zombie member remains (the rule of the ps-based group_exited).
A scan lists /proc once and reads only /proc/<pid>/stat for each process: one small read, never cmdline, environ,
status or maps (which take the target process's memory lock). A scan that exceeds its budget raises
ScanBudgetExceeded carrying a bounded census; it never returns a partial, estimated or zero result. The census holds
counts and timings only, never process names, command lines or identifiers of other processes.
"""
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


def scan(pgid, budget, *, clock=time.monotonic, read=read_stat, listdir=os.listdir):
    """[(state, resident pages)] for every member of process group `pgid`, and the census."""
    if type(pgid) is not int or pgid <= 0:
        raise ValueError('invalid process group')
    began = clock()
    census = {'budget_seconds': budget, 'entries': 0, 'stat_reads': 0, 'vanished': 0, 'members': 0,
              'member_states': {}, 'slowest_read_seconds': 0.0, 'list_seconds': None, 'elapsed_seconds': None}

    def over(where):
        census['elapsed_seconds'] = clock() - began
        if census['elapsed_seconds'] > budget:
            raise ScanBudgetExceeded(f'/proc scan exceeded {budget} s ({where})', census)

    names = [name for name in listdir('/proc') if name.isdigit()]
    census['entries'], census['list_seconds'] = len(names), clock() - began
    over('listing')
    members = []
    for name in names:
        started = clock()
        row = read(int(name))
        census['slowest_read_seconds'] = max(census['slowest_read_seconds'], clock() - started)
        census['stat_reads'] += 1
        if row is None:
            census['vanished'] += 1
        else:
            state, group, pages = row
            if group == pgid:
                members.append((state, pages))
                census['member_states'][state] = census['member_states'].get(state, 0) + 1
        over('stat reads')
    census['members'] = len(members)
    over('complete')
    return members, census


def group_rss(pgid, budget=RSS_BUDGET_SECONDS, **kwargs):
    """(resident bytes of the whole group, census); raises instead of returning a partial value."""
    members, census = scan(pgid, budget, **kwargs)
    return sum(pages for _, pages in members) * PAGE_BYTES, census


def group_live(pgid, budget=GROUP_BUDGET_SECONDS, **kwargs):
    """True while any non-zombie member remains (a reparented zombie may keep the group id until init reaps it)."""
    members, _ = scan(pgid, budget, **kwargs)
    return any(state != 'Z' for state, _ in members)
