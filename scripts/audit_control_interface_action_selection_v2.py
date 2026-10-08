# Derived by scripts/build_control_interface_action_selection_v2.py; edit the derivation.
"""Exact frozen-tokenizer counts and explicit planning scenarios; CPU only, local files only."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.control_interface_action_selection_v2 import probe as P


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer', required=True, type=Path)
    args = parser.parse_args()
    from transformers import AutoTokenizer
    versions = {n: importlib.metadata.version(n) for n in ('transformers', 'tokenizers')}
    if versions != {'transformers': '4.57.6', 'tokenizers': '0.22.2'}:
        raise ValueError('use the frozen tokenizer runtime')
    manifest = json.loads((ROOT / 'certification/phase4_coordinates_v2/tokenizer_manifest.json').read_bytes())
    for name, row in manifest['files'].items():
        raw = (args.tokenizer / name).read_bytes()
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('tokenizer byte drift: ' + name)
    tokenizer = AutoTokenizer.from_pretrained(str(args.tokenizer), local_files_only=True, trust_remote_code=False)
    cases = P.load_cases(ROOT)
    protocol = json.loads((ROOT / P.PACKAGE / 'protocol.json').read_bytes())
    rows = []
    for case in cases:
        for arm in P.ARMS:
            request = P.request_for(case, arm, protocol['server']['served_model_name'])
            count = len(tokenizer.apply_chat_template(request['messages'], tokenize=True, add_generation_prompt=True,
                                                      truncation=False, **request['chat_template_kwargs']))
            rows.append({'case_id': case['case_id'], 'arm': arm, 'request_sha256': P.digest(request),
                         'prompt_tokens': count, 'max_tokens': 128, 'within_limits': count <= 60000 and count + 128 <= 65536})
    # A bounded-shape sanity check, not a claim about all whitespace-equivalent JSON encodings.
    compact = json.dumps({'action': {'action_id': 6, 'action_data': {'x': 63, 'y': 63}}}, separators=(',', ':'))
    pretty = json.dumps({'action': {'action_id': 6, 'action_data': {'x': 63, 'y': 63}}}, indent=4)
    answer_tokens = {k: len(tokenizer.encode(v, add_special_tokens=False)) + 1 for k, v in [('compact', compact), ('pretty', pretty)]}
    audit = {'schema': 'control_interface_token_audit_v1', 'cases_sha256': protocol['experiment']['cases_sha256'],
             'tokenizer': manifest, 'versions': versions, 'requests': rows, 'scheduled_calls': 120,
             'scheduled_prompt_tokens': 2 * sum(r['prompt_tokens'] for r in rows),
             'max_prompt_tokens': max(r['prompt_tokens'] for r in rows), 'representative_action_tokens': answer_tokens,
             'passed': all(r['within_limits'] for r in rows) and max(answer_tokens.values()) <= 128,
             'model_calls': 0, 'gpu_used': False}
    (ROOT / P.PACKAGE / 'token-audit.json').write_bytes((json.dumps(audit, sort_keys=True, indent=1) + '\n').encode())
    overhead = 1000
    scenarios = [{'assumed_seconds_per_research_call': t, 'research_seconds': 120 * t,
                  'pre_and_post_request_allowance_seconds': overhead,
                  'before_cleanup_seconds': overhead + 120 * t,
                  'fits_1500_second_research_ceiling': 120 * t < 1500,
                  'fits_3120_second_admission_cutoff': overhead + 120 * t < 3120}
                 for t in (5, 10, 20)]
    budget = {'status': 'proposal_not_authorized', 'counted_http_cap': 131, 'research_calls': 120,
              'other_http_calls_max': 11, 'gpu': 'exactly one RTX PRO 6000',
              'authorized_seconds_proposal': 3600, 'internal_seconds': 3420, 'admission_cutoff_seconds': 3120,
              'cleanup_reserve_seconds': 300, 'research_ceiling_seconds': 1500,
              'scenarios': scenarios,
              'note': 'Assumptions, not throughput predictions. Historical selected calls used another decoder and cache setting. '
                      'Tiny smoke prompts do not predict these real prompt costs. Slow or incomplete runs fail and retain partial evidence; '
                      'no automatic retries. The 300-second cleanup reserve is separate from every estimate.'}
    out = ROOT / 'reports/control_interface_action_selection_v2_budget.json'
    out.write_bytes((json.dumps(budget, sort_keys=True, indent=1) + '\n').encode())
    print(json.dumps({k: audit[k] for k in ('passed', 'scheduled_calls', 'scheduled_prompt_tokens', 'max_prompt_tokens', 'representative_action_tokens')}))
    return 0 if audit['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
