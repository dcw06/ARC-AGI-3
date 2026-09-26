"""Exact prompt-token audit and cache-disabled runtime scenarios for evidence comprehension v1 (no model calls).

tokenize (pinned tokenizer env): count every exported request's prompt tokens, and each key answer's
    completion tokens, with the frozen Qwen3-VL tokenizer (requests from
    build_evidence_comprehension_v1.py --export-requests).
estimate (any env): combine the counts with throughput bounds measured in the archived
    action-effect-history run, plus pessimistic stress scenarios.

Measured bounds (cached-service timings are never used as a prefill bound):
- decode: each call's completion_tokens / total latency is a lower bound on decode throughput, which
  prefix caching does not affect; the maximum over all 144 archived calls is used;
- uncached prefill: the first call of an episode on a newly started game had no cached grid prefix;
  attributing that call's whole latency to prefill bounds throughput from below. The slowest such
  call is used. Those prompts were ~8.8k tokens, so 26k-token prompts may prefill more slowly per
  token; the stress scenarios cover that.
"""
import argparse
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REQUESTS = ROOT / '.cache/evidence_comprehension_v1_requests.jsonl'
REPORT = ROOT / 'reports/evidence_comprehension_v1_token_audit.json'
TOKENIZER = ROOT / '.cache/phase4-tokenizer'
ARCHIVE_LOCK = ROOT / 'reports/action_effect_history_v1_archive.json'
EPISODES = 'reports/runs/action-effect-history-v1/download/action-effect-history-v1/worker/run/episodes/'
RUN_ORDER = ('b1-ar25-baseline', 'b1-ar25-history', 'b1-s5i5-baseline', 'b1-s5i5-history', 'b1-wa30-baseline',
             'b1-wa30-history', 'b2-wa30-history', 'b2-wa30-baseline', 'b2-s5i5-history', 'b2-s5i5-baseline',
             'b2-ar25-history', 'b2-ar25-baseline')
PROMPT_CEILING, CONTEXT = 60000, 65536
PASSES = 2
COMPLETION_SLACK = 2  # wrong answers can be longer than the key; max_tokens caps every call
OVERHEAD_SECONDS_PER_CALL = 0.15
STARTUP_SECONDS, CLEANUP_RESERVE_SECONDS, INTERNAL_SECONDS = 403, 300, 3300
GATE = 'evidence_only'


def tokenize():
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(TOKENIZER), local_files_only=True, trust_remote_code=False)
    rows = []
    with REQUESTS.open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            request = row['request']
            ids = tokenizer.apply_chat_template(request['messages'], tokenize=True, add_generation_prompt=True,
                                                truncation=False, **request['chat_template_kwargs'])
            key_tokens = len(tokenizer.encode(row['key_response'], add_special_tokens=False)) + 1  # plus end token
            rows.append({'probe_id': row['probe_id'], 'condition': row['condition'], 'prompt_tokens': len(ids),
                         'key_completion_tokens': key_tokens, 'max_tokens': request['max_tokens'],
                         'within_limits': len(ids) <= PROMPT_CEILING and len(ids) + request['max_tokens'] <= CONTEXT})
    REPORT.write_text(json.dumps({'tokenizer': 'pinned Qwen3-VL-30B-A3B-Instruct-FP8 tokenizer (.cache/phase4-tokenizer)',
                                  'requests': rows}, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'requests': len(rows), 'max_prompt_tokens': max(r['prompt_tokens'] for r in rows),
                      'max_key_completion_tokens': max(r['key_completion_tokens'] for r in rows),
                      'all_within_limits': all(r['within_limits'] for r in rows)}))


def measured_bounds():
    lock = json.loads(ARCHIVE_LOCK.read_bytes())
    decode, cold, previous = 0.0, [], None
    with zipfile.ZipFile(ROOT / lock['archive']) as bundle:
        for name in RUN_ORDER:
            episode = json.loads(bundle.read(EPISODES + name + '.json'))
            for i, call in enumerate(episode['calls']):
                latency = call['returned_at'] - call['started_at']
                decode = max(decode, call['server_completion_tokens'] / latency)
                if i == 0 and episode['game_id'] != previous:
                    cold.append({'episode': name, 'prompt_tokens': call['server_prompt_tokens'],
                                 'latency_seconds': round(latency, 3),
                                 'prefill_lower_bound_tokens_per_second': round(call['server_prompt_tokens'] / latency)})
            previous = episode['game_id']
    return {'source': 'action-effect-history v1 archive ' + lock['archive_sha256'],
            'decode_lower_bound_tokens_per_second': round(decode, 1),
            'cold_first_calls': cold,
            'uncached_prefill_lower_bound_tokens_per_second': min(c['prefill_lower_bound_tokens_per_second'] for c in cold)}


