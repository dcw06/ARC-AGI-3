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
# Reading instructions, version 2 (2026-11-14). The record formats are unchanged. Version 1 above is kept as
# it was so that earlier inputs can be rebuilt exactly. Changes: a range may cover cells that do not change;
# the cell count is defined; the "net before>last" block is optional; M-ref says how the earlier board is
# rebuilt from the current board. A longer first wording put input A at 2,085 tokens, over the 2,048
# allowance (kept in frozen_v2_draft1_over_limit/); this wording is shorter and says the same things.
NOTE_COMMON_V2 = (
    'Boards are text. A board line "y:c*n,..." gives row y as runs: colour c (one hex digit) repeated n times, '
    'left to right; "a-b:" means rows a to b are identical. A change line "y:x1-x2=c" sets every cell in '
    'columns x1 to x2 of row y to colour c ("x=c" for one cell); "a-b:" applies it to rows a to b. A range may '
    'include cells that already had that colour. Row 0 is the top, column 0 the left; ACTION6 clicks '
    '(x=column, y=row). Frames are the boards returned by one action, in order. A frame header names its '
    'reference ("vs before": the board before the action; "vs previous": the previous frame) and counts the '
    'cells whose colour differs from that reference, which can be fewer than the cells the lines cover. '
    'A "net before>last" block is optional: it appears only when the last frame is "vs previous", and restates '
    'the change from the board before the action to the last frame.')
NOTE_REF_V2 = (' The board before the action is not printed. "before vs current: N cells" gives it relative to '
               'the current board: take the current board and apply the lines. N counts the cells that differ; '
               'every cell the lines do not set had the same colour as on the current board.')
READING_NOTES_V2 = {'M-key-v1': NOTE_COMMON_V2, 'M-ref-v1': NOTE_COMMON_V2 + NOTE_REF_V2}
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


# ---- version 2 of B (M-ref-v2): every record states how its starting board is given ----

NOTE_FROM_CURRENT_V3 = (
    ' A record marked "start board: from current" does not print its board before the action. Its "before vs '
    'current: N cells" lines give that board relative to the current board named in the pack header: take the '
    'current board and apply the lines. N counts the cells that differ; every cell the lines do not set had '
    'the same colour as on the current board. "before: same as current" means no cell differs.')
NOTE_FULL_V3 = (' A record marked "start board: full" prints its board before the action in full, as board lines '
                'under "before"; it does not depend on the current board.')


def m_ref2(record, current):
    """M-ref-v2: as M-ref-v1, plus a line saying whether the starting board is rebuilt from the current
    board or printed in full. The rule for choosing between the two is unchanged (whichever is shorter)."""
    before = record['before_frame']
    block = _delta(current, before, 'before', 'current')
    mode = 'full' if block[0].startswith('before %d' % before.shape[1]) else 'from current'
    return '\n'.join(_head('M-ref-v2', record) + ['start board: ' + mode] + block
                     + frame_lines(before, record['response_frames']) + _tail(record))


def start_mode(text):
    return text.split('\n')[2].split(': ', 1)[1]


def pack_b2(game, run, decision, chosen, texts):
    """Complete older-memory section for B version 2. Instructions name only the modes present; a pack
    with both kinds of record carries both paragraphs, each tied to its own marker."""
    events = [r['event_seq'] for r in chosen]
    many = len(events) > 1
    modes = {start_mode(t) for t in texts}
    lines = ['== OLDER MEMORY ==',
             'Source: game %s, saved run %s, action%s %s (transition%s %s). %s, selected by rule.' % (
                 game, run, 's' if many else '', ' and '.join(map(str, events)), 's' if many else '',
                 ', '.join('t%d' % e for e in events), '%d records' % len(events) if many else 'One record')]
    if 'from current' in modes:
        lines.append('In this pack "current" means the current board given above, observation o%d.' % decision)
    note = NOTE_COMMON_V2 + (NOTE_FROM_CURRENT_V3 if 'from current' in modes else '') + (NOTE_FULL_V3 if 'full' in modes else '')
    return '\n'.join(lines + [note, '', '\n\n'.join(texts)])


# ---- Q-key-v2: lossless description with shift-coded changes (investigation; version 1 is unchanged) ----

MAX_SHIFT = 8


def shifted(board, dy, dx):
    """`board` moved down by dy rows and right by dx columns; cells with no source keep their old value."""
    out = board.copy()
    h, w = board.shape
    out[max(dy, 0):h + min(dy, 0), max(dx, 0):w + min(dx, 0)] = board[max(-dy, 0):h + min(-dy, 0), max(-dx, 0):w + min(-dx, 0)]
    return out


