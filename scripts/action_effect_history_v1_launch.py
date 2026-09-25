"""First-cell lifecycle for the action-effect-history comparison (live needs separate reviewed authority)."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time

from certification.phase4_integrated_v2.evidence import EvidenceStore

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_NAME = 'action-effect-history-v1'


def _group_exited(pgid):
    if type(pgid) is not int or pgid <= 0 or pgid == os.getpgrp():
        raise ValueError('invalid owned process group')
    result = subprocess.run(['ps', '-axo', 'pgid=,stat='], capture_output=True, text=True, timeout=2, check=True)
    return not any(int(parts[0]) == pgid and not parts[1].startswith('Z') for line in result.stdout.splitlines()
                   if len(parts := line.split()) >= 2 and parts[0].isdigit())


def _stop_group(pgid):
    if _group_exited(pgid):
        return True
    for sig, wait in ((signal.SIGTERM, 1), (signal.SIGKILL, 3)):
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            pass
        until = time.monotonic() + wait
        while time.monotonic() < until and not _group_exited(pgid):
            time.sleep(.05)
        if _group_exited(pgid):
            return True
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


def run_supervisor(output, working, game_python, model_python, games, *, started, mode, internal_seconds,
                   fault='none', root=ROOT, spawn=subprocess.Popen):
    """Own the supervisor's session and every group it records; verify all are gone."""
    root, output = Path(root), Path(output)
    log, control = EvidenceStore(output, 'logs'), EvidenceStore(output, 'control')
    errors, retained = [], bytearray()
    command = [str(game_python), '-m', 'research.action_effect_history_v1.supervisor', '--output', str(output),
               '--working', str(working), '--game-python', str(game_python), '--model-python', str(model_python),
               '--environments', str(games), '--started', str(started), '--mode', mode,
               '--internal-seconds', str(internal_seconds), '--fault', fault]
    env = dict(os.environ)
    for key in ('PYTHONHOME', 'VIRTUAL_ENV'):
        env.pop(key, None)
    if mode == 'live':
        env.pop('PYTHONPATH', None)
    else:
        env['PYTHONPATH'] = str(root)
    env['PYTHONNOUSERSITE'] = '1'
    env['MPLBACKEND'] = 'Agg'
    process = spawn(command, cwd=root, env=env, start_new_session=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

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
            if time.monotonic() >= started + internal_seconds - 5:
                raise TimeoutError('first-cell supervisor deadline')
            time.sleep(.05)
    finally:
        groups = [process.pid]
        try:
            groups = _owned_groups(output, process.pid)
        except Exception as exc:
            errors.append('ownership evidence: ' + type(exc).__name__)
        for pgid in groups:
            try:
                cleanup[str(pgid)] = _stop_group(pgid)
            except Exception as exc:
                cleanup[str(pgid)] = type(exc).__name__ + ': ' + str(exc)[:128]
        try:
            process.wait(timeout=5)
        except Exception as exc:
            errors.append('supervisor reap: ' + type(exc).__name__)
        thread.join(timeout=3)
        control.save('first-cell-supervisor-cleanup.json', {'groups': cleanup, 'drain_finished': not thread.is_alive(),
                                                            'returncode': process.returncode, 'errors': errors})
    report_path = output / 'control/outer.json'
    if report_path.is_symlink() or not report_path.is_file() or report_path.stat().st_size > 65536:
        raise RuntimeError('missing or oversized supervisor report')
    report = json.loads(report_path.read_bytes())
    report['first_cell_cleanup_verified'] = not errors and not thread.is_alive() and all(v is True for v in cleanup.values())
    return report


def run(output, working, *, started, root=ROOT, mode='live', internal_seconds=3300, fault='none'):
    """Installation, supervisor, evidence and cleanup all charged to `started`."""
    root, output = Path(root), Path(output)
    if mode == 'live':
        from research.action_effect_history_v1.authority import consume_runtime, require
        require(root)
        if fault != 'none' or internal_seconds != 3300:
            raise PermissionError('live mode uses the frozen lifecycle and no faults')
        if not 0 <= time.monotonic() - started < 450:
            raise TimeoutError('first-cell installation deadline')
        consume_runtime(working, root)  # one attempt is consumed before installation
    else:
        from research.action_effect_history_v1.authority import rehearsal_gate
        rehearsal_gate()
    output.mkdir(parents=True, exist_ok=False)
    control = EvidenceStore(output, 'control')
    error, report, folder = None, None, None
    try:
        if mode == 'live':
            manifest = json.loads((root / 'reports/phase4_v2_offline_package.json').read_bytes())
            mount = Path('/kaggle/input/competitions/arc-prize-2026-arc-agi-3')
            candidates = [Path('/kaggle/input/datasets/driessmit1/arc3-vllm-h100-wheelhouse-v3'),
                          Path('/kaggle/input/arc3-vllm-h100-wheelhouse-v3')]
            wheelhouse = next(path for path in candidates if path.is_dir())
            with tempfile.TemporaryDirectory(prefix='action-effect-history-dependencies-') as folder:
                from certification.phase4_integrated_v2.game_assets import stage_games
                from certification.phase4_integrated_v2.prepare import prepare
                from certification.phase4_integrated_v2.dependencies import freeze, thaw
                rootdir = Path(folder)
                games = stage_games(mount / 'environment_files', rootdir / 'games', manifest)
                pair = prepare(rootdir, output, wheelhouse, mount / 'arc_agi_3_wheels', manifest, started)
                try:
                    freeze(rootdir)
                    report = run_supervisor(output, working, pair['game'], pair['model'], games, started=started,
                                            mode=mode, internal_seconds=internal_seconds, root=root)
                finally:
                    thaw(rootdir)
        else:
            games = Path(os.environ.get('AEH_REHEARSAL_GAMES', str(output / 'unused-environments')))
            report = run_supervisor(output, working, sys.executable, sys.executable, games,
                                    started=started, mode=mode, internal_seconds=internal_seconds, fault=fault, root=root)
    except Exception as exc:
        error = type(exc).__name__ + ': ' + str(exc)[:256]
    elapsed = time.monotonic() - started
    if elapsed >= internal_seconds:
        error = error or 'first-cell hard deadline exceeded'
    receipt = {'scope': 'action_effect_history_first_cell', 'mode': mode, 'elapsed_seconds': elapsed, 'error': error,
               'dependency_trees_removed': (not Path(folder).exists()) if folder else None,
               'study_status': report['status'] if report else None,
               'first_cell_cleanup_verified': report.get('first_cell_cleanup_verified') if report else None,
               'provider_reconciliation_required': mode == 'live', 'phase4_complete': False}
    control.save('notebook-cost.json', receipt)
    return receipt


def notebook_entry(source, started, mode):
    """Called by the notebook cell after source extraction and hash verification."""
    if mode == 'live':
        from research.action_effect_history_v1.authority import require
        require(source)
        working = Path('/kaggle/working')
        receipt = run(working / OUTPUT_NAME, working, started=started, root=source, mode='live')
    elif mode == 'rehearsal':
        working = Path(os.environ['AEH_REHEARSAL_WORKING'])
        receipt = run(working / OUTPUT_NAME, working, started=started, root=source, mode='rehearsal',
                      internal_seconds=int(os.environ.get('AEH_REHEARSAL_SECONDS', '600')),
                      fault=os.environ.get('AEH_REHEARSAL_FAULT', 'none'))
    else:
        raise ValueError('mode')
    if receipt['error'] or receipt['study_status'] != 'study_complete_pending_independent_evaluation':
        raise RuntimeError(receipt['error'] or 'study did not complete: ' + str(receipt['study_status']))
    return receipt
