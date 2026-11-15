"""What would each pilot condition send to the model on its first turn? Offline: no game, no model call.

Each condition's configuration is run against the saved November 6 boards. The controller repeats the
first 100 saved actions, checking every board, and builds the request for action 101. That request is
captured and the run is stopped there. The preview shows what differs from the control's request.

Usage (project environment): preview_pilot.py <out.json>
"""
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from arcengine import GameState

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from agent.state import Observation  # noqa: E402
from research.claude_arc_v1 import config as C, run  # noqa: E402
from research.claude_arc_v1.backends import Budget  # noqa: E402


class Stop(Exception):
    pass


class Capture:
    """Stands in for the model: keeps the first request and ends the run."""

    def __init__(self, c):
        self.config, self.budget, self.request, self.last_record = c, Budget(c), None, None

    def complete(self, request):
        self.request = request
        raise KeyboardInterrupt()   # ends the whole attempt at once; nothing is sent anywhere


class Saved:
    def __init__(self, games):
        self.games = games

    @staticmethod
    def observation(value):
        return Observation(value['game_id'], tuple(np.asarray(f, dtype=np.uint8) for f in value['frames']),
                           GameState[value['state']], value['levels_completed'], value['win_levels'], 'saved-guid',
                           tuple(value['available_actions']), value['full_reset'])

    def list_game_ids(self):
        return tuple(self.games)

    def open_scorecard(self, tags):
        return 'offline-preview'

    def bootstrap(self, game):
        return SimpleNamespace(observation=self.observation(self.games[game]['initial']), game_id=game, sent=0)

    def dispatch(self, client, decision):
        action, after = self.games[client.game_id]['steps'][client.sent]
        if {'action_id': decision.action_id, 'action_data': dict(decision.action_data)} != action:
            raise AssertionError('not the saved action')
        client.sent += 1
        client.observation = self.observation(after)
        return client.observation

    def finalize_client(self, client):
        pass

    def close_scorecard(self):
        return {'card_id': 'offline-preview'}


def load_saved(path, prefixes):
    games = {}
    with open(path) as handle:
        for line in handle:
            if '"kind":"transition"' not in line and '"kind":"initial_observation"' not in line:
                continue
            event = json.loads(line)
            game = event['game_id']
            if game.split('-')[0] not in prefixes:
                continue
            if event['kind'] == 'initial_observation':
                games[game] = {'initial': event['observation'], 'steps': []}
            else:
                games[game]['steps'].append((event['action'], event['after']))
    return games


def first_request(c, saved, game):
    one = C.Config(**{**c.public(), 'games': [game], 'live_enabled': True})
    backend = Capture(one)
    with tempfile.TemporaryDirectory() as folder:
        run.evaluate(one, backend, Saved({game: saved[game]}), run.Evidence(Path(folder) / 'preview'))
    return backend.request


def main(out_path):
    folder = ROOT / 'config/recovery_v1'
    control = C.Config.load(folder / 'r0_control.json')
    saved = load_saved(ROOT / control.resume_events, set(control.games))
    result = {}
    base = {game: first_request(control, saved, game) for game in saved}
    for path in sorted(folder.glob('*.json')):
        c = C.Config.load(path)
        rows = {}
        for game in (g for g in saved if g.split('-')[0] in c.games):
            request = first_request(c, saved, game)
            mine = json.loads(request['messages'][1]['content'])
            theirs = json.loads(base[game]['messages'][1]['content'])
            rows[game.split('-')[0]] = {
                'system_prompt_same_as_control': request['messages'][0]['content'] == base[game]['messages'][0]['content'],
                'evidence_added': {k: v for k, v in mine['evidence'].items() if k not in theirs['evidence']},
                'evidence_shared_parts_identical': all(mine['evidence'][k] == v for k, v in theirs['evidence'].items()),
                'contract_changed': {k: v for k, v in mine['output_contract'].items()
                                     if theirs['output_contract'].get(k) != v},
                'procedure_added': [p for p in mine['procedure'] if p not in theirs['procedure']],
                'request_characters': sum(len(m['content']) for m in request['messages'])}
        result[path.stem] = rows
    Path(out_path).write_text(json.dumps(result, indent=1) + '\n')
    return result


if __name__ == '__main__':
    for name, rows in main(sys.argv[1]).items():
        for game, row in rows.items():
            check = row['evidence_added'].get('recovery_check')
            print(name, game, 'check' if check else '-', (check or {}).get('why'),
                  'offer' if 'replay_offer' in row['evidence_added'] else '-', sorted(row['contract_changed']),
                  row['system_prompt_same_as_control'], row['evidence_shared_parts_identical'], row['request_characters'])
