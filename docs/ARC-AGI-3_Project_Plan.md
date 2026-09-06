---
title: "ARC Prize 2026 — ARC-AGI-3"
subtitle: "Evidence-Driven Project Execution Plan"
author: "Project Team"
date: "4 September 2026"
status: "Active — supersedes the preliminary plan"
---

# Document purpose

This is the active engineering and research plan for the ARC-AGI-3 Kaggle competition. It supersedes `ARC-AGI-3_Preliminary_Project_Plan.md` while preserving that file as the record of the initial design.

The plan incorporates the competition rules, the first Kaggle milestone results, official ARC Prize replay analyses, and the later public systems that reached near-complete or complete public-set performance. Its purpose is not to reproduce an expensive frontier-model harness. Its purpose is to identify the smallest architecture that can generalize under Kaggle's offline, single-GPU, nine-hour evaluation.

# 1. Executive decision

Build a model-first agent around three mandatory layers:

1. **Lossless evidence:** append every observation, legal-action set, chosen action, outcome, and level transition to a queryable trajectory store.
2. **Compact working state:** maintain a short, revisable symbolic description of objects, mechanics, hypotheses, failed ideas, current goals, and expected outcomes.
3. **Guarded action policy:** use the strongest feasible local model to propose probes and short plans, but validate legality, predicted effects, deadlines, and queue continuation deterministically.

Do not make a full executable world model, a fixed multi-agent hierarchy, or learned test-time training part of the initial critical path. Add them only when a measured failure cannot be addressed more cheaply by better model choice, perception, memory, prompting, retrodiction, or a small task-specific script.

The working thesis is:

> Under Kaggle constraints, model capability and context continuity will provide most of the score; exact evidence, prediction checks, and deterministic guards will prevent that capability from being wasted.

# 2. Target outcome

## 2.1 Primary objective

Produce a reproducible, permissively licensed Kaggle notebook that maximizes private-set RHAE while completing the full hidden evaluation within nine hours and without internet access.

## 2.2 Milestone objective

By the September 30 milestone, deliver a complete local-model system with:

- Valid competition-mode execution over all environments.
- One shared local-model instance with controlled concurrency.
- Exact trajectory logging and compact per-game memory.
- Raw-grid, rendered-image, crop, object, and transition-diff representations.
- Legal actions only, with deterministic fallback and deadline behavior.
- One-to-four-action prediction-checked queues.
- Bounded competing hypotheses and discriminating probes.
- Structural retrodiction against the full interaction history.
- Reproducible ablations showing which components earn their runtime.

## 2.3 Final objective

Between Milestone 2 and November 2, improve hidden-set generalization, model throughput, hypothesis revision, conditional search, and robustness without adding public-game-specific logic.

# 3. Evidence translated into design rules

| Evidence | Finding | Project decision |
|---|---|---|
| Kaggle Milestone #1 | The winning Duck harness used Qwen 3.6 27B FP8, images plus raw grids, a Python REPL, and a deliberately small harness. Reki and forge used Gemma-4-31B, reflection memory, short JSON action queues, and deterministic guards. Extra candidate-selection machinery was disabled in forge's best run. | Start simple, profile strong local models early, keep mixed perception, and require ablation evidence for every layer. |
| OpenAI context study | Retained reasoning and compaction raised GPT-5.6 Sol public performance from 13.3% to 38.3% while cutting output tokens by roughly six times. | Never make each model call reconstruct the game from scratch. Preserve conclusions explicitly and compact before truncating evidence. |
| PRO-LONG | A complete structured log plus programmatic search improved a basic coding agent by an average of 18 percentage points; the full log mattered more than elaborate note tooling. | Write every transition losslessly. Keep raw evidence outside the active prompt and retrieve it with deterministic queries. |
| Rodionov component study | Stronger models and larger reasoning budgets helped every tested architecture. Verification ranked first, but forcing a persistent executable simulator was not consistently beneficial and was expensive. | Treat model selection and inference allocation as first-order experiments. Verify routinely; simulate conditionally. |
| Tycho | Actor-requested model construction outperformed automatic repair even though automatic repair produced more exact models. A fixed single configuration reached 100% publicly with frontier models. | Let observable need trigger modeling. Exactness is valuable only when it changes decisions. |
| Retrodict and Schema | Successful systems test hypotheses against recorded transitions and stop queued plans when observations diverge. | Make retrodiction and queue invalidation core behavior. |
| VISTA, AVO, and Prime Agent | Public success repeatedly correlates with persistent state, compact context, programmatic inspection, recovery, and flexible tool use. | Build durable state and recovery semantics before specialized solvers. |
| Official failure analysis | Agents form false global models from true local effects, import misleading familiar-game analogies, or clear a level without learning why. | Track evidence and contradictions, discourage genre analogies, and require a level-boundary learning review. |
| GPT-6 Astra | On the semi-private set, dense symbolic shorthand and preserved context accompanied 62.7% with the standard harness and 99.9% with the provider adapter. | Optimize the local prompt around a compact symbolic state rather than repeatedly serializing the entire trajectory. |

