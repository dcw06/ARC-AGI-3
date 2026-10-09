# progress_subgoal_v1 runtime2: readiness record (no approval, no compute authority)

Prepared 2026-10-08/09 on branch `track4-successor-runtime-v1` (from `origin/track4-progress-subgoal-v1` at `4cedb1f`).
CPU only. No GPU, provider or Kaggle API call, upload, notebook submission, reservation, approval or compute
authorization was made, and no such record exists in this branch. Every rehearsal below is a scripted CPU rehearsal:
**not GPU, model or runtime-compatibility evidence**, and labels produced by scripted answers are not results.

## 1. What exists

| Item | Where |
|---|---|
| Successor package (runtime2) | `research/progress_subgoal_v1_runtime2/` (derivation record `derivation.json`) |
| Verified controller, copied unchanged from `5a21dd3` | `certification/direct_publisher_smoke_v1/` and its 9 regression suites `tests/test_direct_publisher_smoke*.py` |
| GPU-disabled review snapshot **r5** | `notebooks/progress-subgoal-v1-runtime2-review-r5/` — review-source-lock SHA-256 **`0cf45e6ccaf88bb956289e2b9b05729d0e9e9078c633e0994b35aea1592d4feb`**; notebook 565,066 bytes; 60 bound runtime sources; 15 bound review documents; supersedes r4 (`e7e1518b…`, unchanged) |
| Runtime-binding inventory | `reports/progress_subgoal_v1_runtime2_binding_inventory.md` |
| Runtime-only source diff | `reports/progress_subgoal_v1_runtime2_source_diff.md` / `.json` |
| Exact token audit | `research/progress_subgoal_v1_runtime2/token-audit.json`; planning scenarios `reports/progress_subgoal_v1_runtime2_budget.json` |
| CPU check receipts (fresh WSL clone of the committed branch) | `reports/progress_subgoal_v1_runtime2/`, `reports/progress_subgoal_v1_diagnostics/runtime2-branch-old-suite-2.json` (+ `.rehearsals.jsonl`) |

## 2. Third arm: what the protocol says

Protocol v2 §2 and the frozen rule (`research/progress_subgoal_v1/decision_rules.json`, `third_arm_rule`, committed in
`07308e3`) add the optional `raw_evidence` arm **only if** WS3 questionnaire v1's frozen evaluator output exists, is
`technically_complete`, and at least one of three conditions holds (paired upper bound < 0 on `claim_progress` or
`claim_causal`; candidate both-pass accuracy more than 0.05 below the reference on either; a `false_progress` or
`unsupported_causal_claim` gate status differing between WS3's arms). **Otherwise two arms are kept**, explicitly
including "WS3 v1 has not run or its result is unavailable". If the trigger had fired, the design would be **two
sessions, each a paired two-arm comparison** (`raw_evidence` vs A; A vs B), A repeated: 2 × 5,580 evaluation calls.

The decision was applied and recorded before the evaluation seed was drawn
(`research/progress_subgoal_v1/third_arm_decision.json`, commit `991a277`): **`keep_two_arms`**, because no WS3 v1
evaluator output exists (WS3 v1 had no compute authorization). A search of every ref in this repository finds no
WS3 v1 live, launch, evaluation or compute-authorization record today. The successor therefore has **two arms**
(`raw_plus_computed_record`, `raw_plus_computed_record_plus_safeguard`) and one session. No arm was added.

## 3. Verification (item 4)

All results below come from a **fresh WSL clone of the committed branch** (git bundle; `de7f726`, and `3d85236` for
the last two rows), Python 3.12.3, CPU only. Receipts: `reports/progress_subgoal_v1_runtime2/` (log `clone.txt`) and
`reports/progress_subgoal_v1_diagnostics/runtime2-branch-old-suite-2.json`.

**Distinctions on the actual successor schedule** (`tests/test_progress_subgoal_v1_runtime2_science.py`, unchanged
scorer, frozen `probes.json`):

| Requirement | Verified |
|---|---|
| Raw vs computed evidence differ only as intended | Both arms receive byte-identical evidence; their 5,852 requests differ only in the system prompt (B = A + the constant safeguard). Every computed measurement in all 2,706 frozen transitions is recomputed from the same transition's raw part (validity, changed cells, visual status, availability, progress) and agrees; the computed record has a fixed key set and carries no keys, shortcut or class labels. The `raw_evidence` arm is not part of the two-arm design (§2). |
| Unknown outcomes keep their distinction | 68 `outcome_unknown` transitions: returned frames "none observed", environment "not observed", availability `missing`, visual `indeterminate`; questions on them are keyed `indeterminate` / `unknown` / `cannot_tell`. 24 failed dispatches: `not_applicable`, never a no-op |
| Transient changes | 150 `changed_then_returned` transitions; their `visual_effect` key is always `changed_then_returned` (≥ 20 contexts in the class) |
| Dimension changes | The frozen evaluation set has **none** (protocol v2 §4 assigns them to WS3 v1). The unchanged contract and presentation still yield `dimensions_differ`, an unavailable cell count and `final_frame_differs` for a dimension-change transition |
| Visible change ≠ confirmed progress | `visible_change_without_progress` contexts are keyed `unknown` / not established; `progress_without_visible_change` keyed `confirmed`; a respondent reading visible change as progress **fails** `false_progress` while `unsupported_causal_claim` passes |
| Temporal sequence ≠ causation | `claim_causal` is never keyed `supported`; "mechanism identified" never established; `strengthened` hypotheses exist but their causal claims are not established; reading sequence as cause **fails** `unsupported_causal_claim` |
| Interrupted schedules cannot be complete | Missing pass 2, one missing gate answer, recovered evidence: readiness `incomplete`. Evaluator: a run cut at the admission cutoff, a never-finalized index, a missing manifest, an intent-only call record, a timed-out call (missing answer) all give `gate_status: incomplete` / not technically complete; HTTP rehearsal cut by the frozen admission rule after 1,963 calls → incomplete |
| Invalid answers are a reliability category | All gate members malformed → every gate `insufficient_valid_opportunities` with 0 over-claim contexts, gate-member validity fails, both arms `not_eligible`; invalid causal/progress answers → 0 over-claims, validity fails |

**Token caps and request counts** (exact, pinned tokenizer: transformers 4.57.6, tokenizers 0.22.2, files equal to the
tokenizer manifest of revision `d9748a51…`): 5,852 scheduled calls (withheld pass 1: 2,790; pass 2: 2,790 reversed;
development: 272), 3,062 distinct requests, 12,779,190 prompt tokens, largest prompt 5,675 (≤ 60,000; + 32 ≤ 65,536),
longest valid answer 15 tokens pretty-printed / 11 compact (≤ 32). Counted HTTP requests: 5,852 + 11 runtime probes +
≤ 750 idle reads = cap 6,613; a nominal rehearsal issues 5,863.

**Independent scorer reproduces scores from retained responses**: from the HTTP-retained raw replies of the nominal
scripted rehearsal, the evaluator's full analysis equals the offline recomputation (same scripted rule, unchanged
scorer); every one of the 5,852 retained answers equals the old runtime's retained answers from review r4's connected
rehearsal, and the **old evaluator's analysis of the old evidence equals the successor evaluator's analysis** of the
new evidence (`scoring_reproduction_scripted.json`). Oracle answers: both arms `eligible_for_memory_or_supervision`
through the same path (`scoring_reproduction_oracle.json`). Scripted labels are not results.

