# Track 3 runtime v2: successor package for review (r2)

**Status.** This is a GPU-disabled review record. It authorises nothing: no GPU time, provider call, upload,
reservation, approval, claim or submission. Every earlier record is preserved: r1 (snapshot, receipts and this
report's predecessor), the R4–R7 packages and the consumed R6 attempt.

| Item | Location |
|---|---|
| Frozen protocol | `reports/stagnation_supervision_v1_protocol_v2_frozen.md` (October 11, 2026, on the owner's decisions; v2 kept as history) |
| Gap checklist | `reports/stagnation_supervision_runtime_v2_gap_checklist_r2.md` |
| Review snapshot r2 | `notebooks/stagnation-supervision-v1-runtime-v2-review-r2/`, lock `96e88a91cbd747a2e2907a7fb928b9088beaaa6e06c2cfb2a6a16336fb0a9b2d`: 160 embedded bindings, 178 review documents, the four private placeholders unresolved, GPU disabled |
| Review check r2 | `reports/stagnation_supervision_runtime_v2_review_check_r2.json` |
| CPU suite r3 | `reports/stagnation_supervision_runtime_v2_local_checks_r3.json` |
| Structured outputs | `reports/stagnation_supervision_runtime_v2_structured_outputs_r1.json` (schemas: `..._structured_outputs_schemas_r1.json`) |
| Runtime diff | `reports/stagnation_supervision_runtime_v2_runtime_diff_r2.json` (r1 retained) |

## 1. What changed since r1

**Science.** No science file changed. Every file bound under `science` in the runtime protocol is byte-identical,
including:
- the detector, the trigger, supervision and intervention;
- the outcome functions and the frozen trajectory evaluator;
- the closed-loop protocol and protocol v2.

The owner's decisions are recorded in the frozen protocol text, which is now a bound review document.

**Runtime.** These changes go through the derivation, which still inverts:
- protected supervisor startup ownership;
- fail-closed finalization, with the target evaluator checking both;
- `MPLBACKEND=Agg` for the model installation and its checks.

**Gate.** On the repository side the gate now requires:
- the complete payload closure;
- lock bindings equal to the reviewed notebook's embedded inventory;
- the review documents (`review_documents.json`): the frozen protocol text and the evaluators' strict import
  closure.

Inside the payload it checks the embedded bindings only. A session-2 attempt must bind a technically complete,
accepted session-1 evaluation.

**Evaluation.**
- Live session reports verify the evaluating checkout's review lock.
- New post-run modules:
  - `selfreview.py`: the amendment-S1 sample and annotation validation;
  - `pooled.py`: the two-session evaluation, with stale records rejected and annotations required before any
    comparison. It covers the primary endpoint over ar25, wa30 and ls20 (s5i5 separate, repeats excluded), the P2
    suggestion-following measure, reproducibility and the §8.6 conditions.

The checklist maps each change to the lesson behind it and to its regression test.

## 2. Verification (CPU only; scripted model; injected GPU; not target evidence)

| Check | Result |
|---|---|
| CPU suite r3 (Linux CPython 3.12.3) | 263 tests (161 historical R4, 102 runtime v2), 0 failures, errors or skips, 1,324 s; all seven receipt checks pass (R4 derivation, R4 local checks, R3 token-audit replay of 1,122 requests, R4 package review, R7 package check, detector verification, runtime diff r2) |
| Derivation (Windows checkout, git objects) | 16 derived files match; 14 invert to their sources |
| Structured outputs (vLLM 0.19.0, backend `auto`) | All five policy schemas accepted (four games' legal sets and the canary); xgrammar 0.1.34 selected; 50/50 decoder cases agree with the study's verdicts |
| Review check r2 | Passed: all 160 bindings verified and every embedded file compiled; the live cell refused at the gate ("unresolved placeholders" and "no review source lock") with no `nvidia-smi` call, no leftovers and no `/kaggle` access; the embedded cell's CPU rehearsal (one game group, three arms) was technically complete with verified cleanup and no leaked source |

## 3. Private binding (values kept in the private checkout)

**Checkout.** The private checkout is a plain copy of the public commit `7ccc719`. It fills only the four private
placeholders:
- the kernel ids for the two sessions;
- the model dataset (version 1), whose tree matches the pinned `b480ad92…`;
- its verified mount.

**Private review snapshot r3.**
- Lock `02160417eea9e240f898098c375ac1ad1c37b2f076bff414a0f76489ff4790de`, with no unresolved placeholder.
- It differs from r2 only in the runtime protocol.
- The repository-side gate stops at the absent source approval, and the evaluating-checkout check verifies r3.
- The private review check (attempt 2) passed: the notebook refused at the live gate with no `nvidia-smi` call, and
  its embedded-cell rehearsal was technically complete with verified cleanup.
- Attempt 1 is retained as failed. The check's own condition demanded a placeholder refusal, which a privately bound
  snapshot cannot give; this was fixed at `d1285b6`.

**Staged real-interpreter rehearsals from the extracted private r3 payload.** These ran the real trusted-lock installs
in the model and game venvs, the scripted transport, the offline engine and an injected GPU:

| Rehearsal | Result |
|---|---|
| Interpreters | Both installs passed (270 s); every game-side and model-side module imported, including `vllm.entrypoints.openai.api_server` (vLLM 0.19.0, torch 2.10.0, transformers 4.57.6) |
| Session 1 (15 episodes at 40 actions) | Technically complete with the lifecycle verified; first cell 418 s (installation 212 s); dependency trees removed; finalization certified (guard version 1, extracted source removed inside the charged lifecycle) |
| Session 2 (12 episodes at 40 actions; attempt 2) | Technically complete with the lifecycle verified; first cell 314 s against the 4,500-s ceiling (installation 189 s); finalization certified, source removed. Attempt 1 is retained as failed: the operator passed session 1's 5,100-s budget, and the supervisor correctly refused a budget above session 2's ceiling, before any study work |

## 4. What remains (owner and target)

1. **Gate 4.**
   - Reconfirm the carried-over use facts for this scope.
   - Accept reuse of the mounted-byte receipt and of the on-target model-snapshot verification.
   - One GPU/TPU-off Quick Save of the private r3 notebook as account-attachment evidence.
2. **Gate 6.** Three separate decisions for session 1 only (source, compute, launch), then the execution lock,
   reservation and claim.
3. **Target-only facts, still unverified.** CUDA, model startup, real per-step timing, GPU cleanup on the RTX PRO
   6000, and the 450-s installation window on the pinned image.
4. **Limits that stay open.** A second qualified continuation control (the gate is not certifiable). The self-review
   is not an independent audit.
