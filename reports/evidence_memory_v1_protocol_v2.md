# Evidence-linked memory v1: Stage 1 protocol, version 2 (DRAFT for review, not frozen)

**Status: draft for review.**
- Nothing is frozen, scheduled, reserved or approved.
- **The run package is GPU-disabled.** Its authority refuses every live request before reading any approval.
- Every number is CPU-only measurement on development cases, with exact readers or scripted fake answers standing in
  for a model.
- The budget in §12 is a proposal. **Estimated runtime is not an authorization ceiling;** see §11 and §12.
- Version 1 (`reports/evidence_memory_v1_protocol_v1.md`) stays as history.

**Changes from version 1, applying the review of `22ce694`:**
- **Primary endpoint.** Old-evidence factual accuracy under the common token budget. The recent-minus-old
  difference and recent controls are now diagnostics. A smaller difference can come from *worse* recent accuracy;
  a regression test shows it is no longer rewarded.
- **Two predeclared contrasts**, with separate conclusions. The representation contrast is restricted, question by
  question, to evidence available in both packages.
- **Repeat.** One pass, plus a preselected 10% repeat of whole groups covering every family.
- **Thresholds re-scoped.** 0.80 is an interpretability floor and 0.15 a diagnostic.
- **The withheld seed.** It is drawn only after the design is fixed, and the protocol specifies how it is retained
  securely.
- **Scope.** Generalisation within the generator only.
- **New software:** a GPU-disabled run package derived from the reviewed WS3 stack, and a request enumeration for
  the tokenizer cross-check.

## 1. Research question

> Does evidence-linked memory preserve access to action-relevant facts when those facts fall outside the
> recent-history window?

**What is measured: loss of access under a restricted context.** It is not necessarily forgetting inside the model.

**The setup.**
- The memory is written by the **deterministic faithful writer** (`writers.Faithful`).
- The model is **the reader only**.
- Stage 1 therefore tests **memory access and representation**, not the model's ability to write faithful memories
  or to complete levels.

**What is compared:** context packages (store, selection, rendering) at a common token budget. Prompt formatting
alone is not what is compared.

**Scope.** The withheld cases are **new synthetic instances from the same generator**. They test generalisation
within the generator, **not** to unfamiliar real games.

## 2. Arms

**What is the same in every arm:**
- the model and decoding (temperature 0, request seed 0, `max_tokens` 64, prefix caching off);
- one system message describing both formats (`protocol.SYSTEM`);
- the question text and answer form;
- a strict JSON schema (`stage1.response_schema`);
- response validation before scoring (`readers.validate_response`).

**What differs:** only the evidence block.

| Arm | Evidence block | Budget | Role |
|---|---|---|---|
| `recent_raw` | The last 6 transition records (window frozen) | Defines the budget | Primary |
| `state_keyed_raw` | Raw records from the current exact state first, then the most recent | The common budget | Primary |
| `memory` | Faithful-writer entries ranked by how specifically their scope covers the current state | The common budget | Primary |
| `full_history` | Every record | More context, unbudgeted | **Diagnostic reference only; excluded from every comparison** |

**The common token budget, per trajectory:**
- **Definition.** It is the token count, under the pinned tokenizer, of that trajectory's rendered `recent_raw` block
  (119–264 tokens on development).
- **The tokenizer.** Qwen3-VL-30B-A3B-Instruct-FP8, revision `d9748a51`, hash-pinned files. `tokens.py` is a
  pure-Python reimplementation for these prompts. It reproduces the committed `transformers` audit exactly: 3,116
  of 3,116 prompt counts.
- **Cross-check on the Stage 1 requests.** It is pending (§14).

**Identical requests.** At delay 0 several arms can receive identical evidence blocks, and so identical requests.
They stay separate scheduled calls. Their answers must agree, which is checked as part of stability.

## 3. Cases

- **Families.** Seven synthetic families, each one continuous episode through `transition_evidence_v2`, with no
  masks.
