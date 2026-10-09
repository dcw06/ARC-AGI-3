# Derived by scripts/build_control_interface_action_selection_v2.py; edit the derivation.
"""The smoke-test sequence, shared by the live attempt and the scripted CPU rehearsals (only injected effects differ):
host facts -> bundle integrity -> offline install and package checks -> GPU facts -> model artifact -> server startup
-> startup probes -> inference -> cancellation probes -> termination and cleanup -> retained evidence.
One attempt; nothing is retried; any failure ends the run, still stopping the server and retaining evidence."""
import json
import shutil
import signal
import sys
import tempfile
import time
from pathlib import Path

from certification.direct_publisher_smoke_v1 import host
from certification.direct_publisher_smoke_v1.accounting import Clock, Ledger
from certification.direct_publisher_smoke_v1.client import Client, RequestFailed
from research.control_interface_action_selection_v2.evidence import Evidence
from certification.direct_publisher_smoke_v1.install import InstallationProcesses, install, verify_bundle
from certification.direct_publisher_smoke_v1.server import ModelServer, argv_for

NOT_ESTABLISHED = ['solving ability, level progress or action usefulness', 'Phase 4 completion', 'throughput or capacity limits',
                   'behaviour beyond the frozen request plan']


def run(mode, protocol, output, started, *, bundle, workdir, gpu_query=None, model_check=None, server_argv=None,
        python=sys.executable, now=time.monotonic, sleep=time.sleep, attempt_id=None, on_cleanup=None,
        on_environment_cleanup=None, trusted_inputs=None, experiment_root=None):
    if mode not in ('live', 'rehearsal'):
        raise ValueError('mode must be live or rehearsal')
    if mode == 'live' and gpu_query is None:
        raise ValueError('the live path requires GPU queries')
    if mode == 'live' and on_environment_cleanup is None:
        raise ValueError('the live path requires owned temporary-environment cleanup')
    if mode == 'live' and trusted_inputs is not None:
        raise ValueError('fixture trusted inputs are forbidden on the live path')
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
    installation = InstallationProcesses(server_cfg['terminate_grace_seconds'], server_cfg['kill_grace_seconds'])
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
                                                        within_install, inputs=trusted_inputs))
        installed = stage('installation', lambda: install(bundle, workdir / 'venv', runtime, install_deadline,
                                                          workdir / 'install.log', python=python, processes=installation,
                                                          requirements=Path(trusted_inputs) / 'trusted_requirements.lock' if trusted_inputs else None))
        if gpu_query is not None:
            gpu = stage('gpu', lambda: host.gpu_facts(runtime, gpu_query))
            telemetry('before_server')
        model_deadline = clock.phase_deadline(limits['model_verification_seconds'])

        def within_model():
            if now() >= model_deadline:
                raise TimeoutError('model verification deadline reached')
        model_artifact = stage('model_artifact', lambda: (model_check or (lambda c: host.verify_model(protocol['model'], c)))(
            within_model))
        model_path = model_artifact.get('mounted_path', protocol['model']['mounted_path'])
        argv = (server_argv or (lambda py: argv_for(server_cfg, py, model_path,
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
        from research.control_interface_action_selection_v2.probe import run_cases
        from research.control_interface_action_selection_v2.runtime_controls import verify_cache_disabled
        if experiment_root is None:
            raise ValueError('frozen experiment root required')
        stage('cache_config', lambda: verify_cache_disabled(workdir / 'server.log'))
        result['action_selection'] = stage('action_selection', lambda: run_cases(experiment_root, client, evidence, clock))
        telemetry('after_action_selection')
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
        # Cleanup is its own phase: first stop the cutoff alarm from interrupting it (retried once: the alarm is
        # one-shot), then stop processes within the cleanup reserve. stop() escalates to SIGKILL regardless.
        transition = []
        for _ in range(2):
            try:
                if on_cleanup:
                    on_cleanup()
                transition.append('entered')
                break
            except BaseException as exc:  # noqa: B036 - the alarm may land here; never skip cleanup
                transition.append(f'interrupted: {type(exc).__name__}')
        result['cleanup_phase'] = {'entered_at': round(clock.elapsed(), 3), 'transition': transition,
                                   'deadline_at': round(clock.cleanup_deadline() - started, 3)}
        stop_deadline = min(now() + server_cfg['terminate_grace_seconds'] + server_cfg['kill_grace_seconds'] + 5,
                            clock.cleanup_deadline())
        begin = now()
        stopped = server.stop(stop_deadline, server_cfg['terminate_grace_seconds'], server_cfg['kill_grace_seconds']) \
            if server else {'groups_absent': True, 'ownership': 'never_spawned', 'note': 'server never started'}
        clock.record('server_cleanup', begin, 'passed' if stopped['groups_absent'] else 'failed')
        begin = now()
        installed_cleanup = installation.stop(stop_deadline)
        clock.record('installation_cleanup', begin, 'passed' if installed_cleanup['groups_absent']
                     and not installed_cleanup['error'] else 'failed')
        groups_absent = stopped['groups_absent'] and installed_cleanup['groups_absent']
        result['cleanup'] = {'server': stopped, 'installation': installed_cleanup, 'groups_absent': groups_absent}
        if gpu is not None:
            begin = now()
            result['cleanup']['gpu'] = host.gpu_cleanup(gpu['uuid'], groups_absent, gpu_query)
            cleaned = groups_absent and result['cleanup']['gpu']['gpu_cleanup_verified']
            clock.record('gpu_cleanup', begin, 'passed' if cleaned else 'failed')
        else:
            result['cleanup']['gpu'] = ('not_exercised (GPU verification stage not reached)' if mode == 'live'
                                        else 'not_exercised (no GPU in a CPU rehearsal)')
            cleaned = groups_absent
        cleaned = cleaned and installed_cleanup['error'] is None
        interruptions = stopped.get('interrupted', []) + installed_cleanup['interrupted']
        if interruptions:
            result['cleanup_interrupted'] = interruptions
        result['cleanup_verified'] = cleaned
        eligible = (bool(result.get('completed_plan')) and cleaned and result['error'] is None
                    and not interruptions)
        if result['error'] is None and not cleaned:
            result['failed_stage'], result['error'] = 'cleanup', 'process or GPU cleanup not verified'
        result['ledger'] = ledger.summary()
        result['phases'] = clock.phases
        result['elapsed_seconds'] = round(clock.elapsed(), 3)
        result['limits'] = limits
        begin = now()
        evidence.text_tail('logs/server.log', workdir / 'server.log', server_cfg['log_retained_bytes'])
        evidence.text_tail('logs/install.log', workdir / 'install.log', server_cfg['log_retained_bytes'])
        clock.record('log_retention', begin, 'passed')
        # Logs have been retained before removing the venv, scratch and (in the notebook) extracted source.
        # Cleanup still runs after an overrun; that never restores eligibility for a passing verdict.
        begin = now()
        try:
            details = on_environment_cleanup() if on_environment_cleanup else None
            result['cleanup']['environment'] = {'removed': True if on_environment_cleanup else None, 'details': details,
                                                 'scope': 'owned temporary directories' if on_environment_cleanup
                                                 else 'caller-retained rehearsal work directory'}
        except Exception as exc:
            eligible = False
            result['cleanup_verified'] = False
            result['cleanup']['environment'] = {'removed': False, 'error': f'{type(exc).__name__}: {exc}'}
            if result['error'] is None:
                result['failed_stage'], result['error'] = 'environment_cleanup', str(exc)[:500]
        clock.record('environment_cleanup', begin, 'not_applicable' if not on_environment_cleanup else
                     'passed' if result['cleanup']['environment']['removed'] else 'failed')
        # Persist a non-passing result first. Only a complete lifecycle, including evidence finalization,
        # can reach the explicit final deadline check and become a passing verdict.
        result['verdict_status'] = 'pending_lifecycle'
        begin = now()
        evidence.finalize(result)
        clock.record('evidence_finalization', begin, 'passed')

        def final_deadline_check(phase):
            elapsed = clock.elapsed()
            try:
                clock.check(phase)
                met = True
            except TimeoutError as exc:
                met = False
                result['passed'] = False
                if result['error'] is None:
                    result['failed_stage'], result['error'] = 'lifecycle_deadline', str(exc)
            result['lifecycle_deadline'] = {'met': met, 'checked_after': phase,
                                            'checked_at_seconds': elapsed,
                                            'internal_seconds': limits['internal_seconds']}
            result['elapsed_seconds'] = round(elapsed, 3)
            return met

        met = final_deadline_check('GPU cleanup, environment removal and evidence finalization')
        result['passed'] = eligible and met
        result['verdict_status'] = 'passed' if result['passed'] else 'failed'
        try:
            final = evidence.finalize(result)
        except BaseException as exc:
            # A partially published verdict is not success. Try to retain failure evidence; if storage itself
            # is broken, propagate instead of returning a passing result.
            result['passed'], result['verdict_status'] = False, 'failed'
            result['failed_stage'], result['error'] = 'verdict_publication', f'{type(exc).__name__}: {exc}'
            try:
                evidence.finalize(result)
            except BaseException:
                pass
            raise
        # Verdict/manifest publication is also accounted for. If it crosses the deadline, replace the result
        # with failure and rebuild its manifest. Failure evidence may be written after the deadline.
        try:
            clock.check('final verdict and manifest publication')
        except TimeoutError:
            final_deadline_check('final verdict and manifest publication')
            result['passed'], result['verdict_status'] = False, 'failed'
            final = evidence.finalize(result)
    return final


class CutoffAlarm:
    """The whole-run alarm at the admission cutoff. `enter_cleanup` disarms it and blocks SIGALRM, so the cutoff can
    never interrupt cleanup; `release` restores the previous state without delivering a pending alarm."""

    def __init__(self):
        self.previous = None
        self.in_cleanup = False

    @staticmethod
    def _raise(*_):
        raise TimeoutError('internal deadline (admission cutoff alarm)')

    def arm(self, seconds):
        if seconds <= 0:
            raise TimeoutError('clock exhausted before the run could start')
        self.previous = signal.signal(signal.SIGALRM, self._raise)
        signal.setitimer(signal.ITIMER_REAL, seconds)

    def enter_cleanup(self):
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
        signal.setitimer(signal.ITIMER_REAL, 0)
        self.in_cleanup = True

    def release(self):
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, signal.SIG_IGN)  # a pending alarm is discarded, not raised
        signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGALRM})
        signal.signal(signal.SIGALRM, self.previous if self.previous is not None else signal.SIG_DFL)


