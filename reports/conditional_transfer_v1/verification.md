# Conditional transfer CPU verification

Historical receipt for the original `97c4c3c` package. Local review repairs and rebuilt-package verification are
recorded separately in `review_fixes.md`; the original logs below remain unchanged.

Verified October 13, 2026, on native macOS arm64 using Python 3.12.15 in the Track 2 `.venv`. Branch: `teammate/mac-conditional-transfer-v1`, based on `b39bfd237f2754598cd6e5fac0f983693a8dda86`. Package manifest SHA-256: `ecad0661ba05c51fe69c981b2ed5baa74e7a5bd8ca6c91831ea5cc7283f7fdf6`.

| Check | Result |
| --- | --- |
| New fixtures, components, selection and package tests | 28 passed, zero failures/skips |
| Existing memory, memory protocol and memory-stress tests | 57 passed, zero failures/skips |
| New builder `--check` | All 13 package artifacts reproduce byte for byte |
| Semantic replay | 144 variants, 48 clusters verified |
| Previous memory-stress builder `--check` | All six historical development artifacts unchanged |
| Pinned tokenizer | Four asset hashes verified; existing token audit reproduced |
| Dependency inspection | `uv pip check`: 56 compatible installed packages |
| New-file whitespace check | Zero errors |
| Existing tracked files | `git diff --exit-code HEAD` succeeds; original files unchanged |
| Credential exclusion | `.env` remains Git-ignored; never read or included in the package |

Raw receipts are [cpu_tests.txt](cpu_tests.txt) and [regression_tests.txt](regression_tests.txt). Package and replay outputs are retained in [package_checks.txt](package_checks.txt).

## Commands

```bash
.venv/bin/python -m unittest -v \
  tests.test_conditional_transfer_v1_fixtures \
  tests.test_conditional_transfer_v1_components \
  tests.test_conditional_transfer_v1_selection \
  tests.test_conditional_transfer_v1_package

.venv/bin/python -m unittest -v \
  tests.test_evidence_memory_v1 \
  tests.test_evidence_memory_v1_protocol \
  tests.test_evidence_memory_stress_v1

.venv/bin/python -m research.conditional_transfer_v1.build --check
.venv/bin/python -m research.conditional_transfer_v1.replay
.venv/bin/python -m research.evidence_memory_stress_v1.build --check
UV_CACHE_DIR=/private/tmp/conditional-uv-cache uv pip check --python .venv/bin/python
git diff --exit-code HEAD
```

The temporary uv cache avoids the filesystem sandbox's restriction on the user's normal cache. This is a cache-location adjustment, not a dependency change. No packages were upgraded or GPU dependencies installed.

## Verification scope

Tests cover exact coordinates and scope, failed/unknown dispatch distinctions, transient frames, continuous trajectories, independent keys and independently reconstructed target annotations, split reservations, atomic corrections, hypothesis status, hidden-metadata poisoning, final prompt caps, duplicate aliases, strict invalid-output handling, separate reference precision/coverage, simultaneous actual writer/selector/reader faults, and forged evidence/requests with refreshed manifest hashes.

No live model output was produced, no held-out evaluation seed was drawn, and no Linux runtime, Kaggle installation, process supervision, schema backend or connected launch was certified. The CPU construction milestone is complete. Independent package review and separately authorized later studies remain outside this milestone. Source-relative reference thresholds are not met by the current budgeted packages; those negative results remain in the report and all per-probe artifacts.
