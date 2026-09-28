"""Exact prompt-token audit and runtime scenarios for evidence comprehension v3 (no model calls).

tokenize (pinned tokenizer env): count every frozen request's prompt tokens and each key answer's completion
    tokens with the frozen Qwen3-VL tokenizer, and check every family's max_tokens against its longest
    schema-valid answer, pretty-printed.
estimate (any env): runtime scenarios fitted to the v2 live attempt's measured, cache-disabled calls (same
    runtime stack, model and GPU type; a different workload), plus explicit first-cell overhead from v2's
    receipts with planning allowances. The 300 s cleanup reserve is separate and is never spent by any estimate.

These are planning figures, not guarantees. Admission control protects the deadline; a slower run is cut and
reported incomplete.
"""
import argparse
import json
from pathlib import Path
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REPORT = ROOT / 'reports/evidence_comprehension_v3_token_audit.json'
TOKENIZER = ROOT / '.cache/phase4-tokenizer'
V2_ARCHIVE = ROOT / 'evidence/evidence-comprehension-v2-live.tar.xz'
V2_RUN = 'reports/runs/evidence-comprehension-v2/download/evidence-comprehension-v2/'
PROMPT_CEILING, CONTEXT = 60000, 65536
CLEANUP_RESERVE_SECONDS, INTERNAL_SECONDS = 300, 3300
COMPLETION_SLACK = 2
ALLOWANCE_FACTORS = {'installation': 2.0, 'model_startup': 1.5, 'other_pre_question': 5.0,
                     'post_question_finalization': 5.0}
MIN_ALLOWANCE_SECONDS = 30


def frozen_requests():
    from research.evidence_comprehension_v3 import probes as P
    frozen, digest = P.load_frozen()
    contexts = {c['context_id']: c for c in frozen['contexts']}
    return frozen, digest, [(p, P.build_request(contexts[p['context_id']], p)) for p in frozen['probes']]


def tokenize():
    from transformers import AutoTokenizer
    from scripts.audit_evidence_comprehension_v2_tokens import longest_answers
    from research.evidence_comprehension_v3.probes import MAX_TOKENS, TRACK_OF
    tokenizer = AutoTokenizer.from_pretrained(str(TOKENIZER), local_files_only=True, trust_remote_code=False)
    caps = {}
    for family, answer in longest_answers().items():
        if family not in TRACK_OF:
            continue
        tokens = len(tokenizer.encode(json.dumps({'answer': answer}, indent=4), add_special_tokens=False)) + 1
        caps[family] = {'longest_valid_answer_tokens_pretty': tokens, 'max_tokens': MAX_TOKENS[family],
                        'cap_covers_longest_answer': MAX_TOKENS[family] >= tokens}
    _, digest, requests = frozen_requests()
    rows = []
    for probe, request in requests:
        ids = tokenizer.apply_chat_template(request['messages'], tokenize=True, add_generation_prompt=True,
                                            truncation=False, **request['chat_template_kwargs'])
        key = json.dumps({'answer': probe['key']}, separators=(',', ':'))
        rows.append({'probe_id': probe['probe_id'], 'partition': probe['partition'], 'condition': probe['condition'],
                     'variant': probe['variant'], 'family': probe['family'], 'prompt_tokens': len(ids),
                     'key_completion_tokens': len(tokenizer.encode(key, add_special_tokens=False)) + 1,
                     'max_tokens': request['max_tokens'],
                     'within_limits': len(ids) <= PROMPT_CEILING and len(ids) + request['max_tokens'] <= CONTEXT})
    REPORT.write_text(json.dumps({'tokenizer': 'pinned Qwen3-VL-30B-A3B-Instruct-FP8 tokenizer (.cache/phase4-tokenizer)',
                                  'probe_set_sha256': digest, 'max_tokens_check': caps, 'requests': rows},
                                 indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'requests': len(rows), 'max_prompt_tokens': max(r['prompt_tokens'] for r in rows),
                      'all_within_limits': all(r['within_limits'] for r in rows),
                      'all_caps_cover_longest_answer': all(c['cap_covers_longest_answer'] for c in caps.values())}))


