# Track 2 Stage 1: files changed at the protocol freeze (review snapshots r2)

**Scope.** Every file changed or added to implement the owner's decisions of October 9, 2026
(`freeze_decisions.md`; frozen protocol `reports/evidence_memory_v1_protocol_v2_frozen.md`, §16), grouped by
decision. Each change belongs to exactly one decision, or to the rebuild and wiring those decisions require. Nothing
else changed. In particular, these are unchanged:
- the prompts, arms, cases, seeds, schedule, admission and stop rules;
- the scorer (`readers.py`, `run/score.py`) and the per-session technical report;
- the frozen sets (`probes.json`, both sessions) and `run/probes.json`;
- the reviewed per-scope live gate (`binding.py`, both sessions);
- session A's launch tooling (`launch.py`, `notebook.launch_artifacts`, `launch-build`);
- the verified runtime (`certification/direct_publisher_smoke_v1/`, vendored byte for byte);
- `LIVE_ENABLED = False`, and every `REPLACE_WITH_` placeholder.

Kept byte-identical as history: the draft `reports/evidence_memory_v1_protocol_v2.md` (and v1), review snapshots r1
of both sessions, their review-check receipts, `structured_outputs_check_r1.json`, `token_cross_check.json`, and the
earlier verification receipts.

## Decision 0: the recall decoding schema drops `uniqueItems` (choice 9)

**Science change.**

| File | Change |
|---|---|
| `research/evidence_memory_v1/stage1.py` | `response_schema('recall')` has no `uniqueItems`; a docstring says why. Recorded as an exact change from `107d8b4` (`FREEZE_AMENDMENTS` in the builder) |
| `tests/test_evidence_memory_v1_stage1.py` | New: no request schema carries `uniqueItems`; answers the decoder now admits (duplicates, "no_evidence" with another value) are still scored invalid by `readers`, `protocol.score` and `run/score.score` |

**Check script and receipts.**

