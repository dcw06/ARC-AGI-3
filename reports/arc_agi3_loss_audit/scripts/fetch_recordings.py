"""Stream ARC public replay recordings and keep only a compact per-step record (no raw file is stored).

Sample is fixed in advance: every game x the three 'high' configurations in the benchmark index.
Output per session: rec/<label>__<game>.json (step metadata) and .npz (final frame of every step, uint8).
"""
import hashlib, json, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np

IDX = json.load(open(sys.argv[1]))
OUT = Path(sys.argv[2]); OUT.mkdir(exist_ok=True)
LABELS = sys.argv[3].split(",")
runs = IDX["runs"]


def fetch(job):
    label, game, guid = job
    dst = OUT / f"{label}__{game}.json"
    if dst.exists():
        return f"skip {dst.name}"
    url = f"https://arcprize.org/api/recordings/{game}/{guid}"
    req = urllib.request.Request(url, headers={"User-Agent": "arc-audit/0.1"})
    steps, frames, t0 = [], [], time.time()
    for attempt in range(3):
        try:
            steps, frames = [], []
            with urllib.request.urlopen(req, timeout=120) as r:
                for line in r:
                    line = line.strip()
                    if not line:
                        continue
                    d = json.loads(line)["data"]
                    ai = d.get("action_input") or {}
                    fr = d.get("frame") or []
                    last = np.asarray(fr[-1], dtype=np.uint8) if fr else np.zeros((64, 64), np.uint8)
                    if last.shape != (64, 64):
                        last = np.zeros((64, 64), np.uint8)
                    ad = ai.get("data") or {}
                    steps.append({
                        "a": ai.get("id"), "x": ad.get("x"), "y": ad.get("y"), "state": d.get("state"),
                        "lc": d.get("levels_completed"), "full_reset": d.get("full_reset"),
                        "nf": len(fr), "h": hashlib.sha1(last.tobytes()).hexdigest()[:16],
                        "avail": d.get("available_actions"),
                    })
                    frames.append(last)
            break
        except Exception as e:  # network errors: retry
            err = repr(e)
            time.sleep(5)
    else:
        return f"FAIL {label} {game} {err}"
    np.savez_compressed(OUT / f"{label}__{game}.npz", frames=np.stack(frames))
    dst.write_text(json.dumps({"label": label, "game": game, "guid": guid, "steps": steps}))
    return f"ok {label} {game} steps={len(steps)} {time.time() - t0:.0f}s"


jobs = [(lab, g, runs[g][lab]["guid"]) for lab in LABELS for g in sorted(runs) if lab in runs[g]]
print(len(jobs), "jobs", flush=True)
with ThreadPoolExecutor(4) as ex:
    for msg in ex.map(fetch, jobs):
        print(msg, flush=True)
print("DONE", flush=True)
