"""v3 client finalization, preserving v1 policy/workload bindings."""
from dataclasses import asdict
import json
import time
from agent.e1_policy import E1Policy, E1ModelBinding
from agent.feature_manifest import load_e1_feature_manifests
from agent.framework_adapter import PreDispatchFailure, FinalizationUnknown
from certification.phase4_v1.lifecycle import (ROOT, validate_freeze, DispatchGuard,
    IsolatedInference, journal_record)
from certification.phase4_v3.terminal import TerminalAwareLoop


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
        record['result'] = asdict(TerminalAwareLoop(
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
        record['terminal_observation'] = ({'state': client.observation.state.value,
            'hash': client.observation.canonical_hash, 'rendered_frames': len(client.observation.frames)}
            if client is not None else None)
        record['client_closed'] = bool(client is not None and client.closed)
        record['blocked_after_cancellation'] = guard.blocked_after_cancellation
        record['elapsed_seconds'] = time.monotonic() - started
    return record
