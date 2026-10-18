"""Isolation, timing, geometry and independent replay regressions; no model."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research.initial_geometry_assistance_v1.audit import audit_episode
from research.initial_geometry_assistance_v1.engine import verify_game_environment
from research.initial_geometry_assistance_v1.episodes import episode
from research.initial_geometry_assistance_v1.geometry import (
    check_inventory, checked_cells, decode_mask, digest, encode_mask, inventory)
from research.initial_geometry_assistance_v1.policy import parse_answer, request_for
from research.initial_geometry_assistance_v1.prepare import pinned
from certification.phase4_multimodal_preflight_v3.images import grid_from_png
import base64


def fixture():
    grid = [[0]*64 for _ in range(64)]
    return {'case_id': 'board-01', 'game_id': 'fixture-version', 'grid': grid, 'grid_sha256': digest(grid),
            'geometry': {'automatic': [], 'reviewed': inventory([[[7, 9], [8, 9]]])}}


class Engine:
    def __init__(self, case, win=False):
        self.obs = {'grid': deepcopy(case['grid']), 'state': 'NOT_FINISHED',
                    'levels_completed': 0, 'legal_actions': [1, 6]}
        self.calls = 0
        self.closes = 0
        self.win = win

    def bootstrap(self):
        return deepcopy(self.obs)

    def dispatch(self, action):
        self.calls += 1
        self.obs['grid'][0][0] = self.calls
        if self.win:
            self.obs['levels_completed'] = 1
        return deepcopy(self.obs)

    def close(self):
        self.closes += 1
        return {'closed': True, 'local_scorecard_opened': True, 'local_scorecard_closed': True, 'online_calls': 0}


class BrokenEngine(Engine):
    def dispatch(self, action):
        self.calls += 1
        raise RuntimeError('engine failed')


class FailingClose(BrokenEngine):
    def close(self):
        self.closes += 1
        raise OSError('close failed')


ANSWER = '{"action_id":6,"action_data":{"x":7,"y":9},"predicted_visible_change":"yes"}'


def trace(win=False, response=ANSWER, arm='reviewed'):
    case = fixture()
    engine = Engine(case, win=win)
    events = []
    result = episode(case, arm, engine, lambda _: response, events.append,
                     model='frozen-model', deadline=10, cap=2, now=lambda: 0)
    return case, engine, events, result


def interrupted(engine=None, win=False, late_record=None, deadline=10):
    """Run an episode that must raise; writing `late_record` moves the clock past the deadline."""
    case, clock, events = fixture(), [0], []
    engine = engine or Engine(case, win=win)

    def sink(event):
        events.append(event)
        if event['kind'] == late_record:
            clock[0] = 11
    try:
        episode(case, 'reviewed', engine, lambda _: ANSWER, sink, model='frozen-model', deadline=deadline, cap=2,
                now=lambda: clock[0])
    except BaseException as exc:
        return case, engine, events, exc
    raise AssertionError('episode did not raise')


class GeometryTests(unittest.TestCase):
    def test_hollow_object_anchor_is_occupied(self):
        cells = [[1, 1], [2, 1], [3, 1], [1, 2], [3, 2], [1, 3], [2, 3], [3, 3]]
        mask = encode_mask(cells)
        self.assertIn(mask['occupied_anchor_xy'], cells)
        self.assertNotEqual(mask['occupied_anchor_xy'], [2, 2])
        self.assertEqual(decode_mask(mask), cells)

    def test_multicolor_disconnected_mask_is_not_split(self):
        mask = encode_mask([[0, 0], [63, 63], [62, 63]])
        self.assertEqual(len(decode_mask(mask)), 3)

    def test_all_cells_roundtrip(self):
        cells = [[x, y] for y in range(64) for x in range(64)]
        self.assertEqual(len(encode_mask(cells)['row_runs_y_x0_x1_inclusive']), 64)
        self.assertEqual(decode_mask(encode_mask(cells)), cells)

    def test_empty_and_duplicate_proposals_retained(self):
        objects = inventory([[], [[7, 9]], [[7, 9]]])
        self.assertEqual(len(objects), 3)
        self.assertEqual(check_inventory(objects), objects)

    def test_bad_cells_refused(self):
        for cells in ([[True, 1]], [[1.0, 2]], [[64, 2]], [[1, 2], [1, 2]]):
            with self.subTest(cells=cells), self.assertRaises(ValueError):
                checked_cells(cells)

    def test_semantic_geometry_fields_refused(self):
        objects = inventory([[[1, 1]]])
        objects[0]['role'] = 'player'
        with self.assertRaises(ValueError):
            check_inventory(objects)

    def test_false_centroid_anchor_refused(self):
        mask = encode_mask([[1, 1], [3, 3]])
        mask['occupied_anchor_xy'] = [2, 2]
        with self.assertRaises(ValueError):
            decode_mask(mask)

    def test_source_labels_cannot_change_neutral_ids(self):
        self.assertEqual(inventory([[[7, 9]], [[20, 1]]]), inventory([[[20, 1]], [[7, 9]]]))


class PolicyTests(unittest.TestCase):
    def test_legal_action(self):
        self.assertEqual(parse_answer(ANSWER, [6])['action_data'], {'x': 7, 'y': 9})

    def test_no_reset_or_illegal_action(self):
        for action in (0, True, 1.0, 7):
            text = json.dumps({'action_id': action, 'action_data': {}, 'predicted_visible_change': 'yes'})
            with self.subTest(action=action), self.assertRaises(ValueError):
                parse_answer(text, [1, 6])

    def test_no_coordinate_rounding_or_clamping(self):
        for x in (-1, 64, True, 7.0):
            text = ANSWER.replace('"x":7', '"x":'+json.dumps(x))
            with self.subTest(x=x), self.assertRaises(ValueError):
                parse_answer(text, [6])

    def test_duplicate_and_extra_answer_fields(self):
        for text in (ANSWER.replace('"action_id":6', '"action_id":6,"action_id":1'),
                     ANSWER[:-1]+',"rationale":"move it"}', '```json\n'+ANSWER+'\n```'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_answer(text, [1, 6])

    def test_arm_name_and_game_id_not_in_request(self):
        case = fixture()
        obs = Engine(case).bootstrap()
        requests = [request_for(obs, case['geometry'][arm], obs, [], 0, 'model') for arm in ('automatic', 'reviewed')]
        left, right = deepcopy(requests[0]), deepcopy(requests[1])
        for body in (left, right):
            meta = json.loads(body['messages'][1]['content'][0]['text'])
            meta.pop('initial_objects')
            body['messages'][1]['content'][0]['text'] = json.dumps(meta)
        self.assertEqual(left, right)
        self.assertNotIn('fixture-version', json.dumps(requests))

    def test_current_image_and_geometry_timestamp(self):
        case = fixture()
        initial = Engine(case).bootstrap()
        current = deepcopy(initial)
        current['grid'][0][0] = 4
        history = [{'step': 0, 'before': initial, 'after': current, 'action': {'action_id': 1, 'action_data': {}}}]
        request = request_for(initial, case['geometry']['reviewed'], current, history, 1, 'model')
        content = request['messages'][1]['content']
        meta = json.loads(content[0]['text'])
        self.assertEqual(meta['geometry_observed_at_step'], 0)
        self.assertEqual(meta['geometry_initial_grid_sha256'], digest(initial['grid']))
        raw = base64.b64decode(content[-1]['image_url']['url'].split(',')[1])
        self.assertEqual(grid_from_png(raw, cell=7), current['grid'])


class EpisodeTests(unittest.TestCase):
    def test_stops_on_first_level(self):
        _, engine, _, result = trace(win=True)
        self.assertEqual(engine.calls, 1)
        self.assertEqual(result['stop_reason'], 'first_level_complete')
        self.assertEqual(engine.closes, 1)

    def test_cap_no_retry(self):
        _, engine, _, result = trace()
        self.assertEqual(engine.calls, 2)
        self.assertEqual(result['policy_calls'], 2)
        self.assertEqual(result['stop_reason'], 'action_cap')

    def test_invalid_response_no_action_no_repair(self):
        _, engine, _, result = trace(response='not JSON')
        self.assertEqual(engine.calls, 0)
        self.assertEqual(result['policy_calls'], 1)
        self.assertEqual(result['stop_reason'], 'invalid_answer')

    def test_initial_board_mismatch_closes_without_policy(self):
        case = fixture()
        engine = Engine(case)
        engine.obs['grid'][0][0] = 1
        with self.assertRaisesRegex(ValueError, 'reviewed level-1'):
            episode(case, 'automatic', engine, lambda _: self.fail('unexpected policy call'), lambda _: None,
                    model='model', deadline=10, now=lambda: 0)
        self.assertEqual(engine.closes, 1)

    def test_interrupted_bootstrap_record_closes(self):
        engine = Engine(fixture())
        def sink(_):
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            episode(fixture(), 'automatic', engine, lambda _: ANSWER, sink, model='model', deadline=10, now=lambda: 0)
        self.assertEqual(engine.closes, 1)

    def test_inference_overrun_no_dispatch(self):
        clock = [0]
        engine = Engine(fixture())
        def complete(_):
            clock[0] = 11
            return ANSWER
        with self.assertRaises(TimeoutError):
            episode(fixture(), 'automatic', engine, complete, lambda _: None, model='model', deadline=10, now=lambda: clock[0])
        self.assertEqual(engine.calls, 0)
        self.assertEqual(engine.closes, 1)

    def test_slow_dispatch_intent_write_cannot_admit_action(self):
        clock = [0]
        engine = Engine(fixture())
        def sink(event):
            if event['kind'] == 'dispatch_intent':
                clock[0] = 11
        with self.assertRaises(TimeoutError):
            episode(fixture(), 'automatic', engine, lambda _: ANSWER, sink, model='model', deadline=10, now=lambda: clock[0])
        self.assertEqual(engine.calls, 0)

    def test_late_summary_write_cannot_return_success(self):
        clock = [0]
        engine = Engine(fixture(), win=True)
        def sink(event):
            if event['kind'] == 'summary':
                self.assertFalse(event['lifecycle_certified'])
                clock[0] = 11
        with self.assertRaises(TimeoutError):
            episode(fixture(), 'automatic', engine, lambda _: ANSWER, sink, model='model', deadline=10, now=lambda: clock[0])


class AuditTests(unittest.TestCase):
    def test_complete_engine_replay(self):
        case, _, events, _ = trace()
        result = audit_episode(case, 'reviewed', events, model='frozen-model', cap=2, replay_engine=Engine(case))
        self.assertTrue(result['engine_replayed'])
        self.assertTrue(result['first_action_click_on_reviewed_object'])
        self.assertEqual(result['correct_visible_change_predictions'], 2)
        self.assertFalse(result['lifecycle_certified'])
        self.assertFalse(result['outcome_claim_permitted'])

    def test_invalid_answer_trace_kept(self):
        case, _, events, _ = trace(response='bad')
        result = audit_episode(case, 'reviewed', events, model='frozen-model', cap=2)
        self.assertEqual(result['stop_reason'], 'invalid_answer')

    def test_first_click_is_reported_against_each_arms_supplied_geometry(self):
        inside = ANSWER.replace('"x":7', '"x":8')
        for arm, response, expected in (('reviewed', ANSWER, (True, True, True)),
                                        ('reviewed', inside, (True, True, False)),
                                        ('automatic', ANSWER, (True, False, False))):
            case, _, events, _ = trace(response=response, arm=arm)
            self.assertEqual(case['geometry']['reviewed'][0]['occupied_anchor_xy'], [7, 9])
            result = audit_episode(case, arm, events, model='frozen-model', cap=2)
            with self.subTest(arm=arm, response=response):
                self.assertEqual((result['first_action_click_on_reviewed_object'],
                                  result['first_action_click_in_supplied_mask'],
                                  result['first_action_click_on_supplied_anchor']), expected)
        case, _, events, _ = trace(response='{"action_id":1,"action_data":{},"predicted_visible_change":"no"}')
        result = audit_episode(case, 'reviewed', events, model='frozen-model', cap=2)
        self.assertEqual({result[k] for k in result if k.startswith('first_action_click')}, {None})

    def test_changed_request_cannot_be_rehashed_into_validity(self):
        case, _, events, _ = trace()
        for mutate in (lambda r: r.update(model='another-model'),
                       lambda r: r['messages'][0].update(content='changed system'),
                       lambda r: r['messages'][1].update(role='assistant'),
                       lambda r: r.update(response_format={'type': 'text'})):
            changed = deepcopy(events)
            req = next(e for e in changed if e['kind'] == 'request')
            mutate(req['body']); req['request_sha256'] = digest(req['body'])
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                audit_episode(case, 'reviewed', changed, model='frozen-model', cap=2)

    def test_terminal_and_count_tampering_refused(self):
        case, _, events, _ = trace()
        for key, value in (('stop_reason', 'first_level_complete'), ('dispatches', 0), ('policy_calls', 0)):
            changed = deepcopy(events)
            changed[-1][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                audit_episode(case, 'reviewed', changed, model='frozen-model', cap=2)

    def test_boolean_counts_and_invalid_elapsed_refused(self):
        case, _, events, _ = trace(win=True)
        for key, value in (('dispatches', True), ('policy_calls', True), ('elapsed_seconds', float('inf')),
                           ('elapsed_seconds', -1), ('lifecycle_certified', 0)):
            changed = deepcopy(events)
            changed[-1][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                audit_episode(case, 'reviewed', changed, model='frozen-model', cap=2)

    def test_grid_tampering_detected_by_engine_replay(self):
        case, _, events, _ = trace(win=True)
        transition = next(e for e in events if e['kind'] == 'transition')
        transition['after']['grid'][0][1] = 7
        events[-1]['final_observation']['grid'][0][1] = 7
        with self.assertRaisesRegex(ValueError, 'engine transition'):
            audit_episode(case, 'reviewed', events, model='frozen-model', cap=2, replay_engine=Engine(case, win=True))

    def test_missing_response_or_transition_refused(self):
        case, _, events, _ = trace()
        for kind in ('response', 'transition', 'closed'):
            changed = deepcopy(events)
            changed.pop(next(i for i, e in enumerate(changed) if e['kind'] == kind))
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                audit_episode(case, 'reviewed', changed, model='frozen-model', cap=2)

    def test_reference_hash_checked_before_loading(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'changed.json'
            path.write_text('this is deliberately not JSON')
            with self.assertRaisesRegex(ValueError, 'input hash differs'):
                pinned(path, '0'*64)


class InterruptionTests(unittest.TestCase):
    def test_each_cut_off_point_ends_with_a_classified_record(self):
        for late, calls, dispatches, model_unconfirmed, dispatch_unconfirmed in (
                ('request', 0, 0, True, False), ('response', 1, 0, False, False),
                ('dispatch_intent', 1, 0, False, True), ('transition', 1, 1, False, False)):
            case, engine, events, exc = interrupted(late_record=late)
            with self.subTest(late=late):
                self.assertIsInstance(exc, TimeoutError)
                self.assertEqual([e['kind'] for e in events[-2:]], ['closed', 'summary'])
                self.assertEqual((events[-1]['stop_reason'], engine.calls, engine.closes), ('deadline', dispatches, 1))
                result = audit_episode(case, 'reviewed', events, model='frozen-model', cap=2, replay_engine=Engine(case))
                self.assertEqual((result['stop_reason'], result['policy_calls'], result['dispatches']),
                                 ('deadline', calls, dispatches))
                self.assertEqual((result['unconfirmed_model_call'], result['unconfirmed_dispatch']),
                                 (model_unconfirmed, dispatch_unconfirmed))
                self.assertFalse(result['first_level_complete'])

    def test_completion_is_kept_when_the_deadline_passes_during_its_record(self):
        case, _, events, exc = interrupted(win=True, late_record='transition')
        self.assertIsInstance(exc, TimeoutError)  # a late final write still cannot return success
        self.assertEqual(events[-1]['stop_reason'], 'first_level_complete')
        result = audit_episode(case, 'reviewed', events, model='frozen-model', cap=2,
                               replay_engine=Engine(case, win=True))
        self.assertTrue(result['first_level_complete'])

    def test_admission_closed_before_start_is_recorded(self):
        case, engine, events, exc = interrupted(deadline=0)
        self.assertIsInstance(exc, TimeoutError)
        self.assertEqual([e['kind'] for e in events], ['closed', 'summary'])
        self.assertIsNone(events[-1]['final_observation'])
        result = audit_episode(case, 'reviewed', events, model='frozen-model', cap=2)
        self.assertEqual((result['stop_reason'], result['policy_calls'], result['dispatches']), ('deadline', 0, 0))

    def test_engine_error_is_recorded_with_an_unconfirmed_dispatch(self):
        case, _, events, exc = interrupted(engine=BrokenEngine(fixture()))
        self.assertIsInstance(exc, RuntimeError)
        self.assertEqual(events[-1]['error'], 'RuntimeError: engine failed')
        result = audit_episode(case, 'reviewed', events, model='frozen-model', cap=2)
        self.assertEqual((result['stop_reason'], result['dispatches'], result['unconfirmed_dispatch']),
                         ('exception', 0, True))

    def test_close_failure_is_recorded_without_replacing_the_stop_error(self):
        case, engine, events, exc = interrupted(engine=FailingClose(fixture()))
        self.assertIsInstance(exc, RuntimeError)
        self.assertEqual(engine.closes, 1)
        self.assertEqual(events[-2], {'kind': 'closed', 'receipt': None, 'error': 'OSError: close failed'})
        self.assertEqual(events[-1]['error'], 'RuntimeError: engine failed')
        with self.assertRaisesRegex(ValueError, 'engine close not established'):
            audit_episode(case, 'reviewed', events, model='frozen-model', cap=2)

    def test_stop_reason_must_match_where_the_record_ends(self):
        late, won, full = interrupted(late_record='response'), interrupted(win=True, late_record='transition'), trace()
        for (case, _, events, _), changes in ((late, {'stop_reason': 'action_cap', 'error': None}),
                                              (late, {'error': None}),
                                              (won, {'stop_reason': 'deadline', 'error': 'TimeoutError: late'}),
                                              (full, {'stop_reason': 'deadline', 'error': 'TimeoutError: late'})):
            changed = deepcopy(events)
            changed[-1].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                audit_episode(case, 'reviewed', changed, model='frozen-model', cap=2)


class GameEnvironmentTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        files = {'environment_files/g1/v1/g1.py': b'game = 1\n', 'environment_files/g1/v1/metadata.json': b'{}',
                 'wheels/w-1.0-py3-none-any.whl': b'wheel', 'game_requirements.lock': b'w==1.0\n'}
        for name, raw in files.items():
            (self.root/name).parent.mkdir(parents=True, exist_ok=True)
            (self.root/name).write_bytes(raw)
        receipt = {'verified_members': {n: {'sha256': hashlib.sha256(r).hexdigest(), 'bytes': len(r)}
                                        for n, r in files.items() if n != 'game_requirements.lock'},
                   'requirements_sha256': hashlib.sha256(files['game_requirements.lock']).hexdigest()}
        raw = json.dumps(receipt).encode()
        (self.root/'receipt.json').write_bytes(raw)
        self.pin = hashlib.sha256(raw).hexdigest()

    def test_pinned_environment_passes_and_both_hashes_are_returned(self):
        self.assertEqual(verify_game_environment(self.root, self.pin),
                         {'game_environment_receipt_sha256': self.pin,
                          'game_requirements_sha256': hashlib.sha256(b'w==1.0\n').hexdigest()})

    def test_receipt_hash_is_checked_before_the_receipt_is_read(self):
        (self.root/'receipt.json').write_text('deliberately not JSON')
        with self.assertRaisesRegex(ValueError, 'receipt differs'):
            verify_game_environment(self.root, self.pin)

    def test_rewritten_receipt_cannot_cover_a_changed_game(self):
        (self.root/'environment_files/g1/v1/g1.py').write_bytes(b'game = 2\n')
        with self.assertRaisesRegex(ValueError, 'game environment differs'):
            verify_game_environment(self.root, self.pin)
        receipt = json.loads((self.root/'receipt.json').read_bytes())
        receipt['verified_members']['environment_files/g1/v1/g1.py'] = {
            'sha256': hashlib.sha256(b'game = 2\n').hexdigest(), 'bytes': 9}
        (self.root/'receipt.json').write_bytes(json.dumps(receipt).encode())
        with self.assertRaisesRegex(ValueError, 'receipt differs'):
            verify_game_environment(self.root, self.pin)

    def test_unlisted_game_file_or_changed_lock_refuses(self):
        (self.root/'environment_files/g1/v1/extra.py').write_bytes(b'')
        with self.assertRaisesRegex(ValueError, 'inventory differs'):
            verify_game_environment(self.root, self.pin)
        (self.root/'environment_files/g1/v1/extra.py').unlink()
        (self.root/'game_requirements.lock').write_bytes(b'w==2.0\n')
        with self.assertRaisesRegex(ValueError, 'requirements lock differs'):
            verify_game_environment(self.root, self.pin)


if __name__ == '__main__':
    unittest.main()
