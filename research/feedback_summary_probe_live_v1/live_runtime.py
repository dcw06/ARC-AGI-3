"""Private notebook entry point. All imports before installation are stdlib-safe."""
import csv
import json
import os
import re
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import time

from certification.direct_publisher_smoke_v1 import host
from certification.direct_publisher_smoke_v1.install import install, verify_bundle
from certification.direct_publisher_smoke_v1.server import ModelServer, defer_startup_signals
from research.initial_geometry_assistance_v1.game_wheels import verify_mounted_game
from research.initial_geometry_assistance_v1.geometry import canonical, digest
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from research.initial_geometry_assistance_v1.live_resources import HardDeadline, Processes, environment

SCOPE = {'GPU': 'one RTX PRO 6000', 'session_timeout_seconds': 3600, 'worker_seconds': 3300,
         'admission_seconds': 3000, 'cleanup_reserve_seconds': 300, 'generations': 81, 'counted_HTTP_requests': 81,
         'recognition_generations': 16, 'checkpoints': 8, 'policy_conditions': 16,
         'policy_actions': 64, 'prefix_dispatches': 36, 'bootstrap_resets': 16, 'offline_engine_actions': 116,
         'local_scorecards': 16, 'online_game_calls': 0, 'online_scorecards': 0,
         'scoreboard_submissions': 0, 'automatic_retries': 0, 'attempts': 1,
         'access': 'private_account_only', 'internet': False, 'TPU': False}


