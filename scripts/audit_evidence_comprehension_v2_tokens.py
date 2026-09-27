"""Exact prompt-token audit and runtime scenarios for evidence comprehension v2 (no model calls).

tokenize (pinned tokenizer env): count every exported request's prompt tokens and each key answer's
    completion tokens with the frozen Qwen3-VL tokenizer (requests from
    build_evidence_comprehension_v2.py --export-requests), and check every family's max_tokens against its
    longest schema-valid answer, pretty-printed.
estimate (any env): runtime scenarios from the v1 live attempt's measured, cache-disabled call timings, plus
    explicit first-cell overhead: installation, model startup, other pre-question work and post-question
    finalization, each measured in v1 and given a planning allowance. The 300 s cleanup reserve is separate
    and is never spent by any estimate.

The v1 timings are measurements of a different workload on the same model, server configuration and GPU
type, not guarantees for this one. The runner, not these figures, protects the deadline (per-call bounds and
admission control); a slower run is cut at the admission cutoff and reported incomplete.
"""
import argparse
import json
from pathlib import Path
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REQUESTS = ROOT / '.cache/evidence_comprehension_v2_requests.jsonl'
REPORT = ROOT / 'reports/evidence_comprehension_v2_token_audit.json'
TOKENIZER = ROOT / '.cache/phase4-tokenizer'
PROBES = ROOT / 'research/evidence_comprehension_v2/probes.json'
V1_ARCHIVE = ROOT / 'evidence/evidence-comprehension-v1-live.tar.xz'
V1_CALLS = 'reports/runs/evidence-comprehension-v1/download/evidence-comprehension-v1/worker/run/calls/'
PROMPT_CEILING, CONTEXT = 60000, 65536
V1_RUN = 'reports/runs/evidence-comprehension-v1/download/evidence-comprehension-v1/'
CLEANUP_RESERVE_SECONDS, INTERNAL_SECONDS = 300, 3300  # the reserve is never spent by any estimate below
COMPLETION_SLACK = 2
# Planning allowances for first-cell work that is not a question, each a multiple of its v1 measurement.
ALLOWANCE_FACTORS = {'installation': 2.0, 'model_startup': 1.5, 'other_pre_question': 5.0,
                     'post_question_finalization': 5.0}
MIN_ALLOWANCE_SECONDS = 30


def longest_answers():
    """The longest schema-valid answer per family (every list at maxItems with the widest values)."""
    from research.evidence_comprehension_v2.probes import ANSWER_SCHEMAS
    click = {'action_id': 6, 'action_data': {'x': 63, 'y': 63}}
    result = {}
    for family, schema in ANSWER_SCHEMAS.items():
        if 'enum' in schema:
            result[family] = max(schema['enum'], key=len)
        elif 'anyOf' in schema:
            result[family] = 'not_shown'
        elif schema['items'].get('type') == 'integer':
            result[family] = [schema['items']['maximum']] * schema['maxItems']
        else:
            result[family] = [click] * schema['maxItems']
    return result


def tokenize():
    from transformers import AutoTokenizer
    from research.evidence_comprehension_v2.probes import MAX_TOKENS
    tokenizer = AutoTokenizer.from_pretrained(str(TOKENIZER), local_files_only=True, trust_remote_code=False)
    caps = {}
    for family, answer in longest_answers().items():
        text = json.dumps({'answer': answer}, indent=4)
        tokens = len(tokenizer.encode(text, add_special_tokens=False)) + 1
        caps[family] = {'longest_valid_answer_tokens_pretty': tokens, 'max_tokens': MAX_TOKENS[family],
                        'cap_covers_longest_answer': MAX_TOKENS[family] >= tokens}
    rows = []
    with REQUESTS.open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            request = row['request']
            ids = tokenizer.apply_chat_template(request['messages'], tokenize=True, add_generation_prompt=True,
                                                truncation=False, **request['chat_template_kwargs'])
            rows.append({'probe_id': row['probe_id'], 'partition': row['partition'], 'condition': row['condition'],
                         'family': row['family'], 'prompt_tokens': len(ids),
                         'key_completion_tokens': len(tokenizer.encode(row['key_response'], add_special_tokens=False)) + 1,
                         'max_tokens': request['max_tokens'],
                         'within_limits': len(ids) <= PROMPT_CEILING and len(ids) + request['max_tokens'] <= CONTEXT})
    REPORT.write_text(json.dumps({'tokenizer': 'pinned Qwen3-VL-30B-A3B-Instruct-FP8 tokenizer (.cache/phase4-tokenizer)',
                                  'max_tokens_check': caps, 'requests': rows}, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'requests': len(rows), 'max_prompt_tokens': max(r['prompt_tokens'] for r in rows),
                      'all_within_limits': all(r['within_limits'] for r in rows),
                      'all_caps_cover_longest_answer': all(c['cap_covers_longest_answer'] for c in caps.values())}))


