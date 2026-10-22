"""Footprint-safe DFS terrain with explicit, tightly bounded object overlays."""
from copy import deepcopy
from research.initial_geometry_assistance_v1.geometry import check_grid, digest
from research.ls20_dfs_v1.planner import Terrain, point
from research.ls20_knn_path_v1.geometry import player, PLAYFIELD_ROWS


class ObjectTerrain(Terrain):
    def __init__(self, initial, color, objects):
        super().__init__(initial, color)
        self.observed = deepcopy(self.grid)
        self.assumed = set(self.assumed_cells)
        self.objects = deepcopy(objects)
        self.sprite = {tuple(p) for p in player(initial)['cells']}
        self.patterns_match = False
        self.rebuild()

    def rebuild(self):
        self.grid = deepcopy(self.observed)
        for obj in self.objects:
            if not obj['targetability'] or obj['kind'] == 'reference':
                continue
            occupied={tuple(p) for p in obj['cells']}
            if not obj.get('visible',True) and not occupied & self.sprite:
                continue
            if obj['kind'] == 'destination':
                if not self.patterns_match:
                    continue
                left, top, right, bottom = obj['bbox']
                cells = [(x,y) for y in range(top,bottom+1) for x in range(left,right+1)]
            else:
                # An unknown marker grants no permission to open its neighbors,
                # enclosing room or arbitrary rectangle. Only occupied cells.
                cells = obj['cells'] if obj.get('visible',True) else occupied & self.sprite
            for x,y in cells:
                self.grid[y][x] = self.color
        # The current sprite hides its floor. Keep this explicit hypothesis
        # separate from the observed cache, especially after a color change.
        # Pixels outside the sprite retain their actual observed colors.
        for x,y in self.sprite:
            self.grid[y][x] = self.color

    def update(self, grid, objects):
        check_grid(grid)
        sprite = {tuple(p) for p in player(grid)['cells']}
        self.sprite = sprite
        # Visible object colors are overlays, not evidence of floor color.
        marks = {tuple(p) for obj in objects if obj.get('visible', True) for p in obj['cells']}
        for y in range(PLAYFIELD_ROWS):
            for x in range(64):
                if (x,y) not in sprite | marks:
                    self.observed[y][x] = grid[y][x]
                    self.assumed.discard((x,y))
        self.objects = deepcopy(objects)
        self.rebuild()

    def set_color(self, color):
        if type(color) is not int or not 0 <= color < 16:
            raise ValueError('resolved floor color required')
        self.color = color
        for x,y in self.assumed:
            self.observed[y][x] = color
        self.rebuild()

    def set_goal(self, goal, *, patterns_match):
        self.goal = point(goal)
        if type(patterns_match) is not bool:
            raise ValueError('observed pattern-match flag required')
        self.patterns_match = patterns_match
        self.rebuild()

    def topology_sha256(self):
        return digest([[v==self.color for v in row] for row in self.grid[:PLAYFIELD_ROWS]])
