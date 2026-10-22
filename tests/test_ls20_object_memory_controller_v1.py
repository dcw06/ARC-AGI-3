"""Visible multilevel fixtures: encounter memory, novelty, DFS and exact replay.

These fixtures disclose every movement/contact rule; they contain no game-engine
internals, model responses, provider calls or saved real-game solutions.
"""
from copy import deepcopy
import unittest

from research.initial_geometry_assistance_v1.geometry import digest
from research.ls20_knn_path_v1.geometry import player
from research.ls20_object_memory_v1.audit import audit_levels
from research.ls20_object_memory_v1.controller import run_levels, floor_evidence
from research.ls20_object_memory_v1.objects import discover
from research.ls20_object_memory_v1.terrain import ObjectTerrain
from tests.test_ls20_pattern_goal_v1 import glyph
from tests.test_ls20_pattern_recognition_v1 import panel


START = (36, 47)
CROSS = (21, 32)
DESTINATION = (36, 12)
MARKER = (46, 47)
DIRECTIONS = {1: (0, -5), 2: (0, 5), 3: (-5, 0), 4: (5, 0)}


def observation(center=START, *, reference_turns=0, target_turns=2,
                levels_completed=0, marker=True, next_layout=False,
                terminal=None, changed_player=False):
    """Two scale-separated panels, one cross and an optional whole marker."""
    grid = [[3] * 64 for _ in range(64)]
    cross = (26, 32) if next_layout else CROSS
    destination = (46, 12) if next_layout else DESTINATION
    x, y = cross
    for dx, dy, color in ((0, -1, 0), (-1, 0, 1), (0, 0, 0), (1, 0, 0), (0, 1, 1)):
        grid[y + dy][x + dx] = color
    panel(grid, glyph(reference_turns), left=3, top=43, scale=2, margin=2)
    panel(grid, glyph(target_turns), left=destination[0] - 3, top=9, margin=2)
    if marker:
        for b in range(MARKER[1] - 1, MARKER[1] + 2):
            for a in range(MARKER[0] - 1, MARKER[0] + 2):
                grid[b][a] = 8
    if terminal is None:
        x, y = center
        for b in range(y - 2, y + 3):
            for a in range(x - 2, x + 3):
                grid[b][a] = (7 if changed_player else 12) if b < y else 9
    elif terminal == 'WIN':
        # Final engine completion may remove every recognized old-level object.
        grid = [[4] * 64 for _ in range(64)]
    return dict(grid=grid, legal_actions=[1, 2, 3, 4],
                state=terminal or 'NOT_FINISHED', levels_completed=levels_completed)


