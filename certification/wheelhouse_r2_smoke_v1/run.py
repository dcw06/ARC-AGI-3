"""The smoke-test sequence, shared by the live attempt and the scripted CPU rehearsals (only injected effects differ):
host facts -> bundle integrity -> offline install and package checks -> GPU facts -> model artifact -> server startup
-> startup probes -> inference -> cancellation probes -> termination and cleanup -> retained evidence.
One attempt; nothing is retried; any failure ends the run, still stopping the server and retaining evidence."""
import json
import signal
import sys
import tempfile
import time
from pathlib import Path

from certification.wheelhouse_r2_smoke_v1 import host
from certification.wheelhouse_r2_smoke_v1.accounting import Clock, Ledger
from certification.wheelhouse_r2_smoke_v1.client import Client, RequestFailed
from certification.wheelhouse_r2_smoke_v1.evidence import Evidence
from certification.wheelhouse_r2_smoke_v1.install import install, verify_bundle
from certification.wheelhouse_r2_smoke_v1.server import ModelServer, argv_for

NOT_ESTABLISHED = ['solving ability or task performance', 'Phase 4 completion', 'throughput or capacity limits',
                   'behaviour beyond the frozen request plan']


def run(mode, protocol, output, started, *, bundle, workdir, gpu_query=None, model_check=None, server_argv=None,
        python=sys.executable, now=time.monotonic, sleep=time.sleep, attempt_id=None):
    if mode not in ('live', 'rehearsal'):
        raise ValueError('mode must be live or rehearsal')
    if mode == 'live' and gpu_query is None:
        raise ValueError('the live path requires GPU queries')
    limits, runtime, server_cfg = protocol['limits'], protocol['runtime'], protocol['server']
    evidence = Evidence(output, mode)
    clock = Clock(limits, started, now)
    ledger = Ledger(protocol['requests'], limits['maximum_model_requests'], clock)
    result = {'passed': False, 'failed_stage': None, 'error': None, 'stages': {}, 'requests': {},
              'gpu_telemetry': [], 'not_established': NOT_ESTABLISHED, 'attempt_id': attempt_id}
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    if gpu_query is None:
        result['stages']['gpu'] = 'not_exercised (no GPU in a CPU rehearsal)'
    server = gpu = None
    stage_name = None

    def stage(name, action):
        nonlocal stage_name
        stage_name = name
        clock.check(name)
        begin = now()
        try:
            value = action()
        except BaseException:
            clock.record(name, begin, 'failed')
            raise
        clock.record(name, begin, 'passed')
        result['stages'][name] = value if value is not None else 'passed'
        return value

    def telemetry(label):
        if gpu is not None:
            result['gpu_telemetry'].append({'label': label, **host.gpu_sample(gpu['uuid'], gpu_query)})

    try:
        stage('host', lambda: host.host_facts(runtime))
        install_deadline = started + limits['installation_seconds']

        def within_install():
            if now() >= install_deadline:
                raise TimeoutError('installation deadline reached')
        stage('bundle_integrity', lambda: verify_bundle(bundle, protocol['dataset'], protocol['bundle'],
                                                        within_install))
        installed = stage('installation', lambda: install(bundle, workdir / 'venv', runtime, install_deadline,
                                                          workdir / 'install.log', python=python))
        if gpu_query is not None:
            gpu = stage('gpu', lambda: host.gpu_facts(runtime, gpu_query))
            telemetry('before_server')
        model_deadline = clock.phase_deadline(limits['model_verification_seconds'])

        def within_model():
            if now() >= model_deadline:
                raise TimeoutError('model verification deadline reached')
        stage('model_artifact', lambda: (model_check or (lambda c: host.verify_model(protocol['model'], c)))(
            within_model))
        argv = (server_argv or (lambda py: argv_for(server_cfg, py, protocol['model']['mounted_path'],
                                                     server_cfg['port'])))(installed['python'])
        server = ModelServer(argv, server_cfg['env'], workdir / 'server.log', server_cfg['host'], server_cfg['port'])
        stage('server_start', server.start)
        startup_deadline = clock.phase_deadline(limits['startup_ceiling_seconds'])
        stage('server_ready', lambda: {'seconds': round(server.wait_ready(startup_deadline), 3)})
        client = Client(server_cfg['host'], server_cfg['port'], ledger, clock, server_cfg['served_model_name'])
        sampling = protocol['sampling']

        def health():
            status, _ = client.call('S1')
            if status != 200:
                raise RequestFailed(f'S1: HTTP {status}')
            return {'status': status}

        def models():
            status, data = client.call('S2')
            names = [m.get('id') for m in json.loads(data).get('data', [])] if status == 200 else []
            if server_cfg['served_model_name'] not in names:
                raise RequestFailed(f'S2: served model not listed ({names})')
            return {'models': names}
        result['requests']['S1'] = stage('startup_probe_S1', health)
        result['requests']['S2'] = stage('startup_probe_S2', models)
        result['requests']['S3'] = stage('startup_probe_S3', lambda: client.completion('S3', 'canary', sampling))
        telemetry('after_startup')
        cases = {item['id']: item.get('case') for item in protocol['requests']}
        for request_id in ('I1', 'I2', 'I3', 'I4'):
            result['requests'][request_id] = stage('inference_' + request_id,
                                                   lambda r=request_id: client.completion(r, cases[r], sampling))
        result['observations'] = {
            'I1_I2_identical': result['requests']['I1']['content'] == result['requests']['I2']['content'],
            'I4_answer': result['requests']['I4']['content'],
            'note': 'observations are recorded, not pass criteria'}
        telemetry('after_inference')
        result['requests']['C1'] = stage('cancellation_C1', lambda: client.stream_then_cancel('C1', cases['C1'],
                                                                                             sampling))
        result['requests']['C2'] = stage('cancellation_C2_idle', lambda: client.idle_after_cancel('C2', sleep))
        result['requests']['C3'] = stage('cancellation_C3_responsive',
                                         lambda: client.completion('C3', cases['C3'], sampling))
        telemetry('after_cancellation')
        result['completed_plan'] = True
    except BaseException as exc:  # includes the live alarm; recorded, then cleanup still runs
        result['failed_stage'] = stage_name
        result['error'] = f'{type(exc).__name__}: {str(exc)[:500]}'
        if not isinstance(exc, Exception):
            raise
    finally:
        stop_deadline = min(now() + server_cfg['terminate_grace_seconds'] + server_cfg['kill_grace_seconds'] + 5,
                            clock.cleanup_deadline())
        stopped = server.stop(stop_deadline, server_cfg['terminate_grace_seconds'], server_cfg['kill_grace_seconds']) \
            if server else {'groups_absent': True, 'note': 'server never started'}
        result['cleanup'] = {'server': stopped}
        if gpu is not None:
            result['cleanup']['gpu'] = host.gpu_cleanup(gpu['uuid'], stopped['groups_absent'], gpu_query)
            cleaned = result['cleanup']['gpu']['gpu_cleanup_verified']
        else:
            result['cleanup']['gpu'] = 'not_exercised (no GPU in a CPU rehearsal)'
            cleaned = stopped['groups_absent']
        result['cleanup_verified'] = cleaned
        result['passed'] = bool(result.get('completed_plan')) and cleaned and result['error'] is None
        if result['error'] is None and not cleaned:
            result['failed_stage'], result['error'] = 'cleanup', 'process or GPU cleanup not verified'
        result['ledger'] = ledger.summary()
        result['phases'] = clock.phases
        result['elapsed_seconds'] = round(clock.elapsed(), 3)
        result['limits'] = limits
        evidence.text_tail('logs/server.log', workdir / 'server.log', server_cfg['log_retained_bytes'])
        evidence.text_tail('logs/install.log', workdir / 'install.log', server_cfg['log_retained_bytes'])
        final = evidence.finalize(result)
    return final


def live_main(root, output, started, working):
    """Live entry, called from the notebook only after `binding.consume`. Installs a whole-run alarm at the internal
    deadline so a hang still reaches cleanup and evidence retention."""
    from certification.wheelhouse_r2_smoke_v1.binding import require_live
    protocol, execution = require_live(root)  # again: nothing below runs unless every condition holds
    remaining = protocol['limits']['internal_seconds'] - (time.monotonic() - started)
    if remaining <= protocol['limits']['cleanup_reserve_seconds']:
        raise TimeoutError('clock exhausted before the run could start')

    def alarm(*_):
        raise TimeoutError('internal deadline (whole-run alarm)')
    signal.signal(signal.SIGALRM, alarm)
    signal.setitimer(signal.ITIMER_REAL, remaining - protocol['limits']['cleanup_reserve_seconds'])
    try:
        bundle = host.dataset_mount(protocol['dataset']['ref'], protocol['dataset']['version'])
        with tempfile.TemporaryDirectory(prefix='wheelhouse-r2-smoke-', dir=working) as folder:
            return run('live', protocol, output, started, bundle=bundle, workdir=folder, gpu_query=host.nvidia_smi,
                       attempt_id=execution['attempt_id'])
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
