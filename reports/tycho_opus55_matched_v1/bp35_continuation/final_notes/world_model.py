"""World model: tile-based gravity platformer with vertical scrolling camera.
See notes/world_model.md for prose. Rendering rules live in tiles.py; per-level world maps
(stitched from observed frames, initial tile types) live in maps/level_<L>.json (python build_maps.py).
"""
from dataclasses import dataclass, field
import json, os

import numpy as np
import wmlib
import tiles as T

UNKNOWN = wmlib.UNKNOWN
TRANSITION_RETURNS_NEW_STATE = True

_BASES = {}


@dataclass
class State:
    level: int
    player: tuple            # (j, k) tile
    facing: str              # 'R' or 'L'
    grav: int                # -1 = up, +1 = down
    mods: dict               # (j,k) -> code overrides of base map
    bar: int                 # actions taken this level (row 63 purple bar)
    status: str = "ongoing"  # ongoing | level_complete | game_over
    history: tuple = ()      # undo stack of (player, facing, grav, mods-items, status)


def _load_map(level):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'maps', f'level_{level}.json')
    out = {}
    if os.path.exists(path):
        try:
            d = json.load(open(path))
            for key, v in d['tiles'].items():
                j, k = key.split(',')
                out[(int(j), int(k))] = v
        except Exception:
            out = {}
    return out


def _base(level):
    return _BASES.get(level, {})


def tile(s, jk):
    if jk in s.mods:
        return s.mods[jk]
    return _base(s.level).get(jk, 'U')


def cam_of(s):
    j = s.player[0]
    return 6 * j if s.grav < 0 else 6 * j + 10


def init_state(grid0: np.ndarray, level: int) -> State:
    seen, player = T.classify_screen(grid0, 0)
    base = _load_map(level)
    base.update(seen)  # the actual start frame wins
    _BASES[level] = base
    if player is None:
        player = (0, 1)
    # facing from yellow pixel side
    j, k = player
    r0 = 36 + 6 * j + 2
    c0 = 12 + 6 * k + 1
    facing = 'R'
    if 0 <= r0 < 63 and grid0[r0, c0 + 1] == 11:
        facing = 'L'
    bar = int((grid0[63] == 15).sum())
    return State(level=level, player=player, facing=facing, grav=-1, mods={}, bar=bar)


def _snapshot(s):
    return (s.player, s.facing, s.grav, tuple(sorted(s.mods.items())), s.status)


def _settle(s):
    """Move player in gravity direction until blocked; pink -> win; hazard face -> death."""
    j, k = s.player
    for _ in range(200):
        if tile(s, (j, k)) == 'P':
            s.player = (j, k)
            s.status = 'level_complete'
            return
        nxt = (j + s.grav, k)
        if tile(s, nxt) in T.PASSABLE:
            j = j + s.grav
        else:
            break
    s.player = (j, k)
    if tile(s, (j, k)) == 'P':
        s.status = 'level_complete'
        return
    # hazard faces: HD directly above, HU directly below
    # only a face lying in the gravity direction kills (observed: resting with gravity up just
    # above an up-facing hazard is safe, L5 turn 15)
    if (s.grav < 0 and tile(s, (j - 1, k)) == 'HD') or (s.grav > 0 and tile(s, (j + 1, k)) == 'HU'):
        s.status = 'game_over'


def transition(state: State, action: dict) -> State:
    s = wmlib.clone(state)
    if s.status != 'ongoing':
        return s
    a = action["action"]
    if a == 'ACTION7':
        s.bar += 1
        if s.history:
            p, f, g, mods, st = s.history[-1]
            s.player, s.facing, s.grav, s.mods, s.status = p, f, g, dict(mods), st
            s.history = s.history[:-1]
        return s
    snap = _snapshot(s)
    s.bar += 1
    if a in ('ACTION3', 'ACTION4'):
        dk = -1 if a == 'ACTION3' else 1
        s.facing = 'L' if dk < 0 else 'R'
        j, k = s.player
        if tile(s, (j, k + dk)) in T.PASSABLE:
            s.player = (j, k + dk)
        _settle(s)
    elif a == 'ACTION6':
        r, c = action.get("row"), action.get("col")
        if r is not None and c is not None and 0 <= r < 63:
            jk = T.tile_of(r + cam_of(s), c)
            t = tile(s, jk)
            if jk != s.player:
                if t == 'G':
                    s.mods[jk] = 'O'
                elif t == 'C':
                    s.mods[jk] = 'X'
                elif t == 'X':
                    s.mods[jk] = 'C'
                elif t == 'R':
                    s.mods[jk] = 'O'
                    s.grav = -s.grav
        _settle(s)
    else:
        _settle(s)
    s.history = s.history + (snap,)
    return s


def _tiles_view(s):
    base = _base(s.level)
    cam = cam_of(s)
    j0 = (cam - 36) // 6 - 1
    j1 = (cam + 63 - 36) // 6 + 1
    out = {}
    for j in range(j0, j1 + 1):
        for k in range(T.KMIN - 1, T.KMAX + 2):
            jk = (j, k)
            v = s.mods.get(jk, base.get(jk))
            if v is not None:
                out[jk] = v
    return out


def render(state: State) -> np.ndarray:
    s = state
    return T.render(_tiles_view(s), cam_of(s), s.player, s.facing, s.bar)


def outcome(state: State) -> str:
    return state.status


def actions(state: State) -> list:
    acts = [{"action": "ACTION3", "row": None, "col": None},
            {"action": "ACTION4", "row": None, "col": None}]
    cam = cam_of(state)
    for (j, k), v in _tiles_view(state).items():
        if v in ('G', 'C', 'X', 'R'):
            r = 36 + 6 * j + 3 - cam
            c = 12 + 6 * k + 3
            if 0 <= r < 63 and 0 <= c < 64:
                acts.append({"action": "ACTION6", "row": r, "col": c})
    return acts


def planner_key(state: State):
    return (state.player, state.facing, state.grav, tuple(sorted(state.mods.items())), state.status)


def subgoals(state: State) -> list:
    return [lambda s: outcome(s) == "level_complete"]


def heuristic(state: State) -> float:
    base = _base(state.level)
    goals = [jk for jk, v in base.items() if v == 'P']
    if not goals:
        return 0
    j, k = state.player
    return min(abs(k - gk) for gj, gk in goals)