**Review snapshot r5**: the notebook cell refuses at the live gate (unresolved placeholders; no review lock or
authority) before installation, model or GPU activity, with a decoy `nvidia-smi` never called and no temporary files
left (`review_check_r5.json`); `launch-build` refuses; a fresh rebuild reproduces `profile.ipynb`,
`kernel-metadata.json` and the lock byte for byte, all 60 bindings and 15 review documents verify
(`snapshot_r5.json`); the payload's default trusted-input path loads all 174 wheels (`embedded_inputs_r5.json`); run
from the extracted payload alone in an isolated interpreter, the full lifecycle completes all 5,852 calls with no
repository module imported from outside the payload, cleanup verified, and the independent evaluation is technically
complete (`extracted_payload_rehearsal_r5.json`; lifecycle 121.8 s on CPU).

**Test results**

| Suite | Tests | Failures / errors | Interpreter |
|---|---|---|---|
| Successor (`tests/test_progress_subgoal_v1_runtime2*.py`, incl. 5 full HTTP rehearsals and the basis-reproduction test) | 55 | 0 / 0 (0 skipped) | dev-env 3.12.3 |
| Verified controller's regression suites (copied unchanged) | 96 | 0 / 0 | /usr/bin/python3 3.12.3 (host pip) |
| Existing Track 4 full local check (r4 package; old-runtime CPU rehearsals) on this branch | 148 | 0 / 0 | dev-env, `python -m scripts.check_progress_subgoal_v1` |
| Builder `--check`, builder `--basis` (derivation from a `5a21dd3` extract), diff regeneration | — | pass; regenerated files identical | dev-env |

The first invocation of the existing check in that clone ran it as a plain script, so `tests` was not importable and
every suite errored at import (`clone.txt`, "old suite exit 1"); it was re-run as a module, as the r4 record was, and
passed. A preliminary run of the extracted-payload check (before the clone) took 32 minutes of wall time for unknown
host reasons; the retained run took 126 s.

Rehearsal fault coverage for the new runtime: one timeout (verified idle, answer missing), two consecutive timeouts,
server not idle after a timeout, HTTP error, prompt-token mismatch against the audit, admission cutoff; the
controller's own suites cover install/bundle tampering, version and model-tree mismatches, server exit and startup
ceiling, wrong served model, request timeout, not idle after cancellation, and servers/children ignoring SIGTERM. The
old runtime's storage, log-flood, monitor-loss and late-reply faults have no counterpart in the new single-process
controller beyond its own bounded-log and deadline tests.

