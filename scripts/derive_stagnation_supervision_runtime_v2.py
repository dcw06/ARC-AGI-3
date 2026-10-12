"""Derive the Track 3 runtime-binding successor (runtime v2) from two frozen sources; CPU only, no provider calls.

Sources (each identified by commit, path and SHA-256, verified before use):
  * the verified GPU runtime: branch wheelhouse-replacement-audit at REFERENCE_COMMIT, whose
    certification/direct_publisher_smoke_v1 modules ran the control-interface v2 probe (one RTX PRO 6000,
    CPython 3.12 image, full cleanup);
  * the Track 3 R4 runtime: branch track3-stagnation-supervision-v1 at TRACK3_COMMIT.

Every derived file is the source plus an explicit, ordered list of literal replacements. Each replacement's old
text occurs exactly `count` times in the source and its new text occurs nowhere in the source, so the derivation is
invertible: `inverse_check` reproduces the exact source bytes from the derived file and its record, without git.
Data files are copied byte-for-byte. The runtime protocol is built from the reference protocol, the reference
model-attachment inventory and the unchanged Track 3 science files.

    python -m scripts.derive_stagnation_supervision_runtime_v2            # write (refuses to overwrite drift)
    python -m scripts.derive_stagnation_supervision_runtime_v2 --check    # re-derive from git objects and compare

Nothing here grants authority, reserves compute, contacts a provider or creates an approval record.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'research/stagnation_supervision_runtime_v2'
RECORD = PACKAGE + '/derivation.json'
REFERENCE_BRANCH = 'wheelhouse-replacement-audit'
REFERENCE_COMMIT = '5a21dd339d22ec6e13307722b42dcef0882f6829'
TRACK3_BRANCH = 'track3-stagnation-supervision-v1'
TRACK3_COMMIT = 'bc19919dace8dd919bf5617174534526783c159d'
HEADER = ('# Derived from {path} at {commit} by scripts/derive_stagnation_supervision_runtime_v2.py; '
          'edit the derivation, not this file.\n')
RT = 'research.stagnation_supervision_runtime_v2'
CL = 'research.stagnation_supervision_v1.closed_loop'

REFERENCE = {  # derived path: (source path, source sha256, replacements)
    'publisher_preflight.py': ('certification/direct_publisher_smoke_v1/preflight.py', None, []),
    'publisher_process.py': ('certification/direct_publisher_smoke_v1/server.py', None, []),
    'publisher_host.py': ('certification/direct_publisher_smoke_v1/host.py', None, []),
    'publisher_install.py': ('certification/direct_publisher_smoke_v1/install.py', None, [
        ('from certification.direct_publisher_smoke_v1.server import ModelServer, defer_startup_signals',
         f'from {RT}.publisher_process import ModelServer, defer_startup_signals', 1),
        ('    from certification.direct_publisher_smoke_v1.preflight import PACKAGE, load_inputs, verify_mounted',
         f'    from {RT}.publisher_preflight import PACKAGE, load_inputs, verify_mounted', 1)]),
}
REFERENCE_DATA = {  # copied byte-for-byte
    'proposal.json': 'certification/direct_publisher_smoke_v1/proposal.json',
    'trusted_manifest.json': 'certification/direct_publisher_smoke_v1/trusted_manifest.json',
    'trusted_requirements.lock': 'certification/direct_publisher_smoke_v1/trusted_requirements.lock',
}
REFERENCE_INPUTS = {  # read to build the protocol; not copied
    'protocol': 'research/control_interface_action_selection_v2/protocol.json',
    'model_attachment': 'reports/direct_publisher_smoke_v1/qwen_upstream_attachment_candidate_2026-10-07.json',
}

PARENTS = ('ROOT = Path(__file__).resolve().parents[3]', 'ROOT = Path(__file__).resolve().parents[2]', 1)
TRACK3 = {
    'supervisor.py': ('research/stagnation_supervision_v1/closed_loop/supervisor.py', [
        ('from .resources import independent_cleanup, probes_for',
         f'from {RT}.resources import independent_cleanup, probes_for', 1),
        PARENTS,
        ('    from .worker import gate as worker_gate', f'    from {RT}.worker import gate as worker_gate', 1),
        ('    from .worker import FAULTS as WORKER_FAULTS', f'    from {RT}.worker import FAULTS as WORKER_FAULTS', 1),
        ('        from .authority import consume_runtime, verify_runtime_claim',
         f'        from {RT}.authority import consume_runtime, verify_runtime_claim', 1),
        (f"'{CL}.worker'", f"'{RT}.worker'", 1),
        (f"'{CL}.monitor'", f"'{RT}.monitor'", 1),
        ('        from .evidence import load_verified', f'        from {CL}.evidence import load_verified', 1)]),
    'worker.py': ('research/stagnation_supervision_v1/closed_loop/worker.py', [
        ('from .model_service import ProxyService', f'from {CL}.model_service import ProxyService', 1),
        PARENTS,
        ('        from .authority import require\n        return require()',
         f'        from {RT}.authority import require\n        return require()', 1),
        ('        from .authority import rehearsal_gate', f'        from {RT}.authority import rehearsal_gate', 1),
        (f"'{CL}.host'", f"'{RT}.host'", 2),
        ('        from .engine import DevelopmentAdapter\n        from .runner import run\n'
         '        from .bridge import session_run_spec, supervision_factory, worker_token_counter',
         f'        from {CL}.engine import DevelopmentAdapter\n        from {CL}.runner import run\n'
         f'        from {CL}.bridge import session_run_spec, supervision_factory, worker_token_counter', 1)]),
    'host.py': ('research/stagnation_supervision_v1/closed_loop/host.py', [
        ('from .model_service import SupervisionModelService', f'from {CL}.model_service import SupervisionModelService', 1),
        PARENTS,
        ('    from research.grounded_action_v1.artifact_contract import expected_artifact as frozen\n'
         '    return frozen(root)  # the same pinned model tree as every earlier run',
         f'    from {RT}.model_binding import expected_artifact as bound\n'
         "    return bound(root)  # runtime v2: the verified runtime's version-pinned dataset snapshot", 1),
        ('    from certification.phase4_integrated_v2.model_artifact import verify_artifact\n',
         '    from certification.phase4_integrated_v2.model_artifact import verify_artifact\n'
         f'    from {RT}.model_binding import bind_primary\n', 1),
        ("    primary = replace(load_operational_primary(ROOT), scratch_log=Path('/dev/stdout'),",
         "    primary = bind_primary(ROOT, replace(load_operational_primary(ROOT), scratch_log=Path('/dev/stdout'),", 1),
        ('                      hard_seconds=5100, finalization_reserve_seconds=300)  # the longer session',
         '                      hard_seconds=5100, finalization_reserve_seconds=300))  # the longer session;'
         ' runtime v2 binds the verified mount and tree pin', 1),
        ('    from .authority import rehearsal_gate\n    from .rehearsal import FixtureTokenizer, ScriptedTransport',
         f'    from {RT}.authority import rehearsal_gate\n    from {CL}.rehearsal import FixtureTokenizer, ScriptedTransport', 1),
        ('    from .server_config import rehearsal_record', f'    from {CL}.server_config import rehearsal_record', 1),
        ('        from .server_config import KIND', f'        from {CL}.server_config import KIND', 1),
        ('        from .authority import require\n        require()  # before model import, subprocess or GPU query',
         f'        from {RT}.authority import require\n        require()  # before model import, subprocess or GPU query', 1),
        ('    from .server_config import model_owner', f'    from {CL}.server_config import model_owner', 1)]),
    'monitor.py': ('research/stagnation_supervision_v1/closed_loop/monitor.py', [
        ('from .resources import probes_for', f'from {RT}.resources import probes_for', 1),
        ('        from .authority import require\n        require()', f'        from {RT}.authority import require\n        require()', 1)]),
    'resources.py': ('research/stagnation_supervision_v1/closed_loop/resources.py', [
        ('        from .authority import require\n', f'        from {RT}.authority import require\n', 1),
        ('        from .authority import rehearsal_gate\n', f'        from {RT}.authority import rehearsal_gate\n', 1)]),
    'target_evaluate.py': ('research/stagnation_supervision_v1/closed_loop/target_evaluate.py', [
        ('from . import evaluate as trajectories\nfrom .model_service import validate_ready\n'
         'from .server_config import validate as validate_configuration',
         f'from {CL} import evaluate as trajectories\nfrom {CL}.model_service import validate_ready\n'
         f'from {CL}.server_config import validate as validate_configuration', 1),
        ("VERSION = 'stagnation_supervision_target_evaluation_r1'",
         "VERSION = 'stagnation_supervision_target_evaluation_runtime_v2_r3'", 1),
        # r2: certify the fail-closed finalization and the protected startup ownership independently (Track 1 lessons).
        ("    require(first['study_status'] == outer['status'] == 'study_complete_pending_independent_evaluation', 'lifecycle status')\n",
         "    require(first['study_status'] == outer['status'] == 'study_complete_pending_independent_evaluation',\n"
         "            'lifecycle status')\n"
         "    pending = root / 'control/finalization-pending.json'\n"
         "    require(first.get('finalization_guard_version') == 1 and first.get('lifecycle_finalized') is True\n"
         "            and not pending.exists() and not pending.is_symlink()\n"
         "            and (mode != 'live' or first.get('extracted_source_removed') is True),\n"
         "            'lifecycle finalization/source removal not certified')\n", 1),
        ("    require(cleanup['drain_finished'] is True and cleanup['returncode'] == 0 and cleanup['errors'] == [], 'first-cell process/log cleanup')\n",
         "    require(cleanup['drain_finished'] is True and cleanup['returncode'] == 0 and cleanup['errors'] == []\n"
         "            and cleanup.get('ownership') == 'registered' and cleanup.get('groups_absent') is True,\n"
         "            'first-cell process/log cleanup')\n", 1),
        ('    from .authority import SESSION_LIMITS\n    from .evidence import load_verified',
         f'    from {RT}.authority import SESSION_LIMITS\n    from {CL}.evidence import load_verified', 1),
        ('        from .bridge import session_spec\n        from .runner import protocol',
         f'        from {CL}.bridge import session_spec\n        from {CL}.runner import protocol', 1),
        ("    require(first['dependency_trees_removed'] is (True if mode == 'live' else None), 'dependency cleanup')",
         "    require(first.get('installation') == ('target' if mode == 'live' else first.get('installation'))\n"
         "            and first.get('installation') in (('target',) if mode == 'live' else ('none', 'staged_rehearsal')),\n"
         "            'runtime v2 installation class')\n"
         "    require(first['dependency_trees_removed'] is (True if first['installation'] != 'none' else None),"
         " 'dependency cleanup')", 1),
        ('    from .host import expected_artifact', f'    from {RT}.host import expected_artifact', 1)]),
    'launch.py': ('scripts/stagnation_supervision_v1_launch.py', [
        ("ROOT = Path(__file__).resolve().parents[1]\nOUTPUT_NAME = 'stagnation-supervision-v1'",
         "ROOT = Path(__file__).resolve().parents[2]\nOUTPUT_NAME = 'stagnation-supervision-v1-runtime-v2'", 1),
        (f"'{CL}.supervisor'", f"'{RT}.supervisor'", 1),
        # r2 (Track 1 lessons, 3aeeb65): protect startup ownership and retain a cleanup receipt even when startup,
        # registration or log retention is interrupted; an uncertain spawn never claims that the groups are absent.
        ('    """Own the supervisor\'s session and every group it records; verify all are gone."""\n',
         '    """Protect startup ownership and retain cleanup even if startup or logging is interrupted (r2)."""\n'
         f'    from {RT}.publisher_process import defer_startup_signals  # stdlib only\n', 1),
        ('    errors, retained = [], bytearray()\n',
         '    errors, retained, cleanup = [], bytearray(), {}\n'
         "    process, thread, ownership = None, None, 'never_spawned'\n", 1),
        ("    env['PYTHONNOUSERSITE'] = '1'\n    env['MPLBACKEND'] = 'Agg'\n"
         '    process = spawn(command, cwd=root, env=env, start_new_session=True, stdout=subprocess.PIPE, '
         'stderr=subprocess.STDOUT)\n',
         "    env['PYTHONNOUSERSITE'], env['MPLBACKEND'] = '1', 'Agg'\n", 1),
        ('    thread = threading.Thread(target=drain, daemon=True)\n    thread.start()\n    cleanup = {}\n    try:\n',
         '    try:\n'
         '        with defer_startup_signals():\n'
         "            ownership = 'uncertain'  # entering Popen does not prove that no child was created\n"
         '            process = spawn(command, cwd=root, env=env, start_new_session=True,\n'
         '                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)\n'
         '            # start_new_session fixes ownership to this PID, including a leader that exits early.\n'
         '            cleanup[str(process.pid)] = False\n'
         "            ownership = 'registered'\n"
         '        thread = threading.Thread(target=drain, daemon=True)\n'
         '        thread.start()\n', 1),
        ('    finally:\n'
         '        groups = [process.pid]\n'
         '        try:\n'
         '            groups = _owned_groups(output, process.pid)\n'
         '        except Exception as exc:\n'
         "            errors.append('ownership evidence: ' + type(exc).__name__)\n"
         '        for pgid in groups:\n'
         '            try:\n'
         '                cleanup[str(pgid)] = _stop_group(pgid)\n'
         '            except Exception as exc:\n'
         "                cleanup[str(pgid)] = type(exc).__name__ + ': ' + str(exc)[:128]\n"
         '        try:\n'
         '            process.wait(timeout=5)\n'
         '        except Exception as exc:\n'
         "            errors.append('supervisor reap: ' + type(exc).__name__)\n"
         '        thread.join(timeout=3)\n'
         "        control.save('first-cell-supervisor-cleanup.json', {'groups': cleanup, 'drain_finished': not thread.is_alive(),\n"
         "                                                            'returncode': process.returncode, 'errors': errors,\n"
         "                                                            'checked_monotonic': time.monotonic()})\n",
         '    finally:\n'
         '        # Handled signals cannot skip a kill, reap or receipt during emergency cleanup.\n'
         '        with defer_startup_signals():\n'
         '            if process is not None:\n'
         '                groups = [process.pid]\n'
         '                try:\n'
         '                    groups = _owned_groups(output, process.pid)\n'
         '                except BaseException as exc:\n'
         "                    errors.append('ownership evidence: ' + type(exc).__name__)\n"
         '                for pgid in groups:\n'
         '                    try:\n'
         '                        cleanup[str(pgid)] = _stop_group(pgid)\n'
         '                    except BaseException as exc:\n'
         "                        cleanup[str(pgid)] = type(exc).__name__ + ': ' + str(exc)[:128]\n"
         '                        try:\n'
         '                            os.killpg(pgid, signal.SIGKILL)\n'
         '                            cleanup[str(pgid)] = _group_exited(pgid)\n'
         '                        except BaseException:\n'
         '                            pass\n'
         '                try:\n'
         '                    process.wait(timeout=5)\n'
         '                except BaseException as exc:\n'
         "                    errors.append('supervisor reap: ' + type(exc).__name__)\n"
         '                if thread is not None and thread.ident is not None:\n'
         '                    thread.join(timeout=3)\n'
         '                elif process.stdout is not None:\n'
         '                    process.stdout.close()\n'
         "            absent = ownership == 'never_spawned' or (ownership == 'registered' and bool(cleanup)\n"
         '                                                      and all(v is True for v in cleanup.values()))\n'
         "            if ownership == 'uncertain':\n"
         "                errors.append('spawn ownership uncertain; group absence cannot be verified')\n"
         '            drained = thread is None or not thread.is_alive()\n'
         "            control.save('first-cell-supervisor-cleanup.json', {\n"
         "                'ownership': ownership, 'groups': cleanup, 'groups_absent': absent, 'drain_finished': drained,\n"
         "                'returncode': process.returncode if process else None, 'errors': errors,\n"
         "                'checked_monotonic': time.monotonic()})\n", 1),
        ("    report['first_cell_cleanup_verified'] = not errors and not thread.is_alive() and all(v is True for v in cleanup.values())\n",
         "    report['first_cell_cleanup_verified'] = absent and drained and not errors\n", 1),
        ("def run(output, working, *, started, root=ROOT, mode='live', internal_seconds=None, fault='none', session=None):",
         "def run(output, working, *, started, root=ROOT, mode='live', internal_seconds=None, fault='none', session=None,\n"
         "        staged_inputs=None, install_seconds=None, source_cleanup=None):", 1),
        # The notebook (image) interpreter has no game packages: importing the supervisor module here pulls
        # agent -> arcengine into it (found by the staged CPU rehearsal on a base CPython 3.12 interpreter; the
        # action-effect-history v1 launcher that ran live never imported it). The values are identical.
        (f'    from {CL}.supervisor import LIVE_INTERNAL_SECONDS',
         f'    from {RT}.authority import SESSION_LIMITS  # stdlib-only closure in the notebook interpreter\n'
         "    LIVE_INTERNAL_SECONDS = {s: v['internal_seconds'] for s, v in SESSION_LIMITS.items()}  # 5100 / 4500", 1),
        (f"    if mode == 'live':\n        from {CL}.authority import consume_runtime, require\n        execution = require(root)",
         f"    if mode == 'live':\n        from {RT}.authority import consume_runtime, require\n"
         "        if staged_inputs is not None or install_seconds is not None:\n"
         "            raise PermissionError('staged inputs and installation overrides are rehearsal-only')\n"
         "        execution = require(root)", 1),
        (f'        from {CL}.authority import rehearsal_gate', f'        from {RT}.authority import rehearsal_gate', 1),
        ("        if mode == 'live':\n"
         "            manifest = json.loads((root / 'reports/phase4_v2_offline_package.json').read_bytes())\n"
         "            mount = Path('/kaggle/input/competitions/arc-prize-2026-arc-agi-3')\n"
         "            candidates = [Path('/kaggle/input/datasets/driessmit1/arc3-vllm-h100-wheelhouse-v3'),\n"
         "                          Path('/kaggle/input/arc3-vllm-h100-wheelhouse-v3')]\n"
         "            wheelhouse = next(path for path in candidates if path.is_dir())\n",
         "        if mode == 'live' or staged_inputs is not None:\n"
         "            manifest = json.loads((root / 'reports/phase4_v2_offline_package.json').read_bytes())\n"
         f"            from {RT}.mounts import competition_mount, wheelhouse_mount\n"
         "            mount = competition_mount(root, inputs=staged_inputs)\n"
         "            wheelhouse = wheelhouse_mount(root, inputs=staged_inputs)\n", 1),
        ('                from certification.phase4_integrated_v2.prepare import prepare\n',
         f'                from {RT}.prepare import prepare\n', 1),
        ("                pair = prepare(rootdir, output, wheelhouse, mount / 'arc_agi_3_wheels', manifest, started)",
         "                pair = prepare(rootdir, output, wheelhouse, mount / 'arc_agi_3_wheels', manifest, started,\n"
         "                               root=root, install_seconds=install_seconds)", 1),
        ('    except Exception as exc:\n        error = type(exc).__name__ + \': \' + str(exc)[:256]\n',
         '    except BaseException as exc:  # r2: an interruption is recorded, never a silent exit\n'
         '        error = type(exc).__name__ + \': \' + str(exc)[:256]\n', 1),
        ("               'provider_reconciliation_required': mode == 'live', 'phase4_complete': False}",
         "               'provider_reconciliation_required': mode == 'live', 'phase4_complete': False,\n"
         "               'installation': ('target' if mode == 'live' else\n"
         "                                'staged_rehearsal' if staged_inputs is not None else 'none'),\n"
         "               'runtime_binding': 'stagnation-supervision-v1-runtime-v2'}", 1),
        # r2 (Track 1 lessons, 3aeeb65 and cfda982): fail-closed finalization. A durable barrier makes every receipt
        # provisional until a bounded transaction completes; source removal and the final writes are charged to the
        # first-cell clock; any interruption or overrun revokes certification. The evaluator checks it independently.
        ("    control.save('notebook-cost.json', receipt)\n    return receipt\n",
         "    from research.stagnation_supervision_runtime_v2.publisher_process import defer_startup_signals\n"
         "    pending = control.save('finalization-pending.json', {'scope': 'first_cell_finalization', 'pending': True})\n"
         "    receipt.update(lifecycle_finalized=False, extracted_source_removed=None, finalization_guard_version=1)\n"
         "    control.save('notebook-cost.json', receipt)\n"
         "    try:\n"
         "        if source_cleanup is not None:\n"
         "            source_cleanup()\n"
         "            receipt['extracted_source_removed'] = True\n"
         "    except BaseException as exc:\n"
         "        receipt['extracted_source_removed'] = False\n"
         "        receipt['error'] = receipt['error'] or 'source cleanup: ' + type(exc).__name__\n"
         "    receipt['elapsed_seconds'] = time.monotonic() - started\n"
         "    if receipt['elapsed_seconds'] >= internal_seconds:\n"
         "        receipt['error'] = receipt['error'] or 'first-cell hard deadline exceeded during finalization'\n"
         "    try:\n"
         "        # Handled cutoff/interrupt signals are replayed inside this try, after the write and checks.\n"
         "        with defer_startup_signals():\n"
         "            receipt['lifecycle_finalized'] = True\n"
         "            control.save('notebook-cost.json', receipt)\n"
         "            receipt['elapsed_seconds'] = time.monotonic() - started\n"
         "            if receipt['elapsed_seconds'] >= internal_seconds:\n"
         "                raise TimeoutError('first-cell hard deadline exceeded during final evidence write')\n"
         "            if receipt['error'] is None:\n"
         "                pending.unlink()\n"
         "                # Removing the barrier is charged too; any interruption/overrun revokes certification.\n"
         "                receipt['elapsed_seconds'] = time.monotonic() - started\n"
         "                if receipt['elapsed_seconds'] >= internal_seconds:\n"
         "                    raise TimeoutError('first-cell hard deadline exceeded during finalization commit')\n"
         "    except BaseException as exc:\n"
         "        receipt['lifecycle_finalized'] = False\n"
         "        receipt['elapsed_seconds'] = time.monotonic() - started\n"
         "        receipt['error'] = receipt['error'] or 'finalization: ' + type(exc).__name__ + ': ' + str(exc)[:192]\n"
         "        with defer_startup_signals():\n"
         "            # Invalidate first, before emergency writes: failed storage must not leave a passing receipt.\n"
         "            (output / 'control/notebook-cost.json').unlink(missing_ok=True)\n"
         "            control.save('finalization-pending.json', {'scope': 'first_cell_finalization', 'pending': True})\n"
         "            control.save('notebook-cost.json', receipt)\n"
         "    return receipt\n", 1),
        ('    """Called by the notebook cell after source extraction and hash verification."""\n',
         '    """Called by the notebook cell after source extraction and hash verification. r2: the extracted source is\n'
         '    removed inside the charged lifecycle; only a tree carrying the cell\'s extraction prefix is ever removed\n'
         '    (in live mode any other tree fails finalization; a rehearsal from a checkout removes nothing)."""\n'
         '    import shutil\n'
         "    extracted = Path(source).name.startswith('stagnation-supervision-runtime-v2-source-')\n"
         '\n'
         '    def remove_source():\n'
         '        if not extracted:\n'
         "            raise ValueError('refusing to remove a tree that is not the extracted payload')\n"
         '        shutil.rmtree(source)\n', 1),
        ("        receipt = run(working / OUTPUT_NAME, working, started=started, root=source, mode='live', session=session)",
         "        receipt = run(working / OUTPUT_NAME, working, started=started, root=source, mode='live', session=session,\n"
         "                      source_cleanup=remove_source)", 1),
        (f'        from {CL}.authority import require\n        require(source)',
         f'        from {RT}.authority import require\n        require(source)', 1),
        ("                      fault=os.environ.get('SSV_REHEARSAL_FAULT', 'none'))",
         "                      fault=os.environ.get('SSV_REHEARSAL_FAULT', 'none'),\n"
         "                      staged_inputs=os.environ.get('SSV_RUNTIME_V2_STAGED_INPUTS') or None,\n"
         "                      install_seconds=(int(os.environ['SSV_RUNTIME_V2_REHEARSAL_INSTALL_SECONDS'])\n"
         "                                       if os.environ.get('SSV_RUNTIME_V2_REHEARSAL_INSTALL_SECONDS') else None),\n"
         "                      source_cleanup=remove_source if extracted else None)", 1)]),
}

