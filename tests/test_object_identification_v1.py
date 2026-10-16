"""Behavioral checks for private probe separation and honest localization scoring."""
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from research.object_identification_v1.probe import (
    GAMES, MODEL, MODEL_REVISION, canonical, digest, evaluate, match,
    parse_prediction, prepare, score_case, sha, verify,
)


def region(rid='piece', bounds=None, parent=None, kind='controlled_object'):
    bounds = bounds or [2, 3, 3, 4]
    x0, y0, x1, y1 = bounds
    return {'id': rid, 'label': 'synthetic visible square', 'kind': kind,
            'frame_index': 0, 'parent_id': parent, 'geometry': 'rectangle',
            'target_points': [[x, y] for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)],
            'bbox_xyxy': bounds}


def prediction(pid='p1', bounds=None):
    return {'id': pid, 'description': 'visible square', 'bbox_xyxy': bounds or [2, 3, 3, 4],
            'role_guess': 'unknown'}


def snapshot(folder):
    folder.mkdir()
    answers, cases = {'cases': {}, 'context_sha256': 'synthetic-only'}, {}
    for game in GAMES:
        grid = [[5] * 64 for _ in range(64)]
        for x, y in region()['target_points']:
            grid[y][x] = 14
        r = region(kind='obstacle' if game == GAMES[0] else 'controlled_object')
        r['grid_sha256'] = digest(grid)
        key = game + '.level1'
        cases[key] = {'frames': [{'grid': grid, 'grid_sha256': digest(grid)}]}
        answers['cases'][key] = {'revision': 1, 'regions': [r]}
    values = {'answers.json': answers, 'cases.json': cases, 'provenance.json': {'synthetic': True}}
    files = {}
    for name, value in values.items():
        raw = canonical(value)
        (folder / name).write_bytes(raw)
        files[name] = {'sha256': sha(raw), 'bytes': len(raw)}
    (folder / 'snapshot-manifest.json').write_bytes(canonical({
        'files': files, 'context_sha256': 'synthetic-only', 'qualification': 'unit fixture only'}))


