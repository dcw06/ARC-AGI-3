"""Development lifecycle preparation; no GPU launch or compute authority.

Each row owns an adapter/scorecard. The frozen E1 policy is unchanged; only
queue isolation keys and lifecycle admission are enforced by this wrapper.
"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time

from agent.competition_loop import CompetitionAgentLoop
from agent.e1_policy import E1Policy, E1ModelBinding
from agent.feature_manifest import load_e1_feature_manifests
from agent.framework_adapter import PreDispatchFailure, FinalizationUnknown

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_freeze(root=ROOT):
    folder = root / 'certification/phase4_v1'
    lock = json.loads((folder / 'lock.json').read_text())
    expected = {'contract.json', 'workload.json', 'budget.json', 'lifecycle.py',
                'local_probe.py'}
    required = {f'certification/phase4_v1/{name}' for name in expected}
    required.update({'config/operational_primary.yaml', 'config/e1_feature_manifests.yaml',
                     'config/e1_experiment_protocol.yaml', 'config/m0_launch_spec_q3vl30.json'})
    required.update(f'agent/{name}' for name in ('e1_policy.py', 'scheduler.py',
        'competition_loop.py', 'framework_adapter.py', 'watchdog.py', 'action.py',
        'action_journal.py', 'controller.py', 'state.py', 'representation.py',
        'feature_manifest.py', 'safe_operations.py'))
    if set(lock.get('bindings', {})) != required:
        raise ValueError('incomplete lifecycle bindings')
    for name, value in lock['bindings'].items():
        if digest(root / name) != value:
            raise ValueError('lifecycle source drift: ' + name)
    contract = json.loads((folder / 'contract.json').read_text())
    rows = json.loads((folder / 'workload.json').read_text())
    pairs = json.loads((root / 'config/e1_experiment_protocol.yaml').read_text())['development_game_seed_pairs']
    expected_rows = [{'client_id': f'p4-client-{i:03d}',
                      'game_id': pairs[i % len(pairs)]['game_id'],
                      'environment_seed': pairs[i % len(pairs)]['seed'],
                      'request_seed': 0, 'max_actions': 80} for i in range(110)]
    if rows != expected_rows or contract['parent'] != 'E1S-R':
        raise ValueError('frozen workload mismatch')
    return contract, rows


class IsolatedInference:
    """Opaque per-client queue key; never mutate the policy-visible observation."""
    def __init__(self, executor, client_id):
        self.executor, self.client_id = executor, client_id

    def execute(self, **kwargs):
        kwargs['client_id'] = self.client_id
        return self.executor.execute(**kwargs)

    def cancel(self):
        self.executor.cancel_client(self.client_id)


class DispatchGuard:
    def __init__(self, adapter, watchdog):
        self.adapter, self.watchdog = adapter, watchdog
        self.blocked_after_cancellation = 0

    def dispatch(self, client, decision):
        # The policy may have blocked since the loop's admission check.
        if self.watchdog.stop_admission:
            self.blocked_after_cancellation += 1
            raise PreDispatchFailure('deadline/cancellation denies late dispatch')
        return self.adapter.dispatch(client, decision)

    def finalize_client(self, client):
        return self.adapter.finalize_client(client)


def journal_record(journal):
    return [{'transaction_id': e.transaction_id, 'kind': str(e.kind),
             'status': str(e.status), 'sequence': e.sequence,
             'prepared_fields': dict(e.prepared_fields), 'fields': dict(e.fields)}
            for e in journal.snapshot()]


def run_client(row, adapter, policy_factory, watchdog):
    """Always attempt scorecard finalization after successful open, even on error.

    This synchronous unit must run under a bounded external supervisor before
    target deployment: it cannot kill a hung environment or model process.
    """
    _, inventory = validate_freeze()
    matching = [r for r in inventory if r['client_id'] == row['client_id']]
    if (not matching or {**row, 'max_actions': 80} != matching[0]
            or type(row['max_actions']) is not int or not 1 <= row['max_actions'] <= 80):
        raise ValueError('client outside development-only frozen workload')
    started = time.monotonic()
    client = None
    guard = DispatchGuard(adapter, watchdog)
    record = {'client_id': row['client_id'], 'game_id': row['game_id'],
              'environment_seed': row['environment_seed'], 'request_seed': row['request_seed'],
              'max_actions': row['max_actions'], 'parent': 'E1S-R',
              'error': None, 'result': None, 'scorecard_id': None,
              'scorecard_receipt': None, 'finalization_status': 'not_opened'}
    try:
        if watchdog.stop_admission:
            raise PreDispatchFailure('admission closed before scorecard open')
        record['scorecard_id'] = adapter.open_scorecard(tags=['p4-development-lifecycle'])
        if not record['scorecard_id'] or record['scorecard_id'] == 'None':
            raise ValueError('missing scorecard identity')
        client = adapter.bootstrap(row['game_id'])
        if client.game_id != row['game_id']:
            raise ValueError('wrong environment')
        policy = policy_factory(client)
        if not isinstance(policy, E1Policy) or policy.manifest.treatment_id != 'E1S-R':
            raise TypeError('exact E1S-R policy required; no silent E0 replacement')
        primary = json.loads((ROOT / 'config/operational_primary.yaml').read_text())['primary']
        expected_manifest = load_e1_feature_manifests(ROOT / 'config/e1_feature_manifests.yaml')['E1S-R']
        if (policy.manifest != expected_manifest
                or policy.binding != E1ModelBinding.from_mapping(primary['model_binding'])
                or not isinstance(policy.inference, IsolatedInference)
                or policy.inference.client_id != row['client_id']):
            raise ValueError('policy binding or queue isolation drift')
        if policy.seed != row['request_seed'] or policy.max_new_tokens != 128:
            raise ValueError('policy request configuration drift')
        record['result'] = asdict(CompetitionAgentLoop(
            guard, client, policy=policy, max_actions=row['max_actions'],
            watchdog=watchdog).run())
    except Exception as exc:
        record['error'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        if client is not None and not client.closed:
            try:
                adapter.finalize_client(client)
            except Exception as exc:
                record['error'] = record['error'] or 'client_finalize: ' + type(exc).__name__
        if record['scorecard_id']:
            closing = time.monotonic()
            try:
                receipt = adapter.close_scorecard()
                if (not isinstance(receipt, dict)
                        or receipt.get('card_id') != record['scorecard_id']):
                    raise FinalizationUnknown('empty scorecard receipt')
                record['scorecard_receipt'] = receipt
                record['finalization_status'] = 'acknowledged_local_framework'
            except Exception as exc:
                record['finalization_status'] = 'unknown'
                record['error'] = record['error'] or 'scorecard_finalize: ' + type(exc).__name__
            record['finalization_seconds'] = time.monotonic() - closing
        record['lifecycle_journal'] = journal_record(adapter.lifecycle_journal)
        record['client_journal'] = journal_record(client.journal) if client is not None else []
        record['client_closed'] = bool(client is not None and client.closed)
        record['blocked_after_cancellation'] = guard.blocked_after_cancellation
        record['elapsed_seconds'] = time.monotonic() - started
    return record


def evaluate_local_record(record, *, expected_fault='none'):
    """Evidence checks for CPU exercises only, never a model/GPU certificate."""
    errors = []
    entries = record['lifecycle_journal']
    for kind in ('scorecard_open', 'scorecard_close'):
        matching = [e for e in entries if e['kind'] == kind]
        if len(matching) != 1 or matching[0]['status'] != 'acknowledged':
            errors.append(kind)
    if (record['finalization_status'] != 'acknowledged_local_framework'
            or not isinstance(record['scorecard_receipt'], dict)
            or record['scorecard_receipt'].get('card_id') != record['scorecard_id']):
        errors.append('finalization')
    if record['error'] or not record['client_closed'] or not record['result']:
        errors.append('client_failure')
    result = record['result'] or {}
    actions = [e for e in record['client_journal'] if e['kind'] == 'action']
    if any(e['status'] != 'acknowledged' for e in actions):
        errors.append('unresolved_dispatch')
    if len(actions) != result.get('acknowledged_actions') or len(actions) > record['max_actions']:
        errors.append('action_accounting')
    if result.get('ambiguous_actions') != 0:
        errors.append('ambiguous_action')
    if expected_fault == 'cancel':
        if actions or record['blocked_after_cancellation'] != 1:
            errors.append('late_dispatch')
    else:
        if not actions or result.get('terminal_reason') not in ('win', 'action_cap'):
            errors.append('missing_nominal_dispatch')
        if expected_fault == 'policy_error' and result.get('policy_failures') != record['max_actions']:
            errors.append('fallback_not_exercised')
        if expected_fault == 'none' and result.get('policy_failures') != 0:
            errors.append('unexpected_fallback')
    return {'passed': not errors, 'failures': errors,
            'scope': 'local_actual_environment_scripted_completion_only',
            'model_inference': False, 'target_gpu_certified': False, 'phase4_complete': False}
