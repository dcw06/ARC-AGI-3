"""Depth-bounded DFS checked against an independent visible-grid BFS oracle."""
from collections import deque
from copy import deepcopy
import unittest

from research.ls20_object_memory_v1.objects import discover
from research.ls20_object_memory_v1.search import iddfs
from research.ls20_object_memory_v1.terrain import ObjectTerrain
from tests.test_ls20_object_memory_controller_v1 import observation, START, CROSS


DIRECTIONS = {1: (0, -5), 2: (0, 5), 3: (-5, 0), 4: (5, 0)}


def raw_edge(grid, color, center, action):
    """Independent cell arithmetic, without calling production edge/clear."""
    dx, dy = DIRECTIONS[action]
    for step in range(1, 6):
        x, y = center[0] + dx * step // 5, center[1] + dy * step // 5
        if not (2 <= x < 62 and 2 <= y < 58):
            return None
        if any(grid[b][a] != color for b in range(y - 2, y + 3)
               for a in range(x - 2, x + 3)):
            return None
    return center[0] + dx, center[1] + dy


def bfs_length(terrain, start, blocked=()):
    blocked = set(blocked)
    queue, seen = deque([(tuple(start), 0)]), {tuple(start)}
    while queue:
        position, depth = queue.popleft()
        if position == tuple(terrain.goal):
            return depth
        for action in DIRECTIONS:
            if (position, action) in blocked:
                continue
            target = raw_edge(terrain.grid, terrain.color, position, action)
            if target is not None and target not in seen:
                seen.add(target)
                queue.append((target, depth + 1))
    return None


def terrain_for(walls=()):
    initial = observation(marker=False)
    for x0, y0, x1, y1 in walls:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                initial['grid'][y][x] = 4
    terrain = ObjectTerrain(initial['grid'], 3, discover(initial['grid'], 3))
    terrain.set_goal(CROSS, patterns_match=False)
    return terrain


class DisclosedGraph:
    """A pure movement graph with no dispatch/model/environment interface."""
    def __init__(self, nodes, goal):
        self.nodes = set(nodes)
        self.goal = goal
        self.edge_calls = []

    def edge(self, position, action):
        self.edge_calls.append((position, action))
        dx, dy = DIRECTIONS[action]
        target = (position[0] + dx, position[1] + dy)
        return target if target in self.nodes else None


class IterativeDFS(unittest.TestCase):
    def test_shortest_modeled_depth_matches_independent_bfs_on_disclosed_mazes(self):
        mazes = ((), ((0, 38, 43, 42),), ((28, 0, 32, 44),),
                 ((0, 38, 43, 42), (43, 12, 47, 36)))
        for walls in mazes:
            with self.subTest(walls=walls):
                terrain = terrain_for(walls)
                expected = bfs_length(terrain, START)
                self.assertIsNotNone(expected)
                before = deepcopy(terrain.grid)
                result = iddfs(terrain, START)
                self.assertEqual(result['status'], 'route')
                self.assertEqual(len(result['action_ids']), expected)
                self.assertEqual(result['centers'][0], list(START))
                self.assertEqual(result['centers'][-1], list(CROSS))
                for previous, action, target in zip(result['centers'], result['action_ids'],
                                                     result['centers'][1:]):
                    self.assertEqual(raw_edge(terrain.grid, terrain.color, previous, action), tuple(target))
                self.assertEqual(terrain.grid, before)

    def test_off_center_wall_blocks_a_center_only_shortcut(self):
        terrain = terrain_for()
        terrain.grid[40][38] = 4
        self.assertEqual(terrain.grid[42][36], 3)
        self.assertIsNone(raw_edge(terrain.grid, 3, START, 1))
        result = iddfs(terrain, START)
        self.assertEqual(result['status'], 'route')
        self.assertNotEqual(result['action_ids'][0], 1)
        self.assertEqual(len(result['action_ids']), bfs_length(terrain, START))

    def test_swept_footprint_cannot_jump_an_intermediate_obstacle(self):
        terrain = terrain_for()
        # Upward destination's footprint is clear; an intermediate footprint is not.
        terrain.grid[46][38] = 4
        self.assertTrue(terrain.clear((36, 42)))
        self.assertIsNone(raw_edge(terrain.grid, 3, START, 1))
        result = iddfs(terrain, START)
        self.assertEqual(result['status'], 'route')
        self.assertNotEqual(result['action_ids'][0], 1)
        self.assertEqual(len(result['action_ids']), bfs_length(terrain, START))

    def test_depth_cap_and_expansion_cap_return_no_unbounded_partial_route(self):
        graph = DisclosedGraph(((5, 5), (10, 5), (15, 5), (20, 5)), (20, 5))
        short = iddfs(graph, (5, 5), max_depth=2)
        self.assertEqual(short['status'], 'no_route')
        self.assertEqual(short['action_ids'], [])
        self.assertEqual(iddfs(graph, (5, 5), max_depth=3)['action_ids'], [4, 4, 4])
        capped = iddfs(graph, (5, 5), max_nodes=1)
        self.assertEqual(capped['status'], 'search_cap')
        self.assertLessEqual(capped['expanded_nodes'], 1)
        self.assertEqual(capped['action_ids'], [])

    def test_strict_caps_reject_booleans_and_out_of_range_values(self):
        graph = DisclosedGraph(((5, 5), (10, 5)), (10, 5))
        for key, values in (('max_depth', (True, False, -1, 97, 1.0, None)),
                            ('max_nodes', (True, False, 0, 50001, 1.0, None))):
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    iddfs(graph, (5, 5), **{key: value})

    def test_deadline_callback_aborts_search_before_any_effect_call(self):
        graph = DisclosedGraph(((5, 5), (10, 5), (15, 5)), (15, 5))
        checks = []
        def expired():
            checks.append(True)
            raise TimeoutError('work admission closed')
        with self.assertRaises(TimeoutError):
            iddfs(graph, (5, 5), check=expired)
        self.assertEqual(checks, [True])
        self.assertEqual(graph.edge_calls, [])

    def test_start_at_goal_is_zero_action_route_even_at_zero_depth(self):
        graph = DisclosedGraph(((5, 5),), (5, 5))
        result = iddfs(graph, (5, 5), max_depth=0)
        self.assertEqual(result['status'], 'route')
        self.assertEqual(result['action_ids'], [])
        self.assertEqual(result['centers'], [[5, 5]])
        self.assertEqual(result['expanded_nodes'], 0)
        self.assertEqual(graph.edge_calls, [])

    def test_blocked_edges_are_directed_and_do_not_remove_the_reverse_edge(self):
        blocked = {((5, 5), 4)}
        forward = DisclosedGraph(((5, 5), (10, 5)), (10, 5))
        self.assertEqual(iddfs(forward, (5, 5), blocked=blocked, max_depth=4)['status'], 'no_route')
        backward = DisclosedGraph(((5, 5), (10, 5)), (5, 5))
        result = iddfs(backward, (10, 5), blocked=blocked)
        self.assertEqual(result['action_ids'], [3])
        self.assertEqual(result['centers'], [[10, 5], [5, 5]])

    def test_off_lattice_goal_refuses_without_expanding_the_movement_graph(self):
        graph = DisclosedGraph(((5, 5), (10, 5)), (11, 5))
        result = iddfs(graph, (5, 5))
        self.assertEqual(result['status'], 'no_route')
        self.assertEqual(result['expanded_nodes'], 0)
        self.assertEqual(graph.edge_calls, [])


if __name__ == '__main__':
    unittest.main()