class LocalizationTests(unittest.TestCase):
    def test_full_board_box_does_not_cover_small_object(self):
        result = score_case({'case_id': 'fixture', 'regions': [region()]},
                            json.dumps({'objects': [prediction(bounds=[0, 0, 63, 63])]}), 'stop')
        self.assertTrue(result['response_valid'])
        self.assertEqual(result['localization']['whole_regions']['matched'], 0)

    def test_one_prediction_cannot_cover_two_whole_objects(self):
        refs = [region('a'), region('b')]
        self.assertEqual(len(match(refs, [prediction()])), 1)

    def test_matching_reassigns_an_earlier_match_to_cover_both_objects(self):
        refs = [region('a', [0, 0, 9, 0]), region('b', [0, 0, 4, 0])]
        preds = [prediction('p1', [0, 0, 5, 0]), prediction('p2', [4, 0, 9, 0])]
        self.assertEqual(len(match(refs, preds)), 2)

    def test_parts_are_separate_and_obstacle_guess_is_not_mechanical_truth(self):
        ref = {'case_id': 'fixture', 'regions': [region('parent', kind='obstacle'),
                                                region('child', parent='parent')]}
        pred = prediction()
        pred['role_guess'] = 'obstacle_candidate'
        result = score_case(ref, json.dumps({'objects': [pred]}), 'stop')
        self.assertEqual(result['localization']['whole_regions']['matched'], 1)
        self.assertEqual(result['localization']['parts']['matched'], 1)
        self.assertIsNone(result['obstacles']['movement_blocking_accuracy'])
        self.assertNotIn('precision', result)

    def test_strict_coordinates_duplicate_keys_and_truncation(self):
        for coordinate in (True, 2.5, -1, 64):
            with self.subTest(coordinate=coordinate):
                pred = prediction()
                pred['bbox_xyxy'][0] = coordinate
                with self.assertRaises(ValueError):
                    parse_prediction(json.dumps({'objects': [pred]}), 'stop')
        for raw, finish in [('{}', 'stop'), ('{"objects":[],"objects":[]}', 'stop'),
                            ('{"objects":[]}', 'length')]:
            with self.assertRaises(ValueError):
                parse_prediction(raw, finish)

    def test_unmatched_predictions_are_unreviewed_not_false_positives(self):
        result = score_case({'case_id': 'fixture', 'regions': [region()]},
                            json.dumps({'objects': [prediction(), prediction('extra', [40, 40, 45, 45])]}),
                            'stop')
        self.assertEqual(result['localization']['whole_regions']['matched'], 1)
        self.assertEqual(result['localization']['whole_regions']['unmatched_prediction_ids_for_review'],
                         ['extra'])
        self.assertNotIn('false_positives', result)


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source, self.bundle = self.root / 'source', self.root / 'bundle'
        snapshot(self.source)
        self.receipt = prepare(self.source, self.bundle)

    def tearDown(self):
        self.temp.cleanup()

    def response(self):
        request = json.loads((self.bundle / 'inputs/requests.jsonl').read_bytes().splitlines()[0])
        return {'case_id': request['case_id'], 'model': MODEL, 'model_revision': MODEL_REVISION,
                'request_sha256': sha(canonical(request)),
                'content': json.dumps({'objects': [prediction()]}), 'finish_reason': 'stop'}

    def test_answer_free_model_archive_and_gpu_off_refusal(self):
        verify(self.bundle)
        with zipfile.ZipFile(self.bundle / 'model-inputs-only.zip') as archive:
            self.assertEqual(len(archive.namelist()), 7)
            self.assertTrue(all(name.startswith('inputs/') for name in archive.namelist()))
            request = json.loads(archive.read('inputs/requests.jsonl').splitlines()[0])
            self.assertNotIn('regions', request)
            self.assertNotIn('source_case_id', request)
        meta = json.loads((self.bundle / 'kaggle-review/kernel-metadata.json').read_bytes())
        self.assertTrue(meta['is_private'])
        self.assertFalse(meta['enable_gpu'])
        self.assertFalse(meta['enable_tpu'])
        self.assertFalse(meta['enable_internet'])
        book = json.loads((self.bundle / 'kaggle-review/profile.ipynb').read_bytes())
        cell = next(c for c in book['cells'] if c['cell_type'] == 'code')
        with self.assertRaisesRegex(SystemExit, 'REVIEW ONLY'):
            exec(compile(''.join(cell['source']), '<review-refusal>', 'exec'), {})

    def test_missing_and_malformed_answers_remain_in_planned_inventory(self):
        row = self.response()
        row['finish_reason'] = 'length'
        responses = self.root / 'responses.jsonl'
        responses.write_bytes(canonical(row))
        result = evaluate(self.bundle, responses)
        self.assertEqual(result['planned_cases'], 6)
        self.assertEqual(result['available_responses'], 1)
        self.assertEqual(result['valid_responses'], 0)
        self.assertEqual(len(result['missing_case_ids']), 5)

    def test_wrong_request_revision_and_duplicate_response_are_refused(self):
        for field in ('request_sha256', 'model_revision'):
            row = self.response()
            row[field] = 'wrong'
            path = self.root / (field + '.jsonl')
            path.write_bytes(canonical(row))
            with self.assertRaisesRegex(ValueError, 'mismatch'):
                evaluate(self.bundle, path)
        path = self.root / 'duplicate.jsonl'
        row = self.response()
        path.write_bytes(canonical(row) * 2)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            evaluate(self.bundle, path)

    def test_mutated_image_and_snapshot_are_refused(self):
        (self.bundle / 'inputs/board-01.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            verify(self.bundle)
        (self.source / 'cases.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'snapshot hash/size mismatch'):
            prepare(self.source, self.root / 'new-bundle')

    def test_preparation_never_overwrites_an_existing_attempt(self):
        with self.assertRaisesRegex(ValueError, 'already exists'):
            prepare(self.source, self.bundle)


if __name__ == '__main__':
    unittest.main()