def v2_measurements():
    with tarfile.open(V2_ARCHIVE, 'r:xz') as bundle:
        def record(name):
            return json.load(bundle.extractfile(V2_RUN + name))
        calls = [json.loads(line) for line in bundle.extractfile(V2_RUN + 'worker/run/calls.jsonl').read().splitlines()]
        installation = record('control/installation.json')['elapsed_seconds']
        startup = record('worker/model-ready.json')['startup_seconds']
        cell = record('control/notebook-cost.json')['elapsed_seconds']
    calls.sort(key=lambda c: c['started_at'])
    rows = [(c['server_prompt_tokens'], c['server_completion_tokens'], n['started_at'] - c['started_at'])
            for c, n in zip(calls, calls[1:])]
    sx, sy = [[0.0] * 3 for _ in range(3)], [0.0] * 3
    for p, q, t in rows:
        v = (1.0, p, q)
        for i in range(3):
            sy[i] += v[i] * t
            for j in range(3):
                sx[i][j] += v[i] * v[j]
    a = [row[:] + [sy[i]] for i, row in enumerate(sx)]
    for i in range(3):
        pivot = max(range(i, 3), key=lambda r: abs(a[r][i]))
        a[i], a[pivot] = a[pivot], a[i]
        for r in range(3):
            if r != i:
                f = a[r][i] / a[i][i]
                a[r] = [x - f * y for x, y in zip(a[r], a[i])]
    coef = [a[i][3] / a[i][i] for i in range(3)]
    first, last = calls[0]['started_at'], max(c['returned_at'] for c in calls)
    measured = {'installation': round(installation, 1), 'model_startup': round(startup, 1),
                'other_pre_question': round(first - installation - startup, 1),
                'post_question_finalization': round(cell - last, 1)}
    return {'source': 'evidence comprehension v2 live attempt ecv2-65759c16 (cache disabled, one RTX Pro 6000)',
            'calls': len(calls), 'questions_seconds': round(last - first, 1), 'first_cell_seconds': round(cell, 1),
            'fit_seconds_per_call': coef[0], 'fit_seconds_per_prompt_token': coef[1],
            'fit_seconds_per_completion_token': coef[2], 'overhead_measured_seconds': measured}


def estimate():
    report = json.loads(REPORT.read_bytes())
    frozen, _, _ = frozen_requests()
    by_id = {r['probe_id']: r for r in report['requests']}
    fit = v2_measurements()
    measured = fit['overhead_measured_seconds']
    allowance = {k: round(max(MIN_ALLOWANCE_SECONDS, v * ALLOWANCE_FACTORS[k])) for k, v in measured.items()}
    phases = [(f"{b['partition']}/{b['pass']}", [by_id[i] for i in b['probe_ids']]) for b in frozen['schedule']]
    admission = INTERNAL_SECONDS - CLEANUP_RESERVE_SECONDS

    def seconds(rows, completion):
        return sum(fit['fit_seconds_per_call'] + fit['fit_seconds_per_prompt_token'] * r['prompt_tokens']
                   + fit['fit_seconds_per_completion_token'] * (r['max_tokens'] if completion == 'cap' else
                                                                min(r['max_tokens'], r['key_completion_tokens'] * COMPLETION_SLACK))
                   for r in rows)
    withheld = [r for phase, rows in phases if phase.startswith('withheld/') for r in rows]
    scenarios, headroom = {}, {}
    for name, overhead, factor, completion in (
            ('measured_overhead_v2_rates', measured, 1.0, 'key_x2'),
            ('allowance_overhead_v2_rates', allowance, 1.0, 'key_x2'),
            ('allowance_overhead_two_times_slower', allowance, 2.0, 'key_x2'),
            ('allowance_overhead_three_times_slower_every_call_at_cap', allowance, 3.0, 'cap')):
        pre = overhead['installation'] + overhead['model_startup'] + overhead['other_pre_question']
        elapsed, row = pre, {'pre_question_seconds': round(pre)}
        for phase, rows in phases:
            elapsed += factor * seconds(rows, completion)
            row[phase + '_ends_at_seconds'] = round(elapsed)
        end = elapsed + overhead['post_question_finalization']
        scenarios[name] = {'slowdown_factor': factor, 'completion_tokens': completion, **row,
                           'first_cell_end_seconds': round(end),
                           'withheld_fits_admission_cutoff': max(v for k, v in row.items() if k.startswith('withheld/')) <= admission,
                           'first_cell_fits_before_cleanup_reserve': end <= admission}
    for label, overhead in (('measured_overhead', measured), ('allowance_overhead', allowance)):
        pre = overhead['installation'] + overhead['model_startup'] + overhead['other_pre_question']
        headroom[label] = round((admission - pre) / seconds(withheld, 'key_x2'), 2)
    report.update(summary={'scheduled_calls': sum(len(rows) for _, rows in phases),
                           'distinct_requests': len(report['requests']),
                           'prompt_tokens_scheduled': sum(r['prompt_tokens'] for _, rows in phases for r in rows),
                           'max_prompt_tokens': max(r['prompt_tokens'] for r in report['requests']),
                           'all_within_limits': all(r['within_limits'] for r in report['requests']),
                           'calls_by_phase': {phase: len(rows) for phase, rows in phases}},
                  v2_measurements=fit,
                  runtime_scenarios={'status': 'planning scenarios fitted to v2 measured calls of a different workload; '
                                               'not guarantees. Admission control protects the deadline.',
                                     'first_cell_overhead_measured_seconds': measured,
                                     'first_cell_overhead_allowance_seconds': allowance,
                                     'allowance_factors': ALLOWANCE_FACTORS,
                                     'cleanup_reserve_seconds': CLEANUP_RESERVE_SECONDS,
                                     'cleanup_reserve_note': 'separate from every allowance; no estimate consumes it',
                                     'admission_cutoff_seconds': admission, 'withheld_rate_headroom_factor': headroom,
                                     'scenarios': scenarios})
    REPORT.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'summary': report['summary'], 'fit': {k: v for k, v in fit.items()},
                      'allowance': allowance, 'headroom': headroom, 'scenarios': scenarios}, indent=1))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('tokenize', 'estimate'))
    tokenize() if parser.parse_args().operation == 'tokenize' else estimate()