class MultilevelEngine:
    """Observed five-cell moves, cross rotation and counter-based completion."""
    def __init__(self, *, levels=3, turns=2, marker=True, finish=True,
                 rotate_on_contact=True, translate_later=True, blocked_moves=0,
                 initial_counter=0, win_without_increment=False):
        self.level_limit = initial_counter + levels
        self.counter = initial_counter
        self.initial_counter = initial_counter
        self.turns = turns
        self.reference_turns = 0
        self.marker = marker
        self.finish = finish
        self.rotate_on_contact = rotate_on_contact
        self.translate_later = translate_later
        self.blocked_moves = blocked_moves
        self.win_without_increment = win_without_increment
        self.center = START
        self.actions = []
        self.contacts = []
        self.bootstraps = 0
        self.closed = False
        self.won = False

    def layout(self):
        return self.translate_later and self.counter > self.initial_counter

    def cross(self):
        return (26, 32) if self.layout() else CROSS

    def destination(self):
        return (46, 12) if self.layout() else DESTINATION

    def observation(self):
        return observation(self.center, reference_turns=self.reference_turns,
            target_turns=self.turns, levels_completed=self.counter, marker=self.marker,
            next_layout=self.layout(), terminal='WIN' if self.won else None)

    def bootstrap(self):
        self.bootstraps += 1
        if self.bootstraps != 1:
            raise AssertionError('a level transition must not reset/bootstrap the engine')
        return self.observation()

    def dispatch(self, command):
        if self.won:
            raise AssertionError('no action after terminal engine completion')
        if set(command) != {'action_id', 'action_data'} or command['action_data']:
            raise AssertionError('one directional command required')
        action = command['action_id']
        if action not in DIRECTIONS:
            raise AssertionError('unsupported directional action')
        self.actions.append(dict(level=self.counter, center=list(self.center), action=action))
        if self.blocked_moves:
            self.blocked_moves -= 1
            return self.observation()
        old = self.center
        dx, dy = DIRECTIONS[action]
        self.center = (old[0] + dx, old[1] + dy)
        if not (2 <= self.center[0] < 62 and 2 <= self.center[1] < 58):
            raise AssertionError('fixture moved outside the playable board')
        if self.center == MARKER and old != MARKER and self.marker:
            self.contacts.append((self.counter, 'marker'))
        if self.center == self.cross() and old != self.cross():
            self.contacts.append((self.counter, 'cross'))
            if self.rotate_on_contact:
                self.reference_turns = (self.reference_turns + 1) % 4
        if self.center == self.destination():
            self.contacts.append((self.counter, 'destination'))
            if self.finish and self.reference_turns == self.turns:
                if self.win_without_increment:
                    self.won = True
                else:
                    self.counter += 1
                    if self.counter == self.level_limit:
                        self.won = True
                    else:
                        self.center = START
                        self.reference_turns = 0
        return self.observation()

    def close(self):
        self.closed = True
        return dict(closed=True, local_scorecard_opened=True,
                    local_scorecard_closed=True, online_calls=0)


