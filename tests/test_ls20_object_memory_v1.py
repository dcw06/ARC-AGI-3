"""Visible-only object identity, encounter receipts and level-local novelty."""
from copy import deepcopy
import json
import unittest

from research.initial_geometry_assistance_v1.geometry import digest
from research.ls20_object_memory_v1.objects import discover
from research.ls20_object_memory_v1.memory import EncounterMemory
from tests.test_ls20_pattern_recognition_v1 import board, ASYMMETRIC, panel, rotate


def objects_board():
    grid, _, _ = board()
    # Two visually identical bounded yellow rings, each with an empty hole.
    for left, top in ((18, 20), (38, 30)):
        for y in range(top, top+5):
            for x in range(left, left+5):
                grid[y][x] = 11 if x in (left, left+4) or y in (top, top+4) else 3
    return grid


class ObjectMemory(unittest.TestCase):
    def test_identical_instances_keep_distinct_ids_and_shared_appearance(self):
        objs = discover(objects_board(), 3)
        rings = [obj for obj in objs if obj['kind'] == 'unknown']
        self.assertEqual(len(rings), 2)
        self.assertNotEqual(rings[0]['id'], rings[1]['id'])
        self.assertEqual(rings[0]['appearance_sha256'], rings[1]['appearance_sha256'])
        self.assertEqual(len(rings[0]['cells']), 16)
        self.assertNotIn(rings[0]['center'], rings[0]['cells'])

    def test_panels_keep_whole_glyphs_and_reference_is_not_navigation_target(self):
        objs = discover(objects_board(), 3)
        panels = {obj['kind']: obj for obj in objs if obj['kind'] in ('reference', 'destination')}
        self.assertFalse(panels['reference']['targetability'])
        self.assertTrue(panels['destination']['targetability'])
        self.assertEqual(panels['reference']['center'], [8.5, 46.5])
        self.assertEqual(len(panels['reference']['cells']), 100)

    def test_whole_reference_panel_may_extend_into_bottom_interface_rows(self):
        grid = [[3]*64 for _ in range(64)]
        panel(grid, ASYMMETRIC, left=1, top=53, scale=2, margin=2)
        panel(grid, rotate(ASYMMETRIC), left=33, top=9, margin=2)
        objects = discover(grid, 3)
        reference = next(obj for obj in objects if obj['kind'] == 'reference')
        self.assertEqual(reference['bbox'], [1, 53, 10, 62])
        self.assertEqual(len(reference['cells']), 100)
        self.assertFalse(reference['targetability'])
        memory = EncounterMemory()
        memory.observe('level:0', objects, digest(grid))
        self.assertEqual(EncounterMemory.from_snapshot(memory.snapshot()).snapshot(), memory.snapshot())
        self.assertNotIn(reference['id'], [obj['id'] for obj in memory.priorities('level:0')])
        bad = deepcopy(reference)
        bad['targetability'] = True
        with self.assertRaises(ValueError): memory.observe('level:0', [bad], digest(grid))

    def test_touching_multicolor_marks_group_and_interface_is_excluded(self):
        grid = [[3]*64 for _ in range(64)]
        grid[10][10], grid[10][11], grid[11][11] = 8, 9, 11
        grid[60][10] = 8
        objects = discover(grid, 3)
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]['cells'], [[10, 10], [11, 10], [11, 11]])

    def test_cross_and_player_are_not_unknown_fragments(self):
        from tests.test_ls20_pattern_goal_v1 import make_observation
        objects = discover(make_observation()['grid'], 3)
        self.assertEqual(sorted(obj['kind'] for obj in objects), ['cross', 'destination', 'reference'])

    def test_bad_grid_and_bool_floor_are_rejected(self):
        with self.assertRaises(ValueError): discover([], 3)
        with self.assertRaises(ValueError): discover(objects_board(), True)

    def make_memory(self):
        objects = discover(objects_board(), 3)
        memory = EncounterMemory()
        memory.observe('level:0', objects, digest('initial'))
        return memory, objects

    def test_visibility_does_not_encounter_and_absence_preserves_identity(self):
        memory, objects = self.make_memory()
        self.assertTrue(all(obj['encounter_count'] == 0 for obj in memory.objects('level:0')))
        memory.observe('level:0', [], digest('occluded'))
        self.assertEqual(len(memory.objects('level:0')), len(objects))
        self.assertTrue(all(not obj['visible'] for obj in memory.objects('level:0')))
        self.assertEqual(memory.events, [])

    def test_encounter_is_receipt_bound_not_duplicated_until_release(self):
        memory, objects = self.make_memory()
        obj = next(obj for obj in objects if obj['kind'] == 'unknown')
        before, after = digest('before'), digest('after')
        effect = {'changed_cells': [[1, 2]]}
        event = memory.record_encounter('level:0', obj['id'], before, after, pattern_changes=effect)
        effect['changed_cells'].append([3, 4])
        self.assertEqual(event['pattern_changes'], {'changed_cells': [[1, 2]]})
        self.assertEqual(event['before_sha256'], before)
        self.assertEqual(event['after_sha256'], after)
        self.assertIsNone(memory.record_encounter('level:0', obj['id'], before, after))
        memory.release('level:0', obj['id'])
        memory.record_encounter('level:0', obj['id'], before, after, floor_changes={'3': '8'})
        self.assertEqual(len(memory.events), 2)

    def test_same_appearance_new_instance_and_new_level_are_novel(self):
        memory, objects = self.make_memory()
        rings = [obj for obj in objects if obj['kind'] == 'unknown']
        memory.record_encounter('level:0', rings[0]['id'], digest('a'), digest('b'))
        self.assertEqual(next(obj for obj in memory.objects('level:0') if obj['id'] == rings[1]['id'])['encounter_count'], 0)
        memory.observe('level:1', objects, digest('next level'))
        self.assertTrue(all(obj['encounter_count'] == 0 for obj in memory.objects('level:1')))
        self.assertEqual(memory.knowledge[rings[0]['appearance_sha256']]['encounters'], 1)

    def test_priorities_put_unvisited_instances_before_visited_even_same_appearance(self):
        memory, objects = self.make_memory()
        rings = [obj for obj in objects if obj['kind'] == 'unknown']
        memory.record_encounter('level:0', rings[0]['id'], digest('a'), digest('b'))
        priorities = memory.priorities('level:0', rings)
        self.assertEqual([obj['id'] for obj in priorities], [rings[1]['id'], rings[0]['id']])
        self.assertFalse(any(obj['kind'] == 'reference' for obj in memory.priorities('level:0')))

    def test_updated_appearance_at_same_bounds_does_not_create_novel_instance(self):
        memory, objects = self.make_memory()
        ring = next(obj for obj in objects if obj['kind'] == 'unknown')
        memory.record_encounter('level:0', ring['id'], digest('a'), digest('b'))
        changed = deepcopy(objects)
        next(obj for obj in changed if obj['id'] == ring['id'])['appearance_sha256'] = digest('changed')
        memory.observe('level:0', changed, digest('changed board'))
        self.assertEqual(len(memory.objects('level:0')), len(objects))
        self.assertEqual(next(obj for obj in memory.objects('level:0') if obj['id'] == ring['id'])['encounter_count'], 1)
        restored = EncounterMemory.from_snapshot(memory.snapshot())
        self.assertEqual(restored.snapshot(), memory.snapshot())

    def test_occluded_panel_fragments_do_not_become_new_unknown_instances(self):
        memory, objects = self.make_memory()
        reference = next(obj for obj in objects if obj['kind'] == 'reference')
        grid = [[3]*64 for _ in range(64)]
        x, y = reference['bbox'][:2]
        grid[y+1][x+1] = 9
        memory.observe('level:0', discover(grid, 3), digest('occlusion'))
        self.assertEqual(len(memory.objects('level:0')), len(objects))

    def test_partial_ring_occlusion_retains_instance_without_new_fragment_target(self):
        memory, objects = self.make_memory()
        grid = objects_board()
        # Hide one half with the supplied floor; the remaining visible mark is
        # exactly a subset of the old occupied cells, not a new ring instance.
        for y in range(20, 25):
            for x in range(18, 21): grid[y][x] = 3
        memory.observe('level:0', discover(grid, 3), digest('partial occlusion'))
        self.assertEqual(len(memory.objects('level:0')), len(objects))
        self.assertEqual(memory.events, [])

    def test_distinct_object_inside_ring_hole_is_not_suppressed_as_fragment(self):
        memory, objects = self.make_memory()
        grid = objects_board()
        grid[22][20] = 8
        memory.observe('level:0', discover(grid, 3), digest('new inside piece'))
        self.assertEqual(len(memory.objects('level:0')), len(objects)+1)

    def test_invalid_encounters_never_write_events(self):
        memory, objects = self.make_memory()
        key = objects[0]['id']
        for args, kwargs in [
                (('level:0', 'not observed', digest('a'), digest('b')), {}),
                (('level:0', key, 'no hash', digest('b')), {}),
                (('level:0', key, digest('a'), digest('b')), {'overlaps': 1}),
                (('level:0', key, digest('a'), digest('b')), {'pattern_changes': float('nan')})]:
            with self.subTest(args=args, kwargs=kwargs), self.assertRaises(ValueError):
                memory.record_encounter(*args, **kwargs)
        self.assertEqual(memory.events, [])

    def test_false_overlap_releases_without_an_encounter(self):
        memory, objects = self.make_memory()
        key = objects[0]['id']
        self.assertIsNone(memory.record_encounter('level:0', key, digest('a'), digest('b'), overlaps=False))
        self.assertEqual(memory.events, [])

    def test_snapshot_round_trip_and_tamper_refusal(self):
        memory, objects = self.make_memory()
        memory.record_encounter('level:0', objects[0]['id'], digest('a'), digest('b'))
        snapshot = json.loads(json.dumps(memory.snapshot()))
        self.assertEqual(EncounterMemory.from_snapshot(snapshot).snapshot(), snapshot)
        for mutation in ('count', 'hash', 'knowledge', 'event', 'contact', 'version', 'object'):
            changed = deepcopy(snapshot)
            if mutation == 'count': changed['levels']['level:0']['objects'][objects[0]['id']]['encounter_count'] = 2
            elif mutation == 'hash': changed['events'][0]['before_sha256'] = 'bad'
            elif mutation == 'knowledge': changed['knowledge'] = {}
            elif mutation == 'event': changed['events'][0]['index'] = True
            elif mutation == 'contact': changed['levels']['level:0']['contacts'].append('absent')
            elif mutation == 'version': changed['version'] = True
            else: changed['levels']['level:0']['objects'][objects[0]['id']]['center'] = [True, 4]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                EncounterMemory.from_snapshot(changed)

    def test_observation_mutation_is_rejected_before_memory_changes(self):
        memory, objects = self.make_memory()
        baseline = memory.snapshot()
        changed = deepcopy(objects)
        changed[0]['id'] = 'false identity'
        with self.assertRaises(ValueError): memory.observe('level:0', changed, digest('mutation'))
        self.assertEqual(memory.snapshot(), baseline)


if __name__ == '__main__': unittest.main()
