# Evidence-linked memory v1: Stage 1 protocol, version 2, frozen

**Status.**
- Frozen on October 9, 2026, by the owner decisions recorded in §16. From review snapshot r2 on, this is the protocol
  of record for both session packages (`research/evidence_memory_v1_session_a/` and `_session_b/`). Each session's
  `protocol.json` names it (`protocol_document`), and each r2 review lock binds its SHA-256 (`review_documents`).
- It supersedes the draft `reports/evidence_memory_v1_protocol_v2.md`, which is kept unchanged as history. Review
  snapshots r1 were built under the draft; they are kept byte-identical.
- **The science is the draft's.** The research question, arms, prompts, cases, seeds, horizons, metrics,
  denominators, availability ceilings, thresholds, failure rules, schedule and the technical-only session report are
  unchanged. Section numbers are the draft's, so code comments citing "protocol v2, section N" still point to the
  same section. Sections 1, 3, 6, 7, 8 and 10 are copied verbatim.
- **What changed from the draft**, each by an owner decision (§16):
  - §2: the recall decoding schema allows exactly the eight valid answers (October 9: without `uniqueItems`, which
    the verified runtime refuses; October 10: the exact enum). Scoring is unchanged.
  - §3, §10–§12: the withheld draw (October 10) fixes the exact calls, ceilings and repeat split; the earlier figures
    are the development stand-in's.
  - §4 and §5: a withheld draw with any failing trajectory is refused and redrawn; it is never thinned.
  - §5: one human holder, the owner, keeps the two copies of the withheld nonce (decided by the owner on
    October 9, 2026). The nonce was drawn on October 10, 2026, and its commitment is recorded in §5 (review
    snapshots r4).
  - §9: the unsupported-claim margins are read three ways (met, exceeded, not shown). The thresholds and the
    advancement rule are unchanged.
  - §11: the measured runtime figures replace the v3 estimates (documentation only).
  - §12: the two session packages, both request ceilings, and session B's dependency on session A's technical
    completion, enforced by session B's launch tooling.
  - §13 to §15: a note on the runtime, the status of the draft's remaining items, and the answers to its open
    questions.
- **A freeze is not an approval.** No withheld nonce has been drawn and no withheld set built. No model has been
  called. There has been no GPU run, upload, reservation, approval, compute authorization, claim or launch.

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
- a strict JSON schema for decoding (`stage1.response_schema`; for recall, exactly the eight valid answers, see
  below);
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
- **Cross-check on the Stage 1 requests.** Done, and rerun after the schema change below (§14).

**Identical requests.** At delay 0 several arms can receive identical evidence blocks, and so identical requests.
They stay separate scheduled calls. Their answers must agree, which is checked as part of stability.

**Decoding schema and response validation** (owner decision, October 9, 2026). Each request carries a strict JSON
schema for decoding (`stage1.response_schema`). The scorer then validates every answer (`readers.validate_response`)
before any correctness is computed.
- **The defect.** vLLM 0.19's default structured-output path (backend `auto`, as in the verified server argv) refuses
  the draft's recall schema because of `uniqueItems`. xgrammar does not support the keyword, and the llguidance
  fallback fails with `Unimplemented keys: ["uniqueItems"]`
  (`reports/evidence_memory_v1_successor/structured_outputs_check_r1.json`). The server would refuse every recall
  request, so session A would stop at its first recall call and spend its attempt with no result.
- **The change (October 9).** `uniqueItems` is dropped from the recall **decoding** schema.
- **The amendment (owner decision, October 10, 2026, after the withheld draw).** With `uniqueItems` gone, the
  decoder could emit a duplicate value, or "no_evidence" with another value. Both are invalid answers, and the
  withheld draw leaves session A's repeat with 48 answers per arm, where one invalid answer fails the 2% rule (§10).
  The recall decoding schema is therefore an object with exactly one key, `values`, whose value is one of the
  **eight valid answers in canonical order** (`stage1.RECALL_ANSWERS`): one to three distinct observed values, or
  "no_evidence" alone. The decision schema is unchanged.
- **Checked on the exact runtime install (CPU).** `structured_outputs_check_r3.json`: both schemas are accepted
  (xgrammar). Over every recall answer of one to four values, the decoder admits exactly the canonical form of each
  answer the scorer accepts, and nothing else.
