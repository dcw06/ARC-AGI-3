"""Frozen requests and independent action validation. No game engine or dispatch API."""
import copy
import hashlib
import json
from pathlib import Path

PACKAGE = 'research/control_interface_action_selection_v1'
ARMS = ('reference', 'computed_control_metadata')
FIELD = 'computed_control_metadata'
SYSTEM = (
    'You control one ARC-AGI-3 game from a stateless observation. history_compaction explicitly reports any '
    'older transitions omitted from this prompt. Return only one compact JSON object with exactly one '
    'outer key action, containing exactly action_id and action_data. Omit intent, rationale, Markdown and '
    'reset/action 0. Choose exactly one currently legal action_id. For ACTION6, choose a display-grid location '
    'and include integer x and y in [0,63]. For actions 1,2,3,4,5,7 use empty action_data. Never return ACTION6 '
    'with empty action_data. Keep the response under 64 tokens.')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def loads(text):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key: ' + key)
            result[key] = value
        return result
    def reject(value):
        raise ValueError('non-finite JSON constant: ' + value)
    return json.loads(text, object_pairs_hook=unique, parse_constant=reject)


def legal_ids(observation):
    legal = observation['legal_actions']
    if (not isinstance(legal, list) or not legal or len(legal) != len(set(legal))
            or any(type(k) is not int or not 1 <= k <= 7 for k in legal)):
        raise ValueError('invalid retained legal actions')
    return sorted(legal)


def control_metadata(legal):
    # Exactly the v3 Track A tool field; no history-dependent additions.
    return {'computed_by': 'deterministic tool from legal_actions and the control rules, not the model; '
                           'the history is not used',
            'legal_actions_with_action_data': [
                {'action_id': k, 'action_data': 'x and y, integers 0 to 63' if k == 6 else 'empty {}'}
                for k in sorted(legal)]}


