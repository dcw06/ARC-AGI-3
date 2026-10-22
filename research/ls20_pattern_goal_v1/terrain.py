"""Retain observed floor while changing DFS goals and a narrow destination overlay."""
from copy import deepcopy
from research.initial_geometry_assistance_v1.geometry import check_grid, digest
from research.ls20_knn_path_v1.geometry import context, player, PLAYFIELD_ROWS
from research.ls20_dfs_v1.planner import Terrain, point


class SceneTerrain(Terrain):
    def __init__(self, initial, color, destination):
        super().__init__(initial, color)
        self.observed = deepcopy(self.grid)
        self.assumed = set(self.assumed_cells)
        self.destination = deepcopy(destination)
        left, top, right, bottom = destination['bbox']
        self.destination_cells = {(x,y) for y in range(top,bottom+1) for x in range(left,right+1)}
        self.destination_open = False

    def rebuild(self):
        self.grid = deepcopy(self.observed)
        if self.destination_open:
            # Explicit goal-overlay assumption only after visible patterns match.
            # Other black/blue panels and regions remain untouched obstacles.
            for x,y in self.destination_cells: self.grid[y][x] = self.color

    def observe(self, grid):
        check_grid(grid)
        hidden = {tuple(p) for p in player(grid)['cells']} | self.target_cells
        for y in range(PLAYFIELD_ROWS):
            for x in range(64):
                if (x,y) not in hidden:
                    self.observed[y][x] = grid[y][x]
                    self.assumed.discard((x,y))
        self.rebuild()

    def set_color(self, color):
        if type(color) is not int or not 0 <= color < 16: raise ValueError('resolved path color required')
        self.color = color
        for x,y in self.assumed: self.observed[y][x] = color
        self.rebuild()

    def set_goal(self, goal, *, patterns_match):
        self.goal = point(goal)
        if type(patterns_match) is not bool: raise ValueError('exact pattern-match flag required')
        self.destination_open = patterns_match
        self.rebuild()

    def topology_sha256(self):
        return digest([[c == self.color for c in row] for row in self.grid[:PLAYFIELD_ROWS]])
