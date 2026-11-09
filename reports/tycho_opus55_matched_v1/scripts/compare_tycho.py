"""Compare a Tycho run (game_<id>.json records) with the baseline Opus 5.5 competition run."""
import json
import sys
from pathlib import Path

RUN = Path(sys.argv[1])
BASE = Path("/Users/dcw06/Desktop/AGI/.cache/claude_arc_runs/opus55-competition-20261106T054112Z/summary.json")


def env_score(level_actions, baselines, completed_n):
    tot = wsum = comp = 0.0
    for i, h in enumerate(baselines, 1):
        tot += i
        if i <= completed_n:
            a = level_actions[i - 1]
            wsum += i * min((h / a) ** 2 * 100.0, 115.0)
            comp += i
    return min(wsum / tot, comp / tot * 100.0) if tot else 0.0


base = {e["id"][:4]: e for e in json.load(open(BASE))["official_scorecard"]["environments"]}
rows = []
for g in ("lf52", "bp35"):
    b = base[g]["runs"][0]
    rows.append((g, "baseline harness", base[g]["levels_completed"], base[g]["level_count"], base[g]["score"],
                 base[g]["actions"], base[g]["resets"], b["level_actions"][:base[g]["levels_completed"] + 1], "-", "competition card"))
    p = RUN / f"game_{g}.json"
    if not p.exists():
        rows.append((g, "Tycho", "?", "?", "?", "?", "?", "not finished", "?", "?"))
        continue
    r = json.load(open(p))
    lv = r.get("level_results") or r.get("levels") or []
    done = [l for l in lv if l.get("completed")]
    la = [l.get("actions_taken") for l in lv]
    unfinished = r.get("unfinished_level_actions") or 0
    if unfinished and len(la) == len(done):
        la = la + [unfinished]
    bl = b["level_baseline_actions"]
    score = env_score([l.get("actions_taken") for l in done], bl, len(done))
    ib = r.get("inference_budget") or {}
    cost = ib.get("game_cost_usd") or ib.get("cost_usd") or r.get("inference_cost_usd")
    rows.append((g, "Tycho", len(done), len(bl), round(score, 2), r.get("total_actions_including_unfinished"),
                 r.get("resets"), la, None if cost is None else round(cost, 2), r.get("stop_reason")))

hdr = ("game", "harness", "levels", "of", "score", "actions", "resets", "per-level actions", "cost $", "stop")
print(" | ".join(hdr))
for row in rows:
    print(" | ".join(str(x) for x in row))