class MultilevelControl(unittest.TestCase):
    def run_case(self, engine, **kwargs):
        events = []
        result = run_levels(engine.observation(), engine, events.append,
                            deadline=10, now=lambda: 0, **kwargs)
        return result, events

    def test_completes_three_actual_levels_without_reset_or_model_calls(self):
        engine = MultilevelEngine()
        result, events = self.run_case(engine)
        self.assertTrue(result['success'])
        self.assertEqual((result['levels_completed'], result['levels_gained']), (3, 3))
        self.assertEqual(engine.counter, 3)
        self.assertEqual(engine.bootstraps, 1)
        self.assertEqual(result['new_dispatches'], len(engine.actions))
        self.assertEqual(result['model_calls'], 0)
        self.assertTrue(engine.closed)
        self.assertEqual(len([e for e in events if e['kind'] == 'level_complete']), 3)

    def test_new_marker_is_contacted_before_revisiting_known_cross(self):
        engine = MultilevelEngine(levels=1, turns=2)
        result, _ = self.run_case(engine, max_levels=1)
        self.assertTrue(result['success'])
        order = [kind for level, kind in engine.contacts if level == 0]
        self.assertEqual(order.count('marker'), 1)
        cross_indices = [i for i, kind in enumerate(order) if kind == 'cross']
        self.assertGreaterEqual(len(cross_indices), 2)
        self.assertLess(order.index('marker'), cross_indices[1])

    def test_dfs_keeps_its_detour_instead_of_reversing_at_each_new_position(self):
        class DetourMaze(MultilevelEngine):
            def observation(self):
                value = super().observation()
                if self.won:
                    return value
                before = deepcopy(value['grid'])
                sprite = player(before)['cells']
                # A horizontal wall separates the start from the cross. The
                # reference panel also bounds the left-hand dead-end. Following
                # a complete DFS route escapes below and around the right edge;
                # greedily restarting DFS reverses into its own preceding cell.
                for y in range(38, 43):
                    for x in range(44):
                        value['grid'][y][x] = 4
                for x, y in sprite:
                    value['grid'][y][x] = before[y][x]
                return value
        engine = DetourMaze(levels=1, turns=1, marker=False)
        result, events = self.run_case(engine, max_levels=1, action_cap=96)
        self.assertTrue(result['success'])
        self.assertEqual(result['levels_gained'], 1)
        self.assertLessEqual(result['new_dispatches'], 96)
        self.assertTrue(any(event['kind'] == 'plan' and
                            event['plan'].get('retained_DFS_suffix') for event in events))
        self.assertTrue(engine.closed)

    def test_observed_relocation_retains_encounters_and_resumes_without_reset(self):
        class OneRelocation(MultilevelEngine):
            def __init__(self):
                super().__init__(levels=1, turns=1)
                self.relocated = False

            def dispatch(self, command):
                had_marker = (0, 'marker') in self.contacts
                value = super().dispatch(command)
                if had_marker and not self.relocated:
                    self.relocated = True
                    self.center = (31, 42)
                    value = self.observation()
                return value
        engine = OneRelocation()
        result, events = self.run_case(engine, max_levels=1)
        self.assertTrue(result['success'])
        self.assertEqual(result['levels_gained'], 1)
        self.assertEqual(engine.bootstraps, 1)
        relocated = [event for event in events if event['kind'] == 'observed_relocation']
        self.assertEqual(len(relocated), 1)
        receipt = relocated[0]
        transition = next(event['record'] for event in events if event['kind'] == 'transition'
                          and digest(event['record']['after']) == receipt['after_sha256'])
        self.assertEqual(transition['before']['levels_completed'], 0)
        self.assertEqual(transition['after']['levels_completed'], 0)
        self.assertEqual(receipt['before_sha256'], digest(transition['before']))
        self.assertEqual(receipt['actual_center'], [31, 42])
        index = events.index(receipt)
        before = next(event for event in reversed(events[:index])
                      if event['kind'] == 'memory_checkpoint')
        after = next(event for event in events[index + 1:]
                     if event['kind'] == 'memory_checkpoint')
        self.assertEqual(after['trigger'], 'observed_relocation')
        self.assertEqual(before['memory']['events'], after['memory']['events'])
        self.assertTrue(any(event['object_id'].startswith('unknown:')
                            for event in after['memory']['events']))
        self.assertTrue(all(event in result['memory']['events']
                            for event in after['memory']['events']))
        self.assertEqual(result['new_dispatches'], len(engine.actions))
        self.assertTrue(engine.closed)

    def test_repeated_relocations_are_bounded_without_crediting_planned_targets(self):
        class RepeatedRelocations(MultilevelEngine):
            def dispatch(self, command):
                self.actions.append(dict(level=self.counter, center=list(self.center),
                                         action=command['action_id']))
                self.center = (31, 42) if len(self.actions) % 2 else START
                return self.observation()
        engine = RepeatedRelocations()
        result, events = self.run_case(engine)
        relocations = [event for event in events if event['kind'] == 'observed_relocation']
        self.assertEqual(result['reason'], 'relocation_cap')
        self.assertEqual(len(relocations), 3)
        self.assertEqual(result['new_dispatches'], 3)
        self.assertEqual(result['levels_gained'], 0)
        self.assertFalse(result['success'])
        self.assertEqual(result['memory']['events'], [])
        self.assertFalse(any(event['kind'] == 'encounter' for event in events))
        self.assertEqual(engine.bootstraps, 1)
        self.assertTrue(engine.closed)

    def test_new_farther_object_after_contact_preempts_nearby_known_cross_reentry(self):
        class DelayedMarker(MultilevelEngine):
            def observation(self):
                visible = any(kind == 'cross' for _, kind in self.contacts)
                return observation(self.center, reference_turns=self.reference_turns,
                    target_turns=self.turns, levels_completed=self.counter,
                    marker=visible, terminal='WIN' if self.won else None)
        engine = DelayedMarker(levels=1)
        result, _ = self.run_case(engine, max_levels=1)
        self.assertTrue(result['success'])
        order = [kind for _, kind in engine.contacts]
        first_cross = order.index('cross')
        next_cross = order.index('cross', first_cross + 1)
        self.assertLess(first_cross, order.index('marker'))
        self.assertLess(order.index('marker'), next_cross)

    def test_unreachable_new_object_is_deferred_without_blocking_required_cross(self):
        class RingMarker(MultilevelEngine):
            def observation(self):
                value = super().observation()
                if not self.won:
                    grid = value['grid']
                    for y in range(44, 51):
                        for x in range(43, 50):
                            grid[y][x] = 8 if x in (43, 49) or y in (44, 50) else 4
                return value
        engine = RingMarker(levels=1)
        result, events = self.run_case(engine, max_levels=1)
        self.assertTrue(result['success'])
        self.assertNotIn((0, 'marker'), engine.contacts)
        self.assertTrue(any(event['kind'] == 'object_deferred' and
                            event['object_id'].startswith('unknown:') for event in events))
        for state in result['memory']['levels'].values():
            unknowns = [obj for obj in state['objects'].values() if obj['kind'] == 'unknown']
            self.assertTrue(unknowns)
            self.assertTrue(all(obj['encounter_count'] == 0 for obj in unknowns))

    def test_encounter_receipt_is_checkpointed_before_any_further_plan(self):
        result, events = self.run_case(MultilevelEngine(levels=1), max_levels=1)
        count = 0
        for index, event in enumerate(events):
            if event['kind'] != 'encounter':
                continue
            count += 1
            later = events[index + 1:]
            checkpoint_index = next(i for i, value in enumerate(later)
                                    if value['kind'] == 'memory_checkpoint')
            self.assertFalse(any(value['kind'] in ('plan', 'dispatch_intent')
                                 for value in later[:checkpoint_index]))
            checkpoint = later[checkpoint_index]
            self.assertEqual(checkpoint['memory_sha256'], digest(checkpoint['memory']))
            self.assertIn(event['receipt'], checkpoint['memory']['events'])
        self.assertGreater(count, 0)
        self.assertEqual(count, len(result['memory']['events']))

    def test_visual_observation_alone_does_not_record_encounters(self):
        engine = MultilevelEngine()
        events = []
        clock = [0]
        def sink(event):
            events.append(event)
            if event['kind'] == 'level_start':
                clock[0] = 10
        result = run_levels(engine.observation(), engine, sink, deadline=10,
                            now=lambda: clock[0])
        self.assertFalse(result['success'])
        self.assertEqual(result['new_dispatches'], 0)
        self.assertEqual(result['memory']['events'], [])
        self.assertTrue(engine.closed)

    def test_level_transition_uses_new_namespace_and_current_geometry(self):
        engine = MultilevelEngine(levels=2)
        result, events = self.run_case(engine, max_levels=2)
        self.assertTrue(result['success'])
        starts = [event for event in events if event['kind'] == 'level_start']
        self.assertEqual(len(starts), 2)
        self.assertNotEqual(starts[0]['level_key'], starts[1]['level_key'])
        self.assertEqual(len(result['memory']['levels']), 2)
        # The next level has a moved cross and destination; old goals cannot win.
        completed_levels = {level for level, kind in engine.contacts if kind == 'destination'}
        self.assertEqual(completed_levels, {0, 1})
        for level_key in result['memory']['levels']:
            visits = [event for event in result['memory']['events'] if event['level_key'] == level_key]
            self.assertTrue(any(event['object_id'].startswith('cross:') for event in visits))

    def test_same_appearance_on_another_level_is_still_a_fresh_instance(self):
        engine = MultilevelEngine(levels=2, translate_later=False)
        result, _ = self.run_case(engine, max_levels=2)
        self.assertTrue(result['success'])
        markers = [event for event in result['memory']['events']
                   if event['object_id'].startswith('unknown:')]
        self.assertEqual(len(markers), 2)
        self.assertEqual(markers[0]['appearance_sha256'], markers[1]['appearance_sha256'])
        self.assertNotEqual(markers[0]['level_key'], markers[1]['level_key'])

    def test_success_requires_requested_number_of_actual_counter_increments(self):
        engine = MultilevelEngine(levels=1)
        result, _ = self.run_case(engine, max_levels=3)
        self.assertEqual(result['levels_gained'], 1)
        self.assertFalse(result['success'])
        self.assertTrue(engine.closed)

    def test_counter_is_relative_to_the_supplied_start_level(self):
        engine = MultilevelEngine(levels=1, initial_counter=4)
        result, _ = self.run_case(engine, max_levels=1)
        self.assertEqual(result['levels_completed'], 5)
        self.assertEqual(result['levels_gained'], 1)
        self.assertTrue(result['success'])

    def test_win_label_without_counter_change_cannot_claim_a_level_pass(self):
        engine = MultilevelEngine(levels=1, win_without_increment=True)
        result, _ = self.run_case(engine, max_levels=1)
        self.assertFalse(result['success'])
        self.assertEqual(result['levels_gained'], 0)
        self.assertEqual(result['levels_completed'], 0)
        self.assertTrue(engine.closed)

    def test_destination_contact_without_progress_does_not_fabricate_success(self):
        engine = MultilevelEngine(levels=1, turns=0, finish=False)
        result, _ = self.run_case(engine, max_levels=1)
        self.assertFalse(result['success'])
        self.assertEqual(result['levels_gained'], 0)
        self.assertLessEqual(result['new_dispatches'], 96)
        self.assertTrue(engine.closed)

    def test_deadline_after_first_observed_transition_dispatches_no_more(self):
        engine = MultilevelEngine()
        events, clock = [], [0]
        def sink(event):
            events.append(event)
            if event['kind'] == 'transition':
                clock[0] = 10
        result = run_levels(engine.observation(), engine, sink, deadline=10,
                            now=lambda: clock[0])
        self.assertEqual(result['reason'], 'deadline')
        self.assertEqual(result['new_dispatches'], 1)
        self.assertEqual(len(engine.actions), 1)
        self.assertTrue(engine.closed)

    def test_blocked_intent_does_not_fabricate_an_object_encounter(self):
        engine = MultilevelEngine(blocked_moves=1)
        events, clock = [], [0]
        def sink(event):
            events.append(event)
            if event['kind'] == 'transition':
                clock[0] = 10
        result = run_levels(engine.observation(), engine, sink, deadline=10,
                            now=lambda: clock[0])
        self.assertEqual(result['new_dispatches'], 1)
        self.assertEqual(result['memory']['events'], [])
        self.assertFalse(any(event['kind'] == 'encounter' for event in events))

    def test_completion_observed_at_deadline_is_kept_without_new_level_work(self):
        engine = MultilevelEngine(levels=3)
        events, clock = [], [0]
        def sink(event):
            events.append(event)
            if event['kind'] == 'transition' and event['record']['after']['levels_completed']:
                clock[0] = 10
        result = run_levels(engine.observation(), engine, sink, deadline=10,
                            now=lambda: clock[0])
        self.assertEqual(result['levels_gained'], 1)
        self.assertFalse(result['success'])
        self.assertEqual(len([e for e in events if e['kind'] == 'level_complete']), 1)
        self.assertTrue(all(action['level'] == 0 for action in engine.actions))

    def test_total_and_per_level_caps_bound_real_actions(self):
        for limits in (dict(action_cap=1), dict(per_level_cap=1)):
            with self.subTest(limits=limits):
                engine = MultilevelEngine()
                result, _ = self.run_case(engine, **limits)
                self.assertLessEqual(result['new_dispatches'], 1)
                self.assertFalse(result['success'])
                self.assertTrue(engine.closed)

    def test_unchanged_cross_effect_cannot_create_an_unbounded_revisit_loop(self):
        engine = MultilevelEngine(rotate_on_contact=False)
        result, _ = self.run_case(engine, action_cap=60, per_level_cap=40)
        self.assertLessEqual(result['new_dispatches'], 40)
        self.assertFalse(result['success'])
        self.assertTrue(engine.closed)

    def test_changed_player_geometry_is_rejected_without_dispatch(self):
        engine = MultilevelEngine()
        initial = observation(changed_player=True)
        try:
            result = run_levels(initial, engine, lambda event: None, deadline=10, now=lambda: 0)
        except ValueError:
            result = None
        self.assertFalse(engine.actions)
        if result is not None:
            self.assertFalse(result['success'])
            self.assertIsNotNone(result['error'])

    def test_unoccluded_destination_mutation_stops_after_the_observed_action(self):
        class MutatingDestination(MultilevelEngine):
            def observation(self):
                value = super().observation()
                if self.actions and not self.won:
                    value['grid'][9][33] = 9
                return value
        engine = MutatingDestination(levels=1)
        result, _ = self.run_case(engine, max_levels=1)
        self.assertEqual(result['reason'], 'destination_pattern_changed')
        self.assertEqual(result['new_dispatches'], 1)
        self.assertFalse(result['success'])
        self.assertTrue(engine.closed)

    def test_unsupported_new_player_preserves_completed_counter_without_new_actions(self):
        class ChangedNextLevel(MultilevelEngine):
            def observation(self):
                value = super().observation()
                if self.counter > self.initial_counter and not self.won:
                    for row in value['grid']:
                        for x, color in enumerate(row):
                            if color == 12:
                                row[x] = 7
                return value
        engine, events = ChangedNextLevel(levels=3), []
        with self.assertRaises(ValueError):
            run_levels(engine.observation(), engine, events.append, deadline=10, now=lambda: 0)
        result = next(event for event in reversed(events) if event['kind'] == 'summary')
        self.assertEqual(result['levels_gained'], 1)
        self.assertFalse(result['success'])
        self.assertIsNotNone(result['error'])
        self.assertTrue(all(action['level'] == 0 for action in engine.actions))
        self.assertTrue(engine.closed)

    def test_empty_hollow_center_without_occupied_overlap_is_not_an_encounter(self):
        class HollowMarker(MultilevelEngine):
            def observation(self):
                value = super().observation()
                if self.won:
                    return value
                before = deepcopy(value['grid'])
                sprite = player(before)['cells']
                for y in range(43, 52):
                    for x in range(42, 51):
                        value['grid'][y][x] = 8 if x in (42, 50) or y in (43, 51) else 3
                for x, y in sprite:
                    value['grid'][y][x] = before[y][x]
                return value
        engine, events, clock = HollowMarker(levels=1, marker=False), [], [0]
        engine.center = (41, 47)
        def sink(event):
            events.append(event)
            if event['kind'] == 'transition':
                clock[0] = 10
        result = run_levels(engine.observation(), engine, sink, deadline=10, now=lambda: clock[0])
        self.assertEqual(player(result['final_observation']['grid'])['center'], list(MARKER))
        self.assertFalse(any(event['object_id'].startswith('unknown:')
                             for event in result['memory']['events']))
        self.assertEqual(result['new_dispatches'], 1)

    def test_observed_floor_color_change_replans_without_inventing_a_floor_object(self):
        class ChangedFloor(MultilevelEngine):
            def observation(self):
                value = super().observation()
                if self.actions and not self.won:
                    for row in value['grid']:
                        for x, color in enumerate(row):
                            if color == 3:
                                row[x] = 8
                return value
        engine = ChangedFloor(levels=1, marker=False)
        result, events = self.run_case(engine, max_levels=1)
        self.assertTrue(result['success'])
        changes = [event for event in events if event['kind'] == 'floor_hypothesis_changed']
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]['before'], 3)
        self.assertEqual(changes[0]['evidence']['color_id'], 8)
        for state in result['memory']['levels'].values():
            self.assertFalse(any(obj['kind'] == 'unknown' for obj in state['objects'].values()))


