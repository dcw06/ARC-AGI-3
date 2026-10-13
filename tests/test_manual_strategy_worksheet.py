"""Persistence, provenance and scope checks for the local annotation worksheet."""
from copy import deepcopy
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
import zipfile

from scripts.serve_manual_strategy_worksheet import (
    FIELDS, GAMES, Worksheet, build_cases, handler_for, private_directory,
)


def observation(game, level):
    grid = [[9]*64 for _ in range(64)]
    grid[0][0] = level+1
    return {'game_id': game+'-fixture', 'frames': [grid], 'levels_completed': level,
            'win_levels': 8, 'available_actions': [1, 2, 3, 4], 'state': 'NOT_FINISHED'}


def logs(folder):
    paths = []
    for game in GAMES:
        previous = observation(game, 0)
        rows = [{'type': 'session_start', 'actor': 'human_manual', 'game_id': game+'-fixture',
                 'schema': 'public_game_manual_v1', 'seed': 0, 'sdk_versions': {},
                 'exposure': 'synthetic unit fixture, not a human session', 'initial_observation': previous}]
        for index in range(6):
            level = (index+1)//2
            after = observation(game, level)
            sequence = index+1
            rows += [{'type': 'action_entered', 'sequence': sequence, 'request_id': str(sequence),
                      'before': previous, 'action': {'action_id': 1, 'action_data': {}}},
                     {'type': 'action_acknowledged', 'sequence': sequence, 'request_id': str(sequence),
                      'after': after, 'seconds': .01}]
            previous = after
        path = folder/(game+'.jsonl')
        path.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
        paths.append(path)
    return paths


class WorksheetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.paths = logs(self.root)
        self.folder = self.root/'answers'
        self.workspace = Worksheet(self.folder, self.paths)

    def tearDown(self):
        self.temporary.cleanup()

    def value(self):
        return {'case_id': 'ls20.level1', 'expected_revision': 0,
                'answers': {field: 'unknown' for field in FIELDS}, 'marks': [], 'status': 'draft'}

    def test_all_entries_and_no_following_level_boards(self):
        self.assertEqual(len(self.workspace.cases), 18)
        for case in self.workspace.cases.values():
            self.assertEqual(len(case['steps']), 2)
            self.assertTrue(case['completed'])
            self.assertEqual(len(case['frames']), 2)
            self.assertTrue(all(frame['grid'][0][0] == case['level'] for frame in case['frames']))
        self.assertFalse(any(any(row['answers'].values()) for row in self.workspace.document['cases'].values()))

    def test_broken_action_chain_is_refused(self):
        rows = [json.loads(row) for row in self.paths[0].read_text().splitlines()]
        rows[3]['before']['frames'][0][0][0] = 15
        self.paths[0].write_text('\n'.join(json.dumps(row) for row in rows))
        with self.assertRaisesRegex(ValueError, 'broken'):
            build_cases(self.paths)

    def test_save_restart_and_snapshot_preservation(self):
        value = self.value()
        value['answers']['objects'] = 'A distinct blue object.\nAn outlined target.'
        self.workspace.save(value)
        restarted = Worksheet(self.folder, self.paths)
        self.assertEqual(restarted.document['cases']['ls20.level1']['answers'], value['answers'])
        self.assertTrue((self.folder/'answers-revision-000001.json').exists())
        with self.assertRaises(RuntimeError):
            restarted.save(value)
        value['expected_revision'] = 1
        value['answers']['objects'] = 'Corrected description'
        restarted.save(value)
        old = json.loads((self.folder/'answers-revision-000001.json').read_bytes())
        self.assertIn('blue', old['cases']['ls20.level1']['answers']['objects'])

    def test_ready_requires_answers_without_claiming_validation(self):
        value = self.value()
        value['status'] = 'ready_for_review'
        value['answers']['rules'] = ''
        with self.assertRaises(ValueError):
            self.workspace.save(value)
        value['answers']['rules'] = 'unknown'
        self.assertEqual(self.workspace.save(value)['status'], 'ready_for_review')
        self.assertIn('not independently validated', self.workspace.document['qualification'])

    def test_mark_and_revision_types_and_frame_binding(self):
        value = self.value()
        value['marks'] = [{'label': 'controlled piece', 'kind': 'controlled_object', 'x': 5, 'y': 6,
                           'frame_index': 0, 'grid_sha256': self.workspace.cases['ls20.level1']['frames'][0]['grid_sha256']}]
        invalid = deepcopy(value)
        invalid['marks'][0]['x'] = True
        with self.assertRaises(ValueError):
            self.workspace.save(invalid)
        invalid = deepcopy(value)
        invalid['marks'][0]['grid_sha256'] = 'wrong board'
        with self.assertRaises(ValueError):
            self.workspace.save(invalid)
        invalid = deepcopy(value)
        invalid['expected_revision'] = False
        with self.assertRaises(RuntimeError):
            self.workspace.save(invalid)
        self.assertEqual(self.workspace.save(value)['marks'], value['marks'])

    def test_changed_source_refuses_existing_answers(self):
        self.paths[0].write_text(self.paths[0].read_text()+'\n')
        with self.assertRaisesRegex(ValueError, 'different logs'):
            Worksheet(self.folder, self.paths)

    def test_export_has_answers_boards_and_bound_provenance(self):
        self.workspace.save(self.value())
        name, kind, raw = self.workspace.export(True)
        self.assertEqual(kind, 'application/zip')
        with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
            self.assertEqual(set(bundle.namelist()), {'answers.json', 'cases.json', 'provenance.json', 'README.txt'})
            answers = json.loads(bundle.read('answers.json'))
            provenance = json.loads(bundle.read('provenance.json'))
            self.assertEqual(answers['context_sha256'], provenance['context_sha256'])
            self.assertEqual(answers['cases']['ls20.level1']['revision'], 1)

    def test_tracked_output_is_refused(self):
        with self.assertRaises(ValueError):
            private_directory(Path(__file__).resolve().parents[1]/'reports/worksheet-not-private')

    def test_http_refuses_missing_token_and_cross_origin(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(self.workspace, 'unit-test-only'))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            def post(headers):
                connection = HTTPConnection('127.0.0.1', server.server_port)
                connection.request('POST', '/api/save', json.dumps(self.value()), headers)
                response = connection.getresponse()
                status = response.status
                response.read()
                connection.close()
                return status
            self.assertEqual(post({'Content-Type': 'application/json'}), 400)
            self.assertEqual(post({'X-Local-Token': 'unit-test-only', 'Origin': 'https://example.com'}), 400)
            self.assertEqual(self.workspace.document['revision'], 0)
            self.assertEqual(post({'X-Local-Token': 'unit-test-only'}), 200)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
