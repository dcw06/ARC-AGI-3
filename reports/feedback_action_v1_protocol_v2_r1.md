# Feedback-action v1: experiment protocol v2, draft r1 (frozen-protocol candidate)

**Status: candidate for freezing. Not frozen, not authorized.** No reservation, approval, compute authorization,
launch claim or model call exists. Nothing here approves compute.

**Two owner gates are open (§14):**
- the permitted free-text format;
- F5 early abort.

The text below states the committed behaviour, which applies while no decision is recorded.

**Relation to r0.** Draft r0 (`reports/feedback_action_v1_protocol_v2.md`, at `687acc8`) stays unchanged as history.
r1 changes four things:
- it binds the runtime to the verified successor runtime (§7, §12);
- it replaces the token-count TODO with the exact audit (§2);
- it adds interpretation notes (§2.1, §8.1);
- it records the CPU verification of the connected stack (§11).

The scientific configuration is unchanged byte for byte: prompts, arms, schemas, seeds, schedule, scoring and stop
rules. The record of that is `reports/feedback_action_v1_runtime_diff.md`.

## 1. Research question (unchanged)

**Does structured hypothesis testing improve action selection?** A solving improvement is claimed only from
completed levels.

**Scope (unchanged).** All three games (s5i5, ls20, sk48) are exposed development games. Prior exposure limits every
real-game claim. Results describe these three development games under this protocol. They are not evidence of:
- generalization;
- performance on unexposed or holdout games;
- competition performance.

## 2. Arms and treatment (unchanged)