# r3 independent prelaunch repairs; literal, invertible changes over the frozen sources.
PRELAUNCH_REPAIRS = {'supervisor.py': [('    rfd = wfd = None\n    uuid = None\n',
                    '    rfd = wfd = None\n'
                    '    uuid = None\n'
                    '    from research.stagnation_supervision_runtime_v2.ownership import ChildOwners\n'
                    '    from research.stagnation_supervision_runtime_v2.publisher_process import '
                    'defer_startup_signals\n'
                    '    nonce = secrets.token_hex(32)\n'
                    '    owners = ChildOwners(output, started, nonce)\n',
                    1),
                   ('    def launch(argv, *, env=None, pass_fds=()):\n'
                    '        process = spawn(argv, cwd=ROOT, env=env, pass_fds=pass_fds, '
                    'start_new_session=True,\n'
                    '                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)\n'
                    '        processes.append(process)\n'
                    '        thread = threading.Thread(target=drain, args=(process, str(process.pid)), '
                    'daemon=True)\n'
                    '        thread.start()\n'
                    '        drains.append(thread)\n'
                    '        return process\n',
                    '    def launch(argv, *, env=None, pass_fds=()):\n'
                    '        with defer_startup_signals():\n'
                    "            role = 'worker' if not processes else 'monitor'\n"
                    '            process = owners.start(role, argv, spawn=spawn, cwd=ROOT, env=env, '
                    'pass_fds=pass_fds)\n'
                    '            processes.append(process)\n'
                    '            thread = threading.Thread(target=drain, args=(process, str(process.pid)), '
                    'daemon=True)\n'
                    '            drains.append(thread)\n'
                    '            thread.start()\n'
                    '        return process\n',
                    1),
                   ('        try:\n            env = worker_environment(os.environ, scratch)',
                    '        try:\n'
                    '            owners.save()\n'
                    '            env = worker_environment(os.environ, scratch)',
                    1),
                   ('            nonce = secrets.token_hex(32)\n', '            # Nonce fixed before child creation.\n', 1),
                   ("            control.save('ownership.json', {'worker_pgid': worker.pid, 'monitor_pgid': "
                    "monitor.pid, 'nonce': nonce,\n"
                    "                                            'first_cell_monotonic': started})",
                    '            owners.save()  # both per-child recovery records already exist',
                    1),
                   ("        except Exception as exc:\n            report['error'] =",
                    "        except BaseException as exc:\n            report['error'] =",
                    1),
                   ('        finally:\n'
                    '            for fd in (rfd, wfd):\n'
                    '                if fd is not None:\n'
                    '                    os.close(fd)\n'
                    '            from scripts.run_grounded_action_v1_engine_local import terminate_group, '
                    'group_exited\n'
                    '            cleanup_errors = []\n'
                    '            for process in processes:\n'
                    '                try:\n'
                    '                    terminate_group(process, grace=.5, verification_seconds=3)\n'
                    '                except Exception as exc:\n'
                    "                    cleanup_errors.append(type(exc).__name__ + ': ' + str(exc)[:128])\n"
                    '            try:\n'
                    "                report['process_groups_exited'] = not cleanup_errors and "
                    'all(group_exited(p.pid) for p in processes)\n'
                    '            except Exception as exc:\n'
                    "                cleanup_errors.append(type(exc).__name__ + ': ' + str(exc)[:128])\n"
                    '            try:\n'
                    '                probes = probes_for(mode)(processes[0].pid if processes else 1, '
                    'scratch)\n'
                    '                if uuid is None:\n'
                    '                    uuid = validate_binding(probes.bind())\n'
                    '                receipt = independent_cleanup(probes, expected_uuid=uuid, '
                    "groups_absent=report['process_groups_exited'],\n"
                    '                                              deadline=started + internal_seconds - 2)\n'
                    "                control.save('gpu-cleanup.json', receipt)\n"
                    "                report['independent_gpu_cleanup_verified'] = "
                    "receipt['gpu_cleanup_verified']\n"
                    '            except Exception as exc:\n'
                    "                report['cleanup_error'] = type(exc).__name__ + ': ' + str(exc)[:256]\n"
                    '            for thread in drains:\n'
                    '                thread.join(timeout=2)\n'
                    '            if cleanup_errors or log_errors or any(t.is_alive() for t in drains):\n'
                    "                report['error'] = report['error'] or 'process/log cleanup failure'\n",
                    '        finally:\n'
                    '            with defer_startup_signals():\n'
                    '                for fd in (rfd, wfd):\n'
                    '                    if fd is not None:\n'
                    '                        os.close(fd)\n'
                    "                report['process_groups_exited'], cleanup_errors = owners.stop()\n"
                    "                report['child_ownership_verified'] = report['process_groups_exited']\n"
                    '                try:\n'
                    '                    probes = probes_for(mode)(processes[0].pid if processes else 1, '
                    'scratch)\n'
                    '                    if uuid is None:\n'
                    '                        uuid = validate_binding(probes.bind())\n'
                    '                    receipt = independent_cleanup(probes, expected_uuid=uuid, '
                    "groups_absent=report['process_groups_exited'],\n"
                    '                                                  deadline=started + internal_seconds - '
                    '2)\n'
                    "                    control.save('gpu-cleanup.json', receipt)\n"
                    "                    report['independent_gpu_cleanup_verified'] = "
                    "receipt['gpu_cleanup_verified']\n"
                    '                except Exception as exc:\n'
                    "                    report['cleanup_error'] = type(exc).__name__ + ': ' + "
                    'str(exc)[:256]\n'
                    '                for thread in drains:\n'
                    '                    if thread.ident is not None:\n'
                    '                        thread.join(timeout=2)\n'
                    '                for process, thread in zip(processes, drains):\n'
                    '                    if thread.ident is None and process.stdout is not None:\n'
                    '                        process.stdout.close()\n'
                    '                if cleanup_errors or log_errors or any(t.is_alive() for t in drains):\n'
                    "                    report['error'] = report['error'] or 'process/log cleanup "
                    "failure'\n",
                    1)],
 'launch.py': [('def _owned_groups(output, supervisor_pid):\n'
                '    groups = [supervisor_pid]\n'
                "    ownership = output / 'control/ownership.json'\n"
                '    if ownership.is_file() and not ownership.is_symlink() and ownership.stat().st_size <= '
                '8192:\n'
                '        record = json.loads(ownership.read_bytes())\n'
                "        for name in ('worker_pgid', 'monitor_pgid'):\n"
                '            pgid = record.get(name)\n'
                '            if type(pgid) is int and pgid > 0 and pgid not in groups:\n'
                '                groups.append(pgid)\n'
                '    return groups\n',
                'def _owned_groups(output, supervisor_pid):\n'
                '    from research.stagnation_supervision_runtime_v2.ownership import recovery_inventory\n'
                '    return recovery_inventory(output, supervisor_pid)[0]',
                1),
               ('                try:\n'
                '                    groups = _owned_groups(output, process.pid)\n'
                '                except BaseException as exc:\n'
                "                    errors.append('ownership evidence: ' + type(exc).__name__)\n",
                '                inner_certain = False\n'
                '                try:\n'
                '                    # Freeze child creation before scanning recovery records. Undetached\n'
                '                    # bootstraps are still in this group; detached children registered '
                'first.\n'
                '                    cleanup[str(process.pid)] = _stop_group(process.pid)\n'
                '                    process.wait(timeout=5)\n'
                '                    from research.stagnation_supervision_runtime_v2.ownership import '
                'recovery_inventory\n'
                '                    groups, inner_certain = recovery_inventory(output, process.pid)\n'
                '                except BaseException as exc:\n'
                "                    errors.append('ownership evidence: ' + type(exc).__name__)\n",
                1),
               ("            absent = ownership == 'never_spawned' or (ownership == 'registered' and "
                'bool(cleanup)\n'
                '                                                      and all(v is True for v in '
                'cleanup.values()))',
                "            absent = ownership == 'never_spawned' or (ownership == 'registered' and "
                'bool(cleanup)\n'
                '                                                      and inner_certain and all(v is True '
                'for v in cleanup.values()))',
                1),
               ("                'ownership': ownership, 'groups': cleanup, 'groups_absent': absent, "
                "'drain_finished': drained,",
                "                'ownership': ownership, 'groups': cleanup, 'groups_absent': absent, "
                "'drain_finished': drained,\n"
                "                'child_ownership_verified': inner_certain if process is not None else "
                "ownership == 'never_spawned',",
                1)],
 'target_evaluate.py': [("    require(first['dependency_trees_removed'] is (True if first['installation'] != "
                         "'none' else None), 'dependency cleanup')",
                         "    require(first['dependency_trees_removed'] is (True if first['installation'] != "
                         "'none' else None), 'dependency cleanup')\n"
                         '    from research.stagnation_supervision_runtime_v2.installation_evidence import '
                         'validate_installation\n'
                         '    validate_installation(root, first, outer, mode=mode)',
                         1),
                        ("    groups = cleanup['groups']",
                         "    require(cleanup.get('child_ownership_verified') is True and "
                         "outer.get('child_ownership_verified') is True,\n"
                         "            'child ownership uncertainty cannot certify cleanup')\n"
                         '    from research.stagnation_supervision_runtime_v2.ownership import '
                         'recovery_inventory\n'
                         "    supervisor_groups = [int(p) for p in cleanup['groups'] if int(p) not in "
                         "(owned['worker_pgid'], owned['monitor_pgid'])]\n"
                         "    require(len(supervisor_groups) == 1, 'supervisor group inventory')\n"
                         '    recovered, certain = recovery_inventory(root, supervisor_groups[0])\n'
                         "    require(certain and {str(p) for p in recovered} == set(cleanup['groups']), "
                         "'per-child ownership recovery inventory')\n"
                         "    groups = cleanup['groups']",
                         1)]}