def v1_measurements():
    """Per-call slots (start to next start, so host checks are included) from the v1 live attempt, fitted as
    seconds = a + b * prompt_tokens + c * completion_tokens by least squares."""
    calls = []
    with tarfile.open(V1_ARCHIVE, 'r:xz') as bundle:
        for member in bundle.getmembers():
            if member.name.startswith(V1_CALLS) and member.name.endswith('.json'):
                calls.append(json.load(bundle.extractfile(member)))
    calls.sort(key=lambda c: c['started_at'])
    rows = [(c['server_prompt_tokens'], c['server_completion_tokens'], nxt['started_at'] - c['started_at'])
            for c, nxt in zip(calls, calls[1:])]
    n = len(rows)
    sx = [[0.0] * 3 for _ in range(3)]
    sy = [0.0] * 3
    for p, q, t in rows:
        v = (1.0, p, q)
        for i in range(3):
            sy[i] += v[i] * t
            for j in range(3):
                sx[i][j] += v[i] * v[j]
    a = [row[:] + [sy[i]] for i, row in enumerate(sx)]  # Gaussian elimination
    for i in range(3):
        pivot = max(range(i, 3), key=lambda r: abs(a[r][i]))
        a[i], a[pivot] = a[pivot], a[i]
        for r in range(3):
            if r != i:
                f = a[r][i] / a[i][i]
                a[r] = [x - f * y for x, y in zip(a[r], a[i])]
    coef = [a[i][3] / a[i][i] for i in range(3)]
    slots = sorted(t for _, _, t in rows)
    with tarfile.open(V1_ARCHIVE, 'r:xz') as bundle:
        def record(name):
            return json.load(bundle.extractfile(V1_RUN + name))
        installation = record('control/installation.json')['elapsed_seconds']
        startup = record('worker/model-ready.json')['startup_seconds']
        cell = record('control/notebook-cost.json')['elapsed_seconds']
    first_start, last_return = calls[0]['started_at'], max(c['returned_at'] for c in calls)
    timeline = {'installation_seconds': round(installation, 1), 'model_startup_seconds': round(startup, 1),
                'other_pre_question_seconds': round(first_start - installation - startup, 1),
                'first_question_started_at_seconds': round(first_start, 1),
                'questions_seconds': round(last_return - first_start, 1),
                'post_question_finalization_seconds': round(cell - last_return, 1),
                'first_cell_seconds': round(cell, 1)}
    return {'source': 'evidence comprehension v1 live attempt ecv1-4458251e (cache disabled, one RTX Pro 6000)',
            'calls': len(calls), 'slots': n, 'total_slot_seconds': round(sum(slots), 1),
            'prompt_tokens': sum(p for p, _, _ in rows), 'max_slot_seconds': round(slots[-1], 3),
            'fit_seconds_per_call': round(coef[0], 5), 'fit_seconds_per_prompt_token': coef[1],
            'fit_seconds_per_completion_token': coef[2], 'first_cell_timeline': timeline}


def overheads(timeline):
    """Measured v1 non-question first-cell work, and the planning allowances derived from it."""
    measured = {'installation': timeline['installation_seconds'], 'model_startup': timeline['model_startup_seconds'],
                'other_pre_question': timeline['other_pre_question_seconds'],
                'post_question_finalization': timeline['post_question_finalization_seconds']}
    allowance = {k: round(max(MIN_ALLOWANCE_SECONDS, v * ALLOWANCE_FACTORS[k])) for k, v in measured.items()}
    return measured, allowance


