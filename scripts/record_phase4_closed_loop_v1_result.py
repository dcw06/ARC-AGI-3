"""Archive and independently replay the completed R1 run; never launch compute."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from certification.phase4_closed_loop_v1.replay import replay

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')

def main():
    run = ROOT/'reports/runs/phase4-closed-loop-v1-r1-pilot'
    lock = ROOT/'notebooks/phase4-closed-loop-v1-review-r1/review-source-lock.json'
    assert sha(lock) == '078b1dc692e0a1a9580218e642f2329893593e0931959900a5ca565f5ce457f3'
    bindings = read(lock)['bindings']
    for name, digest in bindings.items():
        assert sha(ROOT/name) == digest, name
    manifest = read(run/'download-manifest.json')
    assert len(manifest) == len({item['path'] for item in manifest})
    for item in manifest:
        path = (run/'output'/item['path']).resolve()
        assert path.is_relative_to((run/'output').resolve())
        assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256'], item['path']
    archive = ROOT/'evidence/phase4-closed-loop-v1-r1-completed-v1.zip'
    files = sorted(p for p in run.rglob('*') if p.is_file())
    if not archive.exists():
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
            for path in files:
                z.write(path, path.relative_to(run).as_posix())
    with tempfile.TemporaryDirectory(prefix='closed-loop-replay-') as temp:
        with zipfile.ZipFile(archive) as z:
            assert set(z.namelist()) == {p.relative_to(run).as_posix() for p in files}
            for path in files:
                assert hashlib.sha256(z.read(path.relative_to(run).as_posix())).hexdigest() == sha(path)
            z.extractall(temp)
        evidence = Path(temp)/'output/phase4-closed-loop-v1'
        result = replay(evidence)
        final = read(evidence/'evaluation/notebook-result.json')
    evaluation = ROOT/'reports/phase4_closed_loop_v1_evaluation.json'
    write(evaluation, result)
    metrics = {}
    for arm, totals in result['comparison']['arms'].items():
        episodes = [e for e in result['comparison']['episodes'] if e['arm'] == arm]
        actions = sum(e['actions'] for e in episodes)
        adjacent = sum(max(0, e['actions']-1) for e in episodes)
        repeats = sum(e['adjacent_repeats'] for e in episodes)
        clicks = [c for e in episodes for c in e['click_coordinates']]
        metrics[arm] = dict(totals, episodes=len(episodes), actions=actions,
            adjacent_repeats=repeats, adjacent_opportunities=adjacent, repeat_rate=repeats/adjacent,
            canonical_changes=sum(round(e['canonical_change_rate']*e['actions']) for e in episodes),
            frame_changes=sum(round(e['frame_change_rate']*e['actions']) for e in episodes),
            repeats_after_unchanged=sum(e['repeats_after_unchanged'] for e in episodes),
            longest_streak=max(e['longest_streak'] for e in episodes),
            click_actions=len(clicks), example_coordinate_clicks=sum(c=={'x':12,'y':34} for c in clicks))
    observations = [json.loads(line) for line in (run/'provider-observations.jsonl').read_text().splitlines()]
    terminal = observations[-1]
    assert terminal['status'] == 'KernelWorkerStatus.COMPLETE' and terminal['provider_version'] == 1
    before = read(ROOT/'reports/phase4_closed_loop_v1_pilot_prelaunch.json')['gpu_quota_seconds']['time_used']
    after = terminal['gpu_quota_seconds']['time_used']
    receipt = dict(independent_passed=result['passed'], errors=result['errors'],
        source_bindings_verified=len(bindings), source_lock_sha256=sha(lock),
        downloaded_files=len(manifest), archive=archive.relative_to(ROOT).as_posix(),
        archive_sha256=sha(archive), archive_bytes=archive.stat().st_size,
        evaluation_sha256=sha(evaluation), recorder_sha256=sha(Path(__file__)),
        startup_inclusive_elapsed_seconds=final['elapsed_seconds'], metrics=metrics,
        provider_observation=terminal, account_time_used_before=before, account_time_used_after=after,
        account_usage_delta_seconds=round(after-before, 6), exact_provider_billed_seconds=None,
        accounting_limit='Account quota delta only; malformed SDK duration serialization and inconsistent total allowance retained in archive. Not exact per-job billing.',
        phase4_complete=False, production_C_admit=None, new_compute_authorized=False)
    write(ROOT/'reports/phase4_closed_loop_v1_evidence_receipt.json', receipt)
    print(json.dumps(receipt, indent=2))
    if not result['passed']:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
