"""Bounded offline CPU rehearsal with scripted HTTP replies, never neural inference.

Run in a Linux network namespace containing only an enabled loopback interface.
Local game actions and local scorecards are used and counted, including replay.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
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
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from research.initial_geometry_assistance_v1.live_resources import HardDeadline, Processes, environment
from research.initial_geometry_assistance_v1.live_runtime import verify_inputs
from research.initial_geometry_assistance_v1.model_io import TokenAudit, validate_reply
from research.recent_feedback_v1.audit import audit_episode
from research.recent_feedback_v1.episodes import episode
from research.recent_feedback_v1.interface import VARIANTS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('inputs', 'game-environment', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--input-pin', required=True)
    parser.add_argument('--game-pin', required=True)
    args = parser.parse_args()
    # /sys may still be mounted from the host namespace. /proc/net resolves
    # through the current process's network namespace instead.
    interfaces = ({line.split(':', 1)[0].strip() for line in Path('/proc/net/dev').read_text().splitlines()[2:]
                   if ':' in line} if sys.platform == 'linux' else set())
    if sys.platform != 'linux' or interfaces != {'lo'}:
        raise ValueError('requires isolated Linux network namespace with loopback only')
    os.environ.update(CUDA_VISIBLE_DEVICES='', NVIDIA_VISIBLE_DEVICES='void', HF_HUB_OFFLINE='1',
                      TRANSFORMERS_OFFLINE='1', MPLBACKEND='Agg')
    verify_inputs(args.inputs, args.input_pin)
    verify_game_environment(args.game_environment, args.game_pin)
    cases = json.loads((args.inputs/'cases.json').read_bytes())['cases']
    args.output.mkdir(parents=True, exist_ok=False)
    import importlib.metadata as metadata
    import torch
    torch.set_num_threads(2)
    started = time.monotonic()
    deadline = started+900
    watchdog = HardDeadline(deadline)
    watchdog.start()
    resources = Processes(watchdog)
    temporary = Path(tempfile.mkdtemp(prefix='recent-feedback-CPU-'))
    env = dict(environment(), PYTHONPATH=str(ROOT), CUDA_VISIBLE_DEVICES='', NVIDIA_VISIBLE_DEVICES='void')
    server = None
    successful = False
    try:
        log = args.output/'install.log'
        python = temporary/'venv/bin/python'
        resources.command([sys.executable, '-m', 'venv', '--without-pip', str(temporary/'venv')],
                          log, deadline, env, 'CPU game interpreter')
        resources.command([sys.executable, '-m', 'pip', '--python', str(python), 'install', '--no-index',
            '--no-cache-dir', '--require-hashes', '--only-binary=:all:', '--find-links', str(args.game_environment/'wheels'),
            '-r', str(args.game_environment/'game_requirements.lock')], log, deadline, env, 'CPU offline install')
        archive = ROOT/'evidence/phase4-multimodal-preflight-v3-processor-inputs.zip'
        if sha(archive) != 'af5aebbe4761d80b50effd5758fbadac13f80edacbf37a1f0591baa473c913d1':
            raise ValueError('processor fixture changed')
        checkpoint = temporary/'processor'
        checkpoint.mkdir()
        with zipfile.ZipFile(archive) as bundle:
            for name in bundle.namelist():
                if Path(name).name != name:
                    raise ValueError('unsafe processor member')
                (checkpoint/name).write_bytes(bundle.read(name))
        native = TokenAudit(checkpoint)
        received = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_POST(self):
                request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                received.append(request)
                meta = json.loads(request['messages'][1]['content'][0]['text'])
                action = meta['current_legal_actions'][0]
                answer = json.dumps({'action_id': action, 'action_data': {'x': 31, 'y': 31} if action == 6 else {},
                                     'predicted_visible_change': 'unknown'})
                count = native(request)
                raw = json.dumps({'model': request['model'], 'choices': [{'message': {'role': 'assistant', 'content': answer},
                    'finish_reason': 'stop'}], 'usage': {'prompt_tokens': count, 'completion_tokens': 32,
                                                       'total_tokens': count+32}}).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        ids = [f"{c['case_id']}/{v}/{i}" for c in cases for v in VARIANTS for i in range(4)]
        plan = [{'id': key, 'kind': 'policy', 'method': 'POST', 'path': '/v1/chat/completions',
                 'timeout_seconds': 30, 'max_issues': 1} for key in ids]
        clock = Clock({'internal_seconds': 900, 'admission_cutoff_seconds': 850}, started)
        ledger = Ledger(plan, len(plan), clock)
        client = Client('127.0.0.1', server.server_port, ledger, clock, 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8')
        rows = []
        for case in cases:
            for variant in VARIANTS:
                name = case['case_id']+'-'+variant
                trace, issued = [], []
                def complete(request):
                    request_id = f"{case['case_id']}/{variant}/{len(issued)}"
                    issued.append(request)
                    status, raw = client.call(request_id, request)
                    if status != 200:
                        raise ValueError('scripted server did not return HTTP 200')
                    return validate_reply(request, json.loads(raw), native(request))
                engine = BridgeEngine(python, case['game_id'], args.game_environment/'environment_files',
                    temporary/(name+'-play'), args.output/(name+'-play.log'), deadline, env=env)
                episode(case, variant, engine, complete, trace.append,
                        model='Qwen/Qwen3-VL-30B-A3B-Instruct-FP8',
                        deadline=deadline, cap=4)
                write_new(args.output/(name+'-events.json'), trace)
                if issued != [e['body'] for e in trace if e['kind'] == 'request']:
                    raise ValueError('journal and sent requests differ')
                replay = BridgeEngine(python, case['game_id'], args.game_environment/'environment_files',
                    temporary/(name+'-replay'), args.output/(name+'-replay.log'), deadline, env=env)
                rows.append(audit_episode(case, variant, trace, model='Qwen/Qwen3-VL-30B-A3B-Instruct-FP8',
                                          cap=4, replay_engine=replay))
        if len(received) != 48 or ledger.summary()['issued'] != 48 or len(rows) != 12:
            raise ValueError('scripted call/episode count differs')
        # Direct order is checked against each persisted request, not just totals.
        recorded = []
        for case in cases:
            for variant in VARIANTS:
                trace = json.loads((args.output/(case['case_id']+'-'+variant+'-events.json')).read_bytes())
                recorded.extend(e['body'] for e in trace if e['kind'] == 'request')
        if received != recorded:
            raise ValueError('actual scripted server request order differs')
        successful = True
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        cleanup = resources.stop(deadline)
        shutil.rmtree(temporary)
        watchdog.close()
        if not cleanup['groups_absent'] or cleanup['error'] or cleanup['interrupted'] or time.monotonic() >= deadline:
            raise ValueError('CPU process cleanup/deadline failed')
        write_new(args.output/'lifecycle.json', {'passed': successful, 'process_cleanup': cleanup,
            'temporary_environment_removed': not temporary.exists(), 'elapsed_seconds': time.monotonic()-started})
    receipt = {'passed': successful, 'episodes': len(rows), 'engine_replays': len(rows),
        'scripted_HTTP_requests': len(received), 'policy_dispatches': sum(r['dispatches'] for r in rows),
        'bootstrap_resets': 12, 'replay_dispatches': sum(r['dispatches'] for r in rows), 'replay_bootstrap_resets': 12,
        'local_scorecards_including_replay': 24, 'new_neural_model_requests': 0, 'GPU_jobs': 0,
        'online_game_calls': 0, 'rows': rows,
        'versions': {n: metadata.version(n) for n in ('torch', 'transformers', 'pillow')},
        'qualification': 'CPU fixtures, cap 4; does not certify policy effectiveness, target CUDA/vLLM or live lifecycle.'}
    write_new(args.output/'receipt.json', receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k != 'rows'}), flush=True)


if __name__ == '__main__':
    main()
