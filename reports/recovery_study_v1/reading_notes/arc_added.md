# Reading notes: ARC-AGI-3 harness papers, harness-evaluation papers, ARC Prize policy and results page

Reader notes for the recovery study (R0 control / R1 stall detection / R2 priced recovery).
Fetched 2026-11-14 with `tools/fetch_doc.py`. Text copies are in `scratchpad/library/<name>/text.txt`.
Convention: "QUOTE" = exact sentence from the document (section given). "INFERENCE" = my reading, not stated by the document.

## 0. What was read, and how much

| # | Document (title as fetched) | Version | Coverage |
|---|---|---|---|
| 1 | "Executable World Models for ARC-AGI-3 in the Era of Coding Agents" (Rodionov), arXiv 2605.05138 | v2, 06 Jun 2026 | All of it (965 lines; no appendix). Title matches. |
| 2 | "Do Coding Agents Need Executable World Models, Simplification, and Verification to Solve ARC-AGI-3?" (Rodionov), arXiv 2607.15439 | v2, 27 Aug 2026 | Main text sections 1-9 in full; appendix 12 (exact prompts) in full; appendix 10-11 per-game tables skimmed (they hold only score / unsolved-levels). References not read. Title matches. |
| 3 | "OPINE-World: Programmatic World Modeling with Ontology-error-Prioritized Interactive Exploration for ARC-AGI-3" (Courtis, Li, Sanner), arXiv 2607.01531 | v3, 26 Sep 2026 | Main text in full; appendices B.6-B.8, C, D, E, F.1-F.5, F.8, F.9, G in full; appendices A, B.1-B.5, F.6-F.7 keyword-searched only (reset, game over, undo, checkpoint, stall, budget, attempt, terminate). Title matches ("OPINE-World"). |
| 4 | "Rethinking the Evaluation of Harness Evolution for Agents" (Wang, Zhu, et al.; AI2 / UW), arXiv 2607.12227 | v4, 05 Oct 2026 | Main text in full; appendices A and B in full except the numeric rows of Table 11 (win rates) and the lp85 per-level table; appendix C read to the start of Table 15. Title matches. |
| 5 | "Self-Harness: Harnesses That Improve Themselves" (Zhang et al., Shanghai AI Lab), arXiv 2606.09498 | v3, 20 Aug 2026 | All of it including appendices A-B (figure captions only for figures). Title matches ("Self-Harness"). |
| 6 | "HarnessDev: Can LLMs Create and Evolve Their Own Agent Harness?" (ByteDance Seed et al.), arXiv 2609.01437 | v1, 01 Sep 2026 | Main text sections 1-6 in full (numeric rows of Tables 3-4 skipped); appendix B (configuration) and E.2 (evolution contract prompt) read; appendices A, C, D, F-I keyword-searched only. Title matches ("HarnessDev"). |
| 7 | https://arcprize.org/policy - "ARC Prize Verified Testing Policy" | page as served 2026-11-14 | All of it (383 lines of text). |
| 8 | https://arcprize.org/results/anthropic-claude-opus-5-5 - "Claude Opus 5.5 - ARC-AGI Results" | page as served 2026-11-14 | Rendered text in full, plus the embedded page data in raw.html (decoded copy at `library/arc_opus55/decoded_payload.txt`). |

All eight fetches succeeded on the first try. Nothing below is from memory unless labelled.

---

## A. Policy and results pages

### A1. Harness definitions (policy, section "How We Run Evaluations: ARC-AGI-3" > "ARC-AGI-3 Harnesses")

QUOTES (complete passage):
- "We may report ARC-AGI-3 results using two evaluation conditions:"
- "Standard harness - Uses a minimal, provider-neutral interface. It enables a model to carry forward notes it chooses to keep throughout the environment."
- "Provider Adapter harness - Uses provider-designed context-management features, such as preserving opaque reasoning state between requests and using compaction for longer conversations."
- "These harnesses answer different evaluation questions. We report their results separately and clearly label the harness used for each result. You can learn more about the distinction in our GPT-6 Astra blog post."

Check of the plan sentence ("the adapter differs by preserving opaque reasoning state between requests and compacting long conversations"):
- Supported as a paraphrase. Three qualifications:
  1. The policy says "such as": the two features are examples of "provider-designed context-management features", not an exhaustive definition.
  2. The plan sentence leaves out what the Standard harness does provide: a "minimal, provider-neutral interface" in which the model can "carry forward notes it chooses to keep throughout the environment". So the Standard harness is not memoryless; it has a model-curated notes channel.
  3. The policy defers the fuller distinction to a "GPT-6 Astra blog post", which was not on my list and was not read.

### A2. Rules on action limits, resets, cost, runs, what counts as an action, score reporting (policy)

What the policy states:
- Cost cap and number of runs (section "What We Test" > "Verified Leaderboard"): "We cap our evaluations at $10,000 USD per run. No single semi-private evaluation run can exceed this amount. A single run is used, we do not average scores across runs."
- How runs are configured: "ARC-AGI-3 evaluations are run using the open source ARC-AGI-3 Benchmarking repository." and "As with ARC-AGI-1 & 2, we create a model configuration (example) for each new model specifying model name, reasoning levels, and token limits." (The linked repository is github.com/arcprize/arc-agi-3-benchmarking; not read.)
- Action space (FAQ "Are models tested as agents?"): "ARC-AGI-3 is interactive: models take actions within each task to play the game, so the available action space is part of the task itself. In any case where a model is tested with a defined action or tool space, that space is specified in the open-source model configuration. Humans are given the same input actions as buttons in the testing app and keyboard."
- Tools (FAQ): "By default, yes. We do not enable additional tools behind the model, including code execution. We specifically do not enable web search..." and "tool use should be opt-in, not opt-out, so any tool use will always be declared."
- Reporting: "Results are published on arcprize.org" and "ARC-AGI-3 results pages also include replays showing the exact run a model performed on each individual task. ... Replays provide full transparency into how a model interacted with a task during evaluation."
- Cost metric (FAQ): "We will use retail pricing to assess cost efficiency."
- Reasoning levels (FAQ): "we will often repeat model tests at varied reasoning levels." and "We may not publish results for every reasoning level. ... When we do not publish a given reasoning level, we will say so explicitly and explain why it was omitted."
- Public vs semi-private (section "Submission Rules"): "ARC-AGI-3 - The public demo is harder than the Semi-Private set, so we expect Semi-Private scores to be the higher of the two; scores are in good agreement when within ±15 percentage points."
- Community submissions: "$10,000 USD is the maximum amount that can be spent on runtime costs, including calling commercial APIs." and "Solutions must be submitted via a Kaggle notebook and run in <12 hours".
- Testing philosophy: "our scoring methodology attempts to replicate the exact same testing procedure for all test-takers (whether AI or human) such that no one is benefited by having additional information, context, strategy, or answers."