| File | Change |
|---|---|
| `scripts/check_evidence_memory_v1_structured_outputs.py` | Each test answer carries both expectations: does the decoder admit it, and is it valid under the protocol (the scorer's verdict, computed in the dump step). The receipt (schema v2) passes only if both Track 2 schemas are accepted, every valid answer passes decoder and scorer, and the scorer rejects every invalid answer the decoder admits |
| `reports/evidence_memory_v1_successor/structured_outputs_check_r2.json` | New receipt: both schemas accepted via xgrammar; the decoder admits exactly two invalid recall answers, and the scorer rejects both |
| `scripts/compare_evidence_memory_v1_token_audits.py` | New: compares each session's token audit row by row with an earlier revision |
| `reports/evidence_memory_v1_successor/token_counts_r1_vs_r2.json` | New receipt against `fb8cf77`. Every prompt count is identical (A: 1,728,220 tokens; B: 1,686,442); every recall request digest changed (A 2,144, B 2,096); every decision digest is unchanged |

**Rebuilt** (request bodies changed; prompts did not).

| File | Change |
|---|---|
| `research/evidence_memory_v1_session_{a,b}/token-audit.json` | New request digests; identical counts |
| `scripts/audit_evidence_memory_v1_tokens.py` | Writes its report to `token_cross_check_r2.json`; r1's `token_cross_check.json` is kept |
| `reports/evidence_memory_v1_successor/token_cross_check_r2.json` | New: the real-tokenizer cross-check on the new requests; summary identical to r1 except the audit hashes |
| `research/evidence_memory_v1_session_{a,b}/protocol.json` | The token-audit hash (and `protocol_document`, below) |
| `research/evidence_memory_v1_session_{a,b}/derivation.json` | Session inputs and source hashes; see the builder below |

## Decision 1: the unsupported-claim margins are read three ways (choice 5)

| File | Change |
|---|---|
| `research/evidence_memory_v1/protocol.py` | New `unsupported_margin`: `met` / `exceeded` / `not_shown` (`not_estimable` without an interval), with unchanged thresholds. `conclusions` maps `exceeded` to `..._outside_margin` and `not_shown` to the new `..._margin_not_shown`; only `met` advances. The docstring names the frozen protocol. Recorded as an exact change from `107d8b4` |
| `tests/test_evidence_memory_v1_protocol.py` | The existing case now reads `exceeded`. New tests: every branch including the inclusive boundaries (+0.02, +0.05, and just above each); the verdict for each outcome; that only `met` advances; and an end-to-end `not_shown` (point 0, wide interval) |

The consumers (`run/final.py`, `successor/final.py`) pass the verdict through unchanged, so their code did not change;
their pooled-analysis tests still give `memory_preserves_access_not_shown_over_retrieval` for exact readers.

## Decision 2: refuse and redraw (choice 8)

No code change: `successor/freeze.py withheld` already refuses on any failing trajectory and writes nothing.

| File | Change |
|---|---|
| `reports/evidence_memory_v1_protocol_v2_frozen.md` | §4 and §5 state the procedure |
| `reports/evidence_memory_v1_successor/owner_gates.md` | Gates 1 and 2: the redraw procedure, and the redraw record |

## Decision 3: session B launches only after session A is technically complete (choice 7)

| File | Change |
|---|---|
| `research/evidence_memory_v1/successor/session_order.py` | New. Checks the retained record `reports/evidence_memory_v1_session_a_technical_evaluation.json`: it must exist, match `session_a_technical_evaluation_sha256` in B's compute authorization, and show A live, on A's registered withheld set, technically complete and valid in every pass |
| `research/evidence_memory_v1_session_b/notebook.py` (derived) | `launch_artifacts` refuses unless the condition holds; when the live gate already refuses, it adds the record's reasons. It covers `launch-build`, `write_package` and `submit`. `source_names` adds `session_order.py`, so B's review lock binds it |
| `research/evidence_memory_v1_session_b/launch.py` (derived) | `claim` refuses unless the condition holds; the docstring says so |
| `scripts/evidence_memory_v1_session_b_package.py` (derived) | The docstring of `launch-build` |
| `tests/test_evidence_memory_v1_successor_session_order.py` | New, with fabricated fixtures only: absent record, unnamed or mismatched hash, not technically complete, invalid in a pass, not live, not withheld, wrong session or frozen set, and success. Also: B's launch package, `write_package`, `submit` and `claim` refuse and spend nothing; the per-scope live gate ignores A; A's tooling never reads the record; B's lock binds `session_order.py`; `launch-build` in this checkout names the missing record |
| `tests/test_evidence_memory_v1_successor.py` | `gated_fixture` retains a fabricated session-A record for B and names its hash in the fabricated compute authorization |
| `tests/test_evidence_memory_v1_successor_connected.py` | The check applied to real evaluator output. A complete rehearsal of A is refused only as "not live" and "not withheld"; the invalid-repeat and timeout rehearsals are refused as invalid and incomplete |

Session A's derived `binding.py`, `launch.py` and `launch_artifacts`, and session B's `binding.py`, are unchanged.

## Decisions 4 to 11 (choices 1, 2, 3, 4, 6, 10, 11, 12)

These need no code change; the packages already implement them. They are recorded in the frozen protocol: §11 (the
measured runtime, documentation only), §12 (two builds, both request ceilings in each compute authorization) and §15.
Gate 6 of `owner_gates.md` states the ceilings and B's extra field.

## The frozen document and its wiring

| File | Change |
|---|---|
| `reports/evidence_memory_v1_protocol_v2_frozen.md` | New: the protocol of record. Sections 1, 3, 6, 7, 8 and 10 are verbatim from the draft, and §13 keeps the draft's text after a note; the decided sections are replaced or amended. The name follows Track 4's convention (`progress_subgoal_v1_protocol_v2_frozen.md`): it is the frozen draft v2 |
| `scripts/build_evidence_memory_v1_sessions.py` | `PROTOCOL_DOCUMENT`, `FREEZE_AMENDMENTS` and `FREEZE_AMENDED_TESTS`, with `amended` and `baseline_of`. Each protocol gets `protocol_document`. Each review lock gets `review_documents`: the frozen protocol, the structured-output check script and its r2 receipt, the evaluator and pooled analysis, the token audit, the builder and the package script. Each review check verifies them. The B-only launch substitutions. In `derivation.json`, `track2_amended_at_protocol_freeze` records baseline and current hashes, and `baseline_files_modified` lists the four files (`preserves_baseline_files` is now false) |
| `research/evidence_memory_v1_session_{a,b}/notebook.py` (derived) | `REVIEW_DOCUMENTS`, and the lock's `review_documents` |
| `scripts/evidence_memory_v1_session_{a,b}_package.py` (derived) | `review-check` verifies the review documents |
| `scripts/run_evidence_memory_v1_successor_checks.py` | Reproduces the latest snapshot (r2) instead of r1, and runs the session-order suite |
| `tests/test_evidence_memory_v1_successor.py` | The baseline tests allow exactly the four amended files, and verify each amendment against the `107d8b4` blob. The snapshot test reproduces r2 and keeps r1 at its recorded lock hashes. New: the frozen document and the review documents are bound, and the r2 structured-output receipt is the one bound |

## New review snapshots (GPU-disabled; not approved)

| File | Content |
|---|---|
| `notebooks/evidence-memory-v1-session-{a,b}-review-r2/` | `profile.ipynb`, `kernel-metadata.json`, `review-source-lock.json`, built by each package script's `review-build --revision 2`. `LIVE_ENABLED` is False and the placeholders are unresolved |
| `reports/evidence_memory_v1_session_{a,b}_review_check_r2.json` | Each review notebook, executed with a decoy `nvidia-smi`, stops at the live gate |

## Documentation

`freeze_decisions.md` (each item marked decided on October 9, 2026), `open_protocol_choices.md` (a status note),
`owner_gates.md` (gate 0 done; the holder rule open in gate 1; the redraw procedure; B's compute-authorization field
and launch condition), `runtime_diff.md` (an addendum), this list, `README.md` and `verification.md`.
