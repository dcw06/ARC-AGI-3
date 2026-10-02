"""Token audit of every enumerated stagnation-supervision request with the pinned tokenizer (CPU only; no model).

Counts each request from `research.stagnation_supervision_v1.closed_loop.requests.enumerate_requests` (all game groups
of the frozen protocol, 40 actions) plus `maximal_reflection_request`, with the same chat-template call the model
service uses for admission. Checks: every policy prompt fits the 60,000-token ceiling and the 65,536 context with
128 completion tokens; every reflection prompt plus 400 completion tokens fits the context; four maximal reflections
plus their reserved output fit the 8,000-token per-episode supervisor ceiling. Writes the report once.

Must run in the pinned tokenizer environment (transformers 4.57.6, tokenizers 0.22.2, jinja2 3.1.6):
  python scripts/audit_stagnation_supervision_v1_tokens.py --tokenizer PATH
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / 'reports/stagnation_supervision_v1_token_audit.json'
PINNED = {'transformers': '4.57.6', 'tokenizers': '0.22.2', 'jinja2': '3.1.6'}
POLICY_CEILING, CONTEXT, POLICY_COMPLETION = 60000, 65536, 128


def count(tokenizer, request):
    tokens = tokenizer.apply_chat_template(request['messages'], tokenize=True, add_generation_prompt=True,
                                           truncation=False, **request['chat_template_kwargs'])
    return len(tokens)


def audit(tokenizer, requests, maximal):
    from research.stagnation_supervision_v1 import supervision as SV
    from research.stagnation_supervision_v1.closed_loop import bridge as B
    rows = [{k: r[k] for k in ('kind', 'pair_id', 'arm', 'episode_id', 'request_sha256')} | {'tokens': count(tokenizer, r['request'])}
            for r in requests]
    maximal_tokens = count(tokenizer, maximal)
    by_kind = {}
    for r in rows:
        k = by_kind.setdefault(r['kind'], {'requests': 0, 'max_tokens': 0, 'total_tokens': 0})
        k['requests'] += 1
        k['max_tokens'] = max(k['max_tokens'], r['tokens'])
        k['total_tokens'] += r['tokens']
    policy_max = by_kind.get('policy', {}).get('max_tokens', 0)
    reflection_max = max(by_kind.get('reflection', {}).get('max_tokens', 0), maximal_tokens)
    reserve = SV.POLICY['reserved_output_tokens']
    cap = B.EXPERIMENT_POLICY['max_interventions_per_episode']
    ceiling = B.EXPERIMENT_POLICY['max_supervisor_tokens_per_episode']
    checks = {'policy_within_prompt_ceiling': policy_max <= POLICY_CEILING,
              'policy_within_context': policy_max + POLICY_COMPLETION <= CONTEXT,
              'reflection_within_context': reflection_max + B.REFLECTION_MAX_TOKENS <= CONTEXT,
              'four_maximal_reflections_within_supervisor_ceiling': cap * (reflection_max + reserve) <= ceiling}
    return {'version': 'stagnation_supervision_v1_token_audit', 'by_kind': by_kind,
            'maximal_reflection_tokens': maximal_tokens, 'reflection_max_tokens': reflection_max,
            'supervisor_ceiling': ceiling, 'reserved_output_tokens': reserve, 'cap': cap, 'checks': checks,
            'all_checks_pass': all(checks.values()), 'requests': rows}


def main():
    import importlib.metadata
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer', type=Path, required=True)
    args = parser.parse_args()
    if OUTPUT.exists():
        raise SystemExit('refusing to overwrite the write-once audit: ' + str(OUTPUT))
    versions = {n: importlib.metadata.version(n) for n in PINNED}
    if versions != PINNED:
        raise SystemExit(f'pinned tokenizer environment required, found {versions}')
    from certification.phase4_integrated_v2.tokenizer_binding import verify
    verify(args.tokenizer)
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(args.tokenizer), local_files_only=True, trust_remote_code=False)
    from research.stagnation_supervision_v1.closed_loop.requests import enumerate_requests, maximal_reflection_request
    report = audit(tokenizer, enumerate_requests(), maximal_reflection_request())
    report['versions'] = versions
    OUTPUT.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('by_kind', 'reflection_max_tokens', 'checks', 'all_checks_pass')}))


if __name__ == '__main__':
    main()
