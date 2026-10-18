"""CPU-only two-action episodes plus independent real-engine replay.

Uses a scripted first-legal-action stub. No model results or scientific outcome
claims. The caller must disable networking at OS level as well.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import sys
import time

os.environ.update(MPLBACKEND='Agg', CUDA_VISIBLE_DEVICES='', NVIDIA_VISIBLE_DEVICES='void')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.initial_geometry_assistance_v1.audit import audit_episode
from research.initial_geometry_assistance_v1.engine import OfflineEngine, verify_game_environment
from research.initial_geometry_assistance_v1.episodes import episode
from research.initial_geometry_assistance_v1.geometry import canonical, digest
from research.initial_geometry_assistance_v1.policy import request_for


def no_network(*args, **kwargs):
    raise PermissionError('CPU geometry rehearsal: network forbidden')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--game-environment', type=Path, required=True)
    parser.add_argument('--game-receipt-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    socket.socket.connect = socket.create_connection = no_network
    started = time.monotonic()
    manifest_raw = (args.inputs/'manifest.json').read_bytes()
    if hashlib.sha256(manifest_raw).hexdigest() != args.manifest_sha256:
        raise ValueError('independently supplied input manifest differs')
    manifest = json.loads(manifest_raw)
    if {p.name for p in args.inputs.iterdir()} != set(manifest['files']) | {'manifest.json'}:
        raise ValueError('input file inventory differs')
    for name, pin in manifest['files'].items():
        if Path(name).name != name or hashlib.sha256((args.inputs/name).read_bytes()).hexdigest() != pin:
            raise ValueError('input file differs: ' + name)
    repo = Path(__file__).resolve().parents[1]
    protocol = json.loads((repo/'research/initial_geometry_assistance_v1/protocol.json').read_bytes())
    if hashlib.sha256((repo/'research/initial_geometry_assistance_v1/protocol.json').read_bytes()).hexdigest() != manifest['protocol_sha256']:
        raise ValueError('protocol changed since preparation')
    versions = {n: importlib.metadata.version(n) for n in ('arc-agi', 'arcengine', 'numpy')}
    if versions != {'arc-agi': '0.9.8', 'arcengine': '0.9.3', 'numpy': '2.4.4'}:
        raise ValueError('pinned game interpreter differs')
    game = verify_game_environment(args.game_environment, args.game_receipt_sha256)
    cases = json.loads((args.inputs/'cases.json').read_bytes())['cases']
    if [(c['case_id'], c['game_id'], c['order']) for c in cases] != [
            (c['case_id'], c['game_id'], c['order']) for c in protocol['cases']]:
        raise ValueError('schedule differs')
    args.output.mkdir(exist_ok=False)
    rows, traces, maximum_request_bytes = [], {}, 0

    def stub(request):
        nonlocal maximum_request_bytes
        maximum_request_bytes = max(maximum_request_bytes, len(canonical(request)))
        meta = json.loads(request['messages'][1]['content'][0]['text'])
        action_id = meta['current_legal_actions'][0]
        return json.dumps({'action_id': action_id, 'action_data': {'x': 31, 'y': 31} if action_id == 6 else {},
                           'predicted_visible_change': 'unknown'})

    for case in cases:
        for arm in case['order']:
            name = case['case_id']+'-'+arm
            events = []
            with (args.output/(name+'.jsonl')).open('xb') as stream:
                def sink(event):
                    stream.write(canonical(event)); stream.flush(); os.fsync(stream.fileno())
                    events.append(event)
                engine = OfflineEngine(case['game_id'], args.game_environment/'environment_files', args.output/name)
                episode(case, arm, engine, stub, sink, model=protocol['policy']['model'],
                        deadline=min(started+480, time.monotonic()+60), cap=2)
            replay = OfflineEngine(case['game_id'], args.game_environment/'environment_files', args.output/(name+'-replay'))
            rows.append(audit_episode(case, arm, events, model=protocol['policy']['model'], cap=2, replay_engine=replay))
            traces[name+'.jsonl'] = hashlib.sha256((args.output/(name+'.jsonl')).read_bytes()).hexdigest()
    # Exercise the maximum history request for every arm, without engine/model calls.
    # This checks construction size only, not native tokenizer/template acceptance.
    maximum_history_bytes = 0
    for case in cases:
        obs = {'grid': case['grid'], 'state': 'NOT_FINISHED', 'levels_completed': 0, 'legal_actions': [1, 6]}
        history = [{'step': i, 'before': obs, 'after': obs, 'action': {'action_id': 1, 'action_data': {}}} for i in range(23)]
        for arm in case['order']:
            body = request_for(obs, case['geometry'][arm], obs, history, 23, protocol['policy']['model'])
            maximum_history_bytes = max(maximum_history_bytes, len(canonical(body)))
    receipt = {'schema': 'initial_geometry_CPU_rehearsal_v1', 'scientific_results': False, 'real_model_calls': 0,
               'GPU_jobs': 0, 'online_game_calls': 0, 'online_scorecards': 0, 'leaderboard_submissions': 0,
               'engine_versions': versions, **game, 'input_manifest_sha256': args.manifest_sha256,
               'per_episode_action_cap_for_this_rehearsal_only': 2, 'episodes': len(rows),
               'starting_board_checks': len(rows), 'independent_engine_replay_checks': len(rows),
               'rehearsal_dispatches': sum(r['dispatches'] for r in rows), 'bootstrap_resets': len(rows),
               'replay_dispatches': sum(r['dispatches'] for r in rows), 'replay_bootstrap_resets': len(rows),
               'local_scorecards_including_replay': 2*len(rows),
               'maximum_rehearsal_request_bytes': maximum_request_bytes,
               'maximum_synthetic_history_request_bytes': maximum_history_bytes,
               'native_Qwen_template_and_token_audit': 'pending',
               'rows': rows, 'trace_sha256': traces, 'elapsed_seconds': time.monotonic()-started,
               'lifecycle_certified': False, 'live_launch_authorized': False}
    if receipt['elapsed_seconds'] >= 480:
        raise TimeoutError('CPU rehearsal budget exceeded')
    (args.output/'receipt.json').write_bytes(canonical(receipt))
    print(json.dumps({k: v for k, v in receipt.items() if k not in ('rows', 'trace_sha256')}))


if __name__ == '__main__':
    main()
