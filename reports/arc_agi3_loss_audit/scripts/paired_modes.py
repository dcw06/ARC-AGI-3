"""Paired comparison of Tycho's published modes on action efficiency, level by level.

For two arms, take every level BOTH completed and compare actions on that level (log ratio). Games are the
resampling unit (levels within a game are not independent). Seeded bootstrap, 20000 resamples.
"""
import json, math, random, sys
h = json.load(open(sys.argv[1])); runs, meta = h["runs"], h["meta"]
random.seed(0)
def compare(a, b):
    per_game = {}
    for g in runs:
        la, lca = runs[g][a][0], runs[g][a][1]; lb, lcb = runs[g][b][0], runs[g][b][1]
        pairs = [(la[i], lb[i]) for i in range(min(lca, lcb)) if la[i] > 0 and lb[i] > 0]
        if pairs: per_game[g] = pairs
    games = sorted(per_game)
    def stat(gs):
        xs = [math.log(x / y) for g in gs for x, y in per_game[g]]
        sa = sum(x for g in gs for x, _ in per_game[g]); sb = sum(y for g in gs for _, y in per_game[g])
        return sum(xs) / len(xs), sa / sb
    m, r = stat(games)
    bs = sorted(stat([random.choice(games) for _ in games])[1] for _ in range(20000))
    n = sum(len(v) for v in per_game.values())
    wins = sum(x < y for v in per_game.values() for x, y in v); losses = sum(x > y for v in per_game.values() for x, y in v)
    print(f"{a[6:]:28} vs {b[6:]:28} levels={n:3} games={len(games):2}  actions ratio a/b={r:.3f}  "
          f"95% CI [{bs[500]:.3f}, {bs[19500]:.3f}]  geo-mean per-level ratio={math.exp(m):.3f}  a fewer:{wins} more:{losses}")
P = "tycho-"
compare(P + "opus48_trigger", P + "opus48_orchestrator")
compare(P + "opus48_single", P + "opus48_orchestrator")
compare(P + "opus48_no_world_model", P + "opus48_orchestrator")
compare(P + "opus48_trigger", P + "opus48_no_world_model")
compare(P + "gpt56_sol_orchestrator_max", P + "opus5_orchestrator")
compare(P + "opus5_orchestrator", P + "opus48_orchestrator")
print()
# levels completed, paired by game
for a, b in [("opus48_trigger", "opus48_orchestrator"), ("opus48_orchestrator", "opus48_no_world_model")]:
    d = [runs[g][P + a][1] - runs[g][P + b][1] for g in sorted(runs)]
    print(f"levels completed {a} - {b}: sum {sum(d):+d}, games better {sum(x > 0 for x in d)}, worse {sum(x < 0 for x in d)}, same {sum(x == 0 for x in d)}")
