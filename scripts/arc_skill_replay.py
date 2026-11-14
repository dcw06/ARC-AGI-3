#!/usr/bin/env python3
"""Build a self-contained replay page for an arc-skill run.

  scripts/arc_skill_replay.py <game>-<tag> [out.html] [--note "text shown under the table"]

Reads <run>/.arc/events.jsonl (every animation frame of every action) and writes one HTML file with a
player: the game screen, each action's prediction and stated reason, a timeline, and per-level counts
against the published arc-skill + Opus 5 scorecard. Frames are stored as cell changes, 2 bytes each.
"""
import base64, json, os, sys
from pathlib import Path

AGI = Path(__file__).resolve().parent.parent
WORK = Path(os.environ.get("ARC_SKILL_WORK", Path.home() / "Desktop" / "arc-skill-work"))
CARD = AGI / "reports" / "arc_agi3_loss_audit" / "data" / "arc_skill_opus5_scorecard.json"
NAMES = {"ACTION1": "Up", "ACTION2": "Down", "ACTION3": "Move left", "ACTION4": "Move right",
         "ACTION5": "Interact", "ACTION7": "Undo"}

args = [a for a in sys.argv[1:]]
note = ""
if "--note" in args:
    i = args.index("--note"); note = args[i + 1]; del args[i:i + 2]
if not args:
    print(__doc__); sys.exit(2)
run = Path(args[0]) if os.path.isdir(args[0]) else WORK / "runs" / args[0]
out = Path(args[1]) if len(args) > 1 else WORK / "replays" / f"{run.name}.html"
arc = next(p.parent for p in run.rglob("events.jsonl") if p.parent.name == ".arc")
events = [json.loads(l) for l in open(arc / "events.jsonl") if l.strip()]
cfg = json.load(open(arc / "config.json"))
game = cfg["game_id"]
base = {e["id"].split("-")[0]: e["runs"][0] for e in json.load(open(CARD))["environments"]}.get(game)

pack = bytearray(); prev = [0] * 4096
meta = []; levels = {}; k_in_level = {}
for idx, ev in enumerate(events):
    fr = ev["frames"]
    if len(fr) > 255:
        fr = fr[:254] + fr[-1:]
    pack.append(len(fr))
    for f in fr:
        g = [int(c, 16) for row in f for c in row]
        ch = [(i << 4) | g[i] for i in range(4096) if g[i] != prev[i]]
        pack += len(ch).to_bytes(2, "little")
        for c in ch:
            pack += c.to_bytes(2, "little")
        prev = g
    if idx == 0:
        meta.append({"a": "START", "lv": 1, "k": 0}); continue
    before = int(events[idx - 1]["levels_completed"])
    lv = before + 1
    k_in_level[lv] = k_in_level.get(lv, 0) + 1
    dead = "GAME_OVER" in str(ev["state"]) and "GAME_OVER" not in str(events[idx - 1]["state"])
    up = int(ev["levels_completed"]) > before
    L = levels.setdefault(lv, {"lv": lv, "n": 0, "deaths": 0, "resets": 0, "start": idx})
    L["n"] += 1; L["deaths"] += dead; L["resets"] += ev["action"] == "RESET"
    d = ev.get("data") or {}
    m = {"a": ev["action"], "lv": lv, "k": k_in_level[lv]}
    if ev["action"] == "ACTION6":
        m["x"], m["y"] = d.get("x"), d.get("y")
    if ev.get("predict_ok") is not None and ev.get("predict"):
        m["ok"] = bool(ev["predict_ok"])
    if ev.get("predict"):
        m["p"] = ev["predict"]
    if ev.get("note"):
        m["n"] = ev["note"]
    grade = [[g.get("text", ""), bool(g.get("ok")), g.get("actual", "")] for g in (ev.get("grade") or []) if isinstance(g, dict)]
    if grade:
        m["g"] = grade
    if dead: m["dead"] = 1
    if up: m["up"] = 1
    meta.append(m)

rows = []
for lv in sorted(levels):
    L = levels[lv]
    L["base"] = base["level_actions"][lv - 1] if base and lv <= len(base["level_actions"]) else 0
    L["human"] = base["level_baseline_actions"][lv - 1] if base and lv <= len(base["level_baseline_actions"]) else 0
    rows.append(L)
n = len(events) - 1
done = int(events[-1]["levels_completed"])
deaths = sum(L["deaths"] for L in rows)
html = (Path(__file__).with_name("arc_skill_replay_template.html")).read_text()
fill = {
    "__TITLE__": f"{game} Replay {run.name.split('-', 1)[-1]}",
    "__HEADING__": f"{game}, levels 1 to {max(levels)}",
    "__SUBHEAD__": (f"Run {run.name}: arc-skill in Claude Code, started {events[0]['timestamp'][:10]}. {n} actions, "
                    f"{done} level{'s' if done != 1 else ''} completed, {deaths} death{'s' if deaths != 1 else ''}. "
                    "Step through to see what the agent predicted before each action and whether it held."),
    "__FOOTNOTE__": ("Published baseline: arc-skill with Claude Opus 5, ARC scorecard 24ddb219, one run. Human: the "
                     "benchmark's per-level reference. Select a row to jump to the start of that level. " + note).strip(),
    "__META__": json.dumps(meta, separators=(",", ":")).replace("</", "<\\/"),
    "__LEVELS__": json.dumps(rows, separators=(",", ":")),
    "__ACTION_NAMES__": json.dumps(NAMES),
    "__PACK__": base64.b64encode(bytes(pack)).decode(),
}
for key, val in fill.items():
    html = html.replace(key, val)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(html)
print(f"{out}  ({len(html) / 1e6:.2f} MB, {n} actions, {sum(len(e['frames']) for e in events)} frames)")
