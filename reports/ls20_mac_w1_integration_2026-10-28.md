# Mac M1 / Windows W1 local integration — 2026-10-28

Alan's fix was fast-forwarded onto `teammate/mac-world-model` from `c920f5d` to
`f4bf522e96b1642bed8772c29f153bfe44f98bd5`. Rain's source was exported directly
from `078beccea4526d96710493ebed1b934167966e20` to an isolated temporary directory;
Windows implementation files were not merged into the Mac branch.

## Native Mac verification

- Discovery worktree Python 3.12 environment used for all checks.
- Fixed Mac M1 31 tests plus baseline 102 tests: 133 passed in 16.310 seconds.
- Windows W1 contracts, schema and retained replay suite: 36 passed in 0.059 seconds.
- Fresh integration used actual fixed M1, verified by Rain's source-byte manifest.
- 20 scripted attempts (10 per mode), with all 20 independently checked by the
  replay command. These are synthetic callbacks, not real engine actions.
- Model calls, GPU jobs and real game actions: zero.

| Mode | Attempts | Scored | Single-label predictions | Correct | Incorrect | Disagreements |
|---|---:|---:|---:|---:|---:|---:|
| Immediate | 10 | 8 | 4 | 2 | 2 | 0 |
| Competing | 10 | 8 | 3 | 2 | 1 | 1 |

Competition avoids one incorrect single-label commitment by reporting disagreement;
it does not add a correct forecast. This reproduces Rain's diagnostic counts, not
a new held-out advantage or evidence of game solving.

## Reproduce

Export Rain's exact commit to a separate directory with `git archive`, then run
there using the discovery worktree's Python:

```bash
/Users/elena/projects/ARC-AGI-3-discovery/.venv/bin/python -m unittest tests.test_ls20_discovery_windows_w1 tests.test_ls20_discovery_windows_schema tests.test_ls20_discovery_windows_replay
/Users/elena/projects/ARC-AGI-3-discovery/.venv/bin/python scripts/demo_ls20_discovery_windows_w1.py --mac-source /Users/elena/projects/ARC-AGI-3-discovery --mac-commit f4bf522e96b1642bed8772c29f153bfe44f98bd5 --output /private/tmp/mac-w1-fresh-run
/Users/elena/projects/ARC-AGI-3-discovery/.venv/bin/python scripts/demo_ls20_discovery_windows_w1.py --verify /private/tmp/mac-w1-fresh-run/trace.json
```

Use a previously nonexistent output directory. Logs and complete newly generated
artifacts are retained locally under ignored `reports/runs/mac-w1-integration-2026-10-28/`.

## Interface and next boundary

Pass `memory.snapshot()` and the full M1 producer commit. The two M1 algorithms
share a version string; a version string alone is insufficient. W1 consumes the
raw observation/action history and does not independently validate M1's derived
regions. It predicts appearance categories, not executable object mechanics.
W2 objective and target arrays remain empty. Next work is object-conditioned
prospective movement/interaction prediction, followed by M2 planning when suitable
transition and goal interfaces exist. No online game fallback or new assets were used.

This report records local integration only; it does not assert a new GitHub push
or recheck GitHub Actions status.

Fresh trace SHA256: `c4ba64b0e82f8ae52b5ff0fa5800cb8fd085e8d00e50a5df670eff8d5965950b`.
