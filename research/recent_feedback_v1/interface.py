"""An optional factual summary derived exclusively from the displayed prompt."""
import base64
from copy import deepcopy
from functools import lru_cache
import json

from certification.phase4_multimodal_preflight_v3.images import grid_from_png

VARIANTS = ('recent_raw', 'recent_summary')
SUMMARY_BYTE_LIMIT = 4096
NOTE = ('Computed from the same last two displayed transitions only. Grid equality does not prove hidden-state '
        'equality; a visual change does not establish progress. No control meaning or recommended action is supplied.')


@lru_cache(maxsize=64)
def image_grid(url):
    prefix = 'data:image/png;base64,'
    if type(url) is not str or not url.startswith(prefix):
        raise ValueError('only embedded board PNGs are allowed')
    grid = grid_from_png(base64.b64decode(url[len(prefix):], validate=True), cell=7)
    if len(grid) != 64 or any(len(row) != 64 for row in grid):
        raise ValueError('expected 448px board-only image')
    return tuple(tuple(row) for row in grid)


def displayed_history(body):
    """Parse the unchanged baseline's text/image sequence, without reading logs."""
    content = body['messages'][1]['content']
    meta = json.loads(content[0]['text'])
    step = meta['step']
    if type(step) is not int or not 0 <= step < 24:
        raise ValueError('decision step')
    count = min(step, 2)
    if len(content) != 5+5*count:
        raise ValueError('unexpected baseline content layout')
    if content[-2] != {'type': 'text', 'text': 'Current image; choose the next action here:'}:
        raise ValueError('current image label differs')
    current = image_grid(content[-1]['image_url']['url'])
    records = []
    for i in range(count):
        offset = 3+5*i
        info = json.loads(content[offset]['text'])
        if (set(info) != {'historical_step', 'action', 'before_state', 'after_state', 'after_levels_completed'} or
                type(info['historical_step']) is not int or info['historical_step'] != step-count+i or
                content[offset+1] != {'type': 'text', 'text': 'Historical before:'} or
                content[offset+3] != {'type': 'text', 'text': 'Historical after:'}):
            raise ValueError('historical display binding differs')
        before = image_grid(content[offset+2]['image_url']['url'])
        after = image_grid(content[offset+4]['image_url']['url'])
        records.append((info, before, after))
    return step, current, records


def recent_summary(body):
    step, current, records = displayed_history(body)
    rows = []
    for info, before, after in records:
        changed = [(x, y) for y in range(64) for x in range(64) if before[y][x] != after[y][x]]
        bbox = ([min(x for x, y in changed), min(y for x, y in changed),
                 max(x for x, y in changed), max(y for x, y in changed)] if changed else None)
        rows.append(dict(deepcopy(info), changed_cell_count=len(changed), changed_bbox_xyxy_inclusive=bbox,
                         before_grid_equals_current=before == current, after_grid_equals_current=after == current))
    return {'schema': 'recent_feedback_summary_v1', 'decision_step': step, 'qualification': NOTE,
            'transitions': rows}


def request_for_variant(body, variant):
    if variant not in VARIANTS:
        raise ValueError('unknown feedback variant')
    result = deepcopy(body)
    if variant == 'recent_summary':
        text = json.dumps(recent_summary(body), sort_keys=True, separators=(',', ':'), allow_nan=False)
        if len(text.encode('utf-8')) > SUMMARY_BYTE_LIMIT:
            raise ValueError('summary exceeds frozen byte budget; no silent truncation')
        result['messages'][1]['content'].append({'type': 'text', 'text': text})
    return result
