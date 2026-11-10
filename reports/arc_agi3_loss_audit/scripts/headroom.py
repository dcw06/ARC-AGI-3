"""Per-level best-known action counts across every public run we have, and each agent's gap to them.

Sources: 325 public ARC sessions (GPT-6 Astra 12 configs + Opus 5) and Tycho's six published 25-game
scorecards. 'Best known' for a level = fewest actions any run needed on that level (failed attempts included,
as ARC counts them). The sum over levels is an upper bound on the true optimum for the game.
"""
import json, glob, statistics as st, sys
T = sys.argv[2].rstrip('/') + '/'   # Tycho checkout: artifacts/scorecards
idx = json.load(open(sys.argv[3]))
meta, pub = idx["meta"], idx["runs"]
runs = {g: {} for g in meta}                      # game -> label -> (level_actions, levels_completed, resets, guid)
for g in pub:
    for lab, r in pub[g].items():
        runs[g][lab] = (r["level_actions"], r["levels_completed"], r["resets"], r["guid"])
for f in sorted(glob.glob(T + "*.json")):
    lab = "tycho-" + f.split("/")[-1][:-5]
    for env in json.load(open(f))["environments"]:
        r = env["runs"][0]
        runs[env["id"]][lab] = (r["level_actions"], r["levels_completed"], r["resets"], r["guid"])
best = {}
for g in runs:
    n = meta[g]["levels"]
    best[g] = [min((la[i] for la, lc, _, _ in runs[g].values() if lc > i and la[i] > 0), default=None) for i in range(n)]
json.dump({"best": best, "runs": runs, "meta": meta}, open(sys.argv[1], "w"))
AG = ["tycho-opus5_orchestrator", "tycho-gpt56_sol_orchestrator_max", "astra-adapter-max", "astra-adapter-high"]
print(f"{'game':5} {'human':>6} {'best':>5} | " + " | ".join(f"{a[-18:]:>18}" for a in AG) + "   (actions, resets)")
tot = {a: [0, 0] for a in AG}; tb = th = 0
rows = []
for g in sorted(runs):
    b = sum(best[g]); h = sum(meta[g]["baseline"]); tb += b; th += h
    cells = []
    for a in AG:
        la, lc, rs, _ = runs[g][a]
        cells.append(f"{sum(la):12} {rs:5}"); tot[a][0] += sum(la); tot[a][1] += rs
    rows.append((g, h, b, cells))
    print(f"{g[:4]:5} {h:6} {b:5} | " + " | ".join(cells))
print(f"{'TOTAL':5} {th:6} {tb:5} | " + " | ".join(f"{tot[a][0]:12} {tot[a][1]:5}" for a in AG))
print()
a = "tycho-opus5_orchestrator"
print("Tycho + Opus 5: gap to best-known, by game (sorted by absolute gap)")
gaps = []
for g in sorted(runs):
    la, lc, rs, _ = runs[g][a]
    gaps.append((sum(la) - sum(best[g]), g, sum(la), sum(best[g]), rs))
tg = sum(x[0] for x in gaps)
for gap, g, act, b, rs in sorted(gaps, reverse=True):
    print(f"  {g[:4]} gap {gap:4} ({100 * gap / tg:4.1f}% of total gap)  actions {act:4} best {b:4} ratio {act / b:4.2f} resets {rs}")
print("  total gap", tg, "of", sum(x[2] for x in gaps), "actions")
# by level position
print("\nTycho + Opus 5: actions / best-known by level position (first level, middle, last)")
pos = {"first": [], "second": [], "middle": [], "last": []}
for g in runs:
    la = runs[g][a][0]; n = len(la)
    for i in range(n):
        k = "first" if i == 0 else "second" if i == 1 else "last" if i == n - 1 else "middle"
        pos[k].append((la[i], best[g][i]))
for k, v in pos.items():
    print(f"  {k:6} levels={len(v):3} actions={sum(x for x, _ in v):5} best={sum(y for _, y in v):5} excess={sum(x - y for x, y in v):5} ratio={sum(x for x, _ in v) / sum(y for _, y in v):.2f}")
# replicate-like noise: Astra adapter, 6 effort settings, all wins
print("\nSpread of total actions across the 6 Astra-adapter configurations (all wins): per-game CV")
cvs = []
for g in sorted(runs):
    v = [sum(runs[g][l][0]) for l in runs[g] if l.startswith("astra-adapter") and runs[g][l][1] == meta[g]["levels"]]
    cv = st.pstdev(v) / st.mean(v); cvs.append(cv)
print("  median CV %.1f%%, max %.1f%%, games with CV>10%%: %d" % (100 * st.median(cvs), 100 * max(cvs), sum(c > .10 for c in cvs)))
tots = [sum(sum(runs[g][l][0]) for g in runs) for l in sorted({l for g in runs for l in runs[g]}) if l.startswith("astra-adapter")]
print("  25-game totals:", tots)
