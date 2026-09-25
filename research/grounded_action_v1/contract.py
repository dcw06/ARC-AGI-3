"""Versioned, deliberately small Stage B request and response contract."""
import copy
import hashlib
import json
from pathlib import Path

from certification.phase4_transient_v2.action_contract import validate_action

ROOT = Path(__file__).resolve().parents[2]


def case_protocol():
    value = json.loads((ROOT / 'reports/perception_stage_b_v1_case_protocol.json').read_bytes())
    bindings = {'initial_observation_sha256': 'reports/integrated_case_v1/initial_observation.json',
                'reviewer_geometry_sha256': 'reports/integrated_case_v1/geometry_reference.json',
                'baseline_protocol_sha256': 'reports/phase4_transient_v2_protocol.json',
                'tokenizer_manifest_sha256': 'certification/phase4_integrated_v2/tokenizer_manifest.json'}
    if any(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != value[key]
           for key, path in bindings.items()):
        raise ValueError('Stage B case/source binding drift')
    archive = ROOT / 'evidence/phase4-v2-development-offline.zip'
    if archive.is_file():
        if hashlib.sha256(archive.read_bytes()).hexdigest() != value['development_archive_sha256']:
            raise ValueError('Stage B development archive drift')
    else:
        # The target uses the separately mounted, manifest-verified game files.
        # The 43 MiB historical archive is not embedded in the notebook.
        manifest = json.loads((ROOT / 'reports/phase4_v2_offline_package.json').read_bytes())
        if manifest['archive_sha256'] != value['development_archive_sha256']:
            raise ValueError('Stage B development archive manifest drift')
    if (value['game_id'] != 'ar25-0c556536' or value['arms_in_order'] != ['control', 'target'] or
            value['max_actions_per_arm'] != 2 or value['max_model_calls'] != 12 or
            value['provider_seconds_authorized'] != 0 or value['gpu_launch_authorized'] is not False):
        raise ValueError('Stage B case protocol drift')
    return value

TARGET_INSTRUCTION = (
    " Commit one visible target as an inclusive cell or box in grid[y][x] "
    "coordinates alongside the action. Use null only for a nonspatial action. "
    "Do not infer a game rule from visual similarity."
)
LEGACY_PREDICTION_INSTRUCTION = (
    "Return only JSON. Report an observable prediction and distinct alternative "
    "for the already committed action; this answer cannot change the action."
)
PREDICTION_INSTRUCTION = (
    "Return only JSON with prediction='change' if at least one visible cell "
    "will change after the already committed action, otherwise 'no_change'. "
    "The opposite alternative is derived mechanically; this answer cannot "
    "change the action."
)
FEEDBACK_INSTRUCTION = (
    "Return only JSON. Feedback grids use hex_rows_v1: each row is 64 hexadecimal "
    "digits, one color value per cell, with rows in y order and digits in x order. "
    "Compare every returned frame with the supplied before frame. "
    "Assess the supplied committed prediction as supported, contradicted, or "
    "unresolved; report changed frame indices. This answer cannot change the "
    "committed action or enter a later policy request."
)
LEGACY_FEEDBACK_INSTRUCTION = (
    "Return only JSON. Compare every returned frame with the supplied before frame. "
    "Assess the supplied committed prediction as supported, contradicted, or "
    "unresolved; report changed frame indices. This answer cannot change the "
    "committed action or enter a later policy request."
)


def feedback_grid(frame):
    """Losslessly encode the fixed 64x64 development board for sealed audits."""
    if (type(frame) is not list or len(frame) != 64 or
            any(type(row) is not list or len(row) != 64 for row in frame)):
        raise ValueError('feedback grid shape')
    digits = '0123456789abcdef'
    rows = []
    for row in frame:
        if any(type(value) is not int or not 0 <= value < 16 for value in row):
            raise ValueError('feedback grid palette')
        rows.append(''.join(digits[value] for value in row))
    return rows


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def target_schema():
    return {'type': 'object', 'properties': {
        'kind': {'type': 'string', 'enum': ['cell', 'box', 'none']},
        'box': {'anyOf': [{'type': 'array', 'items': {'type': 'integer', 'minimum': 0, 'maximum': 63},
                          'minItems': 4, 'maxItems': 4}, {'type': 'null'}]}},
        'required': ['kind', 'box'], 'additionalProperties': False}


def policy_request(runtime, arm):
    # The model host imports this module for the canary/protocol. Only the game
    # worker builds policy requests; its historical builder imports arcengine.
    from certification.phase4_integrated_v2.contract import baseline_request
    request = baseline_request(runtime)
    if arm == 'control':
        return request
    if arm != 'target':
        raise ValueError('arm')
    request = copy.deepcopy(request)
    request['messages'][0]['content'] += TARGET_INSTRUCTION
    schema = request['response_format']['json_schema']['schema']
    schema['properties']['target'] = target_schema()
    schema['required'].append('target')
    request['response_format']['json_schema']['name'] = 'grounded_target_v1'
    return request