class FloorEvidence(unittest.TestCase):
    def dead_end(self):
        value = observation(marker=False)
        objects = discover(value['grid'], 3)
        # These are exactly the four closest unoccluded cells, all distance 3.
        for x, y in ((36, 44), (33, 47), (39, 47)):
            value['grid'][y][x] = 4
        return value['grid'], objects

    def test_wall_majority_keeps_raw_vote_and_qualifies_previously_traversed_floor(self):
        grid, objects = self.dead_end()
        evidence = floor_evidence(grid, objects, {3})
        self.assertEqual(evidence['estimate']['votes'], {'3': 1, '4': 3})
        self.assertEqual(evidence['estimate']['predicted_color_id'], 4)
        self.assertEqual(evidence['color_id'], 3)
        self.assertEqual(evidence['source'], 'previously_traversed_color_hypothesis')

    def test_same_wall_majority_without_prior_traversal_stays_unresolved(self):
        grid, objects = self.dead_end()
        evidence = floor_evidence(grid, objects, set())
        self.assertEqual(evidence['estimate']['votes'], {'3': 1, '4': 3})
        self.assertEqual(evidence['estimate']['predicted_color_id'], 4)
        self.assertIsNone(evidence['color_id'])
        self.assertEqual(evidence['source'], 'unresolved')

    def test_multiple_sampled_floor_candidates_are_not_resolved_by_the_prior(self):
        grid, objects = self.dead_end()
        grid[47][39] = 3
        grid[50][36] = 8
        evidence = floor_evidence(grid, objects, {3})
        self.assertEqual(evidence['estimate']['votes'], {'3': 1, '4': 2, '8': 1})
        self.assertEqual(evidence['estimate']['predicted_color_id'], 4)
        self.assertIsNone(evidence['color_id'])
        self.assertEqual(evidence['source'], 'unresolved')