- **Scoring is unchanged.** `readers.validate_response` still requires distinct values, and "no_evidence" on its
  own, in any order. An invalid answer is retained, counts in every denominator and against the 2% rule, and is
  never correct, unsupported or abstaining. The questions, the withheld sets and the prompt tokens are unchanged;
  only the request digests change.
- **Checked on CPU** with the exact runtime install (vLLM 0.19.0, xgrammar 0.1.34, llguidance 1.3.0, the pinned
  tokenizer; `reports/evidence_memory_v1_successor/structured_outputs_check_r2.json`):
  - both Track 2 schemas are accepted, through xgrammar;
  - the decoder admits every valid answer tested and rejects every structural error tested;
  - it admits exactly the two invalid answers above, and the scorer rejects both.
- **What was rebuilt.** The request bodies changed, so every recall request digest changed. The token audits, the
  session protocols and the review snapshots were rebuilt (r2). The prompts did not change: every prompt token count
  is identical, row by row, in both sessions
  (`reports/evidence_memory_v1_successor/token_counts_r1_vs_r2.json`).

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
- **Calls.** The repeat's size depends on which whole groups the run seed selects, so the withheld draw fixes the
  exact counts. The run packages use the withheld sets; the public rehearsal packages use the development stand-in.

  | Session | Pass 1 | Repeat (pass 2) | Total |
  |---|---|---|---|
  | A, withheld (October 10) | 2,592 | 192 (3 groups) | **2,784** |
  | B, withheld (October 10) | 2,592 | 368 (6 groups) | **2,960** |

  The development stand-in (`stage1.enumerate_requests`), for the public rehearsal packages:

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
| Trajectory | Fails v2 `verify_history`; or gold ≠ construction; or the faithful memory is not faithful under the independent checker; or a prompt fails to encode or exceeds 4,096 tokens | The whole withheld draw is refused and redrawn (below); a trajectory is never dropped. On development: 0. |
| Question | Evidence class `mixed` | Reported, never primary |
| Question | Recall whose truth is `no_evidence` | Uncertainty metrics only |
| Question | Decisions | Secondary |
| Question | Representation contrast, where the evidence is not available in **both** packages | Excluded from that contrast only; counts reported (dry run: 24 of 168 old questions) |
| Horizon | Delay 4 | Diagnostic |
| Arm | `full_history` | Diagnostic reference |

**Refuse and redraw** (owner decision, October 9, 2026). The trajectory conditions in the first row are
checked by `research/evidence_memory_v1/successor/freeze.py withheld` on every trajectory of the withheld draw,
before anything is written. `stage1.build` has no exclusion step, and none is added. If any withheld trajectory fails
any condition:
1. `freeze withheld` refuses, and no frozen set is written;
2. the failed commitment (`sha256(seed)`) and its failure counts, per condition, are published;
3. that nonce is discarded and never used again;
4. a new nonce is drawn and committed (§5);
5. the failed set is never inspected beyond the automated checks.

So a withheld set is always whole, with the designed denominators, and any redraw is on record. On development seeds,
336 of 336 trajectories pass every condition.

**Two families have no old-evidence factual question by design:** supported_then_contradicted and level_change,
which test revision.

## 5. Seeds

| Use | Seed |
|---|---|
| Development | `evidence-memory-v1-development` |
| Bootstrap | `evidence-memory-v1-stage1-bootstrap`, 10,000 resamples |
| Model requests | 0 |

**The withheld seed was drawn after every design decision in this document was fixed** (October 10, 2026, 01:40
UTC). Its commitment is `7f11432aed195bbd18732abd6cb513024b48e401de17c5fd27e11b17dadfb04b`. The procedure:

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

**A failed draw** is refused and redrawn (§4): the failed commitment and its counts are published, the nonce is
discarded, and a new nonce is drawn and committed afresh.

**Holder rule (owner decision of October 9, 2026, recorded before the draw).**
- **One human holder.** The owner draws the nonce and keeps both copies of step 3, stored separately outside
  every repository. The owner checks each copy personally by recomputing the commitment, which prints only the
  hash.
- **Limitation.** There is no independent second holder, so the owner is a single point of failure.
- **The draw.** Both copies were checked on October 10, 2026: copy A in the WSL home and copy B in the Windows user
  folder of the same computer, on separate filesystems. Both print the commitment above. They do not protect
  against losing that computer.