def audit_request(stage, observation, action, *, before=None, prediction=None,
                  feedback_encoding='hex_rows_v1', prediction_contract='single_choice_v2'):
    if stage not in ('prediction', 'feedback'):
        raise ValueError('audit stage')
    if prediction_contract not in ('single_choice_v2', 'legacy_pair_v1'):
        raise ValueError('prediction contract')
    payload = {'stage': stage, 'action': action,
               'observation': {k: observation[k] for k in ('frames', 'levels_completed', 'state')}}
    if stage == 'feedback':
        if feedback_encoding not in ('hex_rows_v1', 'legacy_grid_json_v1'):
            raise ValueError('feedback encoding')
        if not 1 <= len(observation['frames']) <= (6 if feedback_encoding == 'legacy_grid_json_v1' else 8):
            raise ValueError('feedback frame admission; retain all returned frames and stop')
        if before is None or type(prediction) is not dict or set(prediction) != {'prediction', 'alternative'} or \
                {prediction['prediction'], prediction['alternative']} != {'change', 'no_change'}:
            raise ValueError('missing or invalid committed prediction')
        # The prediction was made from the latest pre-action grid. Earlier
        # returned frames remain in evidence but are not repeated in this audit.
        if feedback_encoding == 'hex_rows_v1':
            payload['grid_encoding'] = feedback_encoding
            payload['observation']['frames'] = [feedback_grid(frame) for frame in observation['frames']]
        payload['before'] = {'frames': [feedback_grid(before['frames'][-1])
                                       if feedback_encoding == 'hex_rows_v1' else before['frames'][-1]],
                             'levels_completed': before['levels_completed'], 'state': before['state']}
        payload['committed_prediction'] = prediction
    else:
        if before is not None or prediction is not None or feedback_encoding != 'hex_rows_v1':
            raise ValueError('unexpected pre-action observation/prediction')
    fields = ({'prediction': {'type': 'string', 'enum': ['change', 'no_change']},
               **({'alternative': {'type': 'string', 'enum': ['change', 'no_change']}}
                  if prediction_contract == 'legacy_pair_v1' else {})}
              if stage == 'prediction' else
              {'assessment': {'type': 'string', 'enum': ['supported', 'contradicted', 'unresolved']},
               'changed_frames': {'type': 'array', 'items': {'type': 'integer', 'minimum': 0, 'maximum': 7},
                                  'maxItems': 8}})
    return {'model': baseline_request_model(), 'messages': [
        {'role': 'system', 'content': (LEGACY_PREDICTION_INSTRUCTION if prediction_contract == 'legacy_pair_v1'
                                    else PREDICTION_INSTRUCTION) if stage == 'prediction' else
         (LEGACY_FEEDBACK_INSTRUCTION if feedback_encoding == 'legacy_grid_json_v1' else FEEDBACK_INSTRUCTION)},
        {'role': 'user', 'content': json.dumps(payload, sort_keys=True, separators=(',', ':'))}],
        'temperature': 0, 'seed': 0, 'max_tokens': 128,
        'chat_template_kwargs': {'enable_thinking': False},
        'response_format': {'type': 'json_schema', 'json_schema': {
            'name': ('grounded_prediction_v2' if stage == 'prediction' and
                     prediction_contract == 'single_choice_v2' else 'grounded_' + stage + '_v1'),
            'strict': True,
            'schema': {'type': 'object', 'properties': fields, 'required': list(fields),
                       'additionalProperties': False}}}}


def baseline_request_model():
    from certification.phase4_transient_v2.request_contract import protocol
    return protocol()['model_binding']['model_id']


def strict_json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('duplicate JSON key')
            out[key] = value
        return out
    return json.loads(raw, object_pairs_hook=pairs)


def parse_policy(raw, arm, legal, grid):
    value = strict_json(raw)
    if type(value) is not dict or set(value) != ({'action'} if arm == 'control' else {'action', 'target'}):
        raise ValueError('policy fields')
    action = validate_action(json.dumps({'action': value['action']}), legal)['action']
    if arm == 'control':
        return value
    target = value['target']
    if type(target) is not dict or set(target) != {'kind', 'box'}:
        raise ValueError('target fields')
    kind, box = target['kind'], target['box']
    if kind == 'none':
        if box is not None or action['action_id'] == 6:
            raise ValueError('click requires target')
    elif kind in ('cell', 'box'):
        if type(box) is not list or len(box) != 4 or any(type(v) is not int for v in box):
            raise ValueError('target box')
        x0, y0, x1, y1 = box
        if not (0 <= x0 <= x1 < len(grid[0]) and 0 <= y0 <= y1 < len(grid)):
            raise ValueError('target bounds')
        if kind == 'cell' and (x0 != x1 or y0 != y1):
            raise ValueError('cell extent')
    else:
        raise ValueError('target kind')
    return value


def parse_audit(raw, stage, frames, *, prediction_contract='single_choice_v2'):
    value = strict_json(raw)
    if type(value) is not dict:
        raise ValueError('audit object')
    if stage == 'prediction':
        if prediction_contract == 'legacy_pair_v1':
            if set(value) != {'prediction', 'alternative'} or \
                    {value['prediction'], value['alternative']} != {'change', 'no_change'}:
                raise ValueError('prediction alternatives')
        elif prediction_contract == 'single_choice_v2':
            if set(value) != {'prediction'} or value['prediction'] not in ('change', 'no_change'):
                raise ValueError('prediction fields')
            value['alternative'] = 'no_change' if value['prediction'] == 'change' else 'change'
        else:
            raise ValueError('prediction contract')
    elif stage == 'feedback':
        if (set(value) != {'assessment', 'changed_frames'} or value['assessment'] not in
                ('supported', 'contradicted', 'unresolved') or type(value['changed_frames']) is not list or
                len(value['changed_frames']) > len(frames) or len(set(value['changed_frames'])) != len(value['changed_frames']) or
                any(type(i) is not int or not 0 <= i < len(frames) for i in value['changed_frames'])):
            raise ValueError('feedback fields')
    else:
        raise ValueError('audit stage')
    return value


def target_hit(value):
    if 'target' not in value or value['action']['action_id'] != 6:
        return None
    x, y = (value['action']['action_data'][k] for k in ('x', 'y'))
    x0, y0, x1, y1 = value['target']['box']
    return x0 <= x <= x1 and y0 <= y <= y1
