"""First-cell Stage B target lifecycle; launch only with separate reviewed authority."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import threading
import time

from certification.phase4_integrated_v2.evidence import EvidenceStore
from research.grounded_action_v1.authority import consume_runtime, require

ROOT = Path(__file__).resolve().parents[1]


def _group_exited(pgid):
    if type(pgid) is not int or pgid <= 0 or pgid == os.getpgrp():
        raise ValueError('invalid owned process group')
    result = subprocess.run(['ps', '-axo', 'pgid=,stat='], capture_output=True,
                            text=True, timeout=2, check=True)
    return not any(int(parts[0]) == pgid and not parts[1].startswith('Z')
                   for line in result.stdout.splitlines()
                   if len(parts := line.split()) >= 2 and parts[0].isdigit())


def _stop_group(pgid):
    if _group_exited(pgid):
        return True
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    until = time.monotonic() + 1
    while time.monotonic() < until and not _group_exited(pgid):
        time.sleep(.05)
    if not _group_exited(pgid):
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    until = time.monotonic() + 3
    while time.monotonic() < until and not _group_exited(pgid):
        time.sleep(.05)
    return _group_exited(pgid)


def _owned_groups(output, supervisor_pid):
    groups = [supervisor_pid]
    ownership = output / 'control/ownership.json'
    if ownership.is_file() and not ownership.is_symlink() and ownership.stat().st_size <= 8192:
        record = json.loads(ownership.read_bytes())
        for name in ('worker_pgid', 'monitor_pgid'):
            pgid = record.get(name)
            if type(pgid) is int and pgid > 0 and pgid not in groups:
                groups.append(pgid)
    return groups


def run_game_supervisor(output, working, game_python, model_python, games, *,
                        started, root=ROOT, spawn=subprocess.Popen):
    """Keep game-only imports in the game interpreter and own its descendants."""
    root, output = Path(root), Path(output)
    log = EvidenceStore(output, 'logs')
    control = EvidenceStore(output, 'control')
    errors = []
    retained = bytearray()
    command = [str(game_python), '-m', 'research.grounded_action_v1.target_supervisor',
               '--output', str(output), '--working', str(working),
               '--game-python', str(game_python), '--model-python', str(model_python),
               '--environments', str(games), '--started', str(started)]
    env = dict(os.environ)
    for key in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV'):
        env.pop(key, None)
    env['PYTHONNOUSERSITE'] = '1'
    # Kaggle's notebook backend is unavailable in the isolated game Python.
    # The supervisor passes this value through to its game worker; the
    # monitored worker environment sets MPLCONFIGDIR under scratch.
    env['MPLBACKEND'] = 'Agg'
    process = spawn(command, cwd=root, env=env, start_new_session=True,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def drain():
        try:
            while chunk := process.stdout.read(4096):
                if len(retained) + len(chunk) > 3 * 1024**2:
                    raise ValueError('supervisor log evidence exhausted')
                retained.extend(chunk)
                log.write('supervisor.json', bytes(retained))
        except Exception as exc:
            errors.append(type(exc).__name__ + ': ' + str(exc)[:200])
        finally:
            process.stdout.close()

    thread = threading.Thread(target=drain, daemon=True)
    thread.start()
    cleanup = {}
    try:
        while process.poll() is None:
            if errors:
                raise RuntimeError('supervisor log retention failed: ' + errors[0])
            if time.monotonic() >= started + 3295:
                raise TimeoutError('first-cell supervisor deadline')
            time.sleep(.05)
    finally:
        groups = [process.pid]
        try:
            groups = _owned_groups(output, process.pid)
        except Exception as exc:
            errors.append('ownership evidence: ' + type(exc).__name__ + ': ' + str(exc)[:128])
        for pgid in groups:
            try:
                cleanup[str(pgid)] = _stop_group(pgid)
            except Exception as exc:
                cleanup[str(pgid)] = type(exc).__name__ + ': ' + str(exc)[:128]
        try:
            process.wait(timeout=5)
        except Exception as exc:
            errors.append('supervisor reap: ' + type(exc).__name__ + ': ' + str(exc)[:128])
        thread.join(timeout=3)
        control.save('first-cell-supervisor-cleanup.json',
                     {'groups': cleanup, 'drain_finished': not thread.is_alive(),
                      'returncode': process.returncode, 'errors': errors})
    if errors or thread.is_alive() or not all(value is True for value in cleanup.values()):
        raise RuntimeError('first-cell supervisor cleanup or evidence failure')
    report_path = output / 'control/outer.json'
    if report_path.is_symlink() or not report_path.is_file() or report_path.stat().st_size > 65536:
        raise RuntimeError('missing or oversized target supervisor report')
    report = json.loads(report_path.read_bytes())
    if process.returncode != 0 or report.get('status') != 'development_study_complete_pending_archive_review':
        raise RuntimeError('target supervisor failed: ' + str(report.get('error'))[:200])
    if report.get('independent_gpu_cleanup_verified') is not True or report.get('process_groups_exited') is not True:
        raise RuntimeError('target supervisor cleanup unverified')
    return report


def run(output, working, *, started, root=ROOT):
    require(root)
    if not 0 <= time.monotonic() - started < 450:
        raise TimeoutError('Stage B first-cell installation deadline')
    consume_runtime(working, root)  # One attempt is consumed before installation.
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    control = EvidenceStore(output, 'control')
    error = None
    report = None
    try:
        manifest = json.loads((root / 'reports/phase4_v2_offline_package.json').read_bytes())
        mount = Path('/kaggle/input/competitions/arc-prize-2026-arc-agi-3')
        candidates = [Path('/kaggle/input/datasets/driessmit1/arc3-vllm-h100-wheelhouse-v3'),
                      Path('/kaggle/input/arc3-vllm-h100-wheelhouse-v3')]
        wheelhouse = next(path for path in candidates if path.is_dir())
        with tempfile.TemporaryDirectory(prefix='stage-b-dependencies-') as folder:
            from certification.phase4_integrated_v2.game_assets import stage_games
            from certification.phase4_integrated_v2.prepare import prepare
            from certification.phase4_integrated_v2.dependencies import freeze, thaw
            rootdir = Path(folder)
            games = stage_games(mount / 'environment_files', rootdir / 'games', manifest)
            pair = prepare(rootdir, output, wheelhouse,
                           mount / 'arc_agi_3_wheels', manifest, started)
            try:
                freeze(rootdir)
                report = run_game_supervisor(output, working, pair['game'],
                                             pair['model'], games, started=started, root=root)
            finally:
                thaw(rootdir)
    except Exception as exc:
        error = type(exc).__name__ + ': ' + str(exc)[:256]
    elapsed = time.monotonic() - started
    if elapsed >= 3300:
        error = error or 'Stage B first-cell hard deadline exceeded'
    receipt = {'scope': 'stage_b_first_cell', 'elapsed_seconds': elapsed,
               'error': error, 'dependency_trees_removed':
               not Path(folder).exists() if 'folder' in locals() else None,
               'provider_reconciliation_required': True, 'phase4_complete': False,
               'study_status': report['status'] if report else None}
    control.save('notebook-cost.json', receipt)
    if error or report is None or report['status'] != 'development_study_complete_pending_archive_review':
        raise RuntimeError(error or 'Stage B target supervisor did not complete')
    return receipt


def main():
    require()  # No installation, provider query or GPU use without Stage B authority.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--working', type=Path, required=True)
    parser.add_argument('--started', type=float, required=True)
    args = parser.parse_args()
    run(args.output, args.working, started=args.started)


if __name__ == '__main__':
    main()