- **Records.** `reports/evidence_memory_v1_successor/nonce_custody.json`; the commitment is in
  `research/evidence_memory_v1/successor/seed-commitment.json` and in each session's `protocol.json`.

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

## 9. Analysis and decision rules (frozen)

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
5. **Unsupported claims: pilot margins, read three ways** (owner decision, October 9, 2026). The difference is
   memory minus recent, paired over all recall questions (§7). The thresholds are the draft's: point estimate
   ≤ +0.02 and 95% upper bound ≤ +0.05. The reading (`protocol.unsupported_margin`) has three outcomes:

   | Outcome | Condition | Reading |
   |---|---|---|
   | `met` | point ≤ +0.02 **and** upper bound ≤ +0.05 | The margin is met |
   | `exceeded` | point > +0.02 | Memory asserts unsupported values more often than the margin allows |
   | `not_shown` | point ≤ +0.02 **but** upper bound > +0.05 | Not measured precisely enough to show the margin |

   - Both bounds are inclusive. Without an interval the outcome is `not_estimable`, which is read like `not_shown`.
   - **Only `met` permits advancement.** The rule is therefore exactly as strict as the draft's two-way reading. The
     change only reports imprecision as imprecision, instead of as a failed margin.
   - Invalid outputs and abstention are reported alongside.

   *Why three outcomes.* With 960 pairs in 84 groups (about 11 per group, pooled over both sessions), the interval
   half-width is about 1.96 √(d·DEFF/960). Here *d* is the share of pairs where the two arms disagree on
   "unsupported", and DEFF is the design effect of clustering within groups. Track 4 saw 4% to 17% of paired questions
   change correctness when two arms differed in one prompt element, so *d* of 10–20% is plausible here.

   | Discordance *d* | Half-width, DEFF 2 | Half-width, DEFF 4 | Largest point estimate that still passes "upper ≤ +0.05" |
   |---|---|---|---|
   | 5% | 0.020 | 0.028 | +0.030 / +0.022 |
   | 10% | 0.028 | 0.040 | +0.022 / +0.010 |
   | 17% | 0.037 | 0.052 | +0.013 / below 0 |

   Macro-averaging over families adds variance, so these half-widths are lower bounds. At plausible discordance the
   upper-bound condition, not the point margin, decides, and a true difference near zero can fail it from imprecision
   alone. The draft's verdict could not tell that case from a difference that exceeds the margin.
6. **Diagnostics, never gates.** The forgetting difference (threshold 0.15 for `recent_raw`), recent controls, and
   decision accuracy.

**Verdicts.** These are implemented in `protocol.conclusions` and tested:

| Verdict | Meaning |
|---|---|
| `not_interpretable_cannot_isolate_retention_from_comprehension` | The floor failed |
| `memory_preserves_access_and_improves_over_retrieval` | Both contrasts positive, margin `met` |
| `memory_preserves_access_not_shown_over_retrieval` | Contrast 1 positive, contrast 2 not shown, margin `met` |
| `memory_preserves_access_unsupported_claims_outside_margin` | Contrast 1 positive, margin `exceeded` |
| `memory_preserves_access_unsupported_claims_margin_not_shown` | Contrast 1 positive, margin `not_shown` (or not estimable) |
| `access_preservation_not_shown` | Contrast 1 not shown |

The verdict names are the draft's, plus `..._margin_not_shown`; `..._outside_margin` now means `exceeded` only.

**Advancement** (Stage 2, or any closed-loop use) requires contrast 1 to be positive with the margin `met`,
that is, one of the two verdicts that follow the floor in the table above. A claim of advantage over
retrieval requires contrast 2 as well. Concision or readability never qualifies.

## 10. Failure rules (technical validity)

**A session is technically complete only if all of these hold:**
- **Calls.** Every scheduled call (pass 1 and the repeat) was answered. A timed-out, rejected or missing call leaves
  the session **incomplete**. Truncated answers count as answered and invalid.
- **Evidence.** The evaluator verifies the evidence: the retained calls are exactly a prefix of the frozen order,
  every request hash is re-derived, and token parity, timing and cancellation records all check out.
- **Recovered evidence.** Evidence recovered from an interrupted run is never complete.
- **Prefix caching off.** Verified from the server's own counters at the canary and at every call.
- **Invalid outputs.** At most 2% per arm **in every pass**: in pass 1, and separately in the repeat pass. Each is
  measured against that pass's own answered calls for that arm. In the withheld draw, session A's repeat has 48
  answers per arm, so one invalid answer in an arm fails the rule; session B's repeat has 92, so at most one. All
  invalid answers are retained, and both passes' counts, rates and verdicts are reported.
