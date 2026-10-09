# Derived from scripts/stagnation_supervision_v1_launch.py at bc19919 by scripts/derive_stagnation_supervision_runtime_v2.py; edit the derivation, not this file.
# Derived from scripts/action_effect_history_v1_launch.py by scripts/derive_stagnation_supervision_v1.py; edit the derivation, not this file.
"""First-cell lifecycle for one stagnation-supervision session (live needs separate reviewed authority)."""
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

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_NAME = 'stagnation-supervision-v1-runtime-v2'


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
                   fault='none', root=ROOT, spawn=subprocess.Popen, session=None):
    """Own the supervisor's session and every group it records; verify all are gone."""
    root, output = Path(root), Path(output)
    log, control = EvidenceStore(output, 'logs'), EvidenceStore(output, 'control')
    errors, retained = [], bytearray()
    command = [str(game_python), '-m', 'research.stagnation_supervision_runtime_v2.supervisor', '--output', str(output),
               '--working', str(working), '--game-python', str(game_python), '--model-python', str(model_python),
               '--environments', str(games), '--started', str(started), '--mode', mode,
               '--internal-seconds', str(internal_seconds), '--fault', fault,
               '--session', str(session)]
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
                                                            'returncode': process.returncode, 'errors': errors,
                                                            'checked_monotonic': time.monotonic()})
    report_path = output / 'control/outer.json'
    if report_path.is_symlink() or not report_path.is_file() or report_path.stat().st_size > 65536:
        raise RuntimeError('missing or oversized supervisor report')
    report = json.loads(report_path.read_bytes())
    report['first_cell_cleanup_verified'] = not errors and not thread.is_alive() and all(v is True for v in cleanup.values())
    return report


def run(output, working, *, started, root=ROOT, mode='live', internal_seconds=None, fault='none', session=None,
        staged_inputs=None, install_seconds=None):
    """Installation, supervisor, evidence and cleanup all charged to `started`."""
    from research.stagnation_supervision_runtime_v2.supervisor import LIVE_INTERNAL_SECONDS
    if str(session) not in LIVE_INTERNAL_SECONDS:
        raise ValueError('unknown session')
    internal_seconds = LIVE_INTERNAL_SECONDS[str(session)] if internal_seconds is None else internal_seconds
    root, output = Path(root), Path(output)
    if mode == 'live':
        from research.stagnation_supervision_runtime_v2.authority import consume_runtime, require
        if staged_inputs is not None or install_seconds is not None:
            raise PermissionError('staged inputs and installation overrides are rehearsal-only')
        execution = require(root)
        if str(execution.get('session')) != str(session):
            raise PermissionError('launch session differs from the approved execution')
        if fault != 'none' or internal_seconds != LIVE_INTERNAL_SECONDS[str(session)]:
            raise PermissionError('live mode uses the frozen lifecycle and no faults')
        if not 0 <= time.monotonic() - started < 450:
            raise TimeoutError('first-cell installation deadline')
        consume_runtime(working, root)  # one attempt is consumed before installation
    else:
        from research.stagnation_supervision_runtime_v2.authority import rehearsal_gate
        rehearsal_gate()
    output.mkdir(parents=True, exist_ok=False)
    control = EvidenceStore(output, 'control')
    error, report, folder = None, None, None
    try:
        if mode == 'live' or staged_inputs is not None:
            manifest = json.loads((root / 'reports/phase4_v2_offline_package.json').read_bytes())
            from research.stagnation_supervision_runtime_v2.mounts import competition_mount, wheelhouse_mount
            mount = competition_mount(root, inputs=staged_inputs)
            wheelhouse = wheelhouse_mount(root, inputs=staged_inputs)
            with tempfile.TemporaryDirectory(prefix='stagnation-supervision-dependencies-') as folder:
                from certification.phase4_integrated_v2.game_assets import stage_games
                from research.stagnation_supervision_runtime_v2.prepare import prepare
                from certification.phase4_integrated_v2.dependencies import freeze, thaw
                rootdir = Path(folder)
                games = stage_games(mount / 'environment_files', rootdir / 'games', manifest)
                pair = prepare(rootdir, output, wheelhouse, mount / 'arc_agi_3_wheels', manifest, started,
                               root=root, install_seconds=install_seconds)
                try:
                    freeze(rootdir)
                    report = run_supervisor(output, working, pair['game'], pair['model'], games, started=started,
                                            mode=mode, internal_seconds=internal_seconds, root=root, session=session)
                finally:
                    thaw(rootdir)
        else:
            games = Path(os.environ.get('SSV_REHEARSAL_GAMES', str(output / 'unused-environments')))
            report = run_supervisor(output, working, sys.executable, sys.executable, games,
                                    started=started, mode=mode, internal_seconds=internal_seconds, fault=fault, root=root,
                                    session=session)
    except Exception as exc:
        error = type(exc).__name__ + ': ' + str(exc)[:256]
    elapsed = time.monotonic() - started
    if elapsed >= internal_seconds:
        error = error or 'first-cell hard deadline exceeded'
    receipt = {'scope': 'stagnation_supervision_first_cell', 'mode': mode, 'session': str(session), 'elapsed_seconds': elapsed, 'error': error,
               'first_cell_monotonic': started, 'internal_seconds': internal_seconds,
               'dependency_trees_removed': (not Path(folder).exists()) if folder else None,
               'study_status': report['status'] if report else None,
               'first_cell_cleanup_verified': report.get('first_cell_cleanup_verified') if report else None,
               'provider_reconciliation_required': mode == 'live', 'phase4_complete': False,
               'installation': ('target' if mode == 'live' else
                                'staged_rehearsal' if staged_inputs is not None else 'none'),
               'runtime_binding': 'stagnation-supervision-v1-runtime-v2'}
    control.save('notebook-cost.json', receipt)
    return receipt


def notebook_entry(source, started, mode, session):
    """Called by the notebook cell after source extraction and hash verification."""
    if mode == 'live':
        from research.stagnation_supervision_runtime_v2.authority import require
        require(source)
        working = Path('/kaggle/working')
        receipt = run(working / OUTPUT_NAME, working, started=started, root=source, mode='live', session=session)
    elif mode == 'rehearsal':
        working = Path(os.environ['SSV_REHEARSAL_WORKING'])
        receipt = run(working / OUTPUT_NAME, working, started=started, root=source, mode='rehearsal', session=session,
                      internal_seconds=int(os.environ.get('SSV_REHEARSAL_SECONDS', '600')),
                      fault=os.environ.get('SSV_REHEARSAL_FAULT', 'none'),
                      staged_inputs=os.environ.get('SSV_RUNTIME_V2_STAGED_INPUTS') or None,
                      install_seconds=(int(os.environ['SSV_RUNTIME_V2_REHEARSAL_INSTALL_SECONDS'])
                                       if os.environ.get('SSV_RUNTIME_V2_REHEARSAL_INSTALL_SECONDS') else None))
    else:
        raise ValueError('mode')
    if receipt['error'] or receipt['study_status'] != 'study_complete_pending_independent_evaluation':
        raise RuntimeError(receipt['error'] or 'study did not complete: ' + str(receipt['study_status']))
    return receipt
