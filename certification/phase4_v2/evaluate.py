"""Independent evidence checks; does not trust worker success flags."""
from collections import Counter
import math


def evaluate(report, rows):
    errors = []
    worker = report.get('worker')
    if not isinstance(worker, dict):
        return {'passed': False, 'errors': ['missing worker'], 'phase4_complete': False}
    if report.get('error') or worker.get('error') or report.get('status') != 'worker_completed_pending_independent_evaluation':
        errors.append('supervisor/worker failure')
    if report.get('cleanup_verified') is not True or report.get('scratch_removed') is not True:
        errors.append('cleanup not verified')
    for key, limit in [('elapsed_seconds', 60), ('peak_rss_bytes', 4 * 1024**3),
                       ('peak_scratch_bytes', 64 * 1024**2), ('final_scratch_bytes', 64 * 1024**2),
                       ('cleanup_seconds', 6)]:
        value = report.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value < limit:
            errors.append('resource limit/evidence: ' + key)
    clients = worker.get('clients', [])
    expected = {r['client_id']: r for r in rows}
    if len(rows) != 110 or len(expected) != 110:
        errors.append('expected inventory is not 110 unique clients')
    if Counter(c.get('client_id') for c in clients) != Counter(expected.keys()):
        errors.append('missing/duplicate/extra client')
    for c in clients:
        cid = c.get('client_id')
        row = expected.get(cid)
        if row is None:
            continue
        if any(c.get(k) != row[k] for k in ('game_id', 'environment_seed', 'request_seed', 'max_actions')):
            errors.append(f'{cid}: workload drift')
        result = c.get('result') or {}
        if c.get('error') or c.get('client_closed') is not True:
            errors.append(f'{cid}: client failure')
        receipt = c.get('scorecard_receipt') or {}
        if (not c.get('scorecard_id') or receipt.get('card_id') != c['scorecard_id']
                or c.get('finalization_status') != 'acknowledged_local_framework'):
            errors.append(f'{cid}: missing/mismatched receipt')
        life = c.get('lifecycle_journal', [])
        if Counter(e.get('kind') for e in life) != Counter(['scorecard_open', 'scorecard_close']):
            errors.append(f'{cid}: lifecycle inventory')
        if any(e.get('status') != 'acknowledged' for e in life):
            errors.append(f'{cid}: lifecycle unresolved')
        entries = c.get('client_journal', [])
        bootstrap = [e for e in entries if e.get('kind') == 'bootstrap_reset']
        actions = [e for e in entries if e.get('kind') == 'action']
        audit = c.get('dispatch_audit', [])
        if len(audit) != len(actions):
            errors.append(f'{cid}: missing dispatch audit')
        for index, entry in enumerate(audit):
            action = entry.get('action_id')
            if (type(action) is not int or action not in entry.get('legal_actions', [])
                    or entry.get('outcome') != 'acknowledged'):
                errors.append(f'{cid}: illegal/unresolved action')
            data = entry.get('action_data')
            if action == 6:
                if (not isinstance(data, dict) or set(data) != {'x', 'y'}
                        or any(type(v) is not int or not 0 <= v < 64 for v in data.values())):
                    errors.append(f'{cid}: illegal click')
            elif data != {}:
                errors.append(f'{cid}: unexpected action data')
            if index < len(actions):
                prepared = actions[index].get('prepared_fields', {})
                if prepared.get('action_id') != action or prepared.get('decision_id') != entry.get('decision_id'):
                    errors.append(f'{cid}: journal/action mismatch')
        if len(bootstrap) != 1 or any(e.get('status') != 'acknowledged' for e in entries):
            errors.append(f'{cid}: dispatch unresolved')
        ids = [e.get('transaction_id') for e in entries]
        if None in ids or len(ids) != len(set(ids)):
            errors.append(f'{cid}: duplicate transaction')
        acknowledged = sum(e.get('status') == 'acknowledged' for e in actions)
        if (type(result.get('acknowledged_actions')) is not int
                or acknowledged != result.get('acknowledged_actions')
                or len(actions) > row['max_actions']):
            errors.append(f'{cid}: action count')
        if result.get('terminal_reason') not in ('win', 'action_cap'):
            errors.append(f'{cid}: incomplete lifecycle')
        if result.get('terminal_reason') == 'action_cap' and len(actions) != row['max_actions']:
            errors.append(f'{cid}: partial action cap')
        for key in ('policy_failures', 'ambiguous_actions', 'inference_queue_failures', 'inference_transport_failures'):
            if result.get(key) != 0:
                errors.append(f'{cid}: {key}')
        if result.get('inference_requests') != result.get('inference_completions'):
            errors.append(f'{cid}: missing completions')
        calls = [r for r in worker.get('requests', []) if r.get('client_id') == cid]
        if len(calls) != result.get('inference_requests'):
            errors.append(f'{cid}: missing request accounting')
        for call in calls:
            duration = call.get('service_seconds')
            if (type(duration) not in (int, float) or not math.isfinite(duration) or duration < 0
                    or call.get('error')):
                errors.append(f'{cid}: invalid request measurement')
    queue = worker.get('queue', {})
    for key, limit in [('max_size', 110), ('max_age_seconds', 300)]:
        value = queue.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= limit:
            errors.append('queue limit/evidence')
    return {'passed': not errors, 'errors': errors,
            'scope': 'development_repeated_games_separate_scorecards_local_integration',
            'model_inference': worker.get('model_inference') is True,
            'C_nominal': None, 'C_admit': None,
            'capacity_status': 'requires_real_model_token_audit_and_trajectory_measurements',
            'target_gpu_certified': False, 'phase4_complete': False}