Public frontier results are architectural evidence, not expected Kaggle scores. They often use closed models, large API budgets, public environments, provider-specific reasoning retention, or best-of-multiple-run selection. Only Kaggle milestone systems directly demonstrate operation under the competition's offline constraints.

# 4. Fixed constraints

## 4.1 Environment and scoring

- Observations are sequences of up to 64 × 64 grids over a 16-color palette.
- The goal, mechanics, object roles, and action semantics are not described.
- The available action subset can change; `ACTION6` carries an `(x, y)` coordinate.
- Later levels normally extend or combine earlier mechanics.
- Per-level RHAE is based on `(human_actions / agent_actions)^2`, capped at 1.15.
- Later levels receive larger weights, so preserving learned mechanics across levels is essential.
- Every environment action is both a control decision and a potentially costly experiment.

## 4.2 Kaggle execution

- Maximum notebook runtime: nine hours.
- Internet disabled during evaluation.
- Model weights and dependencies must be attached in advance.
- One environment creation and one scorecard in competition mode.
- All hidden environments contribute to the score, including untouched games.
- Multiple game agents may run concurrently, so GPU inference must be shared and bounded.
- The final system must be open source and reproducible with compatible licenses.

## 4.3 Engineering budget

- Design to finish within 7.65 hours, preserving a 15% safety margin.
- Treat GPU memory, host memory, disk, model tokens, queue wait, and environment actions as separate budgets.
- Never allow a model exception, parse failure, or timeout to crash a game thread.
- Do not use game IDs, public solution tables, or inspected engine internals in the production policy.

# 5. Target architecture

```text
Frames + legal actions + status
              │
              ▼
    Deterministic perception
    - stable-frame selection
    - exact grid and delta
    - components and crops
    - state/action fingerprints
              │
       ┌──────┴────────┐
       ▼               ▼
Lossless event log   Compact state
(complete evidence)  - confirmed rules
                     - live hypotheses
                     - failed hypotheses
                     - current subgoal
                     - short plan + predictions
       └──────┬────────┘
              ▼
        Local model policy
    observe → hypothesize → probe/plan
              │
              ▼
    Retrodiction and plan checks
              │
     ┌────────┴──────────┐
     ▼                   ▼
prediction holds    contradiction/uncertainty
     │                   │
execute short queue   probe, revise, or escalate
     └────────┬──────────┘
              ▼
   Legal/runtime/safety guard
              │
              ▼
        Environment action
```

## 5.1 Deterministic perception

Mandatory outputs for every step:

- Canonical current frame and all transient frames retained in the event log.
- Exact changed-cell mask and compact changed-region summary.
- Color counts, bounding box of change, and stable-frame hash.
- Connected components with color, area, bounding box, centroid, shape mask, and adjacency.
- Candidate correspondences between previous and current components.
- Available actions, game state, level count, step count, and remaining budgets.
- Click candidates derived from components, rare colors, endpoints, intersections, changed regions, and button-like small shapes.

The model can receive any combination of:

- A nearest-neighbor rendered PNG.
- The exact ASCII or integer grid.
- Selected crops or component masks.
- A deterministic transition diff.
- A compact object table.

Representation selection should be controlled by measured usefulness and prompt cost. The raw evidence must remain retrievable even when it is omitted from the active prompt.

## 5.2 Lossless event log

Each game owns an append-only transition record containing:

```text
game / level / attempt / step
pre-action frame sequence
canonical pre-action frame
available actions
chosen action and coordinates
model proposal and declared expectation
canonical post-action frame
exact and structural diff
status / reward / level transition
queue continuation or invalidation
timing / token / fallback data
```

