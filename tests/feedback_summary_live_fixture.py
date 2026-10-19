"""Synthetic live-worker fixture; never model or provider authority."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import time
from unittest.mock import patch

from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_io import write_new
from research.feedback_summary_probe_v1.interface import recognition_request
from research.feedback_probe_v1.interface import recognition_key
from research.feedback_summary_probe_live_v1.live_worker import MODEL,canary,study
from tests.feedback_probe_live_fixture import checkpoints as original_checkpoints, EffectEngine
from tests.test_feedback_probe_audit_v1 import answer


def checkpoints():
    rows = deepcopy(original_checkpoints())
    for ordinal, row in enumerate(rows):
        row['order'] = ['recent_raw','recent_summary'] if ordinal % 2 == 0 else ['recent_summary','recent_raw']
    return rows


def protocol_patches(stack):
    for module in ('live_worker','live_evaluation'):
        stack.enter_context(patch('research.feedback_summary_probe_live_v1.'+module+'.verify_inputs',return_value={}))
        stack.enter_context(patch('research.feedback_summary_probe_live_v1.'+module+'.check_checkpoints',side_effect=lambda x:x))


def create(root, *, invalid_recognition=False, invalid_policy=False):
    root = Path(root)
    inputs, output = root/'inputs',root/'output'
    inputs.mkdir(); output.mkdir()
    values = checkpoints()
    write_new(inputs/'checkpoints.json',{'checkpoints':values})
    write_new(inputs/'manifest.json',{'SYNTHETIC_TEST_ONLY':True})
    (inputs/'model-inputs').mkdir()
    keys = {}
    for value in values:
        for variant in value['order']:
            body = recognition_request(value['base_request'],variant)
            write_new(inputs/'model-inputs'/(value['checkpoint_id']+'-'+variant+'-recognition.json'),body)
            keys[digest(body)] = recognition_key(value['base_request'])
    sent=[]
    def call(client,identity,body):
        _,entry=client.ledger.admit(identity)
        sent.append(deepcopy(body))
        text=('ok' if body==canary() else 'INVALID' if identity.endswith('/recognition') and invalid_recognition else
              json.dumps(keys[digest(body)]) if identity.endswith('/recognition') else
              'INVALID' if invalid_policy else answer())
        entry.update(outcome='http_200',seconds=0.01)
        raw={'model':MODEL,'choices':[{'message':{'role':'assistant','content':text},'finish_reason':'stop'}],
             'usage':{'prompt_tokens':100,'completion_tokens':10,'total_tokens':110}}
        return 200,json.dumps(raw).encode()
    with ExitStack() as stack:
        protocol_patches(stack)
        stack.enter_context(patch('research.feedback_summary_probe_live_v1.live_worker.Client.call',new=call))
        study({'inputs':str(inputs),'input_manifest_sha256':digest({'SYNTHETIC_TEST_ONLY':True}),
               'started':time.monotonic(),'port':1},output,token_audit=lambda _:100,
              engine_factory=lambda cp,variant,effect:EffectEngine(cp,effect))
    return inputs,output,sent