- **Timeouts.** At most 1% of calls. The reviewed runner also stops after its consecutive-timeout limit.
- **Model startup** within the reviewed ceiling.

**Technical validation and scientific analysis are separate steps.**

1. **Per session: technical only** (`run/score.analyze`, reported by the independent evaluator). It reports:
   - completeness;
   - answered and schema-valid counts per pass;
   - invalid answers per arm **for each pass** (pass 1 and the repeat), with their denominators, rates and the 2%
     rule; a session is valid only if every pass meets it;
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
   - each session is **independently evaluated by `run/final.py` itself**, on its exact retained output against its
     own frozen set, using the derived evaluator: lifecycle receipts, server evidence, call order, request hashes,
     timing, token parity, cancellations. No evaluation is accepted from outside;
   - each evaluation is **bound to its inputs**: a digest taken before and after evaluation covers every file in
     the output tree, the run manifest, call log and run index, the frozen set, and the evaluator's source. The
     digest of the evaluated inputs must equal that of the inputs being pooled, so a stale or substituted
     successful evaluation is refused;
   - each evaluation is technically complete, with a complete run, in `live` mode (rehearsal evaluations count only
     for the development stand-in);
   - each session's technical status, recomputed from its retained answers, is valid.

   It then pools both sessions' pass-1 answers into one analysis (§7–§9), and both repeats into one stability
   report. Otherwise it refuses and lists the reasons, with no outcome numbers. There is no per-session or
   incomplete-session scientific result.

## 11. Runtime estimate (measured on the verified runtime; labelled estimates, not authorizations)

**Owner decision (October 9, 2026): documentation only.** The draft's figures came from the v3 runtime (961 s
measured before the first question, and a 1,540 s allowance). They are replaced by measurements on the verified
runtime. The budget (§12) does not change. (`protocol.FIT` and `protocol.estimate_seconds` keep the v3 fit; they
decide nothing.)

**Basis.** Track 4's attempt ran the same runtime, model snapshot and lifecycle on one RTX PRO 6000
(`reports/progress_subgoal_v1_runtime2_attempt1_results.md` on `track4-successor-runtime-v1`). It split the overhead
before the first study call into:

| Phase | Seconds |
|---|---|
| Wheel integrity (all 174 mounted wheels hashed) | 31 |
| Hash-pinned installation | 85 |
| Model tree verification | 146 |
| Server start to ready | 113 |
| Startup and inference probes | about 26 |
| **First study call** | **at about 401 s** |

After the questionnaire, the cancellation probes and cleanup took about 5 s.

**Per-call time.** Fitted on 5,852 sequential calls:
- 0.0134 s per call, plus 2.11 × 10⁻⁵ s per prompt token, plus 0.0063 s per completion token;
- mean 0.114 s per call; p95 0.143 s.
- Track 4's prompts ran up to 5,675 tokens, but its completions were at most 10 tokens. The completion rate
  therefore extrapolates to Track 2's 64-token cap. It matches the v3 fit (0.0064 s).

**Re-derived estimates** (planning only). Track 2's prompts average about 597 tokens, with a maximum of 1,249. A
metrics read per call is allowed at 0.01 s.

| Session | Typical completions (about 20 tokens) | All completions at the 64-token cap | All at the cap, per-call time doubled |
|---|---|---|---|
| A (2,784 calls, withheld) | ≈ 860 s | ≈ 1,630 s | ≈ 2,850 s |
| B (2,960 calls, withheld) | ≈ 885 s | ≈ 1,705 s | ≈ 3,010 s: the last calls cut by admission |

**These are planning figures, not authorization ceilings.** The reviewed admission control enforces the deadline:
a call starts only if its whole per-call bound ends before the cutoff. An over-long session ends **incomplete**; it
never overruns. The verified runtime's own phase ceilings (installation 900 s, model verification 600 s, server
startup 900 s) all lie within the unchanged 3,000 s admission cutoff.

## 12. Run packages and budget (terms for each compute authorization; nothing is authorized)

