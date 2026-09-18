"""v6 measured development lifecycles, one bounded shared inference queue.

Gated real model backend; separate approval required before startup.
"""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
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
from certification.phase4_v13.measurement import RequestTimeline, MeasuredInference, save_bounded


def save(path, value):
    return save_bounded(path, value, byte_limit=64 * 1024**2)
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
                 *, seconds=27540, reserve=600, model_service=None, started=None,
                 evidence_store=None):
    """Injectable service seam; 110 simultaneous client workers, eight inference workers."""
    _, frozen = validate_freeze()
    if rows != frozen:
        raise ValueError('exact 110-client workload required')
    def retain():
        # Appended request/client/sample records are no longer mutated. Copy
        # their containers under the lock, then encode and fsync outside it so
        # checkpoint I/O cannot hold up inference completion callbacks.
        with mutex:
            snapshot = {key: list(value) if isinstance(value, list) else value
                        for key, value in state.items()}
            snapshot['request_timeline'] = timeline.snapshot()
        if evidence_store is None:
            save(checkpoint, snapshot)
        else:
            evidence_store.save('state.json', snapshot)
    manifests = load_e1_feature_manifests(ROOT / 'config/e1_feature_manifests.yaml')
    binding = E1ModelBinding.from_mapping(json.loads(
        (ROOT / 'config/operational_primary.yaml').read_text())['primary']['model_binding'])
    watchdog = DeadlineWatchdog(seconds, reserve, started_monotonic=time.monotonic() if started is None else started)
    origin = time.monotonic() if started is None else started
    timeline = RequestTimeline(origin)
    stop = threading.Event()
    state = {'schema_version': 1, 'status': 'running', 'error': None, 'clients': [],
             'action_output_contract':'arc_action_v12',
             'policy_parent':'E1S-R',
             'model_inference': bool(model_service and model_service.started),
             'model_artifact': model_service.artifact if model_service else None,
             'canary_audit': model_service.canary_audit if model_service else None,
             'model_startup_seconds': model_service.startup_seconds if model_service else None,
             'scope': 'model_development_integration',
             'requests': [], 'prompt_samples': [], 'prompt_sample_bytes': 0,
             'prompt_samples_omitted': 0, 'maximum_client_workers': 110,
             'workload_started_seconds': timeline.now(), 'workload_ended_seconds': None,
             'request_timeline': []}
    mutex = threading.Lock()

    def poll_cancel():
        while not stop.wait(.02):
            if cancel_path.exists() or watchdog.stop_admission:
                watchdog.cancel()
                return

    watcher = threading.Thread(target=poll_cancel, daemon=True)
    watcher.start()
    retain()
    try:
        with QueuedInferenceExecutor(maxsize=110, worker_count=8, max_age_seconds=300) as executor:
            def client(row):
                completion = completion_factory(row, watchdog)
                from certification.phase4_v13.policy_evidence import PolicyEvidence
                from certification.phase4_v13.contract_policy import ContractPolicy
                diagnostics=PolicyEvidence(row['client_id'])
                class MeasuredCompletion:
                    def complete(self, request):
                        begin = time.monotonic()
                        payload = json.dumps(request, sort_keys=True).encode()
                        error = None
                        try:
                            result = completion.complete(request)
                            diagnostics.received(request,result,timeline.current_id())
                            return result
                        except Exception as exc:
                            error = type(exc).__name__
                            raise
                        finally:
                            # Real trajectory prompt retained; no synthetic fixture replacement.
                            with mutex:
                                state['requests'].append({'client_id': row['client_id'],
                                    'request_id': timeline.current_id(),
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
                    return ContractPolicy(evidence=diagnostics,manifest=manifests['E1S-R'], binding=binding,
                        client=MeasuredCompletion(), inference=MeasuredInference(executor, row['client_id'], timeline),
                        seed=row['request_seed'])
                record = run_client(row, adapter, factory, watchdog)
                record['dispatch_audit'] = adapter.audit
                record['policy_diagnostics']=diagnostics.summary()
                record['action_output_contract']='arc_action_v12'
                return record
            with ThreadPoolExecutor(max_workers=110) as pool:
                futures = {pool.submit(client, row): row for row in rows}
                pending = set(futures)
                while pending:
                    # A checkpoint can take long enough for several clients to
                    # finish. Drain all ready records into the next checkpoint,
                    # instead of rewriting the entire history for each one.
                    done, pending = wait(pending, return_when=FIRST_COMPLETED)
                    for future in done:
                        row = futures[future]
                        try:
                            record = future.result()
                        except Exception as exc:
                            record = {'client_id': row['client_id'], 'error': type(exc).__name__ + ': ' + str(exc)}
                        with mutex:
                            state['clients'].append(record)
                    retain()
            state['workload_ended_seconds'] = timeline.now()
            state['queue'] = {'max_size': executor.queue.max_observed_size,
                              'max_age_seconds': executor.queue.max_observed_age}
        if any(worker.is_alive() for worker in executor._workers):
            raise RuntimeError('inference workers still active; final evidence unstable')
        state['status'] = 'complete'
    except Exception as exc:
        state['error'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        stop.set()
        watcher.join(timeout=1)
        state['request_timeline'] = timeline.snapshot()
        state['model_token_audit'] = list(model_service.audit_records) if model_service else []
        retain()
    return state


if __name__ == '__main__':
    raise PermissionError('v6 measurement integration is local-only; outer watchdog and target review pending')
