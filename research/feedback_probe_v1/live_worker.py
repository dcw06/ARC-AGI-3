"""Bounded Qwen HTTP worker with separate recognition and restored continuations.

Only main starts the verified vLLM. Injectable study dependencies permit CPU
integration checks without granting model, game or provider authority.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

from certification.direct_publisher_smoke_v1.accounting import Clock, Ledger
from certification.direct_publisher_smoke_v1.client import Client
from research.initial_geometry_assistance_v1.engine_bridge import BridgeEngine
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_io import Journal, sha, write_new
from research.initial_geometry_assistance_v1.live_resources import environment
from research.initial_geometry_assistance_v1.model_io import TokenAudit, validate_reply
from .continuation import continuation
from .interface import recognition_request
from .live_contract import check_checkpoints, verify_inputs, MAX_PROMPT_TOKENS

MODEL = 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8'
WORKER_SECONDS = 3300
ADMISSION_SECONDS = 3000


def canary():
    return {'model': MODEL, 'messages': [{'role': 'user', 'content': 'Reply with the single word: ok'}],
            'max_tokens': 16, 'temperature': 0, 'seed': 0,
            'chat_template_kwargs': {'enable_thinking': False}}


def request_plan(checkpoints):
    ids = [('canary', 'canary')]
    for checkpoint in checkpoints:
        identity = checkpoint['checkpoint_id']
        ids.append((identity+'/recognition', 'recognition'))
        ids.extend((identity+'/'+variant+'/'+str(step), 'policy')
                   for variant in checkpoint['order'] for step in range(4))
    if len(ids) > 73 or len({identity for identity, _ in ids}) != len(ids):
        raise ValueError('checkpoint HTTP plan exceeds scope or repeats identities')
    return [{'id': identity, 'kind': kind, 'method': 'POST', 'path': '/v1/chat/completions',
             'timeout_seconds': 30, 'max_issues': 1} for identity, kind in ids]


class DurableLedger(Ledger):
    def __init__(self, plan, clock, sink):
        super().__init__(plan, 73, clock)
        self.sink = sink

    def admit(self, request_id):
        item, entry = super().admit(request_id)
        self.sink({**entry, 'request_kind': entry['kind'], 'kind': 'HTTP_admission'})
        if not self.clock.admission_open():
            raise TimeoutError('HTTP admission expired while saving intent')
        return item, entry


def study(config, output, *, token_audit, engine_factory=None, headroom=120):
    """Execute one canary, each factual question, and both policy conditions.

    Recognition text is retained independently and never parsed into a policy
    request or execution argument. Invalid policy JSON stops its condition;
    technical failures terminate the worker without retries.
    """
    output, inputs = Path(output), Path(config['inputs'])
    verify_inputs(inputs, config['input_manifest_sha256'])
    checkpoints = check_checkpoints(json.loads((inputs/'checkpoints.json').read_bytes())['checkpoints'])
    clock = Clock({'internal_seconds': WORKER_SECONDS, 'admission_cutoff_seconds': ADMISSION_SECONDS},
                  config['started'])
    journal = Journal(output/'transport.jsonl')
    ledger = DurableLedger(request_plan(checkpoints), clock, journal)
    client = Client('127.0.0.1', config['port'], ledger, clock, MODEL)
    resets = dispatches = closes = closed_scorecards = 0
    completed, recognition, error = [], [], None
    deadline = config['started']+ADMISSION_SECONDS

    def complete(identity, body):
        count = token_audit(body)
        if type(count) is not int or not 0 < count <= MAX_PROMPT_TOKENS:
            raise ValueError('prospective prompt-token budget exceeded before HTTP admission')
        journal({'kind': 'HTTP_request', 'id': identity, 'body': body, 'native_prompt_tokens': count})
        status, raw = client.call(identity, body)
        journal({'kind': 'HTTP_response', 'id': identity, 'status': status, 'raw': raw.decode('utf-8')})
        if status != 200:
            raise ValueError('model HTTP status '+str(status))
        return validate_reply(body, json.loads(raw), count)

    def admission():
        if deadline-time.monotonic() < headroom:
            raise TimeoutError('checkpoint condition admission headroom not met')

    try:
        if complete('canary', canary()).strip() != 'ok':
            raise ValueError('startup canary content differs')
        for checkpoint in checkpoints:
            identity = checkpoint['checkpoint_id']
            admission()
            body = recognition_request(checkpoint['base_request'])
            retained = json.loads((inputs/'model-inputs'/(identity+'-recognition.json')).read_bytes())
            if digest(body) != digest(retained):
                raise ValueError('recognition request differs from sealed model input')
            recognition.append({'checkpoint_id': identity, 'text': complete(identity+'/recognition', body)})
            for variant in checkpoint['order']:
                admission()
                name = identity+'-'+variant
                events = Journal(output/(name+'.jsonl'))
                local_step = 0

                def response(request):
                    nonlocal local_step
                    value = complete(identity+'/'+variant+'/'+str(local_step), request)
                    local_step += 1
                    return value

                def effect(operation):
                    nonlocal resets, dispatches, closes
                    if operation == 'bootstrap':
                        if resets >= 16: raise ValueError('bootstrap cap')
                        resets += 1
                    elif operation == 'dispatch':
                        if dispatches >= 100: raise ValueError('prefix/continuation dispatch cap')
                        dispatches += 1
                    elif operation == 'close':
                        if closes >= 16: raise ValueError('local scorecard close cap')
                        closes += 1
                    else:
                        raise ValueError('unexpected engine operation')
                    journal({'kind': 'engine_admission', 'episode': name, 'operation': operation,
                             'bootstrap_attempts': resets, 'dispatch_attempts': dispatches,
                             'close_attempts': closes})

                try:
                    engine = (engine_factory(checkpoint, variant, effect) if engine_factory is not None else
                              BridgeEngine(config['game_python'], checkpoint['game_id'], config['games'],
                                           output/(name+'-recordings'), output/(name+'-engine.log'), deadline,
                                           env=dict(environment(), PYTHONPATH=str(Path(__file__).resolve().parents[2])),
                                           on_effect=effect))

                    def retain(event):
                        nonlocal closed_scorecards
                        events(event)
                        if event.get('kind') == 'closed' and event.get('receipt') == {
                                'closed': True, 'local_scorecard_opened': True,
                                'local_scorecard_closed': True, 'online_calls': 0}:
                            closed_scorecards += 1

                    completed.append(continuation(checkpoint, variant, engine, response, retain,
                                                  model=MODEL, deadline=deadline))
                finally:
                    events.close()
        clock.check('worker completed')
    except BaseException as exc:
        error = type(exc).__name__+': '+str(exc)
        raise
    finally:
        try:
            write_new(output/'worker-result.json', {
                'schema': 'feedback_probe_worker_v1', 'error': error, 'recognition': recognition,
                'continuations': completed, 'ledger': ledger.summary(), 'bootstrap_attempts': resets,
                'dispatch_attempts': dispatches, 'close_attempts': closes,
                'closed_scorecards': closed_scorecards, 'lifecycle_certified': False})
        finally:
            journal.close()
    return completed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_bytes())
    expected = os.environ.pop('FEEDBACK_PROBE_CONFIG_SHA256')
    if sha(args.config) != expected:
        raise ValueError('worker configuration changed')
    if not sys.version.startswith('3.12.'):
        raise ValueError('pinned Python interpreter differs')
    import importlib.metadata as metadata
    if any(metadata.version(key) != value for key, value in config['model_host_packages'].items()):
        raise ValueError('pinned model packages differ')
    verify_inputs(config['inputs'], config['input_manifest_sha256'])
    with (args.output/'vllm.log').open('ab') as log:
        process = subprocess.Popen(config['server_argv'], stdin=subprocess.DEVNULL, stdout=log,
                                   stderr=subprocess.STDOUT, env=environment())
        startup_deadline = min(config['started']+ADMISSION_SECONDS, time.monotonic()+900)
        while True:
            if process.poll() is not None:
                raise RuntimeError('vLLM exited before TCP readiness')
            remaining = startup_deadline-time.monotonic()
            if remaining <= 0:
                raise TimeoutError('model startup deadline')
            try:
                with socket.create_connection(('127.0.0.1', config['port']), timeout=min(1, remaining)):
                    break
            except OSError:
                time.sleep(min(0.5, max(0, startup_deadline-time.monotonic())))
        study(config, args.output, token_audit=TokenAudit(config['model_path']))
    # The supervisor owns vLLM and all engine children through final cleanup.


if __name__ == '__main__':
    main()