**Packages** (owner decision: two builds). Session A is `research/evidence_memory_v1_session_a/`, session B
`research/evidence_memory_v1_session_b/`. Each is its own package build from the same code on the verified
direct-publisher runtime, with its own frozen set, token audit, review lock, approvals, claim, receipt and
reservation. A session-A authority cannot run session B. Both are GPU-disabled (`LIVE_ENABLED = False`). The
runtime-only changes from the draft's package are listed in `reports/evidence_memory_v1_successor/runtime_diff.md`.

| Item | Session A | Session B |
|---|---|---|
| **Maximum reservation** | **3,600 s** (`authorized_seconds`; internal lifecycle 3,300 s) | the same |
| **Admission cutoff** | **3,000 s** after the first-cell start; per-call bound 80 s | the same |
| **Cleanup reserve** | **300 s.** No admitted call can reach it. | the same |
| **Study completions** (the calls ceiling: the withheld schedule) | **2,784** | **2,960** |
| **Counted HTTP requests to the model server** (`maximum_model_requests`) | **≤ 186,540** | **≤ 198,332** |
| **Retry policy** | **No retry allowance.** `automatic_retries = 0` and `maximum_attempts = 1`. A failed or incomplete session is reported as such; any further attempt needs a new, separate approval. | the same |

**Both ceilings go into each compute authorization** (owner decision, October 9, 2026).
- **Study completions.** The study service refuses any request beyond the frozen schedule.
- **Counted HTTP requests.** The verified runtime's ledger counts every HTTP request to the server, and admits only
  planned request ids, each at most its permitted number of times:
  - the startup and inference probes (S1–S3, I1–I4) and the cancellation probes (C1–C3, with C2 issued up to twice);
  - one metrics read before the first study call (K0000);
  - per scheduled call, its completion (Q) and one metrics read (M) after an answer, or at most 65 idle-verification
    reads (V) after a timeout.
- The cap is the plan's worst case: 11 + 1 + 67 per scheduled call. A complete session issues at most 2 × calls +
  12 requests (5,580 for A and 5,932 for B). The worst case counts metrics reads, not model generations.
- The development stand-in's figures (2,896 / 2,832 completions; 194,044 / 189,756 requests; 5,804 for A in
  rehearsal) apply to the public rehearsal packages only.

**Proposed GPU budget: 2 sessions × 3,600 s reserved = 2 GPU-hours reserved.** The expected use is lower: about
900 s per session on the measured figures (§11), which is an estimate. **The reservation, not the estimate, is the
ceiling.**

**Stop rules:**
- **After session A, only technical rules may stop the experiment.** No outcome metric exists before B: the
  session-level evaluation is technical only (§10).
- **Session B launches only after session A is technically complete** (owner decision, October 9, 2026; enforced).
  - Session B's compute authorization names `session_a_technical_evaluation_sha256`: the SHA-256 of session A's
    retained technical evaluation, the output of `research/evidence_memory_v1/successor/evaluate.py` for A's output,
    retained at `reports/evidence_memory_v1_session_a_technical_evaluation.json`.
  - Session B's launch tooling refuses unless that record exists in B's checkout, matches the named hash, and shows
    session A in live mode, on A's registered withheld frozen set, technically complete and valid in every pass
    (`research/evidence_memory_v1/successor/session_order.py`). The tooling covers the claim and the launch package
    (`launch-build`, `write_package`, `submit`).
  - This is launch tooling, not the reviewed per-scope live gate (`binding.require_live`), which also runs inside the
    Kaggle payload and stays per scope. It follows the Track 4 seed-gate pattern. Session A's tooling never reads it.
  - If session A is not technically complete, no pooled analysis is possible: the experiment stops, and session B is
    never launched.
- **The analysis runs once,** on A and B pooled, by `research/evidence_memory_v1/successor/final.py` (the rules of
  `run/final.py`), after both are technically valid. It refuses anything less.

## 13. The GPU-disabled run package

**On the verified runtime** (a note added at the freeze). The run stack below is the reviewed science stack. Inside
the session packages (§12), its lifecycle pieces (authority, host, worker, supervisor, monitor, resources, the phase4
installation and the bridge) are replaced by the verified direct-publisher lifecycle. Its science pieces are reused
unchanged: the frozen set and request builder, the schedule and admission, the call log and evidence, scoring, the
technical report and the pooled analysis. The changes are runtime-only and are listed in
`reports/evidence_memory_v1_successor/runtime_diff.md`. The draft's text follows unchanged.

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
  - invalid answers are retained and counted against the 2% rule in each pass;
  - a fully valid pass 1 with an invalid repeat pass leaves the session not valid;
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

