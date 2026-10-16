"""MolmoPoint GPU supervisor candidate, adapted from the hardened InternVL lifecycle. Review packages refuse before any GPU query.

This supplies no provider launcher. Live operation requires the owner's accepted
session/worker time policy, scoped use, fresh approval and a consumed claim.
"""
import csv
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import time

from certification.direct_publisher_smoke_v1.install import InstallationProcesses
from research.object_identification_v1.install_check import install_commands, requirement_pins
from research.object_identification_v1.mount_check import canonical, find_mount, verify_files
from .adapter import MODEL, REVISION

SCOPE = {'gpu_count': 1, 'gpu_name_contains': 'RTX PRO 6000', 'session_timeout_seconds': 3600,
         'whole_job_cap_seconds': None, 'provider_overhead_may_exceed_one_hour': True,
         'worker_seconds': 3300, 'work_seconds': 3000, 'cleanup_reserve_seconds': 300,
         'installation_seconds': 900, 'model_load_seconds': 900,
         'per_generation_seconds': 180, 'generation_requests': 6,
         'max_tokens_per_generation': 1024, 'max_generated_tokens': 6144,
         'game_actions': 0, 'scorecards': 0, 'automatic_retries': 0, 'attempts': 1,
         'access': 'account_holder_only', 'internet': False}


def subprocess_environment(host=None):
    """Keep isolation, but retain the platform's absolute driver-library paths."""
    host = os.environ if host is None else host
    value = host.get('LD_LIBRARY_PATH', '')
    if type(value) is not str or len(value) > 16384 or '\0' in value or '\n' in value:
        raise ValueError('invalid driver-library search path')
    parts = value.split(os.pathsep)
    if len(parts) > 64:
        raise ValueError('too many driver-library search paths')
    paths = list(dict.fromkeys(part for part in parts if part and os.path.isabs(part)))
    env = {'PATH': os.defpath, 'PYTHONNOUSERSITE': '1', 'PIP_NO_INDEX': '1',
           'PIP_CONFIG_FILE': os.devnull, 'PIP_DISABLE_PIP_VERSION_CHECK': '1',
           'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'HF_HUB_DISABLE_TELEMETRY': '1',
           'MPLBACKEND': 'Agg', 'TOKENIZERS_PARALLELISM': 'false'}
    if paths:
        env['LD_LIBRARY_PATH'] = os.pathsep.join(paths)
    return env


def driver_loader_evidence(env):
    """Filesystem-only diagnostics: no driver load, GPU query or broad env dump."""
    selected = env.get('LD_LIBRARY_PATH', '').split(os.pathsep) if env.get('LD_LIBRARY_PATH') else []
    candidates = list(dict.fromkeys(selected+[
        '/usr/local/nvidia/lib', '/usr/local/nvidia/lib64', '/usr/lib/x86_64-linux-gnu', '/opt/lib']))
    libraries = {}
    for folder in candidates:
        for name in ('libnvidia-ml.so', 'libnvidia-ml.so.1', 'libcuda.so.1'):
            path = Path(folder)/name
            libraries[str(path)] = path.is_file()
    return {'LD_LIBRARY_PATH_retained': bool(selected), 'driver_search_paths': selected,
            'nvidia_smi_resolved': shutil.which('nvidia-smi'), 'library_paths_present': libraries,
            'actual_GPU_allocation_verified': False, 'driver_load_tested_by_this_record': False}


