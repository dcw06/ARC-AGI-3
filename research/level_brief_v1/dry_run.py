"""Run the level brief over saved play without a model, to see how it behaves on real boards of all 25 games.

Part A, the saved 6 November run (our harness, 100 actions a game). Every turn's request is built with the
memory layers and the object ledger, once with level_brief and once without, feeding the saved replies. Where
a brief is due a placeholder is stored, so that the count of brief turns and the size of the later requests
are what a run would see. Reported: requests built, brief turns, growth of the request.

Part B, the public recordings of GPT-6 Astra with the provider harness (it completes most levels, so there
are many more level starts). At the first board of every level after the first: how many looks the listing
shows and how many of them it marks new. This is the check on the controller's part of the layer: a mark
that is on nearly everything, or on nothing, tells the agent nothing.

No game is singled out: the same numbers are reported for every game.

Usage (project environment): dry_run.py <out.json>
"""
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'research'))
from agent.action import ActionDecision  # noqa: E402
from recovery_v1 import traces  # noqa: E402
from research.claude_arc_v1 import config as C, policy, things  # noqa: E402
from research.memory_fix_v1 import death_test as D  # noqa: E402

SAVED = ROOT / '.cache/claude_arc_runs/opus55-competition-20261106T054112Z/events.jsonl'
LAYERS = {'game_over_lessons': True, 'no_effect_lessons': True, 'no_effect_wait': 4, 'lesson_check': True,
          'object_ledger': True}
PLACEHOLDER = {'won_by': 'placeholder ' * 12, 'different': 'placeholder ' * 20, 'why': 'placeholder ' * 20,
               'first': 'placeholder ' * 8}


def saved_games():
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
    return games


def marks(listing):
    looks = listing.get('looks', [])
    return {'looks_listed': len(looks), 'marked_new': sum(bool(look.get('new')) for look in looks),
            'not_listed': listing.get('looks_not_listed', 0), 'new_not_listed': listing.get('new_looks_not_listed', 0)}


def part_a():
    base, games = json.loads(D.CONTROL.read_text()), saved_games()
    built, brief_turns, extra, extra_at_brief, per_game, boards = 0, 0, [], [], {}, []
    for game in sorted(games):
        g, began, prefix = games[game], time.time(), game.split('-')[0]
        make = lambda **more: policy.Policy(C.Config(**{**base, 'mode': 'online', 'games': [prefix], **LAYERS, **more}))
        on, off = make(level_brief=True), make()
        before, starts = D.observation(g['first']), []
        for i, (action, value) in enumerate(g['steps']):
            after = D.observation(value)
            decision = ActionDecision(action['action_id'], dict(action['action_data']), source='controller_resume')
            saved = g['replies'].get(i)
            answer = dict(saved) if saved else None
            if saved:
                with_it = json.loads(on.request(before)['messages'][1]['content'])
                without = off.request(before)['messages'][1]['content']
                built += 1
                grown = len(json.dumps(with_it, separators=(',', ':'))) - len(without)
                if on.brief_state(before)[1]:
                    brief_turns += 1
                    extra_at_brief.append(grown)
                    shown = with_it['evidence'].get('completed_level') or {}
                    boards.append(bool(shown.get('board')))
                    starts.append({'level': before.levels_completed + 1, 'at_action': i + 1,
                                   'completed_board_shown': bool(shown.get('board')),
                                   'frames_the_completing_action_returned': shown.get('frames_returned'),
                                   **marks(with_it['evidence'].get('things') or {})})
                    answer['level_brief'] = PLACEHOLDER
                    answer['rule_notes'] = [{'rule': 'placeholder ' * 12, 'replaces': 0}]
                else:
                    extra.append(grown)
            on.observe(before, decision, after, answer or {'action': action, 'hypotheses': list(on.hypotheses)})
            off.observe(before, decision, after, saved or {'action': action, 'hypotheses': list(off.hypotheses)})
            before = after
        per_game[prefix] = {'brief_turns': starts, 'seconds': round(time.time() - began, 1)}
    return {'requests_built': built, 'brief_turns': brief_turns, 'brief_turns_showing_the_completed_board': sum(boards),
            'extra_characters_on_a_brief_turn_median': round(statistics.median(extra_at_brief)) if extra_at_brief else None,
            'extra_characters_on_other_turns_median': round(statistics.median(extra)),
            'extra_characters_on_other_turns_max': max(extra), 'per_game': per_game}


def part_b(source='astra-adapter-high'):
    recordings, rows = traces.load_recordings(), []
    for (name, game), trace in sorted(recordings.items()):
        if name != source:
            continue
        inventory, board, level = things.Inventory(), np.asarray(trace['initial'], dtype=np.uint8), 0
        inventory.listing(board)                             # the first level's first board is seen as well
        for n, step in enumerate(trace['steps'], 1):
            frame = np.asarray(step['frame'], dtype=np.uint8)
            if step['lc'] > level:
                level = step['lc']
                inventory.next_level()
                if step['state'] == 'NOT_FINISHED' and frame.ndim == 2:
                    rows.append({'game': game.split('-')[0], 'level': level + 1,
                                 **marks(inventory.listing(frame, mark_new=True))})
            elif step['a'] != 'RESET' and frame.ndim == 2 and board.shape == frame.shape:
                inventory.observe(board, [frame], 't%d' % n)
            board = frame
    shares = [r['marked_new'] / r['looks_listed'] for r in rows if r['looks_listed']]
    by_game = {}
    for r in rows:
        by_game.setdefault(r['game'], []).append('%d/%d' % (r['marked_new'], r['looks_listed']))
    return {'source': source, 'level_starts': len(rows), 'games': len(by_game),
            'with_no_look_marked': sum(r['marked_new'] == 0 and r['new_not_listed'] == 0 for r in rows),
            'with_every_listed_look_marked': sum(r['looks_listed'] > 0 and r['marked_new'] == r['looks_listed'] for r in rows),
            'with_one_to_three_marked': sum(1 <= r['marked_new'] <= 3 for r in rows),
            'share_of_listed_looks_marked_median': round(statistics.median(shares), 2) if shares else None,
            'marked_of_listed_at_each_level_start': by_game, 'rows': rows}


if __name__ == '__main__':
    result = {'saved_run': part_a(), 'recordings': part_b()}
    Path(sys.argv[1]).parent.mkdir(parents=True, exist_ok=True)
    Path(sys.argv[1]).write_text(json.dumps(result, indent=1) + '\n')
    a, b = result['saved_run'], result['recordings']
    print({k: v for k, v in a.items() if k != 'per_game'})
    print('slowest games (seconds):', sorted(((v['seconds'], g) for g, v in a['per_game'].items()), reverse=True)[:3])
    print({k: v for k, v in b.items() if k not in ('rows', 'marked_of_listed_at_each_level_start')})
    for game, values in b['marked_of_listed_at_each_level_start'].items():
        print('  ', game, ' '.join(values))
