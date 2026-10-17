# Evaluation integrity fixes and separate reference freeze

The runtime branch now contains the owner's scoring policy from `4a071f3`:
invalid responses remain zero detections in all-board totals, and unmatched
predictions may match one ignore region at the same hierarchy and IoU threshold
without becoming false positives. Included references are assigned first. Raw,
neutralized and scored proposal counts remain distinguishable. The policy's
27 targeted tests pass after integration.

Both the offline object-boundary evaluator and the granularity replay evaluator
now require an experiment manifest **and its independently retained SHA256**.
Before any call to the scorer, they check the manifest digest, exact reference
bytes, input/preparation manifest, scoring threshold, hierarchy and the current
evaluator source hashes. Rehashing changed labels inside the supplied manifest
does not override the externally retained manifest digest. Missing authority
arguments refuse; evaluators never generate their own freezes.

The old SAM 2.1 runner now shares the granularity worker's strict input validator.
Each actual PNG must match both the input manifest and its seed frame's
`image_sha256`, including skipped frames. Swapping or altering PNGs while
recomputing local manifest and policy hashes is refused before checkpoint reads,
model imports or output creation.

## Independent freeze for the retained audit

The [committed audit manifest](granularity_retained_reference_audit_manifest_2026-10-17.json)
has SHA256 **`aa9d49422f9b44efa0a4dc504bcaecaa55236b2281be37adb12e6bef3a4348ad`**.
It pins the existing confirmed reference SHA256
`5304e35b1f0ee17e0ffd77293ac4fba260bbfa08755c2d48e914ed72ac9cec63`,
the retained seed manifest, a new offline preparation binding and all current
evaluation sources. Reference contents are not published in this manifest.

This is explicitly a **retrospective audit freeze**, made after the earlier
inference and smoke scores were seen. It is not preregistration, a new owner
mask approval, or a claim that the historical packages used these new checks.
The old preparation, review packages, evaluations, upload payloads and consumed
attempts remain untouched. A separate offline-only copy refreshes preparation
source bindings; no source, use or compute approval transfers to it.

The explicit freeze builder refuses an unexpected reviewed-reference digest and
never overwrites an existing manifest. For a future experiment, freeze and
independently review its manifest before scoring (and before inference when
claiming prospective evaluation). Pass its retained digest to either evaluator:

```text
--experiment-manifest <reviewed-manifest.json>
--experiment-manifest-sha256 <digest-from-independent-review-record>
```

## Verification

- Against extracted `5c72610`, the ignore-region reproduction reports 0.5 instead
  of 1.0 precision; the changed-reference reproduction is accepted; all three
  changed/swapped seed-image cases progress past input validation. These
  baseline failures and their logs are retained privately.
- **73 Linux CPU tests pass, zero failures, errors or skips**, covering scoring,
  preparation, real Torch adapter contracts, replay, source links, frozen
  reference substitution and SAM input binding. No real model inference runs.
- Retained SAM board audit and rescoring under the new external freeze follow
  as separate audit outputs. Historical scores are not silently overwritten.

No GPU job, notebook save, upload retry or new compute authorization was made.
The separately staged Semantic-SAM payload predates these fixes. Its approval
does not cover changed scoring code or a future live package; that package must
bind the current implementation and reviewed experiment manifest.
