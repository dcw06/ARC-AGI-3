# Local repairs of the 97c4c3c review findings

October 13, 2026. Implemented on local branch `fix/conditional-transfer-review-97c4c3c`, based on
`97c4c3c5608ce132430d8b81c73dbb2d7653faf4`. These are CPU package repairs, not model results or execution authority.

## Changes

1. Tokenizer reference verification is now required to cover every unique reference probe with zero mismatches.
   Construction refuses before generating evidence if coverage is incomplete, the reference is empty/duplicated,
   or a mismatch exists. The successful receipt records 3,116 checked/expected probes, zero mismatches and the
   reference-file SHA-256; the audit's verification flag comes from that receipt.
2. Reference-loss flags compare only reference alternatives/groups and eligible IDs, independently of the answer
   category. Overall stage-distortion flags are retained. Ordering of alternatives is not a reference loss.
3. A standard-library-only static import walker binds the transitive project sources, including imports inside
   functions and existing package initializers. `input_hashes.json` separately binds the protocol, reference audit,
   archive locks and the retained archives used by reference verification. Builder checking and replay refuse
   changed or omitted bindings before reconstruction. Construction also rejects inputs changing during a build.

Earlier memory, stress, transition and replay-helper sources and retained archives were not edited. No thresholds,
prompts, schemas, fixtures, seeds, or request schedules were changed. A future dynamic project import must be
explicitly covered by binding discovery before use.

## Verification

Native macOS arm64, existing CPython 3.12.13 environment and hash-verified tokenizer cache:

| Check | Result |
| --- | --- |
| Original new-benchmark tests | 28 pass |
| Added review regressions | 12 pass |
| Earlier memory/protocol/stress tests | 57 pass |
| Combined run | **97 pass; zero failures/errors/skips**, 46.628 s |
| Builder `--check` | 14 artifacts reproduce; 144 variants, 48 clusters, 5,184 probes, 3,354 unique requests, 1,830 aliases |
| Semantic replay | 144 variants and 48 clusters verified |
| Actual reference mismatch injection | Incrementing an expected token count now raises before construction |
| Dependency tamper injection | Builder check and replay both reject altered vocabulary bytes |
| Bindings | 36 project sources and 6 retained reference/protocol inputs |
| Artifact hashes and whitespace | All manifest hashes match; `git diff --check` passes |

Tests cover category-only, reference-only, combined and unchanged losses at writer and selector stages; real
category-only corruption; reference ordering; mismatch/coverage refusal before writes; empty/duplicate/changing
reference audits; transitive/relative imports; omitted bindings; modified dependencies, inputs and protocol;
unsafe dependency paths; and identity checking before reconstruction.

The baseline benchmark, independent keys, requests, request aliases, schema probes/keys, shortcuts, protocol JSON,
scientific summary and attribution rows remain byte-identical to `97c4c3c`. The current development cases did not
exercise category-only/reference-identical losses, so correcting that diagnostic changes its fault tests but not
these baseline rows. Only bindings/validation receipts and the manifest need new package bytes.

Rebuilt manifest SHA-256: `c980354ed0127ae87944ea9002846e52a40fb937e357d4c85985376ee6edcf93`.
GPU and execution-authority flags remain false. The original verification receipt/test logs remain historical.

## Reproduce

From the fix worktree, using the existing Python environment and the pinned tokenizer cache:

```sh
python -m unittest -v \
  tests.test_conditional_transfer_v1_fixtures \
  tests.test_conditional_transfer_v1_components \
  tests.test_conditional_transfer_v1_selection \
  tests.test_conditional_transfer_v1_package \
  tests.test_conditional_transfer_v1_review_fixes \
  tests.test_evidence_memory_v1 \
  tests.test_evidence_memory_v1_protocol \
  tests.test_evidence_memory_stress_v1
python -m research.conditional_transfer_v1.build --check
python -m research.conditional_transfer_v1.replay
```

This local run used `EVIDENCE_MEMORY_TOKENIZER=/Users/dcw06/Desktop/AGI/.cache/phase4-tokenizer` and the existing
`/Users/dcw06/Desktop/AGI/.venv/bin/python`; it installed no dependencies. The active checkout at `47329b9` and its
unrelated worksheet were preserved. No commits, pushes, approvals, uploads, reservations, model requests,
GPU launches or Kaggle submissions were made. Linux/runtime validation and any later held-out study still need
their own review and authorization.
