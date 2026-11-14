"""Find a 25-action continuation from the abandoned level-6 state and replay it in the game's own logic."""
import sys
sys.path.insert(0, "/Users/dcw06/Desktop/AGI/.cache/bp35_play/solver")
from sim import Level, WIN, LOSE
from engine_util import new_level, act
from solve_general import gen
from l6_prefix import PREFIX, to_act, sim_state

lv = Level(6); L = new_level(6)
for tok in PREFIX:
    act(L, to_act(tok))
st = sim_state(L)
key = lambda s: (s[0], s[1], s[2], s[5])
parent, frontier, path = {key(st): None}, [st], None
while frontier and path is None:
    nxt = []
    for s in frontier:
        for a, ns, o in gen(lv, (s[0], s[1], s[2], 0, 0, s[5])):
            if o == LOSE: continue
            if o == WIN:
                path, cur = [a], key(s)
                while parent[cur] is not None:
                    cur, pa = parent[cur]; path.append(pa)
                path.reverse(); break
            k = key(ns)
            if k not in parent:
                parent[k] = (key(s), a); nxt.append(ns)
        if path: break
    frontier = nxt
print("continuation length:", len(path))
print(" ".join("A4" if a == ("R",) else "A3" if a == ("L",) else f"C({a[1]},{a[2]})" for a in path))
for i, a in enumerate(path, 1):
    win, lose = act(L, a)
    assert not lose, f"lost at step {i}"
    if win:
        print(f"game logic: WIN at continuation step {i} (total level-6 actions {16 + i})"); break
else:
    print("game logic: no win")
