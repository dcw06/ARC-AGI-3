"""Connected CPU HTTP -> shared episode -> isolated real game -> replay check.

Replies are scripted, not neural model results. Only loopback HTTP is used;
run this in an OS network namespace with only its loopback interface enabled.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import zipfile

os.environ.update(CUDA_VISIBLE_DEVICES='', NVIDIA_VISIBLE_DEVICES='void', HF_HUB_OFFLINE='1',
                  TRANSFORMERS_OFFLINE='1', MPLBACKEND='Agg')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.recent_feedback_v1.audit import audit_episode
from research.initial_geometry_assistance_v1.engine import verify_game_environment
from research.initial_geometry_assistance_v1.engine_bridge import BridgeEngine
from research.recent_feedback_v1.live_evaluation import audit_transport, lines
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from research.initial_geometry_assistance_v1.live_resources import environment
from research.recent_feedback_v1.live_runtime import verify_inputs
from research.recent_feedback_v1.live_worker import MODEL, canary, study
from research.initial_geometry_assistance_v1.model_io import TokenAudit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--input-pin', required=True)
    parser.add_argument('--game-environment', type=Path, required=True)
    parser.add_argument('--game-pin', required=True)
    parser.add_argument('--game-python', type=Path, required=True)
    parser.add_argument('--competition-input', type=Path,
                        help='CPU fixture of the provider input root for the mounted-wheel successor')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    verify_inputs(args.inputs, args.input_pin)
    if args.competition_input is None:
        verify_game_environment(args.game_environment, args.game_pin)
    else:
        from research.initial_geometry_assistance_v1.game_wheels import verify_mounted_game
        runtime = json.loads((ROOT/'runtime.json').read_bytes())
        verify_mounted_game(args.game_environment, args.game_pin, runtime['game_wheel_source'],
                            base=args.competition_input)
    archive = ROOT/'evidence/phase4-multimodal-preflight-v3-processor-inputs.zip'
    if sha(archive) != 'af5aebbe4761d80b50effd5758fbadac13f80edacbf37a1f0591baa473c913d1':
        raise ValueError('processor archive pin differs')
    import torch
    import importlib.metadata as metadata
    torch.set_num_threads(2)
    args.output.mkdir(exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='geometry-native-CPU-') as folder:
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                if Path(name).name != name:
                    raise ValueError('processor member path')
                (Path(folder)/name).write_bytes(bundle.read(name))
        native = TokenAudit(folder)
        request_count = [0]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                count = native(body)
                request_count[0] += 1
                if body == canary():
                    text = 'ok'
                else:
                    meta = json.loads(body['messages'][1]['content'][0]['text'])
                    action = meta['current_legal_actions'][0]
                    text = json.dumps({'action_id': action, 'action_data': {'x': 31, 'y': 31} if action == 6 else {},
                                       'predicted_visible_change': 'unknown'})
                raw = json.dumps({'model': MODEL, 'choices': [{'message': {'role': 'assistant', 'content': text},
                                                                'finish_reason': 'stop'}],
                                  'usage': {'prompt_tokens': count, 'completion_tokens': 32,
                                            'total_tokens': count+32}}).encode()
                # Canary cap is 16, so use one scripted completion token there.
                if body == canary():
                    value = json.loads(raw)
                    value['usage'].update(completion_tokens=1, total_tokens=count+1)
                    raw = json.dumps(value).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        started = time.monotonic()
        try:
            study({'cases': str(args.inputs/'cases.json'), 'started': started, 'port': server.server_port,
                   'game_python': str(args.game_python), 'games': str(args.game_environment/'environment_files')},
                  args.output, token_audit=native, cap=24, headroom=0)
        finally:
            server.shutdown()
            server.server_close()
        cases = json.loads((args.inputs/'cases.json').read_bytes())['cases']
        expected, rows = {'canary': canary()}, []
        for case in cases:
            for arm in case['order']:
                name = case['case_id']+'-'+arm
                events = lines(args.output/(name+'.jsonl'))
                replay = BridgeEngine(args.game_python, case['game_id'], args.game_environment/'environment_files',
                                      args.output/(name+'-replay'), args.output/(name+'-replay.log'), time.monotonic()+60,
                                      env=dict(environment(), PYTHONPATH=str(ROOT)))
                rows.append(audit_episode(case, arm, events, model=MODEL, cap=24, replay_engine=replay))
                for event in events:
                    if event['kind'] == 'request':
                        expected[f"{case['case_id']}/{arm}/{event['step']}"] = event['body']
        transport, effects = audit_transport(lines(args.output/'transport.jsonl'), expected, token_audit=native)
        if len(transport) != request_count[0] or len(transport) != 289:
            raise ValueError('connected HTTP count differs')
        receipt = {'schema': 'recent_feedback_connected_CPU_rehearsal_v1', 'passed': True,
                   'real_model_generations': 0, 'GPU_jobs': 0, 'scripted_HTTP_completions': len(transport),
                   'episodes': len(rows), 'independent_engine_replays': sum(r['engine_replayed'] for r in rows),
                   'offline_dispatches': sum(r['dispatches'] for r in rows), 'bootstrap_resets': 12,
                   'replay_dispatches': sum(r['dispatches'] for r in rows), 'replay_bootstrap_resets': 12,
                   'local_scorecards_including_replay': 24, 'online_game_calls': 0, 'online_scorecards': 0,
                   'input_manifest_sha256': args.input_pin, 'game_receipt_sha256': args.game_pin,
                   'versions': {n: metadata.version(n) for n in ('torch', 'transformers', 'pillow')},
                   'elapsed_seconds': time.monotonic()-started,
                   'qualification': 'Actual engine in isolated pinned interpreter, actual absolute-deadline HTTP, native CPU processor; scripted replies only. Does not certify live vLLM, CUDA or provider lifecycle.'}
        write_new(args.output/'connected-receipt.json', receipt)
        print(json.dumps(receipt))


if __name__ == '__main__':
    main()
