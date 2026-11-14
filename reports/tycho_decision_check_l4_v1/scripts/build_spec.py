"""Write run_spec.json for a level-4 replicate that starts from the action-100 checkpoint of the matched
Opus 5.5 run. Same construction as run_parallel's own spec. Every difference from the source run's spec is
printed and saved; anything outside the allow-list given on the command line is refused."""
import inspect, json, os, sys
from pathlib import Path

src_spec_path, out_dir, config, games_json, allowed_csv = sys.argv[1], Path(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]
ALLOWED = set(allowed_csv.split(","))

from tycho.config import apply_config_file, resolved_config
file_applied = apply_config_file(config)
os.environ["LLM_LOG"] = "1"

from tycho.harness import run_parallel as rp
from tycho.harness.run_spec import build_run_spec

games = json.loads(games_json)
recorded, _ = rp._recorded_run_config(file_applied)
spec = build_run_spec(
    repo=rp.REPO, approach="tycho", games=games, seed=0, viz=True, operation_mode="normal",
    resolved_config=resolved_config(config_file=config, file_applied=file_applied),
    recorded_config=recorded, git_version=rp._git_version(),
    extra_sources={"run_parallel._run_one": inspect.getsource(rp._run_one)},
)
src = json.loads(Path(src_spec_path).read_text())
diffs = []
for section, keys in spec["policy"]["config"].items():
    old = src["policy"]["config"].get(section, {})
    for k, v in keys.items():
        if old.get(k) != v:
            diffs.append((section, k, old.get(k), v))
for k in ("approach", "seed", "viz", "operation_mode", "sources_sha256"):
    if src["policy"].get(k) != spec["policy"].get(k):
        diffs.append(("policy", k, src["policy"].get(k), spec["policy"].get(k)))
for d in diffs:
    print("diff vs source run:", d)
bad = [d for d in diffs if d[1] not in ALLOWED]
if bad:
    raise SystemExit(f"refusing: differences outside the allow-list {bad}")
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "run_spec.json").write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n")
(out_dir / "run_spec_override.json").write_text(json.dumps(
    {"source_run_spec_fingerprint": src["fingerprint"], "new_fingerprint": spec["fingerprint"],
     "diffs_vs_source": diffs, "reason": "level-4 replicate from the exact action-100 checkpoint"}, indent=2) + "\n")
print("wrote", out_dir / "run_spec.json", "fingerprint", spec["fingerprint"][:16])
