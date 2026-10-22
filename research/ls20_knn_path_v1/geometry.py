"""Visible-pixel geometry only; no engine state, demonstrations or future frames."""
from collections import Counter
from research.initial_geometry_assistance_v1.geometry import check_grid, digest

K = 4
PLAYFIELD_ROWS = 60  # Excludes the bottom interface/timer, fixed before inference.


def player(grid):
    check_grid(grid)
    orange = {(x, y) for y, row in enumerate(grid[:PLAYFIELD_ROWS])
              for x, color in enumerate(row) if color == 12}
    if len(orange) != 10:
        raise ValueError('expected ten orange player cells')
    cells = set(orange)
    stack = list(orange)
    while stack:
        x, y = stack.pop()
        for a, b in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
            if (0 <= a < 64 and 0 <= b < PLAYFIELD_ROWS and
                    grid[b][a] in (9, 12) and (a, b) not in cells):
                cells.add((a, b)); stack.append((a, b))
    xs, ys = zip(*cells)
    left, top, right, bottom = min(xs), min(ys), max(xs), max(ys)
    if len(cells) != 25 or (right-left, bottom-top) != (4, 4):
        raise ValueError('player cannot be uniquely resolved as a 5x5 visible piece')
    return dict(center=[left+2, top+2], bbox=[left, top, right, bottom],
                cells=[list(p) for p in sorted(cells, key=lambda p: (p[1], p[0]))])


def cross(grid):
    check_grid(grid)
    candidates = []
    offsets = ((0, -1), (-1, 0), (0, 0), (1, 0), (0, 1))
    for y in range(1, PLAYFIELD_ROWS-1):
        for x in range(1, 63):
            cells = [[x+dx, y+dy] for dx, dy in offsets]
            if sorted(grid[b][a] for a, b in cells) == [0, 0, 0, 1, 1]:
                candidates.append(dict(center=[x, y], cells=cells))
    if len(candidates) != 1:
        raise ValueError('initial white cross must be unique')
    return candidates[0]


def neighbors(samples, query):
    """Unweighted k=4 categorical vote; equal distances ordered by y, then x.

    Vote ties have no predicted color. Agreement is a vote fraction, not a
    calibrated probability. Distances use native screen coordinates, never RGB.
    """
    if (type(query) not in (list, tuple) or len(query) != 2 or
            any(type(v) is not int or not 0 <= v < 64 for v in query)):
        raise ValueError('query must be a native integer screen position')
    rows = []
    seen = set()
    for x, y, color in samples:
        if (any(type(v) is not int for v in (x, y, color)) or
                not (0 <= x < 64 and 0 <= y < PLAYFIELD_ROWS and 0 <= color < 16)
                or (x, y) in seen):
            raise ValueError('invalid or repeated training cell')
        seen.add((x, y))
        rows.append(dict(x=x, y=y, color_id=color,
                         squared_distance=(x-query[0])**2+(y-query[1])**2))
    if len(rows) < K:
        raise ValueError('fewer than four visible training cells')
    rows.sort(key=lambda r: (r['squared_distance'], r['y'], r['x']))
    selected = rows[:K]
    votes = Counter(row['color_id'] for row in selected)
    winners = [color for color, count in votes.items() if count == max(votes.values())]
    return dict(k=K, query=list(query), neighbors=selected,
                votes={str(c): votes[c] for c in sorted(votes)},
                predicted_color_id=winners[0] if len(winners) == 1 else None,
                tied=len(winners) != 1, vote_fraction=max(votes.values())/K)


def context(initial, current):
    """Freeze training cells to the initial board, excluding its player and cross.

    No later frame is added to training. A color at the query is included when
    originally visible; the original player footprint always stays withheld.
    The estimate is for the floor near the piece center, not its colored sprite.
    """
    origin = player(initial)
    target = cross(initial)
    active = player(current)
    excluded = {tuple(p) for p in origin['cells']+target['cells']}
    samples = [(x, y, color) for y, row in enumerate(initial[:PLAYFIELD_ROWS])
               for x, color in enumerate(row) if (x, y) not in excluded]
    adjacent = []
    for action, dx, dy in ((1, 0, -5), (2, 0, 5), (3, -5, 0), (4, 5, 0)):
        x, y = active['center'][0]+dx, active['center'][1]+dy
        if 2 <= x < 62 and 2 <= y < PLAYFIELD_ROWS-2:
            region = [initial[b][a] for b in range(y-2, y+3) for a in range(x-2, x+3)
                      if (a, b) not in excluded]
            colors = sorted(set(region))
            adjacent.append(dict(action_id=action, projected_center=[x, y],
                initial_visible_color_ids=colors,
                uniform_visible_color_id=colors[0] if len(colors) == 1 and len(region) == 25 else None))
    return dict(initial_grid_sha256=digest(initial), initial_player=origin,
                current_player=active, target_cross=target,
                adjacent_regions=adjacent,
                training_source='initial visible pixels only; player, cross and bottom interface excluded',
                initial_floor_estimate=neighbors(samples, origin['center']),
                current_floor_estimate=neighbors(samples, active['center']),
                cross_reached=active['center'] == target['center'])
