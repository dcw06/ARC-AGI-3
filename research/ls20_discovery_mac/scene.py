"""Neutral, observation-local proposals. Coordinates are [row, column]."""
from collections import deque
from research.action_effect_v1.records import check_grid


def extract_scene(grid, observation_id):
    check_grid(grid)
    regions, seen = [], set()
    rows, cols = len(grid), len(grid[0])
    for r in range(rows):
        for c in range(cols):
            if (r, c) in seen:
                continue
            color, cells, queue = grid[r][c], [], deque([(r, c)])
            seen.add((r, c))
            while queue:
                y, x = queue.popleft()
                cells.append([y, x])
                for a, b in ((y-1, x), (y+1, x), (y, x-1), (y, x+1)):
                    if (0 <= a < rows and 0 <= b < cols and (a, b) not in seen
                            and grid[a][b] == color):
                        seen.add((a, b))
                        queue.append((a, b))
            cells.sort()
            top, left = min(y for y, x in cells), min(x for y, x in cells)
            bottom, right = max(y for y, x in cells), max(x for y, x in cells)
            regions.append({'id': f'{observation_id}:r{len(regions)}',
                            'observation_id': observation_id, 'color': color,
                            'cells': cells, 'bbox': [top, left, bottom, right],
                            'shape': [[y-top, x-left] for y, x in cells],
                            'crop': [row[left:right+1] for row in grid[top:bottom+1]],
                            'kind': 'computed_region_proposal'})
    owner = {tuple(cell): region['id'] for region in regions for cell in region['cells']}
    adjacent = set()
    for (r, c), ident in owner.items():
        for target in ((r+1, c), (r, c+1)):
            other = owner.get(target)
            if other is not None and other != ident:
                adjacent.add(tuple(sorted((ident, other))))
    return {'observation_id': observation_id, 'regions': regions,
            'relations': [{'kind': 'boundary_adjacent', 'regions': list(pair)}
                          for pair in sorted(adjacent)]}


def identity_candidates(previous_scenes, current):
    """Keep all compatible predecessors; never equate a proposal ID with a true object.

    Historical matches permit reappearance after occlusion. Overlap permits splits,
    merges and partial masks. This is a permissive heuristic, not data association.
    """
    links = []
    for scene in previous_scenes:
        for old in scene['regions']:
            old_cells = {tuple(p) for p in old['cells']}
            for new in current['regions']:
                if old['color'] != new['color']:
                    continue
                overlap = bool(old_cells.intersection(map(tuple, new['cells'])))
                same_shape = old['shape'] == new['shape']
                if not (overlap or same_shape):
                    continue
                links.append({'before': old['id'], 'after': new['id'],
                              'same_shape': same_shape, 'overlap': overlap,
                              'translation': [new['bbox'][i]-old['bbox'][i] for i in (0, 1)]
                              if same_shape else None,
                              'status': 'unresolved',
                              'alternatives': ['same_entity', 'different_entities']})
    return links