Requirements:

- The write path is deterministic and does not ask the model what to preserve.
- Large frames may be compressed on disk, but compression must be lossless.
- Query helpers retrieve transitions by level, attempt, action, changed object, status, score change, or hypothesis reference.
- The model receives only the relevant slices plus a compact summary, not the whole log on every call.

## 5.3 Compact per-game state

Use three separate stores:

### Durable game memory

- One-sentence current objective hypothesis.
- Confirmed action semantics and mechanics.
- Cross-level invariants.
- Known hazards and irreversible actions.
- Reusable strategies and execution macros.
- Important counterexamples.

### Level scratch state

- Current objects and latent-state estimates.
- Two to four active hypotheses.
- Current subgoal and cheapest useful probe.
- Candidate plan and expected effects.
- Unresolved observations.

### Rejected-hypothesis ledger

- Rejected claim.
- Evidence that rejected it.
- Scope of rejection.
- Conditions under which it may be reconsidered.

This separation prevents stale level details from polluting the durable model while preventing contradicted ideas from being rediscovered repeatedly.

## 5.4 Hypothesis records

Every active hypothesis must state:

| Field | Meaning |
|---|---|
| Claim | Compact proposed rule or goal |
| Scope | Game-wide, level-specific, object-specific, or state-dependent |
| Evidence for | Transition references that support it |
| Evidence against | Contradictions or unexplained observations |
| Predictions | Expected results of candidate legal actions |
| Discriminator | Cheapest action expected to distinguish it from alternatives |
| Risk | Reversibility and failure cost of that action |
| Complexity | Penalty for exceptions and level-specific clauses |
| Status | Tentative, supported, verified-for-plan, contradicted, or retired |

Hypotheses are ranked by predictive coverage, contradictions, simplicity, expected progress, probe cost, and risk. Model confidence is advisory and must not be used as the ranking signal by itself.

## 5.5 Model action contract

A normal model response should contain:

```json
{
  "state_update": "compact revision, if any",
  "hypothesis_updates": [],
  "mode": "probe | execute | recover | escalate",
  "subgoal": "short target state",
  "actions": [
    {
      "action": "ACTION1",
      "data": null,
      "expected_effect": "specific observable change",
      "stop_if": "material mismatch condition"
    }
  ],
  "memory_update": "durable fact only, or null"
}
```

The parser must repair only syntax and schema defects. It must never invent an action that the model did not propose. If repair fails, the deterministic controller chooses a legal fallback.

## 5.6 Prediction-checked execution

- Queue one action when exploring, after contradiction, or under high risk.
- Queue up to four actions only when earlier dynamics are verified and every step has a meaningful expected effect.
- Validate the observation after each environment action.
- Stop immediately on a state, legal-action, status, object, or changed-mask mismatch material to the plan.
- Do not treat a level completion as proof of the proposed mechanic; run a level-boundary retrospective first.
- Reuse an established plan in later levels only after the first materially new transition matches expectation.

## 5.7 Retrodiction and verification

Verification escalates through three levels:

1. **Outcome:** predict no-op, progress, death, reset, or level transition.
2. **Structural:** predict changed regions, object motion, recoloring, creation/deletion, counts, and relations.
3. **Exact:** reproduce the canonical next grid when exactness is useful and the observation process is demonstrably deterministic.

Structural retrodiction is mandatory before a hypothesis controls a long action sequence. Exact reconstruction is optional. A hypothesis may be useful without explaining decorative or irrelevant pixels, but its unexplained regions must remain visible in diagnostics.

## 5.8 Conditional executable modeling

The local model may create a small Python transition or planning function only when at least one trigger fires:

- A plan requires more steps than can be reasoned about reliably in text.
- Multiple hypotheses remain consistent and can be separated by replay.
- The observed state graph is small enough for BFS or A*.
- The same deterministic transformation recurs across levels.
- Two recovery cycles have failed without a new explanation.
- A fixed action threshold is crossed on the current level without progress.

Generated code must run in a temporary isolated process with restricted imports, bounded CPU time, bounded memory, bounded output, and no write access to agent source, model artifacts, credentials, or submission files.

The executable model is a tool, not a required deliverable. Delete or bypass it when maintaining it costs more than the decisions it improves.

## 5.9 Reasoning controller

Use observable triggers to select one of four modes:

