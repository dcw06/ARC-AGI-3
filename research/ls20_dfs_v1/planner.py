"""Iterative DFS over visible, footprint-safe five-cell directional moves."""
from copy import deepcopy
from research.initial_geometry_assistance_v1.geometry import check_grid, digest
from research.ls20_knn_path_v1.geometry import context, player, PLAYFIELD_ROWS

STEP = 5
RADIUS = 2
DIRECTIONS = {1: (0, -STEP), 2: (0, STEP), 3: (-STEP, 0), 4: (STEP, 0)}


def point(value):
    if (type(value) not in (tuple, list) or len(value) != 2 or
            any(type(v) is not int or not 0 <= v < 64 for v in value)):
        raise ValueError('native integer position required')
    return tuple(value)


class Terrain:
    """Observed screen pixels only. Sprite/cross floor is an explicit assumption.

    Future observations may replace occluded cells with newly visible evidence.
    No engine internals, future rollout, saved solution or demonstration is read.
    """
    def __init__(self, initial, color):
        check_grid(initial)
        if type(color) is not int or not 0 <= color < 16:
            raise ValueError('resolved path color required')
        geometry = context(initial, initial)
        self.color = color
        self.initial = deepcopy(initial)
        self.grid = deepcopy(initial)
        self.goal = tuple(geometry['target_cross']['center'])
        self.target_cells = {tuple(p) for p in geometry['target_cross']['cells']}
        self.occluded_start = {tuple(p) for p in geometry['initial_player']['cells']}
        self.assumed_cells = self.target_cells | self.occluded_start
        for x, y in self.assumed_cells:
            self.grid[y][x] = color

    def observe(self, grid):
        check_grid(grid)
        hidden = {tuple(p) for p in player(grid)['cells']} | self.target_cells
        for y in range(PLAYFIELD_ROWS):
            for x in range(64):
                if (x, y) not in hidden:
                    self.grid[y][x] = grid[y][x]

    def clear(self, center):
        x, y = center
        if not (RADIUS <= x < 64-RADIUS and RADIUS <= y < PLAYFIELD_ROWS-RADIUS):
            return False
        return all(self.grid[b][a] == self.color
                   for b in range(y-RADIUS, y+RADIUS+1)
                   for a in range(x-RADIUS, x+RADIUS+1))

    def edge(self, center, action):
        if type(action) is not int or action not in DIRECTIONS:
            raise ValueError('directional action required')
        dx, dy = DIRECTIONS[action]
        # Every intermediate footprint is checked, not merely the destination.
        if not all(self.clear((center[0]+dx*i//STEP, center[1]+dy*i//STEP))
                   for i in range(1, STEP+1)):
            return None
        return center[0]+dx, center[1]+dy


def dfs(terrain, start, *, blocked=(), max_nodes=4096, check=lambda: None):
    """Depth-first traversal; Manhattan distance orders neighbors, not search cost.

    This is not shortest-path search. Visited nodes bound cycles; search never
    dispatches real actions. A route exceeding the remaining action budget is
    reported by the controller rather than silently changing algorithms.
    """
    start = point(start)
    if type(max_nodes) is not int or not 1 <= max_nodes <= 4096:
        raise ValueError('search-node cap required')
    blocked = set(blocked)
    visited = {start}
    parents = {}
    expanded = 0

    def adjacent(center):
        candidates = []
        for action in DIRECTIONS:
            if (center, action) in blocked: continue
            target = terrain.edge(center, action)
            if target is not None:
                distance = abs(target[0]-terrain.goal[0])+abs(target[1]-terrain.goal[1])
                candidates.append((distance, action, target))
        return iter((action, target) for _, action, target in sorted(candidates))

    check()
    stack = [(start, adjacent(start))]
    while stack:
        check()
        center, options = stack[-1]
        if center == terrain.goal:
            actions, centers = [], [center]
            while center != start:
                previous, action = parents[center]
                actions.append(action); centers.append(previous); center = previous
            return dict(status='route', action_ids=list(reversed(actions)),
                        centers=[list(p) for p in reversed(centers)], expanded_nodes=expanded,
                        visited_nodes=len(visited))
        try: action, target = next(options)
        except StopIteration: stack.pop(); continue
        if target in visited: continue
        if len(visited) >= max_nodes:
            return dict(status='search_cap', action_ids=[], centers=[], expanded_nodes=expanded,
                        visited_nodes=len(visited))
        parents[target] = center, action
        visited.add(target); expanded += 1
        stack.append((target, adjacent(target)))
    return dict(status='no_route', action_ids=[], centers=[], expanded_nodes=expanded,
                visited_nodes=len(visited))


def terrain_digest(terrain):
    return digest(dict(grid=terrain.grid, path_color_id=terrain.color, goal=terrain.goal))
