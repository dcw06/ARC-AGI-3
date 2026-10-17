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
- The broader boundary suite runs **134 tests: 132 pass, 2 SDK-dependent skips,
  zero failures/errors**. Both skipped tests then pass in the installed Linux
  operator interpreter, using synthetic serialization/transport with no provider
  calls. This covers the package-builder source-binding change as well.
- The old live-package builder also binds the new `experiment.py` evaluator
  dependency in newly built review locks. Existing packages are not rewritten.

## Retained evidence audit

The [aggregate audit receipt](granularity_retained_evidence_audit_2026-10-17.json)
records all six actual board hashes and their matching seed, original request,
original preparation and reviewed-grid bindings. All pass. Five admitted SAM
frames additionally match their retained admission image hashes and seed lists;
invalid ls20 remains skipped, with zero proposals and no partial salvage.
Independent replay of every retained SAM logit tensor, quality-based channel
selection and mask-to-cell projection also passes.

Both scorers were rerun against the committed manifest and independently retained
digest after its commit, using refreshed offline evaluation bindings. The
original files and earlier evaluations were preserved. Results are unchanged:

| Retained condition | Raw / scored proposals | Whole-object matches | Exact masks | Neutral ignore matches |
|---|---:|---:|---:|---:|
| Same-color components | 22 / 22 | 7/37 | 3/37 | 0 |
| SAM 2.1 | 22 / 22 | 12/37 | 6/37 | 0 |
| UnSAMv2+ seeded smoke | 3 / 3 | 0/6 | 0/6 | 0 |
| UnSAMv2+ automatic smoke | 96 / 96 | 0/6 | 0/6 | 0 |
| UnSAMv2 seeded smoke | 3 / 3 | 0/6 | 0/6 | 0 |
| UnSAMv2 automatic smoke | 96 / 96 | 0/6 | 0/6 | 0 |

No prediction in these retained cases matched an ignore region, which is why
the corrected policy does not change their totals. Invalid ls20 stays in the
all-board reference denominator and is reported as a format failure. This audit
establishes consistency of retained evidence and current replay, without claiming
the old runtime performed the newly added validation during inference.

The separate granularity-evaluator reference-mutation reproduction also fails
as expected against `5c72610`: it accepts the changed reference instead of refusing.
Its regression now passes against the integrated evaluator.

No GPU job, notebook save, upload retry or new compute authorization was made.
The separately staged Semantic-SAM payload predates these fixes. Its approval
does not cover changed scoring code or a future live package; that package must
bind the current implementation and reviewed experiment manifest.
