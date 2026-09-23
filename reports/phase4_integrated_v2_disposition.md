# Integrated ar25 v2: inventory now feasible; structured study stops at the first decision

Kaggle version 1 completed. Independent frozen replay passed with no errors,
covering initial-state bindings, request reconstruction, token parity,
`finish_reason` evidence, dispatch journals, stop reasons, finalization,
monitoring and independent process/GPU cleanup. A clean-checkout replay from the
committed archive matches. Technical acceptance does not mean the research
question was answered.

| Arm | Study calls | Actions | Level increase | Stop |
|---|---:|---:|---:|---|
| Unassisted control | 8 | 8 | 0 | Eight-action cap |
| Structured | 2 | 0 | 0 | Invalid first decision |

## What v2 settled: the output burden

The v1 inventory ended at its 2,048-token cap with no `finish_reason` retained.
The v2 compact inventory finished with **`finish_reason=stop` at 462 completion
tokens** (1,200 bytes), valid under every schema and parser bound. The
compact-output repair removed that obstruction. Output burden is no longer a
competing explanation for why the structured arm stops.

## What remains: grounding and span semantics

The inventory is valid but not grounded:

- **Regions.** All four regions are 2-cell-wide vertical strips at x=30..31
  (y 0..31), the same area v1's truncated fragments fixated on. **None overlaps
  any of the three reference object boxes** (A x=18..26, B x=36..44,
  C x=51..59): IoU 0 for every reference.
- **Silhouettes.** The descriptions ("vertical strip of 9s/10s/5s/4s") appear to
  describe colour runs rather than objects.
- **Controls.** ACTION1 and ACTION2 are claimed to take `x_y` arguments, which
  contradicts the action contract (only ACTION6 takes coordinates).

The first decision (377 tokens, `finish_reason=stop`) chose ACTION1 with target
`region_3` and span `[16,25,16]`: row y=16 with x running from 25 down to 16.
That is a reversed span. It looks like region 3's y-range, 16..25, placed in the
x positions. The parser rejected it, so the episode stopped as `invalid_output`
before any dispatch. Its prediction and alternative are also identical
(`level_counter_increase`), which gives no distinguishing test. The rejection
message reads "out-of-frame span"; the span is reversed rather than out of frame,
so the message is imprecise but the rejection is correct. No repair, retry or
fallback followed.

These fragments are qualitative evidence from one case. A decision, target and
prediction/alternative proposal **was observed, but invalid**. Executed
structured actions and feedback remain **unobserved**. This is not a scaffold
efficacy result, and it does not show that scaffolding cannot help. The pattern
is consistent with the earlier grounding diagnostic (localization 0/4). One case
does not isolate whether the cause is visual grounding, the `[y,x0,x1]` span
convention, or both.

## Control

The eight ACTION6 clicks were `(16,16)` six times and `(17,16)` twice, identical
to v1 under the same seed. All fall outside the initial object masks. There was
no level increase.

## Run accounting

Attempt `ic2-9f93f6f20b5646478fb2c2caf3f5e3b8` is consumed. There was one upload.
The provider ceiling was 3,600 s and the internal ceiling 3,300 s.

| Measure | Value |
|---|---|
| Notebook elapsed | 668.687 s |
| Model startup | 524.534 s |
| Study calls | 10, plus the canary (`finish_reason=stop`) |
| Actions | 8 |
| Prompt tokens | 206,733 |
| Study completion tokens | 1,105 |
| Peak VRAM | 72.9 GiB |
| Peak process-group RSS | 13.6 GiB |
| Independent cleanup | 0.33 s; zero remaining GPU processes |
| Dependency trees and extracted source | Removed |

Account SDK usage rose from 6,726.179 to 7,385.136 s, a change of **658.957 s**.
That figure is account-wide, not exact per-attempt billing, and exact billing
stays null. No further run is authorized.

## Archive and replay

All **45 downloaded files** (44 outputs plus the console log, 3,104,154 bytes)
were verified against the download manifest. Archive:
`evidence/phase4-integrated-v2-r1-completed.zip`, SHA-256
`f09686835a880ab9b64e8bc9d10a5023726a61651968fb4b3ecef19b689c5a5a`. Member hashes
are in `reports/phase4_integrated_v2_completed_archive.json` and the result in
`reports/phase4_integrated_v2_pilot_evaluation.json`. Replay:

```bash
python scripts/replay_phase4_integrated_v2_completed.py
```

## Next development boundary

Do not repeat this run unchanged. Do not add memory or planning based on this
result.

The next question is whether the model can state a correct, well-formed region
for a visible object in the current frame. It is a grounding and
target-specification question, not an output-length question. Candidates,
each needing its own review and a separately authorized attempt:

- an offline, zero-action diagnostic contrasting explicit `[y,x0,x1]` span
  examples, or a bbox-only target, against the current contract;
- reuse of the existing grounding-diagnostic machinery on this frozen frame.

Also clarify the reversed-span parser message in a future revision.
Production one-scorecard/110-distinct-game certification, admission limits and
exact accounting remain open. Phase 4 remains open.