What the policy does NOT state (searched the full text for reset, game over, action limit, max actions, RHAE, budget: zero hits):
- No per-game or per-level action limit.
- No rule on RESET, GAME_OVER, undo, or replay.
- No definition of what counts as an action.
- No definition of RHAE or how per-level scores aggregate.
These have to come from the benchmarking repository, the ARC-AGI-3 paper (arXiv 2603.24621) or the scorecard documentation, none of which were on my list. The harness papers supply partial answers (section B below).

### A3. Claude Opus 5.5 results page

- Header: "Anthropic·Sep 22, 2026·5 reasoning variants·$4 input / $20 output per 1M tokens". Summary line: "At high reasoning effort, Claude Opus 5.5 scores 98.5% on v1 semi-private and 93.3% on v2 semi-private."
- "Verified scores" table as rendered:

| Variant | ARC-AGI-1 | ARC-AGI-2 | ARC-AGI-3 |
|---|---|---|---|
| Max | 97.5% | 91.7% | — |
| XHigh | 97.5% | 92.5% | — |
| High | 98.5% | 93.3% | — |
| Medium | 97.5% | 87.5% | — |
| Low | 88.5% | 70.1% | — |

- **There is no ARC-AGI-3 result for Claude Opus 5.5 on this page.** The rendered table shows "—" in every ARC-AGI-3 cell. The embedded page data confirms it: for the page's own model group the scores block is `"v3":[null,null,null,null,null]` and the task block is `"tasks":{"v1":[...],"v2":[...],"v3":[]}`. The "Tasks & environments" section lists only "ARC-AGI-2 Public Eval 120 tasks" and "ARC-AGI-1 Public Eval 400 tasks". There are no Provider Adapter variants listed for Opus 5.5.
- Consequently the page reports no ARC-AGI-3 score, action count, cost, per-game or per-level detail, resets or game overs for Opus 5.5. Anything the plan attributes to "Opus 5.5's published ARC-AGI-3 result" cannot be sourced from this page.
- Embedded ARC-AGI-1/2 data for Opus 5.5 (score, cost per task in USD as I read the field): v1 Max 0.975 / 0.641, XHigh 0.975 / 0.223, High 0.985 / 0.158, Medium 0.975 / 0.152, Low 0.885 / 0.120; v2 Max 0.917 / 1.852, XHigh 0.925 / 0.671, High 0.933 / 0.408, Medium 0.875 / 0.337, Low 0.701 / 0.241.
- Context only (embedded comparison data on the same page, used by its leaderboard chart; these are other models, not rendered as tables here, field units unlabelled):
  - Claude Opus 5 (variants Max, High; no Provider Adapter variants): ARC-AGI-3 entry only for High: score 0.3016, cost 20,657.37.
  - Claude Fable 5.2: Standard Max/XHigh/High/Medium/Low = 0.657 / 0.812 / 0.793 / 0.733 / 0.520; Provider Adapter Max/XHigh/High/Medium/Low = 0.949 / 0.973 / 0.977 / 0.968 / 0.923; cost field 17,141 to 34,907.
  - Claude Sonnet 5.5: Standard XHigh 0.243, High 0.012, Medium 0.004, Low 0.004; Provider Adapter XHigh 0.724, High 0.355, Medium 0.049, Low 0.006.
  - GPT-6 Astra: Standard 0.175 to 0.627; Provider Adapter 0.967 to 0.9995.
  - INFERENCE: in this embedded data the Provider Adapter condition scores far above the Standard condition for the same model, so the context-management layer is a first-order factor on ARC-AGI-3. INFERENCE: the cost field for ARC-AGI-3 entries (about 17k to 50k for the large models) exceeds the policy's "$10,000 USD per run" cap if it is total USD per run; the JSON does not label units and I could not resolve this.
- Resets or game overs are not a field anywhere in the embedded data (keys present: score, cost, rank, total, taskId, results).

---

## B. ARC-AGI-3 harness papers

Terminology warning (INFERENCE): in papers 1-3 "replay" means re-simulating recorded actions inside the agent's own world model and comparing with recorded observations (an offline check that costs no environment actions). In our study "replay" means re-executing a stored action prefix in the real environment after a reset (which costs environment actions). None of the three papers does the latter automatically.

### B1. Paper 1 - Rodionov, "Executable World Models..." (baseline1 agent; Codex CLI 0.128.0; GPT-5.4 / GPT-5.5 high)

Game over, reset:
- Sec 2.1: "A level attempt may end in either LEVEL_COMPLETED or GAME_OVER. If GAME_OVER is reached, the benchmark-provided RESET action can be used to restart the current level attempt within the same game run. RESET is treated as an ordinary environment action and counts against the action budget. The agent cannot restart the whole game to obtain a better run, and the agent cannot return to previously completed levels."
- Sec 2.2: "If GAME_OVER is reached, the controller issues RESET, returns the new attempt observation, and asks the coding agent to simplify and refactor the world model before continuing."
- Sec 4 (Local execution): "The coding agent itself is not instructed to use RESET; this action is normally sent by the external controller after GAME_OVER. Occasionally, the coding agent nevertheless discovers that it can send RESET itself, which we do not treat as problematic by itself."
- Sec 4, a hazard that matters for forced resets: "Local mode has one behavior that is not allowed by our evaluation protocol: sending RESET before taking any action on a level can restart the whole game from the first level." and "If it occurs, we treat the restart as terminal for evaluation purposes and discard all actions taken after the reset when computing the reported score. This situation did occur in one reported run, s5i5 with GPT-5.4."

