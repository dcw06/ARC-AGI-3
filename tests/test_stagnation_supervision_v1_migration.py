"""Stagnation supervision v1 (Track 3): migration onto transition_evidence_v2 (a format change, not an intervention).

The frozen trigger does not move, the detector sees the same evidence, requests are byte-identical wherever available
actions are absent, every record passes v2 validation and verification, and the masked view is never used."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import unittest

from research.stagnation_supervision_v1 import detector as D, fixtures as F, intervention as I, supervision as SV
from research.stagnation_supervision_v1 import thresholds as S
from research.transition_evidence_v1 import transition as T1
from research.transition_evidence_v2 import transition as T2

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'research/stagnation_supervision_v1'
SPEC = S.load()
GENERATED = {p: F.generate(p) for p in ('development', 'evaluation')}
ALL_ON = {'repeat_no_effect': 2, 'state_action_recurrence': 2, 'tiny_effect_repeat': 2, 'novelty_stall': [2, 0],
          'prediction_failures': 1, 'no_progress_horizon': 1}
# sha256 (LF line endings) at 316573d, before the migration. The frozen trigger must stay byte-identical.
FROZEN = {
    'trigger_spec.json': '8dc8d9097d4764a3ecbe5185b3c8ec021d2ab15316e81f0515a67c3d9f6cd7d9',
    'detector.py': 'ee8b340cf69cd092e37508b86152da4b33073bbb9ab5caf833cef6ec6e931d62',
    'thresholds.py': '0a88196a13f74fd3ccb9a89441926ea54b5e3209b9589641b96461ffbfee3985',
    'fixtures.py': '974c66d886551532a9b8bb5f9cbc00c7899b0d8e0cb55d1324a4edec0e2ea1d1',
    'evaluation_results.json': '86d044a838533ff466607504db2adbdf2dc42716e75027c7d0103323b664db88',
}
# Digest of every rehearsal decision (outcome, signals, request sha256, validity, problems, charge, delivered text)
# over all development and evaluation fixtures in the periodic and triggered arms, computed with the v1-record code
# at 316573d. The fixtures retain no available actions, so the migrated code must reproduce it exactly.
PRE_MIGRATION_REHEARSAL = ('618f209ab4d4c3ee8928d2f9b7ed3d1d3e7f98a20a5f48e54bb172fe93eb7282', 3384)
# Review fix (after 463cea3): no reflection at a reset, level change or terminal state. Exactly these 8 of the 3,384
# decisions changed, each at the step whose transition reported a level completion or reset (no fixture reaches a
# terminal state); everything else is byte-identical to the pre-migration rehearsal. The digest is re-pinned.
BOUNDARY_REHEARSAL = ('7eebb858c6e0c096644c4d5fe748133828fbe0dbbaf395846f52788900b18b87', 3384)
# Digest of the 3,376 other rows computed from the pre-fix code; equal to the same rows after the fix.
PRE_MIGRATION_UNCHANGED_ROWS = 'd724e614163eee4005fdc5eeabcbe1d5c1b89d39ed5342a8adb3f02c3949e3b3'
BOUNDARY_CHANGES = {  # (fixture, arm, action index): outcome before the fix
    ('dev-delayed_effect-0', 'triggered', 6): 'suppressed_cooldown',
    ('dev-delayed_effect-2', 'triggered', 7): 'called',
    ('dev-counter_with_static_playfield-1', 'periodic', 5): 'called',
    ('dev-reset_then_replay-0', 'periodic', 5): 'called',
    ('dev-reset_then_replay-2', 'periodic', 5): 'called',
    ('eva-move_to_destination-0', 'periodic', 5): 'called',
    ('eva-delayed_effect-3', 'triggered', 7): 'called',
    ('eva-reset_then_replay-3', 'periodic', 5): 'called',
}
GRID = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
CLICK = {'action_id': 6, 'action_data': {'x': 1, 'y': 1}}


def responder(text):
    content = json.loads(text.split('Evidence:\n', 1)[1])
    shown = [e['action_index'] for e in content['evidence']]
    legal = [a for a in content['available_actions'] if 1 <= a <= 7]
    action = ({'action_id': legal[0], 'action_data': {'x': 0, 'y': 0} if legal[0] == 6 else {}} if legal
              else {'action_id': 1, 'action_data': {}})
    return {'text': json.dumps({'observed_pattern': 'Repeats.', 'evidence_refs': shown[-2:],
                                'assumption_to_reconsider': 'That it responds.',
                                'distinguishing_test': {'description': 'Probe once.', 'actions': [action]}}),
            'input_tokens': 100, 'output_tokens': 50, 'latency_s': 0.5}


def rehearsal_rows():
    rows = []
    for partition in ('development', 'evaluation'):
        for fixture in GENERATED[partition]['fixtures']:
            by_index = {p['action_index']: p for p in fixture['predictions'] or ()}
            for arm in ('periodic', 'triggered'):
                s = SV.Supervisor(arm, SPEC, responder, clock=lambda: 0.0)
                for raw in fixture['raws']:
                    s.observe(raw, by_index.get(raw['identity']['action_index']))
                for e in s.events:
                    call = e.get('call')
                    rows.append([fixture['id'], arm, e['action_index'], e['outcome'],
                                 [x['signal'] for x in e['detector_signals']],
                                 call and call['request_sha256'], call and call['parsed']['valid'],
                                 call and call['parsed']['problems'], call and call['input_tokens'],
                                 e.get('delivered')])
    return rows


def rehearsal_digest(rows=None):
    rows = rehearsal_rows() if rows is None else rows
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest(), len(rows)


def raw(index, before=GRID, after=GRID, action=CLICK, status='acknowledged', actions_before=None, actions_after=None):
    out = {'identity': {'episode_id': 'm', 'action_index': index},
           'before': {'frames': [before], 'levels_completed': 0, 'state': 'NOT_FINISHED', 'full_reset': False},
           'proposal': None, 'dispatched': action, 'environment_source': 'test'}
    if actions_before is not None:
        out['before']['available_actions'] = actions_before
    if status == 'acknowledged':
        out['outcome'] = {'status': status, 'after': {'frames': [after], 'levels_completed': 0,
                                                      'state': 'NOT_FINISHED', 'full_reset': False}}
        if actions_after is not None:
            out['outcome']['after']['available_actions'] = actions_after
    else:
        out['outcome'] = {'status': status, 'reason': 'test'}
    return out


class FrozenTriggerDoesNotMove(unittest.TestCase):
    def test_frozen_files_are_byte_identical(self):
        for name, digest in FROZEN.items():
            data = (PACKAGE / name).read_bytes().replace(b'\r\n', b'\n')
            self.assertEqual(hashlib.sha256(data).hexdigest(), digest, name)

    def test_detector_outputs_are_identical_on_v1_and_v2_records(self):
        for partition, generated in GENERATED.items():
            for fixture in generated['fixtures']:
                v1 = T1.history(fixture['raws'])
                v2 = T2.history(fixture['raws'])
                self.assertEqual([T2.to_v1(r) for r in v2], v1)
                s1, s2 = D.statistics(v1, fixture['predictions']), D.statistics(v2, fixture['predictions'])
                self.assertEqual(s1, s2, fixture['id'])
                for params in (SPEC['params'], ALL_ON):
                    self.assertEqual(D.triggers(s1, params, SPEC['cooldown_actions']),
                                     D.triggers(s2, params, SPEC['cooldown_actions']), fixture['id'])

    def test_held_out_numbers_reproduce_exactly(self):
        from research.stagnation_supervision_v1 import evaluate as E
        frozen = json.loads(E.RESULTS.read_text(encoding='utf-8'))
        self.assertEqual(json.loads(json.dumps(E.report(GENERATED['evaluation'], SPEC))), frozen)
        self.assertEqual(frozen['detectors']['selected']['metrics']['detected_positive_trajectories'], 36)
        self.assertEqual(frozen['detectors']['selected']['metrics']['correct_triggers'], 61)


class RecordsAreValidV2(unittest.TestCase):
    def test_every_fixture_record_validates_and_verifies(self):
        for generated in GENERATED.values():
            for fixture in generated['fixtures']:
                records = T2.history(fixture['raws'])
                for r in records:
                    self.assertEqual(T2.validate(r), [], r['identity']['record_id'])
                self.assertEqual(T2.verify_history(records, fixture['raws']), [], fixture['id'])

    def test_supervisor_records_verify_against_their_raw_evidence(self):
        for fixture in GENERATED['development']['fixtures'][::4]:
            s = SV.Supervisor('triggered', SPEC, responder, clock=lambda: 0.0)
            for r in fixture['raws']:
                s.observe(r)
            self.assertEqual(T2.verify_history(s.records, fixture['raws']), [], fixture['id'])
            self.assertEqual({r['version'] for r in s.records}, {'transition_evidence_v2'})


class RequestsAfterMigration(unittest.TestCase):
    def test_requests_and_results_are_byte_identical_where_available_actions_are_absent(self):
        rows = rehearsal_rows()
        self.assertEqual(rehearsal_digest(rows), BOUNDARY_REHEARSAL)
        boundary = {(r[0], r[1], r[2]) for r in rows if r[3] == 'suppressed_segment_boundary'}
        self.assertEqual(boundary, set(BOUNDARY_CHANGES))
        # every other row is byte-identical to the pre-migration rehearsal (whose full digest is 618f209a...)
        unchanged = [r for r in rows if (r[0], r[1], r[2]) not in BOUNDARY_CHANGES]
        self.assertEqual(len(unchanged), PRE_MIGRATION_REHEARSAL[1] - len(BOUNDARY_CHANGES))
        self.assertEqual(hashlib.sha256(json.dumps(unchanged, sort_keys=True).encode()).hexdigest(),
                         PRE_MIGRATION_UNCHANGED_ROWS)

    def test_absent_available_actions_fall_back_and_say_so(self):
        records = T2.history([raw(i) for i in range(3)])
        self.assertEqual(records[-1]['context']['available_actions_before']['status'], 'absent')
        request = I.build_request(records, 2, 'triggered', [])
        self.assertEqual((request['content']['available_actions'], request['content']['available_actions_source'],
                          request['available_actions_field']), ([6], 'shown_evidence', 'shown_evidence'))
        self.assertEqual(I.build_request(T1.history([raw(i) for i in range(3)]), 2, 'triggered', [])['text'],
                         request['text'])  # a v1 record and an absent v2 field give the same bytes
        caller = I.build_request(records, 2, 'triggered', [], available_actions=[2, 6])
        self.assertEqual((caller['content']['available_actions'], caller['available_actions_field']), ([2, 6], 'caller'))

    def test_reported_available_actions_of_the_current_observation_are_adopted(self):
        """Where records carry available actions, exactly two request values change: `available_actions` becomes
        the reported list of the observation the agent holds, and `available_actions_source` reads 'observation'.
        The prompt, evidence window, frame shape and detector signals are unchanged."""
        raws = [raw(i, actions_before=[0, 1, 6], actions_after=[0, 1, 6]) for i in range(2)]
        raws.append(raw(2, actions_before=[0, 1, 6], actions_after=[0, 2, 3]))
        reported = I.build_request(T2.history(raws), 2, 'triggered', [], available_actions=[1, 6])
        plain = I.build_request(T2.history([raw(i) for i in range(3)]), 2, 'triggered', [])
        self.assertEqual((reported['content']['available_actions'], reported['content']['available_actions_source'],
                          reported['available_actions_field']),
                         ([0, 2, 3], 'observation', 'environment.reported.available_actions_after'))
        changed = {k for k in plain['content'] if plain['content'][k] != reported['content'][k]}
        self.assertEqual(changed, {'available_actions', 'available_actions_source'})
        self.assertEqual(reported['text'].split('Evidence:\n')[0], plain['text'].split('Evidence:\n')[0])
        # validation follows: ACTION6 was shown but is no longer offered; RESET is offered but not choosable
        bad = responder(plain['text'])['text']
        self.assertFalse(I.parse(bad, reported)['valid'])
        good = json.dumps({**json.loads(bad), 'distinguishing_test': {
            'description': 'Probe once.', 'actions': [{'action_id': 2, 'action_data': {}}]}})
        self.assertTrue(I.parse(good, reported)['valid'])
        reset = json.dumps({**json.loads(bad), 'distinguishing_test': {
            'description': 'Probe once.', 'actions': [{'action_id': 0, 'action_data': {}}]}})
        self.assertFalse(I.parse(reset, reported)['valid'])

    def test_after_a_failed_dispatch_the_pre_action_observation_still_holds(self):
        raws = [raw(0, actions_before=[1, 6], actions_after=[1, 6]),
                raw(1, status='failed', actions_before=[1, 6])]
        request = I.build_request(T2.history(raws), 1, 'periodic', [])
        self.assertEqual((request['content']['available_actions'], request['available_actions_field']),
                         ([1, 6], 'context.available_actions_before'))

    def test_evidence_is_referenced_by_record_id_internally(self):
        s = SV.Supervisor('triggered', SPEC, responder, clock=lambda: 0.0)
        for r in [raw(i) for i in range(3)]:
            s.observe(r)
        called = [e for e in s.events if e['outcome'] == 'called'][0]
        self.assertEqual(called['record_id'], 'm#1')
        self.assertEqual(called['detector_evidence_record_ids'], ['m#0', 'm#1'])
        self.assertEqual(called['call']['parsed']['evidence_record_ids'], ['m#0', 'm#1'])
        self.assertNotIn('m#', called['call']['request_text'])  # the prompt still cites action indices only


class NoMaskedView(unittest.TestCase):
    def test_track_code_never_touches_the_masked_view_or_the_masks_module(self):
        for path in sorted(PACKAGE.glob('*.py')):
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [a.name for a in node.names] + [getattr(node, 'module', None) or '']
                    self.assertFalse(any('mask' in n for n in names), path.name)
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    self.assertNotIn(node.value, ('masked', 'masks', 'mask'), path.name)
                if isinstance(node, ast.Attribute):
                    self.assertNotIn('mask', node.attr.lower(), path.name)
                if isinstance(node, ast.Name):
                    self.assertNotIn('mask', node.id.lower(), path.name)
                if isinstance(node, ast.keyword) and node.arg:
                    self.assertNotIn('mask', node.arg.lower(), path.name)

    def test_supervisor_records_carry_no_masked_measurements(self):
        s = SV.Supervisor('triggered', SPEC, responder, clock=lambda: 0.0)
        for r in GENERATED['development']['fixtures'][0]['raws']:
            s.observe(r)
        self.assertEqual({json.dumps(r['masked'], sort_keys=True) for r in s.records},
                         {json.dumps({'status': 'unavailable', 'reason': 'no mask was supplied'}, sort_keys=True)})

    def test_detector_is_blind_to_the_masked_view(self):
        fixture = GENERATED['development']['fixtures'][0]
        records = T2.history(fixture['raws'])
        poisoned = copy.deepcopy(records)
        for r in poisoned:
            r['masked'] = {'status': 'measured', 'visual_effect_outside': {'status': 'no_observed_change'}}
        self.assertEqual(D.statistics(records), D.statistics(poisoned))


if __name__ == '__main__':
    unittest.main()
