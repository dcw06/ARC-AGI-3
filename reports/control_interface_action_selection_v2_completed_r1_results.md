# Paired observation probe v2: completed r1 results

The technical run passed on one NVIDIA RTX PRO 6000 Blackwell Server Edition.
Source commit: `26ef128f9c642044985556468a3c6b9a118d016d`. Public review revision: r1; review-source-lock
SHA256: `beeb6719ed817e3cb42a9842b03a7c47a2ee75aa87831908520318a54c041dc7`.

This is a sanitized aggregate report derived from the independently rescored
private evidence. Raw responses, logs, account identifiers and approval records
remain private. See the [frozen protocol](control_interface_action_selection_v2_protocol_r1.md)
and [machine-readable aggregate](control_interface_action_selection_v2/completed_r1_aggregate.json).

| Arm | Contexts valid in both passes | Fraction |
| --- | ---: | ---: |
| Reference | 30/30 | 100.0% |
| Computed control metadata | 29/30 | 96.7% |

Paired contexts: 0 improved, 1 regressed,
29 valid in both arms and 0 valid in neither.
Full validity requires the exact response shape, a legal integer action ID and
the corresponding valid arguments, in both repeated passes.

Both arms were format-valid on all 60 responses each. Conditional on valid
format, legal IDs occurred in 60/60 reference responses and 58/60 metadata
responses. Argument validity among formatted, legal responses was 60/60 and
58/58 respectively. The single metadata regression repeated an unavailable
action in both passes; it was a legality failure rather than a formatting failure.
Metadata showed no full-validity benefit on these contexts under the shared
explicit contract. This does not establish that metadata is generally unhelpful.

Format validity checks exact structure, an integer action ID and object-valued
action data; legality and action-specific argument contents are scored separately.

The first-cell lifecycle through cleanup and evidence finalization lasted
539.741 seconds, within the 3,600-second limit.
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
