# WS3 transition questionnaire v1: runner and review package r1

**Status.** GPU-disabled review snapshot. Authorized seconds are zero. There has been no reservation, upload or
model call. Source approval and a separately sized compute authorization would follow only after independent review.

| Item | Reference |
|---|---|
| Design | `reports/ws3_questionnaire_design_draft_r2.md` (draft r2.2, the freeze candidate) |
| Question set | `research/ws3_questionnaire_v1/probes.json` (3,116 questions, 5,616 scheduled calls), exported from `research/transition_evidence_v1/questionnaire.py` by `scripts/build_ws3_questionnaire_v1.py`; a fresh build is byte-identical |
| Scorer and decision rules | `research/transition_evidence_v1/score.py` (re-exported by `research/ws3_questionnaire_v1/score.py`) |

## 1. Reuse of the reviewed v3 stack

v3's runner and package files ran live as attempt `ecv3-089bf11f` and are reused, not edited.

| Kind | Files | Relation |
|---|---|---|
| **Derived** | `research/ws3_questionnaire_v1/{authority,host,worker,runner,resources,monitor,supervisor}.py`; the launch, package, review-build, notebook-review, rehearse, evaluate and check scripts; the connected, schedule, snapshot and diagnostics suites and fixtures | Exactly the v3 file, with v3's banner line dropped, the global v3 → WS3 renames, and counted per-file substitutions (`scripts/derive_ws3_questionnaire_v1.py`). A test fails on drift. |
| **Re-exported unchanged** | `schedule.py` (v2's call order; v1's admission rules), `evidence.py` (v2's append-only call log), `transport.py` (v1's), `score.py` (the WS3 scorer) | The same objects, checked by identity. |
| **Adapters** | `probes.py` (loads the frozen set and builds each request from the frozen evidence), `service.py` (v1's service with the WS3 allow-list and a 5,616-call ceiling), `fake_server.py` (scripted answers; wrong answers are another valid enum value) | Hand-written. None loads the v2 or v3 question sets. |

**Substitutions of substance:**
- authority limits allow 5,616 calls, and the required sources list the WS3 runtime, the questionnaire and its record
  code, and the reused v1 and v2 modules;
- the evaluator's `gate_status` requires both primary and over-claim-gate completeness, and the verdict is reported
  under the key `questionnaire`;
- rehearsal slow-latency faults (0.13 s and 0.06 s per call) are sized for a 2,500-call withheld pass;
- test numbers and report paths are updated.

**Provenance disclosure (v3 packaging slip).** v3's review-document list named the v2 diagnostics fixture files
instead of v3's (`tests/ecv3_diagnostics_*.py`), so v3's lock does not bind those two test-only files. They never
affected v3's runtime. For WS3 they are traced instead: they reproduce from v3's derivation, whose sources are bound
by v2's lock (test).

## 2. Notebook inventory

This is the import closure of the entry points, as in v2 and v3.
- **Byte-identical to what ran.** Every packaged file shared with v1's, v2's or v3's live-launch lock is
  byte-identical to what ran (test).
- **Closed.** Every repository import resolves inside the package (test).
- **No other question sets.** The v2, v3 and fixture question sets are not carried. v1's small set is carried,
  because v1's service constructor loads it.

## 3. What the tests show

| Requirement | Where |
|---|---|
| Keys derived three ways and agreeing; observable facts only; the candidate adds only facts recomputable from the reference evidence | `tests/test_ws3_questionnaire_draft.py` (Keys, Isolation) |
| Coverage floors; roles; extraction tagging; transfer labelled and descriptive | Coverage |
| Frozen schedule: withheld pass 1 with balanced condition order, pass 2 reversed, development and transfer once | Schedule, and `tests/test_ws3_questionnaire_v1_schedule.py` (derived) |
| Decision rules: reference meets, clear improvement, over-claim gates, invalid answers counting as over-claims, completeness policy, missing answers in every family × condition × pass, valid-only agreement | Rules, `ReviewOf93142fc`, `ReviewOfC8c0fd5` |
| Measurements, fixtures and the independent reference | `tests/test_transition_evidence_v1.py` |
| Every response retained and independently rescored; interruptions reported incomplete; fault handling | Connected suite (derived) |

## 4. Local results

RESULTS_PLACEHOLDER

These are CPU rehearsals with scripted answers. Their verdicts are artefacts of those answers, not results.

## 5. Budget proposal (for a separate compute authorization; nothing is authorized here)

From `reports/ws3_questionnaire_token_audit.json`: exact tokens from the pinned tokenizer, and scenarios fitted to v3's
measured calls, with overheads taken as the worse of v2 and v3 per component.

| Item | Value |
|---|---|
| Attempts | 1, no automatic retry |
| Authorized seconds | ≤ 3,600, with a 3,300 s internal limit and a 300 s cleanup reserve that is never spent |
| Calls | 5,616; canaries 1; game actions and submissions 0 |
| Prompt tokens | 10,390,311 scheduled; largest prompt 17,544 (transfer) |
| First cell (planning) | 1,849 s with the worst measured overhead; 2,454 s with the allowances (startup 1,228 s) |
| Primary (withheld) headroom | about 2.8× v3's call rate with measured overhead, about 2.0× with the allowances. Beyond that the withheld partition is cut and reported incomplete (the explicit budget decision in the design). |

## 6. Residual risks (disclosed; none accepted)

- **Inherited from v1.** The `late_abort` rehearsal test depends on the host not pausing.
- **The closure inventory.** A file reached only through a dynamically built path on an unexercised live branch
  would be missing. It was checked as for v2 and v3.
- **Longer prompts.** Transfer prompts reach 17.5k tokens, longer than anything v2 or v3 sent. The runtime fit was
  measured on shorter prompts.
- **What a result could show.** This is tool-assisted factual interpretation on synthetic fixtures, plus a small,
  previously exposed transfer group. It establishes neither unaided visual reasoning nor solving.

## 7. How to verify

```sh
python -m scripts.derive_ws3_questionnaire_v1 --check
python -m scripts.build_ws3_questionnaire_v1 --check
python -m scripts.check_ws3_questionnaire_v1
python -m scripts.review_ws3_questionnaire_v1_notebook --folder notebooks/ws3-questionnaire-v1-review-r1
```
