"""Archive the retained rehearsal evidence of the three connected-suite runs (A failed once; B and C passed).

Runs are identified by the first-file times of their rehearsal directories on the WSL clock, which
stepped forward by about 37,430 s during run A. Each run's directories must show the connected suite's
exact fault sequence, or the archive is refused. The archive is a deterministic tar.xz (sorted members,
zeroed timestamps and owners) and a lock records every member's hash and the directory-to-run mapping.
"""
import argparse
import hashlib
import json
from pathlib import Path
import io
import tarfile
import time

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'evidence/evidence-comprehension-v1-intermittent-runs.tar.xz'
LOCK = ROOT / 'reports/evidence_comprehension_v1_intermittent_runs_archive.json'
SOURCE = Path.home() / 'ecv-rehearsal-tests'
# Execution order of the connected suite (tests alphabetical; subtests in listed order).
SEQUENCE = ('slow_gate_pass_1', 'slow_gate_pass_2', 'http_error', 'storage', 'cancel', 'monitor_exit', 'model_startup',
            'log_flood', 'none', 'late_abort', 'trickle_metrics', 'late_reply', 'none', 'prefix_cache_enabled',
            'no_abort', 'slow_abort', 'surviving_child', 'hang_once')
# First-file time windows on the WSL clock (local time, 2026-09-26).
WINDOWS = {'run_a': (('03:12:00', '03:17:30'), ('13:40:00', '13:49:00')),
           'run_b': (('13:57:00', '14:10:30'),),
           'run_c': (('14:11:00', '14:22:00'),)}
OUTPUT = 'working/evidence-comprehension-v1'


def first_file(directory):
    files = [p for p in (directory / OUTPUT).rglob('*') if p.is_file()]
    return min(p.stat().st_mtime for p in files) if files else None


def select():
    runs = {name: [] for name in WINDOWS}
    for directory in SOURCE.iterdir():
        stamp = first_file(directory)
        if stamp is None or time.strftime('%Y-%m-%d', time.localtime(stamp)) != '2026-09-26':
            continue
        clock = time.strftime('%H:%M:%S', time.localtime(stamp))
        for name, windows in WINDOWS.items():
            if any(lo <= clock <= hi for lo, hi in windows):
                runs[name].append((stamp, directory))
    result = {}
    for name, rows in runs.items():
        rows.sort()
        faults = [json.loads((d / OUTPUT / 'control/outer.json').read_bytes())['fault'] for _, d in rows]
        if tuple(faults) != SEQUENCE:
            raise ValueError(f'{name}: rehearsal sequence differs from the connected suite: {faults}')
        result[name] = [{'directory': d.name, 'fault': f, 'first_file_wsl_clock':
                         time.strftime('%H:%M:%S', time.localtime(s))} for (s, d), f in zip(rows, faults)]
    return result


def archive():
    runs = select()
    members = {}
    for name, rows in runs.items():
        for row in rows:
            base = SOURCE / row['directory']
            for path in sorted(p for p in base.rglob('*') if p.is_file() and not p.is_symlink()):
                members[f'{name}/{row["directory"]}/{path.relative_to(base).as_posix()}'] = path.read_bytes()
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(ARCHIVE, 'w:xz', preset=9) as bundle:
        for member, raw in sorted(members.items()):
            info = tarfile.TarInfo(member)
            info.size, info.mtime, info.mode = len(raw), 0, 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ''
            bundle.addfile(info, io.BytesIO(raw))
    lock = {'archive': ARCHIVE.relative_to(ROOT).as_posix(),
            'archive_sha256': hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(), 'runs': runs,
            'members': {m: hashlib.sha256(r).hexdigest() for m, r in sorted(members.items())}}
    LOCK.write_text(json.dumps(lock, indent=1, sort_keys=True) + '\n')
    return {'members': len(members), 'bytes': ARCHIVE.stat().st_size, 'sha256': lock['archive_sha256']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(archive()))
