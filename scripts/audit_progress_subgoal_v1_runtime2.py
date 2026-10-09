"""Exact prompt-token audit of the successor's actual schedule with the pinned tokenizer (CPU only, local files only).

Every scheduled request (all 5,852 calls, built from the frozen question set by the unchanged modules) is tokenized
with the unchanged research.progress_subgoal_v1.token_audit.audit (the chat template exactly as the reviewed
service admitted requests). The tokenizer files must match the pinned tokenizer manifest byte for byte, and the
tokenizer runtime must be transformers 4.57.6 / tokenizers 0.22.2.

Writes:
- research/progress_subgoal_v1_runtime2/token-audit.json: the compact audit the runtime binds (prompt tokens in call
  order, bound to the request digest and the question-set hash); the controller checks every server-reported
  prompt-token count against it;
- reports/progress_subgoal_v1_runtime2_budget.json: planning scenarios from the exact tokens (estimates, never an
  authorization or ceiling).

Usage (pinned tokenizer environment): python scripts/audit_progress_subgoal_v1_runtime2.py --tokenizer DIR
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TOKENIZER_MANIFEST = 'certification/phase4_integrated_v2/tokenizer_manifest.json'
AUDIT = 'research/progress_subgoal_v1_runtime2/token-audit.json'
BUDGET = 'reports/progress_subgoal_v1_runtime2_budget.json'
# Protocol v2 section 10: the least-squares fit to evidence_comprehension_v3's 6,054 measured cache-disabled calls.
FIT = {'intercept_seconds': 0.03944, 'per_prompt_token_seconds': 1.4210e-5, 'per_completion_token_seconds': 0.006418,
       'completion_tokens_assumed': 20}


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=1) + '\n').encode()


def verify_tokenizer(folder):
    manifest = json.loads((ROOT / TOKENIZER_MANIFEST).read_bytes())
    observed = {}
    for name, row in manifest['files'].items():
        raw = (Path(folder) / name).read_bytes()
        observed[name] = hashlib.sha256(raw).hexdigest()
        if len(raw) != row['bytes'] or observed[name] != row['sha256']:
            raise ValueError('tokenizer byte drift: ' + name)
    return manifest, observed


def call_seconds(prompt_tokens):
    return (FIT['intercept_seconds'] + FIT['per_prompt_token_seconds'] * prompt_tokens
            + FIT['per_completion_token_seconds'] * FIT['completion_tokens_assumed'])


def budget(rows, protocol):
    """Where the frozen admission rule would stop the schedule under stated assumptions (never a prediction)."""
    limits = protocol['limits']
    bound = protocol['experiment']['per_call_bound_seconds']
    last_start = limits['admission_cutoff_seconds'] - bound
    evaluation = [r for r in rows if r['phase'].startswith('withheld')]
    scenarios = []
    for overhead in (300, 540, 961, 1540):
        for slowdown in (1.0, 1.5, 2.0):
            t, finished_evaluation, last_index = overhead, None, None
            for r in rows:
                if t > last_start:
                    break
                t += slowdown * call_seconds(r['prompt_tokens'])
                last_index = r['index']
                if r['index'] == evaluation[-1]['index']:
                    finished_evaluation = round(t, 1)
            scenarios.append({'pre_questionnaire_overhead_seconds': overhead, 'call_time_factor': slowdown,
                              'evaluation_calls_end_at_seconds': finished_evaluation,
                              'evaluation_complete_before_admission_closes': finished_evaluation is not None,
                              'calls_started_before_admission_closes': (last_index + 1) if last_index is not None else 0,
                              'all_5852_calls_started': last_index == rows[-1]['index']})
    return {'status': 'estimates_not_authorization', 'gpu_used': False, 'model_calls': 0,
            'method': {'call_seconds': 'intercept + per-prompt-token x exact prompt tokens + per-completion-token x 20',
                       'fit': FIT, 'fit_source': 'reports/progress_subgoal_v1_protocol_v2.md section 10'},
            'admission_rule': {'admission_cutoff_seconds': limits['admission_cutoff_seconds'],
                               'per_call_bound_seconds': bound, 'last_permitted_start_seconds': last_start},
            'exact_evaluation_prompt_tokens': sum(r['prompt_tokens'] for r in evaluation),
            'exact_development_prompt_tokens': sum(r['prompt_tokens'] for r in rows) - sum(
                r['prompt_tokens'] for r in evaluation),
            'fitted_evaluation_call_seconds': round(sum(call_seconds(r['prompt_tokens']) for r in evaluation), 1),
            'fitted_all_call_seconds': round(sum(call_seconds(r['prompt_tokens']) for r in rows), 1),
            'overheads_considered': {
                '300': 'assumption only', '540': 'whole first-cell lifecycle of the verified runtime run (131 '
                'requests, prompts up to 36k tokens), retained in its published aggregate; an upper reference for '
                'its pre-research overhead, not a measurement of it',
                '961': 'protocol v2 measured overhead of the old runtime', '1540': 'protocol v2 old runtime with allowances'},
            'scenarios': scenarios,
            'note': 'A cut session is incomplete; admission control, not this estimate, protects the deadline. The '
                    'verified runtime adds model-tree hashing and offline installation before startup; their '
                    'durations were not published per phase.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer', required=True, type=Path)
    args = parser.parse_args()
    versions = {n: importlib.metadata.version(n) for n in ('transformers', 'tokenizers')}
    if versions != {'transformers': '4.57.6', 'tokenizers': '0.22.2'}:
        raise ValueError('use the pinned tokenizer runtime: ' + str(versions))
    manifest, observed = verify_tokenizer(args.tokenizer)
    from transformers import AutoTokenizer
    from research.action_effect_history_v1.service import request_hash
    from research.progress_subgoal_v1 import questions as Q
    from research.progress_subgoal_v1.token_audit import audit as unchanged_audit, CONTEXT, PROMPT_CEILING
    from research.progress_subgoal_v1_runtime2 import questionnaire as QN
    tokenizer = AutoTokenizer.from_pretrained(str(args.tokenizer), local_files_only=True, trust_remote_code=False)
    frozen, digest, schedule = QN.scheduled(ROOT)
    report = unchanged_audit(tokenizer, frozen)
    rows = report['requests']
    hashes = [request_hash(row[4]) for row in schedule]
    if [(r['index'], r['probe_id']) for r in rows] != [(n, row[3]) for n, row in enumerate(schedule)]:
        raise ValueError('audit rows are not the scheduled calls in order')
    for r, h in zip(rows, hashes):
        r['request_sha256'] = h
    compact_answers = {f: max(len(tokenizer.encode(json.dumps({'answer': a}, separators=(',', ':')),
                                                   add_special_tokens=False)) + 1 for a in answers)
                       for f, answers in Q.ANSWERS.items()}
    caps = dict(report['max_tokens_check'])
    caps['all_cover'] = all(c['covers'] for c in report['max_tokens_check'].values())
    caps['longest_valid_answer_tokens_compact'] = compact_answers
    passed = report['summary']['all_within_limits'] and caps['all_cover']
    protocol = json.loads((ROOT / 'research/progress_subgoal_v1_runtime2/protocol.json').read_bytes())
    audit = {'schema': 'progress_subgoal_v1_runtime2_token_audit_v1', 'probe_set_sha256': digest,
             'request_digest': QN.request_digest(hashes), 'scheduled_calls': len(rows),
             'distinct_requests': report['summary']['distinct_requests'],
             'prompt_tokens': [r['prompt_tokens'] for r in rows], 'max_tokens': Q.MAX_TOKENS,
             'limits': {'prompt_token_ceiling': PROMPT_CEILING, 'context_tokens': CONTEXT},
             'summary': report['summary'], 'max_tokens_check': caps,
             'tokenizer': {'manifest': TOKENIZER_MANIFEST, 'repo': manifest['repo'], 'revision': manifest['revision'],
                           'files_sha256_verified': observed}, 'versions': versions,
             'passed': passed, 'model_calls': 0, 'gpu_used': False}
    (ROOT / AUDIT).write_bytes(encode(audit))
    (ROOT / BUDGET).write_bytes(encode(budget(rows, protocol)))
    print(json.dumps({'passed': passed, **{k: report['summary'][k] for k in (
        'scheduled_calls', 'distinct_requests', 'prompt_tokens_scheduled', 'max_prompt_tokens', 'all_within_limits',
        'caps_cover')}}, indent=1))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
