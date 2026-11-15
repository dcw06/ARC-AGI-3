"""Results of the bp35 level-2 runs: one file with every number the report uses.

For each finished run it reads the event log and adds one thing the log does not hold: at every turn on
level 2 where the agent chose an action, was a game over one action away? That is found by trying, on a
copy of the local game at that exact position, both moves, the undo and a click on every third cell (the
tiles are five cells wide, so every tile is hit). No model is called.

    level2_results.py <out.json> <run folder>...

Usage (project environment), from the repository root.
"""
import copy
import json
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.memory_fix_v1 import bp35_local, continue_bp35  # noqa: E402

GRID = range(1, 64, 3)
DANGER = ('spike', 'hazard', 'game_over', 'game over', 'dies', 'died', 'fatal', 'destroy', 'deadly', 'lethal')


def fatal_options(game):
    """The single actions that end the game from this position: (moves, clicked cells)."""
    moves, cells = [], []
    for action_id in (3, 4, 7):
        if bp35_local.perform(copy.deepcopy(game), {'action_id': action_id}).state.name == 'GAME_OVER':
            moves.append(action_id)
    for y in GRID:
        for x in GRID:
            click = {'action_id': 6, 'action_data': {'x': x, 'y': y}}
            if bp35_local.perform(copy.deepcopy(game), click).state.name == 'GAME_OVER':
                cells.append((x, y))
    return moves, cells


def danger_status(reply):
    """'supported', 'tentative' or None: the strongest status of a note that mentions the danger."""
    found = [h['status'] for h in reply.get('hypotheses', ()) if any(w in h['statement'].lower() for w in DANGER)]
    if any(s.startswith('supported') for s in found):
        return 'supported'
    return 'tentative' if found else None


def one_run(folder):
    folder = Path(folder)
    events = [json.loads(line) for line in (folder / 'events.jsonl').read_text().splitlines()]
    steps = [e for e in events if e['kind'] == 'transition']
    replies, index = {}, None
    usage = []
    for event in events:
        if event['kind'] == 'model_entered':
            index = event['action_index']
        elif event['kind'] == 'model_returned':
            replies[index] = json.loads(event['content'])
            used = event['metadata']['usage']
            usage.append((int(used['input_tokens']) + int(used.get('cache_creation_input_tokens') or 0)
                          + int(used.get('cache_read_input_tokens') or 0), int(used['output_tokens'])))

    game = bp35_local.game_class()()
    bp35_local.perform(game, {'action_id': 0})
    first = continue_bp35.LEVEL_ONE
    turns, deaths = [], []
    for n, step in enumerate(steps):
        on_level_two = step['before']['levels_completed'] == 1
        chosen_by_model = on_level_two and step['before']['state'] != 'GAME_OVER'
        if chosen_by_model:
            moves, cells = fatal_options(game)
            died = step['after']['state'] == 'GAME_OVER'
            reply = replies.get(n, {})
            turn = {'level_2_action': n - first + 1, 'action': step['action'],
                    'fatal_moves': moves, 'fatal_click_cells': len(cells), 'a_game_over_was_one_action_away': bool(moves or cells),
                    'ended_the_game': died, 'earlier_game_overs': len(deaths),
                    'danger_note': danger_status(reply), 'lesson_check': reply.get('lesson_check'),
                    'game_over_lesson': reply.get('game_over_lesson')}
            turns.append(turn)
            if died:
                after = replies.get(n + 2, {})
                deaths.append({'level_2_action': n - first + 1, 'action': step['action'],
                               'danger_note_when_choosing': danger_status(reply),
                               'notes_when_choosing': reply.get('hypotheses'),
                               'notes_on_the_next_turn': after.get('hypotheses'),
                               'lesson_written': after.get('game_over_lesson')})
        result = bp35_local.perform(game, step['action'])
        if result.state.name != step['after']['state'] or int(result.levels_completed) != step['after']['levels_completed']:
            raise SystemExit('%s: the local game differs from the log at action %d' % (folder.name, n + 1))

    def exposure(rows):
        near = [t for t in rows if t['a_game_over_was_one_action_away']]
        return {'turns': len(rows), 'turns_one_action_from_a_game_over': len(near),
                'of_those_the_agent_took_the_fatal_action': sum(t['ended_the_game'] for t in near)}

    row = continue_bp35.summary(folder)
    row.update({
        'input_tokens': sum(u[0] for u in usage), 'output_tokens': sum(u[1] for u in usage),
        'output_per_call_median': round(statistics.median(u[1] for u in usage)),
        'before_the_first_game_over': exposure([t for t in turns if t['earlier_game_overs'] == 0]),
        'after_the_first_game_over': exposure([t for t in turns if t['earlier_game_overs'] > 0]),
        'deaths': deaths, 'turns': turns})
    return row


def main(out_path, folders):
    with ProcessPoolExecutor(max_workers=len(folders)) as pool:
        runs = list(pool.map(one_run, folders))
    Path(out_path).write_text(json.dumps({'runs': runs}, indent=1) + '\n')
    for run in runs:
        print(json.dumps({k: v for k, v in run.items() if k not in ('deaths', 'turns')}))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
