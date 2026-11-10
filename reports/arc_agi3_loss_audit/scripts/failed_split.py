import json, sys
A = sys.argv[1]
meta = json.load(open(A + "/headroom.json"))["meta"]
for lab in ("tycho-opus5_orchestrator", "astra-adapter-high", "astra-standard-high", "opus5-standard-high"):
    death = vol = n_d = n_v = 0; games_d = set(); games_v = set(); undo_games = set(); late = []
    for g in sorted(meta):
        d = json.load(open(f"{A}/rec/{lab}__{g}.json")); steps = d["steps"][1:]
        if any(7 in (s["avail"] or []) for s in steps): undo_games.add(g[:4])
        cur, prev_state = 0, "NOT_FINISHED"; lvl = 0
        for s in steps:
            if s["a"] == "RESET":
                if prev_state == "GAME_OVER": death += cur + 1; n_d += 1; games_d.add(g[:4])
                else: vol += cur + 1; n_v += 1; games_v.add(g[:4])
                late.append(cur); cur = 0
            else:
                cur += 1
                if (s["lc"] or 0) > lvl: lvl = s["lc"]; cur = 0
            prev_state = s["state"]
    late.sort()
    print(f"{lab:26} deaths {n_d:3} cost {death:5} in {len(games_d):2} games | voluntary resets {n_v:3} cost {vol:5} in {len(games_v):2} games | "
          f"median attempt length thrown away {late[len(late)//2] if late else 0} | games offering undo: {len(undo_games)} {sorted(undo_games)}")
