"""Was the level-6 state that all three runs abandoned actually winnable? Uses the bp35 logic port that was
validated against the game (local only; derived from the game's source)."""
import sys, time
sys.path.insert(0, "/Users/dcw06/Desktop/AGI/.cache/bp35_play/solver")
from sim import Level, WIN, LOSE, DYNAMIC
from engine_util import new_level, act, snapshot
from solve_general import gen

PREFIX = "A4 A4 A4 A4 A4 C(39,33) C(27,29) A3 A3 A4 A4 A3 A3 C(33,33) A3 A3".split()

def to_act(tok):
    if tok == "A4": return ("R",)
    if tok == "A3": return ("L",)
    x, y = tok[2:-1].split(","); return ("C", int(x), int(y))

def sim_state(L):
    s = snapshot(L)
    dyn = {c: nm for c, ns in s["cells"].items() for nm in ns if nm in DYNAMIC}
    return (s["P"], s["g"], s["C"], s["w"], 0, frozenset(dyn.items()))

def bfs_from(lv, st, maxdepth=70, cap=3_000_000):
    key = lambda s: (s[0], s[1], s[2], s[5])
    seen, frontier = {key(st)}, [st]
    for depth in range(1, maxdepth + 1):
        nxt = []
        for s in frontier:
            for a, ns, o in gen(lv, (s[0], s[1], s[2], 0, 0, s[5])):
                if o == LOSE: continue
                if o == WIN: return depth, len(seen)
                k = key(ns)
                if k not in seen:
                    seen.add(k); nxt.append(ns)
        frontier = nxt
        if not frontier: return None, len(seen)      # search space exhausted: no win without undo
        if len(seen) > cap: return "cap", len(seen)
    return "depth", len(seen)

lv = Level(6)
L = new_level(6)
states = [sim_state(L)]
for tok in PREFIX:
    win, lose = act(L, to_act(tok))
    assert not win and not lose, tok
    states.append(sim_state(L))
print("after the 16 shared actions: player", states[-1][0], "gravity_up", states[-1][1], "camera", states[-1][2])
rem = []
for j, st in enumerate(states):
    t0 = time.time(); d, n = bfs_from(lv, st)
    rem.append(d)
    print(f"after {j:2} actions ({PREFIX[j-1] if j else 'start':9}): fewest further actions to win = {d}  (states searched {n:,}, {time.time()-t0:.0f}s)", flush=True)
print("\ncost to finish from the abandoned state (16 actions in):")
print("  restart: 1 +", rem[0], "=", 1 + rem[0])
best = min(((16 - j) + r, j) for j, r in enumerate(rem) if isinstance(r, int))
print("  undo back to the state after action", best[1], "then play on:", 16 - best[1], "+", rem[best[1]], "=", best[0])
print("  play on without undo:", rem[16])