def readiness(protocol, evidence):
    """No booleans masquerading as evidence: records bind exact scope and bytes."""
    problems = []
    if canonical(protocol.get('scope')) != canonical(SCOPE):
        problems.append('scope differs from frozen six-request design')
    if protocol.get('live_runs_enabled') is not True:
        problems.append('review-only package: live runs disabled')
    if protocol.get('source_bindings_confirmed') is not True:
        problems.append('model/input datasets have not been attached and verified')
    if protocol.get('model') != MODEL or protocol.get('revision') != REVISION:
        problems.append('MolmoPoint model/revision differs')
    if not evidence:
        problems.append('accepted time policy, scoped use, approvals and consumed launch claim missing')
        return problems
    required = ('time_policy', 'scoped_use', 'source_approval', 'compute_authorization', 'launch_claim')
    for name in required:
        if type(evidence.get(name)) is not dict:
            problems.append(name+' missing')
    if problems:
        return problems
    pin = evidence.get('review_lock_sha256')
    for name in required:
        if evidence[name].get('review_lock_sha256') != pin or not pin:
            problems.append(name+' is not bound to this review lock')
    policy = evidence['time_policy']
    if (policy.get('approved') is not True or policy.get('accepted_provider_overhead') is not True
            or type(policy.get('session_timeout_seconds')) is not int or policy['session_timeout_seconds'] != 3600
            or type(policy.get('worker_seconds')) is not int or policy['worker_seconds'] != 3300
            or policy.get('provider_full_job_cap_verified') is not False
            or not policy.get('owner_amendment_sha256')):
        problems.append('owner-accepted session/worker time policy not established')
    for name in ('scoped_use', 'source_approval', 'compute_authorization'):
        record = evidence[name]
        if record.get('approved') is not True or not record.get('owner_answer'):
            problems.append(name+' not personally approved')
    if (evidence['scoped_use'].get('model') != MODEL or
            evidence['scoped_use'].get('revision') != REVISION):
        problems.append('scoped use does not cover this MolmoPoint checkpoint')
    if canonical(evidence['compute_authorization'].get('scope')) != canonical(SCOPE):
        problems.append('compute authorization scope mismatch')
    bound = {name: hashlib.sha256(canonical(evidence[name])).hexdigest()
             for name in ('time_policy', 'scoped_use')}
    if evidence['source_approval'].get('scope_evidence_sha256') != bound:
        problems.append('source approval does not bind current scope evidence')
    if evidence['compute_authorization'].get('source_approval_sha256') != hashlib.sha256(
            canonical(evidence['source_approval'])).hexdigest():
        problems.append('compute authorization does not bind source approval')
    if evidence['launch_claim'].get('authorization_sha256') != hashlib.sha256(
            canonical(evidence['compute_authorization'])).hexdigest():
        problems.append('claim does not bind authorization')
    if evidence['launch_claim'].get('consumed') is not True or not evidence['launch_claim'].get('attempt_id'):
        problems.append('single-use launch claim not consumed')
    # Every receipt named by an authority must be retained alongside it and hashed.
    retained = evidence.get('retained_evidence', {})
    for name in required:
        for field, digest in evidence[name].items():
            if field.endswith('_sha256') and field not in ('review_lock_sha256', 'scope_evidence_sha256'):
                if digest not in retained:
                    problems.append(name+' missing retained '+field)
    return problems


def verify_packet(packet):
    packet = Path(packet).resolve()
    runtime_lock = packet/'runtime-lock.json'
    raw = (runtime_lock if runtime_lock.exists() else packet/'review-lock.json').read_bytes()
    lock = json.loads(raw)
    for name, digest in lock['artifacts'].items():
        path = packet/name
        if (path.is_symlink() or not path.resolve().is_relative_to(packet)
                or hashlib.sha256(path.read_bytes()).hexdigest() != digest):
            raise ValueError('private packet artifact differs: '+name)
        if name.startswith('reviewed-source/'):
            current=Path(__file__).resolve().parents[2]/name[len('reviewed-source/'):]
            generated_empty_root=(name in ('reviewed-source/research/__init__.py',
                'reviewed-source/certification/__init__.py') and not current.exists() and
                digest==hashlib.sha256(b'').hexdigest())
            if not generated_empty_root and (not current.is_file() or hashlib.sha256(current.read_bytes()).hexdigest()!=digest):
                raise ValueError('executing checkout differs from reviewed source: '+name)
    return hashlib.sha256(raw).hexdigest()


def finish(result, output, started, deadline):
    """A provisional receipt needs post-write witness AND provider COMPLETE."""
    result['elapsed_before_receipt_write_seconds'] = time.monotonic()-started
    raw = canonical(result)
    destination = Path(output)/'result.json'
    with destination.open('xb') as stream:
        stream.write(raw)
    if time.monotonic() >= deadline or result['status'] != 'provisional_complete':
        raise RuntimeError('inference lifecycle failed or exceeded deadline; preserve evidence')
    witness = canonical({'result_sha256': hashlib.sha256(raw).hexdigest(),
                         'elapsed_after_receipt_write_seconds': time.monotonic()-started,
                         'provider_COMPLETE_required': True})
    with (Path(output)/'completion-witness.json').open('xb') as stream:
        stream.write(witness)
    if time.monotonic() >= deadline:
        raise TimeoutError('inference finalization overrun')
    print('MOLMOPOINT_RETURNED '+hashlib.sha256(witness).hexdigest(), flush=True)
    if time.monotonic() >= deadline:
        raise TimeoutError('completion-output finalization overrun')
    return result


