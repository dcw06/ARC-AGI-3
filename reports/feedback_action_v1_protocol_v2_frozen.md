# Feedback-action v1: experiment protocol v2 (frozen)

**Status: frozen on October 10, 2026, on the owner's decisions. Not authorized.** No reservation, approval, compute
authorization, launch claim or model call exists. Nothing here approves compute.

**The two owner gates are decided (§14), and this text records them:**
- **Gate A, free-text format: `ascii_only`.** `hypothesis` and `if_different` are printable ASCII without quote
  and backslash, at most 240 characters, enforced by the decoder.
- **Gate B, F5 early abort: `denominator_floor_10`.** F5 aborts when failed plus unknown dispatches × 10 >
  max(dispatches so far, 10).

The record is `research/feedback_action_v1/live/owner_gates.json`, with the owner's response. Review snapshots r2
bind it, this text and the other review documents (§15).

**Relation to r0 and r1.** Draft r0 (`reports/feedback_action_v1_protocol_v2.md`, at `687acc8`) and draft r1
(`reports/feedback_action_v1_protocol_v2_r1.md`, at `078bf4d`) stay unchanged as history. This frozen text is r1
with:
- the two gate decisions (§2, §10, §14);
- the structured-output check through vLLM's own request path (§11);
- measured setup times and the per-session ceilings (§12);
- the review documents and the evaluator's review-lock check (§10, §15).

r1 itself changed four things relative to r0:
- it binds the runtime to the verified successor runtime (§7, §12);
- it replaces the token-count TODO with the exact audit (§2);
- it adds interpretation notes (§2.1, §8.1);
- it records the CPU verification of the connected stack (§11).

Relative to r0, prompts, arms, seeds, schedule and scoring are unchanged byte for byte
(`reports/feedback_action_v1_runtime_diff.md`). The two decisions change exactly two things, both fixed before
session 1: the candidate's response schema (gate A) and F5's small-sample region (gate B).

## 1. Research question (unchanged)

**Does structured hypothesis testing improve action selection?** A solving improvement is claimed only from
completed levels.

**Scope (unchanged).** All three games (s5i5, ls20, sk48) are exposed development games. Prior exposure limits every
real-game claim. Results describe these three development games under this protocol. They are not evidence of:
- generalization;
- performance on unexposed or holdout games;
- competition performance.

## 2. Arms and treatment (unchanged; the free-text format set by gate A)

