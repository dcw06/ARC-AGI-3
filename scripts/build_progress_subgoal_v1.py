"""Freeze the progress_subgoal_v1 question set into the runtime file (offline; no model, no GPU).

The evaluation partition is built from the evaluation seed, which is never in the repository: pass the file that holds
it (--seed-file, or PSV1_EVALUATION_SEED_FILE). The seed must match the committed SHA-256 in
research/progress_subgoal_v1/evaluation_seed.json, or nothing is built. Every coverage floor must hold on the
evaluation build (the build fails otherwise). Outputs:
- research/progress_subgoal_v1/probes.json: the runner-shaped set (decision partition labelled `withheld`, then
  development), which live mode reads; per-probe shortcut answers (evaluator-only build metadata) are omitted;
- reports/progress_subgoal_v1_probe_summary.json: sizes, schedule and the evaluation coverage report.
A fresh build must be byte-identical (`--check`).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / 'research/progress_subgoal_v1/probes.json'
SUMMARY = ROOT / 'reports/progress_subgoal_v1_probe_summary.json'
SEED_RECORD = ROOT / 'research/progress_subgoal_v1/evaluation_seed.json'


def read_seed(seed_file):
    seed = Path(seed_file).read_text(encoding='ascii').strip()
    record = json.loads(SEED_RECORD.read_bytes())
    if len(seed) != 32 or any(c not in '0123456789abcdef' for c in seed):
        raise ValueError('the evaluation seed must be 32 lowercase hex characters (128 bits)')
    if hashlib.sha256(seed.encode()).hexdigest() != record['sha256']:
        raise ValueError('the seed does not match the committed evaluation-seed hash')
    return seed


def build(seed):
    from research.progress_subgoal_v1 import probes as P, questions as Q
    evaluation = Q.build('evaluation', seed=seed)
    report = Q.coverage(evaluation['probes'], 'evaluation')  # raises below any floor
    development = Q.build('development')
    frozen = P.runner_shape(evaluation, development)
    for p in frozen['probes']:
        p.pop('shortcut_answers', None)  # build metadata; `shortcuts_correct` (used by the evaluator) is kept
    return frozen, report


def outputs(seed):
    from research.progress_subgoal_v1 import probes as P
    frozen, report = build(seed)
    raw = P.encode(frozen)
    summary = {'version': frozen['version'], 'probe_set_sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
               'evaluation_seed_sha256': json.loads(SEED_RECORD.read_bytes())['sha256'],
               'arms': frozen['conditions'], 'probes': len(frozen['probes']), 'contexts': len(frozen['contexts']),
               'scheduled_calls': sum(len(b['probe_ids']) for b in frozen['schedule']),
               'calls_by_phase': {f"{b['partition']}/{b['pass']}": len(b['probe_ids']) for b in frozen['schedule']},
               'evaluation_coverage': report}
    return {OUTPUT: raw, SUMMARY: (json.dumps(summary, sort_keys=True, indent=1) + '\n').encode()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed-file', default=os.environ.get('PSV1_EVALUATION_SEED_FILE'))
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if not args.seed_file:
        raise SystemExit('the evaluation seed file is required (--seed-file or PSV1_EVALUATION_SEED_FILE)')
    files = outputs(read_seed(args.seed_file))
    if args.check:
        stale = [str(p.relative_to(ROOT)) for p, raw in files.items() if not p.exists() or p.read_bytes() != raw]
        if stale:
            raise SystemExit(f'frozen files differ from a fresh build: {stale}')
        print('question set matches a fresh build:', hashlib.sha256(files[OUTPUT]).hexdigest())
    else:
        for path, raw in files.items():
            path.write_bytes(raw)
        print(json.dumps({'bytes': len(files[OUTPUT]), 'sha256': hashlib.sha256(files[OUTPUT]).hexdigest()}))
