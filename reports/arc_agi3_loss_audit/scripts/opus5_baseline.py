"""Opus 5 baseline from public data: the official standard-harness run (25 games), full length and cut at
100 actions per game, next to our Opus 5.5 thin-harness baseline (100 actions) and Tycho + Opus 5.

Game score formula is checked against official scores before it is used on truncated runs:
  level score = min(115, 100 * (human baseline / actions)^2), weighted by level number (1..n);
  game score is capped at 100 * (weight of the completed levels).
"""
import glob, json, sys
A = sys.argv[1]; CAP = 100
h = json.load(open(A + "/headroom.json")); meta, runs = h["meta"], h["runs"]
sess = {}
for f in glob.glob(sys.argv[2] + "/*.json"):
    d = json.load(open(f))
    if d["config"] == "anthropic-claude-opus-5-high":
        e = d["environments"][0]; sess[e["id"]] = e
base = json.load(open(A + "/baseline_steps.json"))

def score(level_actions, n_done, bl):
    n = len(bl); W = n * (n + 1) / 2
    raw = sum((i + 1) / W * min(115.0, 100 * (bl[i] / level_actions[i]) ** 2) for i in range(n_done))
    return min(raw, 100 * sum((i + 1) / W for i in range(n_done)))

# 1) check the formula on official numbers
err = max(abs(score(e["runs"][0]["level_actions"], e["runs"][0]["levels_completed"], meta[g]["baseline"]) - e["score"]) for g, e in sess.items())
err2 = max(abs(score(o["level_actions"], o["levels_completed"], meta[g]["baseline"]) - o["score"]) for g, o in base["official"].items())
print(f"score formula vs official: max error {err:.4f} (Opus 5 public, 25 games), {err2:.4f} (our Opus 5.5 baseline, 25 games)")

def truncate(steps, n_levels, cap):
    la, lvl = [0] * n_levels, 0
    for s in steps[:cap]:
        if lvl >= n_levels: break
        la[lvl] += 1
        if s["a"] == "RESET":
            lvl = min(lvl, s["lc"] or 0)
        elif (s["lc"] or 0) > lvl or s["state"] == "WIN":
            lvl = n_levels if s["state"] == "WIN" else s["lc"]
    return la, lvl

rows, T = [], dict(full_l=0, full_a=0, full_s=0, c_l=0, c_a=0, c_s=0, b_l=0, b_s=0, t_l=0, t_a=0, t_s=0)
for g in sorted(meta):
    bl, n = meta[g]["baseline"], meta[g]["levels"]
    e = sess[g]["runs"][0]
    steps = json.load(open(f"{A}/rec/opus5-standard-high__{g}.json"))["steps"][1:]
    la, lc = truncate(steps, n, CAP)
    # sanity: untruncated reproduction equals official
    la_full, lc_full = truncate(steps, n, 10**9)
    assert la_full == e["level_actions"] and lc_full == e["levels_completed"], g
    cs = score(la, lc, bl)
    o = base["official"][g]
    ta, tlc = runs[g]["tycho-opus5_orchestrator"][0], runs[g]["tycho-opus5_orchestrator"][1]
    ts = score(ta, tlc, bl)
    rows.append((g[:4], n, e["levels_completed"], e["actions"], sess[g]["score"], lc, min(len(steps), CAP), cs, o["levels_completed"], o["score"], tlc, sum(ta), ts))
    for k, v in zip(T, (e["levels_completed"], e["actions"], sess[g]["score"], lc, min(len(steps), CAP), cs, o["levels_completed"], o["score"], tlc, sum(ta), ts)): T[k] += v
print(f"\n{'game':5}{'lv':>3} | {'Opus5 std full':>20} | {'Opus5 std @100':>16} | {'Opus5.5 ours @100':>17} | {'Tycho+Opus5 full':>20}")
print(f"{'':8} | {'lv  act  score':>20} | {'lv act score':>16} | {'lv score':>17} | {'lv  act  score':>20}")
for r in rows:
    print(f"{r[0]:5}{r[1]:3} | {r[2]:6}{r[3]:6}{r[4]:8.1f} | {r[5]:4}{r[6]:5}{r[7]:7.1f} | {r[8]:8}{r[9]:9.1f} | {r[10]:6}{r[11]:6}{r[12]:8.1f}")
print(f"{'ALL':8} | {T['full_l']:6}{T['full_a']:6}{T['full_s']/25:8.2f} | {T['c_l']:4}{T['c_a']:5}{T['c_s']/25:7.2f} | {T['b_l']:8}{T['b_s']/25:9.2f} | {T['t_l']:6}{T['t_a']:6}{T['t_s']/25:8.2f}")
json.dump({"rows": rows, "totals": T, "cap": CAP}, open(A + "/opus5_baseline.json", "w"))
