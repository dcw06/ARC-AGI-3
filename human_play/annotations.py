"""Human-named regions, derived only from the exact visible frame."""
import hashlib
import json


def region(observation, body, sequence):
    if type(body.get('expected_sequence')) is not int or body['expected_sequence'] != sequence:
        raise ValueError('画面已变化，请重新框选当前物体。')
    name = body.get('name')
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 100:
        raise ValueError('请填写 1–100 字的物体名称。')
    frame = observation['frames'][-1]
    height, width = len(frame), len(frame[0])
    corners = body.get('corners')
    if not isinstance(corners, list) or len(corners) != 2:
        raise ValueError('需要两个角点。')
    for p in corners:
        if (not isinstance(p, dict) or set(p) != {'x', 'y'} or
                type(p['x']) is not int or type(p['y']) is not int or
                not 0 <= p['x'] < width or not 0 <= p['y'] < height):
            raise ValueError('角点必须是画面内的整数坐标。')
    x0, x1 = sorted(p['x'] for p in corners)
    y0, y1 = sorted(p['y'] for p in corners)
    cells = [{'x': x, 'y': y, 'row': y, 'column': x, 'index': y*width+x,
              'color_index': frame[y][x]} for y in range(y0, y1+1) for x in range(x0, x1+1)]
    return {'name': name.strip(), 'kind': 'rectangle', 'status': 'human_annotation',
            'sequence': sequence, 'frame_index': len(observation['frames'])-1,
            'frame_sha256': hashlib.sha256(json.dumps(frame, separators=(',', ':')).encode()).hexdigest(),
            'level': observation['levels_completed'], 'width': width, 'height': height,
            'bounds_inclusive': {'x_min': x0, 'x_max': x1, 'y_min': y0, 'y_max': y1},
            'matrix_convention': 'frame[row=y][column=x]; flat index=row*width+column; zero based',
            'cells': cells, 'cell_count': len(cells)}
