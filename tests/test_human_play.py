"""Real offline game/API smoke tests. Run --prepare first; no network in tests."""
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import uuid
import zipfile

from human_play.server import DEFAULT_GAMES, GAMES, PlayError, Store, serve


@unittest.skipUnless(DEFAULT_GAMES.is_dir(), 'run python scripts/play_human.py --prepare first')
class HumanPlay(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.logs = Path(self.temp.name)
        self.store = Store(logs_dir=self.logs)

    def tearDown(self):
        self.temp.cleanup()

    def move(self, session, action_id, **coords):
        return session.step({'action_id': action_id, 'event_id': uuid.uuid4().hex,
                             'expected_sequence': session.sequence, **coords})

    def test_all_available_real_games_load(self):
        self.assertEqual([g['id'] for g in self.store.games()], list(GAMES))
        self.assertTrue(all(g['ready'] for g in self.store.games()))
        for code in GAMES:
            with self.subTest(game=code):
                s = self.store.create({'game_id': code})
                self.assertGreater(s.current['win_levels'], 0)
                self.assertEqual(s.current['state'], 'NOT_FINISHED')
                self.assertEqual(len(s.current['frames'][-1]), 64)
                self.assertEqual(len(s.current['frames'][-1][0]), 64)

    def test_first_three_actions_reset_and_full_transition_evidence(self):
        for code in GAMES[:3]:
            with self.subTest(game=code):
                s = self.store.create({'game_id': code})
                self.move(s, 1)
                if 6 in s.current['available_actions']:
                    self.move(s, 6, x=32, y=32)
                self.move(s, 0)
                exported = s.export()
                raws = exported['transitions']
                self.assertEqual(len(raws), s.sequence)
                self.assertTrue(all(r['outcome']['status'] == 'acknowledged' for r in raws))
                for index, raw in enumerate(raws):
                    self.assertEqual(raw['identity'], {'episode_id': s.session_id, 'action_index': index})
                    self.assertEqual(raw['proposal'], raw['dispatched'])
                    self.assertEqual(len(raw['before']['frames'][-1]), 64)
                    self.assertTrue(raw['outcome']['after']['frames'])
                    self.assertIn('available_actions', raw['before'])
                    self.assertIn('full_reset', raw['outcome']['after'])
                for a, b in zip(raws, raws[1:]):
                    self.assertEqual(a['outcome']['after'], b['before'])

    def test_exact_coordinates_not_scaled_or_clamped_by_server(self):
        s = self.store.create({'game_id': 'lf52'})
        self.move(s, 6, x=0, y=63)
        self.assertEqual(s.export()['transitions'][0]['dispatched']['action_data'], {'x': 0, 'y': 63})
        for x, y in ((64, 0), (-1, 0), (0, 64), (True, 0), (0.5, 1)):
            with self.assertRaises(PlayError):
                self.move(s, 6, x=x, y=y)
        self.assertEqual(s.sequence, 1)

    def test_idempotent_action_and_stale_tab_protection(self):
        s = self.store.create({'game_id': 'g50t'})
        body = {'action_id': 1, 'event_id': 'same-action', 'expected_sequence': 0}
        s.step(body)
        self.assertTrue(s.step(body)['duplicate'])
        self.assertEqual(s.sequence, 1)
        with self.assertRaises(PlayError):
            s.step({**body, 'event_id': 'stale-tab'})
        with self.assertRaises(PlayError):
            s.step({**body, 'action_id': 2})
        self.assertEqual(s.sequence, 1)

    def test_unavailable_action_does_not_dispatch(self):
        s = self.store.create({'game_id': 'vc33'})
        with self.assertRaises(PlayError):
            self.move(s, 1)
        self.assertEqual(s.sequence, 0)
        self.assertEqual(len(s.events), 1)

    def test_server_restart_replays_exact_state_and_dedup_ids(self):
        s = self.store.create({'game_id': 'g50t', 'seed': 7})
        self.move(s, 1)
        self.move(s, 4)
        old = s.view()
        restored = Store(logs_dir=self.logs).get(s.session_id)
        self.assertEqual(restored.current, old['observation'])
        self.assertEqual(restored.sequence, old['sequence'])
        self.assertEqual(restored.applied, s.applied)
        self.move(restored, 2)
        self.assertEqual(restored.sequence, 3)

    def test_missing_engine_result_is_unknown_and_blocks_more_actions(self):
        s = self.store.create({'game_id': 'ar25'})
        with patch.object(s.env, 'step', return_value=None):
            self.move(s, 1)
        self.assertTrue(s.uncertain)
        self.assertEqual(s.export()['transitions'][0]['outcome']['status'], 'outcome_unknown')
        with self.assertRaises(PlayError):
            self.move(s, 0)
        restored = Store(logs_dir=self.logs).get(s.session_id)
        self.assertTrue(restored.uncertain)

    def test_unfinished_dispatch_intent_stops_recovery(self):
        s = self.store.create({'game_id': 'ar25'})
        s.append({'type': 'intent', 'event_id': 'interrupted', 'sequence': 1,
                  'action': {'action_id': 1, 'action_data': {}}, 'before_sha256': 'test'})
        restored = Store(logs_dir=self.logs).get(s.session_id)
        self.assertTrue(restored.uncertain)
        self.assertEqual(restored.sequence, 0)

    def test_failed_log_write_after_dispatch_blocks_session(self):
        s = self.store.create({'game_id': 'ar25'})
        append = s.append
        def fail_result(event):
            if event['type'] == 'action':
                raise OSError('simulated full disk')
            append(event)
        with patch.object(s, 'append', side_effect=fail_result):
            with self.assertRaises(PlayError):
                self.move(s, 1)
        self.assertTrue(s.uncertain)
        self.assertIsNotNone(s.pending)

    def test_http_ui_download_notes_and_safety(self):
        server = serve(self.store, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        def request(path, body=None, headers=None):
            h = {'X-Arc-Play': '1', 'Content-Type': 'application/json', **(headers or {})}
            return urlopen(Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                   headers=h), timeout=10)
        try:
            with request('/') as response:
                self.assertEqual(response.status, 200)
                self.assertIn('下载日志', response.read().decode())
                self.assertIn("frame-ancestors 'none'", response.headers['Content-Security-Policy'])
            with request('/api/sessions', {'game_id': 'lf52'}) as r:
                session = json.load(r)
            sid = session['session_id']
            with request(f'/api/sessions/{sid}/action', {'action_id': 6, 'x': 5, 'y': 6,
                    'event_id': 'http-click', 'expected_sequence': 0}) as r:
                self.assertEqual(json.load(r)['sequence'], 1)
            with request(f'/api/sessions/{sid}/note', {'text': '测试笔记：不把猜测当成事实'}) as r:
                self.assertEqual(len(json.load(r)['notes']), 1)
            with request(f'/api/sessions/{sid}/annotation', {'name': '测试区域',
                    'corners': [{'x': 2, 'y': 3}, {'x': 4, 'y': 4}], 'expected_sequence': 1}) as r:
                view = json.load(r)
                self.assertEqual(view['sequence'], 1)
                self.assertEqual(view['annotations'][0]['region']['cell_count'], 6)
            with request(f'/api/sessions/{sid}/download') as r:
                self.assertIn('attachment', r.headers['Content-Disposition'])
                data = json.load(r)
                self.assertEqual(data['transitions'][0]['dispatched']['action_data'], {'x': 5, 'y': 6})
                self.assertEqual(data['metadata']['runtime']['arcengine'], '0.9.3')
                self.assertEqual(data['annotations'][0]['cells'][0]['index'], 3*64+2)
                self.assertNotIn('api_key', json.dumps(data))
            with request(f'/api/sessions/{sid}/end', {}) as r:
                self.assertTrue(json.load(r)['closed'])
            with request(f'/api/sessions/{sid}/download.zip') as r:
                with zipfile.ZipFile(io.BytesIO(r.read())) as z:
                    self.assertEqual(set(z.namelist()), {'session.json', 'events.jsonl'})
                    self.assertTrue(json.loads(z.read('session.json'))['summary']['closed'])
            for path in ('/.env', '/../.env', '/human_play/server.py', '/api/sessions/not-a-session'):
                with self.assertRaises(HTTPError) as error:
                    request(path)
                self.assertEqual(error.exception.code, 404)
            with self.assertRaises(HTTPError) as error:
                request('/api/sessions', {'game_id': 'ar25'}, {'Origin': 'https://other-site.example'})
            self.assertEqual(error.exception.code, 403)
            # Archives remain downloadable without replaying the engine.
            self.store.sessions.clear()
            with request(f'/api/sessions/{sid}/download') as r:
                archive = json.load(r)
                self.assertEqual(len(archive['transitions']), 1)
                self.assertEqual(len(archive['annotations']), 1)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
