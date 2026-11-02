"""Synthetic demonstration-imitation contracts; no engine, model or private log.

The fixture has three visible transitions and three engine-counter increments.
Pixels, legal controls and counters all matter: a valid action sequence alone
must never authorize dispatch after observation drift.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research.initial_geometry_assistance_v1.geometry import digest
from research.ls20_overfit_v1.policy import OverfitPolicy, compile_demo


GAME = 'ls20-9607627b'


def raw_observation(step=0):
    grid = [[3] * 64 for _ in range(64)]
    grid[0][0] = step
    # Interface pixels are part of the observation gate, too.
    grid[63][63] = 11 - step
    return dict(game_id=GAME, state='NOT_FINISHED', levels_completed=step,
                win_levels=7, available_actions=[1, 2, 3, 4], frames=[grid],
                canonical_hash=f'{step:064x}')


def native(raw):
    # Independent fixture projection, rather than the production normalizer.
    return dict(grid=deepcopy(raw['frames'][-1]),
                legal_actions=sorted(raw['available_actions']),
                state=raw['state'], levels_completed=raw['levels_completed'])


def demo_rows():
    initial = raw_observation()
    rows = [dict(type='session_start', schema='public_game_manual_v1',
                 session='synthetic-owner-demo', actor='human_manual', game_id=GAME,
                 seed=0, utc='2026-11-02T12:00:00+00:00',
                 source='offline_public_development_engine',
                 exposure='synthetic fixture, not a real demonstration',
                 sdk_versions={'arc-agi': '0.9.9', 'arcengine': '0.9.3'},
                 initial_observation=initial)]
    for step, action_id in enumerate((3, 1, 4), start=1):
        rows.extend([
            dict(type='action_entered', sequence=step, utc=f'2026-11-02T12:00:{step:02d}+00:00',
                 request_id=f'fixture-{step}',
                 action={'action_id': action_id, 'action_data': {}},
                 before=raw_observation(step - 1)),
            dict(type='action_acknowledged', sequence=step, utc=f'2026-11-02T12:00:{step:02d}.010000+00:00',
                 request_id=f'fixture-{step}', seconds=0.01,
                 after=raw_observation(step)),
        ])
    return rows


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'synthetic.manual.jsonl'

    def compile(self, rows=None, *, expected_sha256=None):
        rows = demo_rows() if rows is None else rows
        payload = ''.join(json.dumps(row, sort_keys=True) + '\n' for row in rows).encode()
        self.path.write_bytes(payload)
        sha = hashlib.sha256(payload).hexdigest()
        return compile_demo(self.path, expected_sha256 or sha)


class Compiler(Fixture):
    def test_three_level_counter_completion_and_exact_observation_gates(self):
        program = self.compile()
        self.assertEqual(program['game_id'], GAME)
        self.assertEqual(program['seed'], 0)
        self.assertEqual(program['goal_levels'], 3)
        self.assertEqual(program['source_demo_sha256'], hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(program['initial_observation'], native(raw_observation()))
        self.assertEqual([row['index'] for row in program['steps']], [0, 1, 2])
        self.assertEqual([row['action'] for row in program['steps']],
                         [{'action_id': n, 'action_data': {}} for n in (3, 1, 4)])
        for step, row in enumerate(program['steps']):
            self.assertEqual(row['before_sha256'], digest(native(raw_observation(step))))
            self.assertEqual(row['after_sha256'], digest(native(raw_observation(step + 1))))
            self.assertEqual((row['before_levels'], row['after_levels']), (step, step + 1))
        self.assertEqual(program['level_boundaries'],
                         [{'level': n, 'after_moves': n, 'moves': 1} for n in (1, 2, 3)])

    def test_stops_compiling_at_goal_and_does_not_import_later_reset(self):
        rows = demo_rows()
        rows.extend([
            dict(type='action_entered', sequence=4, request_id='later-reset', utc='2026-11-02T12:00:04+00:00',
                 action={'action_id': 0, 'action_data': {}}, before=raw_observation(3)),
            dict(type='action_acknowledged', sequence=4, request_id='later-reset', utc='2026-11-02T12:00:04.010000+00:00',
                 seconds=0.01, after=raw_observation()),
        ])
        self.assertEqual(len(self.compile(rows)['steps']), 3)

    def test_source_bytes_must_match_trusted_hash(self):
        with self.assertRaises(ValueError):
            self.compile(expected_sha256='f' * 64)

    def test_demo_identity_and_initial_counter_are_fixed(self):
        mutations = [
            lambda r: r[0].update(actor='agent'),
            lambda r: r[0].update(game_id='ka59-other'),
            lambda r: r[0].update(seed=1),
            lambda r: r[0].update(seed=True),
            lambda r: r[0]['initial_observation'].update(levels_completed=1),
            lambda r: r[0]['initial_observation'].update(game_id='ls20-other'),
        ]
        for mutate in mutations:
            rows = demo_rows()
            mutate(rows)
            with self.subTest(mutation=mutations.index(mutate)), self.assertRaises(ValueError):
                self.compile(rows)

    def test_unacknowledged_action_and_missing_goal_refuse(self):
        for rows in (demo_rows()[:-1], demo_rows()[:-2], demo_rows()[:1]):
            with self.subTest(length=len(rows)), self.assertRaises(ValueError):
                self.compile(rows)

    def test_pairing_sequence_and_before_chain_are_independently_checked(self):
        mutations = [
            lambda r: r[2].update(request_id='different-request'),
            lambda r: r[2].update(sequence=2),
            lambda r: r[1].update(sequence=True),
            lambda r: r[2].update(type='action_entered'),
            lambda r: r[3]['before']['frames'][-1][8].__setitem__(8, 7),
        ]
        for mutate in mutations:
            rows = demo_rows()
            mutate(rows)
            with self.subTest(mutation=mutations.index(mutate)), self.assertRaises(ValueError):
                self.compile(rows)

    def test_reset_click_illegal_and_noninteger_actions_refuse(self):
        for action in ({'action_id': n, 'action_data': {}} for n in (0, 6, 7, True, 1.0)):
            rows = demo_rows()
            rows[1]['action'] = action
            with self.subTest(action=action), self.assertRaises(ValueError):
                self.compile(rows)
        rows = demo_rows()
        rows[1]['action']['action_data'] = {'x': 2}
        with self.assertRaises(ValueError):
            self.compile(rows)

    def test_legal_controls_must_authorize_recorded_action(self):
        rows = demo_rows()
        rows[0]['initial_observation']['available_actions'] = [1, 2, 4]
        rows[1]['before'] = deepcopy(rows[0]['initial_observation'])
        with self.assertRaises(ValueError):
            self.compile(rows)

    def test_counter_jump_or_terminal_before_goal_cannot_fake_completion(self):
        for field, value in (('levels_completed', 3), ('levels_completed', True),
                             ('state', 'WIN'), ('state', 'GAME_OVER')):
            rows = demo_rows()
            rows[2]['after'][field] = value
            rows[3]['before'] = deepcopy(rows[2]['after'])
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.compile(rows)

    def test_duplicate_json_fields_and_nonfinite_duration_refuse(self):
        # Authenticate the changed bytes so rejection tests parsing, not SHA mismatch.
        self.compile()
        text = self.path.read_text()
        for changed in (text.replace('"seed": 0', '"seed": 0, "seed": 0', 1),
                        text.replace('"seconds": 0.01', '"seconds": NaN', 1)):
            self.path.write_bytes(changed.encode())
            sha = hashlib.sha256(changed.encode()).hexdigest()
            with self.subTest(nonfinite='NaN' in changed), self.assertRaises(ValueError):
                compile_demo(self.path, sha)


class Policy(Fixture):
    def test_tampered_program_hash_chain_and_completion_boundaries_refuse(self):
        mutations = [
            lambda p: p['steps'][0].update(before_sha256='a' * 64),
            lambda p: p['steps'][1].update(before_sha256='b' * 64),
            lambda p: p['steps'][0].update(after_levels=3),
            lambda p: p['steps'][-1].update(after_levels=2),
            lambda p: p['level_boundaries'][0].update(level=True),
            lambda p: p['level_boundaries'][1].update(after_moves=3),
            lambda p: p.update(seed=True),
        ]
        program = self.compile()
        for mutate in mutations:
            changed = deepcopy(program)
            mutate(changed)
            with self.subTest(case=mutations.index(mutate)), self.assertRaises(ValueError):
                OverfitPolicy(changed)

    def test_select_does_not_advance_and_acknowledgement_is_required(self):
        policy = OverfitPolicy(self.compile())
        self.assertEqual(policy.cursor, 0)
        self.assertFalse(policy.completed)
        action = policy.select(GAME, native(raw_observation()))
        self.assertEqual(action, {'action_id': 3, 'action_data': {}})
        self.assertEqual(policy.cursor, 0)
        with self.assertRaises(ValueError):
            policy.select(GAME, native(raw_observation()))
        # A duplicate select is refused without erasing the valid pending action.
        policy.acknowledge(action, native(raw_observation(1)))
        self.assertEqual(policy.cursor, 1)

    def test_success_requires_three_verified_counter_increments(self):
        policy = OverfitPolicy(self.compile())
        for step, expected in enumerate((3, 1, 4)):
            self.assertFalse(policy.completed)
            action = policy.select(GAME, native(raw_observation(step)))
            self.assertEqual(action['action_id'], expected)
            policy.acknowledge(action, native(raw_observation(step + 1)))
        self.assertTrue(policy.completed)
        self.assertEqual(policy.cursor, 3)
        with self.assertRaises(StopIteration):
            policy.select(GAME, native(raw_observation(3)))

    def test_wrong_game_or_any_observation_drift_permanently_quarantines(self):
        changes = [
            lambda o: o['grid'][4].__setitem__(5, 8),
            lambda o: o['grid'][63].__setitem__(63, 7),
            lambda o: o.update(legal_actions=[1, 2, 4]),
            lambda o: o.update(levels_completed=1),
            lambda o: o.update(levels_completed=False),
            lambda o: o.update(state='GAME_OVER'),
        ]
        cases = [(GAME, mutate) for mutate in changes] + [('ls20-other', lambda o: None)]
        for game, mutate in cases:
            policy = OverfitPolicy(self.compile())
            obs = native(raw_observation())
            mutate(obs)
            with self.subTest(game=game, case=cases.index((game, mutate))):
                with self.assertRaises(ValueError):
                    policy.select(game, obs)
                self.assertEqual(policy.cursor, 0)
                with self.assertRaises(ValueError):
                    policy.select(GAME, native(raw_observation()))

    def test_wrong_ack_action_pixel_or_counter_never_advances_and_quarantines(self):
        changes = [
            lambda a, o: a.update(action_id=4),
            lambda a, o: a.update(action_id=True),
            lambda a, o: a.update(action_data={'x': 1}),
            lambda a, o: o['grid'][4].__setitem__(5, 8),
            lambda a, o: o.update(levels_completed=2),
            lambda a, o: o.update(levels_completed=True),
            lambda a, o: o.update(legal_actions=[1, 2, 3]),
        ]
        for mutate in changes:
            policy = OverfitPolicy(self.compile())
            action = policy.select(GAME, native(raw_observation()))
            after = native(raw_observation(1))
            mutate(action, after)
            with self.subTest(case=changes.index(mutate)), self.assertRaises(ValueError):
                policy.acknowledge(action, after)
            self.assertEqual(policy.cursor, 0)
            self.assertFalse(policy.completed)
            with self.assertRaises(ValueError):
                policy.select(GAME, native(raw_observation()))

    def test_unrequested_and_duplicate_acknowledgements_refuse(self):
        action = {'action_id': 3, 'action_data': {}}
        policy = OverfitPolicy(self.compile())
        with self.assertRaises(ValueError):
            policy.acknowledge(action, native(raw_observation(1)))
        policy = OverfitPolicy(self.compile())
        policy.acknowledge(policy.select(GAME, native(raw_observation())), native(raw_observation(1)))
        with self.assertRaises(ValueError):
            policy.acknowledge(action, native(raw_observation(1)))
        self.assertEqual(policy.cursor, 1)

    def test_returned_action_and_constructor_input_do_not_mutate_owned_program(self):
        program = self.compile()
        policy = OverfitPolicy(program)
        program['steps'][0]['action']['action_id'] = 4
        action = policy.select(GAME, native(raw_observation()))
        self.assertEqual(action['action_id'], 3)
        action['action_id'] = 2
        policy.acknowledge({'action_id': 3, 'action_data': {}}, native(raw_observation(1)))
        self.assertEqual(policy.cursor, 1)


if __name__ == '__main__':
    unittest.main()