for _name, _replacements in PRELAUNCH_REPAIRS.items():
    TRACK3[_name][1].extend(_replacements)

# r2 behavioural repairs (lessons from Tracks 1, 2 and 4; reports/stagnation_supervision_runtime_v2_gap_checklist_r2.md).
# They are the only replacements that change behaviour rather than rebind runtime paths: each source-text prefix below
# names exactly one replacement, and the tests exempt exactly these from the runtime-path rule.
R2_REPAIRS = {
    'launch.py': (
        '    """Own the supervisor', '    errors, retained = [], bytearray()', "    env['PYTHONNOUSERSITE'] = '1'",
        '    thread = threading.Thread(target=drain', '    finally:\n        groups = [process.pid]',
        "    report['first_cell_cleanup_verified']", '    except Exception as exc:\n        error =',
        "    control.save('notebook-cost.json', receipt)\n    return receipt", '    """Called by the notebook cell',
        "        receipt = run(working / OUTPUT_NAME, working, started=started, root=source, mode='live', session=session)"),
    'target_evaluate.py': ("    require(first['study_status']", "    require(cleanup['drain_finished']"),
}

for _name, _replacements in PRELAUNCH_REPAIRS.items():
    R2_REPAIRS[_name] = R2_REPAIRS.get(_name, ()) + tuple(old for old, _, _ in _replacements)