def check_authority(authority, lock_sha256):
    if not isinstance(authority, dict):
        raise PermissionError('APPROVAL REQUIRED: no live attempt authority')
    if (set(authority) != {'review_lock_sha256', 'scope', 'account', 'source_approval',
                           'use_permission', 'compute_authorization', 'attempt_id', 'reservation', 'claim', 'proofs'} or
            authority['review_lock_sha256'] != lock_sha256 or canonical(authority['scope']) != canonical(SCOPE) or
            authority['account'] != 'daichongwei06' or
            any(type(authority[k]) is not str or not authority[k].strip() for k in
                ('source_approval', 'use_permission', 'compute_authorization', 'attempt_id', 'reservation', 'claim'))):
        raise PermissionError('source/use/compute/reservation/claim authority differs from reviewed scope')
    if any(not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', authority[k]) for k in ('attempt_id', 'reservation', 'claim')):
        raise PermissionError('unsafe attempt/reservation/claim identity')
    if type(authority['proofs']) is not dict or set(authority['proofs']) != {'source_approval', 'use_permission', 'compute_authorization'}:
        raise PermissionError('approval evidence missing')
    for kind, record in authority['proofs'].items():
        if (type(record) is not dict or record.get('kind') != kind or record.get('approved') is not True or
                record.get('review_lock_sha256') != lock_sha256 or canonical(record.get('scope')) != canonical(SCOPE) or
                record.get('account') != 'daichongwei06' or type(record.get('owner_statement')) is not str or
                not record['owner_statement'].strip() or authority[kind] != digest(record)):
            raise PermissionError('approval proof is missing, stale or mismatched: '+kind)


from .live_contract import verify_inputs
from .source_closure import verify_source_inventory


def finalize(output, result, *, deadline, now=time.monotonic, writer=write_new, emit=print):
    """Provisional evidence + post-write witness, never sufficient without provider COMPLETE.

    Interruptions in any final write, marker or subsequent deadline check cannot
    certify success: independent evaluation also requires the saved job COMPLETE
    and its exact return marker. No on-disk file alone is a passing verdict.
    """
    def check():
        if now() >= deadline:
            raise TimeoutError('finalization exceeded lifecycle deadline')
    check()
    manifest = {p.relative_to(output).as_posix(): sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    result = dict(result, evidence_sha256=manifest, lifecycle_finalized=False)
    writer(output/'provisional-result.json', result)
    check()
    witness = {'schema': 'feedback_summary_probe_return_witness_v1',
               'provisional_result_sha256': sha(output/'provisional-result.json'),
               'elapsed_seconds': now()-result['started_monotonic'], 'error': result['error'],
               'provider_COMPLETE_and_exact_return_marker_required': True}
    writer(output/'return-witness.json', witness)
    check()
    marker = 'FEEDBACK_SUMMARY_PROBE_RETURNED '+sha(output/'return-witness.json')
    emit(marker, flush=True)
    check()
    return marker


def run(source, authority, lock_sha256, *, started, bootstrap_guard):
    check_authority(authority, lock_sha256)  # before filesystem / GPU side effects
    source = Path(source).resolve()
    runtime = json.loads((source/'runtime.json').read_bytes())
    output = Path('/kaggle/working/feedback-summary-probe-'+authority['attempt_id'])
    output.mkdir(exist_ok=False)
    deadline, admission = started+3300, started+3000
    watchdog = HardDeadline(deadline)
    watchdog.start()
    processes = Processes(watchdog)
    # The extraction watchdog was created before importing this source tree.
    # It remains owned and timed through handover to the full group watchdog.
    guard = ModelServer([], {}, output/'bootstrap-guard.log', None, None, inherit_env=False)
    guard.process, guard.pgid, guard.ownership = bootstrap_guard, bootstrap_guard.pid, 'registered'
    guard._log = (output/'bootstrap-guard.log').open('ab')
    with defer_startup_signals():
        processes.groups.append({'phase': 'bootstrap watchdog', 'group': guard,
                                 'watch_slot': watchdog.register(guard)})
    env = environment()
    temporary = None
    error, cleanup, gpu, worker_entry = None, None, None, None
    facts = {'scope': SCOPE, 'review_lock_sha256': lock_sha256, 'attempt_id': authority['attempt_id'],
             'started_monotonic': started, 'error': None, 'worker_exit': None}
    previous = {}

    def alarm(signum, frame):
        raise TimeoutError('lifecycle work/final deadline or interruption: '+str(signum))

    def check():
        if time.monotonic() >= admission:
            raise TimeoutError('work admission deadline')

    def query(fields, kind='gpu'):
        flag = '--query-gpu=' if kind == 'gpu' else '--query-compute-apps='
        result = processes.command(['nvidia-smi', flag+','.join(fields), '--format=csv,noheader,nounits'],
                                   output/'gpu-query.log', min(deadline, time.monotonic()+5), env, 'GPU census')
        # command stdout is after the logged argv; CSV parser sees no shell noise.
        return [[v.strip() for v in row] for row in csv.reader(result.stdout.strip().splitlines()) if row]

    try:
        for signum in (signal.SIGALRM, signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            previous[signum] = signal.signal(signum, alarm)
        signal.setitimer(signal.ITIMER_REAL, max(0.001, admission-time.monotonic()))
        facts['host'] = host.host_facts(runtime['runtime'])
        gpu = facts['GPU'] = host.gpu_facts(runtime['runtime'], query)
        if query(['gpu_uuid', 'pid'], kind='apps'):
            raise ValueError('GPU already has compute processes before this attempt')
        execution_sources = json.loads((source/'source-manifest.json').read_bytes())
        verify_source_inventory(source, execution_sources)
        facts['source_inventory_sha256'] = sha(source/'source-manifest.json')
        verify_inputs(source/'inputs', runtime['input_manifest_sha256'])
        game_wheels, facts['game_wheels'] = verify_mounted_game(
            source/'game', runtime['game_receipt_sha256'], runtime['game_wheel_source'], check=check)
        facts['model'] = host.verify_model(runtime['model'], check)
        model_path = facts['model']['mounted_path']
        bundle = host.dataset_mount(runtime['dataset']['ref'], runtime['dataset']['version'])
        facts['wheels'] = verify_bundle(bundle, runtime['dataset'], runtime['bundle'], check,
                                        inputs=source/'certification/direct_publisher_smoke_v1')
        temporary = Path(tempfile.mkdtemp(prefix='feedback-summary-probe-'))
        # One combined installation phase, including all hashes and import checks.
        install_deadline = min(admission, time.monotonic()+900)
        facts['model_install'] = install(bundle, temporary/'model', runtime['runtime'], install_deadline,
                                         output/'model-install.log', environment=env, processes=processes,
                                         requirements=source/'certification/direct_publisher_smoke_v1/trusted_requirements.lock')
        facts['game_install'] = install(game_wheels, temporary/'game', runtime['game_runtime'],
                                        install_deadline, output/'game-install.log',
                                        environment=dict(env, CUDA_VISIBLE_DEVICES='', NVIDIA_VISIBLE_DEVICES='void'),
                                        requirements=source/'game/game_requirements.lock', processes=processes)
        python = facts['model_install']['python']
        argv = [python if item == '{python}' else model_path if item == '{model_path}' else
                str(runtime['port']) if item == '{port}' else item for item in runtime['server_argv']]
        config = {'started': started, 'port': runtime['port'], 'inputs': str(source/'inputs'),
                  'input_manifest_sha256': runtime['input_manifest_sha256'],
                  'game_python': facts['game_install']['python'], 'games': str(source/'game/environment_files'),
                  'model_path': model_path, 'server_argv': argv, 'model_host_packages': runtime['model_host_packages']}
        write_new(output/'worker-config.json', config)
        worker_env = dict(env, PYTHONPATH=str(source),
                          FEEDBACK_SUMMARY_PROBE_CONFIG_SHA256=sha(output/'worker-config.json'))
        worker_entry = processes.spawn([python, '-m', 'research.feedback_summary_probe_live_v1.live_worker',
                                         '--config', str(output/'worker-config.json'), '--output', str(output)],
                                        output/'worker.log', worker_env, 'model/game worker')
        code = worker_entry['group'].process.wait(timeout=max(0.001, admission-time.monotonic()))
        facts['worker_exit'] = code
        if code:
            raise RuntimeError('study worker failed, see retained worker log')
        check()
        worker = json.loads((output/'worker-result.json').read_bytes())
        if (worker['error'] is not None or len(worker['continuations']) != 16 or
                len(worker['recognition']) != 16):
            raise ValueError('study schedule incomplete')
    except BaseException as exc:
        error = type(exc).__name__ + ': ' + str(exc)
    finally:
        # Work cutoff does not cancel the final deadline. An independent process
        # still enforces it even if a one-shot alarm is swallowed below.
        signal.setitimer(signal.ITIMER_REAL, max(0.001, deadline-time.monotonic()))
        try:
            cleanup = processes.stop(deadline)
            facts['process_cleanup'] = cleanup
            if not cleanup['groups_absent'] or cleanup['interrupted'] or cleanup['error']:
                raise ValueError('owned-group cleanup not verified')
            facts['GPU_cleanup'] = host.gpu_cleanup(gpu['uuid'], True, query) if gpu else None
            if not facts['GPU_cleanup'] or not facts['GPU_cleanup']['gpu_cleanup_verified']:
                raise ValueError('GPU cleanup not verified')
            # GPU queries themselves are owned commands, and must be reaped too.
            facts['final_process_cleanup'] = processes.stop(deadline)
            if not facts['final_process_cleanup']['groups_absent']:
                raise ValueError('GPU-query cleanup not verified')
        except BaseException as exc:
            error = error or type(exc).__name__+': '+str(exc)
        try:
            if temporary is not None:
                shutil.rmtree(temporary)
            shutil.rmtree(source)
            facts['temporary_and_source_removed'] = not source.exists() and (temporary is None or not temporary.exists())
        except BaseException as exc:
            error = error or type(exc).__name__+': '+str(exc)
        facts['error'] = error
        # Keep the hard watchdog armed through writes, marker and the final check.
        finalize(output, facts, deadline=deadline)
        watchdog.close()
        if time.monotonic() >= deadline:
            raise TimeoutError('deadline reached stopping watchdog')
        signal.setitimer(signal.ITIMER_REAL, 0)
        for signum, handler in previous.items():
            signal.signal(signum, handler)
    if error:
        raise RuntimeError(error)
    return {'data_collected': True, 'provider_completion_still_required': True, 'output': str(output)}
