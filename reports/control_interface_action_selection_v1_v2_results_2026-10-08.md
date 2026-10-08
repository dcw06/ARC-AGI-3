# Paired observation probes: v1 and v2 results

Both technical runs passed on one RTX PRO 6000, with cleanup and final lifecycle
deadline verification. Both used the same 30 retained development contexts from
15 games, two arms and two passes: 120 research responses per run, zero game
actions and no automatic retries.

| Measure | V1, review r2 | V2, review r1 |
| --- | ---: | ---: |
| Reference contexts valid in both passes | 11/30 (36.7%) | 30/30 (100%) |
| Metadata contexts valid in both passes | 24/30 (80.0%) | 29/30 (96.7%) |
| Metadata improves / regresses contexts | 14 / 1 | 0 / 1 |
| Both arms valid / neither arm valid | 10 / 5 | 29 / 0 |
| Counted HTTP requests | 131/131 | 131/131 |
| Lifecycle through cleanup/finalization | 611.532 s | 539.741 s |

Read the [v1 results](control_interface_action_selection_v1_completed_r2_results.md)
and [v2 results](control_interface_action_selection_v2_completed_r1_results.md)
for provenance, independent verification and scoring details.

V1 showed a metadata advantage within its paired comparison, with residual
formatting and legality failures. V2 supplied the same explicit output contract
to both arms: all responses satisfied the format, while one metadata context
still failed legality in both passes. The reference is a reasonable development
baseline for a separately reviewed next experiment; useful actions remain untested.

V2 changed the shared prompt for both arms. Comparing these separate runs does
not isolate the contract's causal effect. Repeated passes and contexts within a
game are correlated, and the observations are exposed development data. These
results establish neither held-out performance nor game progress or solving.

Only sanitized aggregate results are published. Raw evidence and personal
operations records remain private, and all consumed attempts remain consumed.
