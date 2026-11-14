"""Summarise the levels 5-6 replicates (start: end of level 4 in l4x-base-1, 117 actions, $11.1214)."""
import glob, json, os, sys

BASE = "/Users/dcw06/Desktop/AGI/.cache/tycho/runs"
START_COST, START_ACTIONS = 11.1214246, 117
P = dict(tokens_in=4e-6, tokens_out=20e-6, cache_read=0.2e-6, cache_write=5e-6)
OPT = {5: 30, 6: 41}
out = []
for d in sorted(glob.glob(f"{BASE}/l56-*")):
    f = os.path.join(d, "game_bp35.json")
    if not os.path.exists(f):
        print(os.path.basename(d), "no record yet"); continue
    g = json.load(open(f)); tr = g["trace"]
    row = {"run": os.path.basename(d), "arm": os.path.basename(d).split("-")[1], "stop_reason": g["stop_reason"],
           "levels_completed": g["levels_completed"], "cost_usd": round(g["inference_budget"]["cost_usd"] - START_COST, 2),
           "error": g.get("error"), "levels": {}}
    lvl = 4
    for i in range(START_ACTIONS, len(tr)):
        s = tr[i]; L = lvl + 1
        a = row["levels"].setdefault(L, dict(actions=0, deaths=0, resets=0, failed=0, cur=0, cost=0.0, calls=0, out_tokens=0,
                                             builder_calls=0, decision_points=0, plans=0, refused=0, seq=[]))
        a["actions"] += 1
        a["seq"].append(s["action"].replace("ACTION", "A") if s["action"] != "ACTION6" else f"C({s['x']},{s['y']})")
        if s["action"] == "RESET":
            a["resets"] += 1; a["failed"] += a["cur"] + 1; a["cur"] = 0
        else:
            a["cur"] += 1
        if "GAME_OVER" in s["state"]:
            a["deaths"] += 1
        r = s.get("reasoning")
        if isinstance(r, dict) and r.get("token_delta"):
            a["cost"] += sum(r["token_delta"][k] * P[k] for k in P)
            a["out_tokens"] += r["token_delta"]["tokens_out"]
            calls = r.get("llm_calls") or []
            a["calls"] += len(calls); a["builder_calls"] += sum(c.get("call_type") == "builder" for c in calls)
            dc = r.get("decision_check")
            if dc:
                a["decision_points"] += bool(dc.get("decision_point")); a["plans"] += len(dc.get("plans", []))
            a["refused"] += sum(1 for t in r.get("tool_trace", []) if t.get("tool") == "take_action" and t.get("invalid")
                                and "NOT committed" in str(t.get("result", "")))
        if s["levels_completed"] > lvl:
            a["completed"] = True; lvl = s["levels_completed"]
    out.append(row)
    print(f"\n{row['run']}  stop={row['stop_reason']}  levels={row['levels_completed']}  cost=${row['cost_usd']}  error={row['error']}")
    for L, a in sorted(row["levels"].items()):
        print(f"  level {L}: actions={a['actions']:3} (optimum {OPT.get(L)}) completed={a.get('completed', False)} deaths={a['deaths']} "
              f"resets={a['resets']} failed-attempt actions={a['failed']} cost=${a['cost']:.2f} calls={a['calls']} "
              f"builder calls={a['builder_calls']} out_tokens={a['out_tokens']} decision points={a['decision_points']} "
              f"plans={a['plans']} refused={a['refused']}")
        if "-v" in sys.argv:
            print("     ", " ".join(a["seq"]))
if "--json" in sys.argv:
    json.dump(out, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)