def seconds(rows, prefill, decode, completion):
    total = 0.0
    for r in rows:
        tokens = r['max_tokens'] if completion == 'max_tokens' else min(r['max_tokens'], r['key_completion_tokens'] * COMPLETION_SLACK)
        total += r['prompt_tokens'] / prefill + tokens / decode + OVERHEAD_SECONDS_PER_CALL
    return total


def estimate():
    report = json.loads(REPORT.read_bytes())
    rows = report['requests']
    by_condition = {}
    for r in rows:
        c = by_condition.setdefault(r['condition'], {'requests': 0, 'prompt_tokens': 0, 'max_prompt_tokens': 0,
                                                     'key_completion_tokens': 0})
        c['requests'] += 1
        c['prompt_tokens'] += r['prompt_tokens']
        c['key_completion_tokens'] += r['key_completion_tokens']
        c['max_prompt_tokens'] = max(c['max_prompt_tokens'], r['prompt_tokens'])
    bounds = measured_bounds()
    admission = INTERNAL_SECONDS - CLEANUP_RESERVE_SECONDS
    gate = [r for r in rows if r['condition'] == GATE]
    rest = [r for r in rows if r['condition'] != GATE]
    scenarios = {}
    for name, prefill, decode, completion in (
            ('measured_bounds', bounds['uncached_prefill_lower_bound_tokens_per_second'],
             bounds['decode_lower_bound_tokens_per_second'], 'key_x2'),
            ('stress_slow_prefill_and_decode', 2500, 40, 'key_x2'),
            ('stress_every_call_at_max_tokens', 2500, 40, 'max_tokens')):
        gate_phase = PASSES * seconds(gate, prefill, decode, completion)
        descriptive = PASSES * seconds(rest, prefill, decode, completion)
        scenarios[name] = {'prefill_tokens_per_second': prefill, 'decode_tokens_per_second': decode,
                           'completion_tokens': completion,
                           'gate_both_passes_seconds': round(gate_phase),
                           'descriptive_both_passes_seconds': round(descriptive),
                           'startup_plus_gate_seconds': round(STARTUP_SECONDS + gate_phase),
                           'startup_plus_everything_seconds': round(STARTUP_SECONDS + gate_phase + descriptive),
                           'gate_fits_admission_cutoff': STARTUP_SECONDS + gate_phase <= admission,
                           'everything_fits_admission_cutoff': STARTUP_SECONDS + gate_phase + descriptive <= admission}
    report.update(summary={
        'requests_per_pass': len(rows), 'passes': PASSES, 'calls': len(rows) * PASSES,
        'prompt_tokens_per_pass': sum(r['prompt_tokens'] for r in rows),
        'prompt_tokens_total': PASSES * sum(r['prompt_tokens'] for r in rows),
        'max_prompt_tokens': max(r['prompt_tokens'] for r in rows),
        'all_within_limits': all(r['within_limits'] for r in rows), 'by_condition': by_condition},
        measured_bounds=bounds,
        runtime_scenarios={'schedule': 'evidence_only pass 1, evidence_only pass 2 (reversed), then the descriptive '
                                       'groups pass 1 and pass 2 (reversed); the runner stops admitting calls at the '
                                       'cutoff, so a shortfall can only cut descriptive groups',
                           'overhead_seconds_per_call': OVERHEAD_SECONDS_PER_CALL, 'startup_seconds': STARTUP_SECONDS,
                           'admission_cutoff_seconds': admission, 'scenarios': scenarios})
    REPORT.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'summary': {k: v for k, v in report['summary'].items() if k != 'by_condition'},
                      'measured_bounds': {k: v for k, v in bounds.items() if k != 'cold_first_calls'},
                      'scenarios': scenarios}, indent=1))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('tokenize', 'estimate'))
    args = parser.parse_args()
    tokenize() if args.operation == 'tokenize' else estimate()
