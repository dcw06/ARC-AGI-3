# Replacement-source coverage, October 6, 2026

Read-only assessment; no decisions imported, bindings changed, bundle built/uploaded or GPU launched.

The returned r4 proposal has 52 rows with missing condition evidence and 15 undecided rows. Its 107 other entries have no structural blocker in that proposal; this is not independent licence clearance. The authoritative file still has 174 unresolved decisions.

| Source | Version | Exact required filenames | Of 52 condition gaps | Of 15 undecided |
|---|---:|---:|---:|---:|
| codywhatleymd/arc3-vllm-0271-sm120-wheelhouse | 6 | 52/174 | 10/52 | 0/15 |
| driessmit1/arc3-vllm-h100-wheelhouse-v3 | 1 | 174/174 | 52/52 | 15/15 |
| mirzamilanfarabi/arc3-vllm-h100-wheelhouse-v3 | 1 | 174/174 | 52/52 | 15/15 |
| raist321/vllm-0-19-wheel | 1 | 1/174 | 1/52 | 0/15 |
| raist321/vllm-019-deps | 1 | 107/174 | 33/52 | 0/15 |
| raist321/vllm-019-full | 1 | 126/174 | 38/52 | 13/15 |
| sahangunasekara92/nemotron-3-fc-vllm-0180-cu128-wheels-v2 | 1 | 75/174 | 19/52 | 13/15 |

The recreated driessmit1 source has all 174 matching filenames and sizes; its publisher checksum list matches all 174 hashes of the project download manifest. Therefore it offers the same wheel artifacts, including all 67 blocked rows. This does not supply missing approval/condition evidence or establish permission for CUTLASS binaries.

Its file listing has only wheels plus README.md, SHA256SUMS and requirements.lock; it adds no separate source or notice materials. Licences inside the wheels are unchanged if the published checksums are accurate.

The source requirements.lock hash differs from the existing smoke protocol binding, and the source lists no bundle-manifest.json. It cannot be substituted into that protocol as the reviewed R2 bundle. A separate external-source runtime package would need validation of exact artifacts, dependency closure, licence/use assessment, account attachment and final compute authorization.

Verification limit: wheel filenames, sizes and publisher hashes compared; actual remote wheel bytes not hashed. Anonymous downloads of the three small files succeeded. Launch-account attachment not tested.

No listed candidate has been shown to resolve the review blockers. Other sources with version changes require a new dependency closure and compatibility assessment. None is a drop-in replacement established by this check.

See summary.json for hashes and the blocked_artifact_source_matrix.csv for every blocked row against each candidate.

Evidence retained with this report: `evidence/*__*.json` contains each candidate's public dataset reference, observed version, listing-completeness flag, filenames and byte sizes. The snapshots retain the comparison inputs without unnecessary API fields. `evidence/driessmit1-v1/` contains the three small anonymously downloaded files and their HTTP-status/hash receipt; no remote wheel payload was downloaded.

Comparison method: validate `reports/reviewer_submissions/r4_2026-10-06/returned_r4.csv` with `scripts/wheelhouse_decision_worksheet.py` at the source revision recorded in `summary.json`, without writing its proposed decisions. Classify the proposed rows using `scripts/plan_wheelhouse_r2_bundle.py` condition evaluation. Compare wheel basenames and byte sizes with `reports/wheelhouse_download_manifest.json`, then compare the retained publisher SHA256SUMS against that manifest. The matrix contains 67 blocked artifacts for each of seven candidates (469 rows); a listing match always leaves `review_blocker_resolved_by_listing` false.

Smoke comparison basis: `certification/wheelhouse_r2_smoke_v1/protocol.json` on `wheelhouse-r2-smoke-v1` at `b07e2b2`. This report records that protocol's expected requirements-lock hash and the candidate's differing hash. Dataset listings are observations from the assessment date and can change; account attachment, actual wheel-byte hashes, runtime compatibility and usage permissions remain unverified.