## 4. Proposed amendments (not applied)

**No scientific change was found to be necessary**, and none was made. The following are proposals for the owner:

1. *Protocol text, not science (§10–§12).* Replace the character-based estimates with the exact audit: 5,852
   scheduled calls, 3,062 distinct requests, 12,779,190 prompt tokens (evaluation 12,191,728; development 587,462),
   largest prompt 5,675 tokens; the 32-token cap covers every valid answer (longest 15 tokens pretty-printed, 11
   compact). §11's "call ceiling 5,852" should also name the runtime's counted-request cap (6,613 = 5,852
   questionnaire + 11 runtime probes + at most 750 idle-check reads) that a compute authorization must state.
2. *Runtime note for the decision record.* As in the verified runtime, the cancellation probes C1–C3 run after the
   questionnaire. If the questionnaire finishes within seconds of the 3,000 s admission cutoff, the probes can be
   refused and the lifecycle verdict fails although the questionnaire evidence is complete and retained; the
   evaluator then still computes completeness and per-arm readiness from the retained replies but reports
   `technically_complete: false`. The planning scenarios (`reports/progress_subgoal_v1_runtime2_budget.json`) put
   the end of the questionnaire well before the cutoff unless overhead and call times are both far above the
   measured references, so this is unlikely; the owner may prefer to state how such a run
   is classified before launch. (Moving the probes before the questionnaire would be a runtime change from the
   verified order; not done.)
3. *Model bytes.* The verified runtime serves a dataset-backed snapshot (tree `b480ad92…`) of the same model id and
   revision `d9748a51…`; the old Kaggle Model tree was `052ab27f…` with a different inventory. Tokenizer and chat
   template files are byte-identical to the pinned tokenizer manifest. Equality of the weight shards between the two
   attachments is not established here; the owner should record whether the snapshot's provenance evidence is
   accepted as the same model for this experiment.

## 5. Owner gates

1. **Evaluation seed (two-holder retention).** The seed was drawn on 2026-10-02 (SHA-256 `ca1e518c…` in
   `research/progress_subgoal_v1/evaluation_seed.json`); it is not in the repository and was not drawn, read, printed
   or committed here. The owner confirms that two holders each retain the 32-hex-character value outside the
   repository, and each holder independently runs, in a clean checkout of this branch:

   ```
   python scripts/build_progress_subgoal_v1.py --check --seed-file <path to that holder's copy>
   ```

   which must print `question set matches a fresh build: f93ec44bab00453147e8e7e555704b60edc8220e6b5677b89d199ce8fca5e02c`
   (the script refuses a seed whose hash differs). Nothing else needs the seed.
2. **Protocol freeze.** Protocol v2 is still marked "draft for review; not frozen" although the decision rules are
   frozen (hash `38c8de63…`), the third-arm decision is recorded and `probes.json` is built. The owner decides the
   freeze record and the open questions of §13 (gate sizes, headroom, abandonment floor).
3. **Private bindings, in a private checkout only.** Resolve `kernel_id` (consuming account), `model.kaggle_source`
   (owner/dataset/version of the private model snapshot) and `model.mounted_path` (one of
   `/kaggle/input/datasets/<owner>/<dataset>` or `/kaggle/input/<dataset>`); build a successor review snapshot there
   (`python scripts/progress_subgoal_v1_runtime2_package.py review-build --revision 6`) and re-run its review check.
   The public r5 must keep the placeholders.
4. **Scope evidence for runtime2** (bound by hash; nothing from R2, the smoke test or control-interface scopes is
   reusable): account-attachment receipt with provider evidence for the exact dataset version; direct-use permission
   with the reviewer outcome and use assessment; mounted-byte verification of all 174 wheels.
5. **Source approval and compute authorization**, separate, bound to the r6 lock, the protocol, the dataset and the
   evidence: limits 3,600 s authorized, 3,300 s internal, 3,000 s admission cutoff, 300 s cleanup reserve,
   1 attempt, 0 automatic retries, 6,613 counted model requests, 0 environment actions, 0 scorecards.
6. **Execution lock, reservation and launch claim**, then `launch-build`; one submission with a durable receipt; no
   automatic retry.

## 6. Exactly what remains before review and authorization

1. Independent review of this branch: the derivation (`build_progress_subgoal_v1_runtime2.py --basis` against a
   `git archive 5a21dd3` extract), the questionnaire stage, the evaluator and r5.
2. Owner gates 1–2 above (seed retention check; freeze record and open questions).
3. Owner gate 3 (private bindings and a private successor review snapshot), then gates 4–6.
4. Not established by any CPU check: that Kaggle provisions the pinned image, mounts dataset version 1 and the private
   model dataset, or allocates an RTX PRO 6000; the real per-phase overhead of installation, model-tree hashing and
   startup on this package (only a whole-lifecycle figure of 539.7 s for the verified 131-request run is public);
   real-model call rates, prompt-token parity on the server and the idle behaviour after a real timeout.
