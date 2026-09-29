# Derived from scripts/archive_evidence_comprehension_v2_live.py by scripts/derive_evidence_comprehension_v3_postrun.py; edit the derivation, not this file.
"""Portable checked archive and read-only replay for the evidence-comprehension v3 live attempt.

archive  hashes the downloaded provider output and the launch/approval records into a deterministic
         tar.xz and a lock, after re-running the independent evaluator;
replay   extracts to a temporary folder, verifies every member, re-runs the independent evaluator in
         live mode, and requires it to reproduce the archived evaluation exactly.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ATTEMPT = 'ecv3-089bf11fd38c41f88808794a134a3d56'
RUN = 'reports/runs/evidence-comprehension-v3'
DOWNLOAD = ROOT / RUN / 'download'
OUTPUT = 'evidence-comprehension-v3'
ARCHIVE = ROOT / 'evidence/evidence-comprehension-v3-live.tar.xz'
LOCK = ROOT / 'reports/evidence_comprehension_v3_live_archive.json'
RECORDS = ('reports/evidence_comprehension_v3_launch.json', 'reports/evidence_comprehension_v3_launch_claim.json',
           'reports/evidence_comprehension_v3_prelaunch.json', 'reports/evidence_comprehension_v3_source_approval.json',
           'reports/evidence_comprehension_v3_compute_authorization.json',
           'research/evidence_comprehension_v3/execution_lock.json', 'research/evidence_comprehension_v3/reservation.json',
           'notebooks/evidence-comprehension-v3-run/launch-package-lock.json',
           'notebooks/evidence-comprehension-v3-review-r1/review-source-lock.json')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def evaluate(download):
    from scripts.evaluate_evidence_comprehension_v3 import evaluate_output
    return json.loads(json.dumps(evaluate_output(Path(download) / OUTPUT, mode='live'), sort_keys=True, default=str))


def members():
    result = {}
    for path in sorted(p for p in DOWNLOAD.rglob('*') if p.is_file()):
        if path.is_symlink():
            raise ValueError('symlink in provider download')
        result[f'{RUN}/download/{path.relative_to(DOWNLOAD).as_posix()}'] = path.read_bytes()
    for name in RECORDS:
        result[name] = (ROOT / name).read_bytes()
    return result


def archive():
    verdict = evaluate(DOWNLOAD)
    files = members()
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(ARCHIVE, 'x:xz', preset=9) as bundle:
        for name, raw in sorted(files.items()):
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode = len(raw), 0, 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ''
            bundle.addfile(info, io.BytesIO(raw))
    lock = {'attempt_id': ATTEMPT, 'archive': ARCHIVE.relative_to(ROOT).as_posix(), 'archive_sha256': sha(ARCHIVE.read_bytes()),
            'members': {name: sha(raw) for name, raw in sorted(files.items())}, 'evaluation': verdict}
    with LOCK.open('x', encoding='utf-8') as stream:
        json.dump(lock, stream, sort_keys=True, indent=1)
        stream.write('\n')
    return replay()


def replay():
    lock = json.loads(LOCK.read_bytes())
    if sha((ROOT / lock['archive']).read_bytes()) != lock['archive_sha256']:
        raise ValueError('archive hash mismatch')
    with tempfile.TemporaryDirectory() as folder, tarfile.open(ROOT / lock['archive'], 'r:xz') as bundle:
        names = [m.name for m in bundle.getmembers() if m.isfile()]
        if sorted(names) != sorted(lock['members']):
            raise ValueError('archive inventory')
        for info in bundle.getmembers():
            if Path(info.name).is_absolute() or '..' in Path(info.name).parts:
                raise ValueError('unsafe archive member')
            raw = bundle.extractfile(info).read()
            if sha(raw) != lock['members'][info.name]:
                raise ValueError('member hash mismatch: ' + info.name)
            target = Path(folder) / info.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        verdict = evaluate(Path(folder) / RUN / 'download')
    if verdict != lock['evaluation']:
        raise ValueError('archived independent evaluation drift')
    return {'status': 'archive_verified', 'archive_sha256': lock['archive_sha256'], 'files': len(lock['members']),
            'technically_complete': verdict['technically_complete'], 'gate_status': verdict['gate_status'],
            'gate': verdict['gate']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('archive', 'replay'))
    print(json.dumps({'archive': archive, 'replay': replay}[parser.parse_args().operation](), indent=1))
