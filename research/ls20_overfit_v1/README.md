# ls20: a fitted three-level policy

**Validated on the real offline engine: the first three levels complete in
151 moves (16 / 92 / 43).** A fresh-engine reconstruction matches every action
and observation. See the [results report](../../reports/ls20_three_level_overfit_v1_results_2026-11-02.md).

This is a deliberately memorized policy fitted to the owner's earlier successful
play. It does not retrain a VLM or discover general game rules. It targets
`ls20-9607627b`, seed `0`, starting at level 1. Different boards, time-bar values,
game versions or deviations are unsupported and stop execution.

## How it acts

The committed `policy_seed0.json` contains the initial observation and 151
before/action/after records. Each record stores hashes of the complete native
64×64 board, including the interface, legal controls, game state and completed
level count. It contains no raw human log, timestamps, account details or request
identifiers.

`OverfitPolicy.select(game_id, observation)` returns the next directional action
only when the current observation matches the fitted state exactly. The caller
must execute that action once and pass the observed result to
`acknowledge(action, after)`. Only a matching acknowledgement advances the cursor.
Any mismatch stops further selection. No reset, fallback or corrective retry is
available. `.completed` becomes true only after all three expected counter
increments are actually observed.

The policy uses the existing engine action dictionary interface. Its dedicated
runner is the tested entry point; this change does not switch the general
competition agent or submit anything to Kaggle. In particular, do not attach it
to a loop that silently falls back to another policy after a refusal.

## Reproduce

The compiler needs the owner's retained demonstration, which remains local:

```sh
python scripts/build_ls20_overfit_v1.py \
  --demo /path/to/ls20.manual.jsonl \
  --demo-sha256 5539aa3e36626bcbefa4c4b09e9435dc5b8df3d1ef552d88d141e971f1e9bb9f \
  --output /new/path/policy.json
```

It must print `d70c8ff61040d49405f95ef5d56e17f1634ac51695c97e01b2f7f5a92c35b2cd`.
The committed copy is ready to use without the raw demonstration.

Run `python -B -m unittest tests.test_ls20_overfit_v1` for the 17 synthetic
regressions. For a real-engine test, use `scripts/run_ls20_overfit_v1.py --help`
under Linux/WSL. Supply the policy hash, existing pinned game asset directory,
its independently retained receipt hash, game interpreter and a new output
directory. The runner allows 600 seconds including cleanup and performs one
study episode plus one explicitly counted fresh-engine reconstruction. It uses
no model, GPU, online game service or provider operation. Output directories
are never overwritten.

`scripts/render_ls20_overfit_replay_v1.py` produces a local visual replay from
the hash-pinned **new engine journal**, rather than from the training log.
