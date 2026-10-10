"""Real-tokenizer cross-check of the Track 2 Stage 1 study requests and each session's token audit (no model call).

Run in the isolated pinned-tokenizer environment (transformers 4.57.6, tokenizers 0.22.2) with the pinned tokenizer
files (Qwen/Qwen3-VL-30B-A3B-Instruct-FP8 at d9748a51; `EVIDENCE_MEMORY_TOKENIZER` or tokens.locate()):

    python scripts/audit_evidence_memory_v1_tokens.py [--sessions A B]

For each session package's committed frozen set it:
- counts every scheduled request (both passes, all four arms, recent controls included) with transformers'
  `apply_chat_template(messages, tokenize=True, add_generation_prompt=True, truncation=False, enable_thinking=False)`
  and with the pure-Python tokenizer (tokens.py), and requires equality, the reviewed ceilings (60,000 prompt
  tokens; prompt + 64 within 65,536) and the 4,096-token exclusion bound;
- measures every evidence block with transformers' `encode(text, add_special_tokens=False)` and requires each
  budgeted arm (state_keyed_raw, memory) to fit its trajectory's common budget (the recent_raw block), with
  pure-Python parity for every block; for the development stand-in (seed known) it also rebuilds every trajectory's
  packages with transformers as the measure and requires the identical selection;
- checks that max_tokens (64) covers the longest schema-valid answer, compact and pretty-printed;
- writes the session's token-audit.json (bound to the frozen set) and a combined report.
For a withheld frozen set this prints counts only; it never prints a question, an answer or a context.
"""
import argparse
import hashlib
import importlib.metadata
import itertools
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.evidence_memory_v1 import protocol as P, stage1 as ST, tokens as TK, trajectories as TR  # noqa: E402
from research.evidence_memory_v1 import writers as W  # noqa: E402
from research.evidence_memory_v1.successor import freeze as FZ, plan as PL  # noqa: E402

# r2: after the recall decoding schema change (protocol v2 frozen, section 2). The r1 report,
# token_cross_check.json, is kept unchanged as history.
REPORT = ROOT / 'reports/evidence_memory_v1_successor/token_cross_check_r3.json'


def longest_answers(tokenizer):
    """Completion tokens (+1 for the end token) of the longest answers, compact and pretty: every schema-valid recall
    answer (each ordering of each non-empty subset), and candidate-shaped decision answers (ids 1-7; empty or
    two-coordinate action data at the grid extremes)."""
    recall = [{'values': list(c)} for n in range(1, len(ST.RECALL_VALUES) + 1)
              for c in itertools.permutations(ST.RECALL_VALUES, n)]
    choice = [{'choice': {'action_id': a, 'action_data': d}} for a in range(1, 8)
              for d in ({}, {'x': 63, 'y': 63}, {'x': 0, 'y': 0})]
    out = {}
    for name, answers in (('recall', recall), ('decision', choice)):
        out[name] = {style: max(len(tokenizer.encode(json.dumps(a, indent=indent, separators=sep),
                                                     add_special_tokens=False)) + 1 for a in answers)
                     for style, indent, sep in (('compact', None, (',', ':')), ('pretty', 4, None))}
    return out


