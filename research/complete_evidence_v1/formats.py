"""Text formats from protocol Appendix B, with decoders so every cell can be checked.

M-rle-v1   each row as ordered colour*run_length pairs; nothing is dropped.
M-rle-v1r  the same, but consecutive identical rows are written once as "first-last:" (candidate compact
           format; still exact).
M-diff-v1  only the cells that changed between adjacent frames, one per entry; unchanged cells are absent.
Q-exec-rle-v1  the search description: legal actions, the last two completed responses and the current board.

Frame policy: F-all keeps every returned frame; F-end keeps only the last returned frame.
Colours are one hexadecimal digit (0-9, A-F). Rows run top to bottom, cells left to right, (x, y) = (column, row).
"""
import numpy as np

HEX = '0123456789ABCDEF'
READING_NOTE = (
    'Boards are text. Each line is "row:" then runs "colour*count" from left to right; colour is one hex digit, '
    'count is how many cells in a row have it. A line "a-b:" gives rows a to b, which are identical. '
    'Row 0 is the top, column 0 the left; ACTION6 clicks (x=column, y=row).')


def rle_row(row):
    out, start = [], 0
    row = [int(v) for v in row]
    for i in range(1, len(row) + 1):
        if i == len(row) or row[i] != row[start]:
            out.append('%s*%d' % (HEX[row[start]], i - start))
            start = i
    return ','.join(out)


def board_lines(frame, merge_rows=False):
    rows = [rle_row(r) for r in np.asarray(frame)]
    if not merge_rows:
        return ['%d:%s' % (y, r) for y, r in enumerate(rows)]
    lines, start = [], 0
    for y in range(1, len(rows) + 1):
        if y == len(rows) or rows[y] != rows[start]:
            label = '%d' % start if y - 1 == start else '%d-%d' % (start, y - 1)
            lines.append('%s:%s' % (label, rows[start]))
            start = y
    return lines


def parse_board(lines):
    rows = {}
    for line in lines:
        label, body = line.split(':')
        cells = []
        for run in body.split(','):
            colour, count = run.split('*')
            cells += [HEX.index(colour)] * int(count)
        first, _, last = label.partition('-')
        for y in range(int(first), int(last or first) + 1):
            rows[y] = cells
    return np.array([rows[y] for y in range(len(rows))], dtype=np.uint8)


def _action_text(action):
    if action['x'] is not None:
        return '%s x=%d y=%d' % (action['id'], action['x'], action['y'])
    return action['id']


def _frames(record, policy):
    frames = record['response_frames']
    if policy == 'F-end':
        return [(len(frames), frames[-1])]
    return list(enumerate(frames, 1))


def m_rle(record, policy='F-all', merge_rows=False):
    name = 'M-rle-v1r' if merge_rows else 'M-rle-v1'
    lines = ['%s record=%s event=%d reset=%d level=%d frames=%s' % (
        name, record['memory_id'], record['event_seq'], record['reset_id'], record['level_observed'], policy),
        'action=' + _action_text(record['action']),
        'before %dx%d' % record['before_frame'].shape[::-1]]
    lines += board_lines(record['before_frame'], merge_rows)
    total = len(record['response_frames'])
    for index, frame in _frames(record, policy):
        lines.append('frame %d/%d %dx%d' % ((index, total) + frame.shape[::-1]))
        lines += board_lines(frame, merge_rows)
    lines.append('result state=%s level=%d legal=%s' % (
        record['state_after'], record['level_after'], ','.join(map(str, record['legal_after']))))
    return '\n'.join(lines)


def parse_m_rle(text):
    """Return (before, {frame_index: frame}) from an M-rle text."""
    boards, current = [], None
    for line in text.split('\n')[2:]:
        if line.startswith(('before', 'frame')):
            current = []
            boards.append((line, current))
        elif line.startswith('result'):
            break
        else:
            current.append(line)
    before = parse_board(boards[0][1])
    frames = {int(h.split()[1].split('/')[0]): parse_board(b) for h, b in boards[1:]}
    return before, frames


def m_diff(record, policy='F-all'):
    """Cells that changed, per adjacent frame pair, sorted by row then column: "y,x:old>new"."""
    lines = ['M-diff-v1 record=%s event=%d reset=%d level=%d frames=%s' % (
        record['memory_id'], record['event_seq'], record['reset_id'], record['level_observed'], policy),
        'action=' + _action_text(record['action'])]
    previous, total = record['before_frame'], len(record['response_frames'])
    for index, frame in _frames(record, policy):
        if frame.shape != previous.shape:
            lines.append('frame %d/%d size changed to %dx%d' % ((index, total) + frame.shape[::-1]))
            lines += board_lines(frame)
        else:
            ys, xs = np.nonzero(frame != previous)
            lines.append('frame %d/%d changes=%d' % (index, total, len(ys)))
            if len(ys):
                lines.append(' '.join('%d,%d:%s>%s' % (y, x, HEX[previous[y, x]], HEX[frame[y, x]])
                                      for y, x in zip(ys.tolist(), xs.tolist())))
        previous = frame
    lines.append('result state=%s level=%d legal=%s' % (
        record['state_after'], record['level_after'], ','.join(map(str, record['legal_after']))))
    return '\n'.join(lines)


def q_exec(initial_frame, legal_actions, records, policy='F-all', window=2, merge_rows=False):
    """Search description at a decision. `records` are the completed records so far, in order.

    The current board is the last frame of the latest response, so it is written once, there.
    """
    recent = records[-window:] if window else []
    lines = ['Q-exec-rle-v1%s next_event=%d frames=%s' % ('r' if merge_rows else '', len(records) + 1, policy),
             'legal_actions=' + ','.join(map(str, legal_actions))]
    if not recent:
        board = records[-1]['response_frames'][-1] if records else initial_frame
        lines.append('current board %dx%d' % board.shape[::-1])
        lines += board_lines(board, merge_rows)
        return '\n'.join(lines)
    for offset, record in enumerate(recent, -len(recent)):
        total = len(record['response_frames'])
        lines.append('response %d: action=%s reset=%d level=%d returned_frames=%d' % (
            offset, _action_text(record['action']), record['reset_id'], record['level_observed'], total))
        for index, frame in _frames(record, policy):
            is_current = offset == -1 and index == total
            lines.append('frame %d/%d %dx%d%s' % ((index, total) + frame.shape[::-1]
                                                  + (' (current board)' if is_current else '',)))
            lines += board_lines(frame, merge_rows)
    return '\n'.join(lines)