@contextmanager
def lifecycle_alarm(deadline):
    """Keep the worker alarm active through cleanup and final evidence writes."""
    def expired(*_):
        raise TimeoutError('inference worker alarm expired')
    handlers = {s: signal.signal(s, expired) for s in (signal.SIGALRM, signal.SIGTERM, signal.SIGHUP)}
    previous = signal.setitimer(signal.ITIMER_REAL, max(.001, deadline-time.monotonic()))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        for signum, handler in handlers.items():
            signal.signal(signum, handler)
        signal.setitimer(signal.ITIMER_REAL, *previous)


def run(packet, *, input_root='/kaggle/input', output='/kaggle/working/molmopoint-targeted448-v1'):
    # Approval checks precede imports of inference/model libraries and GPU commands.
    packet = Path(packet).resolve()
    pin = verify_packet(packet)
    protocol = json.loads((packet/'protocol.json').read_bytes())
    authority_path = packet/'live-authority.json'
    authority = json.loads(authority_path.read_bytes()) if authority_path.exists() else {}
    problems = readiness(protocol, authority)
    if authority and authority.get('runtime_lock_sha256', authority.get('review_lock_sha256')) != pin:
        problems.append('authority names a different runtime package')
    for digest, relative in authority.get('retained_evidence', {}).items():
        path = packet/relative
        if (path.is_symlink() or not path.resolve().is_relative_to(packet)
                or hashlib.sha256(path.read_bytes()).hexdigest() != digest):
            problems.append('retained authority evidence differs')
    if problems:
        raise SystemExit('REVIEW ONLY: '+'; '.join(problems))
    started = time.monotonic()
    with lifecycle_alarm(started+3300):
        return _execute(packet, protocol, authority, pin, input_root, output, started)


