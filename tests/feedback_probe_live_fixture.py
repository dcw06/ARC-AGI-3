"""Synthetic whole-study fixtures; never model/GPU/provider authority."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import time
from unittest.mock import patch

from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.policy import request_for
from research.initial_geometry_assistance_v1.live_io import write_new
from research.feedback_probe_v1.interface import recognition_key, recognition_request
from research.feedback_probe_v1.live_worker import MODEL, canary, study
from tests.test_feedback_probe_audit_v1 import ScriptEngine, answer, checkpoint


def checkpoints():
    rows = []
    for i in range(8):
        value = deepcopy(checkpoint())
        if i in (3, 6):
            old = deepcopy(value['prefix'][-1])
            old['step'] = 2
            old['before'] = deepcopy(value['current'])
            old['after'] = deepcopy(value['current'])
            value['prefix'].append(old)
            value['decision_step'] = 3
        case = value['initial_case']
        case['case_id'] = value['case_id'] = 'synthetic-'+str(i)
        value['checkpoint_id'] = value['case_id']+'-step'+str(value['decision_step']).zfill(2)
        value['base_request'] = request_for(value['initial'], case['geometry']['reviewed'], value['current'],
                                           value['prefix'], value['decision_step'], MODEL)
        value['order'] = ['baseline', 'probe_instruction'] if i % 2 == 0 else ['probe_instruction', 'baseline']
        rows.append(value)
    return rows


class EffectEngine(ScriptEngine):
    def __init__(self, value, effect):
        super().__init__(value)
        self.effect = effect

    def bootstrap(self):
        self.effect('bootstrap')
        return super().bootstrap()

    def dispatch(self, action):
        self.effect('dispatch')
        return super().dispatch(action)

    def close(self):
        self.effect('close')
        return super().close()


def protocol_patches(stack):
    # Synthetic scientific inventory is explicit; actual inventory/manifest
    # validation is exercised separately on the rebuilt private bundle.
    for module in ('live_worker', 'live_evaluation'):
        stack.enter_context(patch('research.feedback_probe_v1.'+module+'.verify_inputs', return_value={}))
        stack.enter_context(patch('research.feedback_probe_v1.'+module+'.check_checkpoints', side_effect=lambda x: x))


def create(root, *, invalid_recognition=False, invalid_policy=False):
    root = Path(root)
    inputs, output = root/'inputs', root/'output'
    inputs.mkdir(); output.mkdir()
    values = checkpoints()
    write_new(inputs/'checkpoints.json', {'checkpoints': values})
    write_new(inputs/'manifest.json', {'SYNTHETIC_TEST_ONLY': True})
    (inputs/'model-inputs').mkdir()
    for value in values:
        write_new(inputs/'model-inputs'/(value['checkpoint_id']+'-recognition.json'), recognition_request(value['base_request']))
    keys = {digest(recognition_request(v['base_request'])): recognition_key(v['base_request']) for v in values}
    sent = []
    def call(client, identity, body):
        _, entry = client.ledger.admit(identity)
        sent.append(deepcopy(body))
        text = ('ok' if body == canary() else 'INVALID' if identity.endswith('/recognition') and invalid_recognition else
                json.dumps(keys[digest(body)]) if identity.endswith('/recognition') else
                'INVALID' if invalid_policy else answer())
        entry.update(outcome='http_200', seconds=0.01)
        raw = {'model': MODEL, 'choices': [{'message': {'role': 'assistant', 'content': text}, 'finish_reason': 'stop'}],
               'usage': {'prompt_tokens': 100, 'completion_tokens': 10, 'total_tokens': 110}}
        return 200, json.dumps(raw).encode()
    with ExitStack() as stack:
        protocol_patches(stack)
        stack.enter_context(patch('research.feedback_probe_v1.live_worker.Client.call', new=call))
        config = {'inputs': str(inputs), 'input_manifest_sha256': digest({'SYNTHETIC_TEST_ONLY': True}),
                  'started': time.monotonic(), 'port': 1}
        study(config, output, token_audit=lambda _: 100,
              engine_factory=lambda cp, variant, effect: EffectEngine(cp, effect))
    return inputs, output, sent
