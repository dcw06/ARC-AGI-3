"""Compare each session's committed token audit with the audit at an earlier revision (CPU only; no tokenizer, model,
GPU or network). Used for the recall decoding-schema change of the protocol freeze (protocol v2 frozen, section 2):
the request bodies change, so every recall request digest changes, but the prompts do not, so every prompt token count
must be identical.

    python scripts/compare_evidence_memory_v1_token_audits.py --before fb8cf77 --out <receipt.json>

Per session it requires: the same frozen set; the same scheduled rows in the same order (index, pass, probe); identical
transformers and pure-Python prompt counts on every row; every recall request digest changed and every decision
request digest unchanged; and the same number of distinct requests.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.evidence_memory_v1.successor import plan as PL  # noqa: E402

KEYS = ('index', 'pass_id', 'probe_id')
COUNTS = ('prompt_tokens', 'pure_python_prompt_tokens')


def at_revision(revision, path):
    return json.loads(subprocess.run(['git', 'show', f'{revision}:{path}'], cwd=ROOT, capture_output=True,
                                     check=True, timeout=60).stdout)


def compare(label, before_revision):
    package = PL.SESSIONS[label]['package']
    path = package + '/' + PL.AUDIT_NAME
    before, after = at_revision(before_revision, path), json.loads((ROOT / path).read_bytes())
    frozen, _ = PL.load_frozen(ROOT, package)
    kind = {p['probe_id']: p['kind'] for p in frozen['probes']}
    rows_before, rows_after = before['requests'], after['requests']
    same_rows = [[r[k] for k in KEYS] for r in rows_before] == [[r[k] for k in KEYS] for r in rows_after]
    changed = {'recall': 0, 'decision': 0}
    unchanged = {'recall': 0, 'decision': 0}
    count_mismatches = 0
    for a, b in zip(rows_before, rows_after):
        count_mismatches += any(a[k] != b[k] for k in COUNTS)
        (changed if a['request_sha256'] != b['request_sha256'] else unchanged)[kind[b['probe_id']]] += 1
    total = {name: sum(r['prompt_tokens'] for r in rows) for name, rows in (('before', rows_before), ('after', rows_after))}
    distinct = {name: len({r['request_sha256'] for r in rows})
                for name, rows in (('before', rows_before), ('after', rows_after))}
    result = {'audit': path, 'frozen_set_sha256': {'before': before['frozen_set_sha256'],
                                                   'after': after['frozen_set_sha256']},
              'rows': {'before': len(rows_before), 'after': len(rows_after)}, 'same_rows_in_order': same_rows,
              'prompt_count_mismatches': count_mismatches, 'total_prompt_tokens': total,
              'max_prompt_tokens': {'before': max(r['prompt_tokens'] for r in rows_before),
                                    'after': max(r['prompt_tokens'] for r in rows_after)},
              'distinct_requests': distinct, 'request_digests_changed': changed,
              'request_digests_unchanged': unchanged, 'tokenizer_unchanged': before['tokenizer'] == after['tokenizer']}
    result['passed'] = (same_rows and before['frozen_set_sha256'] == after['frozen_set_sha256'] and not count_mismatches
                        and total['before'] == total['after'] and distinct['before'] == distinct['after']
                        and unchanged['recall'] == 0 and changed['decision'] == 0 and changed['recall'] > 0
                        and result['tokenizer_unchanged'] and before.get('passed') is True and after.get('passed') is True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--before', required=True, help='the revision whose committed audits are compared')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--change', default='recall decoding schema without uniqueItems (protocol v2 frozen, section 2)',
                        help='what changed since --before (recorded in the receipt)')
    args = parser.parse_args()
    before = subprocess.run(['git', 'rev-parse', args.before], cwd=ROOT, capture_output=True, text=True,
                            check=True).stdout.strip()
    sessions = {label: compare(label, before) for label in sorted(PL.SESSIONS)}
    record = {'schema': 'evidence_memory_v1_token_audit_comparison_v1', 'before_revision': before,
              'change': args.change,
              'model_calls': 0, 'gpu_used': False, 'sessions': sessions,
              'passed': all(s['passed'] for s in sessions.values())}
    args.out.write_bytes((json.dumps(record, indent=1, sort_keys=True) + '\n').encode())
    print(json.dumps({label: {k: s[k] for k in ('passed', 'prompt_count_mismatches', 'total_prompt_tokens',
                                                'request_digests_changed', 'request_digests_unchanged')}
                      for label, s in sessions.items()}, indent=1, sort_keys=True))
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