# Session-1 attempt 1 (ssv1rt2-s1-c5ebca7f, 2026-10-11): on the target the monitor's first RSS probe took 5.45 s while
# the GPU probe in the same sample took 0.012 s, so the frozen 1-s sampling-gap limit stopped the monitor before
# readiness (no model start, no game action). Track 1's first probe on the same machine type took 0.03 s, so this is a
# one-time first-call cost in a fresh container. Each probe now runs once, untimed, before the sampling clock starts;
# the 0.5-s interval and 1-s gap limits are unchanged, and a persistently slow probe still fails closed.
ATTEMPT1_REPAIRS = {'monitor.py': [(
    "        state['monitor_started_seconds'] = clock() - started\n",
    "        # One untimed call of each probe before the sampling clock. r6 (attempt-2 review): each warm-up call records\n"
    "        # its own phase and elapsed time on an exception-safe path, so a failed warm-up names the probe.\n"
    "        context['warmup_probe_seconds'] = {}\n"
    "        for name, call in (('gpu', lambda: probes.sample(uuid)), ('rss', lambda: probes.rss(worker_pid)),\n"
    "                           ('scratch', probes.scratch_bytes)):\n"
    "            context['phase'] = 'warmup_' + name\n"
    "            began = clock()\n"
    "            try:\n"
    "                call()\n"
    "            finally:\n"
    "                context['warmup_probe_seconds'][name] = round(clock() - began, 6)\n"
    "        context['phase'] = 'sampling'\n"
    "        state['monitor_started_seconds'] = clock() - started\n", 1)]}
