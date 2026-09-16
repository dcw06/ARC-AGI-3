"""110 independent development lifecycles, one bounded shared inference queue.

Gated real model backend; separate approval required before startup.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import hashlib
import logging
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from certification.phase4_v1.lifecycle import IsolatedInference, validate_freeze
from certification.phase4_v3.lifecycle import run_client
from certification.phase4_v4.service import SharedModelService
from certification.phase4_v4.authority import authority
from certification.phase4_v2.supervisor import save
from agent.e1_policy import E1Policy, E1ModelBinding
from agent.feature_manifest import load_e1_feature_manifests
from agent.framework_adapter import LocalFrameworkAdapter
from agent.scheduler import QueuedInferenceExecutor
from agent.watchdog import DeadlineWatchdog


class AuditedAdapter:
    def __init__(self, adapter):
        self.adapter = adapter
        self.audit = []

    def __getattr__(self, name):
        return getattr(self.adapter, name)

    def dispatch(self, client, decision):
        entry = {'action_id': decision.action_id, 'action_data': dict(decision.action_data),
                 'legal_actions': list(client.observation.available_actions),
                 'decision_id': decision.decision_id, 'outcome': 'entered',
                 'pre_state': client.observation.state.value}
        self.audit.append(entry)
        try:
            result = self.adapter.dispatch(client, decision)
            entry['outcome'] = 'acknowledged'
            entry['post_state'] = result.state.value
            entry['post_hash'] = result.canonical_hash
            return result
        except Exception as exc:
            entry['outcome'] = type(exc).__name__
            entry['cause'] = str(exc.__cause__) if exc.__cause__ else str(exc)
            raise


def run_workload(rows, adapter_factory, completion_factory, checkpoint, cancel_path,
                 *, seconds=27540, reserve=600, model_service=None, started=None):
    """Injectable service seam; 110 simultaneous client workers, eight inference workers."""
    _, frozen = validate_freeze()
    if rows != frozen:
        raise ValueError('exact 110-client workload required')
    manifests = load_e1_feature_manifests(ROOT / 'config/e1_feature_manifests.yaml')
    binding = E1ModelBinding.from_mapping(json.loads(
        (ROOT / 'config/operational_primary.yaml').read_text())['primary']['model_binding'])
    watchdog = DeadlineWatchdog(seconds, reserve, started_monotonic=time.monotonic() if started is None else started)
    stop = threading.Event()
    state = {'schema_version': 1, 'status': 'running', 'error': None, 'clients': [],
             'model_inference': bool(model_service and model_service.started),
             'model_artifact': model_service.artifact if model_service else None,
             'canary_audit': model_service.canary_audit if model_service else None,
             'model_startup_seconds': model_service.startup_seconds if model_service else None,
             'scope': 'model_development_integration',
             'requests': [], 'prompt_samples': [], 'prompt_sample_bytes': 0,
             'prompt_samples_omitted': 0, 'maximum_client_workers': 110}
    mutex = threading.Lock()

    def poll_cancel():
        while not stop.wait(.02):
            if cancel_path.exists() or watchdog.stop_admission:
                watchdog.cancel()
                return

    watcher = threading.Thread(target=poll_cancel, daemon=True)
    watcher.start()
    save(checkpoint, state)
    try:
        with QueuedInferenceExecutor(maxsize=110, worker_count=8, max_age_seconds=300) as executor:
            def client(row):
                completion = completion_factory(row, watchdog)
                class MeasuredCompletion:
                    def complete(self, request):
                        begin = time.monotonic()
                        payload = json.dumps(request, sort_keys=True).encode()
                        error = None
                        try:
                            result = completion.complete(request)
                            return result
                        except Exception as exc:
                            error = type(exc).__name__
                            raise
                        finally:
                            # Real trajectory prompt retained; no synthetic fixture replacement.
                            with mutex:
                                state['requests'].append({'client_id': row['client_id'],
                                    'request_sha256': hashlib.sha256(payload).hexdigest(),
                                    'request_bytes': len(payload), 'error': error,
                                    'service_seconds': time.monotonic() - begin})
                                if (len(state['prompt_samples']) < 64 and
                                        state['prompt_sample_bytes'] + len(payload) <= 16 * 1024**2):
                                    state['prompt_samples'].append({'client_id': row['client_id'], 'request': request})
                                    state['prompt_sample_bytes'] += len(payload)
                                else:
                                    state['prompt_samples_omitted'] += 1
                adapter = AuditedAdapter(adapter_factory(row))
                def factory(_):
                    return E1Policy(manifest=manifests['E1S-R'], binding=binding,
                        client=MeasuredCompletion(), inference=IsolatedInference(executor, row['client_id']),
                        seed=row['request_seed'])
                record = run_client(row, adapter, factory, watchdog)
                record['dispatch_audit'] = adapter.audit
                return record
            with ThreadPoolExecutor(max_workers=110) as pool:
                futures = {pool.submit(client, row): row for row in rows}
                for future in as_completed(futures):
                    row = futures[future]
                    try:
                        record = future.result()
                    except Exception as exc:
                        record = {'client_id': row['client_id'], 'error': type(exc).__name__ + ': ' + str(exc)}
                    with mutex:
                        state['clients'].append(record)
                        save(checkpoint, state)
            state['queue'] = {'max_size': executor.queue.max_observed_size,
                              'max_age_seconds': executor.queue.max_observed_age}
        state['status'] = 'complete'
    except Exception as exc:
        state['error'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        stop.set()
        watcher.join(timeout=1)
        state['model_token_audit'] = list(model_service.audit_records) if model_service else []
        save(checkpoint, state)
    return state


if __name__ == '__main__':
    authority()
    from arc_agi import Arcade, OperationMode
    from certification.phase4_v2.package import verify_environment_mount
    scratch, environments = map(Path, sys.argv[1:3])
    started = float(sys.argv[3])
    save(scratch / 'state.json', {'status': 'starting', 'model_inference': False})
    try:
        verify_environment_mount(environments, json.loads((ROOT / 'reports/phase4_v2_offline_package.json').read_text()))
        _, rows = validate_freeze()
        service = SharedModelService(scratch)
        service.start()
        (scratch / 'model-ready').touch(exist_ok=False)
        logger = logging.getLogger('p4-model-development')
        logger.addHandler(logging.NullHandler()); logger.propagate = False
        def adapter(row):
            arcade = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=str(environments),
                recordings_dir=str(scratch / row['client_id']), logger=logger)
            return LocalFrameworkAdapter(arcade, seed_by_game={row['game_id']: row['environment_seed']})
        result = run_workload(rows, adapter, lambda row, watchdog: service,
            scratch / 'state.json', scratch / 'cancel', model_service=service, started=started)
        raise SystemExit(0 if result['status'] == 'complete' else 1)
    except Exception as exc:
        save(scratch / 'state.json', {'status': 'failed', 'error': type(exc).__name__ + ': ' + str(exc)})
        raise
