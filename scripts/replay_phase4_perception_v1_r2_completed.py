"""Verify the completed R2 archive and replay its frozen live evaluator read-only."""
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REVIEW = ROOT/'notebooks/phase4-perception-v1-review-r2'
ARCHIVE_MANIFEST = ROOT/'reports/phase4_perception_v1_r2_completed_archive.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def run():
    lock = json.loads((REVIEW/'review-source-lock.json').read_bytes())
    for name, digest in lock['bindings'].items():
        if sha((ROOT/name).read_bytes()) != digest:
            raise ValueError('source drift: '+name)
    for name, digest in lock['artifacts'].items():
        if sha((REVIEW/name).read_bytes()) != digest:
            raise ValueError('review artifact drift: '+name)

    manifest = json.loads(ARCHIVE_MANIFEST.read_bytes())
    archive = ROOT/manifest['archive']
    if sha(archive.read_bytes()) != manifest['sha256']:
        raise ValueError('archive hash')
    from certification.phase4_perception_v1.replay import replay

    with tempfile.TemporaryDirectory() as temporary, zipfile.ZipFile(archive) as bundle:
        root = Path(temporary)
        members = manifest['members']
        if set(bundle.namelist()) != set(members) or len(bundle.namelist()) != len(members):
            raise ValueError('archive inventory')
        for name, digest in members.items():
            target = (root/name).resolve()
            if not target.is_relative_to(root.resolve()):
                raise ValueError('archive path')
            raw = bundle.read(name)
            if sha(raw) != digest:
                raise ValueError('archive member hash: '+name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        downloaded = json.loads((root/'receipts/download.json').read_bytes())
        if downloaded['kernel'] != 'daichongwei06/arc3-phase4-perception-v1-r2' or downloaded['requested_version'] != 1:
            raise ValueError('provider identity')
        if downloaded['file_count'] != len(downloaded['files']):
            raise ValueError('download inventory')
        actual_downloads = {name for name in members if name.startswith('download/')}
        expected_downloads = {'download/'+row['path'] for row in downloaded['files']}
        if actual_downloads != expected_downloads:
            raise ValueError('download archive inventory')
        for row in downloaded['files']:
            raw = (root/'download'/row['path']).read_bytes()
            if len(raw) != row['bytes'] or sha(raw) != row['sha256']:
                raise ValueError('download hash: '+row['path'])
        observations = [json.loads(line) for line in (root/'receipts/provider-observations.jsonl').read_text().splitlines()]
        if not observations or observations[-1]['status'] != 'KernelWorkerStatus.COMPLETE':
            raise ValueError('provider terminal status')
        result = replay(root/'download/phase4-perception-v1', live=True, seconds=2280)
        return {'passed': result['passed'], 'errors': result['errors'],
                'comparison': result['comparison'], 'independent_replay': result['independent_replay'],
                'evidence_bytes': result['evidence_bytes'],
                'exact_provider_billed_seconds': None, 'phase4_complete': False}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