for _name, _replacements in ATTEMPT1_REPAIRS.items():
    TRACK3[_name][1].extend(_replacements)
    R2_REPAIRS[_name] = R2_REPAIRS.get(_name, ()) + tuple(old for old, _, _ in _replacements)

# Session-1 attempt 2 (ssv1rt2-s1r-99405387) failed in the warm-up itself: `ps -axo pgid=,rss=` exceeded its 1-s
# timeout, so the cost is not one-time. The independent review then reproduced a cleanup defect: if the first stop of
# the supervisor group raised (for example a timed-out ps query), the child recovery records were never read and only
# the supervisor group was signalled. r6: the RSS probe and every group check read /proc directly (procfs.py: same
# coverage, a hard budget, a bounded census, never a partial or zero result); stopping, reaping and recovering are
# each attempted on their own; every recovered owned group is signalled with a SIGKILL fallback; absence is never
# certified under uncertainty; the monitor's failure receipt carries the probe census.
ATTEMPT2_REPAIRS = {
    'launch.py': [
        ("    result = subprocess.run(['ps', '-axo', 'pgid=,stat='], capture_output=True, text=True, timeout=2, check=True)\n"
         "    return not any(int(parts[0]) == pgid and not parts[1].startswith('Z') for line in result.stdout.splitlines()\n"
         "                   if len(parts := line.split()) >= 2 and parts[0].isdigit())\n",
         "    from research.stagnation_supervision_runtime_v2.procfs import group_live  # r6: /proc, no ps subprocess\n"
         "    return not group_live(pgid)\n", 1),
        ("                groups = [process.pid]\n"
         "                inner_certain = False\n"
         "                try:\n"
         "                    # Freeze child creation before scanning recovery records. Undetached\n"
         "                    # bootstraps are still in this group; detached children registered first.\n"
         "                    cleanup[str(process.pid)] = _stop_group(process.pid)\n"
         "                    process.wait(timeout=5)\n"
         "                    from research.stagnation_supervision_runtime_v2.ownership import recovery_inventory\n"
         "                    groups, inner_certain = recovery_inventory(output, process.pid)\n"
         "                except BaseException as exc:\n"
         "                    errors.append('ownership evidence: ' + type(exc).__name__)\n"
         "                for pgid in groups:\n"
         "                    try:\n"
         "                        cleanup[str(pgid)] = _stop_group(pgid)\n"
         "                    except BaseException as exc:\n"
         "                        cleanup[str(pgid)] = type(exc).__name__ + ': ' + str(exc)[:128]\n"
         "                        try:\n"
         "                            os.killpg(pgid, signal.SIGKILL)\n"
         "                            cleanup[str(pgid)] = _group_exited(pgid)\n"
         "                        except BaseException:\n"
         "                            pass\n",
         "                groups, inner_certain = [process.pid], False\n"
         "                # r6: each step is attempted on its own, so a failed inspection never skips termination or the\n"
         "                # recovery of the durable child ownership records. Stopping the supervisor group first freezes\n"
         "                # child creation (undetached bootstraps are still in it; detached children registered first).\n"
         "                try:\n"
         "                    cleanup[str(process.pid)] = _stop_group(process.pid)\n"
         "                except BaseException as exc:\n"
         "                    cleanup[str(process.pid)] = type(exc).__name__ + ': ' + str(exc)[:128]\n"
         "                    errors.append('supervisor group stop: ' + type(exc).__name__)\n"
         "                    try:\n"
         "                        os.killpg(process.pid, signal.SIGKILL)\n"
         "                    except BaseException:\n"
         "                        pass\n"
         "                try:\n"
         "                    process.wait(timeout=5)\n"
         "                except BaseException as exc:\n"
         "                    errors.append('supervisor reap: ' + type(exc).__name__)\n"
         "                try:\n"
         "                    from research.stagnation_supervision_runtime_v2.ownership import recovery_inventory\n"
         "                    groups, inner_certain = recovery_inventory(output, process.pid)\n"
         "                except BaseException as exc:\n"
         "                    errors.append('ownership evidence: ' + type(exc).__name__)\n"
         "                for pgid in groups:  # every verified owned group; a failed check still gets SIGKILL\n"
         "                    try:\n"
         "                        cleanup[str(pgid)] = _stop_group(pgid)\n"
         "                    except BaseException as exc:\n"
         "                        cleanup[str(pgid)] = type(exc).__name__ + ': ' + str(exc)[:128]\n"
         "                        errors.append('owned group stop: ' + type(exc).__name__)\n"
         "                        try:\n"
         "                            os.killpg(pgid, signal.SIGKILL)\n"
         "                        except BaseException:\n"
         "                            pass\n"
         "                        try:\n"
         "                            cleanup[str(pgid)] = _group_exited(pgid)\n"
         "                        except BaseException:\n"
         "                            pass\n", 1)],
    'resources.py': [
        ("        from evaluation.phase4_runner import group_rss_bytes\n        return group_rss_bytes(pid)\n",
         "        from research.stagnation_supervision_runtime_v2 import procfs  # r6: /proc, whole group, hard budget\n"
         "        try:\n"
         "            value, self.last_rss_census = procfs.group_rss(pid)\n"
         "        except procfs.ScanBudgetExceeded as exc:\n"
         "            self.last_rss_census = exc.census\n"
         "            raise\n"
         "        return value\n", 1)],
    'supervisor.py': [
        ("            from scripts.run_grounded_action_v1_engine_local import terminate_group\n"
         "            terminate_group(worker, grace=.5, verification_seconds=3)\n",
         "            from research.stagnation_supervision_runtime_v2.launch import _stop_group  # r6: /proc checks, no ps\n"
         "            if not _stop_group(worker.pid):\n"
         "                raise RuntimeError('owned worker group still has live members after SIGKILL')\n"
         "            worker.wait(timeout=3)\n", 1)],
    'monitor.py': [
        ("        state.update(status='failed', error=type(exc).__name__ + ': ' + str(exc)[:256])\n",
         "        state.update(status='failed', error=type(exc).__name__ + ': ' + str(exc)[:256])\n"
         "        census = getattr(exc, 'census', None)  # r6: a /proc scan over budget names its own cost\n"
         "        if isinstance(census, dict):\n"
         "            context['rss_census'] = {k: (round(v, 6) if type(v) is float else v) for k, v in census.items()}\n",
         1)],
}
for _name, _replacements in ATTEMPT2_REPAIRS.items():
    TRACK3[_name][1].extend(_replacements)
    R2_REPAIRS[_name] = R2_REPAIRS.get(_name, ()) + tuple(old for old, _, _ in _replacements)