| Arm | Receives |
|---|---|
| Baseline | the current observation (existing pipeline, through AEH v1's `observation_payload`), the legal controls, and the full-frame `transition_evidence_v2` evidence view |
| Candidate | the same bytes, plus the bundled treatment |

**The bundled treatment:**
- the `PROCEDURE` paragraph;
- a required `hypothesis_test` block, whose free-text fields are printable ASCII without quote and backslash, at
  most 240 characters (gate A: the schema pattern `^[ !#-\[\]-~]{0,240}$`, with `maxLength` kept; a disallowed
  character in a parsed block makes the block invalid, never the action);
- the carried previous statement;
- a 640-token completion cap, against 128.

It is applied as one intervention. No arm is added. **The treatment is fixed before session 1.** Session 2 runs the
identical package.

**Exact request sizes.** These were measured with the pinned tokenizer. Counting follows the service's admission
(`apply_chat_template`, generation prompt, thinking disabled). The forms come from the real offline engine for both
sessions. Source: `research/feedback_action_v1/token_audit.json`.

| Form | Prompt tokens | Request bytes |
|---|---|---|
| Startup canary | 39 | 881 |
| Baseline, first | 8,692–8,749 | 11,158–11,438 |
| Baseline, largest steady state | 25,994–26,154 | 30,964–31,188 |
| Candidate, first | 8,982–9,039 | 14,245–14,525 |
| Candidate, largest steady state | 26,356–26,516 | 34,400–34,625 |
| Candidate, carried statement at its caps, worst ASCII text | 26,831–26,991 | about 35,000 |
| Candidate, carried statement at its caps, worst text under the rejected `current` format (reference) | 30,191–30,351 | about 41,000 |

**Ceilings.** Under the frozen option the maximum is 26,991 tokens (30,351 under the rejected option), against the
60,000-token prompt ceiling; with its 640-token cap, well within the 65,536 context.

**Live counts.** The connected rehearsal counted every request with the same tokenizer through the service and the
bridge: 8,692–26,524 tokens per call; 3,660,975 prompt tokens in one session.

**Longest allowed responses against the caps.** The gate A analysis gives the full table
(`reports/feedback_action_v1_owner_gates.md`).
- Baseline: 22–42 tokens, against 128.
- Candidate, English-like text at the caps: 287 tokens (compact) to 446 (with the whitespace seen live).
- Candidate, worst ASCII text (degenerate content, the frozen option's bound): 666–810 tokens.
- For reference, the rejected `current` option's worst text: 2,106–2,250 tokens.

The decoder admits unbounded whitespace and unbounded ref digits, in both arms. No finite cap therefore covers every
admitted response, and a truncated response is an invalid output (§5).

### 2.1 Interpretation notes (new)

- **The candidate is a bundle.** It combines the procedure paragraph, the structured hypothesis block, the carried
  statements and a 5× larger completion allowance.
  - A positive result does not isolate a component. It does not show that hypothesis testing, rather than more
    output tokens or the carried state, produced the difference.
  - Only a later ablation can attribute an effect.
  - A negative result calls first for a check that the candidate used the block and the carried statement.
- **The arms are not compute-matched.**
  - The candidate's prompts are about 360 tokens longer at steady state.
  - Its completions are longer: 138–141 tokens in the scripted rehearsal, against 17–29 for the baseline, and they
    will differ again with the model.
  - Every report states cost per arm: provider prompt and completion tokens, call latency and episode wall time.
    The independent evaluator reports them (`cost_by_arm`).
- **Process measures are not outcome measures.** These are reported separately from board changes and level
  completion:
  - prediction accuracy;
  - hypothesis revision after a falsified prediction;
  - citation supply and supported citations.
  - The process measures are candidate-only, descriptive, and computed from the retained bytes. Outcome measures
    are repeat-after-no-change, untested-type choice, visible change and levels completed.
  - A better process measure does not by itself show better action selection.
  - A better action-selection rate is not a solving result.
- **Supported citations are mechanical support, not truth.** A citation is `supported` when the cited transition
  shows the claimed measured property. Free text is never scored for plausibility.

## 3. Cases and exclusions (unchanged)

**Cases:**
- s5i5 (coordinate-only);
- ls20 (directional only);
- sk48 (mixed).

**Exclusions:**
- H1, H2 and the withheld partitions are never touched;
- ar25, cd82 and ft09 are excluded;
- there is no masked arm or masked evidence, and no outcome-based game replacement.

s5i5 runs with full-frame evidence, and its repeat rate is undefined (§8).

## 4. Seeds, sessions and block order (unchanged)

**Seeds and decoding.**
- Environment seed 0.
- Temperature 0.
- Model seed 0.
- **Prefix caching off.** The successor runtime enforces it. The server argv carries `--no-enable-prefix-caching`
  exactly once, and the server log must confirm `enable_prefix_caching=False` before the canary (§7).

**Sessions.** There are two sessions, one block each, each in a fresh reservation. Within each game, arm order
alternates and reverses between blocks (table as in r0 §4). The session number is bound by the reserved execution
lock, not by the package: one reviewed package runs both sessions. A session-2 attempt must bind the independent
evaluation of session 1 by hash. The gate refuses session 2 unless that evaluation is live, for session 1, and
permits session 2 (§10).

## 5. Horizon, caps and stop behaviour (unchanged)

As r0 §5:
- 24 actions and 32 decision calls per episode;
- completion caps of 128 (baseline) and 640 (candidate);
- 192 policy calls per session;
- terminal states are checked before the caps;
- a dispatch failure or unknown outcome ends its episode, and the schedule continues unless F5 aborts;
- invalid outputs consume a call, never an action.

## 6. Model-facing content and retained evidence (unchanged)

As r0 §6. Every request and raw response is retained. Every transition is retained as a v2 raw with
`record_id` `<episode_id>#<action_index>`. Each valid dispatched candidate block becomes a v2 `model_statement`.

## 7. Model, decoding and runtime (runtime bindings changed; science unchanged)

| Setting | Value |
|---|---|
| Model | `Qwen/Qwen3-VL-30B-A3B-Instruct-FP8`, revision `d9748a51…` (unchanged). Snapshot: version-pinned private dataset (private binding kept as `REPLACE_WITH_…`), tree `b480ad92…` verified before load |
| Decoding | temperature 0, seed 0, `enable_thinking: false`; guided-decoding schema per arm (unchanged). vLLM 0.19 defaults: xgrammar backend, any whitespace |
| Server | vLLM 0.19.0 from the trusted 174-wheel lock, `--max-model-len 65536`, `--gpu-memory-utilization 0.75`, `--no-enable-prefix-caching`; own process group; TCP readiness |
| Startup canary | one, 128-token cap (unchanged) |
| Interpreters | model: trusted lock (hash-pinned, offline). Game: the 31 competition wheels (hash-pinned, offline; arc-agi 0.9.8). Image: CPython 3.12, pinned digest |
| GPU | one, name containing `RTX PRO 6000`, bound by the monitor |

Every binding change, with its old value, is listed in `reports/feedback_action_v1_runtime_bindings.md`.

## 8. Metrics, denominators and failures (unchanged)

As r0 §8, computed by the independent evaluator from retained bytes only.
- Failure-inclusive: an invalid output counts as the unfavourable outcome.
- Undefined is never reported as 0.
- Minimums apply when pooling per (game, arm) over both blocks.
- The valid-only repeat rate is descriptive only.

### 8.1 What the independent evaluation reconstructs (new; §13.3 of r0)

`scripts/evaluate_feedback_action_v1.py` and `research/feedback_action_v1/live_evaluation.py` work from retained
bytes only. The evaluation imports neither the runner, the live policy nor the adapter. It:
- verifies the evidence manifest;
- rebuilds the session's effective spec from `protocol.json` and `owner_gates.json`, and checks the run's protocol
  digest, schedule and episode order;
- runs `verify_history` on every episode against its raws, and checks record ids, call and step links, continuity
  and the frozen initial state;
- checks every call's request contract, response hash and cross-process token audit;
- reconstructs every carried statement from the previous call's raw response and the transition it produced, and
  requires it to equal the statement actually sent;
- checks model-statement records against the dispatched blocks;
- classifies every citation against the window shown at that decision;
- recomputes every rate with explicit denominators;
- recomputes F2a and F5 online, and applies §9–10.

## 9. Outcome and advancement rules (unchanged)

As r0 §9:
- technical validity first;
- solving only from completed levels (more levels than baseline in at least 2 of 3 games, in both blocks, fewer in
  none);
- exploratory action-selection rules;
- provisional exploratory thresholds, which are not reliability evidence.

`live_evaluation.evaluate_sessions` applies them to the two evaluated sessions.

## 10. Failure rules (F5 amended by gate B)

F1–F6 and the exact online definition of F2a are as in r0 §10. Session 2 does not start after a session-1 stop
under F2a or F3–F6. The gate enforces this through the session-1 evaluation (`session_2_permitted`).

**F5 (gate B, decided).** After every dispatch, the session aborts when (failed + unknown dispatches) × 10 >
max(dispatches so far, 10).
- A single failed or unknown dispatch never aborts: it ends its own episode, which is retained, and the schedule
  continues.
- A second failure aborts if it comes before the 20th dispatch.
- From the 10th dispatch on, the rule is identical to r0's (failures × 10 > dispatches).
- The abort record carries `denominator_floor: 10`; the independent evaluator recomputes F5 with it.

**The evaluation must come from the reviewed evaluator.** In live mode the independent evaluation verifies that
the evaluating checkout matches its newest review lock: every review document, the evaluator among them, and
every embedded source, by hash. If that check fails, the evaluation records the problem and never permits
session 2 (§15).

## 11. CPU verification status (no model, no GPU)

Rows from r1 are kept as recorded there; rows marked r2 were redone for this freeze revision.

| Check | Result | Record |
|---|---|---|
| Installation path on replicas of both mounts: 174 trusted wheels plus publisher metadata; 31 competition wheels; system CPython 3.12. The second run calls the first cell's own `install_pair` | passed. 212 s, and 278 s under concurrent load, for both interpreters. `pip check`, exact versions and torch CUDA build `12.8`; game closure 82 modules, model closure 34; cross-side packages absent; install logs retained; groups verified absent | `reports/feedback_action_v1/runtime_install_check.json` |
| Real offline engine inside the installed game interpreter: the 31 competition wheels, arc-agi 0.9.8, arcengine 0.9.3, numpy 2.4.4 | passed, 41 tests: both sessions on s5i5, ls20 and sk48 with frozen initial hashes; 24 actions per game and arm; s5i5 GAME_OVER at action 50 with nothing after it; the evaluator's real-engine sessions. The same tests also pass in the development environment (arc-agi 0.9.9) | same record |
| Exact token audit, pinned stack inside the installed model interpreter (r2) | regenerated with the decisions recorded: all 25 forms within limits; only the 18 candidate forms' request bytes changed (the `ascii_only` pattern), and every prompt-token count is unchanged; completions per gate A | `research/feedback_action_v1/token_audit.json` |
| Connected rehearsal on the installed interpreter pair: first cell → supervisor → worker → monitor → host → bridge → runner → engine | complete: 144 calls, 144 dispatches. Pinned-tokenizer counts matched across processes. 145/145 completions accepted by the xgrammar 0.1.34 grammar of their request. 72 carried statements reconstructed, 0 mismatches | `reports/feedback_action_v1/cpu_checks_successor-game-interpreter.json` |
| **Structured outputs through vLLM's own request path** (vLLM 0.19.0, xgrammar 0.1.34, llguidance 1.3.0; default `auto` backend) | passed. All 10 request schemas accepted: the baseline and canary schemas and the candidate schema under both free-text options, for all three games. xgrammar was selected for each, with no fallback to guidance, so the token audit's xgrammar figures apply on the server path. Over 96 test answers the decoder admits exactly what the study counts valid; under `ascii_only` it rejects non-ASCII text, and it rejects 241 characters under both options | `reports/feedback_action_v1/structured_outputs_check_r2.json` (r1 before the decisions) |
| Live model-host factory over HTTP, unchanged code, with a CPU stand-in for vLLM in the model interpreter | passed. Fixture-tree digest check; server in its own group; TCP readiness; log prefix-caching confirmation; the HTTP canary; all 24 request forms of both arms, each schema compiled server-side by xgrammar; token audit equal across processes (max 30,351); server group cleaned up | `reports/feedback_action_v1/cpu_checks_successor-model-interpreter.json` |
| Fault matrix through the connected path | model startup, transport, monitor exit, cancellation, storage exhaustion, surviving child, truncation, F2a, admission cutoff. A single failed or unknown dispatch (r2): its episode ends and, under the frozen F5 floor, the session completes. F5 aborts (two early failures) and r0's rule are exercised through the runner with synthetic adapters, and recomputed online by the evaluator. A deadline mid-pair is checked with a scripted clock | `tests/test_feedback_action_v1_connected.py`, `tests/test_feedback_action_v1_dispatch.py`, `tests/test_feedback_action_v1_live_evaluation.py` |
| Review snapshot r1 (lock `4b5b7a06…`) | review check: refused at the live gate before installation, model or GPU use; no nvidia-smi call; no files left. Review rehearsal (the same cell, MODE switched, from the extracted payload, on the installed interpreter pair): one complete session, evaluation technically complete | `reports/feedback_action_v1_review_check_r1.json`, `reports/feedback_action_v1_review_rehearsal_r1.json` |
| Review snapshot r2 (this revision) | the review check (must refuse at the live gate) and the review rehearsal are run after this text is frozen, because the r2 lock binds it | `reports/feedback_action_v1_review_check_r2.json`, `reports/feedback_action_v1_review_rehearsal_r2.json` |
| All Track 1 suites (r2) | rerun on the installed game interpreter (with the installed model interpreter, pinned tokenizer, xgrammar check and replica competition mount), the model interpreter (HTTP path) and the development environment; r1 recorded 173 tests with 0 failures | `reports/feedback_action_v1/cpu_checks_*.json` |

**These are CPU checks with scripted completions.** They are not evidence about:
- model behaviour;
- GPU, CUDA or model load;
- guided decoding during generation on the server (the CPU check covers request validation, backend selection
  and grammar enforcement, not decoding on the GPU);
- the provider mounts or image.

## 12. Package and sessions (a proposal; nothing reserved or approved)

| Item | Value |
|---|---|
| Session count | 2, one per block, each a fresh reservation and attempt (one package) |
| Maximum reservation per session | 3,600 s provider timeout (proposal) |
| Internal deadline | 3,300 s per session |
| Installation deadline | 900 s from the first cell, covering both interpreters. Measured on CPU replicas: 212–278 s |
| Model startup ceiling | 900 s |
| Admission cutoff | a pair only if ≥ 600 s remain; unadmitted pairs make the run incomplete |
| Cleanup reserve | 300 s per session |
| Retry policy | none. No call, episode, pair or session is retried |

**Proposed ceilings for each compute authorization** (decision packet, section 3; each authorization states its
own):
- at most 193 model requests: 1 startup canary and at most 192 policy calls; all are generations, and there are no
  metrics reads;
- at most 144 game actions (24 per episode, 6 episodes), all on the local offline engine; zero online game calls and
  zero scorecards;
- one GPU named `RTX PRO 6000`; no automatic retry.

**Measured setup on the target.** Track 2's two sessions used the same installer, model and GPU type: bundle
integrity 36–56 s, model installation 82–83 s, model artifact verification 170–249 s, server ready 114 s. Track 1
also installs the game interpreter (212–278 s for both interpreters on CPU replicas). About 1,800–2,300 s of the
3,300 s internal deadline therefore remain for the six episodes.

**Estimated runtime is not an authorization ceiling.**

The worst case matters: if installation took its full 900 s and startup its full 900 s, then fewer than 6 pairs
could be admitted. The run would then be incomplete; the reservation would not be exceeded. The verified runtime's
whole probe lifecycle, 131 requests included, took 540 s. The budget decision is the owner's.

## 13. Before an exact source and package lock

1. **Owner gates (§14):** decided and recorded; review snapshots r2 bind the record.
2. **Private bindings:** the consuming account, the model dataset reference and the mount path are resolved in a
   private checkout. That checkout produces a successor review snapshot.
3. **Use and attachment evidence:** account attachment, the direct-use permission outcome and the mounted-byte receipt
   for this scope. The gate requires all three.
4. **Review, source approval and compute authorization**, bound to the review lock, `runtime.json`, `protocol.json`
   and `owner_gates.json`. Then one reservation per session.
5. **Still unverified until a GPU session runs:**
   - guided decoding of the candidate's schema during generation (request validation and grammar enforcement are
     verified on CPU, §11);
   - the competition mount layout on the pinned image;
   - model load and cleanup on the target.

## 14. Owner gates (decided October 10, 2026)

Analysis: `reports/feedback_action_v1_owner_gates.md`; decision packet: `reports/feedback_action_v1_freeze_decisions.md`.

| Gate | Decision | Rejected option |
|---|---|---|
| A. Free-text format | **`ascii_only`**: printable ASCII without quote and backslash, ≤ 240, enforced by the decoder | `current`: any code point except quote, backslash, CR, LF; ≤ 240 |
| B. F5 early abort | **denominator floor 10**: a single failure never aborts; identical from the 10th dispatch | running rate from the first dispatch: 1 failure in the first 9 dispatches aborts |

The owner also decided to freeze this protocol with both decisions and to adopt the review-document fix (§15) in
the same revision.

Teammate material at `origin/teammate/windows-track1` `df29206` (the competing-explanations challenge set) is
development material. It could enter only as a separately reviewed amendment.

## 15. Review documents (freeze revision r2)

Every review lock binds these files by hash, and every repository-side gate verifies them: the review check, the
launch tooling, `launch-build` and the live independent evaluation. The runtime payload never carries them, so only
the in-payload gate (inside the notebook) skips them.
- this frozen text;
- the independent evaluator's files that are not embedded in the payload: `research/feedback_action_v1/live_evaluation.py`,
  `research/feedback_action_v1/evaluate.py`, `research/transition_evidence_v1/reference.py` and
  `scripts/evaluate_feedback_action_v1.py` (the rest of its import closure is embedded and bound already);
- the derivations (`research/feedback_action_v1/derive.py`, `research/feedback_action_v1/derive_runtime.py`) and the
  package script (`scripts/feedback_action_v1_package.py`);
- the structured-output check (`scripts/check_feedback_action_v1_structured_outputs.py`) and its receipt r2.

This closes, for Track 1, the defect the Track 4 review found in the shared runtime base: r1's lock bound none of
these documents, so the evaluator that gates session 2 and computes the results could have changed after review.
