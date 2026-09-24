"""Read-only clean-checkout replay of archived Stage B CPU development evidence."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.grounded_action_v1.replay import replay_file


def run():
    receipt = json.loads((ROOT / 'reports/perception_stage_b_v1_local_archive.json').read_bytes())
    archive = ROOT / receipt['archive']
    if hashlib.sha256(archive.read_bytes()).hexdigest() != receipt['archive_sha256']:
        raise ValueError('archive hash')
    with zipfile.ZipFile(archive) as bundle, tempfile.TemporaryDirectory() as temp:
        if set(bundle.namelist()) != set(receipt['members']):
            raise ValueError('archive member inventory')
        for name, info in receipt['members'].items():
            if Path(name).name != name:
                raise ValueError('unsafe member')
            raw = bundle.read(name)
            if len(raw) != info['bytes'] or hashlib.sha256(raw).hexdigest() != info['sha256']:
                raise ValueError('archive member hash')
            (Path(temp) / name).write_bytes(raw)
        result = replay_file(Path(temp) / 'run.json')
        monitor = json.loads((Path(temp) / 'monitor.json').read_bytes())
        if (result['status'] != receipt['independent_replay_status'] or
                result['primary_outcome'] != receipt['primary_outcome'] or
                [ep['level_delta'] for ep in result['episodes']] != receipt['level_deltas'] or
                monitor['status'] != 'complete' or monitor['worker_cleanup_verified'] is not True or
                monitor['temporary_games_removed'] is not True or monitor['process_group_exited'] is not True or
                monitor['worker_exit_code'] != 0 or not 0 < monitor['max_worker_rss_bytes'] <= 8 * 1024**3):
            raise ValueError('archived evaluation/supervision drift')
        return {'status': 'verified', 'archive_sha256': receipt['archive_sha256'],
                'calls': result['calls'], 'dispatches': result['dispatches'],
                'level_deltas': receipt['level_deltas'], 'model_calls': 0, 'gpu_runs': 0}


if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True))
