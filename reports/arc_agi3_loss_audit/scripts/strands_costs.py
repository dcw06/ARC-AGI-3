"""Read each Strands replay's final recorded totals (cost, calls, tokens). Streams; stores nothing raw."""
import json, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
sc = json.load(open(sys.argv[1]))
def one(e):
    g, guid = e["id"], e["runs"][0]["guid"]
    req = urllib.request.Request(f"https://arcprize.org/api/recordings/{g}/{guid}", headers={"User-Agent": "arc-audit/0.1"})
    best, n = None, 0
    for _ in range(3):
        try:
            best, n = None, 0
            with urllib.request.urlopen(req, timeout=120) as r:
                for line in r:
                    if not line.strip(): continue
                    n += 1
                    i = line.rfind(b'"reasoning"')
                    j = line.find(b'aggregate', i)
                    if j < 0: continue
                    d = json.loads(line)["data"]["action_input"].get("reasoning")
                    while isinstance(d, str):
                        try: d = json.loads(d)
                        except Exception: break
                    if isinstance(d, dict) and "aggregate" in d: best = d["aggregate"]
            break
        except Exception as ex:
            err = repr(ex)
    return g, n, best
out = {}
with ThreadPoolExecutor(5) as ex:
    for g, n, agg in ex.map(one, sc["environments"]):
        out[g] = {"steps": n, "aggregate": agg}; print(g, n, agg, flush=True)
json.dump(out, open(sys.argv[2], "w"))
print("DONE", flush=True)
