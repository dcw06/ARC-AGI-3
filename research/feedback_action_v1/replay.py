"""Independent reconstruction from retained packed observations and transitions.

No runner, policy, adapter, representation builder or environment is imported. The frozen request contract is
review-bound data; transition measurements use the format verifier already used by the independent evaluator.
"""
import copy
import hashlib
import json

from research.feedback_action_v1 import evaluate as EV
from research.transition_evidence_v2 import transition as T

BOUNDARY = {'reset_acknowledged', 'level_completed', 'level_count_decreased', 'terminal_state'}


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def grid_bytes(grid):
    if (type(grid) is not list or not grid or type(grid[0]) is not list or not grid[0]
            or any(type(row) is not list or len(row) != len(grid[0]) for row in grid)
            or any(type(v) is not int or not 0 <= v <= 255 for row in grid for v in row)):
        raise ValueError('invalid lossless grid')
    return bytes(v for row in grid for v in row)


def grid_hash(grid):
    header = {'version': 'arc3-grid-v1', 'shape': [len(grid), len(grid[0])], 'dtype': 'uint8',
              'byte_order': 'not_applicable', 'order': 'C'}
    return hashlib.sha256(encode(header) + b'\0' + grid_bytes(grid)).hexdigest()


def check_observation(value):
    fields = {'game_id', 'guid', 'state', 'levels_completed', 'win_levels', 'available_actions', 'full_reset',
              'frames', 'canonical_hash'}
    if type(value) is not dict or set(value) != fields:
        raise ValueError('packed observation fields')
    if (type(value['full_reset']) is not bool or type(value['guid']) is not str or not value['guid']
            or value['state'] not in ('NOT_PLAYED', 'NOT_FINISHED', 'WIN', 'GAME_OVER')
            or type(value['levels_completed']) is not int or type(value['win_levels']) is not int
            or not 0 <= value['levels_completed'] <= value['win_levels']
            or type(value['available_actions']) is not list
            or any(type(a) is not int or not 1 <= a <= 7 for a in value['available_actions'])
            or type(value['frames']) is not list or not value['frames']):
        raise ValueError('packed observation types')
    header = {'version': 'arc3-observation-v2', 'game_id': value['game_id'], 'state': value['state'],
              'levels_completed': value['levels_completed'], 'win_levels': value['win_levels'],
              'available_actions': value['available_actions'], 'dtype': 'uint8', 'byte_order': 'not_applicable',
              'order': 'C', 'frames': [[len(g), len(g[0])] for g in value['frames']]}
    digest = hashlib.sha256(encode(header))
    for grid in value['frames']:
        digest.update(b'\0' + grid_bytes(grid))
    if value['canonical_hash'] != digest.hexdigest():
        raise ValueError('packed observation canonical hash')


def observed(value):
    return {k: value[k] for k in ('frames', 'levels_completed', 'state', 'full_reset', 'available_actions')}


def evidence_view(raws, frame, contract):
    records = T.history(raws)
    current = [] if not records or set(records[-1]['environment']['events']) & BOUNDARY else [
        r for r in records if r['segment'] == records[-1]['segment']]
    entries = []
    for r in current[-8:]:
        m, status = r['measurements'], r['dispatch']['status']
        frames = m['frames']
        final = frames[-1] if frames else None
        change = final['vs_pre']['changed_cells'] if final and final['valid'] else None
        entries.append({
            'ref': f"T{r['identity']['action_index']}", **{
                'action_id': r['action']['dispatched']['action_id'],
                'action_data': r['action']['dispatched']['action_data']},
            'dispatch': status, 'from_state': 'S-' + r['observations']['before_frames_sha256'][-1][:12],
            'returned_frames': m['returned_frame_count'].get('value', 'unavailable'),
            'valid_returned_frames': sum(f['valid'] for f in frames) if status == 'acknowledged' else 'unavailable',
            'visual_effect': m['visual_effect']['status'],
            'final_frame_changed_cells': change['value'] if change and change['status'] == 'measured' else 'unavailable',
            'to_state': ('not_observed' if status != 'acknowledged' else
                         'S-' + final['sha256'][:12] if final and final['valid'] else 'unavailable'),
            'events': r['environment']['events'], 'progress': r['progress']['status'],
            'continuity': r['continuity']['status']})
    return {**contract['evidence_description'], 'current_state': 'S-' + T.T1.frame_sha256(frame)[:12],
            'omitted_entries': max(0, len(current) - 8), 'entries': entries}


def request_for(observation, statement, arm, gates, contract):
    schema = copy.deepcopy(contract[arm + '_schema'])
    legal = sorted(set(observation['legal_actions']))
    branches = schema['json_schema']['schema']['properties']['action']['anyOf']
    selected = []
    for branch in branches:
        ids = [a for a in branch['properties']['action_id']['enum'] if a in legal]
        if ids:
            branch['properties']['action_id']['enum'] = ids
            selected.append(branch)
    schema['json_schema']['schema']['properties']['action']['anyOf'] = selected
    payload = {'observation': observation}
    system = contract['system_prompt']
    if arm == 'candidate':
        system += '\n' + contract['procedure']
        payload['previous_model_statement'] = statement
        gate = gates['free_text_format']
        if (gate['decision'] or gate['committed']) == 'ascii_only':
            fields = schema['json_schema']['schema']['properties']['hypothesis_test']['properties']
            for name in ('hypothesis', 'if_different'):
                fields[name]['pattern'] = '^[ !#-\\[\\]-~]{0,240}$'
    return {'model': contract['model'], 'messages': [{'role': 'system', 'content': system},
            {'role': 'user', 'content': encode(payload).decode()}], 'temperature': 0, 'seed': 0,
            'max_tokens': 128 if arm == 'baseline' else 640, 'chat_template_kwargs': {'enable_thinking': False},
            'response_format': schema}