# Unchanged Track 3 science and lifecycle files the successor imports; their hashes are bound in the protocol.
SCIENCE = (
    'research/stagnation_supervision_v1/trigger_spec.json',
    'research/stagnation_supervision_v1/detector.py',
    'research/stagnation_supervision_v1/supervision.py',
    'research/stagnation_supervision_v1/intervention.py',
    'research/stagnation_supervision_v1/outcomes.py',
    'research/stagnation_supervision_v1/thresholds.py',
    'research/stagnation_supervision_v1/closed_loop/protocol.json',
    'research/stagnation_supervision_v1/closed_loop/runner.py',
    'research/stagnation_supervision_v1/closed_loop/contract.py',
    'research/stagnation_supervision_v1/closed_loop/bridge.py',
    'research/stagnation_supervision_v1/closed_loop/service.py',
    'research/stagnation_supervision_v1/closed_loop/model_service.py',
    'research/stagnation_supervision_v1/closed_loop/server_config.py',
    'research/stagnation_supervision_v1/closed_loop/token_bridge.py',
    'research/stagnation_supervision_v1/closed_loop/engine.py',
    'research/stagnation_supervision_v1/closed_loop/evidence.py',
    'research/stagnation_supervision_v1/closed_loop/evaluate.py',
    'research/stagnation_supervision_v1/closed_loop/authority.py',
    'research/transition_evidence_v2/transition.py',
    'research/transition_evidence_v2/vocabulary.py',
    'research/transition_evidence_v1/transition.py',
    'research/transition_evidence_v1/vocabulary.py',
    'research/action_effect_v1/records.py',
    'certification/phase4_transient_v2/action_contract.py',
    'certification/phase4_transient_v2/contract.py',
    'certification/phase4_integrated_v2/tokenizer_manifest.json',
    'config/m0_launch_spec_q3vl30.json',
    'config/operational_primary.yaml',
    'reports/stagnation_supervision_v1_token_audit.json',
    'reports/stagnation_supervision_v1_ls20_decision.json',
    'reports/stagnation_supervision_v1_protocol_v2.md',
)
# Every consumed attempt, never reusable (r10, fourth review): the R6 attempt and session-1 attempts 1 and 2 of runtime
# v2, both consumed by their single push (provider versions 2 and 3) and failed before readiness.
CONSUMED_ATTEMPTS = ('ssv1-r5-session1-reservation-001', 'ssv1rt2-s1-c5ebca7f7b444bb3b63b6c90b3cf306b',
                     'ssv1rt2-s1r-994053875c1c4a6ea06ab09be3e9c4bc')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git_bytes(commit, path):
    return subprocess.run(['git', 'show', f'{commit}:{path}'], cwd=ROOT, check=True, capture_output=True).stdout