| Mode | Trigger | Behavior |
|---|---|---|
| Fast | Verified plan and previous prediction matched | Continue short queue with minimal model work |
| Normal | Reversible decision with one leading explanation | One model call, one action or short checked queue |
| Deep | Competing hypotheses, novel mechanism, or irreversible choice | Larger reasoning budget, retrieve older evidence, consider scripts |
| Recovery | Repeated no-op, loop, contradiction, parse failure, death, or stagnation | Clear invalid plan, revisit rejected ideas, choose discriminating probe or escalate |

The controller should reduce model calls through verified action queues, not through blind batching of actions.

## 5.10 Shared inference service

- Load the model exactly once.
- Serialize or dynamically batch requests through a bounded queue.
- Keep all game reasoning and memories isolated.
- Track queue wait, inference time, tokens, actions per call, timeouts, and fallback rate by game.
- Apply fairness so one difficult game cannot monopolize the GPU.
- Reserve wall-clock time for every not-yet-finished environment.
- Move to a smaller model, shorter context, or deterministic fallback as the global deadline approaches.
- Avoid mutating shared `GameAction` enum instances when attaching coordinate data.

# 6. Baseline repair plan

The current `agent/my_agent.py` remains a plumbing baseline and must be corrected before model integration:

- Replace enumeration of all actions with `latest_frame.available_actions` or the pinned SDK's equivalent.
- Remove the `ls20` game-ID branch.
- Replace module-global `random.seed(...)` with a per-agent RNG object.
- Replace wall-clock seeding with a stable recorded seed for reproducible evaluation.
- Ensure coordinate actions receive fresh, thread-safe payload state.
- Add state/action fingerprinting and no-op suppression.
- Add bounded reset behavior and explicit handling of `NOT_PLAYED`, `GAME_OVER`, and `WIN`.
- Log every fallback decision and its reason.
- Add unit tests before changing the policy from random to model-driven.

# 7. Experiment ladder

All treatments are incremental. Each treatment must be compared with the previous accepted system in closed-loop runs.

| ID | Treatment | Primary question |
|---|---|---|
| E0 | Correct deterministic fallback | Can the full pipeline run without invalid actions or crashes? |
| E1 | Local model + current frame/grid + legal actions | Does the model produce non-random progress within the runtime envelope? |
| E2 | Mixed perception: image, grid, crops, components, delta | Which representation mix improves completion per prompt token and second? |
| E3 | Compact durable memory + level scratch state | Does continuity improve later levels and reduce repeated exploration? |
| E4 | Lossless log retrieval + retrodiction | Does access to exact earlier evidence prevent false models and repeated failures? |
| E5 | Bounded hypothesis beam + discriminating probes | Does explicit uncertainty improve progress per action? |
| E6 | Prediction-checked one-to-four-action queues | Can model calls fall without increasing plan failures or wasted actions? |
| E7 | Conditional scripts/executable model | Does escalation solve a documented long-horizon or search failure cheaply enough? |
| E8 | Conditional search over a verified model | Does planning improve later-level completion or RHAE? |
| E9 | Optional specialist call | Does a second role outperform spending the same tokens on the primary model? |

E0 through E6 are the milestone critical path. E7 through E9 are conditional.

# 8. Evaluation protocol

## 8.1 Data partitions

Before additional public-game inspection:

1. Record every environment whose play, source, trajectories, or solution discussion has already been inspected.
2. Place exposed environments in the development set.
3. Randomly select at least five uninspected environments as a sealed architecture holdout.
4. Use a separate rotating diagnostic set for ordinary iteration.
5. Never introduce a game-ID condition or public solution primitive into production code.
6. Open the sealed holdout only at named architecture gates.
7. Use Kaggle leaderboard submissions as sparse confirmation, not as the daily optimizer.

## 8.2 Run protocol

- Fix model, quantization, prompt, context policy, seed, action cap, and runtime limits before every comparison.
- Report pass@1-style single runs as the primary result.
- Run multiple seeds when affordable and report all results, not only the best.
- Label selective reruns and best-of-k results separately.
- Evaluate perception and replay code on fixed trajectories, but accept policy changes only from closed-loop runs.
- Archive configuration, source commit, model hashes, prompt, event logs, scorecard, and hardware metrics together.

## 8.3 Metrics

