"""Summarise the restart-decision runs on bp35 level 6.

  analyze_l6rc.py <run> [<run> ...] [--json out.json]

For each run: stop reason, cost added on top of its source checkpoint (read from the run's own record of
the first live action), the level-6 action sequence, whether the 16-action opening was followed, what the
agent did from the abandoned position (restart or continue), and restart-check activity.
"""
import json, os, sys

BASE = "/Users/dcw06/Desktop/AGI/.cache/tycho/runs"
P = dict(tokens_in=4e-6, tokens_out=20e-6, cache_read=0.2e-6, cache_write=5e-6)
OPENING = ["A4", "A4", "A4", "A4", "A4", "C", "C", "A3", "A3", "A4", "A4", "A3", "A3", "C", "A3", "A3"]
CONTINUATION = ["A4", "A4", "A4", "C"]          # first four actions of the 25-action winning continuation


def lab(s, full=True):
    if s["action"] == "ACTION6":
        return f"C({s['x']},{s['y']})" if full else "C"
    return s["action"].replace("ACTION", "A")


args = [a for a in sys.argv[1:] if not a.startswith("--")]
out_path = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
if out_path in args:
    args.remove(out_path)
rows = []
for name in args:
    f = os.path.join(BASE, name, "game_bp35.json")
    if not os.path.exists(f):
        print(name, "no record yet"); continue
    g = json.load(open(f)); tr = g["trace"]
    start6 = next((k for k, s in enumerate(tr) if s["levels_completed"] >= 5), None)
    l6 = tr[start6 + 1:] if start6 is not None else []
    live = [s for s in tr if isinstance(s.get("reasoning"), dict) and s["reasoning"].get("token_delta")]
    cost = sum(s["reasoning"]["token_delta"][k] * P[k] for s in live for k in P)
    short = [lab(s, False) for s in l6]
    followed = short[:16] == OPENING
    after = l6[16:] if followed else []
    challenges, refused = 0, []
    for s in live:
        r = s["reasoning"]
        challenges = max(challenges, int(r.get("restart_challenges") or 0))
        for t in r.get("tool_trace", []):
            if t.get("tool") == "take_action" and "restart check" in str(t.get("result", "")):
                refused.append(len(tr) - len(l6) + l6.index(s) if s in l6 else -1)
    row = {
        "run": name, "stop_reason": g["stop_reason"], "levels_completed": g["levels_completed"],
        "total_actions": len(tr), "live_actions": len(live), "live_cost_usd": round(cost, 2),
        "total_cost_usd": round(g["inference_budget"]["cost_usd"], 2), "error": g.get("error"),
        "level6_actions": [lab(s) for s in l6], "opening_followed": followed,
        "after_position": [lab(s) for s in after],
        "restarted_within_5": any(s["action"] == "RESET" for s in after[:5]),
        "took_continuation": [lab(s, False) for s in after[:4]] == CONTINUATION,
        "restart_checks_shown": challenges or len(refused),
    }
    rows.append(row)
    print(f"\n{name}: stop={row['stop_reason']} levels={row['levels_completed']} actions={row['total_actions']} "
          f"live actions={row['live_actions']} live cost=${row['live_cost_usd']} (total ${row['total_cost_usd']}) error={row['error']}")
    print("  level 6:", " ".join(row["level6_actions"]) or "(none)")
    print(f"  opening followed={followed}  after position: {' '.join(row['after_position']) or '(none)'}")
    print(f"  restarted within 5={row['restarted_within_5']}  took continuation={row['took_continuation']}  "
          f"restart checks shown={row['restart_checks_shown']}")
if out_path:
    json.dump(rows, open(out_path, "w"), indent=1)
