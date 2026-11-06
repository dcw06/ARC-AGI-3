"""Read-only progress of the newest (or a given) Claude ARC run, from its local evidence log.

    python3 scripts/claude_arc_progress.py            # newest run under .cache/claude_arc_runs
    python3 scripts/claude_arc_progress.py <folder>   # a specific run

The public scorecard page only works after the run closes its scorecard; this works while it is running.
"""
import json
from pathlib import Path
import sys
import time

root = Path(__file__).resolve().parents[1] / '.cache/claude_arc_runs'
folder = Path(sys.argv[1]) if len(sys.argv) > 1 else max(
    (p for p in root.iterdir() if p.is_dir() and (p / 'events.jsonl').exists()), key=lambda p: p.stat().st_mtime)
rows = []
for line in (folder / 'events.jsonl').read_text().splitlines():
    try:
        rows.append(json.loads(line))
    except ValueError:
        pass  # a line being written right now

config = next(r['config'] for r in rows if r['kind'] == 'configuration')
selected = next((r['selected'] for r in rows if r['kind'] == 'inventory'), [])
card = next((r['card_id'] for r in rows if r['kind'] == 'scorecard_open_acknowledged'), None)
games, order = {}, []
for r in rows:
    game = r.get('game_id')
    if r['kind'] == 'make_entered':
        games[game] = {'actions': 0, 'levels': 0, 'win_levels': None, 'state': 'starting', 'resets': 0, 'note': ''}
        order.append(game)
    elif r['kind'] == 'initial_observation':
        games[game].update(win_levels=r['observation']['win_levels'], state=r['observation']['state'])
    elif r['kind'] == 'transition':
        g = games[game]
        g['actions'] += 1
        g['resets'] += r['action']['action_id'] == 0
        g['levels'] = r['after']['levels_completed']
        g['state'] = r['after']['state']
    elif r['kind'] == 'game_failed':
        games[game]['note'] = 'failed: ' + r.get('error_type', '?')
done = next((r['summary'] for r in rows if r['kind'] == 'summary'), None)
calls = sum(r['kind'] == 'model_entered' for r in rows)
retries = sum(r['kind'] == 'model_failed_retrying' for r in rows)

print('Run:', folder.name, '| model', config['model'], config['effort'], '| cap', config['max_actions_per_game'], 'actions/game')
print('Scorecard:', 'https://arcprize.org/scorecards/' + card if card else 'not opened yet', '(viewable after the run closes it)')
print('Status:', 'FINISHED' if done else 'running', '| last event %d s ago' % (time.time() - (folder / 'events.jsonl').stat().st_mtime))
print('Games started %d of %d | model calls %d | retries %d' % (len(order), len(selected), calls, retries))
for game in order:
    g = games[game]
    print('  %-16s levels %d/%s  actions %3d  %s%s %s' % (game, g['levels'], g['win_levels'], g['actions'], g['state'],
          ' resets %d' % g['resets'] if g['resets'] else '', g['note']))
if done:
    card_result = done.get('official_scorecard') or {}
    if isinstance(card_result, dict) and 'score' in card_result:
        print('Official score at close:', card_result['score'])
    if done.get('problems'):
        print('Problems:', '; '.join(done['problems']))
