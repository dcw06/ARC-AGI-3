import copy
import json
from pathlib import Path
import tempfile
import unittest

from research.ls20_discovery_mac import EvidenceMemory, extract_scene
from research.ls20_discovery_mac.memory import digest


def obs(grid, **extra):
    return dict(grid=grid, state='NOT_FINISHED', levels_completed=0, legal_actions=[1, 2, 3, 4], **extra)


def action(n=1):
    return dict(action_id=n, action_data={})


def step(memory, grid, n=1):
    return memory.append(action(n), dict(status='acknowledged', post=obs(grid)))


class SceneTests(unittest.TestCase):
    def test_independent_masks_bbox_holes_and_relations(self):
        s = extract_scene([[7, 7, 7], [7, 3, 7], [7, 7, 7]], 'o0')
        ring, center = s['regions']
        self.assertEqual(ring['cells'], [[0, 0], [0, 1], [0, 2], [1, 0], [1, 2], [2, 0], [2, 1], [2, 2]])
        self.assertEqual(ring['bbox'], [0, 0, 2, 2])
        self.assertEqual(ring['crop'][1], [7, 3, 7])
        self.assertEqual(center['shape'], [[0, 0]])
        self.assertEqual(s['relations'], [{'kind': 'boundary_adjacent', 'regions': ['o0:r0', 'o0:r1']}])

    def test_diagonal_is_not_confirmed_group(self):
        scene = extract_scene([[4, 2], [2, 4]], 'o0')
        self.assertEqual(len(scene['regions']), 4)
        self.assertTrue(all(r['kind'] == 'computed_region_proposal' for r in scene['regions']))

    def test_every_palette_value_including_zero_retained(self):
        self.assertEqual({r['color'] for r in extract_scene([list(range(16))], 'o')['regions']}, set(range(16)))

    def test_palette_permutation_does_not_change_geometry(self):
        grid = [[0, 2, 0], [0, 2, 3]]
        first = extract_scene(grid, 'o')
        second = extract_scene([[15-x for x in row] for row in grid], 'o')
        for a, b in zip(first['regions'], second['regions']):
            self.assertEqual(a['cells'], b['cells'])
            self.assertEqual(a['id'], b['id'])
            self.assertEqual(a['shape'], b['shape'])
        self.assertEqual(first['relations'], second['relations'])

    def test_malformed_grids_rejected(self):
        for grid in ([], [[]], [[1], [1, 2]], [[True]], [[16]], [[-1]]):
            with self.subTest(grid=grid), self.assertRaises(ValueError):
                extract_scene(grid, 'o')


