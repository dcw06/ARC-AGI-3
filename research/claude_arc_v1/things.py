"""What is on a board, found from the cells alone: no game knowledge, no model.

ground   a connected region of one colour that covers a large part of the board (walls, floor, empty space)
thing    a connected group of the remaining cells, of any colours (touching diagonally counts)
look     a thing's shape and colours, the same whichever way it is turned or mirrored

Two things with the same look are the same kind of object as far as the board shows. Nothing here says what
anything does. This is a heuristic: a thing standing against another is seen as one, and a busy board gives
many things.

Inventory keeps, for one game, what has happened at each thing on the current level, again from the boards
alone: the last action at which a thing's own cells changed, or cells right beside it did.
"""
import hashlib

import numpy as np

GROUND_SHARE = 1 / 32      # a one-colour region this large is ground: 128 cells of a 64 by 64 board
TOO_BIG_SHARE = 1 / 8      # a "thing" this large is a patterned background, not an object: left out of listings
VIEW_MOVED_SHARE = 0.5     # if more of the board than this changes at once, the view moved: positions are lost
MAX_LOOKS, MAX_INSTANCES = 14, 6
MAX_SHAPES, MIN_SHAPE_CELLS = 8, 4
HEX = '0123456789abcdef'


def regions(board, same_colour=True, mask=None):
    """Connected regions as lists of (y, x). same_colour: neighbours must match in colour and touch by a
    side; otherwise any cells of `mask` that touch, diagonals included."""
    height, width = board.shape
    seen = np.zeros(board.shape, dtype=bool)
    if mask is not None:
        seen |= ~mask
    steps = ((1, 0), (-1, 0), (0, 1), (0, -1)) if same_colour else tuple(
        (dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx)
    out = []
    for y in range(height):
        for x in range(width):
            if seen[y, x]:
                continue
            colour, cells, todo = board[y, x], [], [(y, x)]
            seen[y, x] = True
            while todo:
                cy, cx = todo.pop()
                cells.append((cy, cx))
                for dy, dx in steps:
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < height and 0 <= nx < width and not seen[ny, nx] and (
                            not same_colour or board[ny, nx] == colour):
                        seen[ny, nx] = True
                        todo.append((ny, nx))
            out.append(cells)
    return out


def ground_mask(board):
    ground = np.zeros(board.shape, dtype=bool)
    least = board.size * GROUND_SHARE
    for cells in regions(board):
        if len(cells) >= least:
            ys, xs = zip(*cells)
            ground[list(ys), list(xs)] = True
    return ground


def look_of(patch):
    """One name for a patch (0 = not part of the thing, colour + 1 otherwise) under turns and mirror images."""
    forms = []
    for k in range(4):
        turned = np.rot90(patch, k)
        for form in (turned, np.fliplr(turned)):
            forms.append(repr(form.shape).encode() + form.tobytes())
    return hashlib.sha1(min(forms)).hexdigest()[:12]


def patch_of(board, cells):
    """(box, patch) of a group of cells: patch holds colour + 1 where the thing is and 0 elsewhere."""
    ys, xs = zip(*cells)
    y0, y1, x0, x1 = min(ys), max(ys), min(xs), max(xs)
    patch = np.zeros((y1 - y0 + 1, x1 - x0 + 1), dtype=np.uint8)
    for y, x in cells:
        patch[y - y0, x - x0] = int(board[y, x]) + 1
    return (x0, y0, x1, y1), patch


def described(box, patch):
    part = patch > 0
    return {'box': box, 'cells': int(part.sum()), 'colours': sorted({int(v) - 1 for v in patch[part]}),
            'look': look_of(patch)}


def things(board, known=None, floor=None):
    """[{'box': (x0, y0, x1, y1), 'cells': n, 'colours': [...], 'look': name}] for one board.

    known ({box: patch}, updated in place): things already seen on this level. One that still stands exactly
    where it was stays its own thing even when something else has moved against it; without this a piece
    standing beside an object would be read, for that moment, as one new object.

    floor (an array, updated in place; -1 = never ground): the colour each cell had when it was last part of
    ground on this level. A cell that still has that colour is still ground, so a pocket of floor that a
    piece has cut off from the rest does not turn into an object."""
    board = np.asarray(board)
    if board.ndim != 2:
        return []
    ground = ground_mask(board)
    if floor is not None and floor.shape == board.shape:
        floor[ground] = board[ground]
        ground = ground | (floor == board)
    free = ~ground
    out, present = [], {}
    for box, patch in list((known or {}).items()):
        x0, y0, x1, y1 = box
        part = patch > 0
        now = board[y0:y1 + 1, x0:x1 + 1]
        if now.shape == patch.shape and free[y0:y1 + 1, x0:x1 + 1][part].all() and (now[part] + 1 == patch[part]).all():
            out.append(described(box, patch))
            free[y0:y1 + 1, x0:x1 + 1][part] = False
            present[box] = patch
    for cells in regions(board, same_colour=False, mask=free):
        box, patch = patch_of(board, cells)
        out.append(described(box, patch))
        present[box] = patch
    if known is not None:       # only what stands on this board is remembered, so the memory stays small
        known.clear()
        known.update(present)
    return out


def form_of(mask):
    """(name, size, way up) of a shape given as a boolean mask cropped to its box.

    name is the same for a shape drawn larger (every cell a size-by-size block), turned or mirrored;
    way up tells two drawings of one shape apart when one is turned or mirrored."""
    height, width = mask.shape
    size = 1
    for k in range(min(height, width), 1, -1):
        if height % k == 0 and width % k == 0:
            small = mask[::k, ::k]
            if (np.kron(small, np.ones((k, k), dtype=bool)) == mask).all():
                size, mask = k, small
                break
    forms = []
    for k in range(4):
        turned = np.rot90(mask, k)
        for form in (turned, np.fliplr(turned)):
            forms.append(repr(form.shape).encode() + np.ascontiguousarray(form).tobytes())
    return hashlib.sha1(min(forms)).hexdigest()[:12], size, hashlib.sha1(forms[0]).hexdigest()[:8]


def alike(found, known):
    """Shapes that occur more than once on a board in different colours, sizes or turned.

    A shape here is all the cells of one colour inside one thing (so a pattern drawn on a panel counts, and
    the panel behind it does not). Filled rectangles and shapes of under four cells are left out: they match
    too easily to mean anything. Returns [{'copies': [...], 'differ_in': [...]}], fewest copies first."""
    groups = {}
    for thing in found:
        patch = known.get(thing['box'])
        if patch is None:
            continue
        x0, y0 = thing['box'][0], thing['box'][1]
        layers = [(int((patch == value).sum()), int(value)) for value in np.unique(patch) if value]
        biggest = max(layers)
        for cells, value in layers:
            if len(layers) > 1 and (cells, value) == biggest and cells * 2 >= thing['cells']:
                continue                               # the panel or frame the pattern is drawn on
            ys, xs = np.nonzero(patch == value)
            mask = (patch == value)[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            name, size, way = form_of(mask)
            if mask.all() or cells // (size * size) < MIN_SHAPE_CELLS:
                continue
            groups.setdefault(name, []).append({
                'in': thing.get('letter'), 'at': [x0 + int(xs.min()), y0 + int(ys.min()), x0 + int(xs.max()), y0 + int(ys.max())],
                'colour': HEX[value - 1] if value - 1 < 16 else '?', 'size': size, '_way': way})
    out = []
    for copies in groups.values():
        differ = [name for name, key in (('colour', 'colour'), ('size', 'size'), ('turn', '_way'))
                  if len({c[key] for c in copies}) > 1]
        if len(copies) < 2 or not differ:
            continue
        first = copies[0]['_way']
        shown = [{**{k: v for k, v in c.items() if k != '_way'}, 'turned': c['_way'] != first} for c in copies[:MAX_INSTANCES]]
        row = {'copies': shown, 'differ_in': differ}
        if len(copies) > MAX_INSTANCES:
            row['more_copies'] = len(copies) - MAX_INSTANCES
        out.append(row)
    out.sort(key=lambda row: (len(row['copies']) + row.get('more_copies', 0), row['copies'][0]['at'][1], row['copies'][0]['at'][0]))
    return out[:MAX_SHAPES]


def letters(n):
    """A, B, ..., Z, AA, AB, ... for look number n (from 0)."""
    out = ''
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        out = chr(65 + r) + out
    return out


class Inventory:
    """The things of one game: a letter for every look seen, and what happened at each thing on this level."""

    def __init__(self):
        self.names = {}          # look -> letter, for the whole game
        self.changed = {}        # (look, box) -> id of the last action at which the thing's own cells changed
        self.beside = {}         # (look, box) -> id of the last action at which cells right beside it changed
        self.known = {}          # box -> patch of every thing seen on this level (see things)
        self.floor = None        # the colour each cell had when it was last ground on this level (see things)
        self.view_moved = None   # id of the last action that changed most of the board
        self.earlier = set()     # looks seen on the levels already completed
        self.here = set()        # looks seen on this level so far
        self.levels_done = 0     # how many levels have been completed

    def new_level(self):
        self.changed.clear()
        self.beside.clear()
        self.known.clear()
        self.floor = None
        self.view_moved = None

    def next_level(self):
        """A level was completed: what was seen on it counts from now on as seen before."""
        self.earlier |= self.here
        self.here = set()
        self.levels_done += 1
        self.new_level()

    def find(self, board):
        board = np.asarray(board)
        if self.floor is None or self.floor.shape != board.shape:
            self.floor = np.full(board.shape, -1, dtype=np.int16)
        found = things(board, self.known, self.floor)
        self.here.update(thing['look'] for thing in found)
        return found

    def name(self, look):
        if look not in self.names:
            self.names[look] = letters(len(self.names))
        return self.names[look]

    def observe(self, before, frames, tid, click=None, ignore=None):
        """Account for one action: `before` is the board it was taken on, `frames` what the game returned."""
        base = np.asarray(before)
        if base.ndim != 2:
            return
        diff = np.zeros(base.shape, dtype=bool)
        for frame in frames:
            frame = np.asarray(frame)
            if frame.shape == base.shape:
                diff |= frame != base
        if ignore is not None and ignore.shape == diff.shape:
            diff &= ~ignore
        if diff.mean() > VIEW_MOVED_SHARE:
            self.new_level()
            self.view_moved = tid
            last = np.asarray(frames[-1])
            if last.ndim == 2:
                # What the new view shows has been seen on this level, also when no request is built on it
                # (saved actions repeated at a resume). Nothing else is remembered about it here.
                self.here.update(thing['look'] for thing in things(last))
            return
        if click is not None and 0 <= click[1] < base.shape[0] and 0 <= click[0] < base.shape[1]:
            diff[click[1], click[0]] = True          # acting on a thing counts as something happening at it
        if not diff.any():
            return
        near = diff.copy()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                near |= np.roll(np.roll(diff, dy, axis=0), dx, axis=1)
        for thing in self.find(base):                # the things as they stood when the action was taken
            x0, y0, x1, y1 = thing['box']
            key = (thing['look'], thing['box'])
            if diff[y0:y1 + 1, x0:x1 + 1].any():
                self.changed[key] = tid
            elif near[y0:y1 + 1, x0:x1 + 1].any():
                self.beside[key] = tid
        last = np.asarray(frames[-1])
        if last.shape == base.shape:
            for thing in self.find(last):            # things that moved or appeared: where they are now
                x0, y0, x1, y1 = thing['box']
                if diff[y0:y1 + 1, x0:x1 + 1].any():
                    self.changed[(thing['look'], thing['box'])] = tid

    def rows(self, board):
        """Every thing on the board that is not too big to be an object, with its letter and what happened at it."""
        board = np.asarray(board)
        out = []
        for thing in self.find(board):
            if thing['cells'] > board.size * TOO_BIG_SHARE:
                continue
            key = (thing['look'], thing['box'])
            out.append({**thing, 'letter': self.name(thing['look']),
                        'changed_at': self.changed.get(key), 'beside_change_at': self.beside.get(key)})
        return out

    def alike(self, board):
        """Shapes on the board that recur in another colour, size or turn (see alike)."""
        return alike(self.rows(board), self.known)

    def listing(self, board, notes=None, mark_new=False):
        """What the model is shown: looks with their instances, rarest looks first, within fixed limits.

        mark_new: on a level after the first, mark every look that was on no earlier level."""
        groups = {}
        for row in self.rows(board):
            groups.setdefault(row['letter'], []).append(row)
        ordered = sorted(groups.items(), key=lambda item: (len(item[1]), item[1][0]['cells'], item[0]))
        looks = []
        for letter, rows in ordered[:MAX_LOOKS]:
            rows = sorted(rows, key=lambda r: (r['box'][1], r['box'][0]))
            instances = []
            for row in rows[:MAX_INSTANCES]:
                item = {'at': list(row['box'])}
                if row['changed_at']:
                    item['changed_at'] = row['changed_at']
                if row['beside_change_at']:
                    item['beside_change_at'] = row['beside_change_at']
                if not row['changed_at'] and not row['beside_change_at']:
                    item['untouched'] = True
                instances.append(item)
            look = {'look': letter, 'colours': ''.join(HEX[c] if c < 16 else '?' for c in rows[0]['colours']),
                    'cells': rows[0]['cells'], 'instances': instances}
            if len(rows) > MAX_INSTANCES:
                look['more_instances'] = len(rows) - MAX_INSTANCES
                look['more_untouched'] = sum(not r['changed_at'] and not r['beside_change_at'] for r in rows[MAX_INSTANCES:])
            if notes and letter in notes:
                look['does'] = notes[letter]
            if mark_new and self.levels_done and rows[0]['look'] not in self.earlier:
                look['new'] = True
            looks.append(look)
        value = {'looks': looks}
        if len(ordered) > MAX_LOOKS:
            value['looks_not_listed'] = len(ordered) - MAX_LOOKS
            if mark_new and self.levels_done:
                value['new_looks_not_listed'] = sum(rows[0]['look'] not in self.earlier for _, rows in ordered[MAX_LOOKS:])
        if self.view_moved:
            value['view_moved_at'] = self.view_moved
        return value
