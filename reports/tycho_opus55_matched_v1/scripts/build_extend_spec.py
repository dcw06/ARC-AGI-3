"""Write run_spec.json for a budget-only continuation of an existing Tycho run.

Mirrors tycho.harness.run_parallel.main's spec construction exactly (same function, same inputs),
for the game subset and budget env vars of the continuation. Run with the same clean environment
as the run itself. Prints the policy-config differences against the source run's spec so the
override is documented; refuses if anything other than the allowed budget keys differs.
"""
import inspect
import json
import os
import sys
from pathlib import Path

src_spec_path, out_dir, config, games_json = sys.argv[1], Path(sys.argv[2]), sys.argv[3], sys.argv[4]
ALLOWED = {"TYCHO_MAX_GAME_ACTIONS", "TYCHO_MAX_INFERENCE_COST_PER_GAME"}

from tycho.config import apply_config_file, resolved_config
file_applied = apply_config_file(config)
os.environ["LLM_LOG"] = "1"  # run_parallel sets this when --viz (default on); operational key

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
bad = [d for d in diffs if d[1] not in ALLOWED]
for d in diffs:
    print("policy diff:", d)
print("games:", list(spec["policy"]["games"]))
if bad:
    raise SystemExit(f"refusing: non-budget policy differences {bad}")
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "run_spec.json").write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n")
(out_dir / "run_spec_override.json").write_text(json.dumps(
    {"source_run_spec_fingerprint": src["fingerprint"], "new_fingerprint": spec["fingerprint"],
     "allowed_budget_diffs": diffs, "reason": "budget-only continuation from exact checkpoints"},
    indent=2) + "\n")
print("wrote", out_dir / "run_spec.json", "fingerprint", spec["fingerprint"][:16])
