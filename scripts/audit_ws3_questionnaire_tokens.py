"""Exact prompt-token audit and bounded runtime scenarios for the WS3 transition questionnaire draft (no model calls).

tokenize (pinned tokenizer env): every scheduled request's prompt tokens, the key answer's completion tokens, and
    the longest schema-valid answer against max_tokens.
estimate (any env): scenarios fitted to the v2 live attempt's measured cache-disabled calls, with explicit
    first-cell overhead measured in v2 and planning allowances (scripts/audit_evidence_comprehension_v3_tokens.py,
    unchanged), in schedule order, against the 3,000 s admission cutoff. The 300 s cleanup reserve is never spent.

The raw-frame workload differs from Workstream 1's compact questions: prompts carry whole frame sequences. The fit is
per call, per prompt token and per completion token, so longer prompts are charged, but it was measured on shorter
prompts. These are planning figures; admission control, not the estimate, protects the deadline.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REPORT = ROOT / 'reports/ws3_questionnaire_token_audit.json'
TOKENIZER = ROOT / '.cache/phase4-tokenizer'
PROMPT_CEILING, CONTEXT = 60000, 65536


def requests():
    from research.transition_evidence_v1 import questionnaire as Q
    built = Q.build()
    by_id = {p['probe_id']: p for p in built['probes']}
    return built, {pid: (p, Q.build_request(built['contexts'][p['context_id']], p)) for pid, p in by_id.items()}


def tokenize():
    from transformers import AutoTokenizer
    from research.transition_evidence_v1 import questionnaire as Q
    tokenizer = AutoTokenizer.from_pretrained(str(TOKENIZER), local_files_only=True, trust_remote_code=False)
    caps = {}
    for family, answers in Q.ANSWERS.items():
        longest = max(len(tokenizer.encode(json.dumps({'answer': a}, indent=4), add_special_tokens=False)) + 1
                      for a in answers)
        caps[family] = {'longest_valid_answer_tokens_pretty': longest, 'max_tokens': 32, 'covers': 32 >= longest}
    _, table = requests()
    rows = []
    for pid, (p, request) in table.items():
        ids = tokenizer.apply_chat_template(request['messages'], tokenize=True, add_generation_prompt=True,
                                            truncation=False, **request['chat_template_kwargs'])
        key = json.dumps({'answer': p['key']}, separators=(',', ':'))
        rows.append({'probe_id': pid, 'partition': p['partition'], 'condition': p['condition'], 'family': p['family'],
                     'prompt_tokens': len(ids), 'max_tokens': request['max_tokens'],
                     'key_completion_tokens': len(tokenizer.encode(key, add_special_tokens=False)) + 1,
                     'within_limits': len(ids) <= PROMPT_CEILING and len(ids) + request['max_tokens'] <= CONTEXT})
    REPORT.write_text(json.dumps({'tokenizer': 'pinned Qwen3-VL-30B-A3B-Instruct-FP8 tokenizer', 'max_tokens_check': caps,
                                  'requests': rows}, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'requests': len(rows), 'max_prompt_tokens': max(r['prompt_tokens'] for r in rows),
                      'all_within_limits': all(r['within_limits'] for r in rows),
                      'caps_cover': all(c['covers'] for c in caps.values())}))


def estimate():
    from scripts.audit_evidence_comprehension_v3_tokens import (ALLOWANCE_FACTORS, CLEANUP_RESERVE_SECONDS,
                                                                COMPLETION_SLACK, INTERNAL_SECONDS,
                                                                MIN_ALLOWANCE_SECONDS, v2_measurements)
    report = json.loads(REPORT.read_bytes())
    built, _ = requests()
    rows = {r['probe_id']: r for r in report['requests']}
    fit = v2_measurements()
    measured = fit['overhead_measured_seconds']
    allowance = {k: round(max(MIN_ALLOWANCE_SECONDS, v * ALLOWANCE_FACTORS[k])) for k, v in measured.items()}
    admission = INTERNAL_SECONDS - CLEANUP_RESERVE_SECONDS

    def seconds(items, completion):
        return sum(fit['fit_seconds_per_call'] + fit['fit_seconds_per_prompt_token'] * r['prompt_tokens']
                   + fit['fit_seconds_per_completion_token'] * (r['max_tokens'] if completion == 'cap' else
                                                                min(r['max_tokens'], r['key_completion_tokens'] * COMPLETION_SLACK))
                   for r in items)
    phases = [(f"{b['partition']}/{b['pass']}", [rows[i] for i in b['probe_ids']]) for b in built['schedule']]
    scenarios = {}
    for name, overhead, factor, completion in (('measured_overhead_v2_rates', measured, 1.0, 'key_x2'),
                                               ('allowance_overhead_v2_rates', allowance, 1.0, 'key_x2'),
                                               ('allowance_overhead_two_times_slower', allowance, 2.0, 'key_x2'),
                                               ('allowance_overhead_three_times_slower_every_call_at_cap', allowance, 3.0, 'cap')):
        elapsed = overhead['installation'] + overhead['model_startup'] + overhead['other_pre_question']
        row = {'pre_question_seconds': round(elapsed)}
        for phase, items in phases:
            elapsed += factor * seconds(items, completion)
            row[phase + '_ends_at_seconds'] = round(elapsed)
        end = elapsed + overhead['post_question_finalization']
        withheld_end = max(v for k, v in row.items() if k.startswith('withheld/'))
        scenarios[name] = {**row, 'first_cell_end_seconds': round(end),
                           'withheld_fits_admission_cutoff': withheld_end <= admission,
                           'first_cell_fits_before_cleanup_reserve': end <= admission}
    summary = {'scheduled_calls': sum(len(i) for _, i in phases),
               'prompt_tokens_scheduled': sum(r['prompt_tokens'] for _, i in phases for r in i),
               'max_prompt_tokens': max(r['prompt_tokens'] for r in rows.values()),
               'prompt_tokens_by_partition_max': {part: max(r['prompt_tokens'] for r in rows.values() if r['partition'] == part)
                                                  for part in ('withheld', 'development', 'transfer')},
               'calls_by_phase': {phase: len(i) for phase, i in phases}}
    report.update(summary=summary, v2_measurements=fit, runtime_scenarios={
        'status': 'planning scenarios fitted to v2 measured calls on shorter prompts; not guarantees',
        'first_cell_overhead_measured_seconds': measured, 'first_cell_overhead_allowance_seconds': allowance,
        'cleanup_reserve_seconds': CLEANUP_RESERVE_SECONDS, 'admission_cutoff_seconds': admission,
        'scenarios': scenarios})
    REPORT.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'summary': summary, 'allowance': allowance, 'scenarios': scenarios}, indent=1))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('tokenize', 'estimate'))
    tokenize() if parser.parse_args().operation == 'tokenize' else estimate()
