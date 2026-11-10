import json, sys
sys.path.insert(0, sys.argv[1])
from audit_lib import decompose, summarize
idx = json.load(open(sys.argv[2]))["meta"]
d = json.load(open(sys.argv[1] + "/baseline_steps.json"))
tot = dict.fromkeys(["actions", "final_attempts", "failed_on_completed", "unfinished", "game_overs", "voluntary_resets", "noops", "human_on_completed", "levels_completed"], 0)
print(f"{'game':5} lv  act final failed unfin  GO vres noop human  acts(avail)")
for g in sorted(d["steps"]):
    st = d["steps"][g]
    s = summarize(decompose(st, idx[g]["levels"]), idx[g]["baseline"])
    for k in tot: tot[k] += s[k]
    av = sorted({a for x in st for a in (x["avail"] or [])})
    print(f"{g[:4]:5} {s['levels_completed']:2} {s['actions']:4} {s['final_attempts']:5} {s['failed_on_completed']:6} {s['unfinished']:5} {s['game_overs']:3} {s['voluntary_resets']:4} {s['noops']:4} {s['human_on_completed']:5}  {av}")
print("TOTAL", tot)
