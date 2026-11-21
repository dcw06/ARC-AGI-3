"""Play a public ARC game from its local game file in the browser and record how many actions each level takes.

    player.py [--game tr87-cd924810] [--level 2] [--port 8902]

Binds to 127.0.0.1 only. No model call and no call to the ARC service. What you play is written to
.cache/local_play/<game>/records.json (completed levels) and log.jsonl (every action).

Counting follows the benchmark: every action counts, a level restart (RESET) and an undo included.
    attempt       actions since the level started or since the last restart
    level total   every action spent on the level, restarts included: the number the benchmark scores

A level other than the first is started with the engine's set_level. For tr87 level 2 and cd82 level 3 this
was checked against the four test runs of 16 November of each game: the same first board, the same board
after every action, and every level completed at the same action. Other games and levels are not checked.

Usage (project environment), from the repository root.
"""
import argparse
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'research'))
from research.action_waste_v1 import local_game  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = ROOT / '.cache/local_play'
RUNS = ROOT / '.cache/claude_arc_runs'
PUBLIC = (('astra-adapter-high', 'GPT-6 Astra, provider harness'), ('astra-standard-high', 'GPT-6 Astra, standard harness'),
          ('tycho-opus5_orchestrator', 'Tycho with Opus 5'), ('opus5-standard-high', 'Opus 5, standard harness'))
TESTS = ('reports/object_ledger_v1/held_out_runs/results.json', 'reports/action_waste_v1/level_runs/results.json')


def lists(frames):
    return [f.tolist() if hasattr(f, 'tolist') else f for f in frames]


def per_level(levels_after):
    """Actions on each completed level, and the actions spent on the level left open."""
    done, count, level = [], 0, 0
    for completed in levels_after:
        count += 1
        if completed > level:
            done.append(count)
            count, level = 0, completed
    return done, count


def cells(done, left, levels, first=1):
    """One table cell per level: the count, the count with a star when the level was left open, or None."""
    row = [None] * levels
    for n, count in enumerate(done[:levels]):
        if n + 1 >= first:
            row[n] = str(count)
    if left and len(done) < levels and len(done) + 1 >= first:
        row[len(done)] = '%d*' % left
    return row


def references(game, levels):
    """Rows of the comparison table: what other players needed on each level of this game."""
    rows = []
    try:
        from recovery_v1 import traces
        recordings = traces.load_recordings()
    except Exception:       # the public recordings are a cache; the page works without them
        recordings = {}
    for key, label in PUBLIC:
        trace = recordings.get((key, game))
        if trace:
            rows.append({'who': label, 'levels': cells(*per_level(s['lc'] for s in trace['steps']), levels)})
    try:
        _, steps = local_game.saved_run(game)
        if steps:
            rows.append({'who': 'Opus 5.5 thin harness, 6 November run',
                         'levels': cells(*per_level(after['levels_completed'] for _, after in steps), levels)})
    except OSError:
        pass
    for name in TESTS:      # our test runs of this game, grouped by set-up, from the level they started on
        try:
            runs = json.loads((ROOT / name).read_text()).get('runs', [])
        except (OSError, ValueError):
            continue
        groups = {}
        for run in runs:
            events = RUNS / str(run.get('run')) / 'events.jsonl'
            if not game.startswith(str(run.get('game'))) or not run.get('level_at_start') or not events.exists():
                continue
            after = [json.loads(line)['after']['levels_completed'] for line in events.open() if '"kind":"transition"' in line]
            groups.setdefault(run.get('set_up', 'test run'), []).append(cells(*per_level(after), levels, run['level_at_start']))
        for set_up, found in groups.items():
            merged = [', '.join(c for c in column if c) or None for column in zip(*found)]
            rows.append({'who': 'Opus 5.5 test runs, ' + set_up, 'levels': merged})
    return rows


