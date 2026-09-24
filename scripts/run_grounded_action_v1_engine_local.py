"""Externally supervised CPU-only ar25 integration; never starts a GPU model."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.grounded_action_v1.engine import DevelopmentAdapter, restore_game_mount, verified_game_mount
from research.grounded_action_v1.local import ScriptedService, run, save
from research.grounded_action_v1.replay import replay_file


def child(output, games, recordings, seconds):
    result = run(output, ScriptedService(), lambda arm: DevelopmentAdapter(arm, games, recordings),
                 deadline_seconds=seconds, kind='offline_development_engine')
    if result['status'] != 'complete':
        raise SystemExit(result['error'])
    print(json.dumps(replay_file(output), sort_keys=True), flush=True)


def terminate_group(process):
    if group_exited(process.pid):
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def rss_bytes(pid):
    try:
        for line in (Path('/proc') / str(pid) / 'status').read_text().splitlines():
            if line.startswith('VmRSS:'):
                return int(line.split()[1]) * 1024
    except (FileNotFoundError, PermissionError):
        return None
    return None


def group_exited(pid):
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return True
    return False


def supervise(output, games_source=None, *, seconds=180, evidence_limit=8 * 1024 * 1024):
    if not 15 <= seconds <= 3600 or evidence_limit < 65536:
        raise ValueError('local supervisor limits')
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(output)
    monitor_path = output.with_suffix('.monitor.json')
    log_path = output.with_suffix('.worker.log')
    if monitor_path.exists() or log_path.exists():
        raise FileExistsError('local monitor/log path')
    started = time.monotonic()
    monitor = {'scope': 'offline_cpu_development_engine_only', 'status': 'running',
               'deadline_seconds': seconds, 'evidence_limit_bytes': evidence_limit,
               'samples': [], 'worker_exit_code': None, 'worker_cleanup_verified': False,
               'temporary_games_removed': False, 'process_group_exited': False,
               'max_worker_rss_bytes': 0, 'error': None}
    process = None
    with tempfile.TemporaryDirectory(prefix='grounded-stage-b-') as folder:
        scratch = Path(folder)
        try:
            source = Path(games_source) if games_source else restore_game_mount(scratch / 'restored')
            games = verified_game_mount(source, scratch / 'staged')
            if time.monotonic() - started >= seconds:
                raise TimeoutError('staging consumed local deadline')
            with log_path.open('wb') as log:
                command = [sys.executable, str(Path(__file__).resolve()), '--child', '--output', str(output),
                           '--staged-games', str(games), '--recordings', str(scratch / 'recordings'),
                           '--seconds', str(max(1, seconds - (time.monotonic() - started)))]
                process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                           start_new_session=True)
                monitor['worker_pid'] = process.pid
                save(monitor_path, monitor)
                while process.poll() is None:
                    elapsed = time.monotonic() - started
                    evidence_bytes = output.stat().st_size if output.exists() else 0
                    log_bytes = log_path.stat().st_size
                    rss = rss_bytes(process.pid)
                    monitor['samples'].append({'elapsed_seconds': elapsed, 'record_bytes': evidence_bytes,
                                               'log_bytes': log_bytes, 'worker_rss_bytes': rss,
                                               'worker_alive': True})
                    if rss is not None:
                        monitor['max_worker_rss_bytes'] = max(monitor['max_worker_rss_bytes'], rss)
                    if rss is not None and rss > 8 * 1024**3:
                        raise ValueError('local worker RSS ceiling')
                    if evidence_bytes + log_bytes > evidence_limit:
                        raise ValueError('local evidence limit')
                    if elapsed >= seconds:
                        raise TimeoutError('external local deadline')
                    save(monitor_path, monitor)
                    time.sleep(.5)
            monitor['worker_exit_code'] = process.wait()
            monitor['process_group_exited'] = group_exited(process.pid)
            if (output.stat().st_size if output.exists() else 0) + log_path.stat().st_size > evidence_limit:
                raise ValueError('local evidence limit')
            if monitor['worker_exit_code'] != 0:
                raise RuntimeError('local worker failed; inspect retained record and log')
            if not monitor['process_group_exited']:
                raise RuntimeError('local worker descendants remain')
            replay = replay_file(output)
            monitor['worker_cleanup_verified'] = all(e['cleanup']['closed'] for e in json.loads(output.read_bytes())['episodes'])
            monitor['replay_status'] = replay['status']
            monitor['status'] = 'complete'
        except Exception as exc:
            monitor.update(status='failed', error=type(exc).__name__ + ': ' + str(exc)[:240])
            if process is not None:
                terminate_group(process)
                monitor['worker_exit_code'] = process.returncode
                monitor['process_group_exited'] = group_exited(process.pid)
        finally:
            monitor['elapsed_seconds'] = time.monotonic() - started
            save(monitor_path, monitor)
    monitor['temporary_games_removed'] = not scratch.exists()
    save(monitor_path, monitor)
    return monitor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--games', type=Path)
    parser.add_argument('--seconds', type=float, default=180)
    parser.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--staged-games', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--recordings', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        child(args.output, args.staged_games, args.recordings, args.seconds)
    else:
        result = supervise(args.output, args.games, seconds=args.seconds)
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(0 if result['status'] == 'complete' else 1)


if __name__ == '__main__':
    main()
