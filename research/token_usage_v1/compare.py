"""Token usage per model call, action and completed level: public GPT-6 Astra and Opus 5 runs, and our Opus 5.5 runs.

Sources:
  public recordings   .cache/token_usage/<label>__<game>.json, written by fetch_usage.py from each step's own
                      usage record (input tokens, cached input tokens, output tokens, reasoning tokens)
  our 6 November run  the usage the Claude CLI returned for each of its calls (events.jsonl)
  our Tycho run       the cumulative usage Tycho recorded for bp35 (results.json), two games only

"Input" is every token sent to the model in a call, cached or not. "Cached" is the part the provider read
from its cache. "Output" includes reasoning (OpenAI) or thinking (Anthropic) tokens.

Usage: compare.py <out.json>
"""
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
USAGE = ROOT / '.cache/token_usage'
NOV6 = ROOT / '.cache/claude_arc_runs/opus55-competition-20261106T054112Z'
TYCHO = ROOT / 'reports/tycho_opus55_matched_v1/results.json'
NAMES = {'astra-standard-high': 'GPT-6 Astra, official standard harness, high',
         'astra-adapter-high': 'GPT-6 Astra, provider adapter harness, high',
         'opus5-standard-high': 'Claude Opus 5, official standard harness, high',
         'opus55-ours': 'Claude Opus 5.5, our harness (6 Nov, 100-action cap), high'}


def summarise(calls, actions, levels, games, wins):
    """calls: [(input, cached, output, reasoning or None)]"""
    inp = [c[0] for c in calls]
    out = [c[2] for c in calls]
    reasoning = [c[3] for c in calls if c[3] is not None]
    total_in, total_out, cached = sum(inp), sum(out), sum(c[1] or 0 for c in calls)
    return {'games': games, 'games_won': wins, 'levels_completed': levels, 'actions': actions, 'model_calls': len(calls),
            'input_total': total_in, 'input_cached': cached, 'input_not_cached': total_in - cached,
            'output_total': total_out, 'reasoning_total': sum(reasoning) if reasoning else None,
            'input_per_call_median': round(statistics.median(inp)), 'input_per_call_mean': round(statistics.mean(inp)),
            'input_per_call_max': max(inp),
            'output_per_call_median': round(statistics.median(out)), 'output_per_call_mean': round(statistics.mean(out)),
            'input_per_action': round(total_in / actions), 'output_per_action': round(total_out / actions),
            'input_per_level': round(total_in / levels) if levels else None,
            'not_cached_per_level': round((total_in - cached) / levels) if levels else None,
            'output_per_level': round(total_out / levels) if levels else None}


def public(label):
    calls, actions, levels, games, wins, missing = [], 0, 0, 0, 0, 0
    per_game = {}
    for path in sorted(USAGE.glob(label + '__*.json')):
        steps = json.loads(path.read_text())['steps'][1:]          # the first step is the opening RESET
        mine = [(s['inp'], s.get('cached') or 0, s['out'], s.get('reasoning')) for s in steps if s.get('inp') is not None]
        missing += len(steps) - len(mine)
        calls += mine
        actions += len(steps)
        levels += steps[-1]['lc'] or 0
        wins += steps[-1]['state'] == 'WIN'
        games += 1
        per_game[path.stem.split('__')[1].split('-')[0]] = {
            'actions': len(steps), 'levels': steps[-1]['lc'] or 0, 'input': sum(c[0] for c in mine),
            'cached': sum(c[1] for c in mine), 'output': sum(c[2] for c in mine)}
    row = summarise(calls, actions, levels, games, wins)
    row['steps_without_usage'] = missing
    return row, per_game


def ours():
    calls, per_game = [], defaultdict(lambda: {'input': 0, 'cached': 0, 'output': 0})
    with (NOV6 / 'events.jsonl').open() as handle:
        for line in handle:
            if '"kind":"model_returned"' not in line:
                continue
            event = json.loads(line)
            usage = event['metadata']['usage']
            model = event['metadata']['model_usage']['claude-opus-5-5']
            cached = int(usage.get('cache_read_input_tokens') or 0)
            inp = int(usage['input_tokens']) + int(usage.get('cache_creation_input_tokens') or 0) + cached
            calls.append((inp, cached, int(usage['output_tokens']), int(model.get('thinkingTokens') or 0)))
            game = per_game[event['game_id'].split('-')[0]]
            game['input'] += inp
            game['cached'] += cached
            game['output'] += int(usage['output_tokens'])
    summary = json.loads((NOV6 / 'summary.json').read_text())
    for game in summary['games']:
        per_game[game['game_id'].split('-')[0]].update(actions=game['actions_acknowledged'], levels=game['levels_completed'])
    row = summarise(calls, sum(g['actions_acknowledged'] for g in summary['games']),
                    sum(g['levels_completed'] for g in summary['games']), len(summary['games']),
                    sum(g['final_state'] == 'WIN' for g in summary['games']))
    return row, dict(per_game)


def main(out_path):
    result, games = {}, {}
    for label in ('astra-standard-high', 'astra-adapter-high', 'opus5-standard-high'):
        if list(USAGE.glob(label + '__*.json')):
            result[label], games[label] = public(label)
    result['opus55-ours'], games['opus55-ours'] = ours()
    tycho = json.loads(TYCHO.read_text())['bp35_continuation']
    result['opus55-tycho-bp35'] = {k: tycho['cap100'].get(k) for k in ('total_actions', 'levels_completed', 'cumulative_usage',
                                                                       'llm_calls_by_type_in_record',
                                                                       'cumulative_cost_usd_list_price')}
    Path(out_path).write_text(json.dumps({'names': NAMES, 'runs': result, 'by_game': games}, indent=1) + '\n')
    return result


if __name__ == '__main__':
    table = main(sys.argv[1])
    for label, row in table.items():
        print('==', NAMES.get(label, label))
        print('  ', json.dumps(row))
