# Derived by scripts/build_control_interface_action_selection_v2.py; edit the derivation.
"""Research-specific preconditions layered over the unchanged smoke lifecycle."""
import hashlib
import json
from pathlib import Path
import re
from . import probe as P


def validate_protocol(root, protocol):
    cases = P.load_cases(root)
    experiment = protocol['experiment']
    if (experiment.get('schedule') != P.schedule(cases) or experiment.get('arms') != list(P.ARMS)
            or experiment.get('cases_sha256') != hashlib.sha256((Path(root) / P.CASE_PACKAGE / 'cases.json').read_bytes()).hexdigest()
            or experiment.get('system_sha256') != hashlib.sha256(P.SYSTEM.encode()).hexdigest()
            or experiment.get('prefix_caching') is not False or experiment.get('research_requests') != 120
            or experiment.get('max_tokens') != 128 or experiment.get('prompt_token_ceiling') != 60000
            or protocol['limits'].get('environment_actions') != 0 or protocol['limits'].get('scorecards') != 0):
        raise ValueError('frozen experiment configuration drift')
    if experiment.get('research_seconds') != 1500:
        raise ValueError('research phase ceiling drift')
    audit = json.loads((Path(root) / P.PACKAGE / 'token-audit.json').read_bytes())
    rows = audit['requests']
    expected_tokens = [(c['case_id'], arm, P.digest(P.request_for(c, arm, protocol['server']['served_model_name'])))
                       for c in cases for arm in P.ARMS]
    if (audit.get('passed') is not True or audit.get('cases_sha256') != experiment['cases_sha256']
            or [(r['case_id'], r['arm'], r['request_sha256']) for r in rows] != expected_tokens
            or any(type(r.get('prompt_tokens')) is not int or not 0 < r['prompt_tokens'] <= 60000 for r in rows)):
        raise ValueError('token audit missing, incomplete or not bound to actual requests')
    if experiment.get('shared_output_contract_sha256') != P.digest(P.OUTPUT_CONTRACT):
        raise ValueError('shared output contract drift')
    argv = protocol['server']['argv']
    if argv.count('--no-enable-prefix-caching') != 1 or '--enable-prefix-caching' in argv:
        raise ValueError('prefix caching must be explicitly disabled')
    requests = protocol['requests']
    if len({r['id'] for r in requests}) != len(requests) or sum(r.get('max_issues', 1) for r in requests) != 131:
        raise ValueError('frozen counted request cap drift')
    research = [r for r in requests if r['kind'] == 'action_selection']
    expected = [{'id': r['id'], 'kind': 'action_selection', 'method': 'POST', 'path': '/v1/chat/completions',
                 'timeout_seconds': 60} for r in P.schedule(cases)]
    if research != expected:
        raise ValueError('research request plan drift')


def verify_cache_disabled(log):
    with Path(log).open('rb') as stream:
        stream.seek(max(0, Path(log).stat().st_size - 2097152))
        text = stream.read().decode('utf-8', errors='replace')
    values = re.findall(r"enable_prefix_caching(?:['\"])?\s*[:=]\s*(True|False)", text)
    if not values or any(value != 'False' for value in values):
        raise ValueError('server log does not confirm prefix caching disabled')
    return {'disabled': True, 'confirmation': 'all retained startup configuration entries say enable_prefix_caching=False',
            'matches': len(values)}