def apply(source, replacements):
    text = source.decode('utf-8')
    for old, new, count in replacements:
        if text.count(old) != count:
            raise ValueError(f'replacement source text occurs {text.count(old)} times, expected {count}: {old[:80]!r}')
        if new in source.decode('utf-8'):
            raise ValueError(f'replacement target already present in the source: {new[:80]!r}')
        text = text.replace(old, new)
    return text.encode('utf-8')


def inverse_check(derived, record):
    """Reconstruct the source bytes from a derived file and its record (no git needed)."""
    header = HEADER.format(path=record['source_path'], commit=record['source_commit']).encode()
    if record['kind'] == 'data':
        return sha(derived) == record['source_sha256']
    if not derived.startswith(header):
        return False
    text = derived[len(header):].decode('utf-8')
    for old, new, count in reversed(record['replacements']):
        if text.count(new) != count:
            return False
        text = text.replace(new, old)
    return sha(text.encode('utf-8')) == record['source_sha256']


def tree_digest(rows):
    digest = hashlib.sha256(b'arc3-artifact-tree-v1\0')
    for row in sorted(rows, key=lambda r: r['path']):
        path = row['path'].encode()
        digest.update(len(path).to_bytes(4, 'big') + path + row['bytes'].to_bytes(8, 'big') + bytes.fromhex(row['sha256']))
    return digest.hexdigest()


