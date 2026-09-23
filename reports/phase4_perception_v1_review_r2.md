# Paired perception v1 R2 — transform instruction repair

R1 instructed the model to use `uncertain` whenever multiple transforms fit,
while the frozen scorer awarded transform credit only for one of the valid
transforms. All three P1 relationships have more than one valid transform, so
following that instruction could yield 0/3 transform credit despite correct
objects and contours. R1's notebook, source lock, token audit, local evidence
and review report remain preserved as historical artifacts.

R2 changes only the prompt instruction for perception cases: “When multiple
transforms fit, report any valid transform; use uncertain when you cannot
identify one.” The scorer and mechanically generated transform sets are
unchanged. Each valid P1 transform receives credit. `uncertain` remains a
valid response and receives no transform credit where an identifiable
transform exists. It remains available when the model cannot identify one;
we do not treat a valid but incorrect response as a technical failure.

R2 regenerates all 13 exact requests and their hashes in `cases.json` and
uses `phase4_perception_v1_r2_token_audit.json`. The pinned CPU processor
verified full/manual image token parity, patch geometry and all request
limits. The revised workload has 53,635 prompt tokens, including the startup
canary, and the same 21,696-token generated ceiling. The largest tested
maximum-schema response uses 1,802 of the 2,048-token perception cap.
These output examples are feasibility checks, not bounds on arbitrary text.

The study still has five matched text/image board pairs, two interface
controls and two canaries: 14 completions, zero environment actions and zero
scorecards. P1 comes from one retained development observation; P2–P5 are
synthetic controls. Related questions are grouped by board, not counted as
independent games. Responses, token counts, finish reasons, request identity,
monitoring and cleanup are retained and independently replayed. Incorrect and
malformed responses remain outcomes. No gameplay or solving claim follows.

The proposed budget is unchanged: one fresh 2,400-second provider
reservation, a 2,280-second startup-inclusive internal deadline, a 900-second
model startup ceiling, a 600-second request window, and a 300-second cleanup
reserve. The request window may end with incomplete pairs; the evaluator
rejects an incomplete study without retry. Per-request context, payload,
response and total evidence limits remain those in R1's review.

R2's GPU-disabled private notebook is
`notebooks/phase4-perception-v1-review-r2`. Review and replay with:

```bash
python scripts/check_phase4_perception_v1.py --replay
python scripts/review_phase4_perception_v1_notebook.py --folder notebooks/phase4-perception-v1-review-r2
```

The first verifies every member against the R2 archive manifest and replays
CPU scripted evidence. The second checks the unpacked notebook and refusal
of missing authority, then exercises approval, reservation and launch gates
with a fake provider. Neither grants real authority. Source approval must
reference the R2 source lock, followed by separate compute authorization and
one fresh reservation before any GPU submission. Production Phase 4 gates and
exact billing remain open.