class MemoryTests(unittest.TestCase):
    def test_palette_permutation_preserves_tracking_and_hypotheses(self):
        grids = [[[2, 0, 2]], [[2, 2, 2]], [[0, 2, 0]]]
        memories = []
        for permute in (lambda x: x, lambda x: 15-x):
            transformed = [[[permute(v) for v in row] for row in g] for g in grids]
            m = EvidenceMemory('e', obs(transformed[0]))
            for g in transformed[1:]:
                step(m, g)
            memories.append(m.snapshot())
        self.assertEqual(memories[0]['identity_candidates'], memories[1]['identity_candidates'])
        self.assertEqual(memories[0]['hypotheses'], memories[1]['hypotheses'])

    def test_recoloring_is_explicit_association_failure(self):
        m = EvidenceMemory('e', obs([[2, 0, 0]]))
        step(m, [[7, 0, 0]])
        # Evaluator says the entity recolored. The heuristic cannot establish its identity.
        self.assertFalse(any(x['before'] == 'o0:r0' and x['after'] == 'o1:r0'
                             for x in m.snapshot()['identity_candidates']))
        self.assertEqual(m.snapshot()['events'][0]['changes'], [[0, 0, 2, 7]])

    def test_partial_occlusion_retains_overlap_without_exact_shape(self):
        m = EvidenceMemory('e', obs([[2, 2, 2]]))
        step(m, [[2, 7, 2]])
        links = m.snapshot()['identity_candidates']
        self.assertEqual({x['after'] for x in links}, {'o1:r0', 'o1:r2'})
        self.assertTrue(all(x['overlap'] and not x['same_shape'] for x in links))

    def test_schema_covers_unknown_failed_multiframe_and_conflicts(self):
        from jsonschema import Draft202012Validator
        schema = json.loads((Path(__file__).parents[1] / 'research/ls20_discovery_mac/schema.json').read_text())
        validator = Draft202012Validator(schema)
        m = EvidenceMemory('e', obs([[0]]))
        m.append(action(), dict(status='dispatch_failed', error='not sent'))
        step(m, [[1]])
        step(m, [[0]], 2)
        step(m, [[2]])
        m.append(action(), dict(status='outcome_unknown', reason='response lost'))
        validator.validate(m.snapshot())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'memory.json'
            m.save(path)
            self.assertTrue(EvidenceMemory.load(path).snapshot()['suspended'])

    def test_relocation_is_possible_identity_not_proven_control(self):
        m = EvidenceMemory('episode', obs([[2, 0, 0, 0]]))
        step(m, [[0, 0, 0, 2]])
        s = m.snapshot()
        link = next(x for x in s['identity_candidates'] if x['before'] == 'o0:r0')
        self.assertEqual(link['translation'], [0, 3])
        self.assertEqual(link['status'], 'unresolved')
        self.assertIn('different_entities', link['alternatives'])
        self.assertTrue(all(h['status'] == 'tentative' for h in s['hypotheses']))
        self.assertEqual(s['events'][0]['changes'], [[0, 0, 2, 0], [0, 3, 0, 2]])

    def test_repeated_appearance_keeps_both_predecessors(self):
        m = EvidenceMemory('e', obs([[2, 0, 2]]))
        step(m, [[0, 2, 0]])
        links = [x for x in m.snapshot()['identity_candidates'] if x['after'] == 'o1:r1']
        self.assertEqual({x['before'] for x in links}, {'o0:r0', 'o0:r2'})

    def test_merge_and_split_do_not_destroy_earlier_proposals(self):
        m = EvidenceMemory('e', obs([[2, 0, 2]]))
        step(m, [[2, 2, 2]])
        step(m, [[2, 0, 2]])
        s = m.snapshot()
        merges = [x for x in s['identity_candidates'] if x['after'] == 'o1:r0']
        self.assertEqual({x['before'] for x in merges}, {'o0:r0', 'o0:r2'})
        splits = [x for x in s['identity_candidates'] if x['before'] == 'o1:r0']
        self.assertEqual({x['after'] for x in splits}, {'o2:r0', 'o2:r2'})

    def test_full_occlusion_and_reappearance_preserve_alternative(self):
        m = EvidenceMemory('e', obs([[2, 0, 0]]))
        step(m, [[0, 0, 0]])
        step(m, [[0, 0, 2]])
        self.assertTrue(any(x['before'] == 'o0:r0' and x['after'] == 'o2:r1'
                            for x in m.snapshot()['identity_candidates']))
        self.assertEqual([x['color'] for x in m.cell_history(0, 0)], [2, 0, 0])

    def test_observed_terrain_history_never_replaced_by_assumed_floor(self):
        m = EvidenceMemory('e', obs([[6, 2]]))
        step(m, [[2, 8]])
        step(m, [[6, 2]])
        self.assertEqual([x['color'] for x in m.cell_history(0, 1)], [2, 8, 2])
        self.assertEqual(m.snapshot()['observations'][1]['grid'], [[2, 8]])

    def test_transient_change_is_not_noop(self):
        m = EvidenceMemory('e', obs([[0, 2]]))
        post = obs([[0, 2]])
        del post['grid']
        post['frames'] = [[[2, 0]], [[0, 2]]]
        t = m.append(action(), dict(status='acknowledged', post=post))
        self.assertTrue(t['effect']['any_frame_changed'])
        self.assertTrue(t['effect']['returned_to_pre_frame'])
        self.assertEqual(len(m.snapshot()['events']), 2)

    def test_unchanged_frame_does_not_assert_blocked_edge(self):
        m = EvidenceMemory('e', obs([[0, 2]]))
        t = step(m, [[0, 2]])
        self.assertFalse(t['effect']['any_frame_changed'])
        self.assertEqual(m.snapshot()['events'][0]['changes'], [])
        self.assertEqual(m.snapshot()['hypotheses'], [])

    def test_identical_static_marks_give_no_control_hint(self):
        m = EvidenceMemory('e', obs([[2, 0, 2]]))
        step(m, [[2, 0, 2]])
        self.assertEqual(m.snapshot()['events'][0]['changes'], [])
        self.assertEqual(m.snapshot()['hypotheses'], [])

    def test_only_the_moved_copy_receives_a_control_hint(self):
        # A static mark at column 0 and an identical mark moving from column 2 to 4.
        m = EvidenceMemory('e', obs([[2, 0, 2, 0, 0]]))
        step(m, [[2, 0, 0, 0, 2]])
        hints = m.snapshot()['hypotheses']
        self.assertEqual([h['proposal_id'] for h in hints], ['o1:r2'])
        link = next(x for x in m.snapshot()['identity_candidates']
                    if x['before'] == 'o0:r2' and x['after'] == 'o1:r2')
        self.assertEqual(link['translation'], [0, 2])

    def test_newly_appearing_copy_is_not_a_moved_entity(self):
        m = EvidenceMemory('e', obs([[2, 0, 0]]))
        step(m, [[2, 0, 2]])
        self.assertTrue(any(x['before'] == 'o0:r0' and x['after'] == 'o1:r2'
                            for x in m.snapshot()['identity_candidates']))
        self.assertEqual(m.snapshot()['hypotheses'], [])

    def test_continuously_visible_region_links_only_to_previous_frame(self):
        m = EvidenceMemory('e', obs([[2]]))
        for _ in range(5):
            step(m, [[2]])
        links = m.snapshot()['identity_candidates']
        self.assertEqual([(x['before'], x['after']) for x in links],
                         [(f'o{i}:r0', f'o{i+1}:r0') for i in range(5)])

    def test_reappearance_after_long_occlusion_links_to_last_sighting(self):
        m = EvidenceMemory('e', obs([[2, 0, 0]]))
        for _ in range(3):
            step(m, [[0, 0, 0]])
        step(m, [[0, 0, 2]])
        links = [x for x in m.snapshot()['identity_candidates'] if x['after'] == 'o4:r1']
        self.assertEqual([(x['before'], x['translation']) for x in links], [('o0:r0', [0, 2])])

    def test_failed_dispatch_retained_but_not_noop(self):
        m = EvidenceMemory('e', obs([[0]]))
        t = m.append(action(), dict(status='dispatch_failed', error='rejected before delivery'))
        self.assertIsNone(t['effect']['any_frame_changed'])
        self.assertIsNone(t['after_observation_id'])
        self.assertEqual(len(m.snapshot()['observations']), 1)
        step(m, [[1]])

    def test_unknown_outcome_suspends_further_actions(self):
        m = EvidenceMemory('e', obs([[0]]))
        m.append(action(), dict(status='outcome_unknown', reason='response lost'))
        with self.assertRaises(ValueError):
            step(m, [[1]])

    def test_same_visible_state_action_conflicting_outcomes_survive(self):
        m = EvidenceMemory('e', obs([[0]]))
        step(m, [[1]], 1)
        step(m, [[0]], 2)
        step(m, [[2]], 1)
        events = [e for e in m.snapshot()['events'] if e['kind'] == 'context_dependent_outcome']
        self.assertEqual(events[0]['conflicting_transition_ids'], ['t0'])
        self.assertEqual(events[0]['transition_id'], 't2')

    def test_new_level_does_not_transfer_geometry(self):
        m = EvidenceMemory('e', obs([[2, 0]]))
        post = obs([[0, 2]])
        post['levels_completed'] = 1
        m.append(action(), dict(status='acknowledged', post=post))
        self.assertEqual(m.snapshot()['identity_candidates'], [])
        self.assertEqual(m.snapshot()['observations'][-1]['segment'], 1)
        self.assertEqual(len(m.cell_history(0, 0)), 2)

    def test_shape_change_is_not_pixel_delta_or_identity(self):
        m = EvidenceMemory('e', obs([[2, 0]]))
        step(m, [[2], [0]])
        self.assertIsNone(m.snapshot()['events'][0]['changes'])
        self.assertEqual(m.snapshot()['identity_candidates'], [])

    def test_defensive_copies(self):
        initial = obs([[0]])
        m = EvidenceMemory('e', initial)
        initial['grid'][0][0] = 4
        t = step(m, [[1]])
        t['outcome']['post']['frames'][0][0][0] = 7
        s = m.snapshot()
        s['observations'][0]['grid'][0][0] = 8
        self.assertEqual([x['color'] for x in m.cell_history(0, 0)], [0, 1])

    def test_invalid_append_is_atomic(self):
        m = EvidenceMemory('e', obs([[0]]))
        original = m.snapshot()
        for act, outcome in [(action(7), dict(status='acknowledged', post=obs([[1]]))),
                             (action(), dict(status='acknowledged', post=obs([[True]]))),
                             (action(), dict(status='dispatch_failed', error=''))]:
            with self.assertRaises(ValueError):
                m.append(act, outcome)
            self.assertEqual(m.snapshot(), original)

    def test_disk_roundtrip_and_forged_derived_evidence_rejected(self):
        m = EvidenceMemory('e', obs([[2, 0]]))
        step(m, [[0, 2]])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'memory.json'
            m.save(path)
            self.assertEqual(EvidenceMemory.load(path).snapshot(), m.snapshot())
            raw = json.loads(path.read_text())
            raw['payload']['events'][0]['changes'] = []
            raw['sha256'] = digest(raw['payload'])
            path.write_text(json.dumps(raw))
            with self.assertRaisesRegex(ValueError, 'reconstruct'):
                EvidenceMemory.load(path)

    def test_hidden_mode_old_cue_survives_identical_recent_frames(self):
        # Evaluator owns the rule: initial cue 4 requires action 1, cue 7 action 2.
        # This is an information-retention test, not an agent learning that rule.
        memories = []
        for cue in (4, 7):
            m = EvidenceMemory('e', obs([[cue]]))
            for _ in range(5):
                step(m, [[0]])
            memories.append(m)
        views = [m.snapshot() for m in memories]
        self.assertEqual([o['grid'] for o in views[0]['observations'][-2:]],
                         [o['grid'] for o in views[1]['observations'][-2:]])
        self.assertEqual(views[0]['scenes'][-1], views[1]['scenes'][-1])
        self.assertEqual([m.cell_history(0, 0)[0]['color'] for m in memories], [4, 7])
        evaluator_rule = {4: 1, 7: 2}
        self.assertEqual([evaluator_rule[m.cell_history(0, 0)[0]['color']] for m in memories], [1, 2])

    def test_schema_validates_and_rejects_missing_provenance(self):
        from jsonschema import Draft202012Validator
        schema = json.loads((Path(__file__).parents[1] / 'research/ls20_discovery_mac/schema.json').read_text())
        validator = Draft202012Validator(schema)
        m = EvidenceMemory('e', obs([[2, 0]]))
        step(m, [[0, 2]])
        payload = m.snapshot()
        validator.validate(payload)
        del payload['transitions'][0]['before_sha256']
        self.assertTrue(list(validator.iter_errors(payload)))


if __name__ == '__main__':
    unittest.main()
