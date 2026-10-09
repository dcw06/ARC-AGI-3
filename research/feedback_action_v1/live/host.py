# Derived from research/action_effect_history_v1/host.py by research/feedback_action_v1/derive.py; edit the derivation, not this file.
"""Model host (model interpreter): verify the pinned model snapshot, start the verified-runtime server, run one
canary, serve the bounded bridge (successor runtime v1)."""
import functools
import importlib.metadata
import json
import math
from pathlib import Path
import sys
import time

from certification.phase4_integrated_v2.bridge import BridgeServer
from certification.phase4_integrated_v2.evidence import EvidenceStore
from .service import HistoryModelService

ROOT = Path(__file__).resolve().parents[3]  # one directory deeper than the source


def expected_artifact(root=ROOT):
    from .runtime import expected_artifact as pinned
    return pinned(root)  # the reviewed tree digest of the dataset-backed model snapshot (runtime.json)


def pinned_model_factory(retain, deadline, _fault='none', *, evidence_root, server_log):
    """Live only: verify the pinned model snapshot and start the verified-runtime vLLM server (its own process group,
    TCP readiness, prefix caching disabled and confirmed in its log) in this model interpreter."""
    if time.monotonic() >= deadline:
        raise TimeoutError('model startup admission closed')
    from certification.direct_publisher_smoke_v1.host import verify_model
    from certification.direct_publisher_smoke_v1.server import ModelServer, argv_for
    from certification.phase4_integrated_v2.model_transport import OpenAICompatibleCompletionClient
    from .runtime import load, verify_cache_disabled
    runtime = load(ROOT)
    for package, expected in runtime['model_host_packages'].items():
        if importlib.metadata.version(package) != expected:
            raise ValueError('pinned model package drift: ' + package)
    store = EvidenceStore(evidence_root, 'worker')
    startup = min(deadline, time.monotonic() + runtime['lifecycle']['startup_ceiling_seconds'])

    def within():
        if time.monotonic() >= startup:
            raise TimeoutError('model verification deadline')
    artifact = verify_model(runtime['model'], within)  # the complete tree digest before any model load
    store.save('model-artifact.json', artifact)
    if {'tree_sha256': artifact['tree_sha256']} != expected_artifact(ROOT):
        raise ValueError('verified model artifact differs from the reviewed snapshot')
    cfg = runtime['server']
    server = ModelServer(argv_for(cfg, sys.executable, artifact['mounted_path'], cfg['port']), cfg['env'], server_log,
                         cfg['host'], cfg['port'])
    owner = ServerOwner(server, cfg, store, server_log, evidence_root)
    try:
        server.start()
        store.save('model-server.json', {'pgid': server.pgid, 'pid': server.process.pid, 'argv': server.argv})
        server.wait_ready(startup)
        store.save('model-server-config.json', {'prefix_caching': verify_cache_disabled(server_log),
                                                'argv': server.argv, 'readiness': cfg['readiness']})
        client = OpenAICompatibleCompletionClient(f"http://{cfg['host']}:{cfg['port']}",
                                                  timeout_seconds=cfg['request_timeout_seconds'])
        service = HistoryModelService(artifact['mounted_path'], client.complete, retain_canary=retain)
        service.artifact = expected_artifact(ROOT)
        return service, owner
    except BaseException:
        owner.close()
        raise


class ServerOwner:
    """Stops the server's own process group (SIGTERM, then SIGKILL, verified absent) and retains its log tail."""

    def __init__(self, server, cfg, store, log, evidence_root):
        self.server, self.cfg, self.store, self.log, self.root = server, cfg, store, Path(log), evidence_root

    def close(self):
        grace, kill = self.cfg['terminate_grace_seconds'], self.cfg['kill_grace_seconds']
        receipt = self.server.stop(time.monotonic() + grace + kill + 5, grace, kill)
        self.store.save('model-server-cleanup.json', {'receipt': receipt})
        if self.log.is_file():
            with self.log.open('rb') as stream:
                stream.seek(max(0, self.log.stat().st_size - min(self.cfg['log_retained_bytes'], 1024**2)))
                tail = stream.read().decode('utf-8', errors='replace')
            EvidenceStore(self.root, 'logs').save('model-server.json', {'tail': tail})
        if not receipt['groups_absent']:
            raise RuntimeError('model server process group not verified absent')
        return receipt


def rehearsal_factory(retain, deadline, fault='none', *, evidence_root=None, server_log=None):
    """CPU rehearsal only: scripted transport (optionally the pinned tokenizer and the pinned guided-decoding grammar);
    artifact labelled as rehearsal."""
    from .authority import rehearsal_gate
    from .fake_server import FixtureTokenizer
    from .rehearsal import rehearsal_transport
    rehearsal_gate()
    if fault == 'model_startup':
        raise TimeoutError('rehearsal model startup failure')
    transport, tokenizer = rehearsal_transport(fault)
    service = HistoryModelService('rehearsal', transport, tokenizer=tokenizer or FixtureTokenizer(),
                                  retain_canary=retain, check_versions=tokenizer is not None)
    service.artifact = {'rehearsal': 'scripted_model_not_target_evidence'}
    store = EvidenceStore(evidence_root, 'worker') if evidence_root is not None else None

    class Owner:
        def close(self):
            if store is not None:
                store.save('rehearsal-transport.json', transport.summary())
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
    status = {'scope': 'feedback_action_v1_model_host', 'status': 'starting', 'startup_seconds': None, 'error': None}
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
    bound = {'evidence_root': args.evidence, 'server_log': args.socket.parent / 'model-server.log'}
    if args.mode == 'live':
        from .authority import require
        require()  # before model import, subprocess or GPU query
        if args.fault != 'none':
            raise PermissionError('faults are rehearsal-only')
        factory = functools.partial(pinned_model_factory, **bound)
    else:
        factory = functools.partial(rehearsal_factory, **bound)
    result = serve_host(args.socket, args.evidence, args.cancel, deadline=args.deadline,
                        service_factory=factory, fault=args.fault)
    raise SystemExit(0 if result['status'] == 'stopped' else 1)


if __name__ == '__main__':
    main()
