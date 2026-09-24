# Stage B R8 feedback-limit review (CPU only)

**Status:** Superseded by R9. R8 is a GPU-disabled review snapshot, but its
current-code replay cannot read the frozen historical CPU archive because
it lacks a versioned feedback decoder. No R5 source approval,
compute authorization, reservation, or launch exists. The R3 reservation
remains consumed. R7 and its historical lock are preserved.

The R7 feedback audit carried one full pre-action grid and every returned
grid as nested decimal JSON arrays. Its pinned-tokenizer stress result was
59,569 prompt tokens for six repeated frames, only 431 below the 60,000
per-call ceiling; seven and eight frames exceeded that ceiling. It also
rejected more than six frames before a feedback model call.

R8 changes **only the sealed feedback audit request**. Each 64×64 grid is
encoded losslessly as 64 row strings, one hexadecimal color digit per cell.
The request specifies x/y ordering and carries the full pre-action frame and
every returned frame (up to eight). The full numeric grids remain in durable
trajectory evidence; the policy request, action budget, prediction audit,
scoring, canary, model, and no-retry rule are unchanged. A non-64×64 frame,
color outside 0–15, ninth returned frame, or live tokenizer-limit violation
still stops before the feedback call, with the transition already retained.
This is a new audit representation, so its feedback accuracy cannot be
compared directly with R7's unexecuted feedback condition.

Local tests round-trip all eight frames, reject shape/palette/boolean input,
and show that independent replay rejects an altered encoded row. A dense
eight-frame 0–15 pattern produces a **41,137-byte** complete request,
well below the 196,608-byte transport ceiling. This byte result does not
replace an exact token count. The pinned tokenizer files named in
`certification/phase4_integrated_v2/tokenizer_manifest.json` were not
available in this checkout or the local WSL cache. The updated CPU audit
script is ready to measure exact requests and both repeated/dense eight-frame
stress cases once those manifest-verified files are available. The live
`TokenGuardedService` still counts every request with that tokenizer and
rejects over-limit prompts before transport. Until the offline pinned audit
is run, R8 should **not** be approved for GPU launch.

The R8 notebook is private, internet-disabled and GPU-disabled. Independent
unpacking verified 1,043 source bindings and rejected unapproved execution.
Review-lock SHA-256:
`3c7cec15f87cf8ddc0ad2f7372dff351ebdf0f704b9716902d264b2fe0438c88`.
The R5 authority namespace requires fresh source approval, separate compute
authorization, and a new one-use reservation; prior records cannot authorize
this revision. No provider resource was used in this repair.

The R3 target game bootstrap failed under a notebook Matplotlib backend.
R7's `MPLBACKEND=Agg` repair passed the real local offline-game bootstrap,
but remains unverified on Kaggle. A future run may still fail during target
startup, or the model may give valid but incorrect feedback. Neither local
limit work nor a successful exploratory pair would complete Phase 4
production certification or reconcile exact billing.
