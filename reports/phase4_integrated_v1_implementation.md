# Integrated ar25 implementation handoff

Implemented in `certification/phase4_integrated_v1/`, preserving the original case
specification, historical notebooks and production agent. The new runner executes
two isolated episodes with inventory/decision/feedback stages in the structured
arm, exact historical control requests in the baseline, and fresh observations
after every action. Independent replay reconstructs requests, dispatch journals,
progress, finalization, initial geometry masks and feedback predicate outcomes.

Validation completed: 22 unit/regression tests; supervised CPU fixtures for correct,
full-cap, incorrect, invalid, transport-failing, token-mismatched and cleanup-failing
responses; monitor failure cleanup; checksum-bound archive replay. Incorrect and
invalid model answers are preserved as diagnostic outcomes. Missing evidence,
late returns, incomplete pairs and inconsistent action bindings fail replay.
Mismatch body/hash/token evidence survives the model-process bridge. Synthetic
authority tests reject missing, mismatched and consumed receipts and a second upload.

Pinned-tokenizer audit covered every request in the 25-call full-cap fixture:
557,204 prompt tokens total, largest 28,949. This is a scripted trajectory, not a
prediction of live model usage. The eight-frame stress prompt reached 76,606 tokens
and is deliberately rejected by the 60,000-token admission guard. All returned
frames are retained; there is no silent truncation. A live trajectory can therefore
end technically incomplete if its feedback/history does not fit. This limitation
must remain visible when approving the study.

Review notebook: `notebooks/phase4-integrated-v1-review-r1/profile.ipynb`.
Source lock SHA-256:
`e254bd8f0ce129535b4a6e8b1ac0e963ffb6ba58be19aaf2b0a744acb9beb372`.
Unpacked inspection verified 848 source bindings, compiled packaged Python, checked
private/offline/GPU-disabled metadata and exercised rejection before installation.
The review notebook is 652,490 bytes. See `phase4_integrated_v1_package_review.json`.

Proposed fresh budget: one 3,600-second provider attempt; 3,300-second internal
lifecycle; 25 study completions plus one canary; 16 action attempts. Full semantics,
admission limits, evidence ceilings and budget rationale are in
`phase4_integrated_v1_review.md` and the executable `protocol.json`.

No model call, environment interaction, real approval receipt, reservation or
upload was made. Launch intent is preserved separately. Approval and compute
authorization must bind this actual reviewed source lock before a fresh one-use
reservation and launch package are made. Do not upload an old notebook or toggle
the review notebook's flags. The target vLLM implementation of the new stage
schemas has not yet been exercised; any target rejection is retained without retry.

Portable local archive replay using the project CPU dependency environment:

```bash
python scripts/check_phase4_integrated_v1.py --replay
```

Archive: `evidence/phase4-integrated-v1-local.zip`; member hashes in
`reports/phase4_integrated_v1_local_archive.json`. Source/artifact hashes are checked
when the frozen review lock is present. Clean-copy packaging/replay results are
recorded separately in `phase4_integrated_v1_final_checks.json` after completion.

Geometry prose, internal-marking descriptions, experiment discrimination and
behavioral use remain rubric adjudications; mechanical replay does not manufacture
those conclusions. This is a scaffolded case study on already-inspected development
data, not a causal benchmark or production Phase 4 certification.
