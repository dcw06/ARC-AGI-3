"""Archive the supervised CPU-only real-engine check with member hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.grounded_action_v1.replay import replay_file


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def archive(record, output, receipt_path):
    record = Path(record)
    paths = {'run.json': record, 'monitor.json': record.with_suffix('.monitor.json'),
             'worker.log': record.with_suffix('.worker.log')}
    result = replay_file(record)
    monitor = json.loads(paths['monitor.json'].read_bytes())
    if (result['status'] != 'valid_offline_development_pair' or monitor['status'] != 'complete' or
            monitor['replay_status'] != result['status'] or monitor['worker_cleanup_verified'] is not True or
            monitor['temporary_games_removed'] is not True or monitor['process_group_exited'] is not True or
            monitor['worker_exit_code'] != 0 or not 0 < monitor['max_worker_rss_bytes'] <= 8 * 1024**3):
        raise ValueError('local supervision/replay incomplete')
    members = {name: path.read_bytes() for name, path in paths.items()}
    if any(len(data) > 8 * 1024 * 1024 for data in members.values()):
        raise ValueError('local evidence size')
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for name, raw in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, raw)
    receipt = {'scope': 'CPU-only scripted responses on real offline development engine',
               'archive': output.relative_to(ROOT).as_posix(), 'archive_sha256': sha(output.read_bytes()),
               'members': {name: {'sha256': sha(raw), 'bytes': len(raw)} for name, raw in sorted(members.items())},
               'independent_replay_status': result['status'], 'model_calls': 0, 'gpu_runs': 0,
               'primary_outcome': result['primary_outcome'],
               'level_deltas': [ep['level_delta'] for ep in result['episodes']]}
    Path(receipt_path).write_bytes((json.dumps(receipt, indent=2) + '\n').encode())
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', required=True, type=Path)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(archive(args.record, args.archive, args.receipt), sort_keys=True))
