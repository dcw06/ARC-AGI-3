# Mac M1/M2 extension checkpoint — 2026-10-29

## Scope and completed work

Continued from Alan's fixed M1 `f4bf522e96b1642bed8772c29f153bfe44f98bd5` and the
successful local integration with Rain W1 `078beccea4526d96710493ebed1b934167966e20`.
The existing 2026-10-28 report and other local files were preserved.

Implemented isolated `object_effects.py`, `models.py`, `prospective.py`,
`m2_schema.json`, a synthetic demo, 29 focused tests and an integration guide.
Original M1 implementation and schema remain byte-for-byte compatible with Rain's
fixed-source inventory. The new outputs are separate, versioned contracts.

- M1: candidate displacement/mask changes, ambiguous identity associations,
  unmatched appearances/disappearances, conditional adjacency changes, tentative
  co-motion groups, per-frame evidence references including transient effects.
- M2: evidence-backed exact visible-state transition candidates; appearance/action/
  public-status displacement candidates; support and contradictions retained.
- Prospective protocol: predictions flushed/fsynced before dispatch; unknown and
  malformed outcomes suspend execution; independent raw reconstruction of both
  pre/post states, forecast, plan and score; stale plans and duplicate seals rejected.
- Planner: bounded BFS over supported observed edges only, explicit supplied goal,
  first-action execution, contradiction-triggered invalidation and probe request.
- Diagnostics: memory-length comparison, reactive/prediction-only/planning arms,
  unseen-position displacement check, deliberate blocker/model failure, replay,
  W1 compatibility checks, JSON evidence and HTML summary.

## Verification

| Check | Result |
|---|---|
| Original baseline | 102 tests passed |
| Alan-fixed M1 | 31 tests passed |
| New M1/M2 extension, final source | 29 tests passed, 0.129 s |
| Rain W1 contracts/schema/archived replay | 36 tests passed, 0.062 s |
| Distinct tests across those suites | 198 passed |
| Fresh actual M1-to-W1 compatibility diagnostic | 20 scripted attempts; all replayed |
| Final M1/M2 diagnostic | 22 scripted dispatches; all replayed |
| Real game actions / model calls / GPU jobs | 0 / 0 / 0 |

The combined baseline+M1+then-28-new-test run passed 161 tests in 16.261 s.
After strengthening cross-episode replay validation, the final new suite passed
29 tests. Unchanged original suites were not needlessly rerun. Final evidence
binds runtime source hashes; schema validation has a focused regression.

## What the diagnostics show

The branching toy supplies eight training actions and an explicit goal state.
Every comparison starts with that same observed history. The reactive action rule
is deliberately simple (lowest legal ID); observer forecasts are logged even when
ignored. Prediction-only retains that same action policy.

| Policy | Evaluation moves (cap 4) | Goal reached | Correct full-state forecasts |
|---|---:|---|---:|
| Reactive | 4 | No | 4/4 |
| Prediction-only | 4 | No | 4/4 |
| Bounded planning | 1 | Yes | 1/1 |

This is an illustrative counterexample to prediction accuracy implying useful
behavior. It is not a strong baseline, held-out experiment or statistical finding.
The initial learned graph is shared; subsequent evidence is retained online.
The planner uses observed edges, not an inferred geometric simulator.

Under the identical two-support threshold, current-only and last-two-transition
views abstain while the persistent eight-transition view can predict the chosen
edge. Their serialized snapshots are 1,019 / 6,850 / 23,833 bytes. This example is
constructed around evidence retention and the support threshold, not an independent
measurement of general memory value.

A separate translation case records two movement supports, correctly predicts one
new position, then fails on a deliberately introduced blocker. The displacement
candidate is marked contradicted. These are candidate-correspondence scores from
our extractor, not independently annotated object-tracking accuracy. Whole-image
state forecasts remain unknown on the new positions. A separate exact-edge
counterexample invalidates its plan and causes `request_probe`; repeating the
previous outcome cannot erase the contradiction.

## Artifacts and reproducibility

Final artifacts: `reports/runs/mac-m1-m2-2026-10-29-verified/` (ignored local data).
Includes `summary.json`, `models.json`, `object-effects.json`, `index.html`, and
all prospective step files/M1-restorable snapshots. Run:

```bash
.venv/bin/python -m unittest tests.test_ls20_discovery_mac_m2 -v
.venv/bin/python scripts/demo_ls20_discovery_mac_m2.py --output reports/runs/a-new-m2-diagnostic
```

Use a new output directory, never overwrite a previous attempt. Earlier diagnostic
runs in `mac-m1-m2-2026-10-29` and `mac-m1-m2-2026-10-29-final` remain retained.
Across the three demo invocations there were 66 synthetic dispatches, plus 20
synthetic W1 compatibility attempts; unit-test callbacks are additional test
activity, not real-game interactions or independent scientific trials. New test
logs are under `reports/runs/mac-m1-m2-2026-10-29/`.

## Remaining dependencies and research work

Real ls20 assets are still absent at `scratch/ls20-baseline/`; no online fallback
was used. Obtain Alan's authorized bundle, frozen observation and hash inventory
before engine verification. W2 has no candidate goals yet, so supplied diagnostic
goals are explicitly required. W1 appearance labels are not converted into fake
executable mechanics. Rain should review the new object-effect records and agree
the future executable-rule interface.

M1 still needs robust entity/group identity, recoloring/occlusion handling, terrain
layers and semantic role revision. M2 still needs richer conditional rules,
recovery through new scope/precondition discovery, meaningful policy comparisons,
held-out prospective evidence and live budget supervision. State/action scopes
are conservatively retired after conflicts, so hidden-mode recovery is not solved.
No module knows the ls20 player palette, step size or winning rule. However, this
checkpoint has not demonstrated autonomous rule discovery or cross-game transfer.

See `research/ls20_discovery_mac/M1_M2_CHECKPOINT.md` for detailed APIs and limits.
No commit or push was performed for this extension.

Final summary SHA256: `a95c62380affa274646c8e2fb937bc27ed5900ce4c70032f12d2f6e6b96723a1`.
