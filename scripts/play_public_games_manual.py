"""Local manual play of archived public games, with durable downloadable logs. CPU only."""
import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.metadata
import io
import json
import os
from pathlib import Path
import secrets
import sys
import threading
import time
from urllib.parse import urlsplit
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
GAMES = ('ar25-0c556536','wa30-ee6fef47','ls20-9607627b','s5i5-18d95033')


def utc():
    return datetime.now(timezone.utc).isoformat()


class ManualPlayer:
    def __init__(self, folder, *, actor='human_manual'):
        from scripts.build_retained_game_replay import private_output
        from research.grounded_action_v1.engine import restore_game_mount
        from arc_agi import Arcade, OperationMode
        import requests
        # SDK/game execution is offline even if the host has unrelated credentials.
        def deny_network(*args, **kwargs):
            raise PermissionError('manual player forbids SDK network access')
        requests.Session.send = deny_network
        self.folder = private_output(Path(folder)/'logs.jsonl').parent
        self.folder.mkdir(parents=True,exist_ok=True)
        games = self.folder/'games'
        if not games.exists():
            restore_game_mount(games)
        else:
            # Every start verifies staged files against the original archive.
            manifest = json.loads((ROOT/'reports/phase4_v2_offline_package.json').read_bytes())
            for name, info in manifest['files'].items():
                if name.startswith('environment_files/'):
                    raw = (games/name.removeprefix('environment_files/')).read_bytes()
                    if len(raw) != info['bytes'] or hashlib.sha256(raw).hexdigest() != info['sha256']:
                        raise ValueError('staged game hash mismatch')
        self.arcade = Arcade(operation_mode=OperationMode.OFFLINE,arc_api_key='offline-manual',
                             arc_base_url='http://127.0.0.1:9',environments_dir=str(games),
                             recordings_dir=str(self.folder/'sdk-recordings'))
        self.actor = actor
        self.current = None
        self.lock = threading.RLock()
        self.sequence = 0
        self.failed = False
        self.requests = set()

    def observation(self):
        from agent.state import Observation
        value = Observation.from_value(self.env.observation_space)
        return {'game_id':value.game_id,'state':value.state.name,'levels_completed':value.levels_completed,
                'win_levels':value.win_levels,'available_actions':list(value.available_actions),
                'frames':[frame.tolist() for frame in value.frames],'canonical_hash':value.canonical_hash}

    def append(self, event):
        with self.log.open('ab') as stream:
            stream.write((json.dumps(event,separators=(',',':'),allow_nan=False)+'\n').encode())
            stream.flush()
            os.fsync(stream.fileno())

    def state(self):
        with self.lock:
            return {'games':list(GAMES),'session':self.current,'actions':self.sequence,'failed':self.failed,
                    'observation':self.observation() if self.current else None}

    def start(self, game):
        with self.lock:
            if game not in GAMES:
                raise ValueError('choose one of the four public development games')
            self.current = None
            self.sequence = 0
            self.failed = False
            self.env = self.arcade.make(game,seed=0,save_recording=True,include_frame_data=True)
            if self.env is None or self.env.observation_space is None:
                raise RuntimeError('offline game did not start')
            self.current = game+'-'+uuid.uuid4().hex[:12]
            self.log = self.folder/(self.current+'.manual.jsonl')
            self.log.touch(exist_ok=False)
            self.append({'type':'session_start','schema':'public_game_manual_v1','session':self.current,
                'actor':self.actor,'game_id':game,'seed':0,'utc':utc(),'source':'offline_public_development_engine',
                'exposure':'user previously viewed agent replays; not a naive-human benchmark',
                'sdk_versions':{name:importlib.metadata.version(name) for name in ('arc-agi','arcengine')},
                'initial_observation':self.observation()})
            return self.state()

    def action(self, value):
        with self.lock:
            if not self.current or self.failed:
                raise ValueError('start a game before acting; uncertain sessions cannot continue')
            if value.get('session') != self.current or value.get('expected_actions') != self.sequence:
                raise ValueError('stale page; refresh the current state')
            request_id = value.get('request_id')
            if not isinstance(request_id,str) or not 1 <= len(request_id) <= 80 or request_id in self.requests:
                raise ValueError('missing or duplicate action request; no action retried')
            action_id = value.get('action_id')
            if type(action_id) is not int:
                raise ValueError('action id must be an integer')
            before = self.observation()
            if self.sequence >= 2000:
                raise ValueError('session action limit reached; download the log and start a new session')
            data = value.get('action_data',{})
            if not isinstance(data,dict):
                raise ValueError('invalid action data')
            if action_id == 6:
                if set(data) != {'x','y'} or any(type(data[k]) is not int or not 0 <= data[k] < 64 for k in ('x','y')):
                    raise ValueError('click coordinates must be integers from 0 to 63')
            elif data:
                raise ValueError('only ACTION6 takes coordinates')
            if action_id != 0 and (action_id not in before['available_actions'] or before['state'] != 'NOT_FINISHED'):
                raise ValueError('action is unavailable; reset or start another game')
            self.requests.add(request_id)
            sequence = self.sequence+1
            self.append({'type':'action_entered','sequence':sequence,'utc':utc(),'request_id':request_id,
                         'action':{'action_id':action_id,'action_data':data},'before':before})
            started = time.monotonic()
            try:
                from arcengine import GameAction
                returned = self.env.reset() if action_id == 0 else self.env.step(GameAction.from_id(action_id),data=data)
                if returned is None:
                    raise RuntimeError('engine returned no observation')
                after = self.observation()
                self.sequence = sequence
                self.append({'type':'action_acknowledged','sequence':sequence,'utc':utc(),'request_id':request_id,
                             'seconds':time.monotonic()-started,'after':after})
            except BaseException as exc:
                self.failed = True
                self.append({'type':'action_failed_or_uncertain','sequence':sequence,'utc':utc(),
                             'request_id':request_id,'error':type(exc).__name__+': '+str(exc)[:300]})
                raise
            return self.state()

    def download(self, all_sessions=False):
        with self.lock:
            if all_sessions:
                memory = io.BytesIO()
                with zipfile.ZipFile(memory,'w',compression=zipfile.ZIP_DEFLATED) as archive:
                    for file in sorted(self.folder.glob('*.manual.jsonl')):
                        archive.writestr(file.name,file.read_bytes())
                    for file in sorted((self.folder/'sdk-recordings').rglob('*.jsonl')):
                        archive.writestr('sdk-recordings/'+file.relative_to(self.folder/'sdk-recordings').as_posix(),file.read_bytes())
                return 'manual-public-game-logs.zip','application/zip',memory.getvalue()
            if not self.current:
                raise ValueError('start a game to create a log')
            return self.log.name,'application/x-ndjson',self.log.read_bytes()