- **Groups.** A **group** is one (family, group index). It is generated at delays 0, 4, 8 and 16 from one
  construction seed, so its horizons share their starting state and early actions.
- **Pilot size.** **12 groups per family: 84 groups, 336 trajectories.** This is a pilot. It promises no sensitivity
  to small differences.
- **Sessions.** **Two sessions:**
  - **A:** groups 0–5;
  - **B:** groups 6–11.

  Each session is a balanced replicate (every family, horizon and arm).
- **Questions per trajectory.**
  - **Family questions:** 2–4 per trajectory, recall and decision.
  - **One recent-control question.**
  - Each question is asked under all four arms.
- **Calls** (`stage1.enumerate_requests`, development stand-in):

  | Session | Pass 1 | Repeat (pass 2) | Total | Prompt tokens, mean / max |
  |---|---|---|---|---|
  | A | 2,592 | 304 (5 groups) | **2,896** | 597 / 1,247 |
  | B | 2,592 | 240 (4 groups) | **2,832** | 595 / 1,249 |

- **The repeat.** It is **one pass plus a preselected 10% repeat**:
  - **Selection.** Whole groups, 9 of 84 (`stage1.repeat_groups`): one in every family, then two more, all drawn
    from the run seed before the run.
  - **What it measures.** Response stability of one deterministic configuration. **It is not additional independent
    samples.** Repeat answers never enter the endpoints.
- **Withheld cases.** They are newly generated withheld trajectories (§5). Every development-generated trajectory,
  including those used here and in earlier Track 2 reports, stays development.

## 4. Exclusions (fixed before the run)

| Level | Excluded | Where it goes instead |
|---|---|---|
| Trajectory | Fails v2 `verify_history`; or gold ≠ construction; or the faithful memory is not faithful under the independent checker; or a prompt fails to encode or exceeds 4,096 tokens | Excluded before the run, not replaced, reported. On development: 0. |
| Question | Evidence class `mixed` | Reported, never primary |
| Question | Recall whose truth is `no_evidence` | Uncertainty metrics only |
| Question | Decisions | Secondary |
| Question | Representation contrast, where the evidence is not available in **both** packages | Excluded from that contrast only; counts reported (dry run: 24 of 168 old questions) |
| Horizon | Delay 4 | Diagnostic |
| Arm | `full_history` | Diagnostic reference |

**Two families have no old-evidence factual question by design:** supported_then_contradicted and level_change,
which test revision.

## 5. Seeds

| Use | Seed |
|---|---|
| Development | `evidence-memory-v1-development` |
| Bootstrap | `evidence-memory-v1-stage1-bootstrap`, 10,000 resamples |
| Model requests | 0 |

**The withheld seed is not drawn in this pass.** It is drawn only after every design decision in this document is
fixed. Then:

1. **Drawing.** A person draws `nonce = secrets.token_hex(16)`. The run seed is
   `evidence-memory-v1-stage1-withheld/` + nonce.
2. **Commitment.** Only `sha256(seed)` goes into the frozen protocol and the package. The frozen set records it as
   `seed_sha256`.
3. **Secure retention.** The nonce is stored **outside the repository** in two places: a private note held by the
   person who drew it, and a secret held by the run operator. It is never committed, never pasted into a
   conversation with a model, and never put in a notebook output.