def load_cases(root):
    folder = Path(root) / PACKAGE
    lock = json.loads((folder / 'cases-lock.json').read_bytes())
    raw = (folder / 'cases.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != lock['cases_sha256']:
        raise ValueError('frozen case drift')
    cases = loads(raw)['cases']
    if (len(cases) != 30 or len({c['case_id'] for c in cases}) != 30
            or len({c['game_id'] for c in cases}) != 15):
        raise ValueError('expected 30 contexts in 15 development games')
    for case in cases:
        legal_ids(case['observation'])
        if FIELD in case['observation'] or digest(case['observation']) != case['observation_sha256']:
            raise ValueError('retained observation drift or treatment contamination')
    return cases


def schedule(cases):
    first = [(c['case_id'], arm) for i, c in enumerate(cases)
             for arm in (ARMS if i % 2 == 0 else tuple(reversed(ARMS)))]
    return [dict(id=f'E{i:03d}', case_id=case_id, arm=arm, pass_number=p)
            for i, (p, case_id, arm) in enumerate(
                [(1, c, a) for c, a in first] + [(2, c, a) for c, a in reversed(first)])]


def request_for(case, arm, served):
    if arm not in ARMS:
        raise ValueError('unknown condition')
    observation = copy.deepcopy(case['observation'])
    legal = legal_ids(observation)
    if arm == ARMS[1]:
        observation[FIELD] = control_metadata(legal)
    return {'model': served, 'messages': [{'role': 'system', 'content': SYSTEM},
             {'role': 'user', 'content': canonical({'observation': observation}).decode()}],
            'temperature': 0, 'seed': 0, 'max_tokens': 128,
            'chat_template_kwargs': {'enable_thinking': False}, 'response_format': {'type': 'json_object'}}


def validate(content, legal):
    result = {'json_object': False, 'shape': False, 'legal_id': False, 'arguments': False, 'valid': False,
              'action': None, 'error': None}
    try:
        value = loads(content)
        result['json_object'] = isinstance(value, dict)
        if (not isinstance(value, dict) or set(value) != {'action'} or not isinstance(value['action'], dict)
                or set(value['action']) != {'action_id', 'action_data'}):
            raise ValueError('expected exact action object shape')
        result['shape'] = True
        action = value['action']
        action_id, data = action['action_id'], action['action_data']
        result['legal_id'] = type(action_id) is int and action_id in legal
        result['arguments'] = isinstance(data, dict) and (
            set(data) == {'x', 'y'} and all(type(data[k]) is int and 0 <= data[k] <= 63 for k in ('x', 'y'))
            if type(action_id) is int and action_id == 6 else type(action_id) is int and
            action_id in (1, 2, 3, 4, 5, 7) and data == {})
        result['valid'] = result['legal_id'] and result['arguments']
        if result['valid']:
            result['action'] = action
        else:
            result['error'] = 'illegal action id or invalid arguments'
    except (ValueError, TypeError) as exc:
        result['error'] = str(exc)
    return result


def score(cases, records, served):
    """Recompute from raw responses, never trust runner validity labels. Missing/duplicate/drift is incomplete."""
    plan = schedule(cases)
    by_case = {c['case_id']: c for c in cases}
    if len(records) != len(plan):
        raise ValueError('incomplete comparison: expected exactly 120 responses')
    checked = {}
    for expected, row in zip(plan, records):
        if any(row.get(k) != v for k, v in expected.items()):
            raise ValueError('response schedule mismatch')
        case = by_case[row['case_id']]
        if row.get('request_sha256') != digest(request_for(case, row['arm'], served)):
            raise ValueError('request drift')
        raw = row.get('response')
        if not isinstance(raw, str) or hashlib.sha256(raw.encode()).hexdigest() != row.get('response_sha256'):
            raise ValueError('response drift')
        if row.get('http_status') != 200:
            raise ValueError('non-successful HTTP response in scored records')
        content, usage = completion(raw, served)
        checked[(row['case_id'], row['arm'], row['pass_number'])] = validate(content, legal_ids(case['observation']))
    summary = {'complete': True, 'research_responses': len(records), 'game_actions': 0,
               'contexts': len(cases), 'games': len({c['game_id'] for c in cases}),
               'decision': 'development_diagnostic_only_no_policy_promotion', 'arms': {},
               'paired_contexts': {'improved': 0, 'regressed': 0, 'both_valid': 0, 'neither_valid': 0},
               'action_switches_by_pass': {'1': 0, '2': 0}, 'by_game': {}}
    for arm in ARMS:
        rows = [v for (c, a, p), v in checked.items() if a == arm]
        both = sum(all(checked[(c['case_id'], arm, p)]['valid'] for p in (1, 2)) for c in cases)
        summary['arms'][arm] = {'valid_both_passes': both, 'valid_both_passes_fraction': both / len(cases),
            'components_per_response': {k: sum(r[k] for r in rows)
                                        for k in ('json_object', 'shape', 'legal_id', 'arguments', 'valid')},
            'exact_repeatability': sum(checked[(c['case_id'], arm, 1)]['valid'] and
                checked[(c['case_id'], arm, 2)]['valid'] and
                checked[(c['case_id'], arm, 1)]['action'] == checked[(c['case_id'], arm, 2)]['action'] for c in cases)}
    for case in cases:
        key = case['case_id']
        valid = [all(checked[(key, a, p)]['valid'] for p in (1, 2)) for a in ARMS]
        label = ('both_valid' if all(valid) else 'improved' if valid[1] else 'regressed' if valid[0] else 'neither_valid')
        summary['paired_contexts'][label] += 1
        game = summary['by_game'].setdefault(case['game_id'], {k: 0 for k in summary['paired_contexts']})
        game[label] += 1
        for p in (1, 2):
            a, b = (checked[(key, arm, p)] for arm in ARMS)
            summary['action_switches_by_pass'][str(p)] += int(a['valid'] and b['valid'] and a['action'] != b['action'])
    return summary


def completion(raw, served=None):
    value = loads(raw)
    if served is not None and (not isinstance(value, dict) or value.get('model') != served):
        raise ValueError('unexpected served model')
    choices = value.get('choices') if isinstance(value, dict) else None
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise ValueError('malformed server completion')
    choice = choices[0]
    if choice.get('finish_reason') != 'stop':
        raise ValueError('completion truncated or unfinished')
    content = choice.get('message', {}).get('content')
    usage = value.get('usage')
    if (not isinstance(content, str) or not isinstance(usage, dict)
            or any(type(usage.get(k)) is not int or usage[k] < 0 for k in ('prompt_tokens', 'completion_tokens'))
            or usage['completion_tokens'] > 128 or usage['prompt_tokens'] > 60000):
        raise ValueError('invalid content, usage or context budget')
    return content, usage


def run_cases(root, client, evidence, clock):
    protocol = json.loads((Path(root) / PACKAGE / 'protocol.json').read_bytes())
    original = clock.limits
    phase_cutoff = min(original['admission_cutoff_seconds'], clock.elapsed() + protocol['experiment']['research_seconds'])
    clock.limits = {**original, 'admission_cutoff_seconds': phase_cutoff}
    evidence.json('action-selection/phase-budget.json', {'began_at_seconds': clock.elapsed(),
        'admission_cutoff_seconds': phase_cutoff, 'research_ceiling_seconds': protocol['experiment']['research_seconds']})
    try:
        return _run_cases(root, client, evidence, clock)
    finally:
        clock.limits = original


def _run_cases(root, client, evidence, clock):
    cases = load_cases(root)
    plan = schedule(cases)
    by_case = {c['case_id']: c for c in cases}
    audit = json.loads((Path(root) / PACKAGE / 'token-audit.json').read_bytes())
    prompt_tokens = {(r['case_id'], r['arm']): r['prompt_tokens'] for r in audit['requests']}
    records = []
    for item in plan:
        if not clock.admission_open():
            raise TimeoutError('action selection phase deadline before request')
        clock.check('action selection before request')
        body = request_for(by_case[item['case_id']], item['arm'], client.served)
        row = {**item, 'request_sha256': digest(body), 'status': 'intent'}
        evidence.json(f"action-selection/answers/{item['id']}.json", row)
        status, raw = client.call(item['id'], body)
        row.update(http_status=status, response=raw.decode('utf-8'), response_sha256=hashlib.sha256(raw).hexdigest(),
                   status='received')
        evidence.json(f"action-selection/answers/{item['id']}.json", row)
        clock.check('action selection after response')
        if not clock.admission_open():
            raise TimeoutError('action selection phase deadline after response')
        if status != 200:
            raise ValueError(f"{item['id']}: HTTP {status}")
        content, usage = completion(row['response'], client.served)
        if evidence.mode == 'live' and usage['prompt_tokens'] != prompt_tokens[(item['case_id'], item['arm'])]:
            raise ValueError('server prompt-token count differs from the frozen offline audit')
        row.update(usage=usage, validation=validate(content, legal_ids(by_case[item['case_id']]['observation'])),
                   status='scored')
        evidence.json(f"action-selection/answers/{item['id']}.json", row)
        records.append(row)
    summary = score(cases, records, client.served)
    evidence.json('action-selection/summary.json', summary)
    clock.check('action selection scoring and evidence retention')
    if not clock.admission_open():
        raise TimeoutError('action selection phase deadline after scoring and evidence retention')
    return summary
