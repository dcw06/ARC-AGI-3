"""Token usage per model call from public ARC replay recordings. Streams each recording; keeps no frames.

Every step of a public recording carries the usage of the model call that produced it
(action_input.reasoning.usage): input tokens, cached input tokens, output tokens, reasoning tokens.
This keeps, per step: the action, the state, levels completed, and those four numbers.

Usage: fetch_usage.py <label> [<label> ...]   labels as in .cache/arc_loss_audit/rec/ (e.g. astra-standard-high)
Writes .cache/token_usage/<label>__<game>.json
"""
import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REC = ROOT / '.cache/arc_loss_audit/rec'
OUT = ROOT / '.cache/token_usage'


def fetch(job):
    label, game, guid = job
    target = OUT / ('%s__%s.json' % (label, game))
    if target.exists():
        return 'have ' + target.name
    request = urllib.request.Request('https://arcprize.org/api/recordings/%s/%s' % (game, guid),
                                     headers={'User-Agent': 'arc-audit/0.1'})
    for attempt in range(3):
        try:
            steps = []
            with urllib.request.urlopen(request, timeout=180) as response:
                for line in response:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)['data']
                    act = data.get('action_input') or {}
                    reasoning = act.get('reasoning')
                    while isinstance(reasoning, str):
                        try:
                            reasoning = json.loads(reasoning)
                        except Exception:
                            break
                    usage = reasoning.get('usage') if isinstance(reasoning, dict) else None
                    row = {'a': act.get('id'), 'state': data.get('state'), 'lc': data.get('levels_completed')}
                    if isinstance(usage, dict):
                        row.update(inp=usage.get('input_tokens'),
                                   cached=(usage.get('input_tokens_details') or {}).get('cached_tokens'),
                                   out=usage.get('output_tokens'),
                                   reasoning=(usage.get('output_tokens_details') or {}).get('reasoning_tokens'),
                                   compute_units=usage.get('compute_units'))
                    steps.append(row)
            target.write_text(json.dumps({'label': label, 'game': game, 'guid': guid, 'steps': steps}))
            return 'ok %s steps=%d with_usage=%d' % (target.name, len(steps), sum('inp' in s for s in steps))
        except Exception as error:
            problem = repr(error)
    return 'FAIL %s %s %s' % (label, game, problem)


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = []
    for label in sys.argv[1:]:
        for path in sorted(REC.glob(label + '__*.json')):
            meta = json.loads(path.read_text())
            jobs.append((label, meta['game'], meta['guid']))
    print(len(jobs), 'recordings', flush=True)
    with ThreadPoolExecutor(5) as pool:
        for message in pool.map(fetch, jobs):
            print(message, flush=True)
    print('DONE', flush=True)
