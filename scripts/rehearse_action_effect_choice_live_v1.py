"""Exercise the actual live worker via scripted loopback HTTP and real CPU games.

Requires a separately supervised, GPU-disabled Linux process group inside a
loopback-only network namespace. This is not neural inference or live authority.
The scripted answer server is deliberately excluded from the live payload.
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
from research.initial_geometry_assistance_v1.engine import verify_game_environment
from research.initial_geometry_assistance_v1.engine_bridge import BridgeEngine
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from research.initial_geometry_assistance_v1.live_resources import environment
from research.initial_geometry_assistance_v1.model_io import TokenAudit
from research.action_effect_choice_live_v1.live_contract import verify_inputs
from research.action_effect_choice_live_v1.live_worker import study, canary, MODEL
from research.action_effect_choice_live_v1.live_evaluation import audit_study


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('inputs', 'game-environment', 'game-python', 'output', 'recordings'):
        parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--input-pin', required=True)
    parser.add_argument('--game-pin', required=True)
    args = parser.parse_args()
    interfaces = {line.split(':')[0].strip() for line in Path('/proc/net/dev').read_text().splitlines()[2:] if ':' in line}
    if (sys.platform != 'linux' or interfaces != {'lo'} or os.getpgrp() != os.getpid() or
            os.environ.get('ACTION_EFFECT_CHOICE_CPU_OWNED') != '1' or os.environ.get('CUDA_VISIBLE_DEVICES') != ''):
        raise ValueError('requires externally supervised GPU-disabled Linux group and loopback-only namespace')
    verify_inputs(args.inputs, args.input_pin)
    verify_game_environment(args.game_environment, args.game_pin)
    checkpoints = json.loads((args.inputs/'checkpoints.json').read_bytes())['checkpoints']
    args.output.mkdir(exist_ok=False)
    started, received = time.monotonic(), []
    archive = ROOT/'evidence/phase4-multimodal-preflight-v3-processor-inputs.zip'
    if sha(archive) != 'af5aebbe4761d80b50effd5758fbadac13f80edacbf37a1f0591baa473c913d1':
        raise ValueError('pinned CPU processor fixture changed')
    import torch
    torch.set_num_threads(2)
    with tempfile.TemporaryDirectory(prefix='feedback-summary-probe-live-CPU-processor-') as folder:
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                if Path(name).name != name:
                    raise ValueError('unsafe processor fixture member')
                (Path(folder)/name).write_bytes(bundle.read(name))
        native = TokenAudit(folder)
        # Reference replies exist only in this explicitly scripted CPU server.
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                received.append(body)
                if body == canary():
                    text, tokens = 'ok', 1
                else:
                    extension = json.loads(body['messages'][1]['content'][-1]['text'])
                    first = extension['previous_selected_forecast'] is None
                    text, tokens = json.dumps({'candidate_predictions': {'A': 'unknown', 'B': 'unknown'},
                        'selected_candidate': 'A' if first else 'B',
                        'observed_previous_change': 'not_applicable' if first else 'unknown',
                        'previous_prediction_check': 'not_applicable' if first else 'unknown'}), 64
                count = native(body)
                raw = json.dumps({'model': MODEL, 'choices': [{'message': {'role': 'assistant', 'content': text},
                    'finish_reason': 'stop'}], 'usage': {'prompt_tokens': count, 'completion_tokens': tokens,
                                                       'total_tokens': count+tokens}}).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            config = {'inputs': str(args.inputs), 'input_manifest_sha256': args.input_pin,
                      'started': started, 'port': server.server_port, 'game_python': str(args.game_python),
                      'games': str(args.game_environment/'environment_files')}
            study(config, args.output, token_audit=native)
            replay_effects = []
            def replay(checkpoint, variant):
                name = checkpoint['checkpoint_id']+'-'+variant
                return BridgeEngine(args.game_python, checkpoint['game_id'], config['games'],
                    args.recordings/(name+'-replay'), args.output/(name+'-replay.log'), started+1200,
                    env=dict(environment(), PYTHONPATH=str(ROOT)),
                    on_effect=lambda operation: replay_effects.append(operation))
            result = audit_study(args.output, args.inputs, token_audit=native, replay_factory=replay)
            records = [json.loads(line) for line in (args.output/'transport.jsonl').read_text().splitlines()]
            requests = [r for r in records if r['kind'] == 'HTTP_request']
            if received != [r['body'] for r in requests]:
                raise ValueError('retained requests differ from actual scripted HTTP bodies')
            expected_replay = {name: replay_effects.count(name) for name in ('bootstrap', 'dispatch', 'close')}
            if expected_replay['bootstrap'] < 16 or expected_replay['bootstrap'] != expected_replay['close']:
                raise ValueError('independent replay/reference scorecards not closed')
            verify_inputs(args.inputs, args.input_pin)
            receipt = {'CPU_only': True, 'scripted_responses': True, 'neural_generations': 0,
                       'provider_writes': 0, 'GPU_jobs': 0, 'input_manifest_sha256': args.input_pin,
                       'study': result, 'HTTP_requests': len(requests),
                       'maximum_prompt_tokens': max(r['native_prompt_tokens'] for r in requests),
                       'transport_sha256': sha(args.output/'transport.jsonl'),
                       'CPU_independent_replay_effects': expected_replay,
                       'elapsed_seconds': time.monotonic()-started,
                       'qualification': 'Actual live-worker path with scripted replies; no model performance or live lifecycle certification.'}
            write_new(args.output/'CPU-rehearsal.json', receipt)
            print(json.dumps({k: v for k, v in receipt.items() if k != 'study'}), flush=True)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
            if thread.is_alive():
                raise RuntimeError('scripted CPU server did not stop')


if __name__ == '__main__':
    main()