class ObjectOverlays(unittest.TestCase):
    def test_destination_overlay_requires_current_pattern_match(self):
        initial = observation(marker=False)
        objects = discover(initial['grid'], 3)
        terrain = ObjectTerrain(initial['grid'], 3, objects)
        reference = deepcopy([row[3:13] for row in terrain.grid[43:53]])
        terrain.set_goal(DESTINATION, patterns_match=False)
        self.assertFalse(terrain.clear(DESTINATION))
        terrain.set_goal(DESTINATION, patterns_match=True)
        self.assertTrue(terrain.clear(DESTINATION))
        self.assertEqual([row[3:13] for row in terrain.grid[43:53]], reference)
        terrain.set_goal(CROSS, patterns_match=False)
        self.assertFalse(terrain.clear(DESTINATION))

    def test_unknown_ring_overlay_does_not_fill_its_hole_or_neighboring_walls(self):
        initial = observation(marker=False)
        grid = initial['grid']
        for y in range(44, 51):
            for x in range(43, 50):
                grid[y][x] = 8 if x in (43, 49) or y in (44, 50) else 4
        grid[47][52] = 4
        objects = discover(grid, 3)
        ring = next(obj for obj in objects if obj['kind'] == 'unknown')
        self.assertEqual(ring['center'], list(MARKER))
        terrain = ObjectTerrain(grid, 3, objects)
        terrain.set_goal(MARKER, patterns_match=False)
        self.assertTrue(all(terrain.grid[y][x] == 3 for x, y in ring['cells']))
        self.assertEqual(terrain.grid[47][46], 4)
        self.assertEqual(terrain.grid[47][52], 4)
        self.assertFalse(terrain.clear(MARKER))

    def test_uncovered_floor_is_retained_after_goal_and_color_changes(self):
        initial = observation(marker=False)
        objects = discover(initial['grid'], 3)
        terrain = ObjectTerrain(initial['grid'], 3, objects)
        after = observation((31, 47), marker=False)
        after['grid'][47][36] = 4
        terrain.update(after['grid'], discover(after['grid'], 3))
        terrain.set_goal(DESTINATION, patterns_match=True)
        terrain.set_color(8)
        terrain.set_color(3)
        self.assertEqual(terrain.observed[47][36], 4)
        self.assertEqual(terrain.grid[47][36], 4)

    def test_stale_invisible_object_cannot_open_a_newly_observed_wall(self):
        initial = observation()
        objects = discover(initial['grid'], 3)
        terrain = ObjectTerrain(initial['grid'], 3, objects)
        after = observation((31, 47), marker=False)
        for y in range(46, 49):
            for x in range(45, 48):
                after['grid'][y][x] = 4
        retained = [dict(obj, visible=obj['kind'] != 'unknown') for obj in objects]
        terrain.update(after['grid'], retained)
        self.assertTrue(all(terrain.grid[y][x] == 4 for y in range(46, 49)
                            for x in range(45, 48)))
        self.assertFalse(terrain.clear(MARKER))

    def test_new_floor_hypothesis_applies_only_under_current_sprite(self):
        initial = observation(marker=False)
        terrain = ObjectTerrain(initial['grid'], 3, discover(initial['grid'], 3))
        first = observation((31, 47), marker=False)
        terrain.update(first['grid'], discover(first['grid'], 3))
        # The cache under the current sprite came from the old floor color.
        self.assertEqual(terrain.observed[47][31], 3)
        changed = deepcopy(first)
        for row in changed['grid']:
            for x, color in enumerate(row):
                if color == 3:
                    row[x] = 8
        terrain.set_color(8)
        terrain.update(changed['grid'], discover(changed['grid'], 8))
        self.assertEqual(terrain.observed[47][31], 3)
        self.assertTrue(terrain.clear((31, 47)))
        self.assertEqual(terrain.observed[47][36], 8)
        self.assertEqual(terrain.grid[47][36], 8)


