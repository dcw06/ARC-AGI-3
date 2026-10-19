"""Deterministic past-only selection, independent of the recorded next answer."""
from copy import deepcopy

from research.initial_geometry_assistance_v1.geometry import digest
import json
from research.initial_geometry_assistance_v1.policy import check_observation, parse_answer, request_for


def select_checkpoints(case, events, *, model):
    initial = current = None
    history, chosen, seen = [], [], set()
    for event in events:
        kind = event['kind']
        if kind == 'initial':
            initial = current = deepcopy(check_observation(event['observation']))
            if digest(initial['grid']) != case['grid_sha256']:
                raise ValueError('initial grid differs from reviewed case')
        elif kind == 'transition':
            if event['step'] != len(history) or event['before'] != current:
                raise ValueError('prefix chain differs')
            check_observation(event['after'])
            history.append(deepcopy({k: v for k, v in event.items() if k != 'kind'}))
            current = deepcopy(event['after'])
        elif kind == 'request':
            step = event['step']
            if step > 20:
                break
            if step != len(history) or current is None:
                raise ValueError('checkpoint step differs from prefix')
            body = request_for(initial, case['geometry']['reviewed'], current, history, step, model)
            if event['body'] != body or event['request_sha256'] != digest(body):
                raise ValueError('checkpoint request not reconstructed from past observations')
            if step < 2 or current['state'] != 'NOT_FINISHED' or current['levels_completed'] != 0 or not current['legal_actions']:
                continue
            previous = history[-1]
            stratum = ('unchanged' if previous['before'] == previous['after'] == current else
                       'changed' if previous['before']['grid'] != previous['after']['grid'] else None)
            if stratum is None or stratum in seen:
                continue
            seen.add(stratum)
            chosen.append({'schema': 'feedback_probe_checkpoint_v1',
                'checkpoint_id': case['case_id']+'-step'+str(step).zfill(2),
                'case_id': case['case_id'], 'game_id': case['game_id'], 'stratum': stratum,
                'decision_step': step, 'initial_case': deepcopy(case), 'initial': deepcopy(initial),
                'current': deepcopy(current), 'prefix': deepcopy(history), 'base_request': body})
            if len(seen) == 2:
                break
    return chosen


def checked_checkpoint(value, *, model):
    case, current, initial, prefix = value['initial_case'], value['current'], value['initial'], value['prefix']
    check_observation(initial)
    check_observation(current)
    if (initial['levels_completed'] != 0 or initial['state'] != 'NOT_FINISHED' or
            initial['grid'] != case['grid'] or digest(initial['grid']) != case['grid_sha256'] or
            current['levels_completed'] != 0 or current['state'] != 'NOT_FINISHED' or
            type(value['decision_step']) is not int or not 2 <= value['decision_step'] <= 20 or
            len(prefix) != value['decision_step'] or value['case_id'] != case['case_id'] or
            value['game_id'] != case['game_id']):
        raise ValueError('checkpoint identity/scope differs')
    observed = initial
    for step, entry in enumerate(prefix):
        if (type(entry['step']) is not int or entry['step'] != step or entry['before'] != observed or
                observed['state'] != 'NOT_FINISHED' or observed['levels_completed'] != 0):
            raise ValueError('checkpoint prefix chain differs')
        parse_answer(json.dumps(dict(entry['action'], predicted_visible_change=entry['predicted_visible_change'])),
                     observed['legal_actions'])
        check_observation(entry['after'])
        observed = entry['after']
    if observed != current or value['base_request'] != request_for(initial, case['geometry']['reviewed'], current, prefix,
                                                               value['decision_step'], model):
        raise ValueError('checkpoint current state or full request differs')
    last = prefix[-1]
    stratum = ('unchanged' if last['before'] == last['after'] == current else
               'changed' if last['before']['grid'] != last['after']['grid'] else None)
    if value['stratum'] != stratum or value['checkpoint_id'] != case['case_id']+'-step'+str(len(prefix)).zfill(2):
        raise ValueError('checkpoint stratum/identity differs from prefix')
    return value
