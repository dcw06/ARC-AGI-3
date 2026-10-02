# Derived from scripts/rehearse_ws3_questionnaire_v1.py by research/evidence_memory_v1/derive_run.py; edit the derivation, not this file.
"""Connected-path CPU rehearsal: launcher -> supervisor -> worker -> host -> fake server over HTTP -> runner.

Rehearsal uses the live code path with a CPU fake of vLLM's OpenAI server, the fixture tokenizer,
injected GPU identity, a 2 s call timeout and a 3 s idle-verification window (never target evidence).
"""
import argparse
import json
import os
from pathlib import Path
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
OUTPUT_NAME = 'evidence-memory-v1-stage1'


def rehearse(fault='none', seconds=900, workdir=None, root=ROOT):
    workdir = Path(workdir or tempfile.mkdtemp(prefix='ecv-rehearsal-'))
    os.environ.update(EM1S_REHEARSAL='1', CUDA_VISIBLE_DEVICES='')
    from research.evidence_memory_v1.run.launch import run
    started = time.monotonic()
    receipt = run(workdir / 'working' / OUTPUT_NAME, workdir / 'working', started=started, root=root,
                  mode='rehearsal', internal_seconds=seconds, fault=fault)
    return receipt, workdir / 'working' / OUTPUT_NAME


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fault', default='none')
    parser.add_argument('--seconds', type=int, default=900)
    args = parser.parse_args()
    base = Path.home() / 'ecv-rehearsal'
    base.mkdir(exist_ok=True)
    receipt, output = rehearse(args.fault, args.seconds, tempfile.mkdtemp(dir=base))
    outer = json.loads((output / 'control/outer.json').read_bytes()) if (output / 'control/outer.json').exists() else None
    from research.evidence_memory_v1.run.evaluate import evaluate_output
    value = evaluate_output(output, mode='rehearsal', rehearsal_seconds=args.seconds)
    print(json.dumps({'receipt': receipt, 'outer_status': outer and outer['status'], 'outer_error': outer and outer['error'],
                      'evaluation': {k: v for k, v in value.items() if k != 'analysis'}, 'output': str(output)}, indent=1))
    if not outer or outer['status'] != 'study_ended_pending_independent_evaluation':
        for name in ('worker/failure.json', 'worker/host-status.json', 'worker/worker-result.json', 'monitor/failure.json'):
            if (output / name).exists():
                print('==', name, (output / name).read_text()[:1500])
        for log in sorted((output / 'logs').glob('*.json')):
            print('== log', log.name, log.read_text(errors='replace')[-2500:])