def _shift_from(header, reference):
    found = re.search(r'shifted dx=(-?\d+) dy=(-?\d+)', header)
    return shifted(reference, int(found.group(2)), int(found.group(1))) if found else reference


def _delta_shift(reference, target, name, versus):
    """Like _delta, but may first move the reference by a whole number of cells when that is shorter."""
    best = _delta(reference, target, name, versus)
    if reference is None or reference.shape != target.shape:
        return best
    plain = int((reference != target).sum())
    if plain < 40:
        return best
    options = []
    for dy in range(-MAX_SHIFT, MAX_SHIFT + 1):
        for dx in range(-MAX_SHIFT, MAX_SHIFT + 1):
            if dy or dx:
                options.append((int((shifted(reference, dy, dx) != target).sum()), abs(dy) + abs(dx), dy, dx))
    n, _, dy, dx = min(options)
    if n < plain:
        moved = shifted(reference, dy, dx)
        lines = ['%s vs %s shifted dx=%d dy=%d: %d cells' % (name, versus, dx, dy, n)] + change_lines(moved, target)
        if len('\n'.join(lines)) < len('\n'.join(best)):
            return lines
    return best


def frame_lines_q2(before, frames, current):
    """Frames for a recent response: each against the board before, the previous frame or the current
    board, with or without a shift, whichever text is shortest."""
    lines, previous, total, i = [], before, len(frames), 0
    while i < total:
        frame = frames[i]
        if previous is not before and frame.shape == previous.shape and np.array_equal(frame, previous):
            j = i  # a run of frames identical to the one before them is written once
            while j + 1 < total and frames[j + 1].shape == previous.shape and np.array_equal(frames[j + 1], previous):
                j += 1
            lines.append(('frame %d/%d' % (i + 1, total) if i == j else 'frames %d-%d/%d' % (i + 1, j + 1, total))
                         + ': same as previous')
            i = j + 1
            continue
        name = 'frame %d/%d' % (i + 1, total)
        if frame.shape == current.shape and np.array_equal(frame, current):
            lines.append(name + ': same as current')
        else:
            options = [_delta_shift(before, frame, name, 'before'), _delta_shift(current, frame, name, 'current')]
            if previous is not before:
                options.append(_delta_shift(previous, frame, name, 'previous'))
            lines += min(options, key=lambda o: len('\n'.join(o)))
        previous = frame
        i += 1
    return lines


def recent_q2(record, current):
    before = record['before_frame']
    return '\n'.join(_head('recent', record) + _delta_shift(current, before, 'before', 'current')
                     + frame_lines_q2(before, record['response_frames'], current) + _tail(record))


def q_key2(initial_frame, legal_actions, done, window=2):
    current = done[-1]['response_frames'][-1] if done else initial_frame
    level = done[-1]['level_after'] if done else 0
    reset = done[-1]['reset_id'] if done else 0
    lines = ['Q-key-v2 next_event=%d reset=%d level=%d' % (len(done) + 1, reset, level),
             'legal_actions=' + ','.join(map(str, legal_actions)),
             'current board %dx%d' % current.shape[::-1]] + board_lines(current, True)
    for offset, record in enumerate(done[-window:] if window else [], -min(window, len(done))):
        lines += ['recent %d:' % offset, recent_q2(record, current)]
    return '\n'.join(lines)


# ---- decoders, used only to check what a text preserves ----

_FRAME = re.compile(r'^frames? (\d+)(?:-(\d+))?/(\d+)(.*)$')


def _blocks(text):
    """Split a record into (header line, body lines) blocks after the two head lines."""
    blocks = []
    for line in text.split('\n')[2:]:
        if line.startswith(('before', 'frame', 'net ', 'window', 'state cells', 'result', 'start board')):
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
                before = apply_lines(_shift_from(header, current), body)
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
            elif 'same as current' in rest:
                frame = current
            elif ' vs before' in rest:
                frame = apply_lines(_shift_from(rest, before), body)
            elif ' vs previous' in rest:
                frame = apply_lines(_shift_from(rest, previous), body)
            elif ' vs current' in rest:
                frame = apply_lines(_shift_from(rest, current), body)
            else:
                frame = parse_board(body)
            for _ in range(int(last or first) - int(first) + 1):
                frames.append(frame)
            previous = frame
    return before, known, frames
