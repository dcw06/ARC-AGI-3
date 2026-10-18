"""Lossless, label-free geometry shared by both experimental arms."""
import hashlib
import json


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def check_grid(grid):
    if (type(grid) is not list or len(grid) != 64 or
            any(type(row) is not list or len(row) != 64 or
                any(type(v) is not int or not 0 <= v <= 15 for v in row) for row in grid)):
        raise ValueError('expected a 64 by 64 palette grid')
    return grid


def checked_cells(values):
    if type(values) is not list:
        raise ValueError('mask cells must be a list')
    out = []
    for point in values:
        if (type(point) is not list or len(point) != 2 or
                any(type(v) is not int or not 0 <= v < 64 for v in point)):
            raise ValueError('mask coordinate must be an integer cell')
        out.append(tuple(point))
    if len(set(out)) != len(out):
        raise ValueError('duplicate mask cell')
    return sorted(out, key=lambda p: (p[1], p[0]))


def encode_mask(values):
    cells = checked_cells(values)
    runs = []
    for x, y in cells:
        if runs and runs[-1][0] == y and runs[-1][2] == x - 1:
            runs[-1][2] = x
        else:
            runs.append([y, x, x])
    if not cells:
        return {'row_runs_y_x0_x1_inclusive': [], 'bbox_xyxy_inclusive': None, 'occupied_anchor_xy': None}
    xs, ys = zip(*cells)
    # Nearest occupied cell to the centroid. Never an empty geometric center.
    n, sx, sy = len(cells), sum(xs), sum(ys)
    anchor = min(cells, key=lambda p: ((n*p[0]-sx)**2 + (n*p[1]-sy)**2, p[1], p[0]))
    return {'row_runs_y_x0_x1_inclusive': runs,
            'bbox_xyxy_inclusive': [min(xs), min(ys), max(xs), max(ys)],
            'occupied_anchor_xy': list(anchor)}


def decode_mask(mask):
    if type(mask) is not dict or set(mask) != {
            'row_runs_y_x0_x1_inclusive', 'bbox_xyxy_inclusive', 'occupied_anchor_xy'}:
        raise ValueError('unexpected geometry fields')
    runs = mask['row_runs_y_x0_x1_inclusive']
    if type(runs) is not list:
        raise ValueError('invalid row runs')
    cells = []
    for run in runs:
        if (type(run) is not list or len(run) != 3 or any(type(v) is not int for v in run)
                or not (0 <= run[0] < 64 and 0 <= run[1] <= run[2] < 64)):
            raise ValueError('invalid row run')
        y, left, right = run
        cells.extend([[x, y] for x in range(left, right+1)])
    if encode_mask(cells) != mask:
        raise ValueError('geometry is not canonical or has a false anchor/bounding box')
    return cells


def inventory(masks):
    """Input is *only* cell lists, so source labels and roles cannot leak."""
    if type(masks) is not list:
        raise ValueError('expected mask list')
    encoded = sorted((encode_mask(cells) for cells in masks), key=canonical)
    # Duplicate/empty proposals are retained; their costs are part of perception.
    return [{'id': f'o{i:03d}', **mask} for i, mask in enumerate(encoded, 1)]


def check_inventory(objects):
    if type(objects) is not list:
        raise ValueError('expected object list')
    masks = []
    for i, obj in enumerate(objects, 1):
        if type(obj) is not dict or obj.get('id') != f'o{i:03d}':
            raise ValueError('non-neutral object ID')
        masks.append(decode_mask({k: v for k, v in obj.items() if k != 'id'}))
    if inventory(masks) != objects:
        raise ValueError('noncanonical inventory')
    return objects
