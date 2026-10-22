"""Observed ls20 object inventory, with explicit palette/role conventions.

An instance ID describes a kind and screen bounds, not an inferred game function.
Appearance hashes ignore translation. Unknown objects are connected visible marks;
they are proposals, not a claim that every visual component is a game object.
"""
from research.initial_geometry_assistance_v1.geometry import check_grid, digest
from research.ls20_knn_path_v1.geometry import player, cross
from research.ls20_pattern_goal_v1.patterns import locate_panels

PLAYFIELD_ROWS = 60
KINDS = ('reference', 'destination', 'cross', 'unknown')


def instance_id(kind, bbox):
    return kind + ':' + ','.join(str(v) for v in bbox)


def _object(grid, kind, cells, *, center=None, appearance=None):
    cells = sorted(set(map(tuple, cells)), key=lambda p: (p[1], p[0]))
    xs, ys = zip(*cells)
    bbox = [min(xs), min(ys), max(xs), max(ys)]
    if center is None:
        center = [(bbox[0]+bbox[2])/2, (bbox[1]+bbox[3])/2]
        center = [int(v) if v.is_integer() else v for v in center]
    if appearance is None:
        appearance = [[x-bbox[0], y-bbox[1], grid[y][x]] for x, y in cells]
    return dict(id=instance_id(kind, bbox), appearance_sha256=digest(appearance),
                kind=kind, bbox=bbox, cells=[list(p) for p in cells],
                center=list(center), targetability=kind != 'reference')


def discover(grid, floor_color):
    """Find visible panels, a cross and otherwise unexplained connected marks.

Supplied conventions: wall=4, panel/background=5, selected floor color, and
rows 60..63 as interface. Multicolor touching marks are grouped; holes are not
filled. Panel roles follow the previously reviewed display-scale convention.
An occluded known object is retained by EncounterMemory, not fabricated here.
"""
    check_grid(grid)
    if type(floor_color) is not int or not 0 <= floor_color < 16:
        raise ValueError('native floor color required')
    excluded, found = set(), []
    try:
        excluded.update(map(tuple, player(grid)['cells']))
    except ValueError:
        # Missing/occluded player is not evidence of a new orange object.
        excluded.update((x, y) for y in range(PLAYFIELD_ROWS)
                        for x in range(64) if grid[y][x] == 12)
    try:
        panels = locate_panels(grid)
    except ValueError:
        panels = {}
    for kind, panel in panels.items():
        left, top, right, bottom = panel['bbox']
        # A reference display can straddle the bottom interface rows. Keep its
        # whole observed panel as non-targetable inventory, never a route goal.
        if bottom >= PLAYFIELD_ROWS and kind != 'reference':
            continue
        cells = [(x, y) for y in range(top, bottom+1) for x in range(left, right+1)]
        excluded.update(cells)
        found.append(_object(grid, kind, cells, center=panel['center'],
                             appearance=dict(pattern=panel['pattern'], colors=[5, 9])))
    try:
        target = cross(grid)
    except ValueError:
        target = None
    if target is not None:
        cells = list(map(tuple, target['cells']))
        excluded.update(cells)
        found.append(_object(grid, 'cross', cells, center=target['center']))
    remaining = {(x, y) for y in range(PLAYFIELD_ROWS) for x in range(64)
                 if (x, y) not in excluded and grid[y][x] not in (4, 5, floor_color)}
    while remaining:
        seed = min(remaining, key=lambda p: (p[1], p[0]))
        remaining.remove(seed)
        stack, component = [seed], [seed]
        while stack:
            x, y = stack.pop()
            for p in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
                if p in remaining:
                    remaining.remove(p)
                    component.append(p)
                    stack.append(p)
        found.append(_object(grid, 'unknown', component))
    return sorted(found, key=lambda obj: obj['id'])
