"""Summarise the level-4 replicates: actions to clear level 4, failures, cost, and decision-check activity."""
import glob, json, os, statistics as st, sys

BASE = "/Users/dcw06/Desktop/AGI/.cache/tycho/runs"
START_COST = 9.2752238          # cost carried in the action-100 checkpoint
START_ACTIONS = 98              # actions used on levels 1-3
rows = []
for d in sorted(glob.glob(f"{BASE}/l4x-*")):
    f = os.path.join(d, "game_bp35.json")
    if not os.path.exists(f):
        rows.append({"run": os.path.basename(d), "status": "no record yet"}); continue
    g = json.load(open(f)); tr = g["trace"]
    l4 = [s for i, s in enumerate(tr) if i >= START_ACTIONS]
    done = g["levels_completed"] >= 4
    live = [s for s in l4 if isinstance(s.get("reasoning"), dict) and s["reasoning"].get("token_delta")]
    out = sum(s["reasoning"]["token_delta"]["tokens_out"] for s in live)
    calls = sum(len(s["reasoning"].get("llm_calls") or []) for s in live)
    dc = next((s["reasoning"]["decision_check"] for s in reversed(live) if "decision_check" in s["reasoning"]), None)
    plans = [p for s in live for p in (s["reasoning"].get("decision_check") or {}).get("plans", [])]
    seq = " ".join(s["action"].replace("ACTION", "A") if s["action"] != "ACTION6" else f"C({s['x']},{s['y']})" for s in l4)
    rows.append({
        "run": os.path.basename(d), "arm": os.path.basename(d).split("-")[1], "status": g["stop_reason"],
        "cleared": done, "l4_actions": len(l4),
        "deaths": sum(1 for s in l4 if "GAME_OVER" in s["state"]), "resets": sum(1 for s in l4 if s["action"] == "RESET"),
        "cost": g["inference_budget"]["cost_usd"] - START_COST, "calls": calls, "out_tokens": out,
        "dc": dc["stats"] if dc else None,
        "plan_actions": [p["n_actions"] for p in plans], "answer_chars": [p["answer_chars"] for p in plans],
        "seq": seq, "error": g.get("error"),
    })
for r in rows:
    if "arm" not in r:
        print(r); continue
    print(f"{r['run']:12} stop={r['status']:22} cleared={r['cleared']!s:5} L4 actions={r['l4_actions']:3} deaths={r['deaths']} "
          f"resets={r['resets']} cost=${r['cost']:.2f} calls={r['calls']:3} out_tokens={r['out_tokens']:6}")
    if r["dc"]:
        s = r["dc"]
        print(f"{'':12} decision points={s['decision_points']} plan steps={s['plan_steps']} plans filed={s['plans_filed']} "
              f"refused actions={s['rejected_actions']} reasons={s['by_reason']} plan lengths={r['plan_actions']} "
              f"answer chars={r['answer_chars']}")
    if r["error"]:
        print(f"{'':12} ERROR: {str(r['error'])[:300]}")
    if "-v" in sys.argv:
        print(f"{'':12} {r['seq']}")
print()
for arm in sorted({r["arm"] for r in rows if "arm" in r}):
    v = [r for r in rows if r.get("arm") == arm and r["cleared"]]
    n_all = sum(1 for r in rows if r.get("arm") == arm)
    if not v:
        print(f"{arm}: 0 of {n_all} cleared"); continue
    a = [r["l4_actions"] for r in v]
    print(f"{arm}: cleared {len(v)} of {n_all}; L4 actions {sorted(a)} mean {st.mean(a):.1f} "
          f"(min {min(a)}, max {max(a)}); deaths {sum(r['deaths'] for r in v)}, resets {sum(r['resets'] for r in v)}; "
          f"mean cost ${st.mean(r['cost'] for r in v):.2f}; mean calls {st.mean(r['calls'] for r in v):.0f}; "
          f"mean output tokens {st.mean(r['out_tokens'] for r in v):.0f}")
print(f"total spent on listed runs: ${sum(r.get('cost', 0) for r in rows):.2f}")
