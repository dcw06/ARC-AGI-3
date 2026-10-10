"""Frozen-set generation and its automated pre-run checks for the successor session packages (CPU only).

    python -m research.evidence_memory_v1.successor.freeze stand-in --session A
        the development stand-in: stage1.build(session) with the development seed (the committed rehearsal set);
    python -m research.evidence_memory_v1.successor.freeze withheld --session A --nonce-file PATH [--out-root DIR]
        OWNER GATE (reports/evidence_memory_v1_successor/owner_gates.md). Reads the drawn nonce from a file outside
        the repository, forms seed = 'evidence-memory-v1-stage1-withheld/' + nonce, refuses unless sha256(seed) equals
        the committed seed commitment, then builds stage1.build(session, seed, partition='withheld',
        case_source='withheld') (protocol v2 section 5, step 4).

Both commands run the same automated checks before writing (protocol v2 sections 4 and 5): every trajectory passes
transition_evidence_v2 verify_history, its gold answers equal its construction, and its faithful memory is faithful
under the independent checker; every scheduled prompt encodes with the pinned tokenizer and stays within 4,096
tokens; every arm's evidence block fits the common budget. stage1.build has no exclusion step, so any failure refuses
to write (excluding a trajectory needs the owner's amendment) and reports counts only.

Output is counts, hashes and pass/fail only. Nothing here prints, logs or returns a question, an answer, a truth value,
a context or the seed; the nonce is never echoed. The pinned-tokenizer audit (scripts/audit_evidence_memory_v1_tokens.py,
in the isolated transformers environment) and the package build (scripts/build_evidence_memory_v1_sessions.py)
follow as separate steps.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from research.evidence_memory_v1 import fidelity as F, protocol as P, stage1 as ST, tokens as TK
from research.evidence_memory_v1 import trajectories as TR, writers as W
from research.evidence_memory_v1.successor import plan as PL

ROOT = Path(__file__).resolve().parents[3]
SEED_PREFIX = 'evidence-memory-v1-stage1-withheld/'
COMMITMENT = Path(__file__).with_name('seed-commitment.json')
EXCLUSION_PROMPT_TOKENS = 4096  # protocol v2 section 4


def seed_from_nonce_file(path):
    nonce = Path(path).read_text(encoding='ascii').strip()
    if not re.fullmatch(r'[0-9a-f]{32}', nonce):
        raise ValueError('the nonce file must hold exactly secrets.token_hex(16)')
    return SEED_PREFIX + nonce


def committed_seed_sha256(commitment_path=None):
    record = json.loads(Path(commitment_path or COMMITMENT).read_bytes())
    value = record['withheld_seed_sha256']
    if not re.fullmatch(r'[0-9a-f]{64}', value):
        raise PermissionError('no withheld seed has been committed (owner gate)')
    if value in {draw.get('withheld_seed_sha256') for draw in record.get('retired', [])}:
        raise PermissionError('this commitment belongs to a retired draw; its nonce is never used again')
    return value


def automated_checks(frozen, seed, partition, tokenizer):
    """Counts only. Rebuilds every trajectory of the frozen set and checks the exclusion conditions, prompt size and
    the common budget."""
    exclusions = {'verify_history': 0, 'gold_differs_from_construction': 0, 'faithful_memory_not_faithful': 0,
                  'prompt_fails_or_exceeds_4096': 0}
    trajectories = 0
    from research.transition_evidence_v2 import transition as T2
    for group in frozen['groups']:
        for family in TR.FAMILIES:
            for delay in P.HORIZONS:
                t = TR.build(family, group, delay, seed=seed, partition=partition)
                trajectories += 1
                if T2.verify_history(t['records'], t['raws']):
                    exclusions['verify_history'] += 1
                expected = t['evaluator_only']['expected']
                if any(F.gold(t['records'], q) != q['expected_answer'] for q in expected['questions']):
                    exclusions['gold_differs_from_construction'] += 1
                memory = W.run_writer(W.Faithful(), t)['memory']
                if not F.evaluate(t['records'], memory, expected)['faithful']:
                    exclusions['faithful_memory_not_faithful'] += 1
    contexts = {c['context_id']: c for c in frozen['contexts']}
    sizes, budget_violations = {}, 0
    for context_id, context in contexts.items():
        sizes[context_id] = len(tokenizer.encode(context['evidence']))
    for context_id, size in sizes.items():
        trajectory, arm = context_id.rsplit('/', 1)
        if arm in ('state_keyed_raw', 'memory') and size > sizes[trajectory + '/recent_raw']:
            budget_violations += 1
    largest = 0
    for _, _, _, request in PL.scheduled_requests(frozen):
        try:
            tokens = tokenizer.chat_prompt_tokens(request['messages'])
        except ValueError:
            exclusions['prompt_fails_or_exceeds_4096'] += 1
            continue
        largest = max(largest, tokens)
        if tokens > EXCLUSION_PROMPT_TOKENS:
            exclusions['prompt_fails_or_exceeds_4096'] += 1
    passed = not any(exclusions.values()) and not budget_violations
    return {'trajectories': trajectories, 'contexts': len(contexts), 'probes': len(frozen['probes']),
            'scheduled_calls': sum(len(b['probe_ids']) for b in frozen['schedule']), 'exclusions': exclusions,
            'budget_violations': budget_violations, 'max_prompt_tokens': largest, 'passed': passed}


def build_checked(session, seed, partition, case_source, tokenizer=None):
    """(frozen-set bytes, counts-only summary); raises if any automated check fails."""
    tokenizer = tokenizer or TK.Tokenizer()
    frozen = ST.build(session, seed, partition, case_source, tokenizer)
    raw = ST.encode(frozen)
    checks = automated_checks(frozen, seed, partition, tokenizer)
    summary = {'session': session, 'case_source': case_source, 'seed_sha256': frozen['seed_sha256'],
               'frozen_set_sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), **checks}
    if not checks['passed']:
        raise ValueError('automated pre-run checks failed; nothing written: ' + json.dumps(summary, sort_keys=True))
    return raw, summary


def write(out_root, session, raw):
    path = Path(out_root) / PL.SESSIONS[session]['package'] / PL.FROZEN_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=('stand-in', 'withheld'))
    parser.add_argument('--session', choices=sorted(PL.SESSIONS), required=True)
    parser.add_argument('--nonce-file', type=Path)
    parser.add_argument('--out-root', type=Path, default=ROOT)
    args = parser.parse_args()
    if args.command == 'stand-in':
        raw, summary = build_checked(args.session, TR.SEED, TR.PARTITION, 'development_stand_in')
    else:
        if args.nonce_file is None:
            raise SystemExit('withheld needs --nonce-file (kept outside the repository)')
        commitment = committed_seed_sha256()
        seed = seed_from_nonce_file(args.nonce_file)
        if hashlib.sha256(seed.encode()).hexdigest() != commitment:
            raise SystemExit('the nonce does not match the committed seed SHA-256; nothing built')
        raw, summary = build_checked(args.session, seed, 'withheld', 'withheld')
        del seed
    write(args.out_root, args.session, raw)
    print(json.dumps(summary, indent=1, sort_keys=True))


if __name__ == '__main__':
    main()
