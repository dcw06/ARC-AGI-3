# Coordinate diagnostic R1 attempt: packaging failure, no capability result

Kaggle reported ERROR. All 23 downloaded files were verified against their
download-manifest sizes and SHA-256 hashes and archived with provider observations
and approval/launch/reservation receipts (31 members total).

The model-side readiness check succeeded for the CUDA tensor operation and vLLM
extension import. Startup then failed at tokenizer verification:
`ValueError: tokenizer artifact hash: vocab.json`.

## Confirmed local defect

The revision-copy implementation used an unscoped string replacement from `1800`
to `2100` while adjusting the compute budget. It also changed that substring
inside the tokenizer manifest's expected digest:

- Original: `7a0cfa95c65792d7510205839f80cfd8a3c8f6b1fdad5132d95cee481800374d`
- Failed revision: `7a0cfa95c65792d7510205839f80cfd8a3c8f6b1fdad5132d95cee482100374d`

The local pinned vocab matches the original digest. The target's actual vocab
digest was not printed, so it cannot be independently recovered from these logs.
The corrupted expected digest is directly confirmed in the frozen source.

The offline tokenizer audit verified the inherited grounding manifest rather than
the coordinate revision's runtime manifest. Synthetic package tests likewise did
not validate that exact artifact contract. This explains how the error escaped
review; compiling and hash-locking incorrect source does not establish correctness.
Do not weaken tokenizer verification or silently edit the frozen R2 manifest.

No diagnostic worker state or responses were produced; the canary is downstream
of the failed tokenizer verification. The frozen archive replay verifies sources,
case provenance, and archive members, then raises FileNotFoundError on missing
`worker/state.json`. Record technical failure and **inconclusive capability
evidence**, not zero accuracy or support for any coordinate hypothesis.

## Cleanup, accounting, and next repair boundary

Independent cleanup reports no remaining owned GPU processes/groups. Final
receipt says source removed, but overall pass/completed are false as expected.
Notebook elapsed time: 762.544494411 seconds. Account usage increased 771.862
seconds (4,724.817 to 5,496.679); this is an account-level delta, not exact billing.
Raw provider quota duration/allowance inconsistencies remain unresolved.
The 2,100-second reservation stays consumed; no retry was submitted.

A repair needs a new preserved source revision: copy immutable artifact manifests
byte-for-byte; edit budget fields structurally; audit using the exact new runtime
manifest; add a regression asserting equality of all intended unchanged model and
tokenizer bindings; retain observed artifact hashes on future failures. Then
rebuild/review a GPU-disabled package and obtain separate authorization before
another attempt. No diagnostic wording or case change is justified by this failure.

Evidence: `phase4_coordinates_v1_failure_evaluation.json`,
`phase4_coordinates_v1_download.json`, and `phase4_coordinates_v1_failed_archive.json`.
Archive: `evidence/phase4-coordinates-v1-r1-failed.zip`.
SHA-256: `daa061a31cf3721cab691761ea11f5bbcbe1ac0409f59312f648b0ac3d7fd57a`.

Read-only frozen replay (expected to fail on the missing worker state):

```bash
python scripts/check_phase4_coordinates_v1.py --live-manifest reports/phase4_coordinates_v1_failed_archive.json
```

Production Phase 4 certification, admission limits, and accounting remain open.
