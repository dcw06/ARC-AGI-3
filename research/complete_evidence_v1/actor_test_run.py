"""Send the six requests of the one-case actor prediction test. Does nothing without --send.

Usage: actor_test_run.py <test_dir>            # dry run: prints the plan and limits
       actor_test_run.py <test_dir> --send     # only after the user has explicitly authorised it
Limits: exactly 6 requests (none, useful, irrelevant; two each) in a seeded random order, each a fresh
stateless Messages call with identical settings; 8,000 output tokens each (thinking included); 300 s per
request; no retries; no fallback model; spending stop at $1.20 at list price from reported usage.
A refusal or an error is recorded as that request's result.
"""
import json
import random
import sys
import time
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research'))
from complete_evidence_v1.opus_count import api_key  # noqa: E402

SEED, TIMEOUT_S, CAP_USD = 20261115, 300.0, 1.20
USD_PER_MTOK = {'input': 4.0, 'output': 20.0}  # claude-opus-5-5 list price


def cost(usage):
    read = usage.get('cache_read_input_tokens') or 0
    write = usage.get('cache_creation_input_tokens') or 0
    return ((usage['input_tokens'] + write * 1.25 + read * 0.05) * USD_PER_MTOK['input']
            + usage['output_tokens'] * USD_PER_MTOK['output']) / 1e6


def main(test_dir, send):
    test = Path(test_dir)
    requests = json.loads((test / 'frozen/requests.json').read_text())
    design = json.loads((test / 'frozen/design.json').read_text())
    order = [(name, k + 1) for name, n in design['requests_planned'].items() for k in range(n)]
    random.Random(SEED).shuffle(order)
    worst = {n: (design['token_counts_estimates'][n]['full_request_input_tokens'] * USD_PER_MTOK['input']
                 + requests[n]['max_tokens'] * USD_PER_MTOK['output']) / 1e6 for n in requests}
    print('order', order)
    print('worst case per request', {k: round(v, 3) for k, v in worst.items()},
          '| worst case total $%.2f | stop at $%.2f' % (sum(worst[n] for n, _ in order), CAP_USD))
    print('settings', design['model_settings'])
    if not send:
        print('dry run: nothing sent')
        return
    out = test / 'responses'
    existing = list(out.glob('*.json'))
    if existing:
        raise SystemExit('responses already exist; refusing to send again: %s' % [p.name for p in existing])
    client = anthropic.Anthropic(api_key=api_key(), max_retries=0, timeout=TIMEOUT_S)
    spent = 0.0
    for position, (name, repeat) in enumerate(order, 1):
        tag = '%s_%d' % (name, repeat)
        if spent + worst[name] > CAP_USD:
            result = {'tag': tag, 'outcome': 'not sent: spending stop', 'spent_before_usd': spent}
        else:
            start = time.time()
            try:
                body = client.messages.create(**requests[name]).model_dump(mode='json')
                text = ''.join(b.get('text', '') for b in body['content'] if b['type'] == 'text')
                try:
                    answers = json.loads(text[text.index('{'):text.rindex('}') + 1])
                except ValueError:
                    answers = None
                spent += cost(body['usage'])
                result = {'tag': tag, 'outcome': 'response', 'stop_reason': body['stop_reason'], 'usage': body['usage'],
                          'cost_usd': round(cost(body['usage']), 4), 'answers': answers, 'text': text, 'response': body}
            except anthropic.APIError as error:  # recorded, not retried
                result = {'tag': tag, 'outcome': 'error', 'error': '%s: %s' % (type(error).__name__, str(error)[:500])}
            result['elapsed_seconds'] = round(time.time() - start, 1)
        result.update(condition=name, repeat=repeat, position_in_order=position, sent_at=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                      request_settings=design['model_settings'])
        (out / ('%s.json' % tag)).write_text(json.dumps(result, indent=1))
        print(tag, result['outcome'], result.get('stop_reason'), (result.get('usage') or {}).get('input_tokens'),
              (result.get('usage') or {}).get('output_tokens'), 'spent $%.3f' % spent)


if __name__ == '__main__':
    main(sys.argv[1], '--send' in sys.argv[2:])