class Replay(unittest.TestCase):
    def evidence(self, *, max_levels=2):
        engine = MultilevelEngine(levels=max_levels)
        initial, events = engine.observation(), []
        result = run_levels(initial, engine, events.append, deadline=10,
                            now=lambda: 0, max_levels=max_levels)
        return initial, events, result

    def test_reconstructs_encounters_navigation_and_both_level_transitions(self):
        initial, events, result = self.evidence()
        self.assertTrue(result['success'])
        replay = audit_levels(initial, events, lambda: MultilevelEngine(levels=2), max_levels=2)
        self.assertTrue(replay['content_replay_verified'])
        self.assertEqual(replay['result'], result)
        self.assertEqual(result['model_calls'], 0)

    def test_tampered_memory_plan_transition_and_result_are_refused(self):
        initial, events, _ = self.evidence()
        for kind in ('memory_checkpoint', 'plan', 'transition', 'summary'):
            changed = deepcopy(events)
            event = next(value for value in changed if value['kind'] == kind)
            if kind == 'memory_checkpoint':
                event['memory']['events'].append({'invented': 'encounter'})
                event['memory_sha256'] = digest(event['memory'])
            elif kind == 'plan':
                event['goal_object_id'] = 'invented-object'
            elif kind == 'transition':
                event['record']['after']['levels_completed'] += 1
                event['transition_sha256'] = digest(event['record'])
            else:
                event['success'] = not event['success']
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                audit_levels(initial, changed, lambda: MultilevelEngine(levels=2), max_levels=2)

    def test_partial_deadline_evidence_replays_without_an_unlimited_completion(self):
        engine, events, clock = MultilevelEngine(), [], [0]
        initial = engine.observation()
        def sink(event):
            events.append(event)
            if event['kind'] == 'transition':
                clock[0] = 10
        result = run_levels(initial, engine, sink, deadline=10, now=lambda: clock[0])
        replay = audit_levels(initial, events, MultilevelEngine)
        self.assertEqual(replay['result'], result)
        self.assertEqual(result['new_dispatches'], 1)


if __name__ == '__main__':
    unittest.main()