def build_protocol(reference, attachment, science, reference_sha256):
    files = sorted(({'path': r['path'], 'bytes': r['bytes'], 'sha256': r['sha256']}
                    for r in attachment['attachment_files']), key=lambda r: r['path'])
    model = reference['model']
    if tree_digest(files) != model['tree_sha256'] or sum(r['bytes'] for r in files) != attachment['attachment_bytes']:
        raise ValueError('reference model attachment inventory does not reproduce the pinned tree digest')
    tokenizer = json.loads((ROOT / 'certification/phase4_integrated_v2/tokenizer_manifest.json').read_bytes())
    by_path = {r['path']: r for r in files}
    for name, info in tokenizer['files'].items():
        if by_path.get(name, {}).get('sha256') != info['sha256'] or by_path[name]['bytes'] != info['bytes']:
            raise ValueError('tokenizer file differs between the frozen manifest and the new snapshot: ' + name)
    spec = json.loads((ROOT / 'config/m0_launch_spec_q3vl30.json').read_bytes())
    effective = [x if x != '--enable-prefix-caching' else '--no-enable-prefix-caching' for x in spec['argv']]
    reference_argv = [x if x != '{port}' else str(reference['server']['port']) for x in reference['server']['argv']]
    if effective != reference_argv or spec['env'] != reference['server']['env']:
        raise ValueError('Track 3 effective server command differs from the verified runtime')
    primary = json.loads((ROOT / 'config/operational_primary.yaml').read_bytes())['primary']
    for key in ('required_files', 'shard_glob', 'shard_count'):
        if primary['model_artifact'][key] != model[key]:
            raise ValueError('model layout requirement differs: ' + key)
    if primary['model_binding']['revision'] != model['revision'] or primary['model_binding']['model_id'] != model['model_id']:
        raise ValueError('model identity differs from the frozen Track 3 binding')
    runtime = reference['runtime']
    return {
        'schema': 'stagnation_supervision_runtime_v2_protocol',
        'scope': 'stagnation-supervision-v1-runtime-v2',
        'status': 'gpu_disabled_review_candidate_no_authority',
        'purpose': ('Track 3 stagnation supervision v1 (protocol v2) bound to the verified GPU runtime. Runtime bindings '
                    'only: games, horizon, arms, no-restart rule, frozen trigger, prompts, scoring and stop rules are '
                    'the unchanged files bound under science.'),
        'placeholder_prefix': 'REPLACE_WITH_',
        'kernel_ids': {'1': 'REPLACE_WITH_OWNER/arc3-ssv1-runtime-v2-session-1',
                       '2': 'REPLACE_WITH_OWNER/arc3-ssv1-runtime-v2-session-2'},
        'consumed_attempts': list(CONSUMED_ATTEMPTS),
        'kaggle_image': reference['kaggle_image'],
        'machine_shape': 'NvidiaRtxPro6000',
        'competition': {
            'ref': reference['competition']['ref'],
            'purpose': ('offline development game files and the competition arc_agi_3 wheels for the game interpreter; '
                        'attachment does not submit to the leaderboard'),
            'game_wheels_dir': 'arc_agi_3_wheels', 'environment_files_dir': 'environment_files',
            'manifest': 'reports/phase4_v2_offline_package.json',
            'manifest_sha256': sha((ROOT / 'reports/phase4_v2_offline_package.json').read_bytes()),
            'game_wheel_count': 31, 'environment_file_count': 30},
        'dataset': reference['dataset'],
        'bundle': reference['bundle'],
        'model': {'kaggle_source': 'REPLACE_WITH_MODEL_OWNER/REPLACE_WITH_MODEL_DATASET/1',
                  'mounted_path': 'REPLACE_WITH_VERIFIED_MODEL_MOUNT', 'source_kind': 'dataset',
                  'model_id': model['model_id'], 'revision': model['revision'],
                  'reasoning_setting': model['reasoning_setting'], 'tree_sha256': model['tree_sha256'],
                  'file_count': len(files), 'bytes': sum(r['bytes'] for r in files),
                  'required_files': model['required_files'], 'shard_glob': model['shard_glob'],
                  'shard_count': model['shard_count'], 'files': files},
        'runtime': {'python': runtime['python'], 'machine': runtime['machine'], 'glibc_minimum': runtime['glibc_minimum'],
                    'gpu_count': runtime['gpu_count'], 'gpu_name_contains': runtime['gpu_name_contains'],
                    'model': {'packages': runtime['packages'], 'imports': runtime['imports'],
                              'torch_cuda_build': runtime['torch_cuda_build']},
                    'game': {'packages': {'arc-agi': '0.9.8', 'arcengine': '0.9.3', 'numpy': '2.4.4',
                                          'requests': '2.33.1', 'pydantic': '2.13.2', 'python-dotenv': '1.2.2'}}},
        'server': {'argv': reference_argv, 'env': reference['server']['env'],
                   'launch_spec': 'config/m0_launch_spec_q3vl30.json',
                   'derivation': 'Track 3 m0 launch spec with server_config.cache_disabled_argv; equal to the verified runtime'},
        'limits': {'installation_seconds': 450, 'model_startup_ceiling_seconds': 900,
                   'session_limits_source': 'research/stagnation_supervision_v1/closed_loop/authority.py SESSION_LIMITS'},
        'science': {'unchanged': True, 'files': science},
        'reference_runtime': {'branch': REFERENCE_BRANCH, 'commit': REFERENCE_COMMIT,
                              'protocol': REFERENCE_INPUTS['protocol'],
                              'protocol_sha256': reference_sha256},
    }


def derive(read_reference):
    outputs, records = {}, []
    for name, (path, _, replacements) in REFERENCE.items():
        source = read_reference(path)
        body = apply(source, replacements)
        data = HEADER.format(path=path, commit=REFERENCE_COMMIT[:7]).encode() + body
        outputs[name] = data
        records.append({'derived': f'{PACKAGE}/{name}', 'kind': 'python', 'source_branch': REFERENCE_BRANCH,
                        'source_commit': REFERENCE_COMMIT[:7], 'source_path': path, 'source_sha256': sha(source),
                        'replacements': [list(r) for r in replacements], 'derived_sha256': sha(data)})
    for name, path in REFERENCE_DATA.items():
        source = read_reference(path)
        outputs[name] = source
        records.append({'derived': f'{PACKAGE}/{name}', 'kind': 'data', 'source_branch': REFERENCE_BRANCH,
                        'source_commit': REFERENCE_COMMIT[:7], 'source_path': path, 'source_sha256': sha(source),
                        'replacements': [], 'derived_sha256': sha(source)})
    for name, (path, replacements) in TRACK3.items():
        source = (ROOT / path).read_bytes()
        body = apply(source, replacements)
        data = HEADER.format(path=path, commit=TRACK3_COMMIT[:7]).encode() + body
        outputs[name] = data
        records.append({'derived': f'{PACKAGE}/{name}', 'kind': 'python', 'source_branch': TRACK3_BRANCH,
                        'source_commit': TRACK3_COMMIT[:7], 'source_path': path, 'source_sha256': sha(source),
                        'replacements': [list(r) for r in replacements], 'derived_sha256': sha(data)})
    science = {p: sha((ROOT / p).read_bytes()) for p in SCIENCE}
    reference_raw = read_reference(REFERENCE_INPUTS['protocol'])
    attachment = json.loads(read_reference(REFERENCE_INPUTS['model_attachment']))
    protocol = build_protocol(json.loads(reference_raw), attachment, science, sha(reference_raw))
    outputs['protocol.json'] = (json.dumps(protocol, indent=1, sort_keys=True) + '\n').encode()
    inputs = {key: {'path': path, 'sha256': sha(read_reference(path))} for key, path in REFERENCE_INPUTS.items()}
    record = {'schema': 'stagnation_supervision_runtime_v2_derivation', 'builder': 'scripts/derive_stagnation_supervision_runtime_v2.py',
              'reference': {'branch': REFERENCE_BRANCH, 'commit': REFERENCE_COMMIT, 'inputs': inputs},
              'track3': {'branch': TRACK3_BRANCH, 'commit': TRACK3_COMMIT},
              'files': records, 'protocol_sha256': sha(outputs['protocol.json']),
              'note': ('Runtime bindings plus the r2/r3 behavioural repairs named in R2_REPAIRS (startup ownership and '
                       'fail-closed finalization, with their independent checks). The science files listed in '
                       'protocol.json are imported unchanged. '
                       'Hand-written successor modules (authority, model_binding, mounts, prepare, closure, notebook, '
                       'launch_tooling, provider_preflight, verification) are not derived and are reviewed directly.')}
    for row in records:
        if not inverse_check(outputs[row['derived'].rsplit('/', 1)[1]], row):
            raise ValueError('derivation is not invertible: ' + row['derived'])
    outputs['derivation.json'] = (json.dumps(record, indent=1, sort_keys=True) + '\n').encode()
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = derive(lambda path: git_bytes(REFERENCE_COMMIT, path))
    folder = ROOT / PACKAGE
    drift = [n for n, d in outputs.items() if not (folder / n).is_file() or (folder / n).read_bytes() != d]
    if args.check:
        if drift:
            raise SystemExit('derived files differ from the derivation: ' + ', '.join(sorted(drift)))
        record = json.loads(outputs['derivation.json'])
        for row in record['files']:
            if not inverse_check((ROOT / row['derived']).read_bytes(), row):
                raise SystemExit('inverse check failed: ' + row['derived'])
        print(f'{len(outputs)} derived files match the derivation; {len(record["files"])} invert to their sources')
        return 0
    folder.mkdir(parents=True, exist_ok=True)
    for name, data in outputs.items():
        (folder / name).write_bytes(data)
    print(json.dumps({'written': sorted(outputs), 'drift_replaced': sorted(drift)}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
