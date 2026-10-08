# Paired observation probe v1: completed r2 results

The technical run passed on one NVIDIA RTX PRO 6000 Blackwell Server Edition.
Source commit: `8230c5c18934cf3129b525ad21ddd744ada3b91c`. Public review revision: r2; review-source-lock
SHA256: `1fe36d03ee517f17e8581b9a69515815c6731514c2367aac27c302c1b111c35f`.

This is a sanitized aggregate report derived from the independently rescored
private evidence. Raw responses, logs, account identifiers and approval records
remain private. See the [frozen protocol](control_interface_action_selection_v1_protocol_r1.md)
and [machine-readable aggregate](control_interface_action_selection_v1/completed_r2_aggregate.json).

| Arm | Contexts valid in both passes | Fraction |
| --- | ---: | ---: |
| Reference | 11/30 | 36.7% |
| Computed control metadata | 24/30 | 80.0% |

Paired contexts: 14 improved, 1 regressed,
10 valid in both arms and 5 valid in neither.
Full validity requires the exact response shape, a legal integer action ID and
the corresponding valid arguments, in both repeated passes.

Metadata produced 13 more valid contexts, a 43.3 percentage-point difference
within this paired experiment. Six metadata contexts remained invalid. Their
responses used an incorrect flat structure and string action IDs; two also chose
an unavailable action. The single regression also involved that structure/ID
failure. These findings warranted a separate explicit-contract experiment.

The first-cell lifecycle through cleanup and evidence finalization lasted
611.532 seconds, within the 3,600-second limit.
This measurement excludes provider queueing and mounting time. All 131/131
counted HTTP requests were used: 120 research, 3 startup, 4 compatibility and
4 cancellation requests. Zero game actions; zero automatic retries.

All 174 wheel hashes and 20 model files were verified. Independent rescoring
reproduced the summary from all 120 responses, verified all 125 evidence-file
hashes and matched the frozen prompt token audit. Prefix caching was disabled.
Cancellation, process/GPU cleanup, temporary environment/source removal, evidence
finalization and the explicit final deadline check passed.

The observations comprise 30 exposed development contexts from 15 games, with
two passes per arm. They are correlated observations, not 120 independent
contexts. The decoder enforced JSON objects only; it did not constrain legal
actions, and scoring applied no repair. No action usefulness, game progress,
solving ability, held-out generalization or policy promotion is established.
V2 changed the shared prompt for both arms; cross-version differences are
descriptive and do not isolate the template's causal effect.

All earlier attempts remain consumed and their records are preserved. Publishing
this summary does not authorize another attempt. The remaining legality failure
requires consideration before a separately reviewed closed-loop pilot.

See the [v1/v2 comparison](control_interface_action_selection_v1_v2_results_2026-10-08.md).
