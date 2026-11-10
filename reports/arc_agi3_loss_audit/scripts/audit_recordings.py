"""Loss decomposition for every downloaded replay, checked against the official per-level action counts."""
import glob, json, sys
sys.path.insert(0, sys.argv[1])
from audit_lib import decompose, summarize
h = json.load(open(sys.argv[1] + "/headroom.json")); meta, runs, best = h["meta"], h["runs"], h["best"]
out, bad = {}, []
for f in sorted(glob.glob(sys.argv[1] + "/rec/*.json")):
    d = json.load(open(f)); lab, g = d["label"], d["game"]
    steps = d["steps"]
    if steps and steps[0]["a"] == "RESET":
        steps = steps[1:]                     # the opening RESET creates the game; ARC does not count it
    lv = decompose(steps, meta[g]["levels"])
    official = runs[g][lab][0]
    mine = [L["actions"] for L in lv]
    if mine != official:
        bad.append((lab, g, mine, official))
    s = summarize(lv, meta[g]["baseline"])
    s["best_on_completed"] = sum(best[g][L["level"] - 1] for L in lv if L["completed"])
    s["undo"] = sum(x["a"] == "ACTION7" for x in steps)
    s["levels"] = lv
    out.setdefault(lab, {})[g] = s
json.dump(out, open(sys.argv[1] + "/recordings_audit.json", "w"))
print("sessions", sum(len(v) for v in out.values()), "| per-level count mismatches vs official:", len(bad))
for b in bad[:10]: print("  MISMATCH", b)
K = ["actions", "final_attempts", "failed_on_completed", "unfinished", "game_overs", "voluntary_resets", "noops", "undo", "human_on_completed", "best_on_completed", "levels_completed"]
print(f"\n{'config':26} games " + " ".join(f"{k[:9]:>9}" for k in K))
for lab in sorted(out):
    t = {k: sum(s[k] for s in out[lab].values()) for k in K}
    print(f"{lab:26} {len(out[lab]):5} " + " ".join(f"{t[k]:9}" for k in K))
