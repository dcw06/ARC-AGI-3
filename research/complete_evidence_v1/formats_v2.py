"""Revised record formats (after the starting formats failed their size limits).

Lossless temporal compression
  M-key-v1   one keyframe (the board before the action, identical rows merged), then each returned frame
             as ordered changes. Identical frames are written once. Self-contained.
  M-ref-v1   the same, but the board before the action is written as its differences from the current
             board, which the reader already has. Exact, but only together with that current board.
Lossy regional input
  M-region-v1  the cells that have ever changed in that level so far ("state cells"), a window around the
             click, a padded box around what changed, then the ordered changes. Cells that never changed
             and lie outside the windows are not given.
Search description
  Q-key-v1   legal actions, the current board, and the last two responses as M-ref records.

Change syntax: "y:x1-x2=c" sets columns x1..x2 of row y to colour c; "y1-y2:" applies to each of those rows.
Board syntax (from formats.py): "y:c*n,..." gives a whole row as runs. Row 0 is the top, column 0 the left.
"""
import re

import numpy as np

from .formats import HEX, _action_text, board_lines, parse_board, rle_row

NOTE_COMMON = (
    'Boards are text. A board line "y:c*n,..." gives row y as runs: colour c (one hex digit) repeated n times, '
    'left to right; "a-b:" means rows a to b are identical. A change line "y:x1-x2=c" sets columns x1 to x2 of '
    'row y to colour c ("x=c" for one cell); "a-b:" applies it to rows a to b. Row 0 is the top, column 0 the '
    'left; ACTION6 clicks (x=column, y=row). Frames are the boards returned by one action, in order; each is '
    'given as its changes from the previous frame or from the board before the action, as stated. '
    '"net before>last" restates the total change from the board before the action to the last frame.')
NOTE_REF = (' "before vs current" lists where the board before that action differed from the current board; '
            'every other cell was the same as it is now.')
NOTE_REGION = (' This record is partial: "state cells" are the cells that have changed at some point in that '
               'level, with their colours before the action; "window" blocks give every cell of a small area. '
               'Cells not listed were not recorded here.')
READING_NOTES = {'M-key-v1': NOTE_COMMON, 'M-ref-v1': NOTE_COMMON + NOTE_REF,
                 'M-region-v1': NOTE_COMMON + NOTE_REGION}
CLICK_RADIUS, BOX_PAD, BOX_MAX_CELLS = 4, 2, 1024


def _merge(rows):
    """[(y, text)] in row order -> lines, merging consecutive rows with the same text."""
    lines, i = [], 0
    while i < len(rows):
        j = i
        while j + 1 < len(rows) and rows[j + 1][1] == rows[i][1] and rows[j + 1][0] == rows[j][0] + 1:
            j += 1
        label = '%d' % rows[i][0] if i == j else '%d-%d' % (rows[i][0], rows[j][0])
        lines.append('%s:%s' % (label, rows[i][1]))
        i = j + 1
    return lines


def _row_segments(target, wanted):
    """Runs of one colour in `target` that hold a wanted cell, trimmed to their first and last wanted cell."""
    out, x, n = [], 0, len(target)
    while x < n:
        end = x
        while end + 1 < n and target[end + 1] == target[x]:
            end += 1
        hits = np.flatnonzero(wanted[x:end + 1])
        if hits.size:
            a, b = x + int(hits[0]), x + int(hits[-1])
            out.append(('%d=%s' % (a, HEX[target[x]])) if a == b else '%d-%d=%s' % (a, b, HEX[target[x]]))
        x = end + 1
    return ','.join(out)


def cell_lines(target, wanted):
    """Lines giving the colour in `target` of every cell where `wanted` is true."""
    rows = [(y, _row_segments(target[y].tolist(), wanted[y])) for y in np.flatnonzero(wanted.any(axis=1)).tolist()]
    return _merge(rows)


def change_lines(reference, target):
    return cell_lines(target, reference != target)


def apply_lines(board, lines, known=None):
    """Apply change lines to a copy of `board`; mark the written cells in `known` if given."""
    out = board.copy()
    for line in lines:
        label, body = line.split(':')
        first, _, last = label.partition('-')
        for seg in body.split(','):
            span, colour = seg.split('=')
            a, _, b = span.partition('-')
            ys = slice(int(first), int(last or first) + 1)
            xs = slice(int(a), int(b or a) + 1)
            out[ys, xs] = HEX.index(colour)
            if known is not None:
                known[ys, xs] = True
    return out


