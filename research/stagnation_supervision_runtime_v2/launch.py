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
    from research.stagnation_supervision_runtime_v2.ownership import recovery_inventory
    return recovery_inventory(output, supervisor_pid)[0]

def run_supervisor(output, working, game_python, model_python, games, *, started, mode, internal_seconds,
                   fault='none', root=ROOT, spawn=subprocess.Popen, session=None):
    """Protect startup ownership and retain cleanup even if startup or logging is interrupted (r2)."""
    from research.stagnation_supervision_runtime_v2.publisher_process import defer_startup_signals  # stdlib only
    root, output = Path(root), Path(output)
    log, control = EvidenceStore(output, 'logs'), EvidenceStore(output, 'control')
    errors, retained, cleanup = [], bytearray(), {}
    process, thread, ownership = None, None, 'never_spawned'
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
    env['PYTHONNOUSERSITE'], env['MPLBACKEND'] = '1', 'Agg'

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

    try:
        with defer_startup_signals():
            ownership = 'uncertain'  # entering Popen does not prove that no child was created
            process = spawn(command, cwd=root, env=env, start_new_session=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            # start_new_session fixes ownership to this PID, including a leader that exits early.
            cleanup[str(process.pid)] = False
            ownership = 'registered'
        thread = threading.Thread(target=drain, daemon=True)
        thread.start()
        while process.poll() is None:
            if errors:
                raise RuntimeError('supervisor log retention failed: ' + errors[0])
            if time.monotonic() >= started + internal_seconds - 5:
                raise TimeoutError('first-cell supervisor deadline')
            time.sleep(.05)
    finally:
        # Handled signals cannot skip a kill, reap or receipt during emergency cleanup.
        with defer_startup_signals():
            if process is not None:
                groups = [process.pid]
                inner_certain = False
                try:
                    # Freeze child creation before scanning recovery records. Undetached
                    # bootstraps are still in this group; detached children registered first.
                    cleanup[str(process.pid)] = _stop_group(process.pid)
                    process.wait(timeout=5)
                    from research.stagnation_supervision_runtime_v2.ownership import recovery_inventory
                    groups, inner_certain = recovery_inventory(output, process.pid)
                except BaseException as exc:
                    errors.append('ownership evidence: ' + type(exc).__name__)
                for pgid in groups:
                    try:
                        cleanup[str(pgid)] = _stop_group(pgid)
                    except BaseException as exc:
                        cleanup[str(pgid)] = type(exc).__name__ + ': ' + str(exc)[:128]
                        try:
                            os.killpg(pgid, signal.SIGKILL)
                            cleanup[str(pgid)] = _group_exited(pgid)
                        except BaseException:
                            pass
                try:
                    process.wait(timeout=5)
                except BaseException as exc:
                    errors.append('supervisor reap: ' + type(exc).__name__)
                if thread is not None and thread.ident is not None:
                    thread.join(timeout=3)
                elif process.stdout is not None:
                    process.stdout.close()
            absent = ownership == 'never_spawned' or (ownership == 'registered' and bool(cleanup)
                                                      and inner_certain and all(v is True for v in cleanup.values()))
            if ownership == 'uncertain':
                errors.append('spawn ownership uncertain; group absence cannot be verified')
            drained = thread is None or not thread.is_alive()
            control.save('first-cell-supervisor-cleanup.json', {
                'ownership': ownership, 'groups': cleanup, 'groups_absent': absent, 'drain_finished': drained,
                'child_ownership_verified': inner_certain if process is not None else ownership == 'never_spawned',
                'returncode': process.returncode if process else None, 'errors': errors,
                'checked_monotonic': time.monotonic()})
    report_path = output / 'control/outer.json'
    if report_path.is_symlink() or not report_path.is_file() or report_path.stat().st_size > 65536:
        raise RuntimeError('missing or oversized supervisor report')
    report = json.loads(report_path.read_bytes())
    report['first_cell_cleanup_verified'] = absent and drained and not errors
    return report


def run(output, working, *, started, root=ROOT, mode='live', internal_seconds=None, fault='none', session=None,
        staged_inputs=None, install_seconds=None, source_cleanup=None):
    """Installation, supervisor, evidence and cleanup all charged to `started`."""
    from research.stagnation_supervision_runtime_v2.authority import SESSION_LIMITS  # stdlib-only closure in the notebook interpreter
    LIVE_INTERNAL_SECONDS = {s: v['internal_seconds'] for s, v in SESSION_LIMITS.items()}  # 5100 / 4500
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
    except BaseException as exc:  # r2: an interruption is recorded, never a silent exit
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
    from research.stagnation_supervision_runtime_v2.publisher_process import defer_startup_signals
    pending = control.save('finalization-pending.json', {'scope': 'first_cell_finalization', 'pending': True})
    receipt.update(lifecycle_finalized=False, extracted_source_removed=None, finalization_guard_version=1)
    control.save('notebook-cost.json', receipt)
    try:
        if source_cleanup is not None:
            source_cleanup()
            receipt['extracted_source_removed'] = True
    except BaseException as exc:
        receipt['extracted_source_removed'] = False
        receipt['error'] = receipt['error'] or 'source cleanup: ' + type(exc).__name__
    receipt['elapsed_seconds'] = time.monotonic() - started
    if receipt['elapsed_seconds'] >= internal_seconds:
        receipt['error'] = receipt['error'] or 'first-cell hard deadline exceeded during finalization'
    try:
        # Handled cutoff/interrupt signals are replayed inside this try, after the write and checks.
        with defer_startup_signals():
            receipt['lifecycle_finalized'] = True
            control.save('notebook-cost.json', receipt)
            receipt['elapsed_seconds'] = time.monotonic() - started
            if receipt['elapsed_seconds'] >= internal_seconds:
                raise TimeoutError('first-cell hard deadline exceeded during final evidence write')
            if receipt['error'] is None:
                pending.unlink()
                # Removing the barrier is charged too; any interruption/overrun revokes certification.
                receipt['elapsed_seconds'] = time.monotonic() - started
                if receipt['elapsed_seconds'] >= internal_seconds:
                    raise TimeoutError('first-cell hard deadline exceeded during finalization commit')
    except BaseException as exc:
        receipt['lifecycle_finalized'] = False
        receipt['elapsed_seconds'] = time.monotonic() - started
        receipt['error'] = receipt['error'] or 'finalization: ' + type(exc).__name__ + ': ' + str(exc)[:192]
        with defer_startup_signals():
            # Invalidate first, before emergency writes: failed storage must not leave a passing receipt.
            (output / 'control/notebook-cost.json').unlink(missing_ok=True)
            control.save('finalization-pending.json', {'scope': 'first_cell_finalization', 'pending': True})
            control.save('notebook-cost.json', receipt)
    return receipt


def notebook_entry(source, started, mode, session):
    """Called by the notebook cell after source extraction and hash verification. r2: the extracted source is
    removed inside the charged lifecycle; only a tree carrying the cell's extraction prefix is ever removed
    (in live mode any other tree fails finalization; a rehearsal from a checkout removes nothing)."""
    import shutil
    extracted = Path(source).name.startswith('stagnation-supervision-runtime-v2-source-')

    def remove_source():
        if not extracted:
            raise ValueError('refusing to remove a tree that is not the extracted payload')
        shutil.rmtree(source)
    if mode == 'live':
        from research.stagnation_supervision_runtime_v2.authority import require
        require(source)
        working = Path('/kaggle/working')
        receipt = run(working / OUTPUT_NAME, working, started=started, root=source, mode='live', session=session,
                      source_cleanup=remove_source)
    elif mode == 'rehearsal':
        working = Path(os.environ['SSV_REHEARSAL_WORKING'])
        receipt = run(working / OUTPUT_NAME, working, started=started, root=source, mode='rehearsal', session=session,
                      internal_seconds=int(os.environ.get('SSV_REHEARSAL_SECONDS', '600')),
                      fault=os.environ.get('SSV_REHEARSAL_FAULT', 'none'),
                      staged_inputs=os.environ.get('SSV_RUNTIME_V2_STAGED_INPUTS') or None,
                      install_seconds=(int(os.environ['SSV_RUNTIME_V2_REHEARSAL_INSTALL_SECONDS'])
                                       if os.environ.get('SSV_RUNTIME_V2_REHEARSAL_INSTALL_SECONDS') else None),
                      source_cleanup=remove_source if extracted else None)
    else:
        raise ValueError('mode')
    if receipt['error'] or receipt['study_status'] != 'study_complete_pending_independent_evaluation':
        raise RuntimeError(receipt['error'] or 'study did not complete: ' + str(receipt['study_status']))
    return receipt