def episode_problems(episode, case, gates, limits, contract, statement_for):
    """Reconstruct every complete request and observation; derive completed-episode boundaries from evidence."""
    problems, current, raws, acknowledged = [], episode['initial'], [], []
    chain = hashlib.sha256(b'arc3-transition-history-v1').hexdigest()
    check_observation(current)
    if (current['game_id'] != episode['game_id'] or current['win_levels'] != case['win_levels']
            or current['available_actions'] != case['initial_available_actions'] or current['full_reset'] is not True):
        problems.append('initial observation disagrees with frozen case')
    by_call = {}
    for n, step in enumerate(episode['steps']):
        index = step.get('call_index')
        if type(index) is not int or index in by_call or not 0 <= index < len(episode['calls']):
            raise ValueError('duplicate or invalid dispatch-call link')
        by_call[index] = step
        if step['index'] != n:
            raise ValueError('dispatch index sequence')
    previous_step = previous_record = previous_call = None
    for index, call in enumerate(episode['calls']):
        if current['state'] in ('WIN', 'GAME_OVER') or len(acknowledged) >= limits['actions_per_episode']:
            problems.append('call after terminal state or action cap')
        if index >= limits['decision_calls_per_episode']:
            problems.append('call after decision cap')
        last = acknowledged[-1] if acknowledged else None
        observation = {'current_grid': current['frames'][-1], 'state': current['state'],
                       'levels_completed': current['levels_completed'], 'win_levels': current['win_levels'],
                       'legal_actions': current['available_actions'],
                       'previous_grid': last['before']['frames'][-1] if last else None,
                       'recent_actions': [last['action']['action_id']] if last else [],
                       'recent_final_grids': [last['after']['frames'][-1]] if last else [],
                       'history_compaction': {'policy': 'visible_recent_transitions_v1',
                           'total_transitions': len(acknowledged), 'retained_transitions': int(last is not None),
                           'omitted_transitions': max(0, len(acknowledged) - 1),
                           'history_sha256': chain if last else None},
                       'action_effect_history': evidence_view(raws, current['frames'][-1], contract)}
        statement = statement_for(previous_call, previous_step, previous_record)
        expected = request_for(observation, statement, episode['arm'], gates, contract)
        if encode(call['request']) != encode(expected) or call.get('pre_hash') != current['canonical_hash']:
            problems.append(f'call {index}: frozen request or observation evidence differs from reconstruction')
        value, _ = EV.parse_output(call.get('response'), call.get('finish_reason'), episode['arm'])
        legal = value is not None and EV.action_problem(value.get('action'), current['available_actions']) is None
        if call.get('status') in ('valid', 'invalid_output') and (call['status'] == 'valid') != legal:
            problems.append(f'call {index}: output status differs from independent parsing')
        step = by_call.get(index)
        if legal and call.get('status') == 'valid' and step is None:
            # An interrupted/aborted run can stop between validation and dispatch; never a complete episode.
            if episode['status'] == 'complete':
                problems.append(f'call {index}: valid action has no dispatch')
        previous_call, previous_step, previous_record = call, step, None
        if step is None:
            continue
        raw = step['raw_transition']
        if (step['before'] != current or raw['before'] != observed(current)
                or raw['proposal'] != step['action'] or raw['dispatched'] != step['action']
                or raw.get('environment_source') != 'offline_development_engine'):
            problems.append(f'call {index}: transition before/proposal/source differs')
        statuses = {'acknowledged': 'acknowledged', 'dispatch_failed': 'failed', 'outcome_unknown': 'outcome_unknown'}
        if raw['outcome']['status'] != statuses.get(step['status']):
            problems.append(f'call {index}: dispatch status differs from raw outcome')
        raws.append(raw)
        previous_record = T.history(raws)[-1]
        if step['status'] == 'acknowledged':
            after = step['after']
            check_observation(after)
            if raw['outcome']['after'] != observed(after) or after['guid'] != current['guid']:
                problems.append(f'call {index}: transition after/session differs')
            payload = {'action_id': step['action']['action_id'], 'action_data': step['action']['action_data'],
                       'pre_state_hash': current['canonical_hash'], 'post_state_hash': after['canonical_hash'],
                       'prior_frame_sha256': grid_hash(current['frames'][-1]),
                       'final_frame_sha256': grid_hash(after['frames'][-1])}
            chain = hashlib.sha256(bytes.fromhex(chain) + encode(payload)).hexdigest()
            acknowledged.append(step)
            current = after
        elif index != len(episode['calls']) - 1 or step.get('after') is not None:
            problems.append('call or observation after unobserved dispatch')
    if episode['status'] == 'complete':
        if episode.get('final') != current:
            problems.append('final observation differs from reconstructed state')
        reason = ('dispatch_failure' if episode['steps'] and episode['steps'][-1]['status'] != 'acknowledged' else
                  'win' if current['state'] == 'WIN' else 'game_over' if current['state'] == 'GAME_OVER' else
                  'action_cap' if len(acknowledged) == limits['actions_per_episode'] else
                  'decision_cap' if len(episode['calls']) == limits['decision_calls_per_episode'] else None)
        if reason is None or episode['stop_reason'] != reason:
            problems.append('terminal/cap reason differs from retained evidence')
    return problems