4. **Building.** The run package's frozen sets (`stage1.build(session, seed, partition='withheld',
   case_source='withheld')`) are built from the seed after approval. Only automated checks inspect them before the
   run: exclusions, faithful memory, budget fit and the token cross-check. No person reads the questions or answers.
5. **Reproducing.** After the run, the nonce is published in the results report. Anyone can then rebuild the exact
   cases and verify the commitment.

If the nonce is lost before the run, a new nonce is drawn, committed afresh, and the loss is recorded. If it is lost
after the run, the results stand, but they are recorded as not independently reproducible.

## 6. Horizons

**Delays:** 0, 4, 8 and 16 distractor transitions, with the window frozen at 6.

**Evidence classes.** Each question is classified from the records: `recent`, `old`, `mixed` or `none`.

| Questions | Delays |
|---|---|
| Recent-evidence family questions | 0 |
| Old-evidence family questions | 8 and 16 |
| Recent controls | Every delay |

## 7. Metrics and denominators

**Unit of analysis: the group.** Questions within a group, and a group's horizons, share construction, so they are
not independent.

**How each metric is computed:**
1. per group;
2. then averaged per family;
3. then macro-averaged over families, with equal family weight.

**Intervals.** Stratified cluster bootstrap, resampling groups within families. Contrasts pair the same question
across arms.

**Invalid outputs** fail the schema. They are retained, count in every denominator, and are never correct.

| Metric | Definition | Denominator (development dry run) |
|---|---|---|
| **Primary: old-evidence accuracy** | Truth-correct / factual family recall, old class, delays 8 and 16 | 168 questions, 60 groups per arm |
| **Contrast 1: memory vs recent history** | Paired difference in old-evidence accuracy | 168 pairs, 60 groups |
| **Contrast 2: memory vs state-keyed retrieval** | Same | 168 pairs, 60 groups |
| Contrast 2, restricted to evidence in both packages | Same, over pairs whose package-relative truth equals the full-history truth in **both** packages | 144 eligible, 24 excluded |
| Unsupported-claim difference (memory minus recent) | Paired, over all recall questions | 960 pairs, 84 groups |
| Diagnostic: forgetting difference | Per group, recent (delay 0) minus old (delays 8 and 16) accuracy, in the five families with both | 60 groups |
| Diagnostic: recent controls at old delays | Truth-correct / recent-control questions at delays 8 and 16 | 168, 84 groups |
| Reading accuracy (comprehension floor) | Package-correct / recall questions whose package holds evidence | Arm-specific |
| Abstention (reported) | Correct abstention when the package lacks evidence; overuse when it holds evidence | Arm-specific |
| Invalid outputs (reported) | Invalid / scheduled | 1,296 per arm per session pair |
| Secondary: decision accuracy | Old or none class, delays 8 and 16 | 120, 60 groups |
| Cost | Prompt and completion tokens per call, seconds per arm. Writer: 0 model calls. | Per call and per group |
| Stability (repeat) | Identical answers / repeated questions, by arm | 544 repeated calls |

## 8. Availability ceilings (exact readers, development, 12 groups per family)

| | recent_raw | state_keyed_raw | memory | full_history (reference) |
|---|---|---|---|---|
| **Old-evidence accuracy (primary)** | 0.00 | 0.90 | 0.90 | 1.00 |
| Contrast 1 (memory − recent) | | | **+0.90** | |
| Contrast 2 (memory − state-keyed), all old questions | | | **0.00** | |
| Contrast 2, evidence in both (144 of 168) | | | **0.00** | |
| Forgetting difference (diagnostic) | 1.00 | 0.10 | 0.00 | 0.00 |
| Recent controls at old delays (diagnostic) | 1.00 | 1.00 | 0.321 | 1.00 |

**How to read this table:**
- **Contrast 1 measures access; contrast 2 measures improvement over a simpler retriever.** They support different
  conclusions. Beating recent history alone does not show an advantage over retrieval.
- **Contrast 2 is about representation.** Memory and state-keyed retrieval hold the same old facts. So the
  representation contrast (contrast 2 restricted to evidence in both packages) asks whether the *model* reads one
  representation better than the other, at equal availability.
- **The exact readers' verdict on these cases** would be `memory_preserves_access_not_shown_over_retrieval`.

## 9. Analysis and decision rules (provisional)

1. **Technical validity (§10).** If it fails: no verdict.
2. **Pilot interpretability floor.** Both conditions must hold:
   - reading accuracy ≥ 0.80 in every primary arm;
   - `recent_raw` recent-evidence accuracy ≥ 0.80.

   If either fails, the conclusion is: **"this experiment cannot isolate retention from comprehension"**. It is not
   proof that comprehension is the sole cause.
3. **Contrast 1: does memory preserve access?** If its 95% interval lies above 0, yes; below 0, memory loses access;
   otherwise no difference detected.
4. **Contrast 2: does memory improve over simpler retrieval?** Same reading. Any representation-specific claim uses
   **only** the restricted contrast, with its eligible and excluded counts reported.
5. **Unsupported claims (provisional margins).** Memory minus recent: point estimate ≤ +0.02 and upper bound ≤
   +0.05. Invalid outputs and abstention are reported alongside.
6. **Diagnostics, never gates.** The forgetting difference (threshold 0.15 for `recent_raw`), recent controls, and
   decision accuracy.

**Verdicts.** These are implemented in `protocol.conclusions` and tested:

| Verdict | Meaning |
|---|---|
| `not_interpretable_cannot_isolate_retention_from_comprehension` | The floor failed |
| `memory_preserves_access_and_improves_over_retrieval` | Both contrasts positive, margins met |
| `memory_preserves_access_not_shown_over_retrieval` | Contrast 1 positive, contrast 2 not shown |
| `memory_preserves_access_unsupported_claims_outside_margin` | Contrast 1 positive, margin failed |
| `access_preservation_not_shown` | Contrast 1 not shown |

**Advancement** (Stage 2, or any closed-loop use) requires contrast 1 to be positive with margins met. A claim of
advantage over retrieval requires contrast 2 as well. Concision or readability never qualifies.

## 10. Failure rules (technical validity)

**A session is technically complete only if all of these hold:**
- **Calls.** Every scheduled call (pass 1 and the repeat) was answered. A timed-out, rejected or missing call leaves
  the session **incomplete**. Truncated answers count as answered and invalid.
- **Evidence.** The evaluator verifies the evidence: the retained calls are exactly a prefix of the frozen order,
  every request hash is re-derived, and token parity, timing and cancellation records all check out.
- **Recovered evidence.** Evidence recovered from an interrupted run is never complete.
- **Prefix caching off.** Verified from the server's own counters at the canary and at every call.
- **Invalid outputs.** At most 2% per arm (all retained).
- **Timeouts.** At most 1% of calls. The reviewed runner also stops after its consecutive-timeout limit.
- **Model startup** within the reviewed ceiling.

**Technical validation and scientific analysis are separate steps.**

1. **Per session: technical only** (`run/score.analyze`, reported by the independent evaluator). It reports:
   - completeness;
   - answered and schema-valid counts per pass;
   - invalid answers per arm, against the 2% rule;
   - a SHA-256 over the retained answers;
   - a technical status: `incomplete`, `session_technically_invalid_outputs` or `session_technically_valid`.

   It reports **no** accuracy, contrast, forgetting, abstention, unsupported claims, stability or scientific
   verdict. This applies to any session, including session A before session B runs; no command or report produced
   after session A carries an outcome-bearing number.
2. **Once, on both sessions pooled** (`run/final.py`). It runs only if:
   - exactly sessions A and B are present, once each;
   - each is bound to its registered frozen-set hash and names itself;
   - both share one seed commitment and case source (`withheld`) and split groups 0–11;
   - each retained run names its frozen set;
   - each evaluation is technically complete;
   - each session's technical status, recomputed from its retained answers, is valid.

   It then pools both sessions' pass-1 answers into one analysis (§7–§9), and both repeats into one stability
   report. Otherwise it refuses and lists the reasons, with no outcome numbers. There is no per-session or
   incomplete-session scientific result.

## 11. Runtime estimate (labelled estimates, not authorizations)

**Basis.** The v3 live fit: 0.0394 s per call, 1.42 × 10⁻⁵ s per prompt token, 0.00642 s per completion token.

**Overheads.**
- **Measured:** 961 s before the first question, 4 s after.
- **Allowances:** 1,540 s before, 30 s after.

**Completions.** Twice the key answer's tokens (typical), or the 64-token cap (worst case).

| Session (estimate) | Question time, typical / cap | Measured overhead, v3 rates | Allowance, v3 rates | Allowance, 2× slower | Allowance, all at cap | Allowance, 3× slower, all at cap |
|---|---|---|---|---|---|---|
| A (2,896 calls) | 534 / 1,328 s | ≈ 1,499 s | ≈ 2,104 s | ≈ 2,637 s | ≈ 2,898 s | ≈ 5,555 s: truncated by admission |
| B (2,832 calls) | 520 / 1,299 s | ≈ 1,485 s | ≈ 2,090 s | ≈ 2,609 s | ≈ 2,869 s | ≈ 5,467 s: truncated by admission |

**These are planning figures, not authorization ceilings.** The reviewed admission control enforces the deadline:
a call starts only if its whole per-call bound ends before the cutoff. An over-long session ends **incomplete**; it
never overruns.

## 12. Run package and proposed budget (proposal only)

**Package:** `research/evidence_memory_v1/run/`. It is GPU-disabled; §13 describes it.

| Item | Value |
|---|---|
| **Session count** | **2** (A and B). Each is its own package build from the same code: its own frozen set, review lock and reservation. |
| **Maximum reservation per session** | **3,600 s** (the authority's `authorized_seconds`; internal lifecycle 3,300 s) |
| **Admission cutoff** | **3,000 s** after the first-cell start (internal 3,300 s minus the cleanup reserve) |
| **Cleanup reserve** | **300 s.** No admitted call can reach it. |
| **Calls ceiling per session** | 2,896 (the service refuses any request beyond the frozen schedule) |
| **Retry policy** | **No retry allowance is approved.** `automatic_retries = 0` and `maximum_attempts = 1` per session. A failed or incomplete session is reported as such. Any further attempt would need a new, separate approval. |

**Proposed GPU budget: 2 sessions × 3,600 s reserved = 2 GPU-hours reserved.** The expected use is lower: about
1,500–2,100 s per session, which is an estimate. **The reservation, not the estimate, is the ceiling.**

**Stop rules:**
- **After session A, only technical rules may stop the experiment.** No outcome metric exists before B: the
  session-level evaluation is technical only (§10).
- **The analysis runs once,** on A and B pooled, by `run/final.py`, after both are technically valid. It refuses
  anything less.

## 13. The GPU-disabled run package

**Derived from the reviewed WS3 questionnaire v1 stack** (`research/evidence_memory_v1/derive_run.py`), on the same
pattern as `scripts/derive_ws3_questionnaire_v1.py`:
- each file is an exact copy of its WS3 source;
- ordered global renames are applied;
- per-file substitutions follow, each required to match an exact count;
- a residue check refuses leftover WS3 names;
- a drift test enforces all of this (`tests/test_evidence_memory_v1_run.py`).

**Derived (12 files):**
- runtime: authority, host, worker, runner, resources, monitor, supervisor;
- launcher, rehearsal and evaluator: `run/launch.py`, `run/rehearse.py`, `run/evaluate.py`;
- the rehearsal fake vLLM: `run/fake_vllm.py`, from v1's fake server;
- the connected rehearsal test: `tests/test_evidence_memory_v1_run_connected.py`.

**Substitutions:**
- module depth (`ROOT`);
- the review-lock path (`-r1`, which does not exist yet);
- the call ceiling (2,896);
- the required-source bindings;
- **`LIVE_ENABLED = False`**, refusing live before any approval is read;
- the rehearsal slow-fault latencies, derived from the frozen schedule (`run/rehearsal_timing.py`);
- the fake vLLM's canary test and per-call latency, which become overridable methods with v1's rules as defaults;
- the connected test's counts, answer shapes and technical-only evaluation check.

**Hand-written adapters:**
- `run/probes.py`: the frozen set and the request builder;
- `run/score.py`: schema-first scoring and the **technical-only** session report (§10);
- `run/final.py`: the registered two-session analysis, the only source of scientific results (§10);
- `run/service.py`: the Stage 1 allow-list;
- `run/fake_server.py`: the scripted answers. The canary is identified by request hash, and the repeat-pass
  slowdown applies only after pass 1;
- `run/rehearsal_timing.py`: the slow-fault latencies and their margins;
- `run/schedule.py`, `run/evidence.py`, `run/transport.py`: reviewed modules, re-exported unchanged. Evidence keeps
  WS3's committed-state recovery.

**Call order (group-interleaved admission).**
- **Pass 1** lists every probe, group by group: all horizons, arms and questions of a group together, with families
  interleaved.
- **The reviewed per-call admission** then stops at the cutoff. A truncated session therefore has at most one
  partial group (tested at every 97th cut point).
- **Repeat calls** follow pass 1.

**The call log.** The reviewed append-only log records each call's request hash, status, response, tokenizer and
server token counts, finish reason, cache check and host timing.

**The evaluator** is derived from WS3's. It re-derives every request hash from the frozen set, checks the lifecycle
receipts, timing, token parity and cancellations, and scores only the retained responses. Per session, it reports
only the technical `run/score.analyze`. Scientific results come only from `run/final.py`, on both sessions.

**Rehearsals:**
- **In-process, platform-independent.** The fake server's scripted answers go through the evaluator's scoring and
  the technical session report:
  - the report carries no outcome-bearing word;
  - invalid answers are retained and counted against the 2% rule;
  - a changed response changes the answer hash;
  - a missing answer makes the session incomplete;
  - truncated answers are invalid, never parsed.

  The two-session analysis refuses one session, an invalid or unbound session, swapped or duplicated sessions, and
  the development stand-in. On two valid sessions it equals the analysis of the concatenated rows.
- **Connected, CPU fake server over HTTP** (derived from WS3's ten connected rehearsals). They need POSIX. The main
  session ran all ten in WSL at `b1b7681`, and all passed, after two fixes:
  - the fake server had counted every Stage 1 question as the canary, so no fault fired;
  - the slow-fault latency is now derived from the schedule.

  Their technical-only check changed after that run.

## 14. Before an exact source and package lock

1. **Tokenizer cross-check.** Run `research.evidence_memory_v1.stage1.enumerate_requests()` against pinned
   `transformers` 4.57.6 in the isolated WSL environment. Every one of the 5,728 requests' `apply_chat_template`
   counts must equal `pure_python_prompt_tokens`, and each context must fit its budget under `transformers` too.
2. **Connected rehearsals in POSIX.** Rerun `tests/test_evidence_memory_v1_run_connected.py` on the current
   revision, because its technical-only evaluation check changed after the passing run at `b1b7681`. Retain the
   rehearsal results.
3. **Fix the design decisions,** then draw the withheld nonce (§5) and commit its hash. Build both sessions' frozen
   sets with `case_source='withheld'`, and add a package check that refuses `development_stand_in` or a seed hash
   that does not match the commitment. The development stand-in currently sits where the frozen set will go.
4. **Packaging and review lock.** Not derived in this pass: the WS3 package builder, notebook, review builder and
   snapshot test. They need a review revision with source bindings for both sessions.
5. **Approvals.** Source approval, compute authorization and one reservation per session, all separate and
   human-made. `LIVE_ENABLED` stays `False` until then.

## 15. Open questions for review

1. **Two package builds or one?** Two sessions currently mean two package builds, each locked separately, with
   shared code and different frozen sets. Is a single package that selects its session from a locked frozen file
   preferred?
2. **The repeat split.** It is 9 of 84 groups, falling 5 in session A and 4 in B, and covering every family only
   across both sessions. Should each session's repeat cover every family on its own? That needs 7 groups per session
   (about 17% of a session).
3. **Admission granularity.** Admission stays the reviewed per-call rule. Should a group-level admission (refuse to
   start a group that cannot finish at measured rates) be added, at the cost of modifying the reviewed runner?
4. **Duplicate requests.** Identical requests across arms at delay 0 are asked separately. Should they be asked once
   and the answer shared, saving calls but coupling the arms?
5. **Margins.** Are the unsupported-claim margins (+0.02 / +0.05) acceptable as provisional pilot values?
