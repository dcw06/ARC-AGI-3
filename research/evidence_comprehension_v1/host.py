"""Model host (model interpreter): start the server, run one canary, verify caching is off, serve the bridge.

Live: the pinned vLLM server from the frozen operational launch spec, with exactly one derived
change: `--enable-prefix-caching` is replaced by `--no-enable-prefix-caching`. The derived argv is
retained. Rehearsal: the CPU fake server over real local HTTP (never target evidence).
"""
from dataclasses import replace
import importlib.metadata
import json
import math
from pathlib import Path
import time

from certification.phase4_integrated_v2.bridge import BridgeServer
from certification.phase4_integrated_v2.evidence import EvidenceStore
from . import schedule
from .service import QuestionnaireService

ROOT = Path(__file__).resolve().parents[2]
ENABLE, DISABLE = '--enable-prefix-caching', '--no-enable-prefix-caching'


def expected_artifact(root=ROOT):
    from research.grounded_action_v1.artifact_contract import expected_artifact as frozen
    return frozen(root)  # the same pinned model tree as every earlier run


def derived_argv(argv):
    """The frozen launch argv with prefix caching disabled; any other difference is refused."""
    if argv.count(ENABLE) != 1 or DISABLE in argv:
        raise ValueError('frozen launch spec no longer has exactly one prefix-caching flag')
    return [DISABLE if item == ENABLE else item for item in argv]


def _server_root(base_url):
    return base_url[:-3] if base_url.rstrip('/').endswith('/v1') else base_url.rstrip('/')


def pinned_model_factory(retain, deadline, *, fault='none', timeout_seconds, verify_seconds, **_):
    """Live only: construct the pinned vLLM server, with caching disabled, in this isolated model interpreter."""
    if time.monotonic() >= deadline:
        raise TimeoutError('model startup admission closed')
    from certification.phase4_v6.target_install_probe_r5 import MODEL_CHECK
    exec(compile(MODEL_CHECK, 'evidence_comprehension_model_readiness', 'exec'), {})
    from certification.phase4_integrated_v2.model_process import ModelService, load_operational_primary
    from certification.phase4_integrated_v2.model_artifact import verify_artifact
    from certification.phase4_integrated_v2.tokenizer_binding import verify
    from transformers import AutoTokenizer
    from .transport import CancellableTransport, read_metrics, verify_idle
    for package, expected in {'transformers': '4.57.6', 'tokenizers': '0.22.2', 'jinja2': '3.1.6',
                              'vllm': '0.19.0', 'torch': '2.10.0'}.items():
        if importlib.metadata.version(package).split('+')[0] != expected:
            raise ValueError('pinned model package drift: ' + package)
    primary = replace(load_operational_primary(ROOT), scratch_log=Path('/dev/stdout'),
                      readiness_timeout_seconds=min(900, max(1, deadline - time.monotonic())),
                      completion_canary_timeout_seconds=120, request_timeout_seconds=timeout_seconds,
                      hard_seconds=3300, finalization_reserve_seconds=300)
    artifact = verify_artifact(primary)
    if artifact != expected_artifact(ROOT):
        raise ValueError('verified model artifact differs from the frozen profile')
    launch = {}

    class CachingDisabledServer(ModelService):
        def _argv_and_env(self):
            argv, env = super()._argv_and_env()
            argv = derived_argv(argv)
            launch.update(argv=list(argv), derived_from=str(self.primary.launch_spec_path.relative_to(ROOT)))
            return argv, env

        def _completion_canary(self):
            pass  # the single retained canary runs through QuestionnaireService

    owner = CachingDisabledServer(primary)
    try:
        owner.start()
        root = _server_root(primary.base_url)
        verify(primary.model_path)
        tokenizer = AutoTokenizer.from_pretrained(str(primary.model_path), local_files_only=True, trust_remote_code=False)
        service = QuestionnaireService(
            tokenizer, CancellableTransport(root, timeout_seconds),
            metrics=lambda deadline: read_metrics(root, deadline), verify_idle=lambda deadline: verify_idle(root, deadline),
            timeout_seconds=timeout_seconds, verify_seconds=verify_seconds, teardown_seconds=schedule.TEARDOWN_SECONDS,
            **retain)
        service.launch, service.artifact = launch, artifact
        return service, owner
    except BaseException:
        owner.close()
        raise


def rehearsal_factory(retain, deadline, *, fault='none', timeout_seconds, verify_seconds, latency_seconds=0.0):
    """CPU rehearsal only: the fake server over real HTTP and the fixture tokenizer."""
    from .authority import rehearsal_gate
    from research.action_effect_history_v1.rehearsal import FixtureTokenizer
    from .fake_server import FakeVLLM
    from .transport import CancellableTransport, read_metrics, verify_idle
    rehearsal_gate()
    if fault == 'model_startup':
        raise TimeoutError('rehearsal model startup failure')
    from .fake_server import FAULTS as SERVER_FAULTS
    server = FakeVLLM(fault=fault if fault in SERVER_FAULTS else 'none', latency_seconds=latency_seconds).start()
    service = QuestionnaireService(
        FixtureTokenizer(), CancellableTransport(server.base_url, timeout_seconds),
        metrics=lambda deadline: read_metrics(server.base_url, deadline),
        verify_idle=lambda deadline: verify_idle(server.base_url, deadline),
        timeout_seconds=timeout_seconds, verify_seconds=verify_seconds, teardown_seconds=schedule.TEARDOWN_SECONDS,
        **retain)
    if fault == 'late_reply':  # rehearsal: the host answers only after the worker's per-call bound has passed
        answer = service.complete

        def late(request):
            value = answer(request)
            if service.calls == 7:
                time.sleep(timeout_seconds + schedule.TEARDOWN_SECONDS + verify_seconds + schedule.BRIDGE_MARGIN_SECONDS + 1)
            return value
        service.complete = late
    service.launch = {'rehearsal_fake_server': True, 'fault': fault, 'latency_seconds': latency_seconds}
    service.artifact = {'rehearsal': 'scripted_model_not_target_evidence'}

    class Owner:
        def close(self):
            server.close()
    return service, Owner()


