"""Synthetic test-only worker inputs and transport, never inference authority."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import time
from unittest.mock import patch

from research.action_effect_choice_v2.preparation import derive
from research.action_effect_choice_live_v2.live_worker import MODEL, canary, study
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_io import write_new
from tests.feedback_probe_live_fixture import checkpoints as original_checkpoints, EffectEngine


def checkpoints():
    values = original_checkpoints()
    from research.initial_geometry_assistance_v1.policy import request_for
    for cp in values:
        for observation in [cp['initial'], cp['current']] + [v for record in cp['prefix'] for v in (record['before'], record['after'])]:
            observation['legal_actions'] = [1, 2]
        cp['base_request'] = request_for(cp['initial'], cp['initial_case']['geometry']['reviewed'], cp['current'],
                                         cp['prefix'], cp['decision_step'], MODEL)
    for cp, row in zip(values, derive(values)): cp['order'] = row['order']
    return values[:2]


def protocol_patches(stack):
    for module in ('live_worker', 'live_evaluation', 'audit'):
        stack.enter_context(patch('research.action_effect_choice_live_v2.'+module+'.verify_inputs', return_value={}))
        stack.enter_context(patch('research.action_effect_choice_live_v2.'+module+'.check_checkpoints', side_effect=lambda x: x))


def create(root, *, invalid=False):
    root = Path(root)
    inputs, output = root/'inputs', root/'output'
    inputs.mkdir(); output.mkdir()
    values = checkpoints()
    write_new(inputs/'checkpoints.json', {'checkpoints': values})
    from research.action_effect_choice_v2.interface import candidates, VARIANTS
    write_new(inputs/'candidate-pairs.json', [dict(checkpoint_id=cp['checkpoint_id'],
        candidates=candidates(cp,i), order=list(VARIANTS if i%2==0 else reversed(VARIANTS))) for i,cp in enumerate(values)])
    write_new(inputs/'manifest.json', {'SYNTHETIC_TEST_ONLY': True})
    sent = []

    def call(client, identity, body):
        _, entry = client.ledger.admit(identity)
        sent.append(deepcopy(body))
        first = identity.endswith('/0')
        text = 'ok' if body == canary() else 'INVALID' if invalid else json.dumps({
            'candidate_predictions': {'A': 'unknown', 'B': 'none'}, 'selected_candidate': 'B',
            'observed_previous_change': 'not_applicable' if first else 'no',
            'previous_prediction_check': 'not_applicable' if first else 'matched'})
        entry.update(outcome='http_200', seconds=0.01)
        reply = {'model': MODEL, 'choices': [{'message': {'role': 'assistant', 'content': text}, 'finish_reason': 'stop'}],
                 'usage': {'prompt_tokens': 100, 'completion_tokens': 10, 'total_tokens': 110}}
        return 200, json.dumps(reply).encode()

    with ExitStack() as stack:
        protocol_patches(stack)
        stack.enter_context(patch('research.action_effect_choice_live_v2.live_worker.Client.call', new=call))
        study({'inputs': str(inputs), 'input_manifest_sha256': digest({'SYNTHETIC_TEST_ONLY': True}),
               'started': time.monotonic(), 'port': 1}, output, token_audit=lambda _: 100,
              engine_factory=lambda cp, variant, effect: EffectEngine(cp, effect))
    return inputs, output, sent
