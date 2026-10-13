"""Private, loopback-only annotation of retained human play; no engine/model calls."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import threading
from urllib.parse import parse_qs, urlsplit
import zipfile

GAMES = ('ls20', 's5i5', 'cd82', 'ft09', 'ka59', 'sc25')
FIELDS = ('objects', 'controls', 'goal', 'rules', 'strategy', 'similarity', 'transfer')
KINDS = ('controlled_object', 'target', 'obstacle', 'control', 'other')


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def private_directory(folder):
    folder = Path(folder).resolve()
    ancestor = next(p for p in (folder, *folder.parents) if p.exists())
    result = subprocess.run(['git', '-C', str(ancestor), 'rev-parse', '--show-toplevel'],
                            capture_output=True, text=True)
    if result.returncode == 0:
        ignored = subprocess.run(['git', '-C', result.stdout.strip(), 'check-ignore', '--quiet',
                                  str(folder/'answers.json')], capture_output=True)
        if ignored.returncode != 0:
            raise ValueError('worksheet data must be git-ignored or outside a repository')
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def atomic_write(path, value):
    raw = canonical(value)
    handle, temporary = tempfile.mkstemp(prefix='.saving-', dir=path.parent)
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def check_observation(observation):
    frames = observation.get('frames')
    if not isinstance(frames, list) or not frames:
        raise ValueError('missing recorded frames')
    for grid in frames:
        if len(grid) != 64 or any(len(row) != 64 for row in grid):
            raise ValueError('expected a recorded 64 by 64 board')
        if any(type(v) is not int or not 0 <= v <= 15 for row in grid for v in row):
            raise ValueError('invalid board color')
    actions = observation.get('available_actions')
    if not isinstance(actions, list) or any(type(v) is not int or v not in range(1, 8) for v in actions):
        raise ValueError('invalid recorded legal controls')
    if type(observation.get('levels_completed')) is not int:
        raise ValueError('invalid recorded progress')


def build_cases(paths):
    cases, sources = {}, {}
    for path in paths:
        raw = Path(path).read_bytes()
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
        if not rows or rows[0].get('type') != 'session_start' or rows[0].get('actor') != 'human_manual':
            raise ValueError('expected a retained human manual-play log')
        header = rows[0]
        game_id = header['game_id']
        game = game_id.split('-')[0]
        if game not in GAMES or game in sources:
            raise ValueError('provide exactly one log per requested development game')
        sources[game] = {'game_id': game_id, 'file_sha256': hashlib.sha256(raw).hexdigest(),
                         'schema': header['schema'], 'actor': header['actor'],
                         'seed': header['seed'], 'sdk_versions': header['sdk_versions'],
                         'exposure': header.get('exposure', 'not recorded')}
        previous = header['initial_observation']
        check_observation(previous)
        if previous['levels_completed'] != 0 or previous['game_id'] != game_id:
            raise ValueError('log must begin at the first level')
        for offset in range(1, len(rows), 2):
            if offset+1 >= len(rows):
                raise ValueError('unacknowledged recorded action')
            entered, ack = rows[offset:offset+2]
            sequence = (offset+1)//2
            if (entered.get('type') != 'action_entered' or ack.get('type') != 'action_acknowledged'
                    or entered.get('sequence') != sequence or ack.get('sequence') != sequence
                    or entered.get('request_id') != ack.get('request_id') or entered.get('before') != previous):
                raise ValueError('manual log has a broken before/action/after chain')
            after = ack['after']
            check_observation(after)
            if after['game_id'] != game_id:
                raise ValueError('recorded game changed')
            action = entered['action']
            action_id, data = action['action_id'], action['action_data']
            if type(action_id) is not int or (action_id != 0 and action_id not in previous['available_actions']):
                raise ValueError('illegal recorded input')
            if action_id == 6:
                if set(data) != {'x', 'y'} or any(type(data[k]) is not int or not 0 <= data[k] < 64 for k in data):
                    raise ValueError('invalid recorded click')
            elif data:
                raise ValueError('unexpected action coordinates')
            level = previous['levels_completed']+1
            if level > 3:
                break
            case_id = f'{game}.level{level}'
            case = cases.setdefault(case_id, {'case_id': case_id, 'game': game, 'game_id': game_id,
                'level': level, 'frames': [], 'steps': [], 'completed': False})
            if not case['frames']:
                case['frames'].append({'sequence': 0, 'label': 'Level start',
                    'grid': previous['frames'][-1], 'grid_sha256': digest(previous['frames'][-1]),
                    'legal_controls': previous['available_actions']})
            boundary = after['levels_completed'] == level
            if after['levels_completed'] not in (level-1, level):
                raise ValueError('unexpected level transition')
            step = {'sequence': sequence, 'action': action, 'seconds': ack['seconds'],
                    'state': after['state'], 'levels_completed': after['levels_completed'],
                    'completed_level': boundary}
            case['steps'].append(step)
            if boundary:
                case['completed'] = True
            else:
                case['frames'].append({'sequence': sequence, 'label': f'After recorded input {sequence}',
                    'grid': after['frames'][-1], 'grid_sha256': digest(after['frames'][-1]),
                    'legal_controls': after['available_actions']})
            previous = after
            if level == 3 and boundary:
                break  # Never include a fourth-level board or later inputs.
        if any(not cases.get(f'{game}.level{level}', {}).get('completed') for level in range(1, 4)):
            raise ValueError(f'{game}: retained log must complete levels 1, 2 and 3')
    if set(sources) != set(GAMES):
        raise ValueError('six logs required: '+', '.join(GAMES))
    ordered = {f'{game}.level{level}': cases[f'{game}.level{level}'] for game in GAMES for level in range(1, 4)}
    return ordered, sources


class Worksheet:
    def __init__(self, folder, paths):
        self.folder = private_directory(folder)
        self.cases, self.sources = build_cases(paths)
        self.context_hash = digest({'cases': self.cases, 'sources': self.sources})
        self.lock = threading.RLock()
        self.path = self.folder/'answers.json'
        if self.path.exists():
            self.document = json.loads(self.path.read_bytes())
            if self.document.get('context_sha256') != self.context_hash:
                raise ValueError('existing answers belong to different logs; use a new private data folder')
        else:
            self.document = {'schema': 'human_strategy_annotations_v1', 'context_sha256': self.context_hash,
                'scope': 'first three levels of six exposed public development games',
                'qualification': 'owner recollections and proposed annotations; not independently validated ground truth',
                'sources': self.sources, 'revision': 0, 'updated_utc': None,
                'cases': {key: {'revision': 0, 'status': 'draft', 'answers': {field: '' for field in FIELDS},
                                'marks': []} for key in self.cases}}
            atomic_write(self.path, self.document)
        atomic_write(self.folder/'cases.json', self.cases)
        atomic_write(self.folder/'provenance.json', {'context_sha256': self.context_hash, 'sources': self.sources})

    def overview(self):
        with self.lock:
            return {'context_sha256': self.context_hash, 'revision': self.document['revision'],
                    'cases': [{'case_id': key, 'game': c['game'], 'level': c['level'],
                        'input_count': len(c['steps']), 'completed': c['completed'],
                        'answer': deepcopy(self.document['cases'][key])} for key, c in self.cases.items()]}

    def save(self, value):
        with self.lock:
            key = value.get('case_id')
            if key not in self.cases:
                raise ValueError('unknown worksheet entry')
            current = self.document['cases'][key]
            revision = value.get('expected_revision')
            if type(revision) is not int or revision != current['revision']:
                raise RuntimeError('another page changed this entry; your browser draft is retained—reload before saving')
            answers, marks, status = value.get('answers'), value.get('marks'), value.get('status')
            if not isinstance(answers, dict) or set(answers) != set(FIELDS):
                raise ValueError('all seven answer fields are required')
            if any(not isinstance(text, str) or len(text) > 20000 for text in answers.values()):
                raise ValueError('each answer must be text of at most 20,000 characters')
            if status not in ('draft', 'ready_for_review'):
                raise ValueError('invalid review status')
            if status == 'ready_for_review' and any(not text.strip() for text in answers.values()):
                raise ValueError('fill every field, or write unknown/not applicable, before marking ready')
            if not isinstance(marks, list) or len(marks) > 100:
                raise ValueError('at most 100 object points per entry')
            for mark in marks:
                if not isinstance(mark, dict) or set(mark) != {'label', 'kind', 'x', 'y', 'frame_index', 'grid_sha256'}:
                    raise ValueError('invalid object point')
                if not isinstance(mark['label'], str) or not 1 <= len(mark['label'].strip()) <= 120 or mark['kind'] not in KINDS:
                    raise ValueError('name the object and choose its role')
                if any(type(mark[k]) is not int for k in ('x', 'y', 'frame_index')):
                    raise ValueError('object point coordinates must be integers')
                if not 0 <= mark['x'] < 64 or not 0 <= mark['y'] < 64:
                    raise ValueError('object point outside board')
                if not 0 <= mark['frame_index'] < len(self.cases[key]['frames']):
                    raise ValueError('unknown recorded frame')
                if mark['grid_sha256'] != self.cases[key]['frames'][mark['frame_index']]['grid_sha256']:
                    raise ValueError('object point refers to a different board')
            document = deepcopy(self.document)
            document['revision'] += 1
            document['updated_utc'] = utc()
            document['cases'][key] = {'revision': current['revision']+1, 'status': status,
                                      'answers': answers, 'marks': marks}
            # Immutable snapshots preserve earlier answers. The current file is the commit point.
            atomic_write(self.folder/f'answers-revision-{document["revision"]:06d}.json', document)
            atomic_write(self.path, document)
            self.document = document
            return deepcopy(document['cases'][key])

    def export(self, packed=False):
        with self.lock:
            answers = canonical(self.document)
            if not packed:
                return 'human-strategy-answers.json', 'application/json', answers
            memory = io.BytesIO()
            with zipfile.ZipFile(memory, 'w', zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('answers.json', answers)
                archive.writestr('cases.json', canonical(self.cases))
                archive.writestr('provenance.json', canonical({'context_sha256': self.context_hash, 'sources': self.sources}))
                archive.writestr('README.txt', 'Private development annotations. First three levels only.\n'
                    'Only the final returned frame per input is shown; animations are omitted.\n'
                    'Completion inputs are retained; following-level boards are omitted.\n'
                    'Answers/point labels need independent review. Points are not object masks or proven hit regions.\n')
            return 'human-strategy-test-data.zip', 'application/zip', memory.getvalue()


def handler_for(workspace, token):
    page = Path(__file__).with_name('manual_strategy_worksheet.html').read_text(encoding='utf-8').replace('__LOCAL_TOKEN__', token)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def local(self):
            host = self.headers.get('Host')
            if host not in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'):
                raise PermissionError('loopback host required')
            if self.headers.get('Origin') not in (None, 'http://'+host):
                raise PermissionError('cross-origin access refused')

        def reply(self, status, body, kind='application/json', filename=None):
            raw = canonical(body) if isinstance(body, (dict, list)) else body
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
            if filename:
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            try:
                self.local()
                url = urlsplit(self.path)
                if url.path == '/':
                    self.reply(200, page.encode(), 'text/html; charset=utf-8')
                elif url.path == '/api/workspace':
                    self.reply(200, workspace.overview())
                elif url.path == '/api/case':
                    key = parse_qs(url.query).get('id', [''])[0]
                    if key not in workspace.cases:
                        raise ValueError('unknown worksheet entry')
                    with workspace.lock:
                        self.reply(200, {'case': workspace.cases[key], 'answer': workspace.document['cases'][key]})
                elif url.path in ('/download/answers', '/download/pack'):
                    name, kind, raw = workspace.export(url.path.endswith('/pack'))
                    self.reply(200, raw, kind, name)
                else:
                    self.reply(404, {'error': 'not found'})
            except Exception as exc:
                self.reply(400, {'error': str(exc)[:300]})

        def do_POST(self):
            try:
                self.local()
                if self.headers.get('X-Local-Token') != token:
                    raise PermissionError('local page token required')
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 300000:
                    raise ValueError('invalid request size')
                value = json.loads(self.rfile.read(size))
                if self.path != '/api/save':
                    raise ValueError('unknown local operation')
                self.reply(200, workspace.save(value))
            except RuntimeError as exc:
                self.reply(409, {'error': str(exc)})
            except Exception as exc:
                self.reply(400, {'error': str(exc)[:300]})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--log', type=Path, action='append', required=True)
    parser.add_argument('--port', type=int, default=8791)
    args = parser.parse_args()
    workspace = Worksheet(args.data, args.log)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler_for(workspace, secrets.token_hex(24)))
    print(f'Private strategy worksheet: http://127.0.0.1:{server.server_port} (18 entries)', flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