| Category | Required metrics |
|---|---|
| Completion | Games won, levels completed, weighted completion fraction |
| Action efficiency | Actions per completed level, estimated RHAE, actions before first progress |
| Exploration | No-op rate, repeated state-action rate, probe success, resets, deaths |
| Model quality | Valid schema rate, fallback rate, hypothesis contradictions, revision latency |
| Prediction | Outcome accuracy, changed/unchanged accuracy, structural accuracy, queue break rate |
| Continuity | Repeated rejected hypotheses, later-level transfer, evidence retrieval frequency |
| Compute | Calls, input/output tokens, latency, queue wait, actions per call, RAM/VRAM, total runtime |
| Reliability | Invalid actions, uncaught exceptions, timed-out games, starved threads, incomplete scorecards |
| Generalization | Development/diagnostic/holdout gaps and leaderboard confirmation gap |

## 8.4 Merge gate

Accept a change only if it does at least one of the following without crossing the runtime or reliability ceiling:

- Completes more held-out levels.
- Improves action efficiency on already completed levels.
- Eliminates a documented failure mode.
- Reduces model calls or runtime without losing completion.
- Improves prediction accuracy in a way that changes closed-loop behavior.
- Improves reliability or deadline completion.

Reject or defer a change when:

- Its only gain is on one exposed public game.
- It depends on a best seed or selective rerun.
- It raises projected full-run time above 7.65 hours.
- It increases framework complexity without a measurable behavioral effect.
- It improves simulator accuracy but not action selection.

# 9. Model selection protocol

Begin with three candidates:

1. The strongest local model that fits the target Kaggle accelerator, using the Duck winner's Qwen 3.6 27B FP8 as a reference point.
2. A second architecture with strong visual reasoning, using the Milestone #1 Gemma-4-31B systems as a reference point.
3. A smaller fallback candidate that preserves more time for repeated reasoning or supports deadline degradation.

For every candidate, measure:

- License and redistribution compatibility.
- Offline artifact size and notebook attachment behavior.
- CUDA/kernel compatibility on actual Kaggle hardware.
- Peak VRAM and host RAM.
- Cold-load time and first-token latency.
- Tokens per second at representative context lengths.
- Structured-output reliability.
- Closed-loop levels completed, not only visual-question-answer accuracy.
- Performance with image-only, grid-only, and mixed input.
- Score at a fixed wall-clock and token budget.

Choose the model by closed-loop score within the full-run envelope, not by parameter count or public model benchmarks.

# 10. Schedule

## Phase 0 — Submission and measurement foundation

**September 4–6**

- [ ] Initialize version control and pin Python, SDK, framework commit, packages, notebook builder, and artifact hashes.
- [ ] Accept competition rules and validate the Kaggle submission path.
- [ ] Create the public-game exposure log and seal the holdout.
- [ ] Repair the current fallback agent.
- [ ] Add canonical-frame extraction, hashing, transition logging, and machine-readable reports.
- [ ] Add unit tests for legal actions, coordinate payloads, terminal states, RNG isolation, and no-op suppression.
- [ ] Produce the first valid Kaggle submission.

**Exit gate:** three complete development runs produce zero invalid actions and zero uncaught agent exceptions; a clean checkout builds a valid submission notebook.

## Phase 1 — Local-model vertical slice

**September 7–10**

- [ ] Profile the three model candidates on Kaggle hardware.
- [ ] Implement shared single-load inference with a bounded request queue.
- [ ] Provide current image, raw grid, exact delta, legal actions, and a short history.
- [ ] Implement the strict action schema, bounded syntax repair, timeout, and deterministic fallback.
- [ ] Record model latency, tokens, queue time, VRAM, calls, and actions.
- [ ] Select the primary and fallback models.

**Exit gate:** E1 beats E0 on repeated closed-loop diagnostic runs and projects below 7.65 hours over the hidden evaluation.

## Phase 2 — Evidence, perception, and context continuity

**September 11–15**

- [ ] Complete the append-only lossless event store and deterministic query helpers.
- [ ] Add connected components, crops, object tables, and click candidates.
- [ ] Compare image-only, grid-only, and mixed representations.
- [ ] Implement durable game memory, level scratch state, and rejected-hypothesis ledger.
- [ ] Add explicit compaction triggers that retain transition references.
- [ ] Add level-boundary retrospectives.