def handler_for(player, token):
    page = Path(__file__).with_name('manual_public_game_player.html').read_text(encoding='utf-8').replace('__LOCAL_TOKEN__',token)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):
            pass

        def reply(self,status,body,content_type='application/json',filename=None):
            raw = json.dumps(body).encode() if isinstance(body,dict) else body
            self.send_response(status)
            self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Cross-Origin-Resource-Policy','same-origin')
            if filename:
                self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(raw)

        def local(self):
            if self.headers.get('Host') not in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'):
                raise PermissionError('local player host mismatch')
            origin = self.headers.get('Origin')
            if origin and origin != 'http://'+self.headers['Host']:
                raise PermissionError('cross-origin request refused')

        def do_GET(self):
            try:
                self.local()
                path = urlsplit(self.path).path
                if path == '/':
                    self.reply(200,page.encode(),'text/html; charset=utf-8')
                elif path == '/api/state':
                    self.reply(200,player.state())
                elif path in ('/download/current','/download/all'):
                    name,kind,raw = player.download(path.endswith('/all'))
                    self.reply(200,raw,kind,name)
                else:
                    self.reply(404,{'error':'not found'})
            except Exception as exc:
                self.reply(400,{'error':str(exc)[:300]})

        def do_POST(self):
            try:
                self.local()
                if self.headers.get('X-Local-Token') != token:
                    raise PermissionError('local action token missing')
                length = int(self.headers.get('Content-Length','0'))
                if not 0 < length <= 4096:
                    raise ValueError('invalid request size')
                value = json.loads(self.rfile.read(length))
                if self.path == '/api/start':
                    result = player.start(value['game'])
                elif self.path == '/api/action':
                    result = player.action(value)
                elif self.path == '/api/stop':
                    result = {'stopped':True,'logs_saved':True}
                    threading.Thread(target=self.server.shutdown,daemon=True).start()
                else:
                    raise ValueError('unknown local action')
                self.reply(200,result)
            except Exception as exc:
                self.reply(400,{'error':str(exc)[:300]})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True,help='private git-ignored data directory')
    parser.add_argument('--port',type=int,default=8788)
    args = parser.parse_args()
    os.environ.update(CUDA_VISIBLE_DEVICES='',MPLBACKEND='Agg')
    player = ManualPlayer(args.data)
    server = ThreadingHTTPServer(('127.0.0.1',args.port),handler_for(player,secrets.token_hex(24)))
    print(f'Manual public-game player: http://127.0.0.1:{server.server_port}',flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
