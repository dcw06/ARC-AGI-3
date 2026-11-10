"""How far does Tycho's built-in planner get on bp35 when handed a PERFECT model?

The model is the bp35 simulator that was validated state-for-state against the game. Actions are already
reduced to one click per clickable on-screen block. Only the planner's search capacity is being measured.
"""
import importlib.util, sys, time
sys.path.insert(0, sys.argv[1])            # solver dir (sim.py)
from sim import Level, WIN, LOSE
spec = importlib.util.spec_from_file_location("wmlib", sys.argv[2])
wmlib = importlib.util.module_from_spec(spec); spec.loader.exec_module(wmlib)
budgets = [int(x) for x in sys.argv[3].split(",")]
levels = [int(x) for x in sys.argv[4].split(",")]


class Model:
    TRANSITION_RETURNS_NEW_STATE = True

    def __init__(self, n):
        self.lv = Level(n)

    def start(self):
        return (self.lv.start, None)

    def transition(self, state, action):
        a = {"ACTION3": ("L",), "ACTION4": ("R",)}.get(action["action"]) or ("C", action["col"], action["row"])
        ns, out = self.lv.step(state[0], a)
        return (ns, out)

    def actions(self, state):
        out = []
        for a in self.lv.actions(state[0]):
            if a[0] == "L": out.append({"action": "ACTION3", "row": None, "col": None})
            elif a[0] == "R": out.append({"action": "ACTION4", "row": None, "col": None})
            else: out.append({"action": "ACTION6", "row": a[2], "col": a[1]})
        return out

    def outcome(self, state):
        return "level_complete" if state[1] == WIN else "game_over" if state[1] == LOSE else "ongoing"

    def planner_key(self, state):
        return (self.lv.key(state[0]), state[1])


for n in levels:
    for b in budgets:
        m = Model(n); t0 = time.time()
        r = wmlib.plan_bfs_with_diagnostics(m, m.start(), max_nodes=b)
        plan = r.get("plan")
        print(f"level {n} budget {b:>9,}: {r['status']:22} plan_len={len(plan) if plan else '-':>3} "
              f"expanded={r['expanded_nodes']:,} seen={r['seen_states']:,} {time.time() - t0:.0f}s", flush=True)
