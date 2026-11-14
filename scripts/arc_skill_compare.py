#!/usr/bin/env python3
"""Compare an arc-skill run with the published arc-skill + Opus 5 baseline, level by level.

  scripts/arc_skill_compare.py <game>-<tag>        (a folder under ~/Desktop/arc-skill-work/runs, or a path)
  scripts/arc_skill_compare.py --check-log <log>   (summarise a `run_arc_skill.sh check` log)

Baseline: reports/arc_agi3_loss_audit/data/arc_skill_opus5_scorecard.json, the public ARC scorecard
24ddb219 (Claude Code + arc-skill + Opus 5, all 25 games, 7,645 actions, 18 resets). Every action counts,
including RESET, the same way the scorecard counts them.
"""
import json, os, sys
from pathlib import Path

AGI = Path(__file__).resolve().parent.parent
WORK = Path(os.environ.get("ARC_SKILL_WORK", Path.home() / "Desktop" / "arc-skill-work"))
CARD = AGI / "reports" / "arc_agi3_loss_audit" / "data" / "arc_skill_opus5_scorecard.json"


def load_jsonl(path):
    out = []
    for line in open(path):
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def check_log(path):
    msgs = load_jsonl(path)
    init = next((m for m in msgs if m.get("type") == "system" and m.get("subtype") == "init"), None)
    if not init:
        print("no init message in the log: the CLI did not start a session"); print(open(path).read()[:800]); return 1
    print(f"model           : {init.get('model')}")
    print(f"auth source     : apiKeySource={init.get('apiKeySource')!r}   ('none' means subscription login, no API key)")
    print(f"permission mode : {init.get('permissionMode')}")
    skills = init.get("skills") or []
    print(f"arc-skill found : {'arc-skill' in skills}   (skills: {', '.join(skills) or 'none listed'})")
    calls = {}
    for m in msgs:
        body = m.get("message")
        content = body.get("content") if isinstance(body, dict) else None
        for part in content if isinstance(content, list) else []:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "tool_use" and part.get("name") == "Bash":
                calls[part["id"]] = [part["input"].get("command", ""), None]
            if part.get("type") == "tool_result" and part.get("tool_use_id") in calls:
                text = part.get("content")
                if isinstance(text, list):
                    text = " ".join(str(x.get("text", "")) for x in text if isinstance(x, dict))
                calls[part["tool_use_id"]][1] = ("ERROR/DENIED: " if part.get("is_error") else "ran: ") + str(text)[:110].replace("\n", " ")
    for cmd, res in calls.values():
        print(f"  $ {cmd[:120]}\n      -> {res}")
    res = next((m for m in msgs if m.get("type") == "result"), None)
    if res:
        print(f"model's summary : {str(res.get('result'))[:400]}")
        print(f"turns {res.get('num_turns')}, notional cost ${res.get('total_cost_usd')}, models used: {list((res.get('modelUsage') or {}).keys())}")
        denials = res.get("permission_denials") or []
        print(f"permission denials: {len(denials)}")
    return 0


def summarise(events):
    levels = {}
    for prev, ev in zip(events, events[1:]):
        lv = int(prev["levels_completed"]) + 1
        d = levels.setdefault(lv, dict(actions=0, resets=0, deaths=0, done=False))
        d["actions"] += 1
        d["resets"] += ev["action"] == "RESET"
        d["deaths"] += "GAME_OVER" in str(ev["state"]) and "GAME_OVER" not in str(prev["state"])
        if int(ev["levels_completed"]) > int(prev["levels_completed"]):
            d["done"] = True
    return levels


def compare(arg):
    run = Path(arg) if os.path.isdir(arg) else WORK / "runs" / arg
    found = [p for p in run.rglob("events.jsonl") if p.parent.name == ".arc"]
    if not found:
        print(f"no .arc/events.jsonl under {run}"); return 1
    card = {e["id"].split("-")[0]: e["runs"][0] for e in json.load(open(CARD))["environments"]}
    for path in found:
        events = load_jsonl(path)
        cfg = json.load(open(path.parent / "config.json"))
        game = cfg["game_id"]; base = card.get(game)
        levels = summarise(events)
        last = events[-1]
        print(f"\n{run.name}: {game} ({(cfg.get('public_info') or {}).get('game_id')}, {cfg.get('mode')} mode)  "
              f"state {last['state']}  levels {last['levels_completed']}/{last['win_levels']}  actions {len(events) - 1}")
        print(f"{'level':>5} {'this run':>9} {'resets':>6} {'deaths':>6} {'baseline':>9} {'human':>6}  note")
        tot = btot = 0
        for lv in sorted(levels):
            d = levels[lv]
            b = base["level_actions"][lv - 1] if base and lv <= len(base["level_actions"]) else None
            h = base["level_baseline_actions"][lv - 1] if base and lv <= len(base["level_baseline_actions"]) else None
            note = "" if d["done"] else "in progress"
            if d["done"] and b is not None:
                tot += d["actions"]; btot += b
            print(f"{lv:>5} {d['actions']:>9} {d['resets']:>6} {d['deaths']:>6} {b if b is not None else '-':>9} {h if h is not None else '-':>6}  {note}")
        if btot:
            print(f"completed levels: this run {tot} actions, baseline {btot} ({tot / btot:.2f}x)")
        if base:
            print(f"baseline whole game: {base['actions']} actions, {base['resets']} resets, {base['levels_completed']} levels")
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--check-log":
        sys.exit(check_log(sys.argv[2]))
    if len(sys.argv) != 2:
        print(__doc__); sys.exit(2)
    sys.exit(compare(sys.argv[1]))
