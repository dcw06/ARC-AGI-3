"""Summarize ARC-AGI-3 public-demo session records: actions needed to fully solve (WIN) each game."""
import csv
import glob
import json
import sys
from collections import defaultdict
from pathlib import Path

SESS = Path(sys.argv[1])
OUT = Path(sys.argv[2])
LEVELS = ["max", "xhigh", "high", "medium", "low", "none"]

runs = defaultdict(dict)  # game -> config label -> run
meta = {}
for f in sorted(glob.glob(str(SESS / "*.json"))):
    d = json.load(open(f))
    cfg = d["config"]
    if cfg.startswith("openai-gpt-6-astra-"):
        rest = cfg[len("openai-gpt-6-astra-"):]
        harness = "adapter" if rest.endswith("-provider-adapter") else "standard"
        label = f"astra-{harness}-{rest.replace('-provider-adapter', '')}"
    elif cfg == "anthropic-claude-opus-5-high":
        label = "opus5-standard-high"
    else:
        label = cfg
    for env in d["environments"]:
        r = env["runs"][0]
        game = env["id"]
        bl = r["level_baseline_actions"]
        meta[game] = {"levels": env["level_count"], "baseline": bl}
        runs[game][label] = {
            "guid": r["guid"], "state": r["state"], "levels_completed": r["levels_completed"],
            "actions": r["actions"], "resets": r["resets"], "score": env["score"],
            "level_actions": r["level_actions"],
        }

rows = []
for game in sorted(runs):
    m, rr = meta[game], runs[game]
    human = sum(m["baseline"])
    row = {"game": game, "levels": m["levels"], "human_baseline_total": human,
           "official_cutoff_5x": 5 * human}
    for h in ("adapter", "standard"):
        wins = {lv: rr[f"astra-{h}-{lv}"] for lv in LEVELS
                if f"astra-{h}-{lv}" in rr and rr[f"astra-{h}-{lv}"]["state"] == "WIN"}
        row[f"astra_{h}_wins"] = f"{len(wins)}/{sum(f'astra-{h}-{lv}' in rr for lv in LEVELS)}"
        if wins:
            lv, best = min(wins.items(), key=lambda kv: kv[1]["actions"])
            row[f"astra_{h}_best_win_actions"] = best["actions"]
            row[f"astra_{h}_best_win_effort"] = lv
            row[f"astra_{h}_best_win_replay"] = f"https://arcprize.org/replay/{best['guid']}"
            row[f"astra_{h}_median_win_actions"] = sorted(w["actions"] for w in wins.values())[len(wins) // 2]
        hi = rr.get(f"astra-{h}-high")
        row[f"astra_{h}_high"] = (f"WIN {hi['actions']}" if hi and hi["state"] == "WIN" else
                                  f"{hi['levels_completed']}/{m['levels']} ({hi['actions']} act)" if hi else "-")
    o = rr.get("opus5-standard-high")
    row["opus5_standard_high"] = (f"WIN {o['actions']}" if o and o["state"] == "WIN" else
                                  f"{o['levels_completed']}/{m['levels']} ({o['actions']} act)" if o else "-")
    if o:
        row["opus5_replay"] = f"https://arcprize.org/replay/{o['guid']}"
    rows.append(row)

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "sessions_by_game.json").write_text(json.dumps(
    {"meta": meta, "runs": runs}, indent=1, sort_keys=True) + "\n")
cols = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k) if k in rows[0] else 99)
with open(OUT / "full_solve_benchmark.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)

hdr = ["game", "lv", "human", "5x cutoff", "Astra PA best win", "Astra PA high", "Astra PA wins",
       "Astra Std best win", "Astra Std wins", "Opus 5 Std high"]
print("| " + " | ".join(hdr) + " |")
print("|" + "---|" * len(hdr))
for r in rows:
    pa = f"{r['astra_adapter_best_win_actions']} ({r['astra_adapter_best_win_effort']})" if "astra_adapter_best_win_actions" in r else "-"
    st = f"{r['astra_standard_best_win_actions']} ({r['astra_standard_best_win_effort']})" if "astra_standard_best_win_actions" in r else "-"
    print("| " + " | ".join(str(x) for x in [
        r["game"][:4], r["levels"], r["human_baseline_total"], r["official_cutoff_5x"], pa,
        r["astra_adapter_high"], r["astra_adapter_wins"], st, r["astra_standard_wins"],
        r["opus5_standard_high"]]) + " |")
print("games:", len(rows), "sessions:", sum(len(v) for v in runs.values()))