def _execute(packet, protocol, authority, pin, input_root, output, started):
    if sys.platform!='linux' or sys.version_info[:2]!=(3,12):
        raise ValueError('MolmoPoint locked runtime requires Linux/Python 3.12')
    deadline, work_deadline = started+3300, started+3000
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[2]
    requirements = Path(__file__).with_name('runtime_requirements.lock').read_bytes()
    pins = requirement_pins(requirements)
    if (pins.get('transformers', {}).get('version') != '4.57.1'
            or pins.get('torch', {}).get('version') != '2.10.0'):
        raise ValueError('separate MolmoPoint hashed requirements required')
    processes, sandbox, gpu = InstallationProcesses(), None, None
    result = {'status': 'inference_incomplete', 'runtime_lock_sha256': pin,
              'review_lock_sha256': authority['review_lock_sha256'], 'scope': SCOPE,
              'started_at_monotonic': started, 'work_deadline_monotonic': work_deadline,
              'datasets': {}, 'gpu': None, 'generation_requests': None,
              'game_actions': 0, 'scorecards': 0, 'provider_completion_required': True}
    failure = None
    env = {}
    log = output/'processes.log'
    def check():
        if time.monotonic() >= work_deadline:
            raise TimeoutError('inference work deadline exceeded')
    def query(fields, apps=False):
        binary = shutil.which('nvidia-smi')
        if not binary:
            raise ValueError('nvidia-smi unavailable')
        flag = '--query-compute-apps=' if apps else '--query-gpu='
        report = processes.command([binary, flag+','.join(fields), '--format=csv,noheader,nounits'],
            log, min(deadline, time.monotonic()+5), env, 'GPU process census' if apps else 'GPU identity')
        if len(report.stdout) > 16384:
            raise ValueError('oversized GPU census')
        return [row for row in csv.reader(report.stdout.strip().splitlines()) if row]
    signal.setitimer(signal.ITIMER_REAL, max(.001, work_deadline-time.monotonic()))
    try:
        env.update(subprocess_environment())
        result['driver_loader'] = driver_loader_evidence(env)
        with (output/'driver-loader.json').open('xb') as stream:
            stream.write(canonical(result['driver_loader']))
        check()
        rows = query(['uuid', 'name'])
        if len(rows) != 1 or len(rows[0]) != 2 or 'RTX PRO 6000' not in rows[0][1]:
            raise ValueError('expected exactly one RTX PRO 6000; no fallback allowed')
        gpu = rows[0][0].strip()
        result['gpu'] = {'uuid': gpu, 'name': rows[0][1].strip()}
        if any(row[0].strip() == gpu for row in query(['gpu_uuid', 'pid'], True)):
            raise ValueError('GPU already has a compute process')
        mounts = {}
        for item in protocol['datasets']:
            mount = find_mount(input_root, item['ref'])
            result['datasets'][item['kind']] = verify_files(mount, item['files'], check)
            mounts[item['kind']] = mount
        sandbox = Path(tempfile.mkdtemp(prefix='molmopoint-targeted448-'))
        (sandbox/'requirements.lock').write_bytes(requirements)
        env.update(HOME=str(sandbox), TMPDIR=str(sandbox), HF_HOME=str(sandbox/'hf'),
                   CUDA_VISIBLE_DEVICES='', NVIDIA_VISIBLE_DEVICES='void')
        venv = sandbox/'venv'
        for phase, argv in install_commands(sys.executable, venv, mounts['wheelhouse'],
                                             mounts['inputs'], sandbox/'requirements.lock'):
            processes.command(argv, log, min(started+900, work_deadline), env, phase)
        env.update(CUDA_VISIBLE_DEVICES=gpu, NVIDIA_VISIBLE_DEVICES=gpu)
        worker = ('import json,sys; sys.path.insert(0,sys.argv[1]); '
                  'from research.molmopoint_identification_v1.inference import run; '
                  'run(sys.argv[2],sys.argv[3],sys.argv[4],json.loads(sys.argv[5]),float(sys.argv[6]))')
        processes.command([str(venv/'bin/python'), '-I', '-c', worker, str(root), str(mounts['model']),
            str(mounts['inputs']), str(output/'worker'),
            json.dumps({name: row['version'] for name, row in pins.items()}), str(work_deadline)],
            log, work_deadline, env, 'six-case GPU worker')
        summary = json.loads((output/'worker/worker.json').read_bytes())
        result['generation_requests'] = summary['generation_requests']
        if summary['generation_requests'] != 6:
            raise ValueError('six responses required')
        check()
    except BaseException as error:
        failure = error
        result.update(error_type=type(error).__name__, error=str(error)[:1000])
    finally:
        signal.setitimer(signal.ITIMER_REAL, max(.001, deadline-time.monotonic()))
        try:
            cleanup = processes.stop(deadline)
            result['cleanup'] = cleanup
            if not cleanup['groups_absent'] or cleanup['error'] or cleanup['interrupted']:
                raise ValueError('process-group cleanup not verified')
            if gpu is None or any(row[0].strip() == gpu for row in query(['gpu_uuid', 'pid'], True)):
                raise ValueError('GPU cleanup not verified')
            devices = query(['uuid', 'name'])
            if len(devices) != 1 or devices[0][0].strip() != gpu or 'RTX PRO 6000' not in devices[0][1]:
                raise ValueError('bound GPU identity unavailable at cleanup')
            result['gpu_cleanup_verified'] = True
            result['cleanup'] = processes.stop(deadline)
            if result['cleanup']['error'] or result['cleanup']['interrupted'] or not result['cleanup']['groups_absent']:
                raise ValueError('final GPU census group cleanup failed')
            if sandbox is not None:
                shutil.rmtree(sandbox)
            result['temporary_environment_removed'] = sandbox is None or not sandbox.exists()
        except BaseException as error:
            failure = failure or error
            result['cleanup_error'] = type(error).__name__+': '+str(error)[:1000]
            # A census started during cleanup must also be terminated after failure.
            signal.setitimer(signal.ITIMER_REAL, 0)
            result['emergency_cleanup'] = processes.stop(deadline)
        finally:
            remaining = deadline-time.monotonic()
            signal.setitimer(signal.ITIMER_REAL, max(.001, remaining) if remaining > 0 else 0)
    if failure is None and time.monotonic() < deadline:
        result['status'] = 'provisional_complete'
    result['output_sha256'] = {p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in output.rglob('*') if p.is_file()}
    return finish(result, output, started, deadline)
