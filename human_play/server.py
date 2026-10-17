"""Loopback-only human play. No model, Kaggle submission, or online scorecard.

python -m human_play.server --prepare   # first-time public game downloads
python -m human_play.server             # subsequent play is fully offline
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import io
import json
import logging
import os
from pathlib import Path
import re
import sys
import threading
import time
import uuid
import zipfile
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
STATIC = Path(__file__).parent / 'static'
GAMES = ('ar25', 'g50t', 'lf52', 'sk48', 'sp80', 'su15', 'tr87', 'vc33', 'wa30', 'ls20')
DEFAULT_GAMES = ROOT / '.cache/human-play/environments'
DEFAULT_LOGS = ROOT / 'recordings/human-play'
SESSION_ID = re.compile(r'^[0-9a-f]{32}$')
PALETTE = ['#FFFFFF', '#CCCCCC', '#999999', '#666666', '#333333', '#000000',
           '#E53AA3', '#FF7BCC', '#F93C31', '#1E93FF', '#88D8F1', '#FFDC00',
           '#FF851B', '#921231', '#4FCC30', '#A356D6']


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def now():
    return datetime.now(timezone.utc).isoformat()


def frame_hash(observation):
    return hashlib.sha256(encoded(observation)).hexdigest()


def observation(frame):
    if frame is None or not frame.frame:
        raise RuntimeError('游戏引擎没有返回画面；请下载日志后新开一轮。')
    return {'frames': [f.tolist() for f in frame.frame], 'state': frame.state.value,
            'levels_completed': frame.levels_completed, 'win_levels': frame.win_levels,
            'full_reset': frame.full_reset, 'available_actions': list(frame.available_actions)}


def engine(games_dir, logs_dir, online=False):
    os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.cache/human-play/matplotlib'))
    # The SDK otherwise allows an inherited COMPETITION setting to override OFFLINE.
    from arc_agi import Arcade, OperationMode
    os.environ['OPERATION_MODE'] = 'normal' if online else 'offline'
    logger = logging.getLogger('human_play.engine')
    logger.handlers = [logging.NullHandler()]
    logger.propagate = False  # anonymous API keys must never appear in logs
    return Arcade(operation_mode=OperationMode.NORMAL if online else OperationMode.OFFLINE,
                  environments_dir=str(games_dir), recordings_dir=str(logs_dir / 'sdk'), logger=logger)


class PlayError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


class Session:
    def __init__(self, metadata, env, path, initial, events=None):
        self.metadata, self.env, self.path = metadata, env, path
        self.current = initial
        self.events = list(events or [])
        self.sequence = 0
        self.uncertain = False
        self.closed = False
        self.pending = None
        self.applied = {}
        self.lock = threading.RLock()

    @property
    def session_id(self):
        return self.metadata['session_id']

    def append(self, event):
        event = {'timestamp_utc': now(), **event}
        # An intent is fsynced BEFORE dispatch and its outcome BEFORE response.
        with self.path.open('ab') as f:
            f.write(encoded(event) + b'\n')
            f.flush()
            os.fsync(f.fileno())
        self.events.append(event)

    def view(self):
        with self.lock:
            history = []
            for event in self.events:
                if event['type'] == 'action':
                    raw = event['transition']
                    history.append({'sequence': event['sequence'], 'action': raw['dispatched'],
                                    'status': raw['outcome']['status'],
                                    'levels_completed': raw['outcome'].get('after', {}).get('levels_completed'),
                                    'timestamp_utc': event['timestamp_utc']})
            return {'session_id': self.session_id, 'game_id': self.metadata['game_id'],
                    'short_id': self.metadata['short_id'], 'seed': self.metadata['seed'],
                    'started_at': self.metadata['started_at'], 'sequence': self.sequence,
                    'ended_at': (next((e['timestamp_utc'] for e in reversed(self.events) if e['type'] == 'end'), None)
                                 if self.closed else self.events[-1]['timestamp_utc']
                                 if self.current['state'] == 'WIN' else None),
                    'observation': self.current, 'uncertain': self.uncertain, 'closed': self.closed,
                    'history': history[-12:],
                    'notes': [e for e in self.events if e['type'] == 'note'],
                    'annotations': [e for e in self.events if e['type'] == 'annotation'],
                    'source_sha256': self.metadata['source_sha256']}

    def step(self, body):
        from arcengine import GameAction
        with self.lock:
            action_id = body.get('action_id')
            if type(action_id) is not int or action_id not in range(8):
                raise PlayError('动作编号必须为 0–7 的整数。')
            data = {}
            if action_id == 6:
                frame = self.current['frames'][-1]
                x, y = body.get('x'), body.get('y')
                if (type(x) is not int or type(y) is not int or not 0 <= x < len(frame[0]) or
                        not 0 <= y < len(frame)):
                    raise PlayError('点击坐标超出游戏画面。')
                data = {'x': x, 'y': y}
            event_id = body.get('event_id')
            if not isinstance(event_id, str) or not re.fullmatch(r'[A-Za-z0-9-]{1,80}', event_id):
                raise PlayError('缺少有效的操作 ID，请刷新页面。')
            action = {'action_id': action_id, 'action_data': data}
            if event_id in self.applied:
                if self.applied[event_id] != action:
                    raise PlayError('操作 ID 已被另一个动作使用。', 409)
                return {**self.view(), 'duplicate': True}
            if self.uncertain:
                raise PlayError('上一步结果不确定，请下载日志并新开一轮。', 409)
            if self.closed or self.current['state'] == 'WIN':
                raise PlayError('本轮已结束，可以下载日志或新开一轮。', 409)
            if type(body.get('expected_sequence')) is not int or body['expected_sequence'] != self.sequence:
                raise PlayError('游戏进度已更新，请刷新页面后继续。', 409)
            if action_id != 0 and action_id not in self.current['available_actions']:
                raise PlayError('当前游戏不支持这个动作。')
            if self.current['state'] == 'GAME_OVER' and action_id != 0:
                raise PlayError('本关已失败，请按 R 重置。', 409)
            before = self.current
            index = self.sequence
            self.append({'type': 'intent', 'event_id': event_id, 'sequence': index + 1,
                         'action': action, 'before_sha256': frame_hash(before)})
            self.pending = event_id
            start = time.perf_counter()
            try:
                frame = self.env.step(GameAction.from_id(action_id), data=data)
                after = observation(frame)
                outcome = {'status': 'acknowledged', 'after': after}
            except Exception:
                # The SDK can catch engine exceptions and return None. We cannot
                # prove that dispatch failed before the game changed.
                outcome = {'status': 'outcome_unknown', 'reason': 'engine did not return a valid observation'}
                self.uncertain = True
            raw = {'identity': {'episode_id': self.session_id, 'action_index': index},
                   'before': before, 'proposal': action, 'dispatched': action, 'outcome': outcome,
                   'environment_source': 'local_official_engine_human_play_v1'}
            try:
                self.append({'type': 'action', 'event_id': event_id, 'sequence': index + 1,
                             'duration_ms': round((time.perf_counter() - start) * 1000, 3),
                             'transition': raw})
            except OSError:
                self.uncertain = True
                raise PlayError('日志保存失败，已停止操作。请保留原始记录，并检查磁盘空间。', 503)
            self.sequence += 1
            self.applied[event_id] = action
            self.pending = None
            if outcome['status'] == 'acknowledged':
                self.current = after
            return self.view()

    def export(self):
        with self.lock:
            return {'format': 'arc-human-play-v1', 'metadata': self.metadata,
                    'exported_at': now(), 'summary': self.view(), 'events': list(self.events),
                    'annotations': [e['region'] for e in self.events if e['type'] == 'annotation'],
                    'transitions': [e['transition'] for e in self.events if e['type'] == 'action']}


class Store:
    def __init__(self, games_dir=DEFAULT_GAMES, logs_dir=DEFAULT_LOGS):
        self.games_dir, self.logs_dir = Path(games_dir), Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.arc = engine(self.games_dir, self.logs_dir)
        self.sessions = {}
        self.lock = threading.RLock()

    def games(self):
        infos = {e.game_id.split('-')[0]: e for e in self.arc.get_environments()}
        return [{'id': code, 'game_id': infos[code].game_id if code in infos else None,
                 'ready': code in infos and bool(list(Path(infos[code].local_dir).glob('*.py'))),
                 'priority': i < 3, 'official_url': f'https://arcprize.org/tasks/{code}',
                 'tags': infos[code].tags if code in infos else []}
                for i, code in enumerate(GAMES)]

    def make(self, game_id, seed):
        env = self.arc.make(game_id, seed=seed, save_recording=False)
        if env is None or env.observation_space is None:
            raise PlayError('本地游戏尚未准备好。请先运行 --prepare 下载官方环境。', 503)
        return env

    def create(self, body):
        code, seed = body.get('game_id'), body.get('seed', 0)
        if code not in GAMES:
            raise PlayError('请选择列表中的游戏。')
        if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
            raise PlayError('种子必须是 0–4294967295 的整数。')
        with self.lock:
            env = self.make(code, seed)
            initial = observation(env.observation_space)
            session_id = uuid.uuid4().hex
            game_id = env.environment_info.game_id
            info = env.environment_info
            source = Path(info.local_dir) / (info.class_name.lower() + '.py')
            metadata = {'session_id': session_id, 'short_id': code, 'game_id': game_id,
                        'seed': seed, 'started_at': now(), 'actor': 'human',
                        'official_url': f'https://arcprize.org/tasks/{code}',
                        'runtime': {name: importlib.metadata.version(name) for name in ('arc-agi', 'arcengine')},
                        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                        'coordinates': 'zero-based rendered frame pixels; x=column, y=row',
                        'actions': {'0': 'RESET', '1': 'UP', '2': 'DOWN', '3': 'LEFT', '4': 'RIGHT',
                                    '5': 'ACTION5 / SPACE', '6': 'ACTION6 / CLICK', '7': 'ACTION7 / Z'},
                        'initial_observation': initial}
            if code == 'ls20':
                reference = json.loads((STATIC / 'ls20-level1.json').read_text())
                digest = hashlib.sha256(json.dumps(initial['frames'][-1], separators=(',', ':')).encode()).hexdigest()
                if reference['game_id'] == game_id and reference['frame_sha256'] == digest:
                    metadata['objects_and_roles_reference'] = reference
                    metadata['reference_origin'] = 'assistant scripted inspection, not human-discovered knowledge'
            session = Session(metadata, env, self.logs_dir / (session_id + '.jsonl'), initial)
            session.append({'type': 'start', 'metadata': metadata})
            self.sessions[session_id] = session
            return session

    def get(self, session_id):
        if not SESSION_ID.fullmatch(session_id):
            raise PlayError('记录不存在。', 404)
        with self.lock:
            if session_id in self.sessions:
                return self.sessions[session_id]
            path = self.logs_dir / (session_id + '.jsonl')
            if not path.is_file():
                raise PlayError('记录不存在。', 404)
            try:
                events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
            except (ValueError, OSError):
                raise PlayError('记录文件损坏，请保留原文件以便检查。', 409)
            metadata = events[0]['metadata']
            env = self.make(metadata['game_id'], metadata['seed'])
            source = Path(env.environment_info.local_dir) / (env.environment_info.class_name.lower() + '.py')
            if hashlib.sha256(source.read_bytes()).hexdigest() != metadata['source_sha256']:
                raise PlayError('游戏版本已变更，无法安全恢复；原日志仍保存在 recordings/human-play。', 409)
            session = Session(metadata, env, path, observation(env.observation_space), events)
            from arcengine import GameAction
            for event in events[1:]:
                if event['type'] == 'intent':
                    session.pending = event['event_id']
                elif event['type'] == 'action':
                    raw = event['transition']
                    if raw['outcome']['status'] != 'acknowledged':
                        session.uncertain = True
                    else:
                        act = raw['dispatched']
                        actual = observation(env.step(GameAction.from_id(act['action_id']), data=act['action_data']))
                        if frame_hash(actual) != frame_hash(raw['outcome']['after']):
                            raise PlayError('回放与原记录不一致；已停止恢复，原日志未改动。', 409)
                        session.current = actual
                    session.sequence = event['sequence']
                    session.applied[event['event_id']] = raw['dispatched']
                    session.pending = None
                elif event['type'] == 'end':
                    session.closed = True
            if session.pending:
                session.uncertain = True
            self.sessions[session_id] = session
            return session

    def recent(self):
        rows = []
        for path in sorted(self.logs_dir.glob('*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)[:30]:
            try:
                with path.open() as f:
                    metadata = json.loads(f.readline())['metadata']
                rows.append({k: metadata[k] for k in ('session_id', 'short_id', 'started_at')})
            except (ValueError, KeyError, OSError):
                continue
        return rows


class Handler(BaseHTTPRequestHandler):
    server_version = 'ARC-Human-Local/1'

    def log_message(self, format, *args):
        pass

    @property
    def store(self):
        return self.server.store

    def send(self, status, body, content_type='application/json; charset=utf-8', filename=None):
        data = body if isinstance(body, bytes) else encoded(body)
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; connect-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(data)

    def guard(self):
        allowed = {f'localhost:{self.server.server_port}', f'127.0.0.1:{self.server.server_port}'}
        if self.headers.get('Host') not in allowed:
            raise PlayError('仅允许本机访问。', 403)
        origin = self.headers.get('Origin')
        if origin and origin not in {'http://' + a for a in allowed}:
            raise PlayError('拒绝跨站请求。', 403)

    def do_GET(self):
        try:
            self.guard()
            path = urlsplit(self.path).path
            assets = {'/': ('index.html', 'text/html; charset=utf-8'),
                      '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                      '/style.css': ('style.css', 'text/css; charset=utf-8'),
                      '/ls20-level1.json': ('ls20-level1.json', 'application/json; charset=utf-8')}
            if path in assets:
                name, mime = assets[path]
                return self.send(200, (STATIC/name).read_bytes(), mime)
            if path == '/api/games':
                return self.send(200, {'games': self.store.games(), 'palette': PALETTE})
            if path == '/api/sessions':
                return self.send(200, {'sessions': self.store.recent()})
            match = re.fullmatch(r'/api/sessions/([0-9a-f]{32})(/download(?:\.zip)?)?', path)
            if match:
                sid, download = match.groups()
                # Download original logs directly even if recovery/version check
                # fails. Export must not depend on replaying a running engine.
                if download:
                    log = self.store.logs_dir / (sid + '.jsonl')
                    if not log.is_file():
                        raise PlayError('记录不存在。', 404)
                    if sid in self.store.sessions:
                        session = self.store.get(sid)
                        with session.lock:
                            exported = session.export()
                            journal = log.read_bytes()
                    else:
                        journal = log.read_bytes()
                        events = [json.loads(line) for line in journal.splitlines() if line.strip()]
                        exported = {'format': 'arc-human-play-v1', 'metadata': events[0]['metadata'],
                                    'exported_at': now(), 'events': events,
                                    'annotations': [e['region'] for e in events if e['type'] == 'annotation'],
                                    'transitions': [e['transition'] for e in events if e['type'] == 'action']}
                    stem = 'arc-' + exported['metadata']['short_id'] + '-' + sid[:8]
                    if download.endswith('.zip'):
                        buffer = io.BytesIO()
                        with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as z:
                            z.writestr('session.json', encoded(exported))
                            z.writestr('events.jsonl', journal)
                        return self.send(200, buffer.getvalue(), 'application/zip', stem + '.zip')
                    return self.send(200, encoded(exported), filename=stem + '.json')
                return self.send(200, self.store.get(sid).view())
            raise PlayError('页面不存在。', 404)
        except PlayError as exc:
            self.send(exc.status, {'error': str(exc)})
        except (OSError, ValueError, KeyError):
            self.send(500, {'error': '读取失败；原始日志保存在 recordings/human-play。'})

    def do_POST(self):
        try:
            self.guard()
            if self.headers.get('X-Arc-Play') != '1':
                raise PlayError('请通过本地游戏页面操作。', 403)
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 16384:
                raise PlayError('请求大小不正确。', 413)
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise PlayError('请求必须为 JSON 对象。')
            path = urlsplit(self.path).path
            if path == '/api/sessions':
                return self.send(201, self.store.create(body).view())
            match = re.fullmatch(r'/api/sessions/([0-9a-f]{32})/(action|note|annotation|end)', path)
            if not match:
                raise PlayError('接口不存在。', 404)
            sid, operation = match.groups()
            session = self.store.get(sid)
            if operation == 'action':
                return self.send(200, session.step(body))
            with session.lock:
                if operation == 'annotation':
                    from .annotations import region
                    try:
                        annotation = region(session.current, body, session.sequence)
                    except ValueError as exc:
                        raise PlayError(str(exc))
                    session.append({'type': 'annotation', 'region': annotation, 'sequence': session.sequence})
                elif operation == 'note':
                    note = body.get('text')
                    if not isinstance(note, str) or not 0 < len(note.strip()) <= 4000:
                        raise PlayError('笔记须为 1–4000 字。')
                    session.append({'type': 'note', 'text': note.strip(), 'sequence': session.sequence})
                elif not session.closed:
                    session.append({'type': 'end', 'sequence': session.sequence, 'reason': 'human_finished'})
                    session.closed = True
            self.send(200, session.view())
        except PlayError as exc:
            self.send(exc.status, {'error': str(exc)})
        except (ValueError, TypeError):
            self.send(400, {'error': '无效的请求格式。'})
        except Exception:
            self.send(500, {'error': '本地服务处理失败，请刷新页面；原始日志仍保留。'})


def serve(store, port=8765):
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    server.store = store
    return server


def prepare(games_dir, logs_dir):
    arc = engine(games_dir, logs_dir, online=True)
    missing = []
    for code in GAMES:
        env = arc.make(code, save_recording=False)
        if env is None or env.observation_space is None:
            missing.append(code)
        print(f'{code}: {"READY" if code not in missing else "UNAVAILABLE"}', flush=True)
    if missing:
        raise SystemExit('未下载成功：' + ', '.join(missing) + '。检查网络后重新运行 --prepare。')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port', type=int, default=8765)
    p.add_argument('--games-dir', type=Path, default=DEFAULT_GAMES)
    p.add_argument('--logs-dir', type=Path, default=DEFAULT_LOGS)
    p.add_argument('--prepare', action='store_true')
    args = p.parse_args()
    if args.prepare:
        prepare(args.games_dir, args.logs_dir)
        return
    server = serve(Store(args.games_dir, args.logs_dir), args.port)
    print(f'ARC 本地闯关 → http://localhost:{server.server_port}', flush=True)
    print('日志自动保存：' + str(args.logs_dir), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