| Arm | Receives |
|---|---|
| Baseline | the current observation (existing pipeline, through AEH v1's `observation_payload`), the legal controls, and the full-frame `transition_evidence_v2` evidence view |
| Candidate | the same bytes, plus the bundled treatment |

**The bundled treatment:**
- the `PROCEDURE` paragraph;
- a required `hypothesis_test` block;
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
| Candidate, carried statement at its caps, worst text under the current free-text format | 30,191–30,351 | about 41,000 |

**Ceilings.** The maximum is 30,351 tokens, against the 60,000-token prompt ceiling. It is 30,991 tokens with its
640-token cap, against the 65,536 context.

**Live counts.** The connected rehearsal counted every request with the same tokenizer through the service and the
bridge: 8,692–26,524 tokens per call; 3,660,975 prompt tokens in one session.

**Longest allowed responses against the caps.** Gate A gives the full table.
- Baseline: 22–42 tokens, against 128.
- Candidate, English-like text at the caps: 287 tokens (compact) to 446 (with the whitespace seen live).
- Candidate, worst ASCII text: 666–810 tokens.
- Candidate, worst text under the current format: 2,106–2,250 tokens.

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

## 10. Failure rules (unchanged; F5's early strictness is Gate B)

F1–F6 and the exact online definitions of F2a and F5 are as in r0 §10. Session 2 does not start after a session-1
stop under F2a or F3–F6. The gate enforces this through the session-1 evaluation (`session_2_permitted`).

**F5 early strictness is owner Gate B (§14).** Under the committed rule, one failed or unknown dispatch among the
first nine dispatches exceeds the 10% threshold and aborts the session.

## 11. CPU verification status (this pass; no model, no GPU)

| Check | Result | Record |
|---|---|---|
| Installation path on replicas of both mounts: 174 trusted wheels plus publisher metadata; 31 competition wheels; system CPython 3.12. The second run calls the first cell's own `install_pair` | passed. 212 s, and 278 s under concurrent load, for both interpreters. `pip check`, exact versions and torch CUDA build `12.8`; game closure 82 modules, model closure 34; cross-side packages absent; install logs retained; groups verified absent | `reports/feedback_action_v1/runtime_install_check.json` |
| Real offline engine inside the installed game interpreter: the 31 competition wheels, arc-agi 0.9.8, arcengine 0.9.3, numpy 2.4.4 | passed, 41 tests: both sessions on s5i5, ls20 and sk48 with frozen initial hashes; 24 actions per game and arm; s5i5 GAME_OVER at action 50 with nothing after it; the evaluator's real-engine sessions. The same tests also pass in the development environment (arc-agi 0.9.9) | same record |
| Exact token audit, pinned stack inside the installed model interpreter | all 25 forms within limits; completions per Gate A | `research/feedback_action_v1/token_audit.json` |
| Connected rehearsal on the installed interpreter pair: first cell → supervisor → worker → monitor → host → bridge → runner → engine | complete: 144 calls, 144 dispatches. Pinned-tokenizer counts matched across processes. 145/145 completions accepted by the xgrammar 0.1.34 grammar of their request. 72 carried statements reconstructed, 0 mismatches | `reports/feedback_action_v1/cpu_checks_successor-game-interpreter.json` |
| Live model-host factory over HTTP, unchanged code, with a CPU stand-in for vLLM in the model interpreter | passed. Fixture-tree digest check; server in its own group; TCP readiness; log prefix-caching confirmation; the HTTP canary; all 24 request forms of both arms, each schema compiled server-side by xgrammar; token audit equal across processes (max 30,351); server group cleaned up | `reports/feedback_action_v1/cpu_checks_successor-model-interpreter.json` |
| Fault matrix through the connected path | passed: model startup, transport, monitor exit, cancellation, storage exhaustion, surviving child, truncation, F2a, F5 (failed and unknown dispatch), admission cutoff. A deadline mid-pair is checked with a scripted clock | `tests/test_feedback_action_v1_connected.py`, `tests/test_feedback_action_v1_live_evaluation.py` |
| Review snapshot r1 (lock `4b5b7a06…`) | review check: refused at the live gate before installation, model or GPU use; no nvidia-smi call; no files left. Review rehearsal (the same cell, MODE switched, from the extracted payload, on the installed interpreter pair): one complete session, evaluation technically complete | `reports/feedback_action_v1_review_check_r1.json`, `reports/feedback_action_v1_review_rehearsal_r1.json` |
| All Track 1 suites | installed game interpreter (arc-agi 0.9.8, with the installed model interpreter, pinned tokenizer, xgrammar check and replica competition mount for the connected tests): 173 tests, 0 failures. Model interpreter: the HTTP-path test passed. Development environment (arc-agi 0.9.9): 173 tests, 0 failures. Wherever the model interpreter is absent, the HTTP-path test skips | `reports/feedback_action_v1/cpu_checks_*.json` |

**These are CPU checks with scripted completions.** They are not evidence about:
- model behaviour;
- GPU, CUDA or model load;
- guided decoding on the server;
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

**Estimated runtime is not an authorization ceiling.**

The worst case matters: if installation took its full 900 s and startup its full 900 s, then fewer than 6 pairs
could be admitted. The run would then be incomplete; the reservation would not be exceeded. The verified runtime's
whole probe lifecycle, 131 requests included, took 540 s. The budget decision is the owner's.

## 13. Before an exact source and package lock

1. **Owner gates (§14):** record or decline each decision. A recorded decision means a new review revision.
2. **Private bindings:** the consuming account, the model dataset reference and the mount path are resolved in a
   private checkout. That checkout produces a successor review snapshot.
3. **Use and attachment evidence:** account attachment, the direct-use permission outcome and the mounted-byte receipt
   for this scope. The gate requires all three.
4. **Review, source approval and compute authorization**, bound to the review lock, `runtime.json`, `protocol.json`
   and `owner_gates.json`. Then one reservation per session.
5. **Still unverified until a GPU session runs:**
   - the candidate's extended schema through the vLLM server's structured-output path;
   - the competition mount layout on the pinned image;
   - model load and cleanup on the target.

## 14. Owner gates (open)

See `reports/feedback_action_v1_owner_gates.md`.

| Gate | Committed (applies now) | Recommended (implemented, inactive) |
|---|---|---|
| A. Free-text format | `current`: any code point except quote, backslash, CR, LF; ≤ 240 | `ascii_only`: printable ASCII without quote and backslash, ≤ 240, enforced by the decoder |
| B. F5 early abort | running rate from the first dispatch (1 failure in the first 9 aborts) | denominator floor 10 (a single failure never aborts; identical from the 10th dispatch) |

Teammate material at `origin/teammate/windows-track1` `df29206` (the competing-explanations challenge set) is
development material. It could enter only as a separately reviewed amendment.
