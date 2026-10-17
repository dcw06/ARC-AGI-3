"""Local development comparison; --plan performs no model load or inference.

The execute path is Linux-only and uses existing owned-process-group cleanup.
This is not a Kaggle launcher or authority to spend GPU compute.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.object_discovery_boundaries_v1.granularity import condition, levels, MODELS
from research.object_discovery_boundaries_v1.granularity_worker import inputs_for, write_json
from research.object_discovery_boundaries_v1.granularity_runtime import (
    verify_sources, verify_checkpoint, verify_environment, load_backend, file_sha)


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=MODELS, required=True)
    parser.add_argument('--mode', choices=('seeded','automatic'), required=True)
    parser.add_argument('--granularity', required=True)
    parser.add_argument('--inputs', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--source')
    parser.add_argument('--checkpoint')
    parser.add_argument('--checkpoint-receipt')
    parser.add_argument('--runtime-lock')
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--device', choices=('cpu','cuda'), default='cpu')
    parser.add_argument('--seconds', type=int, default=1200)
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--deadline', type=float, help=argparse.SUPPRESS)
    return parser.parse_args()


def main():
    args = arguments()
    level = int(args.granularity) if args.model == 'semantic_sam_l' else float(args.granularity)
    policy = condition(args.model, args.mode, level)
    inputs_for(args.inputs)
    if args.plan:
        if args.execute or args.worker:
            raise ValueError('planning cannot execute')
        output = Path(args.output)
        output.mkdir(parents=True, exist_ok=False)
        write_json(output/'policy.json', policy)
        write_json(output/'readiness.json', dict(state='development_plan_only',
            inference_executed=False, models_loaded=False, Kaggle_calls=0,
            outstanding=['checkpoint acquisition/byte verification', 'isolated dependency lock and real model-load qualification',
                         'GPU image qualification and exact launch review if GPU compute is proposed'],
            declared_separate_levels=list(levels(args.model))))
        print('Plan written; no model loaded or inference executed.')
        return
    if not args.execute or not 1 <= args.seconds <= 3300 or sys.platform != 'linux':
        raise ValueError('explicit Linux execution with a 1..3300-second worker budget required')
    for key in ('source','checkpoint','checkpoint_receipt','runtime_lock'):
        if getattr(args,key) is None:
            raise ValueError('execution requires --'+key.replace('_','-'))
    if args.worker:
        if args.deadline is None or time.monotonic() >= args.deadline:
            raise TimeoutError('missing or expired parent deadline')
        os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', MPLBACKEND='Agg',
                          HF_HUB_DISABLE_TELEMETRY='1')
        if args.device == 'cpu':
            os.environ.update(CUDA_VISIBLE_DEVICES='', NVIDIA_VISIBLE_DEVICES='void')
        def refuse(*unused, **kwargs):
            raise PermissionError('offline segmentation worker')
        socket.socket.connect = socket.create_connection = refuse
        sources = verify_sources(args.source,args.model)
        checkpoint = verify_checkpoint(args.checkpoint,args.checkpoint_receipt,args.model)
        environment = verify_environment(args.runtime_lock)
        write_json(Path(args.output)/'execution-inputs.json', dict(
            policy=policy, source_repository=sources['repository'], source_revision=sources['revision'],
            source_pins_sha256=file_sha(ROOT/'research/object_discovery_boundaries_v1/granularity_sources.json'),
            checkpoint=checkpoint, checkpoint_receipt_sha256=file_sha(args.checkpoint_receipt),
            runtime_versions=environment, runtime_lock_sha256=file_sha(args.runtime_lock),
            input_manifest_sha256=file_sha(Path(args.inputs)/'manifest.json'), device=args.device,
            implementation_sha256={str(p.relative_to(ROOT)):file_sha(p) for p in
                [Path(__file__).resolve(),*(ROOT/'research/object_discovery_boundaries_v1').glob('granularity*.py')]}))
        backend = load_backend(args.source,args.checkpoint,args.model,args.device)
        from research.object_discovery_boundaries_v1.granularity_worker import run_frames
        result = run_frames(backend,args.inputs,Path(args.output)/'frames',policy,args.deadline)
        write_json(Path(args.output)/'worker-result.json', result)
        if time.monotonic() >= args.deadline:
            raise TimeoutError('worker result write overrun')
        return
    if args.deadline is not None:
        raise ValueError('deadline is parent-owned')
    from certification.direct_publisher_smoke_v1.install import InstallationProcesses
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    deadline = time.monotonic()+args.seconds
    owner = InstallationProcesses()
    completed = False
    try:
        argv = [args.python, '-I', str(Path(__file__).resolve()), '--worker', '--execute',
                '--deadline', str(deadline)]
        for key in ('model','mode','granularity','inputs','source','checkpoint','checkpoint_receipt','runtime_lock','device','seconds'):
            argv.extend(['--'+key.replace('_','-'), str(getattr(args,key))])
        argv.extend(['--output',str(output)])
        # A file log avoids pipe/thread startup and inherited-pipe EOF hangs.
        owner.command(argv,output/'worker.log',deadline,dict(os.environ),'granularity segmentation')
        completed = True
    finally:
        cleanup = owner.stop(deadline)
        write_json(output/'process-cleanup.json',cleanup)
    if not completed or not cleanup['groups_absent'] or cleanup['error'] or cleanup['interrupted']:
        raise RuntimeError('worker/process cleanup not complete')
    if time.monotonic() >= deadline:
        raise TimeoutError('parent cleanup/finalization overrun')
    # External launch review/lifecycle certification is deliberately not claimed.
    print('Development worker returned; process groups absent. No Kaggle certification supplied.')


if __name__ == '__main__':
    main()