def _delta(reference, target, name, versus):
    """Header and lines for `target`: changes from `reference`, or the full board when that is shorter."""
    full = ['%s %dx%d' % ((name,) + target.shape[::-1])] + board_lines(target, True)
    if reference is None or reference.shape != target.shape:
        return full
    n = int((reference != target).sum())
    if n == 0:
        return ['%s: same as %s' % (name, versus)]
    lines = ['%s vs %s: %d cells' % (name, versus, n)] + change_lines(reference, target)
    return lines if len('\n'.join(lines)) <= len('\n'.join(full)) else full


def frame_lines(before, frames, policy='F-all'):
    """F-all writes every returned frame. F-end writes only the last one and says how many were left out."""
    total = len(frames)
    if policy == 'F-end' and total > 1:
        skipped = 'frame 1/%d' % total if total == 2 else 'frames 1-%d/%d' % (total - 1, total)
        return [skipped + ': not included'] + _delta(before, frames[-1], 'frame %d/%d' % (total, total), 'before')
    lines, previous, i = [], before, 0
    last_vs_before = False
    while i < total:
        frame = frames[i]
        if frame.shape == previous.shape and np.array_equal(frame, previous):
            j = i
            while j + 1 < total and frames[j + 1].shape == previous.shape and np.array_equal(frames[j + 1], previous):
                j += 1
            what = 'before' if previous is before else 'previous'
            label = 'frame %d/%d' % (i + 1, total) if i == j else 'frames %d-%d/%d' % (i + 1, j + 1, total)
            lines.append('%s: same as %s' % (label, what))
            last_vs_before = previous is before
            i = j + 1
            continue
        name = 'frame %d/%d' % (i + 1, total)
        best = _delta(before, frame, name, 'before')
        vs_before = True
        if previous is not before:
            other = _delta(previous, frame, name, 'previous')
            if len('\n'.join(other)) <= len('\n'.join(best)):
                best, vs_before = other, False
        lines += best
        last_vs_before = vs_before or ' vs ' not in best[0]
        previous = frame
        i += 1
    if total > 1 and not last_vs_before and frames[-1].shape == before.shape:
        n = int((frames[-1] != before).sum())
        lines += (['net before>last: %d cells' % n] + change_lines(before, frames[-1])) if n else \
            ['net before>last: none']
    return lines


def _head(name, record, extra=''):
    return ['%s record=%s event=%d reset=%d level=%d frames=%d%s' % (
        name, record['memory_id'], record['event_seq'], record['reset_id'], record['level_observed'],
        len(record['response_frames']), extra), 'action=' + _action_text(record['action'])]


def _tail(record):
    return ['result state=%s level=%d legal=%s' % (
        record['state_after'], record['level_after'], ','.join(map(str, record['legal_after'])))]


def m_key(record, policy='F-all'):
    before = record['before_frame']
    return '\n'.join(_head('M-key-v1', record) + ['before %dx%d' % before.shape[::-1]] + board_lines(before, True)
                     + frame_lines(before, record['response_frames'], policy) + _tail(record))


def m_ref(record, current, policy='F-all'):
    before = record['before_frame']
    return '\n'.join(_head('M-ref-v1', record) + _delta(current, before, 'before', 'current')
                     + frame_lines(before, record['response_frames'], policy) + _tail(record))


def level_mask(records, level, shape):
    """Cells changed by any ordinary action in `level` among `records` (resets and level changes excluded)."""
    mask = np.zeros(shape, dtype=bool)
    for r in records:
        if r['level_observed'] != level or r['level_after'] != level or r['action']['id'] == 'RESET':
            continue
        previous = r['before_frame']
        for frame in r['response_frames']:
            if frame.shape == previous.shape == shape:
                mask |= frame != previous
            previous = frame
    return mask


def _window(board, x0, x1, y0, y1):
    rows = [(y, rle_row(board[y, x0:x1 + 1])) for y in range(y0, y1 + 1)]
    return ['window x=%d-%d y=%d-%d (runs start at x=%d)' % (x0, x1, y0, y1, x0)] + _merge(rows)


