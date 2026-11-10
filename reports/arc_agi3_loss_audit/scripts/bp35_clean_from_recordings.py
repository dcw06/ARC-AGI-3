"""Extract each bp35 level's final (successful) attempt from the downloaded replays and replay it in the real,
unmodified game logic from that level's start, to confirm it really clears the level in that many actions."""
import glob, json, sys
sys.path.insert(0, sys.argv[2])
import engine_util as eu
res = {}
for f in sorted(glob.glob(sys.argv[1] + "/rec/*__bp35-0a0ad940.json")):
    d = json.load(open(f)); steps = d["steps"][1:] if d["steps"][0]["a"] == "RESET" else d["steps"]
    lvl, cur = 0, []
    for s in steps:
        if s["a"] == "RESET":
            cur = []; lvl = min(lvl, s["lc"] or 0); continue
        cur.append(s)
        if (s["lc"] or 0) > lvl or s["state"] == "WIN":
            res.setdefault(lvl + 1, []).append((len(cur), d["label"], cur)); cur = []; lvl += 1
for n in sorted(res):
    out = []
    for k, lab, att in sorted(res[n], key=lambda x: x[0]):
        L = eu.new_level(n); win = lose = False; used = 0
        for s in att:
            if s["a"] == "ACTION7":
                used = None; break                       # undo inside the attempt: not replayable with this helper
            a = ("L",) if s["a"] == "ACTION3" else ("R",) if s["a"] == "ACTION4" else ("C", s["x"], s["y"])
            win, lose = eu.act(L, a); used += 1
            if win or lose: break
        tag = "has-undo" if used is None else ("VERIFIED win" if win and used == k else f"NOT verified (win={win} lose={lose} used={used})")
        out.append(f"{k} [{lab.split('-')[0]}-{lab.split('-')[1]}: {tag}]")
    print(f"L{n}: " + "; ".join(out))
