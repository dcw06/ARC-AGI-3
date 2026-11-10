"""Loss decomposition of an ARC-AGI-3 action sequence, using only what the API returns (no game source).

A step is {"a": action name, "state": state after, "lc": levels completed after, "h": hash of final frame}.
Per level, actions are split into attempts (an attempt ends at GAME_OVER, at a RESET, or when the level is
completed). Every action, RESET included, counts as one action, as in ARC scoring.
"""


def decompose(steps, n_levels):
    """steps exclude the opening RESET that creates the game. Returns one dict per level reached."""
    levels = [dict(level=i + 1, actions=0, completed=False, final_attempt=0, failed=0, game_overs=0,
                   voluntary_resets=0, noops=0, attempts=0) for i in range(n_levels)]
    lvl, cur, prev_h, prev_state = 0, 0, None, "NOT_FINISHED"
    for s in steps:
        if lvl >= n_levels:
            break
        L = levels[lvl]
        L["actions"] += 1
        if s["a"] == "RESET":
            if prev_state != "GAME_OVER":
                L["voluntary_resets"] += 1
            L["failed"] += cur + 1            # the abandoned attempt plus the reset itself
            L["attempts"] += 1
            cur = 0
            if (s.get("lc") or 0) < lvl:      # full reset to level 1: later actions belong to the new level index
                lvl = s["lc"] or 0
        else:
            cur += 1
            if prev_h is not None and s["h"] == prev_h and s["state"] == prev_state:
                L["noops"] += 1
            if s["state"] == "GAME_OVER":
                L["game_overs"] += 1
            if (s["lc"] or 0) > lvl or s["state"] == "WIN":
                L["completed"] = True
                L["final_attempt"] = cur
                L["attempts"] += 1
                cur = 0
                lvl = s["lc"] if s["state"] != "WIN" else n_levels
        prev_h, prev_state = s["h"], s["state"]
    if lvl < n_levels and cur:
        levels[lvl]["open_attempt"] = cur
    return levels


def summarize(levels, baseline):
    done = [L for L in levels if L["completed"]]
    und = [L for L in levels if not L["completed"] and L["actions"]]
    return {
        "levels_completed": len(done),
        "actions": sum(L["actions"] for L in levels),
        "final_attempts": sum(L["final_attempt"] for L in done),
        "failed_on_completed": sum(L["failed"] for L in done),
        "unfinished": sum(L["actions"] for L in und),
        "game_overs": sum(L["game_overs"] for L in levels),
        "voluntary_resets": sum(L["voluntary_resets"] for L in levels),
        "noops": sum(L["noops"] for L in levels),
        "human_on_completed": sum(baseline[L["level"] - 1] for L in done),
    }
