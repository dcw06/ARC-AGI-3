"""Require independent cleanup and explicit derived-policy identity."""
from certification.phase4_v13.evaluate import evaluate as evaluate_v13

CONTRACT = 'arc_action_v12'
PARENT = 'E1S-R'


def evaluate(report, rows):
    result = evaluate_v13(report, rows)
    errors = result['errors']
    if report.get('independent_gpu_cleanup_verified') is not True:
        errors.append('independent GPU cleanup evidence required')
    worker = report.get('worker') or {}
    if worker.get('action_output_contract') != CONTRACT or worker.get('policy_parent') != PARENT:
        errors.append('worker derived-policy contract/parent mismatch')
    for client in worker.get('clients', []):
        if client.get('action_output_contract') != CONTRACT or client.get('parent') != PARENT:
            errors.append(f"{client.get('client_id')}: derived-policy contract/parent mismatch")
    result['passed'] = not errors
    result['development_model_lifecycle_passed'] = not errors
    if errors:
        result['capacity_candidate'] = None
    result['C_admit'] = None
    return result