def live_main(root, output, started, working, *, on_source_cleanup=None):
    """Live entry, called from the notebook only after `binding.consume`. A cutoff alarm hands a hung run to cleanup;
    cleanup itself runs with the alarm disarmed and blocked."""
    from research.control_interface_action_selection_v2.binding import require_live
    protocol, execution = require_live(root)  # again: nothing below runs unless every condition holds
    limits = protocol['limits']
    alarm = CutoffAlarm()
    alarm.arm(limits['admission_cutoff_seconds'] - (time.monotonic() - started))
    folder = None
    try:
        bundle = host.dataset_mount(protocol['dataset']['ref'], protocol['dataset']['version'])
        folder = Path(tempfile.mkdtemp(prefix='control-interface-probe-', dir=working))

        def remove_environment():
            shutil.rmtree(folder)
            if folder.exists():
                raise RuntimeError('temporary environment removal was not verified')
            if on_source_cleanup:
                on_source_cleanup()
            return {'temporary_environment_removed': True,
                    'embedded_source_removed': bool(on_source_cleanup)}

        return run('live', protocol, output, started, bundle=bundle, workdir=folder, gpu_query=host.nvidia_smi,
                   attempt_id=execution['attempt_id'], on_cleanup=alarm.enter_cleanup,
                   on_environment_cleanup=remove_environment, experiment_root=root)
    finally:
        try:
            # Emergency fallback for exceptions before the normal cleanup callback. This path cannot return pass.
            if folder is not None and folder.exists():
                shutil.rmtree(folder)
        finally:
            alarm.release()