def audit_session(label, tf, pure, root=ROOT):
    package = PL.SESSIONS[label]['package']
    frozen, digest = PL.load_frozen(root, package)
    rows, cache, mismatches = [], {}, 0
    largest = 0
    for n, pass_id, probe_id, request in PL.scheduled_requests(frozen):
        sha = PL.request_sha256(request)
        if sha not in cache:
            ids = tf.apply_chat_template(request['messages'], tokenize=True, add_generation_prompt=True,
                                         truncation=False, **request['chat_template_kwargs'])
            if type(ids) is not list or not ids or any(type(i) is not int for i in ids):
                raise ValueError('apply_chat_template did not return token ids')
            cache[sha] = (len(ids), pure.chat_prompt_tokens(request['messages']))
        tokens, python_tokens = cache[sha]
        mismatches += tokens != python_tokens
        largest = max(largest, tokens)
        rows.append({'index': n, 'pass_id': pass_id, 'probe_id': probe_id, 'request_sha256': sha,
                     'prompt_tokens': tokens, 'pure_python_prompt_tokens': python_tokens})
    within = all(r['prompt_tokens'] <= min(PL.PROMPT_TOKEN_CEILING, FZ.EXCLUSION_PROMPT_TOKENS)
                 and r['prompt_tokens'] + P.MAX_TOKENS <= PL.CONTEXT_TOKENS for r in rows)
    measure = lambda text: len(tf.encode(text, add_special_tokens=False))  # noqa: E731
    sizes, block_mismatches = {}, 0
    for context in frozen['contexts']:
        sizes[context['context_id']] = measure(context['evidence'])
        block_mismatches += sizes[context['context_id']] != len(pure.encode(context['evidence']))
    budgets, over = [], 0
    for context_id, size in sizes.items():
        trajectory, arm = context_id.rsplit('/', 1)
        if arm == 'recent_raw':
            budgets.append(size)
        elif arm in P.ARMS:
            over += size > sizes[trajectory + '/recent_raw']
    reselected = None
    if frozen['case_source'] == 'development_stand_in':
        texts = {c['context_id']: c['evidence'] for c in frozen['contexts']}
        reselected = {'trajectories': 0, 'identical': 0}
        for group in frozen['groups']:
            for family in TR.FAMILIES:
                for delay in P.HORIZONS:
                    t = TR.build(family, group, delay, seed=TR.SEED, partition=TR.PARTITION)
                    memory = W.run_writer(W.Faithful(), t)['memory']
                    _, contents = P.arm_contents(t, memory, measure)
                    reselected['trajectories'] += 1
                    reselected['identical'] += all(texts[f"{t['id']}/{arm}"] == contents[arm][0] for arm in ST.ARM_ORDER)
    summary = {'scheduled_calls': len(rows), 'distinct_requests': len(cache), 'prompt_token_mismatches': mismatches,
               'max_prompt_tokens': largest, 'mean_prompt_tokens': round(sum(r['prompt_tokens'] for r in rows) / len(rows), 1),
               'within_ceilings_and_4096': within, 'evidence_blocks': len(sizes),
               'evidence_block_mismatches': block_mismatches,
               'budget_tokens': {'min': min(budgets), 'max': max(budgets)}, 'budgeted_blocks_over_budget': over,
               'selection_rebuilt_with_transformers': reselected}
    passed = (not mismatches and within and not block_mismatches and not over
              and (reselected is None or reselected['identical'] == reselected['trajectories']))
    audit = {'schema': PL.AUDIT_SCHEMA, 'session': label, 'case_source': frozen['case_source'],
             'frozen_set_sha256': digest, 'tokenizer': PL.PINNED_TOKENIZER, 'tokenizer_files_sha256': TK.PINNED,
             'method': 'transformers apply_chat_template(tokenize=True, add_generation_prompt=True, truncation=False, '
                       'enable_thinking=False) with pure-Python parity', 'passed': passed, 'summary': summary,
             'requests': rows}
    return audit, summary, passed


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--sessions', nargs='+', choices=sorted(PL.SESSIONS), default=sorted(PL.SESSIONS))
    parser.add_argument('--no-report', action='store_true', help='write only the session audits (owner gate)')
    args = parser.parse_args()
    from transformers import AutoTokenizer
    versions = {name: importlib.metadata.version(name) for name in ('transformers', 'tokenizers')}
    if versions != {k: PL.PINNED_TOKENIZER[k] for k in versions}:
        raise SystemExit(f'pinned tokenizer environment required, found {versions}')
    path = TK.locate()
    if path is None:
        raise SystemExit('pinned tokenizer files not found')
    pure = TK.Tokenizer(path)  # verifies the pinned file hashes
    tf = AutoTokenizer.from_pretrained(str(path), local_files_only=True, trust_remote_code=False)
    report = {'schema': 'evidence_memory_v1_token_cross_check_v1', 'environment': {
        **versions, 'python': sys.version.split()[0], 'tokenizer_files_sha256': TK.PINNED,
        'tokenizer_source': 'EVIDENCE_MEMORY_TOKENIZER' if os.environ.get('EVIDENCE_MEMORY_TOKENIZER') else 'tokens.locate()'},
        'max_tokens': P.MAX_TOKENS, 'longest_valid_answer_tokens': longest_answers(tf), 'sessions': {}}
    report['max_tokens_covers_every_valid_answer'] = all(
        v <= P.MAX_TOKENS for kind in report['longest_valid_answer_tokens'].values() for v in kind.values())
    ok = report['max_tokens_covers_every_valid_answer']
    for label in args.sessions:
        audit, summary, passed = audit_session(label, tf, pure)
        target = ROOT / PL.SESSIONS[label]['package'] / PL.AUDIT_NAME
        target.write_bytes((json.dumps(audit, indent=1, sort_keys=True) + '\n').encode())
        report['sessions'][label] = {'frozen_set_sha256': audit['frozen_set_sha256'], 'case_source': audit['case_source'],
                                     'token_audit_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                                     'passed': passed, **summary}
        ok = ok and passed
    report['passed'] = ok
    if not args.no_report:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_bytes((json.dumps(report, indent=1, sort_keys=True) + '\n').encode())
    print(json.dumps({k: v for k, v in report.items() if k != 'environment'}, indent=1, sort_keys=True))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
