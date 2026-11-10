import hashlib, json, sys
sys.path.insert(0, sys.argv[3])
from audit_lib import decompose, summarize
P, OUT = sys.argv[1], sys.argv[2]
idx = json.load(open(sys.argv[4]))["meta"]
steps, official = {}, {}
NAMES = {0: "RESET"}
def h(frames):
    return hashlib.sha1(json.dumps(frames[-1]).encode()).hexdigest()[:16] if frames else ""
for line in open(P):
    if '"kind":"transition"' in line[:400]:
        e = json.loads(line)
        aid = e["action"]["action_id"]
        steps.setdefault(e["game_id"], []).append({
            "a": NAMES.get(aid, f"ACTION{aid}"), "state": e["after"]["state"], "lc": e["after"]["levels_completed"],
            "h": h(e["after"]["frames"]), "nf": len(e["after"]["frames"]), "x": e["action"]["action_data"].get("x"),
            "y": e["action"]["action_data"].get("y"), "avail": e["after"]["available_actions"]})
    elif '"kind":"summary"' in line[:400]:
        e = json.loads(line)
        for env in e["summary"]["official_scorecard"]["environments"]:
            official[env["id"]] = env["runs"][0]
json.dump({"steps": steps, "official": official}, open(OUT, "w"))
bad = 0
for g in sorted(steps):
    lv = decompose(steps[g], idx[g]["levels"])
    mine = [L["actions"] for L in lv]
    if mine != official[g]["level_actions"]:
        bad += 1; print("MISMATCH", g, mine, official[g]["level_actions"])
print("games", len(steps), "count mismatches vs official scorecard:", bad)