**Exit gate:** E2–E4 improve later-level completion, reduce repeated exploration, or eliminate documented false-memory failures without exceeding the compute envelope.

## Phase 3 — Active hypothesis testing and guarded plans

**September 16–20**

- [ ] Implement two-to-four competing hypotheses.
- [ ] Rank discriminating probes by information value, reversibility, and action cost.
- [ ] Add outcome and structural retrodiction.
- [ ] Implement one-to-four-action queues with expected effects and immediate invalidation.
- [ ] Add fast, normal, deep, and recovery modes.
- [ ] Add stagnation, loop, repeated-no-op, death, and contradiction recovery.

**Exit gate:** E5–E6 improve completion or actions per completed level across repeated diagnostic runs and one sealed-holdout gate.

## Phase 4 — Conditional modeling and competition load

**September 21–25**

- [ ] Implement the isolated script/executable-model boundary.
- [ ] Test conditional E7 only on documented failures.
- [ ] Test E8 search only where a verified compact state model exists.
- [ ] Run a concurrent 110-game load simulation with queue fairness and deadline degradation.
- [ ] Test offline notebook packaging from a clean environment.
- [ ] Confirm artifact licenses and hashes.

**Exit gate:** the competition-like run finishes below 7.65 hours; no thread crashes or starves; every failure degrades to a legal action. E7/E8 remain enabled only if they improve the fixed comparison.

## Phase 5 — Milestone candidates and freeze

**September 26–30**

- [ ] Produce a conservative candidate and a higher-reasoning candidate.
- [ ] Complete full Kaggle reruns early enough to diagnose infrastructure failures.
- [ ] Freeze code, prompt, model, quantization, dependencies, and configuration on September 28.
- [ ] Archive all traces, reports, scorecards, licenses, and reproduction instructions.
- [ ] Use September 29–30 only for release verification and submission recovery.

**Milestone deadline:** September 30, 11:59 PM UTC / October 1, 7:59 AM China Standard Time.

## Phase 6 — Hidden-generalization analysis

**October 1–12**

- Analyze discrepancies among development, sealed, and leaderboard results.
- Improve hypothesis revision and cross-level transfer.
- Expand synthetic tests by mechanic composition, not only new layouts.
- Reduce reliance on public-set visual frequencies.
- Revisit exact replay, conditional simulation, and search where milestone failures justify them.

## Phase 7 — Robustness and efficiency

**October 13–22**

- Optimize quantization, context length, batching, and action-call ratio.
- Run repeated long-duration concurrency tests.
- Verify deadline-aware degradation and failure recovery.
- Reduce RAM, disk, log, and notebook size.
- Consider specialist calls or test-time adaptation only through fixed-budget comparisons.

## Phase 8 — Final freeze

**October 23–November 2**

- Complete any team merger before the competition cutoff.
- Freeze all source, weights, dependencies, prompts, and licenses.
- Produce two final candidates with explicit score/runtime risk differences.
- Run clean-checkout reproduction and open-source audits.
- Submit early and archive the exact final artifacts.

**Final deadline:** November 2, 11:59 PM UTC / November 3, 7:59 AM China Standard Time.

# 11. Immediate 72-hour backlog

Execute in this order:

1. Create the exposure log and sealed holdout before inspecting more games.
2. Initialize and pin the repository and submission toolchain.
3. Repair `agent/my_agent.py` so every action is legal, generic, deterministic under a fixed seed, and thread-safe.
4. Add canonical-frame extraction, hashes, exact diffs, and the append-only transition schema.
5. Add JSON and Markdown run reports.
6. Run and archive three deterministic fallback baselines.
7. Produce a valid Kaggle submission.
8. Build the smallest offline local-model smoke notebook.
9. Measure actual Kaggle load time, VRAM, inference latency, and structured-output validity.
10. Select the primary model only after the first closed-loop comparison.