def estimate():
    report = json.loads(REPORT.read_bytes())
    probes = json.loads(PROBES.read_bytes())
    by_id = {r['probe_id']: r for r in report['requests']}
    fit = v1_measurements()

    def seconds(rows, completion):
        total = 0.0
        for r in rows:
            tokens = r['max_tokens'] if completion == 'cap' else min(r['max_tokens'], r['key_completion_tokens'] * COMPLETION_SLACK)
            total += (fit['fit_seconds_per_call'] + fit['fit_seconds_per_prompt_token'] * r['prompt_tokens']
                      + fit['fit_seconds_per_completion_token'] * tokens)
        return total
    phases = [(f"{s['partition']}/{s['pass']}", [by_id[i] for i in s['probe_ids']]) for s in probes['schedule']]
    admission = INTERNAL_SECONDS - CLEANUP_RESERVE_SECONDS
    measured, allowance = overheads(fit['first_cell_timeline'])
    withheld_rows = [r for phase, rows in phases if phase.startswith('withheld/') for r in rows]
    scenarios = {}
    for name, overhead, factor, completion in (
            ('measured_overhead_v1_rates', measured, 1.0, 'key_x2'),
            ('allowance_overhead_v1_rates', allowance, 1.0, 'key_x2'),
            ('allowance_overhead_two_times_slower', allowance, 2.0, 'key_x2'),
            ('allowance_overhead_three_times_slower_every_call_at_cap', allowance, 3.0, 'cap')):
        pre = overhead['installation'] + overhead['model_startup'] + overhead['other_pre_question']
        elapsed, row = pre, {'pre_question_seconds': round(pre)}
        for phase, rows in phases:
            elapsed += factor * seconds(rows, completion)
            row[phase + '_ends_at_seconds'] = round(elapsed)
        withheld_end = max(v for k, v in row.items() if k.startswith('withheld/'))
        scenarios[name] = {'slowdown_factor': factor, 'completion_tokens': completion, **row,
                           'first_cell_end_seconds': round(elapsed + overhead['post_question_finalization']),
                           'withheld_fits_admission_cutoff': withheld_end <= admission,
                           'everything_fits_admission_cutoff': elapsed <= admission,
                           'first_cell_fits_before_cleanup_reserve':
                               elapsed + overhead['post_question_finalization'] <= admission}
    headroom = {}
    for label, overhead in (('measured_overhead', measured), ('allowance_overhead', allowance)):
        pre = overhead['installation'] + overhead['model_startup'] + overhead['other_pre_question']
        headroom[label] = round((admission - pre) / seconds(withheld_rows, 'key_x2'), 2)
    calls = sum(len(rows) for _, rows in phases)
    report.update(summary={
        'scheduled_calls': calls, 'distinct_requests': len(report['requests']),
        'prompt_tokens_scheduled': sum(r['prompt_tokens'] for _, rows in phases for r in rows),
        'max_prompt_tokens': max(r['prompt_tokens'] for r in report['requests']),
        'all_within_limits': all(r['within_limits'] for r in report['requests']),
        'calls_by_phase': {phase: len(rows) for phase, rows in phases}},
        v1_measurements=fit,
        runtime_scenarios={'status': 'planning scenarios from v1 measured timings of a different workload; not '
                                     'guarantees. Admission control, not these figures, protects the deadline.',
                           'first_cell_overhead_measured_seconds': measured,
                           'first_cell_overhead_allowance_seconds': allowance,
                           'allowance_factors': ALLOWANCE_FACTORS, 'minimum_allowance_seconds': MIN_ALLOWANCE_SECONDS,
                           'cleanup_reserve_seconds': CLEANUP_RESERVE_SECONDS,
                           'cleanup_reserve_note': 'separate from every allowance; no estimate consumes it',
                           'admission_cutoff_seconds': admission,
                           'withheld_rate_headroom_factor': headroom, 'scenarios': scenarios})
    REPORT.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'summary': report['summary'], 'v1_measurements': fit, 'measured': measured,
                      'allowance': allowance, 'headroom': headroom, 'scenarios': scenarios}, indent=1))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('tokenize', 'estimate'))
    tokenize() if parser.parse_args().operation == 'tokenize' else estimate()
