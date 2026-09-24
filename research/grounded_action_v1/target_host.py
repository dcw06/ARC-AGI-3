"""Review-only Stage B model host; CLI deliberately has no live authority.

The injectable lifecycle is exercised on CPU. A later launch revision must
bind this source to fresh approvals, isolated model/game interpreters and an
external monitor before exposing a live entrypoint.
"""
from dataclasses import replace
import importlib.metadata
import json
import math
from pathlib import Path
import time

from certification.phase4_integrated_v2.bridge import BridgeServer
from certification.phase4_integrated_v2.evidence import EvidenceStore
from .artifact_contract import expected_artifact
from .bridge_service import BridgeService

ROOT = Path(__file__).resolve().parents[2]


def pinned_model_factory(retain, deadline):
    """Construct the pinned server in an isolated model Python process only."""
    if time.monotonic() >= deadline:
        raise TimeoutError('model startup admission closed')
    from certification.phase4_v6.target_install_probe_r5 import MODEL_CHECK
    exec(compile(MODEL_CHECK, 'stage_b_model_readiness', 'exec'), {})
    from certification.phase4_integrated_v2.model_process import ModelService, load_operational_primary
    from certification.phase4_integrated_v2.model_artifact import verify_artifact
    from certification.phase4_integrated_v2.model_transport import OpenAICompatibleCompletionClient

    for package, expected in {'transformers': '4.57.6', 'tokenizers': '0.22.2',
                              'jinja2': '3.1.6', 'vllm': '0.19.0', 'torch': '2.10.0'}.items():
        if importlib.metadata.version(package).split('+')[0] != expected:
            raise ValueError('pinned model package drift: ' + package)
    primary = replace(load_operational_primary(ROOT), scratch_log=Path('/dev/stdout'),
                      readiness_timeout_seconds=min(900, max(1, deadline - time.monotonic())),
                      completion_canary_timeout_seconds=120, request_timeout_seconds=120,
                      hard_seconds=3300, finalization_reserve_seconds=300)
    artifact = verify_artifact(primary)
    if artifact != expected_artifact(ROOT):
        raise ValueError('verified model artifact differs from frozen Stage B profile')

    class ServerWithoutLegacyCanary(ModelService):
        def _completion_canary(self):
            # Stage B's single retained canary runs through BridgeService.
            pass

    owner = ServerWithoutLegacyCanary(primary)
    try:
        owner.start()
        client = OpenAICompatibleCompletionClient(primary.base_url, timeout_seconds=120)
        bridge = BridgeService(primary.model_path, client.complete, retain_canary=retain)
        bridge.artifact = artifact
        return bridge, owner
    except BaseException:
        owner.close()
        raise


def serve_host(socket_path, evidence_root, cancel_path, *, deadline, service_factory,
               evidence_limit=4 * 1024**2, clock=time.monotonic):
    """Retain startup/canary state and serve only after one validated canary."""
    if (type(deadline) not in (int, float) or not math.isfinite(deadline) or
            type(evidence_limit) is not int or evidence_limit < 512):
        raise ValueError('host limits')
    socket_path, cancel_path = Path(socket_path), Path(cancel_path)
    store = EvidenceStore(evidence_root, 'worker')
    begun = clock()
    status = {'scope': 'stage_b_review_host', 'status': 'starting',
              'startup_seconds': None, 'error': None}
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
        service, owner = service_factory(retain, deadline)
        if clock() >= deadline or cancel_path.exists():
            raise TimeoutError('model server startup deadline')
        service.startup_canary()
        service.startup_seconds = clock() - begun
        if clock() >= deadline or cancel_path.exists():
            raise TimeoutError('host canary deadline')
        status.update(status='ready', startup_seconds=service.startup_seconds)
        store.save('host-status.json', status)
        with BridgeServer(socket_path, service, deadline, cancel_path) as server:
            while clock() < deadline and not cancel_path.exists():
                server.handle_request()
        status.update(status='stopped', error='canceled' if cancel_path.exists() else 'deadline')
    except Exception as exc:
        status.update(status='failed', error=type(exc).__name__ + ': ' + str(exc)[:256])
        store.save('failure.json', {'error': status['error']}, failure_receipt=True)
    finally:
        if owner is not None:
            try:
                owner.close()
            except Exception as exc:
                status.update(status='failed', error='model cleanup: ' + type(exc).__name__)
                store.save('failure.json', {'error': status['error']}, failure_receipt=True)
        status['ended_seconds'] = clock() - begun
        store.save('host-status.json', status)
    return status


def main():
    import argparse
    from .authority import require
    require()  # Before model import, environment inspection, subprocess or GPU query.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--socket', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--cancel', type=Path, required=True)
    parser.add_argument('--deadline', type=float, required=True)
    args = parser.parse_args()
    result = serve_host(args.socket, args.evidence, args.cancel,
                        deadline=args.deadline, service_factory=pinned_model_factory)
    raise SystemExit(0 if result['status'] == 'stopped' else 1)


if __name__ == '__main__':
    main()
