"""Run the object ledger over the saved 6 November run without a model, to see that it behaves on real boards.

For every turn of every game it builds the request with object_ledger on and with it off, feeding the saved
replies. It reports how many looks are listed, how much the request grows, how long the controller takes, and
what the agent would have been shown at one turn of ls20 (after the refused step into the goal box).

Usage (project environment): dry_run.py <out.json>
"""
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'research'))
from agent.action import ActionDecision  # noqa: E402
from research.claude_arc_v1 import config as C, policy  # noqa: E402
from research.memory_fix_v1 import death_test as D  # noqa: E402

SAVED = ROOT / '.cache/claude_arc_runs/opus55-competition-20261106T054112Z/events.jsonl'


def main(out_path):
    games, pending = {}, None
    with SAVED.open() as handle:
        for line in handle:
            event = json.loads(line)
            kind = event['kind']
            if kind == 'initial_observation':
                games[event['game_id']] = {'first': event['observation'], 'steps': [], 'replies': {}}
            elif kind == 'transition':
                games[event['game_id']]['steps'].append((event['action'], event['after']))
            elif kind == 'model_entered':
                pending = (event['game_id'], event['action_index'])
            elif kind == 'model_returned':
                games[pending[0]]['replies'][pending[1]] = json.loads(event['content'])
    base = json.loads(D.CONTROL.read_text())
    extra, looks, per_game, shown, total, moved = [], [], {}, None, 0, 0
    for game in sorted(games):
        g, began = games[game], time.time()
        prefix = game.split('-')[0]
        on = policy.Policy(C.Config(**{**base, 'mode': 'online', 'games': [prefix], 'object_ledger': True}))
        off = policy.Policy(C.Config(**{**base, 'mode': 'online', 'games': [prefix]}))
        before = D.observation(g['first'])
        for i, (action, value) in enumerate(g['steps']):
            after = D.observation(value)
            decision = ActionDecision(action['action_id'], dict(action['action_data']), source='controller_resume')
            saved = g['replies'].get(i)
            if saved:
                with_it = json.loads(on.request(before)['messages'][1]['content'])
                without = off.request(before)['messages'][1]['content']
                things = with_it['evidence'].get('things') or {'looks': []}
                total += 1
                looks.append(len(things['looks']))
                moved += 'view_moved_at' in things
                extra.append(len(json.dumps(with_it, separators=(',', ':'))) - len(without))
                if prefix == 'ls20' and i == 93:
                    shown = things
            on.observe(before, decision, after, saved or {'action': action, 'hypotheses': list(on.hypotheses)})
            off.observe(before, decision, after, saved or {'action': action, 'hypotheses': list(off.hypotheses)})
            before = after
        per_game[prefix] = {'looks_named': len(on.inventory.names), 'seconds': round(time.time() - began, 1)}
    result = {'requests_built': total, 'requests_after_a_view_move': moved,
              'looks_listed_median': statistics.median(looks), 'looks_listed_max': max(looks),
              'extra_characters_median': round(statistics.median(extra)), 'extra_characters_max': max(extra),
              'per_game': per_game, 'ls20_after_the_refused_step': shown}
    Path(out_path).write_text(json.dumps(result, indent=1) + '\n')
    return result


if __name__ == '__main__':
    result = main(sys.argv[1])
    print({k: v for k, v in result.items() if k not in ('per_game', 'ls20_after_the_refused_step')})
    print('looks named per game:', {g: v['looks_named'] for g, v in result['per_game'].items()})
    print('slowest games (seconds for 100 actions, both policies):', sorted(((v['seconds'], g) for g, v in result['per_game'].items()), reverse=True)[:4])
    for look in result['ls20_after_the_refused_step']['looks']:
        print('  ', json.dumps(look))