Stall handling:
- Sec 2.2: "Before normal continuation and when progress appears to stall, the controller asks the coding agent to simplify and refactor its world model before continuing." The paper does not define the stall test. The response to a stall is a refactoring prompt, not a reset.

Undo: not mentioned anywhere. Checkpoints / restoring environment state: none. Planner utilities can start "from the current state, from the initial state of a level, or from an intermediate point in a previous attempt" (sec 2.3) but that is inside the model, not the environment.

Plan execution and prefix handling (sec 2.3): the plan executor "simulates the sequence in the world model and executes the same actions in the real game. After each non-terminal step, it compares the predicted settled ASCII frame with the observed settled ASCII frame. If the prediction diverges from the observation, the executor stops immediately and records mismatch artifacts for inspection. It also stops on LEVEL_COMPLETED or GAME_OVER. Thus, successful plan execution is not merely action replay: it is an online test of the current world model."

"Runtime recovery" (sec 2.5) is about the coding-agent process, not the game: "this mechanism restarts only the agent process and does not restart or modify the game server" ... "We allow at most ten such recoveries in a single game run."

Budgets:
- Sec 4: "We impose a per-level cap of 1500 environment actions. When the cap is exceeded on an unsolved level, the playthrough is stopped and the score reached so far is reported."
- Scorecard mode limits (sec 4): "the scorecard closes after 15 minutes of inactivity and after 24 hours in total."

Numbers bearing on wasted actions:
- The tables report per game "A_solved ... the number of environment actions spent on solved levels, and A_final ... the number of environment actions spent on the final unsolved level, if any." No counts of resets, deaths or attempts are reported.
- My sums from Tables 1-2 (INFERENCE, computed from the table cells): GPT-5.5: A_solved 17,557, A_final 8,174, so 31.8% of all environment actions went to a final level that was never solved (10 games; 5 of them with 1,325 to 1,586 actions on that level). GPT-5.4: A_solved 12,159, A_final 18,680, so 60.6% (17 games; 10 of them above 1,000). Example rows: GPT-5.5 dc22 0/6 levels with 1,586 actions; lf52 6/10 with 632 solved-level actions then 1,580 on the next level.
- Interrupted runs: 10 of 25 (GPT-5.4) and 7 of 25 (GPT-5.5).

When to give up / restart: no explicit discussion. The only stop rule is the 1,500-action per-level cap. Discussion sec 5 names the suspected failure: "One possible explanation is premature commitment to an incorrect or overly specific world model. Once the agent has built such a model, it may continue refining and planning within it instead of actively considering alternatives." "backtracking" appears once, as one of a list of search routines a future skill library could include.

Ablations: none. "A natural next step is an ablation study. Our preliminary experiments suggest that simpler versions of the agent may achieve comparable performance, but those experiments used vulnerable versions of the evaluation harness and are therefore not included".

Variance and selection bias (relevant to design):
- "Each game is evaluated as a single recorded playthrough."
- "Performance remains uneven and can vary substantially across runs." Examples: ft09 100.00% (GPT-5.4) vs 57.80% (GPT-5.5); wa30 49.77% vs 9.11%. "Overall, these cases should be read as evidence of run-to-run variability, rather than as precise per-game comparisons between the two models."
- Interrupted runs are not restarted: "Restarting after an interruption would conflict with the single-playthrough evaluation protocol. It would also introduce a selection bias. For the same game, runs in which the agent struggles and obtains a lower score usually take longer than runs in which it finds a good solution quickly. ... Restarting after such failures would therefore preferentially discard some low-scoring trajectories."
- Development exposure: "most of the development of this first version was performed using the public game ls20."
- Leak finding relevant to recovery mechanics: in local non-competition mode "an agent could start a second game client and use it as an unscored simulator for trying actions." Now rejected by the client-server protocol.

### B2. Paper 2 - Rodionov, "Do Coding Agents Need..." (v1.2 family: textual / executable / simplification / verification; GPT-5.4, GPT-5.5, follow-ups with GPT-5.6 Sol)

Controller state machine (sec 4.2): the controller "bases its decisions only on basic game-progress information: the current game status (NOT_FINISHED, GAME_OVER, or WIN); the current level and attempt; the number of actions taken on the current level; and whether Codex took any new actions during the preceding turn." Three branches:
- "Reset protocol. If the current attempt is in GAME_OVER, the controller first sends a death-analysis prompt asking the agent to explain the failure and update its model. It then optionally runs the simplification stage, issues RESET through the client, and sends a continuation prompt together with the reset observation. The controller, rather than the coding agent, is intended to own this reset transition."
- "Stuck protocol. If Codex returned without taking any new environment action, the controller optionally runs the simplification stage and then sends the normal continuation text plus an explicit reminder to make meaningful moves. If the agent returns a second consecutive time with the same environment-step count, the run stops. This branch is rare, but prevents an unproductive prompt loop from continuing indefinitely."
- Note the stuck test is "no new environment action in a turn", not "no new state".
- "Codex ... can occasionally discover and invoke RESET despite being instructed not to. Such deviations are handled as part of normal operation."