# 12. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Public-game overfitting | Critical | Exposure log, sealed holdout, no game-ID logic, sparse leaderboard use |
| Model cannot finish 110 games | Critical | Early Kaggle profiling, shared serving, short verified queues, adaptive context, smaller fallback |
| Lost context or false summaries | High | Lossless event log, transition references, explicit compaction, rejected-hypothesis ledger |
| False theory becomes a long plan | High | Competing hypotheses, retrodiction, one-step probing, prediction-checked queues |
| Excessive simulator work | High | Conditional triggers, resource accounting, bypass/delete when not decision-useful |
| Invalid or shared mutable actions | Critical | Dynamic legal filtering, fresh coordinate payloads, per-agent state, concurrency tests |
| Queue starvation | High | Fair bounded queue, per-game quotas, deadline-aware priority and degradation |
| Model parse or inference failure | High | Strict schema, bounded repair, timeout, deterministic legal fallback |
| Generated code escapes or hangs | Critical | Isolated process, restricted imports/filesystem, CPU/memory/output/time limits |
| CUDA or offline packaging failure | Critical | Early Kaggle smoke tests, pinned wheels and kernels, clean-room notebook build |
| Misleading public scores | High | Pass@1 primary reporting, disclose model/harness/reruns/cost, sealed and hidden evidence prioritized |
| License ineligibility | Critical | Review model, code, and data licenses before committing to artifacts |

# 13. Definition of done

The milestone candidate is ready only when:

- It completes a full competition-like run within 7.65 hours.
- It creates a valid scorecard and submission artifact.
- It chooses only available actions and handles coordinate actions safely.
- It records every transition and can reconstruct the evidence for every decision.
- Its compact memory stays bounded over long games.
- Its queued actions stop on material prediction mismatch.
- Model and infrastructure failures degrade to legal deterministic behavior.
- No production behavior depends on public game IDs or solution-specific constants.
- The accepted components have closed-loop ablation evidence.
- Source, weights, dependencies, prompts, hashes, licenses, and reproduction instructions are archived.

The final candidate additionally requires repeated full-run stability, a documented generalization analysis, and two frozen risk profiles submitted before the deadline.

# 14. Decision principles

- Optimize hidden-set generalization, not public-game perfection.
- Preserve evidence losslessly; compress access, not history.
- Prefer a compact, revisable causal account over a long narrative transcript.
- Treat every live action as both an intervention and a score cost.
- Require predictions before long execution and check them after every step.
- Make verification routine and exact simulation conditional.
- Prefer one capable agent with good state over fixed multi-agent ceremony.
- Spend extra reasoning only when novelty, contradiction, risk, or expected value justifies it.
- Evaluate model and harness together, but report their contributions separately.
- Introduce complexity only to address a measured failure.
- Freeze early enough for Kaggle failures to be recoverable.

# 15. Primary references

- [ARC-AGI-3 technical report](https://arcprize.org/media/ARC_AGI_3_Technical_Report.pdf)
- [Kaggle competition](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3)
- [ARC-AGI-3 documentation](https://docs.arcprize.org/)
- [Measuring Human Performance on ARC-AGI-3](https://arcprize.org/blog/arc-agi-3-human-dataset)
- [Analyzing GPT-5.5 and Opus 4.7](https://arcprize.org/blog/arc-agi-3-gpt-5-5-opus-4-7-analysis)
- [ARC-AGI-3 Milestone Prize #1](https://arcprize.org/blog/arc-prize-2026-milestone-1)
- [Duck Harness](https://tufalabs.ai/research/duck-harness/)
- [How enabling two settings tripled ARC-AGI-3 scores](https://openai.com/index/how-two-settings-tripled-our-arc-agi-3-scores/)
- [OpenAI's GPT-6 Astra on ARC-AGI-3](https://arcprize.org/blog/astra)
- [PRO-LONG](https://arxiv.org/abs/2607.20064)
- [Executable World Models for ARC-AGI-3](https://arxiv.org/abs/2605.05138)
- [Executable-model component study](https://arxiv.org/abs/2607.15439)
- [Tycho](https://arxiv.org/abs/2607.28287)
- [Retrodict](https://github.com/ryanbbrown/Retrodict)
- [Schema](https://schema-harness.github.io/)
- [OPINE-World](https://arxiv.org/abs/2607.01531)
- [DreamTeam / Workspace Optimization](https://arxiv.org/abs/2605.09650)
- [VISTA](https://vista-research.github.io/)
- [Prime Agent](https://arxiv.org/abs/2608.23552)
- [NVIDIA AVO](https://developer.nvidia.com/blog/nvidia-avo-reaches-100-on-arc-agi-3-demonstrating-a-frontier-level-general-purpose-architecture-for-long-horizon-autonomous-agents/)
- [ARC-AGI community leaderboard and disclosure policy](https://arcprize.org/leaderboard/community)
