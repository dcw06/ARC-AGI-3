"""Send the four readability requests (A twice, B twice). Does nothing without --send.

Usage: readability_run.py <report_dir>            # dry run: prints the plan and limits
       readability_run.py <report_dir> --send     # only after the user has explicitly authorised it
Limits: exactly 4 requests, no retries, 8,000 output tokens each (thinking included), 300 s per request,
and a spending stop at $0.80 worked out from reported usage at list price. Each request is a fresh,
stateless Messages call with identical settings. No fallback model is configured: a refusal or an error
is recorded as that request's result.
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

PLAN, SEED, TIMEOUT_S, CAP_USD = ['A', 'A', 'B', 'B'], 20261114, 300.0, 0.80
USD_PER_MTOK = {'input': 4.0, 'output': 20.0}  # claude-opus-5-5 list price


def cost(usage):
    read = usage.get('cache_read_input_tokens') or 0
    write = usage.get('cache_creation_input_tokens') or 0
    return ((usage['input_tokens'] + write * 1.25 + read * 0.05) * USD_PER_MTOK['input']
            + usage['output_tokens'] * USD_PER_MTOK['output']) / 1e6


def main(report_dir, send):
    report_dir = Path(report_dir)
    requests = json.loads((report_dir / 'frozen/requests.json').read_text())
    counts = json.loads((report_dir / 'frozen/token_counts.json').read_text())
    order = [(name, PLAN[:i].count(name) + 1) for i, name in enumerate(PLAN)]
    random.Random(SEED).shuffle(order)
    worst = {n: (counts['inputs'][n]['full_request_input_tokens'] * USD_PER_MTOK['input']
                 + requests[n]['max_tokens'] * USD_PER_MTOK['output']) / 1e6 for n in requests}
    print('order', order, '| worst case per request', {k: round(v, 3) for k, v in worst.items()},
          '| worst case total $%.2f | stop at $%.2f' % (sum(worst[n] for n, _ in order), CAP_USD))
    print('settings', {k: v for k, v in requests['A'].items() if k not in ('system', 'messages')})
    if not send:
        print('dry run: nothing sent')
        return
    existing = list((report_dir / 'responses').glob('*.json'))
    if existing:
        raise SystemExit('responses already exist; refusing to send again: %s' % [p.name for p in existing])
    client = anthropic.Anthropic(api_key=api_key(), max_retries=0, timeout=TIMEOUT_S)
    spent = 0.0
    for name, repeat in order:
        tag = '%s%d' % (name, repeat)
        if spent + worst[name] > CAP_USD:
            result = {'tag': tag, 'outcome': 'not sent: spending stop', 'spent_before_usd': spent}
        else:
            start = time.time()
            try:
                response = client.messages.create(**requests[name])
                body = response.model_dump(mode='json')
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
        result.update(input=name, repeat=repeat, sent_at=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                      request_settings={k: v for k, v in requests[name].items() if k not in ('system', 'messages')})
        (report_dir / 'responses' / ('%s.json' % tag)).write_text(json.dumps(result, indent=1))
        print(tag, result['outcome'], result.get('stop_reason'), result.get('usage'), 'spent $%.3f' % spent)


if __name__ == '__main__':
    main(sys.argv[1], '--send' in sys.argv[2:])