Reset semantics (sec 5.2): "The benchmark-provided RESET action can be used at any time to restart the current-level attempt and counts as an environment action. RESET restarts only the current level; it cannot return the agent to a completed level or restart the game from the beginning. In our setup, Codex is instructed not to issue RESET itself, although this instruction is not always followed; resets are ordinarily issued by the controller after GAME_OVER to begin a new attempt at the current level."
(INFERENCE: this conflicts on its face with paper 1's observation that in local mode a RESET sent before any action on a level restarts the whole game. Our harness should test this directly.)

Budgets and stopping (sec 5.4): "The playthrough stops when the game is solved, when no active level remains, when the agent makes no progress after the stuck reminder, or when the evaluation-specific limit of 1,500 environment actions has been reached on the current level. ARC-AGI-3 itself imposes no hard per-level action limit. Actions taken after GAME_OVER and before a reset are not free and remain part of the recorded action budget."
- "The 1,500-action limit may be restrictive for some games. In the human-baseline data for the 25 public games, the largest per-level baseline is 578 actions (level 6 of dc22), and nine levels across six games have baselines of at least 300 actions ... Future evaluations aimed at maximizing performance should use a higher per-level limit."
- Table 4 caption: the summed human baseline over all 183 public levels ("level_baseline_actions") is 17,135 actions. (INFERENCE: about 685 actions per game and about 94 per level on average.)

Prompt text on attempts (appendix 12.2, identical in all three main prompts):
- "If the game is in the `GAME_OVER` state, you should report it, and I will give you another attempt on the same level."
- "Remember that the game is deterministic: each attempt starts from exactly the same state, so the same actions will lead to exactly the same results."
- "Do not repeat the same mistakes. Think carefully, analyze previous failed attempts, and try a different approach in new attempts."
- "You are forbidden to call RESET by yourself."
- Also (12.2.3): "The game is deterministic at level start: all attempts for the same level begin from the same initial world state and produce the same initial observation. This is true even in partially visible worlds."
- Death-analysis prompt (12.3.5): "You have reached the `GAME_OVER` state in the current attempt. Use this outcome to improve your world model. Look at the last step and any available visual clues, including animations when they are useful. Consider whether the failure has a simple explanation that can generalize across levels."
- Stuck reminder (12.3.6): "You haven't made any moves in the game since the last time I told you to continue until you solve the current level or reach the GAME_OVER state. Please follow your prompt and make some meaningful moves. If you do not move, you will lose."
- Reset transition message (12.1): "The level has been reset. You have another attempt."

The closest thing to a recovery intervention: the "trouble prompt" (sec 8.1, follow-up v1.5; not part of the controlled ablation):
- "When the controller is handling a reset after GAME_OVER, it checks how many actions have been spent on the current level. If more than 50 additional actions have accumulated since the previous trouble intervention on that level, the controller sends an extra prompt immediately before resetting. The level-1 prompt emphasizes that the agent may be missing a simple visual cue; the later-level prompt asks what may be missing from the world model. Both ask the agent to analyze prior attempts, identify overlooked evidence, form a new hypothesis, and state a different plan for the next attempt."
- Prompt text (12.5.2): "You are having trouble with this level. This is a strong signal that you are probably missing something important, because every level should be solvable in a single attempt." ... "1. Analyze what you have already tried. Remember that every attempt at the same level starts from the same initial state, and the game is deterministic. Therefore, your previous attempts provide reliable evidence about what does and does not work. 2. Identify what you may have missed. 3. Formulate a new hypothesis about how to solve the level. 4. Explain what you are going to try in the next attempt and why."
- Result and its status: "Version 1.5 also accelerated the game client provided to the agent. We did not isolate this change experimentally. Consequently, in the gpt-5.5-xhigh setting, the increase from 74.78 RHAE for the main verification block to 82.01 for version 1.5 is a ceiling-oriented systems result, not a controlled estimate of the effect of either update."
- Sec 3 describes its origin: "we removed several ad hoc trouble-resolution mechanisms that were activated after an unsuccessful level attempt. As a secondary, ceiling-oriented experiment, we restore one such mechanism ... This follow-up changes more than one implementation detail and is therefore not treated as a controlled estimate of the prompt's effect."
- Note the trigger fires only on the GAME_OVER reset path. A level that never produces GAME_OVER never gets a trouble prompt.

Post-GAME_OVER guard (sec 8.2, v1.6): "a client-side rule that rejects all actions except RESET after GAME_OVER."

Undo: not mentioned. Checkpoints or environment state restore: none. State reconstruction "by simulating the known attempt actions up to the required prefix" (12.2.3) is inside the world model. Helper `run_main_planner.py --from-attempt N A S` "plans from the state obtained by reconstructing the initial state and simulating the first S steps of attempt A on level N" - again in the model.

Plan executor: present in the verification variant's workspace but "none of the agent-facing prompts mentions the plan executor or requires its use" (sec 3).

Numbers on wasted actions / failed attempts:
- Per-game tables report only score and unsolved levels; no reset, death or attempt counts in the paper. (Full run artifacts are on Zenodo, doi 10.5281/zenodo.21412274; not read.)
- Sec 7.6: "the verification agent spent 1,008 actions on level 1 of sk48, whose human baseline is 61 actions ... before eventually completing it." Also r11l under verification with gpt-5.5-xhigh "scores only 4.76 and leaves five levels unsolved" against 47.62, 100.00 and 85.93 for the same variant in the other three settings: "a transient, playthrough-specific tunnel-vision failure".
- Table 4: the three v1.6 blocks that complete all 183 levels use 7,758 to 10,111 total actions against the 17,135 human baseline.

Ablation isolating a recovery component: none. The ablation ladder is textual > executable > simplification > verification. The trouble prompt is explicitly not isolated.

Statements on experimental design that we should reuse:
- One run per game per cell: "Each of the 16 variant-model-effort combinations is evaluated once on each of the same 25 public games". Sec 7.6: "Averaging over 25 games reduces the influence of any one transient failure on the aggregate score, but a single playthrough per game cannot estimate run-to-run variability for that game." Sec 8.2: "with one block per cell and scores pressed against 100, the experiment cannot resolve such a small difference or estimate run-to-run variability."
- Bundled treatments: "the final comparison changes both the verification objective and the supporting workspace ... Its effect should therefore be interpreted as the effect of the complete verification treatment rather than as the isolated effect of a single instruction." Conclusion: "Its advantage therefore cannot be attributed to replay verification alone."
- Effect sizes of harness components are small next to model and effort: "The within-setting range between the best and worst variant is 5.08-14.48 RHAE points, whereas changing model or effort often produces a larger shift."
- No selective reruns (sec 5.5): "If any of the 25 playthroughs in a block suffers an irrecoverable technical failure, none of the playthroughs from that block enters the analysis; the complete 25-game block is run again from scratch." Reason: "Technical failure is not independent of performance ... Replacing only interrupted playthroughs could therefore preferentially discard difficult, potentially low-scoring trajectories and bias the results upward."
- Version control of the runtime (sec 4.2): "We treat the coding-agent runtime and its version as part of the experimental system: changes to the runtime's built-in prompting, context management, and tool-use behavior can change performance even when our controller and prompts are held fixed."
- Cost reporting: a "cost tokens" proxy, C = T_cached/60 + (T_input - T_cached)/6 + T_output. Verification uses "1.82-3.26 times as many cost tokens as the textual variant".
- Scope: "All 25 games evaluated here are public ... Results on these games are not a substitute for a sealed held-out evaluation."
- RHAE and grand totals can disagree: "Because RHAE depends on how actions are distributed across levels and games rather than only on their grand total, these results are compatible."

### B3. Paper 3 - OPINE-World (Claude Opus 4.8 high; 78.40 RHAE, 160/183 levels, 20/25 games)

Game over / reset / undo / replay of prefixes / checkpoints: not described as mechanisms. What exists:
- Algorithm 1 (appendix B.8) calls `Env.Reset()` once at initialisation and loops "while budget remains and the game is unfinished"; there is no branch for GAME_OVER.
- Appendix B.6: the loader "permits level-entry caches for reset and level-advance transitions, because those entry states are selected by the environment."
- A source excerpt (F.6.1) shows a generated engine dropping stale history when "State does not continue our last output (fresh level / planner branch / reset)". A trace excerpt (F.4, Listing 3) shows "Step 929 Fresh board", so resets happen in runs, but the paper never says who issues them or when.
- Undo: not mentioned.

Budgets and a stall stop rule (sec 4): evaluation "on the 25 public ARC-AGI-3 games with a 2000-action budget per game, or on a stall of more than 500 actions per level." This stall rule ends the run; it does not trigger recovery. A reduced-budget comparison (F.2) uses "a 400-action budget cutoff": Full 65.97 RHAE (141/183 levels, 13/25 games), ablation 52.96, epsilon-greedy 39.49.

Plan abort on mismatch (B.7): "During live execution, it compares each observed successor with the model prediction. A disagreement adds a counterexample to D and terminates the remaining plan." Sec 3.2.1: "A prediction mismatch stops the current plan and opens a short collection window for related counterexamples."

How stalls look in this paper (appendix F.4) - they are not "no new state" stalls:
- "It may continue rearranging familiar objects or repeating similar actions without discovering what prevents completion. This low-diversity exploration can be catastrophic because additional combinations of known actions do not reveal the missing interaction."
- Table 9 patterns: "Repeated or narrow search" (su15, g50t, dc22, sk48): "The actor repeats similar action sequences or block configurations while unresolved objects and interactions remain untested."; "Attention remains on familiar objects" (wa30, ar25, m0r0); "Untested or misread mechanic" (cn04, sc25, tn36); "Missing class-level record" (s5i5, ls20); "Incorrect carry-forward model" (sp80).
- cn04 ablation trace: still trying docking arrangements at step 972 with reward 0.
- The paper's remedy is directed exploration, not reset: "exploration can recover progress after the current model stops providing a route to completion."

A detail that breaks naive state hashing (appendix B.6): "Some games display a timer whose rendering changes after each action but whose quantization does not expose a usable state variable. A synthesized model may propose a mask for this display."

Numbers on wasted actions (appendix G.1, Table 18, baseline1 vs OPINE-World): baseline1 "exhausts its budget before completing these games": tn36 3,058 actions for 6/7 levels (human 317); m0r0 2,573 for 5/6 (human 1,107); re86 1,754 for 4/8; vc33 1,596 for 3/7; sc25 1,107 for 3/6; sp80 786 for 1/6. No reset or death counts.

Ablations: Bayesian belief state removed (minus 20.24 RHAE), epsilon-greedy, program structure, persistent NL. None is a recovery component.

Scoring definition (appendix G), the only formal RHAE statement in my set:
- Level contribution z = min{(b/a)^2, 1.15} for completed levels (b human, a agent action count), 0 for uncompleted levels; level weight = level index; game score S_g = 100 * min{ sum(l*z)/W, sum of completed level weights / W }; RHAE = mean over games.
- "Equation 34 assigns zero to incomplete levels while retaining their weight in W_g. The completed-weight cap prevents an early bonus from raising a game above the fraction of level weight completed."
- "The April 2026 update replaced the second-best human reference with the median human reference, raised the per-level cap from 1.00 to 1.15, and changed 15 builds." Two systems were excluded from comparison "because their game builds and scoring cap differ."

Statistics and repeats:
- Main comparison: one run per game per condition, paired across 25 games. Appendix C.2: "The tests follow the unit that generated the variation. Actions, levels, and synthesis rounds within a run are not treated as independent observations." "RQ1 pairs conditions within each game. Per-game RHAE uses the Wilcoxon signed-rank test. Level completion first reduces each game to its paired difference in completed levels and then applies a sign-flip randomization test. The paired cluster bootstrap resamples 25 games with replacement 100,000 times."
- Table 7: mean paired RHAE difference 20.24, "Standard deviation of paired differences 29.45", d_z 0.69, exact p 4.27e-4.
- Table 8 reports completion by level index; "Level positions are sequentially dependent within a game and are not treated as independent samples."
- Repeated runs (RQ3, 5 runs per condition, g50t levels 1-3, 1,000-action cap): actions to clear level 3 were 169, 277, 237, 176, 227 (full) and 626, 268, 756, 249, 289 (ablation). So the same condition on the same game ranges over a factor of 1.6 to 3.
- Reproducibility statement: "Because the agents are language models acting in a live environment, repeated runs vary in their action counts".
- Cost: "individual environments can consume up to 2 billion cumulative tokens."
- Related-work remark on return-to-frontier exploration (appendix D, about Rudakov et al. 2025, not in my list): it navigates "through recorded transitions to previously observed frontier states" and its "exploration cost consequently scales with the reachable visual state space and depends on frontier states remaining recoverable."

---

## C. Harness-evaluation papers

### C1. Paper 4 - "Rethinking the Evaluation of Harness Evolution for Agents"

About ARC-AGI-3? Partly. Sections 3-4 are Terminal-Bench 2.1; section 5.2 and appendix B run all 25 public ARC-AGI-3 games.

Core claims:
- Abstract: "prior work does not compare these approaches with simple task-level search baselines under matched feedback and inference budgets" and "prior work searches for harness configurations using verification signals ... drawn from the same benchmarks on which it reports the final performance of the evolved harnesses, violating the standard separation between training and test data."
- Held-out result (sec 4.4): "we split Terminal-Bench 2.1 into 45 training tasks, 10 validation tasks, and 34 held-out test tasks. We run Harness Evolution on the training set, select the best evolved harness based on validation performance, and evaluate it on the test set." Result: 63.2 to 63.2 on average (+1.2, 0.0, -1.4 by model). "The discrepancy suggests that the revisions discovered during evolution encode task-specific shortcuts rather than genuinely better harness design principles."
- Repeats: "To reduce variance from stochastic rollouts, all results are averaged over two independent runs." Table 8 caption: "the gap between automatic harness evolution and test-time scaling remains within run-to-run variance." Appendix A.1: "the gap between [pass@5 and pass@1] reflects the variance of the agent across independent attempts."
- Infrastructure failures count as failures: "Rollouts that terminate on an infrastructure exception, such as a sandbox crash or an API timeout, are scored as r=0 rather than excluded from the average."
- Self-generated feedback (sec 4.2): "Self-generated feedback is noisy, and sequential revision based on such feedback risks compounding early mistakes."
- What edits do (appendix A.2): "most edits memorize fixes rather than distilling strategies"; "the growing volume of persistent prompt text introduces context bloat that can offset the remaining gains."
- Abstract: "these findings highlight the need for matched-budget baselines and held-out evaluation to distinguish genuine harness improvements from benchmark-specific search and overfitting". Conclusion (sec 6): "current evidence for automatic harness evolution should be interpreted with caution".

ARC-AGI-3 part:
- Budget: "We set the budget to 2,000 actions" (per game); "in some cases the agent chooses to exit before exhausting this budget."
- Scoring as stated (appendix B.1): "The per-level score is min(1.15, (a_human/a_agent)^2), the squared ratio of human to agent actions, capped slightly above human performance. The per-game score is a level-weighted mean in which later levels receive greater weight. Only environment actions enter this count; internal reasoning and read-only inspection are free under the scoring protocol."
- Results (Table 4, RHAE): Claude Opus 4.8: Claude Code 44.3, VISTA* 43.3, VISTA 59.3, full harness 77.5. GPT-5.6 Terra: 4.6, 21.1, 25.9, 38.2. The number of runs behind Table 4 is not stated (the two-run averaging statement is attached to Terminal-Bench and EdgeBench only). INFERENCE: single run per game per column.
- On ARC-AGI-3 the method is tuned per game on that same game ("By task design, the goal is to make use of the rich environmental feedback and optimize performance on each individual task rather than to find a single harness that transfers"), so these numbers are not held-out evidence.
- Game over, reset, undo, replay: not discussed.
- Stall examples with numbers: tr87 with memory-only evolution: "This brute-force enumeration over 7 slots and 7 states consumes 1,320 actions on level 2 alone"; the agent's notes at that point "record the search rather than the rule". lp85 with GPT-5.6 Terra, memory-only: "exhausting the 2,000-action budget after spending 1,413 actions stuck on level 6". ls20: "Levels 5 and 6 introduce the moving entities, and this is precisely where every other run stalls."
- An agent-written no-change detector (appendix B.3, ls20): a hook `blocked_move` with `"when": {"action_in": ["ACTION1","ACTION2","ACTION3","ACTION4"], "frame_unchanged_steps_at_least": 1}`, `"block": false`, note "Frame unchanged: block likely hit a wall (did not move). Re-check tile map/position." It fired "three times over the run (at steps 201, 454, and 485)". Hooks overall: "Hooks are almost never written (0.2 and 0.0 per game), suggesting that agents do not spontaneously reach for event-triggered rules even when the interface is available".
- Context: "VISTA is a strong visual harness that reports perfect RHAE scores on all 25 public games using Claude Opus 5.0." VISTA includes "context-reset continuation for long sessions" and a "WORKING.md, a scratchpad reset at each level boundary".
- Meta-agent behaviour on EdgeBench games: "The meta agent helps by diagnosing failures, breaking redundant loops, and flagging overlooked details, and it is most effective on tasks requiring deep exploration along a single path; it sometimes neglects breadth, failing to prompt exploration of alternative directions."
- Reporting used for long-horizon games: best score so far over the budget window, and "It is important to compare not only final performance but also how quickly each method reaches a given score, which matters when the budget is the binding constraint."

### C2. Paper 5 - Self-Harness

About ARC-AGI-3? No. Terminal-Bench-2.0, SWE-bench Verified, AppWorld; models MiniMax M2.5, Qwen3.5-35B-A3B, GLM-5.

- Method: mine failure clusters from held-in traces, propose K minimal edits, accept only if no split regresses: "A candidate is accepted only if it improves at least one split without degrading the other".
- Repeats: "When evaluation is stochastic, we repeat candidate evaluation and apply the same rule to aggregate pass counts across repeats. This reduces the chance that a harness edit is promoted due to a single favorable run." Appendix A.2: "Each candidate evaluation uses two repeated attempts."
- Splits: "the held-out split is never shown to the proposer and is used only by the automatic promotion gate." INFERENCE: because the held-out split decides which edits are kept, it acts as a validation set; the reported held-out gains (all nine cells improve) are selected on that split and are not a clean test estimate. This is the pattern paper 4 criticises and paper 6 measures.
- Their own caveat: "Accepted edits may still reflect benchmark-specific failure patterns, and the protocol depends on the quality of verifier outcomes and trace records. Higher-stakes harness changes would require stronger acceptance gates than pass-rate non-regression alone."
- One-change-at-a-time principle: "each individual edit is constrained to modify only the surface needed to address its selected mechanism"; "A useful harness edit must specify the behavior it aims to change, the surface it modifies, the evidence that motivates it, and the evaluation result that justifies promotion."
- Recovery-like mechanisms appear only as discovered edits in terminal tasks: for MiniMax "stop unproductive tool-use loops before they become too long" (a limit on total tool messages); for Qwen "avoiding repeated failed commands, breaking cycles of endless exploration"; the seed harness has a "failure_recovery_instruction" ("If a tool call fails, inspect the error and adapt; do not blindly retry the same action.") and a runtime control policy with `max_recent_tool_errors` and `max_total_tool_messages`. None is isolated experimentally.

### C3. Paper 6 - HarnessDev

About ARC-AGI-3? No. SWE-bench Pro, Terminal-Bench 2.1, MLE-bench, EQ-Bench3, BrowseComp.

- Run-to-run noise (sec 4.3, "Stability and final-version selection"): "Of the 64 official switches, eight regress on both benchmarks, 16 show a single-benchmark regression, three show a cross-benchmark trade-off, seven produce no measurable change, 27 report gains that remain inside the repeated-run noise band, two have clear positive evidence beyond the noise band, and one contains no executable code change. The same commit can vary by about ±4.75 pair-score points, so small gains cannot be attributed to code changes from score alone."
- Feedback vs held-out: "Across 64 comparable switches, feedback and held-out scores move in the same direction only 34 times (53.1%), and only 2/9 declared versions are held-out optimal. Visible feedback is therefore useful for local search but unreliable for final selection: repeatedly optimizing a noisy score can favor a lucky run and amplify overfitting."
- Size of transfer: self-runtime feedback-pair gains +3.0 to +13.9 points shrink to held-out gains "+1.43 to +4.44 points and a mean gain of +3.11"; under a fixed other executor "only Opus improves and the other three regress".
- Replicates in creation: "Independent creations from the same model can still differ sharply. ... A single generated harness is therefore not representative, which motivates reporting avg@3."
- Model dependence: "changing only the runtime binding can substantially move H_0 and alter which harness changes are useful."
- Dead mechanisms: "Of 108 component instances in Code, 72 trigger in real runs, 18 have only partial evidence, and 18 are never observed; all unobserved instances concern state and memory." "only one implements periodic checkpointing. No checkpoint event appears in 26,679 recorded task trajectories." In evolution, "of 169 new functions or classes, 113 are reachable from the entry point, 31 are reachable only through dead code, and 25 have no caller."
- Small probes mislead: "one GPT-5.5 candidate passes all five Terminal probes but scores only 0.584 on the full set."
- Limitation they state: "Evolution currently has one trajectory per creator-runtime cell ... so the trajectories do not support uncertainty estimates or population-level comparisons."
- Protocol features worth copying: freeze the artifact before evaluation; "held-out means withheld from the creator's development loop"; evaluate every frozen version on the held-out set afterwards; report execution-token cost with every score; audit that added mechanisms actually fire.

---

## D. Does any of these documents study recovery, resets, backtracking or dead ends as a policy?

No. Among these eight documents none treats when-to-reset, undo, or return-to-furthest-state as an object of study, and none reports reset counts, death counts, dead-end loss or return cost. The plan's claim holds for this set, with these qualifications to state alongside it:

1. Paper 2 sec 8.1 (trouble prompt) is the nearest prior art: a harness-forced deliberation triggered by accumulated actions on a level (more than 50 since the last intervention), fired at the GAME_OVER reset. It was evaluated only bundled with an accelerated client and the authors say it is "not a controlled estimate". Paper 1's unspecified "when progress appears to stall" refactoring prompt is the same family.
2. Papers 1-2 fix a recovery policy by fiat rather than studying it: the controller owns RESET, issues it only after GAME_OVER, and the agent is told "You are forbidden to call RESET by yourself." That is a different default from our R0 (model decides).
3. Paper 3 has a stall rule (more than 500 actions on a level) but it only terminates the run.
4. Paper 4 shows an agent writing its own frame-unchanged hook once; papers 5-6 list loop-breaking and "lifecycle recovery" edits in non-game benchmarks. All plumbing or by-products, none isolated.
5. Undo (ACTION7 or otherwise) is not mentioned in any of the eight documents.
6. Paper 3 cites Rudakov et al. (2025), graph-based exploration that navigates back to recorded frontier states. That paper is outside my list and may be closer to the replay half of R2; it should be checked before the claim is made for the whole literature.

---

## E. Design implications (mine unless a quote is attached)

### E1. Budget regime
- The published harness studies use 1,500 actions per level (papers 1-2) or 2,000 per game (papers 3-4), with 400 per game as a reduced-budget check (paper 3). Paper 2 calls even 1,500 per level possibly "restrictive" and reports a largest per-level human baseline of 578 actions and a summed human baseline of 17,135 actions over 183 levels.
- INFERENCE: our 100-action cap per game is about one seventh of the average human baseline per game (about 685) and near the average for a single level (about 94). Later levels are out of reach in most games at human efficiency, so "stalled on later levels" is partly the cap. Under that cap a reset plus prefix replay almost never fits, R2's pricing rule will nearly always say "do not reset", and R1 and R2 may be indistinguishable. Recovery needs a budget in which recovery is feasible. Options: a per-level budget, a larger per-game budget, or reporting at several cut-offs taken from the same runs (paper 3 reports 400 and 2,000; paper 4 reports best-so-far over the budget window).

### E2. Check RESET semantics in our harness before anything else
- RESET counts as an action (papers 1 and 2). Actions after GAME_OVER and before RESET also count (paper 2 sec 5.4). Add the paper 2 v1.6 guard ("rejects all actions except RESET after GAME_OVER") in all three conditions, or count those actions as a separate measure.
- Paper 1: in local mode a RESET sent before any action on a level "can restart the whole game from the first level". Paper 2 says RESET "cannot ... restart the game from the beginning". Test which holds in our environment. A forced reset in R1 or R2 must never fire at action 0 of a level or immediately after another reset. Decide in advance how a full-game restart is scored (paper 1: terminal, later actions discarded).
- Determinism at level start is asserted by paper 2's prompts, which is what makes prefix replay valid. Still verify the state hash at each replayed step and abort on the first mismatch, as the plan executors in papers 1 and 3 do.

### E3. Price recovery in score units, not only in actions
- Level score is min((b/a)^2, 1.15), zero if the level is not completed, weighted by level index (paper 3 appendix G; paper 4 appendix B.1). Replay actions and the RESET itself are added to a.
- INFERENCE: a single mid-level reset is expensive in RHAE. Example: human baseline 30; a 20-action dead end, 1 reset and a 30-action solution give a = 51 and a level score of 0.35 instead of 1.0. Once a is about 3b the level is already worth at most 0.11, so further cost barely changes that level but still drains budget for later, more heavily weighted levels. The R2 rule should therefore compare expected score with and without reset, and the analysis should report both raw actions and RHAE.
- Paper 2: RHAE and total actions can move in opposite directions. Report both.

### E4. R1 trigger: expect low recall with "no new state hash and no memory change"
- The stalls documented in papers 2-4 are mostly not no-new-state stalls. They are long runs of new but unproductive states: combinatorial rearrangement (paper 3 cn04, still at step 972), brute-force enumeration (paper 4 tr87, 1,320 actions on one level), 1,008 actions on a 61-action level (paper 2 sk48). The agent's notes keep changing during these ("records the search rather than the rule"), so the memory-unchanged condition will also fail to fire.
- Timers and counters that change every step (paper 3 appendix B.6) make every state hash new unless that strip is masked. In those games R1 as specified never triggers.
- Prior triggers to compare against or add as a second criterion: actions on the level since the last intervention above 50 (paper 2); more than 500 actions on a level (paper 3, stop rule); frame unchanged after a move action (paper 4 hook, non-blocking); no environment action in a turn (paper 2 stuck protocol).
- Log every trigger evaluation in all conditions, including R0 in shadow mode, so trigger precision and recall can be reported even where it does not act.
- For the forced deliberation text, paper 2's trouble prompt is a ready template (analyse attempts, name what was missed, new hypothesis, state the next plan and why). Freeze and publish the text. Paper 4's caution applies: "sequential revision based on [self-generated] feedback risks compounding early mistakes."

### E5. Conditions
- R2 adds two things to R1 (the pricing rule and automatic prefix replay). By paper 2's own standard this is a "complete treatment", not a single factor: an R2-minus-R1 difference cannot be assigned to pricing or to replay. Either add an arm (R1 plus auto-replay, no pricing rule) or state the bundle explicitly.
- R0 differs from the convention in papers 1-2 (controller-owned reset only after GAME_OVER, model forbidden to reset). Consider that as a second reference arm, or at least report how often the model resets voluntarily in R0.
- Hold model, reasoning effort, runtime version, prompts and game builds fixed and record them (paper 2 sec 4.2; paper 3 appendix G on build hashes and the April 2026 scoring change). Paper 6 shows harness effects change sign with the executing model, so results for Opus 5.5 should not be generalised to other models.

### E6. Measures
- Add what papers 1-2 report: actions on solved levels versus actions on the final unsolved level (A_solved, A_final), unsolved games and levels, run status, cost tokens. A_final is a level-granularity version of our dead-end loss and makes our numbers comparable with theirs (31.8% and 60.6% of all actions in paper 1, my sums).
- Add: GAME_OVER count versus voluntary reset count versus forced reset count; attempts per level; actions taken after GAME_OVER; replay aborts on hash mismatch; tokens spent in forced deliberations.
- Completion by level index (paper 3 Table 8), since later levels depend on earlier ones.
- "Progress event" and "furthest state reached" need operational definitions. The only environment-provided progress signal in these papers is level completion (paper 3: "sparse completion rewards"). Within a level, "furthest" is not defined by the environment; define return cost against a specific target state hash.

### E7. Repeats and statistics
- One run per game cannot separate a recovery effect from noise: paper 2 ("a single playthrough per game cannot estimate run-to-run variability for that game"), paper 1 (ft09 100 vs 57.8), paper 3 (same condition, same game: 249 to 756 actions over five runs), paper 6 (same commit ±4.75 points; 27 of 64 apparent gains inside the noise band; 2 beyond it).
- Pair conditions within game; treat the game (or run) as the unit, never the action or the level (paper 3 appendix C.2). Use paired tests on per-game differences (Wilcoxon signed-rank, sign-flip randomisation for levels completed, paired cluster bootstrap over games).
- INFERENCE on scale: paper 3 saw a standard deviation of 29.45 RHAE points in paired per-game differences. With that spread, 25 game pairs give 80% power only for mean differences of roughly 17 points; a 10-point effect needs roughly 70 pairs. Harness-component effects in paper 2 were 5 to 14 points. So plan for at least 3 to 5 runs per game per condition and estimate the noise band first by repeating R0 against itself.
- Papers 4 and 5 used two repeats and paper 6 three for creation; the ARC Prize policy uses "A single run ... we do not average scores across runs", so our repeated-run spread has no official counterpart.
- No selective reruns. Pre-register what happens to interrupted runs (papers 1 and 2: struggling runs last longer and are interrupted more often, so replacing them biases scores upward). Paper 4 scores infrastructure failures as failures.

### E8. Overfitting the recovery rule
- The stall threshold and pricing rule are harness parameters. Papers 4 and 6 show tuned harness changes mostly fail to transfer (0.0 average held-out gain; 53.1% directional agreement between feedback and held-out). Fix the parameters on a small set of development games, freeze, and report the remaining games separately. Paper 1 names its development game (ls20); do the same.
- Paper 5's acceptance gate is a useful minimum for adopting any rule change (no regression on either split, with repeats), with the caveat that a split used for acceptance is no longer a test set.
- Check that the mechanism fires: paper 6 found checkpointing code that never executed in 26,679 trajectories. Report how often R1 triggers and R2 replays actually ran per game.
- All 25 public games are public; ARC Prize expects public and semi-private ARC-AGI-3 scores to agree only "within ±15 percentage points", and paper 2 warns of contamination for models released after the games.
