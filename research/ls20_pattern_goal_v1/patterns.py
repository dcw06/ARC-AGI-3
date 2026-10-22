"""Recognize the two visible ls20 glyph panels without coordinates or glyph data.

This is an explicitly assisted, palette-specific recognizer: background 5 and
foreground 9 are supplied visual conventions. It does not infer game rules.
It groups disconnected foreground marks by their enclosing panel, removes only
lossless integer display scaling, and preserves holes and rotation ambiguity.
"""
from math import gcd

from research.initial_geometry_assistance_v1.geometry import check_grid

BACKGROUND = 5
FOREGROUND = 9


def _bbox(value):
    if (type(value) not in (list, tuple) or len(value) != 4 or
            any(type(v) is not int or not 0 <= v < 64 for v in value) or
            value[0] >= value[2] or value[1] >= value[3]):
        raise ValueError('nonempty native panel bounds required')
    return tuple(value)


def _reduce(mask):
    """Take the largest square pixel block that exactly explains every cell."""
    height, width = len(mask), len(mask[0])
    for scale in range(gcd(width, height), 0, -1):
        if width % scale or height % scale:
            continue
        if all(mask[y+dy][x+dx] == mask[y][x]
               for y in range(0, height, scale)
               for x in range(0, width, scale)
               for dy in range(scale) for dx in range(scale)):
            return [[mask[y][x] for x in range(0, width, scale)]
                    for y in range(0, height, scale)], scale
    raise AssertionError('unit scale must explain a binary image')


def read_panel(grid, bbox):
    """Read one frozen background-interior bbox, independently of other panels.

    The complete background border distinguishes a panel from a cropped glyph.
    A contrast mark may have disconnected pieces or enclose background holes.
    """
    check_grid(grid)
    left, top, right, bottom = _bbox(bbox)
    if right-left != bottom-top:
        raise ValueError('square glyph panel required')
    if any(grid[y][x] not in (BACKGROUND, FOREGROUND)
           for y in range(top, bottom+1) for x in range(left, right+1)):
        raise ValueError('unexpected panel color or occlusion')
    border = ([(x, top) for x in range(left, right+1)] +
              [(x, bottom) for x in range(left, right+1)] +
              [(left, y) for y in range(top, bottom+1)] +
              [(right, y) for y in range(top, bottom+1)])
    if any(grid[y][x] != BACKGROUND for x, y in border):
        raise ValueError('complete visible background border required')
    marks = [(x, y) for y in range(top+1, bottom)
             for x in range(left+1, right) if grid[y][x] == FOREGROUND]
    if not marks:
        raise ValueError('panel has no visible glyph')
    xs, ys = zip(*marks)
    gx0, gy0, gx1, gy1 = min(xs), min(ys), max(xs), max(ys)
    raw = [[int(grid[y][x] == FOREGROUND) for x in range(gx0, gx1+1)]
           for y in range(gy0, gy1+1)]
    pattern, scale = _reduce(raw)
    # Integer values for integer centers; retain half-cell centers where needed.
    center = [(left+right)/2, (top+bottom)/2]
    center = [int(v) if v.is_integer() else v for v in center]
    return dict(bbox=[left, top, right, bottom], center=center,
                foreground_bbox=[gx0, gy0, gx1, gy1], pattern=pattern,
                scale=scale, background_color_id=BACKGROUND,
                foreground_color_id=FOREGROUND)


def _matrix(panel):
    matrix = panel.get('pattern') if type(panel) is dict else None
    if (type(matrix) is not list or not matrix or
            type(matrix[0]) is not list or not matrix[0] or
            any(type(row) is not list or len(row) != len(matrix[0]) or
                any(type(v) is not int or v not in (0, 1) for v in row)
                for row in matrix) or not any(any(row) for row in matrix)):
        raise ValueError('nonempty binary pattern required')
    return [row[:] for row in matrix]


def compare_patterns(reference, destination):
    """List every clockwise quarter-turn mapping reference to destination.

    Equality means zero turns are possible. Symmetric patterns can admit several
    rotations; no unique orientation or rotation rule is invented in that case.
    Reflections are not among the transformations considered.
    """
    current, target = _matrix(reference), _matrix(destination)
    turns = []
    for n in range(4):
        if current == target:
            turns.append(n)
        current = [list(row) for row in zip(*current[::-1])]
    return dict(matched=0 in turns, clockwise_quarter_turns=turns)


def locate_panels(grid):
    """Find exactly two bounded panels and identify their visible scale roles.

    The larger-scale glyph is the reference display; the smaller-scale glyph is
    the destination. This role convention is an explicit ls20-level assumption,
    rather than a claim of general object/function discovery.
    """
    check_grid(grid)
    remaining = {(x, y) for y, row in enumerate(grid)
                 for x, color in enumerate(row) if color == BACKGROUND}
    candidates = []
    while remaining:
        seed = remaining.pop()
        stack, component = [seed], [seed]
        while stack:
            x, y = stack.pop()
            for point in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
                if point in remaining:
                    remaining.remove(point)
                    stack.append(point)
                    component.append(point)
        xs, ys = zip(*component)
        bbox = [min(xs), min(ys), max(xs), max(ys)]
        # A screen-edge region is not evidence of an enclosed glyph panel.
        if bbox[0] == 0 or bbox[1] == 0 or bbox[2] == 63 or bbox[3] == 63:
            continue
        try:
            panel = read_panel(grid, bbox)
        except ValueError:
            continue
        if panel['bbox'] not in [p['bbox'] for p in candidates]:
            candidates.append(panel)
    if len(candidates) != 2:
        raise ValueError('exactly two unambiguous visible glyph panels required')
    reference, destination = sorted(candidates, key=lambda p: -p['scale'])
    if reference['scale'] <= destination['scale']:
        raise ValueError('reference and destination display scales are ambiguous')
    if not compare_patterns(reference, destination)['clockwise_quarter_turns']:
        raise ValueError('panels are not exact scaled rotations of one glyph')
    return dict(reference=reference, destination=destination)
