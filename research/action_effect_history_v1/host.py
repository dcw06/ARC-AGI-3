"""Model host (model interpreter): start the model, run one canary, serve the bounded bridge."""
from dataclasses import replace
import importlib.metadata
import json
import math
from pathlib import Path
import time

from certification.phase4_integrated_v2.bridge import BridgeServer
from certification.phase4_integrated_v2.evidence import EvidenceStore
from .service import HistoryModelService

ROOT = Path(__file__).resolve().parents[2]


def expected_artifact(root=ROOT):
    from research.grounded_action_v1.artifact_contract import expected_artifact as frozen
    return frozen(root)  # the same pinned model tree as every earlier run


def pinned_model_factory(retain, deadline, _fault='none'):
    """Live only: construct the pinned vLLM server in this isolated model interpreter."""
    if time.monotonic() >= deadline:
        raise TimeoutError('model startup admission closed')
    from certification.phase4_v6.target_install_probe_r5 import MODEL_CHECK
    exec(compile(MODEL_CHECK, 'action_effect_history_model_readiness', 'exec'), {})
    from certification.phase4_integrated_v2.model_process import ModelService, load_operational_primary
    from certification.phase4_integrated_v2.model_artifact import verify_artifact
    from certification.phase4_integrated_v2.model_transport import OpenAICompatibleCompletionClient
    for package, expected in {'transformers': '4.57.6', 'tokenizers': '0.22.2', 'jinja2': '3.1.6',
                              'vllm': '0.19.0', 'torch': '2.10.0'}.items():
        if importlib.metadata.version(package).split('+')[0] != expected:
            raise ValueError('pinned model package drift: ' + package)
    primary = replace(load_operational_primary(ROOT), scratch_log=Path('/dev/stdout'),
                      readiness_timeout_seconds=min(900, max(1, deadline - time.monotonic())),
                      completion_canary_timeout_seconds=120, request_timeout_seconds=120,
                      hard_seconds=3300, finalization_reserve_seconds=300)
    artifact = verify_artifact(primary)
    if artifact != expected_artifact(ROOT):
        raise ValueError('verified model artifact differs from the frozen profile')

    class ServerWithoutLegacyCanary(ModelService):
        def _completion_canary(self):
            pass  # the single retained canary runs through HistoryModelService

    owner = ServerWithoutLegacyCanary(primary)
    try:
        owner.start()
        client = OpenAICompatibleCompletionClient(primary.base_url, timeout_seconds=120)
        service = HistoryModelService(primary.model_path, client.complete, retain_canary=retain)
        service.artifact = artifact
        return service, owner
    except BaseException:
        owner.close()
        raise


def rehearsal_factory(retain, deadline, fault='none'):
    """CPU rehearsal only: scripted transport and fixture tokenizer; artifact labelled as rehearsal."""
    from .authority import rehearsal_gate
    from .rehearsal import FixtureTokenizer, ScriptedTransport
    rehearsal_gate()
    if fault == 'model_startup':
        raise TimeoutError('rehearsal model startup failure')
    service = HistoryModelService('rehearsal', ScriptedTransport(fault, slow_seconds=2.0),
                                  tokenizer=FixtureTokenizer(), retain_canary=retain, check_versions=False)
    service.artifact = {'rehearsal': 'scripted_model_not_target_evidence'}
    class Owner:
        def close(self):
            return None
    return service, Owner()


def serve_host(socket_path, evidence_root, cancel_path, *, deadline, service_factory, fault='none',
               evidence_limit=4 * 1024**2, clock=time.monotonic):
    """Retain startup and canary state; serve only after one validated canary."""
    if type(deadline) not in (int, float) or not math.isfinite(deadline) or evidence_limit < 512:
        raise ValueError('host limits')
    socket_path, cancel_path = Path(socket_path), Path(cancel_path)
    store = EvidenceStore(evidence_root, 'worker')
    begun = clock()
    status = {'scope': 'action_effect_history_model_host', 'status': 'starting', 'startup_seconds': None, 'error': None}
    service = owner = None
    used = 0

    def retain(record):
        nonlocal used
        raw = json.dumps(record, sort_keys=True, allow_nan=False).encode()
        if len(raw) > evidence_limit or used + len(raw) > evidence_limit:
            raise ValueError('host canary evidence exhausted')
        store.save('canary.json', record)
        used += len(raw)

    try:
        if clock() >= deadline or cancel_path.exists():
            raise TimeoutError('host startup admission closed')
        store.save('host-status.json', status)
        service, owner = service_factory(retain, deadline, fault)
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
                      policy_calls=service.calls)
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
    args = parser.parse_args()
    if args.mode == 'live':
        from .authority import require
        require()  # before model import, subprocess or GPU query
        if args.fault != 'none':
            raise PermissionError('faults are rehearsal-only')
        factory = pinned_model_factory
    else:
        factory = rehearsal_factory
    result = serve_host(args.socket, args.evidence, args.cancel, deadline=args.deadline,
                        service_factory=factory, fault=args.fault)
    raise SystemExit(0 if result['status'] == 'stopped' else 1)


if __name__ == '__main__':
    main()