def serve_host(socket_path, evidence_root, cancel_path, *, deadline, service_factory, fault='none',
               timeout_seconds=schedule.PER_CALL_TIMEOUT_SECONDS, verify_seconds=schedule.CANCELLATION_VERIFY_SECONDS,
               latency_seconds=0.0, evidence_limit=4 * 1024**2, clock=time.monotonic):
    """Retain startup, canary, server and cancellation evidence; serve only after the canary and cache check."""
    if type(deadline) not in (int, float) or not math.isfinite(deadline) or evidence_limit < 512:
        raise ValueError('host limits')
    socket_path, cancel_path = Path(socket_path), Path(cancel_path)
    store = EvidenceStore(evidence_root, 'worker')
    begun = clock()
    status = {'scope': 'evidence_comprehension_model_host', 'status': 'starting', 'startup_seconds': None, 'error': None}
    service = owner = None
    used = {'bytes': 0}

    def bounded(name):
        def save(record):
            raw = json.dumps(record, sort_keys=True, allow_nan=False).encode()
            if len(raw) > evidence_limit or used['bytes'] + len(raw) > evidence_limit:
                raise ValueError('host evidence exhausted')
            store.save(name, record)
            used['bytes'] += len(raw)
        return save

    retain = {'retain_canary': bounded('canary.json'), 'retain_server': bounded('server-config.json'),
              'retain_cancellation': bounded('cancellations.json')}
    try:
        if clock() >= deadline or cancel_path.exists():
            raise TimeoutError('host startup admission closed')
        store.save('host-status.json', status)
        service, owner = service_factory(retain, deadline, fault=fault, timeout_seconds=timeout_seconds,
                                         verify_seconds=verify_seconds, latency_seconds=latency_seconds)
        if clock() >= deadline or cancel_path.exists():
            raise TimeoutError('model server startup deadline')
        service.startup_canary()
        service.startup_seconds = clock() - begun
        status.update(status='ready', startup_seconds=service.startup_seconds)
        store.save('host-status.json', status)
        with BridgeServer(socket_path, service, deadline, cancel_path) as server:
            while clock() < deadline and not cancel_path.exists():
                server.handle_request()
        status.update(status='stopped', error='canceled' if cancel_path.exists() else 'deadline',
                      questionnaire_calls=service.calls, cancellations=len(service.cancellations),
                      service_stopped=service.broken)
    except Exception as exc:
        status.update(status='failed', error=type(exc).__name__ + ': ' + str(exc)[:256])
        store.save('failure.json', {'error': status['error']}, failure_receipt=True)
    finally:
        if owner is not None:
            try:
                owner.close()
            except Exception as exc:
                status.update(status='failed', error='model cleanup: ' + type(exc).__name__)
        status['ended_seconds'] = clock() - begun
        store.save('host-status.json', status)
    return status


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--socket', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--cancel', type=Path, required=True)
    parser.add_argument('--deadline', type=float, required=True)
    parser.add_argument('--mode', choices=('live', 'rehearsal'), required=True)
    parser.add_argument('--fault', default='none')
    parser.add_argument('--call-timeout', type=float, default=schedule.PER_CALL_TIMEOUT_SECONDS)
    parser.add_argument('--verify-seconds', type=float, default=schedule.CANCELLATION_VERIFY_SECONDS)
    parser.add_argument('--latency', type=float, default=0.0)
    args = parser.parse_args()
    if args.mode == 'live':
        from .authority import require
        require()  # before model import, subprocess or GPU query
        if (args.fault != 'none' or args.call_timeout != schedule.PER_CALL_TIMEOUT_SECONDS
                or args.verify_seconds != schedule.CANCELLATION_VERIFY_SECONDS or args.latency != 0.0):
            raise PermissionError('live mode uses the frozen timeouts and no faults')
        factory = pinned_model_factory
    else:
        if not (0 < args.call_timeout <= schedule.PER_CALL_TIMEOUT_SECONDS
                and 0 < args.verify_seconds <= schedule.CANCELLATION_VERIFY_SECONDS and 0 <= args.latency <= 30):
            raise ValueError('rehearsal timing outside the live envelope')
        factory = rehearsal_factory
    result = serve_host(args.socket, args.evidence, args.cancel, deadline=args.deadline, service_factory=factory,
                        fault=args.fault, timeout_seconds=args.call_timeout, verify_seconds=args.verify_seconds,
                        latency_seconds=args.latency)
    raise SystemExit(0 if result['status'] == 'stopped' else 1)


if __name__ == '__main__':
    main()
