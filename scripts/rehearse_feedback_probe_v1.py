"""Owned, loopback-only CPU HTTP/engine/replay rehearsal; scripted replies only.

The caller must supervise this process group with a separate hard deadline.
No model weights, vLLM, GPU allocation, network service or live authority is used.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import zipfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from certification.direct_publisher_smoke_v1.accounting import Clock, Ledger
from certification.direct_publisher_smoke_v1.client import Client
from research.initial_geometry_assistance_v1.engine import verify_game_environment
from research.initial_geometry_assistance_v1.engine_bridge import BridgeEngine
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_io import Journal, sha, write_new
from research.initial_geometry_assistance_v1.live_resources import environment
from research.initial_geometry_assistance_v1.live_worker import canary, MODEL
from research.initial_geometry_assistance_v1.model_io import TokenAudit, validate_reply
from research.feedback_probe_v1.audit import audit_continuation
from research.feedback_probe_v1.continuation import continuation
from research.feedback_probe_v1.interface import recognition_key
from research.feedback_probe_v1.preparation import verify_prepared
from research.feedback_probe_v1.scoring import score_recognition


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('inputs', 'game-environment', 'game-python', 'output', 'recordings'):
        parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--draft-pin', required=True)
    parser.add_argument('--game-pin', required=True)
    args = parser.parse_args()
    interfaces = {line.split(':')[0].strip() for line in Path('/proc/net/dev').read_text().splitlines()[2:] if ':' in line}
    if (sys.platform != 'linux' or interfaces != {'lo'} or os.getpgrp() != os.getpid() or
            os.environ.get('FEEDBACK_PROBE_CPU_OWNED') != '1'):
        raise ValueError('requires owned Linux process group, external watchdog and loopback-only namespace')
    os.environ.update(CUDA_VISIBLE_DEVICES='', NVIDIA_VISIBLE_DEVICES='void', HF_HUB_OFFLINE='1',
                      TRANSFORMERS_OFFLINE='1', MPLBACKEND='Agg')
    prepared = verify_prepared(args.inputs, args.draft_pin, ROOT)
    verify_game_environment(args.game_environment, args.game_pin)
    checkpoints = json.loads((args.inputs/'checkpoints.json').read_bytes())['checkpoints']
    args.output.mkdir(exist_ok=False)
    started, server = time.monotonic(), None
    deadline = started+600
    received, effects, audited, recognition = [], [], [], []
    ids = ['canary']
    for checkpoint in checkpoints:
        ids.append(checkpoint['checkpoint_id']+'/recognition')
        ids.extend(checkpoint['checkpoint_id']+'/'+variant+'/'+str(i) for variant in checkpoint['order'] for i in range(4))
    plan = [{'id': i, 'kind': 'canary' if i == 'canary' else 'study', 'method': 'POST',
             'path': '/v1/chat/completions', 'timeout_seconds': 30, 'max_issues': 1} for i in ids]
    clock = Clock({'internal_seconds': 600, 'admission_cutoff_seconds': 550}, started)
    ledger = Ledger(plan, len(ids), clock)
    transport = Journal(args.output/'transport.jsonl')
    try:
        import torch
        torch.set_num_threads(2)
        archive = ROOT/'evidence/phase4-multimodal-preflight-v3-processor-inputs.zip'
        if sha(archive) != 'af5aebbe4761d80b50effd5758fbadac13f80edacbf37a1f0591baa473c913d1':
            raise ValueError('processor fixture changed')
        with tempfile.TemporaryDirectory(prefix='probe-CPU-processor-') as folder:
            with zipfile.ZipFile(archive) as bundle:
                for name in bundle.namelist():
                    if Path(name).name != name: raise ValueError('unsafe processor file')
                    (Path(folder)/name).write_bytes(bundle.read(name))
            native = TokenAudit(folder)
            scripted_recognition = {digest(json.loads((args.inputs/r['path']).read_bytes())):
                recognition_key(checkpoint['base_request']) for checkpoint in checkpoints
                for r in prepared['model_input_rows'] if r['checkpoint_id'] == checkpoint['checkpoint_id'] and r['kind'] == 'recognition'}
            class Handler(BaseHTTPRequestHandler):
                def log_message(self, *a): pass
                def do_POST(self):
                    body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    received.append(body)
                    if body == canary(): text, tokens = 'ok', 1
                    elif digest(body) in scripted_recognition:
                        text, tokens = json.dumps(scripted_recognition[digest(body)]), 80
                    else:
                        meta = json.loads(body['messages'][1]['content'][0]['text'])
                        action_id = meta['current_legal_actions'][0]
                        text, tokens = json.dumps({'action_id': action_id, 'action_data': {'x': 31, 'y': 31} if action_id == 6 else {},
                                                 'predicted_visible_change': 'unknown'}), 32
                    count = native(body)
                    raw = json.dumps({'model': MODEL, 'choices': [{'message': {'role': 'assistant', 'content': text},
                        'finish_reason': 'stop'}], 'usage': {'prompt_tokens': count, 'completion_tokens': tokens,
                                                           'total_tokens': count+tokens}}).encode()
                    self.send_response(200); self.send_header('Content-Length', str(len(raw))); self.end_headers(); self.wfile.write(raw)
            server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            client = Client('127.0.0.1', server.server_port, ledger, clock, MODEL)
            def complete(identity, body):
                count = native(body)
                if type(count) is not int or not 0 < count <= 8192: raise ValueError('CPU prompt ceiling')
                transport({'kind': 'request', 'id': identity, 'body': body, 'native_prompt_tokens': count})
                status, raw = client.call(identity, body)
                transport({'kind': 'response', 'id': identity, 'status': status, 'raw': raw.decode()})
                if status != 200: raise ValueError('scripted HTTP failed')
                return validate_reply(body, json.loads(raw), count)
            if complete('canary', canary()).strip() != 'ok': raise ValueError('scripted canary')
            for checkpoint in checkpoints:
                identity = checkpoint['checkpoint_id']
                r = next(r for r in prepared['model_input_rows'] if r['checkpoint_id'] == identity and r['kind'] == 'recognition')
                body = json.loads((args.inputs/r['path']).read_bytes())
                scored = score_recognition(complete(identity+'/recognition', body), recognition_key(checkpoint['base_request']))
                if not scored['all_fields_correct']: raise ValueError('scripted recognition integration failed')
                recognition.append(scored)
                for variant in checkpoint['order']:
                    name = identity+'-'+variant
                    events, step = [], [0]
                    def response(body):
                        value = complete(identity+'/'+variant+'/'+str(step[0]), body)
                        step[0] += 1
                        return value
                    def engine(phase):
                        return BridgeEngine(args.game_python, checkpoint['game_id'], args.game_environment/'environment_files',
                            args.recordings/(name+'-'+phase), args.output/(name+'-'+phase+'.log'), deadline,
                            env=dict(environment(), PYTHONPATH=str(ROOT)),
                            on_effect=lambda op: effects.append({'phase': phase, 'episode': name, 'operation': op}))
                    result = continuation(checkpoint, variant, engine('play'), response, events.append, model=MODEL, deadline=deadline)
                    write_new(args.output/(name+'-events.json'), events)
                    audited.append(audit_continuation(checkpoint, variant, events, model=MODEL, replay_engine=engine('replay')))
            sent = [e['body'] for e in [json.loads(x) for x in (args.output/'transport.jsonl').read_text().splitlines()]
                    if e['kind'] == 'request']
            if (received != sent or len(received) != 1+len(recognition)+sum(r['policy_calls'] for r in audited) or
                    len(received) > prepared['prospective_maxima']['total_generations'] or ledger.refusals):
                raise ValueError('actual scripted transport differs from recorded schedule')
            verify_prepared(args.inputs, args.draft_pin, ROOT)
            if time.monotonic() >= deadline: raise TimeoutError('CPU rehearsal deadline')
    finally:
        if server is not None: server.shutdown(); server.server_close()
        transport.close()
    counts = {phase: {op: sum(e['phase'] == phase and e['operation'] == op for e in effects)
                      for op in ('bootstrap', 'dispatch', 'close')} for phase in ('play', 'replay')}
    expected = prepared['prospective_maxima']
    for phase in counts:
        if (counts[phase]['bootstrap'] != expected['bootstrap_resets'] or counts[phase]['close'] != expected['local_scorecards'] or
                counts[phase]['dispatch'] != expected['prefix_dispatches']+sum(r['continuation_dispatches'] for r in audited)):
            raise ValueError('CPU engine accounting differs')
    receipt = {'passed': True, 'draft_lock_sha256': args.draft_pin, 'scripted_HTTP_completions': len(received),
        'recognition_responses': len(recognition), 'continuations': len(audited), 'engine_replays': len(audited),
        'effects': counts, 'rows': audited, 'elapsed_seconds': time.monotonic()-started,
        'GPU_jobs': 0, 'neural_model_generations': 0, 'provider_writes': 0,
        'qualification': 'Scripted responses test integration only. Recognition correctness and policy outcomes are not model performance or live lifecycle certification.'}
    write_new(args.output/'receipt.json', receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k != 'rows'}), flush=True)


if __name__ == '__main__': main()