def m_region(record, history):
    """`history` is every completed record available at the decision (it includes `record`)."""
    before = record['before_frame']
    height, width = before.shape
    mask = level_mask(history, record['level_observed'], before.shape)
    lines = _head('M-region-v1', record, ' partial=yes')
    windows = []
    final = record['response_frames'][-1]
    if final.shape == before.shape and (final != before).any():
        ys, xs = np.nonzero(final != before)
        box = (max(int(xs.min()) - BOX_PAD, 0), min(int(xs.max()) + BOX_PAD, width - 1),
               max(int(ys.min()) - BOX_PAD, 0), min(int(ys.max()) + BOX_PAD, height - 1))
        if (box[1] - box[0] + 1) * (box[3] - box[2] + 1) <= BOX_MAX_CELLS:
            windows.append(box)
    if record['action']['x'] is not None:
        x, y = record['action']['x'], record['action']['y']
        click = (max(x - CLICK_RADIUS, 0), min(x + CLICK_RADIUS, width - 1),
                 max(y - CLICK_RADIUS, 0), min(y + CLICK_RADIUS, height - 1))
        if not any(b[0] <= click[0] and b[1] >= click[1] and b[2] <= click[2] and b[3] >= click[3] for b in windows):
            windows.append(click)
    for box in windows:
        lines += _window(before, *box)
    lines += ['state cells before: %d cells' % int(mask.sum())] + cell_lines(before, mask)
    return '\n'.join(lines + frame_lines(before, record['response_frames']) + _tail(record))


def q_key(initial_frame, legal_actions, done, window=2):
    current = done[-1]['response_frames'][-1] if done else initial_frame
    level = done[-1]['level_after'] if done else 0
    reset = done[-1]['reset_id'] if done else 0
    lines = ['Q-key-v1 next_event=%d reset=%d level=%d' % (len(done) + 1, reset, level),
             'legal_actions=' + ','.join(map(str, legal_actions)),
             'current board %dx%d' % current.shape[::-1]] + board_lines(current, True)
    recent = done[-window:] if window else []
    for offset, record in enumerate(recent, -len(recent)):
        lines += ['recent %d:' % offset] + m_ref(record, current).split('\n')
    return '\n'.join(lines)


# ---- decoders, used only to check what a text preserves ----

_FRAME = re.compile(r'^frames? (\d+)(?:-(\d+))?/(\d+)(.*)$')


def _blocks(text):
    """Split a record into (header line, body lines) blocks after the two head lines."""
    blocks = []
    for line in text.split('\n')[2:]:
        if line.startswith(('before', 'frame', 'net ', 'window', 'state cells', 'result')):
            blocks.append((line, []))
        else:
            blocks[-1][1].append(line)
    return blocks


def decode(text, current=None, shape=None):
    """Return (before, known_before, frames). For M-key and M-ref every cell is known.

    For M-region `known_before` marks the cells the text actually gives; other cells are zero.
    """
    before = known = None
    frames, previous = [], None
    for header, body in _blocks(text):
        if header.startswith('before'):
            if 'same as current' in header:
                before = current.copy()
            elif ' vs current' in header:
                before = apply_lines(current, body)
            else:
                before = parse_board(body)
            known = np.ones(before.shape, dtype=bool)
        elif header.startswith('window'):
            if before is None:
                before, known = np.zeros(shape, dtype=np.uint8), np.zeros(shape, dtype=bool)
            x0, x1, y0, y1 = map(int, re.findall(r'\d+', header)[:4])
            for line in body:
                label, runs = line.split(':')
                first, _, last = label.partition('-')
                cells = []
                for run in runs.split(','):
                    colour, count = run.split('*')
                    cells += [HEX.index(colour)] * int(count)
                before[int(first):int(last or first) + 1, x0:x1 + 1] = cells
                known[int(first):int(last or first) + 1, x0:x1 + 1] = True
        elif header.startswith('state cells'):
            if before is None:
                before, known = np.zeros(shape, dtype=np.uint8), np.zeros(shape, dtype=bool)
            before = apply_lines(before, body, known)
        elif header.startswith('frame'):
            first, last, _, rest = _FRAME.match(header).groups()
            if 'not included' in rest:
                continue
            previous = before if previous is None else previous
            if 'same as before' in rest:
                frame = before
            elif 'same as previous' in rest:
                frame = previous
            elif ' vs before' in rest:
                frame = apply_lines(before, body)
            elif ' vs previous' in rest:
                frame = apply_lines(previous, body)
            else:
                frame = parse_board(body)
            for _ in range(int(last or first) - int(first) + 1):
                frames.append(frame)
            previous = frame
    return before, known, frames
