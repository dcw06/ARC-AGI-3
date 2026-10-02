"""Exact prompt-token audit for progress_subgoal_v1 (no model calls; run with the pinned tokenizer environment).

The requests come from `research.progress_subgoal_v1.probes.scheduled_requests` (every scheduled call, in call
order). `audit(tokenizer)` applies the tokenizer's chat template exactly as the reviewed service admits requests
(`apply_chat_template(messages, tokenize=True, add_generation_prompt=True, truncation=False,
**chat_template_kwargs)`, as in scripts/audit_ws3_questionnaire_tokens.py) and checks every request against the
reviewed limits (prompt <= 60,000 tokens; prompt + max_tokens <= 65,536) and every family's longest valid answer
against max_tokens.

Usage (pinned transformers environment): python -m research.progress_subgoal_v1.token_audit --tokenizer PATH --out FILE
"""
import argparse
import json
from pathlib import Path

from research.progress_subgoal_v1 import probes as P, questions as Q

PROMPT_CEILING, CONTEXT = 60000, 65536


def audit(tokenizer, frozen=None):
    caps = {}
    for family, answers in Q.ANSWERS.items():
        longest = max(len(tokenizer.encode(json.dumps({'answer': a}, indent=4), add_special_tokens=False)) + 1
                      for a in answers)
        caps[family] = {'longest_valid_answer_tokens_pretty': longest, 'max_tokens': Q.MAX_TOKENS,
                        'covers': Q.MAX_TOKENS >= longest}
    rows, seen = [], {}
    for r in P.scheduled_requests(frozen):
        if r['request_sha256'] not in seen:  # a question asked in both passes is tokenized once
            ids = tokenizer.apply_chat_template(r['messages'], tokenize=True, add_generation_prompt=True,
                                                truncation=False, **r['chat_template_kwargs'])
            seen[r['request_sha256']] = len(ids)
        n = seen[r['request_sha256']]
        rows.append({'index': r['index'], 'probe_id': r['probe_id'], 'phase': r['phase'], 'condition': r['condition'],
                     'family': r['family'], 'prompt_tokens': n, 'max_tokens': r['max_tokens'],
                     'within_limits': n <= PROMPT_CEILING and n + r['max_tokens'] <= CONTEXT})
    by_phase = {}
    for row in rows:
        phase = by_phase.setdefault(row['phase'], {'calls': 0, 'prompt_tokens': 0, 'max_prompt_tokens': 0})
        phase['calls'] += 1
        phase['prompt_tokens'] += row['prompt_tokens']
        phase['max_prompt_tokens'] = max(phase['max_prompt_tokens'], row['prompt_tokens'])
    summary = {'scheduled_calls': len(rows), 'distinct_requests': len(seen),
               'prompt_tokens_scheduled': sum(r['prompt_tokens'] for r in rows),
               'max_prompt_tokens': max(r['prompt_tokens'] for r in rows),
               'all_within_limits': all(r['within_limits'] for r in rows),
               'caps_cover': all(c['covers'] for c in caps.values()), 'by_phase': by_phase}
    return {'summary': summary, 'max_tokens_check': caps, 'requests': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(args.tokenizer), local_files_only=True, trust_remote_code=False)
    report = audit(tokenizer)
    report['tokenizer'] = str(args.tokenizer)
    args.out.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(report['summary'], indent=1))