class Session:
    def __init__(self, game, level):
        self.game, self.lock = game, threading.Lock()
        self.cls = local_game.game_class(game)
        meta = json.loads((local_game.game_file(game).parent / 'metadata.json').read_text())
        self.human = [int(n) for n in meta.get('baseline_actions') or []]
        self.folder = OUT / game
        self.folder.mkdir(parents=True, exist_ok=True)
        saved = self.folder / 'records.json'
        self.records = json.loads(saved.read_text()) if saved.exists() else {'completions': []}
        self.start(level)
        self.table = references(game, self.levels)

    # ---- the game ---------------------------------------------------------------------------------
    def start(self, level):
        self.engine = self.cls()
        first = local_game.perform(self.engine, {'action_id': 0})      # the opening RESET, not a counted action
        self.levels = int(first.win_levels)
        level = min(max(int(level), 1), self.levels)
        self.frames = lists(first.frame)
        if level > 1:
            self.engine.set_level(level - 1)
            self.frames = [self.engine.camera.render(self.engine.current_level.get_sprites()).tolist()]
        self.state = first.state.name
        self.available = [int(getattr(a, 'value', a)) for a in first.available_actions]
        self.completed = int(first.levels_completed)
        self.started_at, self.try_id = level, time.strftime('%Y%m%dT%H%M%S')
        self.attempt, self.level_total, self.restarts, self.sequence = 0, 0, 0, []
        self.message = 'Level %d, from its start. The count begins with your first action.' % level
        self.log({'event': 'start', 'level': level})

    def level(self):
        return self.engine.level_index + 1

    def act(self, action, x=None, y=None):
        if self.state == 'WIN':
            self.message = 'The game is won. Start again at a level to keep playing.'
            return None
        if action == 0:
            return self.restart()
        if action not in self.available:
            self.message = 'ACTION%d does nothing in this game.' % action
            return None
        if self.state == 'GAME_OVER':
            self.message = 'Game over on this level. Restart the level (R) to go on.'
            return None
        level = self.level()
        step = {'action_id': action, 'action_data': {'x': int(x), 'y': int(y)} if action == 6 else {}}
        result = local_game.perform(self.engine, step)
        self.attempt += 1
        self.level_total += 1
        self.sequence.append({'a': action, **step['action_data']})
        self.frames = lists(result.frame) or self.frames[-1:]
        self.state = result.state.name
        self.log({'event': 'action', 'level': level, 'a': action, **step['action_data'], 'state': self.state,
                  'attempt': self.attempt, 'level_total': self.level_total})
        if int(result.levels_completed) > self.completed:
            self.completed = int(result.levels_completed)
            self.level_done(level)
        elif self.state == 'GAME_OVER':
            self.message = 'Game over on level %d after %d actions. Restart the level (R) to go on.' % (level, self.level_total)
        else:
            self.message = ''
        return self.frames

    def restart(self):
        # A RESET with no action on the level since its last start sends the whole game back to level 1.
        if self.attempt == 0 and self.state != 'GAME_OVER':
            self.message = 'Nothing to restart: no action on this attempt yet.'
            return None
        level = self.level()
        result = local_game.perform(self.engine, {'action_id': 0})
        if result.full_reset:
            self.start(level)
            self.message = 'The game went back to its beginning, so level %d was started again with the count at 0.' % level
            return self.frames
        self.level_total += 1
        self.restarts += 1
        self.attempt = 0
        self.sequence.append({'a': 0})
        self.frames = lists(result.frame) or self.frames[-1:]
        self.state = result.state.name
        self.message = 'Level %d restarted. The restart counts as one action.' % level
        self.log({'event': 'restart', 'level': level, 'level_total': self.level_total})
        return self.frames

    def level_done(self, level):
        earlier = [c for c in self.records['completions'] if c['level'] == level]
        record = {'level': level, 'level_actions': self.level_total, 'attempt_actions': self.attempt,
                  'restarts': self.restarts, 'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'try': self.try_id,
                  'started_at_level': self.started_at, 'sequence': self.sequence}
        self.records['completions'].append(record)
        (self.folder / 'records.json').write_text(json.dumps(self.records, indent=1) + '\n')
        self.log({'event': 'level_complete', 'level': level, 'level_actions': self.level_total,
                  'attempt_actions': self.attempt, 'restarts': self.restarts})
        self.message = 'Level %d completed in %d actions%s. Recorded%s.' % (
            level, self.level_total,
            ' (%d in the last attempt, %d restart%s)' % (self.attempt, self.restarts, '' if self.restarts == 1 else 's')
            if self.restarts else '',
            '' if earlier else ' as your first time on this level')
        if self.state == 'WIN':
            self.message += ' That was the last level.'
        self.attempt, self.level_total, self.restarts, self.sequence = 0, 0, 0, []

    # ---- what the page gets -----------------------------------------------------------------------
    def log(self, entry):
        with (self.folder / 'log.jsonl').open('a') as out:
            out.write(json.dumps({'t': time.strftime('%Y-%m-%d %H:%M:%S'), 'try': self.try_id, **entry}) + '\n')

    def snapshot(self, frames=None):
        done = self.records['completions']
        first, fewest = [None] * self.levels, [None] * self.levels
        for c in done:
            n = c['level'] - 1
            if n < self.levels:
                first[n] = c['level_actions'] if first[n] is None else first[n]
                fewest[n] = c['level_actions'] if fewest[n] is None else min(fewest[n], c['level_actions'])
        return {'game': self.game, 'frames': frames if frames is not None else self.frames[-1:],
                'level': self.level(), 'levels': self.levels, 'state': self.state, 'available': self.available,
                'attempt': self.attempt, 'level_total': self.level_total, 'restarts': self.restarts,
                'message': self.message, 'human': self.human, 'first': first, 'fewest': fewest, 'table': self.table,
                'completions': [{k: c[k] for k in ('level', 'level_actions', 'attempt_actions', 'restarts', 'time')}
                                for c in done]}


class Handler(BaseHTTPRequestHandler):
    session = None

    def log_message(self, *args):
        pass

    def reply(self, body, kind='application/json', code=200):
        body = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self.reply((HERE / 'page.html').read_bytes(), 'text/html; charset=utf-8')
        elif self.path == '/api/state':
            with self.session.lock:
                self.reply(self.session.snapshot())
        else:
            self.reply({'error': 'not found'}, code=404)

    def do_POST(self):
        try:
            request = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
        except ValueError:
            return self.reply({'error': 'the request is not JSON'}, code=400)
        game = self.session
        with game.lock:
            if self.path == '/api/act':
                action, x, y = request.get('action'), request.get('x'), request.get('y')
                if action not in range(8):
                    return self.reply({'error': 'no such action'}, code=400)
                if action == 6 and not all(isinstance(v, int) and 0 <= v < 64 for v in (x, y)):
                    return self.reply({'error': 'a click needs x and y from 0 to 63'}, code=400)
                return self.reply(game.snapshot(game.act(action, x, y)))
            if self.path == '/api/start':
                level = request.get('level')
                if not isinstance(level, int) or not 1 <= level <= game.levels:
                    return self.reply({'error': 'the level must be from 1 to %d' % game.levels}, code=400)
                game.start(level)
                return self.reply(game.snapshot())
        self.reply({'error': 'not found'}, code=404)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--game', default='tr87-cd924810')
    parser.add_argument('--level', type=int, default=2)
    parser.add_argument('--port', type=int, default=8902)
    args = parser.parse_args()
    Handler.session = Session(args.game, args.level)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print('%s level %d on http://127.0.0.1:%d' % (args.game, args.level, args.port), flush=True)
    server.serve_forever()
