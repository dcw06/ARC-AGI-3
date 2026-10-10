# Feedback-action v1 (Track 1): decisions to freeze protocol v2 (prepared October 10, 2026)

**Status.** A decision packet for the owner. Nothing here is decided, frozen, approved or reserved. Protocol v2 draft
r1 (`reports/feedback_action_v1_protocol_v2_r1.md`) and review snapshot r1 (lock `4b5b7a06…`) are unchanged.

**What is new since r1.**
- **A CPU check through vLLM's own request path** (`scripts/check_feedback_action_v1_structured_outputs.py`;
  receipt `reports/feedback_action_v1/structured_outputs_check_r1.json`). r1 listed the candidate schema on the
  server's structured-output path as unverifiable before a GPU session. Track 2 showed it can be checked on CPU,
  and found a schema the server would have refused.
- **A review of r1 against the defects found in Tracks 4 and 2,** which share the runtime base (section 4).
- **Measured setup times on the target GPU,** from Track 2's two sessions (section 3).

## 1. Gate A: the permitted free-text format

Full analysis: `reports/feedback_action_v1_owner_gates.md`.

| Option | Worst-case candidate response (pinned tokenizer) | Fits the 640-token cap? |
|---|---|---|
| `current` (committed): any code point except quote, backslash, CR, LF; ≤ 240 | 2,106–2,250 tokens | no; natural non-Latin text can be truncated, which counts as an invalid output against the candidate |
| `ascii_only` (recommended): printable ASCII without quote and backslash; ≤ 240, enforced by the decoder | 666–810 tokens (degenerate content only); English-like text at the caps 287–446 | natural text yes |

**New evidence (this pass).** vLLM 0.19.0's request validation, with the server's default `auto` backend, accepts
all 10 Track 1 schemas: the baseline and canary schemas, and the candidate schema under both options, for all three
games. It selects **xgrammar for every one**, with no fallback to guidance, so the token audit's xgrammar figures
apply on the real server path. Over 96 test answers the decoder admits exactly what the study counts valid.

| Test answer | `current` | `ascii_only` |
|---|---|---|
| ASCII text, 240 characters | admitted | admitted |
| 241 characters | rejected | rejected (the bound sits inside the pattern) |
| Non-ASCII text (CJK; accented Latin) | admitted | **rejected** |
| Five citations; bad ref; three-cell region; missing block; illegal action | rejected | rejected |

**Recommendation: `ascii_only`.** It is the smallest change that makes the cap a property of the model's choices
rather than of how the tokenizer splits characters. The cap, the text limit and the baseline stay unchanged. It
changes the candidate's `response_format` bytes, which is a change to the treatment's request made before session 1.

## 2. Gate B: F5 early abort

| Option | Rule | One failure in the first 9 dispatches | From the 10th dispatch |
|---|---|---|---|
| running rate from the first dispatch (committed) | 10k > n | aborts the session | 10k > n |
| **denominator floor 10 (recommended)** | 10k > max(n, 10) | the episode ends; the session continues | identical |

**Recommendation: `denominator_floor_10`.** Dispatches go to the local offline engine, so an early failure points
to the harness rather than the model. A single early failure then costs its own episode, which is retained, rather
than the whole session. A second failure within the first 19 dispatches still aborts.

## 3. Budget and ceilings per session (proposal, for the compute authorizations)

| Item | Value | Basis |
|---|---|---|
| Sessions | 2, one block each, each its own reservation and attempt; one reviewed package | protocol §4 |
| Session 2 | only after session 1's independent evaluation is live and permits it (no F2a or F3–F6 stop); bound by hash | protocol §4, §10; enforced by the gate |
| Reservation | 3,600 s; internal deadline 3,300 s; cleanup reserve 300 s; a pair admitted only if ≥ 600 s remain | protocol §12 |
| Model requests | ≤ 193 per session (1 startup canary + ≤ 192 policy calls); all are generations; no metrics reads | `protocol.json` limits |
| Game actions | ≤ 144 per session (24 per episode, 6 episodes), all on the **local offline engine** (three exposed development games); zero online game calls and zero scorecards | protocol §3, §5 |
| Accelerator | one GPU named `RTX PRO 6000`, bound by the monitor | protocol §7 |
| Retries | none | protocol §12 |

**Measured setup on the target, from Track 2 (same installer, model and GPU type).** Bundle integrity 36–56 s, model
installation 82–83 s, model artifact verification 170–249 s, server ready 114 s: about 7–8 minutes, against the
protocol's worst case of 1,800 s. Track 1 also installs the game interpreter: 212–278 s for both interpreters on CPU
replicas. About 1,800–2,300 s of the 3,300 s internal deadline therefore remain for the six episodes. The connected
rehearsal counted 3,660,975 prompt tokens per session over 8,692–26,524 tokens per call; these are planning figures,
not ceilings.

## 4. Review of r1 against the defects found in Tracks 4 and 2

| Defect (where found) | Track 1 r1 | Proposed fix (no owner decision needed; in the freeze revision) |
|---|---|---|
| Review documents not verified by the repository-side gates (Track 4 review, P2) | **Present, and stronger.** The r1 lock binds none of the review documents: not the independent evaluator (`live_evaluation.py`, `scripts/evaluate_feedback_action_v1.py`), the protocol text, the derivation scripts or the package script. Session 2's gate and the study results depend on that evaluator | Bind them in each review lock (`review_documents`) and verify them in every repository-side gate (launch tooling, live evaluation), as Tracks 4 and 2 do; only the in-payload gate skips them |
| The package does not name its frozen protocol text (Track 4 review, P2) | `protocol.json` has no `protocol_document` | Bind the frozen protocol text by hash in the lock and in each compute authorization |
| A server-refused schema (Track 2, `uniqueItems`) | **Not present** (section 1) | Keep the receipt; bind the check script as a review document |
| The evaluator accepted missing mandatory runtime probes (Track 4 and Track 2 reviews, P1) | **Different design.** Track 1 runs one startup canary, not the probe matrix. The evaluator requires the readiness record, the canary audit, monitor telemetry (GPU named `RTX PRO 6000`), installation, server-group and prefix-caching evidence, and replays every call from retained bytes | A reviewer should confirm the request accounting in the freeze revision: every model request is the canary or a scheduled policy call, with none unaccounted |

## 5. What follows the decisions

1. **Freeze.** A frozen protocol text recording both gate decisions, then review snapshots r2 with the section 4
   fixes. Fresh-clone verification, as for Tracks 4 and 2.
2. **Private checkout:** the private bindings (one notebook, the model dataset), live path enabled, the final
   private review lock.
3. **Gate 4 evidence for the one scope:** use permission and byte-receipt reuse (as approved for Tracks 4 and 2,
   reconfirmed for this scope), and one GPU-off Quick Save of the review notebook. Each needs the owner's approval.
4. **Session 1:** source approval and compute authorization, then one attempt.
5. **Session 2** only if session 1's evaluation permits it, under its own authorization. Then
   `live_evaluation.evaluate_sessions` gives the study's outcome.

## Decisions needed from the owner

1. **Gate A:** `ascii_only` (recommended) or `current`.
2. **Gate B:** `denominator_floor_10` (recommended) or the committed rule.
3. **Freeze** protocol v2 with those decisions, and adopt the section 4 fixes in the same revision.