## 14. Status of the draft's pre-lock items (at the freeze)

1. **Tokenizer cross-check:** done, and rerun after the schema change. transformers 4.57.6 equals the pure-Python
   count on all 5,728 requests, and every context fits its budget under transformers too
   (`reports/evidence_memory_v1_successor/token_cross_check_r2.json`).
2. **Connected rehearsals in POSIX:** done on the verified runtime, both sessions and the fault matrix
   (`tests/test_evidence_memory_v1_successor_connected.py`; `reports/evidence_memory_v1_successor/verification.md`).
3. **Design decisions:** fixed by this freeze (§16). The holder rule was decided before the draw (§5). The
   withheld nonce is drawn and committed (§5); the withheld frozen sets are built only in a private checkout
   (owner gate 2). The package check that refuses
   `development_stand_in`, or a seed hash that does not match the commitment, exists
   (`successor/plan.live_frozen_set_reasons`).
4. **Packaging and review lock:** two session packages on the verified runtime, with GPU-disabled review snapshots r2
   bound to this document.
5. **Approvals:** none. Every remaining step is an owner gate, in order, in
   `reports/evidence_memory_v1_successor/owner_gates.md`: the holder rule and the seed, the withheld sets, the private
   bindings, the scope evidence, enabling the live path in a reviewed revision, and the approvals, reservation and
   launch of each session. Session B comes only after session A's technical completion (§12).

## 15. The draft's open questions, answered at the freeze

1. **Two package builds or one?** Two builds, A and B (§12).
2. **The repeat split.** Kept: 9 of 84 whole groups, one in every family and then two more, covering every family
   across both sessions. The split between sessions follows the draw: 3 in A and 6 in B for the withheld sets (5 and
   4 in the stand-in). The repeat measures stability only and never enters an endpoint.
3. **Admission granularity.** Kept: the reviewed per-call admission. No group-level admission is added.
4. **Duplicate requests.** Every scheduled call is asked; identical requests are not shared. Their answers must agree
   under temperature 0 and seed 0, which doubles as a determinism check.
5. **Margins.** Kept at +0.02 / +0.05, read three ways (§9).

## 16. Decisions recorded at the freeze (October 9, 2026)

All were decided by the owner on October 9, 2026. The decision record is
`reports/evidence_memory_v1_successor/freeze_decisions.md`; the options and reasons are in `open_protocol_choices.md`.
The files changed for each decision are listed in `reports/evidence_memory_v1_successor/freeze_change_list_r2.md`.

0. **Recall response schema** (blocking defect; choice 9): drop `uniqueItems` from the decoding schema only. Scoring is
   unchanged (§2). **Amended by the owner on October 10, 2026, after the withheld draw:** the recall decoding schema
   allows exactly the eight valid answers, so the decoder cannot emit an invalid recall answer (§2).
1. **Unsupported-claim margins** (choice 5): both thresholds kept, read three ways; only `met` permits advancement
   (§9).
2. **Trajectory exclusions** (choice 8): refuse and redraw. No science-code change (§4, §5).
3. **Session B after session A** (choice 7): enforced in session B's launch tooling and bound by hash in B's compute
   authorization (§12).
4. **Package builds** (choice 1): two, A and B (§12).
5. **Repeat split** (choice 2): 9 whole groups, split as the draw falls; 3 + 6 for the withheld sets (§3).
6. **Admission granularity** (choice 3): per-call admission.
7. **Duplicate requests** (choice 4): every scheduled call is asked.
8. **Runtime estimate** (choice 6): §11 replaced by the measured figures; documentation only.
9. **Request cap** (choice 10): the worst case, 186,540 for A and 198,332 for B for the withheld sets, stated in
   each compute authorization with the 2,784 / 2,960 completion ceilings (§12).
10. **Tokenizer admission** (choice 11): the offline pinned-tokenizer audit, rerun on the withheld sets before the
    run.
11. **Teammate stress set** (choice 12): kept out of Stage 1.

**Decided after the freeze, before the draw:** one human holder, the owner, keeps the two copies of the withheld
nonce (§5; owner gate 1). The nonce was drawn and committed on October 10, 2026.
