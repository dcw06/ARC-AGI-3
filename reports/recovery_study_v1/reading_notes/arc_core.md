# Reading notes: five core ARC-AGI-3 documents, read for the recovery study (R0 / R1 / R2)

Date of reading: 2026-11-14. Reader: subagent. Reading task only; no study code written.

Marking used throughout:
- **[DOC]** = the document says this (quoted or closely paraphrased, with section).
- **[INFER]** = my inference or arithmetic from what the documents say.
- **[SUPP]** = from an official ARC-AGI-3 docs page that is NOT one of the five listed documents. I fetched these on my own initiative because the five documents are silent or inconsistent on RESET semantics and undo. Treat as a separate source.

---

## 0. What was read, and how much

| # | arXiv id | Title found (matches the list?) | Version | How much read |
|---|---|---|---|---|
| 1 | 2603.24621 | "ARC-AGI-3: A New Challenge for Frontier Agentic Intelligence" (match) | v2, 17 Apr 2026 | All 960 lines of the text copy, including references. Figures are not in the text copy (captions only). |
| 2 | 2607.28287 | "Tycho: Active Abstraction with Programmatic World Models for ARC-AGI-3" (match) | v1, 30 Jul 2026 | Main text (lines 1-2016) in full; appendices A-E (2724-3891) in full. Reference list (2017-2723) keyword-scanned only. |
| 3 | 2610.02200 | "VISTA: A Visual Harness for Reasoning in an Interactive World" (match) | v1, 1 Oct 2026 | Main text and appendices A-B in full. Reference list read in part. |
| 4 | 2611.12324 | "How Many Exposures Does a World Model Need? Learning Unseen Game Mechanics at Test Time" (match) | v1, 9 Nov 2026 | Main text and appendices A-J in full (two large tables read in condensed form). Reference list read in part. |
| 5 | 2610.30499 | "Can LLMs Improve Their Own Harness? A Controlled Study on ARC-AGI-3" (match; authors Lehmann and Vahdati) | v1, 21 Oct 2026 | Main text and appendices A-G in full. Reference list read in part. |

No title mismatches. All four fetches worked first time (HTML versions). Text copies:
- library/arc3_report/text.txt
- library/tycho/text.txt
- library/vista/text.txt
- library/exposures/text.txt
- library/harness_selfimprove/text.txt

Supplementary official docs pages (not in the list; plain public URLs, no personal or project details sent):
- docs.arcprize.org/methodology -> library/arc3_docs_methodology/text.txt (read in full)
- docs.arcprize.org/actions -> library/arc3_docs_actions/text.txt (read in full)
- docs.arcprize.org/api-reference/commands/start-or-reset-game-instance.md -> library/arc3_docs_reset/text.txt (read in full)
- docs.arcprize.org/scorecards.md -> library/arc3_docs_scorecards/text.txt (read in full)
- docs.arcprize.org/api-reference/commands/execute-simple-action-7.md -> library/arc3_docs_undo/text.txt (description only)
- docs.arcprize.org/llms.txt (index, used only to find the page addresses)
- Two guessed addresses returned 404 (a "game-state" page and a misspelled reset page). Not read: game-schema, recordings, full-play-test, toolkit pages, the scorer source code.

Not verified anywhere in this reading: the actual scorer code. Several points below (cap form, 5x cut-off, whether undo is counted) should be confirmed against the toolkit scorer.

---

## A. Benchmark facts

### A1. RHAE formula

**Technical report, section 4.1 [DOC]:**
- "This scoring function is called RHAE (Relative Human Action Efficiency), pronounced 'Ray'."
- "For each level that the test taker completes, count the number of actions that it took."
- "If the upper-median best human completed a level in only 10 actions, but the AI agent took 100 to complete it, then the AI agent scores (10/100)^2 for that level, which gets reported as 1%. Note that level scoring is calculated using the square of efficiency."
- "Each level is scored in isolation. Each individual level will get a score between 0% (very inefficient) and 115% (surpasses human level efficiency). The environment score will be a weighted-average of level score across all levels of that environment."
- "The total score will be the sum of individual environment scores divided by the total number of environments. This will be a score between 0% and 100%."
- Eq. (1): S_{l,e} = min(1.15, h_{l,e} / a_{l,e})^2, with a = "the number of actions taken by the AI agent" and h = "the human baseline (defined as the upper-median best human action count)".
- Eq. (2): "The Environment Score E_e is the linearly weighted average of the level scores, subject to a per-environment cap. For an environment with n levels (where n=5), the weight for level l is w_l = l. Let k be the number of levels completed by the test taker (where levels are sequential, so completing k levels means completing levels 1 through k, and S_{l,e}=0 for uncompleted levels)." E_e = min( sum_{l<=k} w_l / sum_{l<=n} w_l , sum_{l<=n} w_l S_{l,e} / sum_{l<=n} w_l ).
- "The first term is the environment cap, which limits the maximum environment score to the weighted fraction of levels completed."
- Eq. (3): "The Total Benchmark Score T is the mean of all environment scores across the dataset D".
- "This formulation is inspired by the robotics navigation Success weighted by Path Length (SPL) metric".

**Technical report, section 4.2 [DOC]:**
- "Cap the maximum per-level score ... we cap the per-level efficiency an AI can receive at 1.15x human baseline." "we cap the maximum score for a level at 1.15x the human baseline."
- "Power law scoring ... that value is then squared before contributing to the final score. This adjustment increases the penalty for highly inefficient solutions while preserving partial credit. Under a linear formulation, substantial inefficiencies can still yield disproportionately high scores (e.g., 2x the human action count yields 50% credit)".
- "Weighted levels ... we therefore use a simple linearly weighted average across the five levels of an environment." Level 1 = 1/15 ... Level 5 = 5/15.
- "Per-environment cap ... Completing all 5 levels: environment cap is 15/15=100%. Completing 4 out of 5 levels: environment cap is 10/15 = 66.7%. Completing 3 out of 5 levels: environment cap is 6/15=40%."
- "Per-level aggregation strips away noise from uneven level lengths. For instance, we've observed that vc33's level 6 requires 10x actions of its level 1 (50 vs < 5)."
- "by reinforcing efficiency per level, we won't design environments (or encourage AI) to waste actions on levels because they're still 'under budget' for a given environment."

**Inconsistencies inside and between documents [DOC + INFER]:**
1. Where the 1.15 cap sits. Technical report Eq. (1) squares the capped ratio (maximum 1.15^2 = 1.3225), but its own prose says "between 0% ... and 115%". The other papers put the cap on the squared value:
   - Tycho section 3.1: e_l = min{115, 100 (h_l/a_l)^2} if completed, else 0.
   - VISTA appendix A.3, Eq. (1): S = min(1.15, (h/a)^2), "using the official ARC-AGI-3 scorer".
   - Lehmann and Vahdati appendix A: s_l = min{100 (b_l/a_l)^2, 115}.
   - [SUPP] methodology page: "level_score = (human_baseline_actions / ai_actions) ^ 2" and "The maximum score per level is capped at 1.15x human baseline ... it can receive at most 1.15."
   [INFER] Three independent papers and the docs agree on "at most 115% per level"; the technical report's Eq. (1) is probably a typesetting slip. Under the 115% form the cap is reached when a <= h / sqrt(1.15) = 0.9325 h.
2. Number of levels. Eq. (2) says "n=5" and section 4.2 says "the five levels", but section 3.4 says "Levels: Environments are developed with a level-based structure, with at least six levels per environment." Tycho reports "25 ARC-AGI-3 games (183 levels in total)" (7.3 per game on average; ls20 has 7, sk48 has 8, tr87 has 6). [INFER] The weight is w_l = l over the game's actual n levels; for a 7-level game level 7 carries 7/28 = 25% and level 1 carries 3.6%.
3. "Upper-median" versus "median". Section 4.1/4.2 define the baseline as upper-median; section 4.3 says the budget is "five times the human-baseline median action count per level".

### A2. Does RESET count as an action? How is GAME_OVER scored?

- **Technical report [DOC]:** does not say whether RESET is counted. It never mentions GAME_OVER. Its definition (section 2.3.2): "An action is defined as a discrete interaction with the environment, i.e., a turn where the agent submits a command, move, or input that affects the environment state. Internal operations that do not alter the environment, such as tool calls, reasoning steps, or retries within the model itself, are not counted as actions."
- **Tycho, Definition 2 (section 3.1) [DOC]:** "An ordinary action advances the current level machine and increments a_l. A level_complete output closes the current level after preserving its terminal evidence, then advances without action cost to s_0^{l+1} or ends the game after the last level. A game_over output closes only the current attempt. The protocol control RESET is available independently of alpha_theta(s), the set of ordinary game actions returned with the current decision frame. It costs one in-play action and starts a fresh attempt at s_0^l. The initialization RESET that creates a play is unscored."
- **Tycho, appendix A (actor prompt) [DOC]:** "Tool calls are free for scoring; each take_action, including RESET, spends one scored environment action and ends the turn."
- **Tycho, appendix E (ls20 audit, official score) [DOC]:** "478 scored environment actions: 17, 103, 41, 43, 75, 111, and 88 by level, including 3 RESET commands"; "This set excludes 74 transitions from three RESET-abandoned attempts and the RESET commands themselves, although all three count in the 478-action benchmark total."
- **Exposures paper, appendix I [DOC]:** Algorithm 1 comment: "a reset after a game over counts as an action"; I.2: "every measure is read from its first 1,000 actions, including resets."
- **Lehmann and Vahdati [DOC]:** speak of "charged actions" (appendix A) without itemising RESET.
- **[SUPP] methodology page:** "Each turn where the agent submits a command, move, or input that affects the game state counts as an action." (RESET not named.) Scorecards page lists per-environment "action counts, completed levels, and reset counts".
- **[INFER]** RESET counting as one action is well supported by Tycho (whose totals were checked against official scorecards) and by the exposures paper, but it is not a statement of the technical report. GAME_OVER has no separate score term: only completed levels score, uncompleted levels get 0, and all actions spent in failed attempts stay in that level's a_l (Tycho Definition 2). So the cost of a death is the actions already spent on the level, plus one for the RESET, plus the actions to get back.

### A3. What RESET restores

- **Technical report, section 5.1 [DOC]** (about human testers): "Participants were limited to a single attempt per environment and could not revisit previously completed levels. However, they were allowed to reset the current level at any time. In some cases, participants reset levels after reaching a solution in order to improve efficiency, though this typically increased total interaction time." Section 3.5.2: "Graph construction begins from the reset state of a selected level."
- **Tycho Definition 2 [DOC]:** RESET "starts a fresh attempt at s_0^l" (current level's initial state); "A game_over output closes only the current attempt."
- **VISTA appendix A.4 [DOC]:** "An attempt starts when the level is entered or RESET is issued, and ends at GAME_OVER, WIN, or TERMINAL."
- **[SUPP] Reset command page (official REST docs):** "Provide an existing guid -> reset that session. - If at least one ACTION command has been issued since the last level transition, only the **current level** is restarted. - If no ACTIONs have been issued, the entire game resets. Two consecutive RESETs therefore guarantee a completely fresh game." The frame response carries "full_reset: Whether the RESET created a new game rather than resetting the current level", plus `state` (NOT_PLAYED, NOT_FINISHED, WIN, GAME_OVER), `levels_completed`, `win_levels`, `available_actions`.
- **[SUPP] Actions page:** "When a game reaches a game-over state, the only valid action is RESET. Sending any other action (e.g., ACTION1 through ACTION7) to a game in this state returns a 400 Bad Request error." "issue a RESET to start a new game."
- **[INFER]** A normal RESET (after at least one action in the level) restarts only the current level and keeps completed levels. A RESET at the very start of a level, or a second RESET in a row, wipes the whole game. The Actions page wording "start a new game" after GAME_OVER conflicts in tone with the level-reset rule; Tycho's reading (game over closes only the attempt) is the one validated against scorecards. Not found in any document: whether action counts for already-completed levels are kept after a full game reset, and how a second "run" is scored ([SUPP] scorecards page: "score: Average of the best score for each environment").
- **[DOC] In-level soft resets exist too.** Tycho appendix E, from the ls20 engine source: "When a command starts with the counter at zero, movement and contact handling still occur before possible life loss; respawn restores the avatar, carried shape and color, counter, consumed rings, chambers, and moving-operator positions and directions; the last life ends the game". Technical report Figure 3 caption: "Notice the three repeating states - an artifact of the three-life mechanic of the level."

### A4. Undo and the action list

- **Technical report, section 2.3.2 [DOC]:** "Each environment offers a different action space, which is a subset of: Five key actions, plus an Undo action (reverting to the previous state); One action to select (e.g. click on) a cell from the 64x64 grid by specifying its coordinates".
- **Lehmann and Vahdati, section 4.1 [DOC]:** "Depending on the game, the interface offers directional inputs, a game-specific input, coordinate clicks, or undo."
- **VISTA appendix A.4 [DOC]:** "ARC-AGI-3: RESET, ACTION1..7, where ACTION6 is a click at (x, y)".
- **Exposures paper, section 3 [DOC]:** "an action is one of up to five keys or a click on a cell" (undo not mentioned).
- **Tycho, Remark 1 [DOC]:** "The public games inspected here did not vary the mask within a game, but the interface also supports dynamic masks."
- **[SUPP] Actions page:** RESET "Initializes or restarts the game or level state"; ACTION1-4 "semantically mapped to" up/down/left/right; ACTION5 "interact, select, rotate, attach/detach, execute, etc."; ACTION6 "Complex action requiring x,y coordinates (0-63 range)"; ACTION7 "Simple undo action". ACTION7 page: "ACTION7 will always be an undo action for games that support it." "Each game exposes only the subset currently available through the response's available_actions field." "Action 6 does not provide explicit X/Y coordinates for active areas."
- **Not found in any of the five documents:** which games offer ACTION7; whether undo is counted as a scored action; whether undo restores step counters or lives; whether undo works after GAME_OVER (the [SUPP] Actions page implies not: only RESET is valid then). None of the four harness papers uses or discusses undo. [INFER] By the report's own definition (an input that affects the environment state) undo would count as one action; unverified.

### A5. Human baseline

- **Technical report, section 4.2 [DOC]:** "Exactly 10 members of the public are tested on each environment." "We defined the human baseline as the upper-median best human by number of actions used. For a given level, we rank all participants who completed that level by action count and select the upper-median performer (e.g., the 3rd-place finisher among 4 or 5 completions)."
- **Section 5 [DOC]:** "Only environments that could be fully solved by at least two human participants (independently) were considered". Section 5.1: 90-minute sessions, "soft time limit of 20 minutes ... hard cutoff of 30 minutes". Section 5.3.2: three reference points: "Optimal playthrough", "Best first-run playthrough", "Human baseline: Upper-median best first-run human playthrough. This is what we use as the human baseline in the official score computation." "The difference between the 'optimal playthrough' and the 'best first-run playthrough' captures the amount of actions that need to be expended for initial exploration and mechanics learning."
- **Published or exposed? [DOC]** The technical report does not say. Lehmann and Vahdati call them "hidden human baselines" (section 4.1) and "hidden human action baselines b_l" (appendix A). Yet VISTA Table 2 prints per-game sums ("human actions are the sum of the per-level human baselines"; total 17,135 for the 25 games) and Tycho quotes individual level baselines ("a 146-action human baseline" for tr87 level 6; "the 132-action baseline" for ka59 level 6) and uses "official human baselines". [INFER] Per-level baselines are obtainable (probably from official scorecards or the toolkit), but none of the five documents says where. "Hidden" most likely means hidden from the playing agent.
- **Not stated [INFER]:** whether a human's per-level count includes actions made before that human reset the level. This matters for how fair the baseline is to an agent that resets.
- **Released human data [DOC]:** Tycho: "The release contains 340 usable first-run replays" (10-54 per game). Exposures paper: "279 human recordings"; "90k to 123k transitions after removing resets" (so human recordings contain resets).

Per-game summed human baselines from VISTA Table 2 [DOC]: ar25 748, bp35 651, cd82 171, cn04 789, dc22 1,228, ft09 208, g50t 879, ka59 730, lf52 1,339, lp85 388, ls20 776, m0r0 1,107, r11l 233, re86 1,255, s5i5 638, sb26 213, sc25 350, sk48 1,070, sp80 518, su15 361, tn36 317, tr87 414, tu93 462, vc33 447, wa30 1,843. Total 17,135. [INFER] minimum 171, median 638, maximum 1,843.

### A6. Official action budget

- **Technical report, section 4.3 [DOC]:** "Given the computational cost of evaluating high-reasoning frontier models across the full ARC-AGI-3 evaluation set (tens of thousands of dollars in API costs) we impose an action budget of five times the human-baseline median action count per level. That is, for a level with a human median of n actions to completion, the agent is terminated after 5n actions. This constraint may yield marginally lower reported scores than would be obtained under the environment's intrinsic action limit. However, given the power-law decay of the scoring function, the resulting differential is negligible."
- **Lehmann and Vahdati, appendix A [DOC]:** "a completed level within the 5 b_l action budget receives s_l = min{100 (b_l/a_l)^2, 115} and other levels receive zero."
- **VISTA, appendix A.2 [DOC]:** "The official implementation uses a per-section action limit of 5x the human baseline and a 12-hour runtime limit. We find that many runs terminate upon reaching these limits, leaving the games unfinished. We therefore increase the limits to 2,000 total actions and 48 hours per game, improving the RHAE score to 51.66. We do not observe substantial additional benefits from further increasing these limits."
- **[INFER]** At a = 5h a completed level earns (1/5)^2 = 4%. The 5x rule is a rule of the official leaderboard runs (the agent is stopped); VISTA and PRO-LONG ran with 2,000 actions per game instead, so the scorer itself evidently accepts longer runs. Whether the scorer zeroes a level finished beyond 5h (as Lehmann and Vahdati define it) is unverified. The phrase "environment's intrinsic action limit" suggests each environment also has its own limit; no detail given.
- Official system prompt for leaderboard runs (section 4.3.1) [DOC]: "You are playing a game. Your goal is to win. Reply with the exact action you want to take. The final action in your reply will be executed next turn. Your entire reply will be carried to the next turn."

### A7. Other benchmark facts relevant to recovery

- Section 2.2 [DOC]: resources include "risk (in embodied or game-based scenarios, every action carries a cost: potential 'death,' loss of progress, or wasted energy)"; action efficiency "accounts for data efficiency and risk efficiency: Fewer actions naturally translate to lower exposure to environmental hazards."
- Section 2.3 [DOC]: "The environment's state does not change asynchronously from the agent's actions." Frames may arrive as "a frame or frame sequence" (animations).
- Section 3.4 [DOC]: "Tutorial level: The first level in an environment functions as a tutorial level and is intentionally easy"; "Difficulty through composition: ... Later levels are therefore expected to require the accumulation and integration of concepts learned earlier in the environment."; "Multiple mechanics: Each environment contains multiple mechanics."
- Section 3.5.1 [DOC]: "developer-provided recording-based playback verifies reproducibility. Known-good recordings are replayed under both win and loss conditions, confirming that the engine can serialize and faithfully re-execute action traces." Section 3.5.2: "Invalid actions are recorded as transitions that do not change the state."; node identity "is hash-based".
- Section 4.3.1 [DOC]: "we are releasing an open-source 'harness' which scores 100% on all public environments, using human replay."
- Table 1 [DOC]: 25 public demo, 55 semi-private, 55 fully private environments. "the public set is materially easier than the private set".

---

## B. How each harness or study handles recovery

### B1. Tycho (2607.28287)

**Protocol and evidence [DOC]:**
- Outer protocol (section 3.1): "A level machine describes the mechanics within one attempt, but ARC-AGI-3 also governs resets, repeated attempts, level advancement, and action accounting. We represent these benchmark-wide rules as a small outer protocol". "A terminal frame documents how an attempt ended, whereas a reset or level advancement creates the next state from which an action can be chosen."
- Typed history (Definition 3): "Each grid is tagged by its role: decision, transient, completion terminal, fatal terminal, reset initialization, or next-level initialization. A history is faithful when every recorded action is attached to the decision frame from which it was chosen, never to a transient or terminal frame."
- Section 4.1: wmlib gives "prior decision frames and ordinary transitions, archived reset attempts, completed-level terminal events, fatal events, and animation events. Terminal, fatal, and animation frames remain separate from ordinary transitions because the actor never chooses an action from them." "Resets archive abandoned attempts rather than erasing them."
- Appendix C.1: "Completed-level and fatal boundaries are represented separately by terminal_events() and death_events()".

**Who decides to reset [DOC]:** the model (actor). Appendix A: "The action field of take_action was constrained each turn to RESET and the controls declared by the current frame." Prompt: "Prefer RESET when the current attempt is unwinnable or clearly more expensive than restarting." Appendix E: "RESET is selected by the actor, handled by the outer harness, and not modeled by transition". The builder subagent can recommend RESET: in the audited ls20 run "35 recommended a directional movement action and three recommended RESET. In all 38 cases the subsequently submitted action matched that recommendation."

**Harness-forced intervention at a death [DOC]:** only in the Trigger policy, and it forces model repair, not a reset decision: "It also invokes the builder at new-level and fatal-reset boundaries" (section 4.4); "New levels after the first and fatal resets invoke the builder independently of this gate" (appendix C.2).

**Undo [DOC]:** not mentioned anywhere. Section 7: "The framework supplies conventions for RESET and numbered actions."

**Replay of known prefixes [DOC]:** none in the environment. "Replay" in Tycho means (a) running the learned program over recorded history to verify it ("Verification replays the most recent attempt for each level from its first frame") and (b) "deterministic competition replay" of the finished trace through the official API for scoring. Plans are released one action at a time with a hash guard: "Tycho surfaces the next action only while the model is unchanged, the observed frame matches the stored hash, and the action remains available." "Tycho still invokes a language model around every committed action. A guarded executor could instead carry out several verified actions and interrupt on a prediction mismatch". Future work: "guarded reuse of verified plans". About others: PRO-LONG can "execute up to 20 queued actions between model invocations"; the Schema harness uses "guarded action queues invalidated by prediction mismatches".

**Checkpoints [DOC]:** none for game state. "durable checkpointing for resumption" (section 7) is about interrupted inference. Section 6 lists "incorrect reset semantics" among harness faults found during development.

**Stall or loop detection [DOC]:** none described. Runs end by limits instead (Table 2 and Table 10): LM-call budget 3,500 per game; inference budget $750 per game (policy selection) or $1,500 (selected-policy runs, "not reached"); 40 tool steps per turn; and a "level-action" limit whose value the paper does not give. Table 10 (wins / level limit / LM limit / cost limit): no world model 19/3/0/3; single 19/2/0/4; orchestrator 21/1/1/2; trigger 18/2/5/0; GPT-5.6 25/0/0/0; Opus 5 25/0/0/0. "Every unsuccessful matched-study game hits an imposed limit".

**Giving up [DOC]:** only the one-line RESET preference above, plus "do not treat failure to find a plan as proof that the level is impossible."

**Numbers [DOC]:**
- Opus 4.8 matched study, mean game RHAE: no world model 79.07; single 85.36; orchestrator 88.49; trigger 83.07. Games completed 19/19/21/18; levels 157/162/166/162 of 183.
- Actions: orchestrator 10,354 ("20.3% fewer than direct reasoning"); trigger 9,442; single 11,576. On the 157 levels both completed, orchestrator 7,187 versus direct 8,857.
- Unfinished tails (actions after the last completed level): "It spends 1,361 actions after the last completed level, versus 4,140 for direct reasoning, 2,403 for single, and 1,842 for orchestrator." "Trigger's shorter unfinished tails are budget-censored." "Raw totals are not matched efficiency comparisons because the policies reach different levels."
- [INFER] Share of all actions spent after the last completed level: direct about 32% (4,140 of about 12,997), single 21%, orchestrator 18%, trigger 14%.
- Game-over events: Table 7 (pre-action, evaluable prefixes) GO n = 12 (single), 6 (orchestrator), 4 (trigger), with recall 0.0 for all: "None predicts the small set of observed deaths in the evaluable prefixes." Table 12 (end of run) GO n = 12, 6, 20 (trigger), 10 (GPT-5.6), 6 (Opus 5).
- ls20 audit, GPT-5.6 Sol: 478 actions, 7/7 levels, RHAE 100, "including 3 RESET commands"; 74 transitions in the three abandoned attempts. [INFER] 77 of 478 actions (16%) went to abandoned attempts and resets, and the game still scored 100 because every level stayed under its baseline (ls20 baselines sum to 776).
- sk48, Opus 4.8 orchestrator: "Thirteen builder calls and 314 official scored actions completed no level, whereas the trigger policy completed all eight levels of the same game". Cause: the objective was never identified; "an accurate transition model can amplify a wrong or ungrounded objective."
- Score saturation: "114/157 direct, 133/162 single, 138/166 orchestrator, and 124/162 trigger completions already saturate the per-level cap. The corresponding counts are 167/183 for GPT-5.6 and 171/183 for Opus 5."
- Selected policy: GPT-5.6 Sol 100.00 RHAE, 183 levels, 7,766 actions; Opus 5 100.00 RHAE, 183 levels, 6,641 actions.

### B2. VISTA (2610.02200)

- **[DOC] Design:** image observations, "lossless visual memory" ("stores every frame returned by the environment, including intermediate animation frames"), `inspect` and `read_pixels` tools, two notes. "The harness is purely mechanical and does not involve any trained model". "A single agent interacts with each game throughout the run."
- **[DOC] Reset and game over:** RESET is simply one of the `play` actions. `history(view="attempts")`: "one summary for each attempt in the current level. An attempt starts when the level is entered or RESET is issued, and ends at GAME_OVER, WIN, or TERMINAL." Notes: "GUIDE.md stores reusable knowledge about the game across levels and sessions. WORKING.md stores temporary state and plans for the current level. It is retained across RESETs and context restarts, cleared when the level advances". Figure 10a: "after the board resets, the model retrieves four frames from the preceding 22 turns in a single inspect call to reconstruct the map."
- **[DOC] Undo:** ACTION7 is in the listed action range; never discussed.
- **[DOC] Replay or queued actions:** none; "a new play call is accepted only after the result of the previous action has been returned to the agent."
- **[DOC] Checkpoints:** `save_compact_checkpoint` saves notes before context compaction; it is not a game-state checkpoint.
- **[DOC] Stall detection, give-up rule:** none. The whole prompt (appendix A.5) is: "Complete the game with as few game actions as possible. Build and use a compact, revisable model of the game and its current state. Update it as new evidence changes what is supported. Before each `play`, briefly state what you expect to see. Afterward, briefly state all visible changes, expected or not. Keep concise, durable, revisable game understanding in `GUIDE.md`; use `WORKING.md` as a scratchpad when useful."
- **[DOC] Budgets:** "We limit the number of actions per game to 2,000 for Claude Opus 5.0 and GPT-5.6 Sol, and to 3,000 for GLM-5.3 Flash 320B"; 48 hours per game.
- **[DOC] Numbers:** Opus 5.0 xhigh 100.00 RHAE, 7,302 actions versus 17,135 human ("57.4% fewer"). GPT-5.6 Sol max 99.00, 9,126 actions; ls20 was the one imperfect game (75.03, 1,135 actions versus 776 human). Per-game Opus 5.0 actions: ar25 256, bp35 521, cd82 112, cn04 225, dc22 547, ft09 75, g50t 338, ka59 303, lf52 1,008, lp85 104, ls20 458, m0r0 219, r11l 75, re86 628, s5i5 254, sb26 125, sc25 153, sk48 413, sp80 119, su15 99, tn36 143, tr87 140, tu93 193, vc33 182, wa30 612. No counts of resets or deaths.
- **[DOC] Ablation ladder (GPT-5.6 Sol):** official 13.33 -> (i) PNG images 47.32 -> (ii) limits raised from 5x per level and 12 h to 2,000 actions and 48 h: 51.66 -> (iii) continuous conversation with compaction 65.82 -> (iv) notes 70.05 -> (v) visual memory and inspection 94.10 -> (vi) pixel readout 99.00.
- [INFER] With Opus 5.0, only three games were finished in 100 actions or fewer (ft09 75, r11l 75, su15 99); the median game took 219 actions.

### B3. "How Many Exposures..." (2611.12324): WARC and WARC-Agent

- Mainly a study of a 35M-parameter neural world model with test-time training; no LLM. Recovery is not a topic.
- **[DOC] Game over and reset in the agent (appendix I, Algorithm 1):** the loop runs "for t=1,...,1000 do  > a reset after a game over counts as an action". No voluntary resets. "A transition is valid unless it crosses a reset, a level change, or the end of an episode, and the history window restarts at these boundaries."
- **[DOC] Returning to states:** the graph explorer "hashes frames into states, records the actions tried in each state, and returns along known paths to states with untried actions." "Otherwise it moves along known edges to the nearest untried action, by priority and then by distance. If none is reachable, it retries the least-tried actions of the current state." It "never rebuilds its graph within a level." Related work: "Go-Explore keeps an archive of visited states and returns to promising ones before exploring from them".
- **[DOC] State hashing:** "A state is keyed by a hash of the frame, with the status bars masked as in the first frame of the level, and by the set of available actions." It "masks only thin bars along the top and bottom edges". Separate "action-independent cells" mask: "A cell is action-independent if every candidate action leads to the same predicted color for it and this color differs from the current frame, as for a timer or a step counter."
- **[DOC] Counters are common:** of 69 annotated recurring mechanics in 20 games, 21 are counters: "A counter is a step or budget bar (21)". "the return to the start in ls20" is listed as a mechanic that fires fewer than three times in the median recording.
- **[DOC] Novelty per window:** Figure 6 uses "the share of the window's actions that reached a game state not seen before in the level" over windows of 15 actions.
- **[DOC] Budgets and measures:** "Each run plays one of the 25 public games with environment seed 0 and agent seeds 0 to 9, and every measure is read from its first 1,000 actions, including resets." Measures L1@N, L2@N, and "RHAE@N: the official action-efficiency score over the first N actions". Kaggle: about 380 actions per game in nine hours for 110 hidden games.
- **[DOC] Results:** RHAE@1000: random 0.045, from-scratch CNN 0.099, graph explorer 0.149, with frozen WARC 0.181, WARC-Agent 0.455, oracle world model 1.392 (all on the 0-100 scale). Truncation barely matters at this skill level: RHAE "0.144, 0.177, and 0.451" at 380 actions and "0.143, 0.175, and 0.448 when cut at 250 actions". "In 20% of the decisions at which some action would complete the level, the explorer took another". "test-time training on the GPU is not deterministic."
- No counts of resets, deaths or wasted actions.

### B4. "Can LLMs Improve Their Own Harness?" (2610.30499)

- **[DOC]** Names recovery as a harness function: "A harness is a symbolic program that orchestrates calls to the model, handling perception, memory, tool use, recovery, and inference allocation". It does not analyse in-game recovery.
- **[DOC]** Model-built harness families include "replay systems", "Strategist, executor, and replay system" (Fable high), "World-model and replay hybrids" (Opus xhigh), "deterministic planners, and inference-budget managers". Revisions "repeatedly reorganize memory, perception, batching, replay, and resource allocation." No detail on what the replay systems replay or how they treat game over.
- **[DOC]** "It can request one action or a sequence, use code to execute a discovered strategy, and reuse computations to reduce inference cost."
- **[DOC] Budgets:** RHAE defined with the 5 b_l per-level budget; 24-hour wall clock per gameplay session; "Gameplay inference has no common total-dollar or model-call cap". Smoke qualification: "Each game permits 50 charged actions and stops after two completed levels or a win." Mean charged actions per held-out game: 259.6 (initial), 292.0, 273.6. "lower action counts need not imply better efficiency because systems may stop without completing a game."
- **[DOC] A self-imposed cap as a failure cause:** "Three development games exhausted H1's self-imposed 100-decision limit ... Revision 2 raised this internal limit to 120 ... Held-out RHAE rose from 29.24 to 53.56" (several changes at once; no causal claim).
- **[DOC]** "Recovery" in appendix G means restarting interrupted evaluations: "2,130 attempts for 2,025 game-snapshot slots ... Sixty-three slots have multiple attempts ... Twenty-one slots contain a fresh restart"; "such a restart can draw new model responses and is not deterministic resumption."
- **[DOC] Frame noise:** "The validator accepts a narrowly specified frame-hash discrepancy caused by unseeded visual noise in lf52, while requiring agreement on state, level completion, and available actions." "213 such frame events, all on lf52".
- **[DOC] A caution about forced follow-up, by analogy only:** revision episodes in which "a post-edit result triggers another edit, revert, test change, scope change, or criterion-based stop" averaged -0.76 versus +2.48 for hand-off episodes (interval includes zero). And "Abstention is part of adaptation ... Candidate revisions should be compared with a preserved baseline and rejected or rolled back when they do not justify replacement."

### B5. Technical report on recovery

- [DOC] Nothing on agent recovery policy. Relevant fragments: humans may reset the current level at any time (section 5.1); the definition of planning includes "the agility to course-correct in response to environmental feedback or unexpected results" (section 2.1); section 4.2: per-level scoring so that designers do not "encourage AI to waste actions on levels because they're still 'under budget' for a given environment."
- [DOC] Preview-competition winners "used an informed search approach, exploring as much of the action space of the environment as possible" (StochasticGoose 12.58%, Blind Squirrel 6.71% with "A directed state graph from observed frames").

---

## C. Evaluation method

### C1. Variance across repeated runs

- **Lehmann and Vahdati, section 5 [DOC]:** "Ten evaluations of one frozen final harness on the same twenty held-out games yield a sample SD of 3.99 RHAE."
- **Appendix D.1 [DOC]:** the harness is "Sol-high replicate 1 at H2" (GPT-5.6 Sol, high effort; a model-written harness), "selected post hoc after campaign outcomes were available ... a diagnostic case rather than a random sample of harnesses". "The original evaluation ran in August 2026 and the nine fresh evaluations in September 2026." Scores: 53.56, 46.86, 43.38, 48.21, 45.32, 55.37, 46.52, 49.23, 52.10, 44.75. "mean RHAE is 48.53, the sample standard deviation is 3.99, and the range is 43.38-55.37." "The nine fresh evaluations alone have mean 47.97 and sample standard deviation 3.79". "The mean absolute difference between two evaluations is 4.73 points." "Variation is larger at game level: the median within-game sample standard deviation is 18.78 RHAE points, and the three largest are 30.76 on sb26, 28.33 on m0r0, and 27.13 on tn36." "one harness is insufficient to define a universal noise threshold." Actions per evaluation ranged 8,459-10,135; levels completed 90-104; complete games 5-8.
- They use epsilon = 5 points as a descriptive threshold (Table 9) and say "score changes of only a few points require cautious interpretation".
- **VISTA, appendix B.1 [DOC]:** three runs with GPT-5.6 Sol: 99.00, 98.90, 99.23, "99.04 +/- 0.17". (Lehmann and Vahdati quote VISTA's Sol-max figure as 98.27; the VISTA v1 text I read says 99.00. Probably a different version.)
- **Tycho, section 7 [DOC]:** "We evaluate one stochastic run of each reported configuration". Table 3 intervals "measure sensitivity to benchmark composition, not run-to-run model variability." Orchestrator minus no world model: +9.42, interval [3.97, 15.76], 11/11/3 games better/tied/worse; "deleting any one game leaves a difference between +7.63 and +10.14." Orchestrator minus trigger: +5.43 [-6.73, 16.44].
- **Exposures paper [DOC]:** closed-loop play over 10 agent seeds per game; paired intervals over games and seeds (for example +0.31 [0.12, 0.52]); "With 25 games, the level-1 intervals span 14 to 21 points, so the table rules out only large effects."
- [INFER] The 3.99 figure is for a mid-scoring harness (about 48.5) averaged over 20 games with no tight action cap. Near the ceiling the spread collapses (VISTA 0.17). A single game is far noisier (median SD 18.78).

### C2. Development and held-out splits

- **Tycho, section 5 [DOC]:** "Five were randomly designated for harness development: tr87, vc33, r11l, bp35, and ft09." All 25 are reported; policy selection used all 25 with Opus 4.8.
- **Lehmann and Vahdati, appendix A [DOC]:** "Five development games were selected at random before the campaign: tr87, vc33, r11l, bp35, and ft09. The other 20 public games were fixed as feedback-held-out." Held-out 20 (Table 12): ar25, cd82, cn04, dc22, g50t, ka59, lf52, lp85, ls20, m0r0, re86, s5i5, sb26, sc25, sk48, sp80, su15, tn36, tu93, wa30. Result: development gain 8.42, held-out gain 2.80 (95% interval [-1.44, 7.35]); adaptation gap 5.62 [1.78, 9.77]. "Omitting r11l only from the observed development summary reduces the mean development-held-out gap from 5.62 to 3.02 points."
- **Exposures paper [DOC]:** "The 25 public games are split into three folds"; "The test-time recipe was selected on the five public games not covered by MechEval". Named among those five: cn04, bp35, lf52. [INFER] By elimination from the 20-game table the other two are g50t and sp80.
- **VISTA [DOC]:** no split; all 25 public games.
- **Technical report, section 4.3.1 [DOC]:** researchers built harnesses on ls20, ft09 and vc33 and "We found extreme bimodal performance across the two sets ... in a variant of environment TR87, Opus 4.6 scores 0.0% with no harness and 97.1% with the Duke harness, yet in environment BP35, Opus 4.6 scores 0.0% under both configurations."

### C3. Cost

- **Tycho [DOC]:** 25-game totals at list prices: about $5.66k (no world model), $7.27k (single), $5.78k (orchestrator), $8.03k (trigger) with Opus 4.8; GPT-5.6 Sol $4.47k ($179 mean, $114 median per game, maximum $649); Opus 5 $2.99k ($119 mean, $97 median per game, maximum $303; 15.1k model calls). Trigger used 44.4k calls versus 24.1k for orchestrator. Prefix analysis: Opus 5 "reaches 98.62 at $250 and 100 by $500" per game ceiling.
- **Lehmann and Vahdati [DOC]:** $10.30 / $7.15 / $7.57 mean per held-out game across stages; whole programme "at least $18,129.27".
- **VISTA [DOC]:** subscription command-line tools, not the API; 30.7M tokens per game (GPT-5.6 Sol, 200K context), 71.9M with text grids; "a 64x64 grid requires roughly 4,000 tokens, compared with approximately 308 image tokens".
- **Technical report [DOC]:** full evaluation set costs "tens of thousands of dollars in API costs".

### C4. Contamination and exposure caveats

- **Tycho, section 7 [DOC]:** "Benchmark exposure also cannot be excluded: three games were public before the full 2026 release". Footnote: "The full public set launched on March 25, 2026, but ft09, ls20, and vc33 had been public since the July 2025 developer preview. The reported cutoffs for Opus 4.8 (January 2026) and GPT-5.6 Sol (February 16, 2026) predate the full release but postdate the three preview games; Opus 5 has a May 2026 cutoff, after the full release". Appendix E: "The trace cannot determine whether GPT-5.6 Sol encountered this game during training".
- **VISTA, section 6 [DOC]:** "because the models we use were released after the public benchmarks, we cannot rule out the possibility that these games were included in their training data."
- **Lehmann and Vahdati, section 8 [DOC]:** "Because the games are public, some models may have encountered them during training."
- **Technical report [DOC]:** public-set scores are never reported officially; "evaluating on it is emphatically not a valid measure of progress towards AGI." Section 1.3.3 describes memorised colour mappings in ARC-AGI-2 reasoning traces.
- **Selection effects [DOC]:** Tycho notes that Schema's 98.98 keeps the better of two trajectories per rerun game and PRO-LONG's 97.4 is "a lower bound on best@2"; "The protocol must be stated alongside the score." AERA's evaluator "maps WIN, GAME_OVER, and a None step return to the same termination path, which the agent records as solved".
- [INFER] Our model (Opus 5.5) is newer than every cutoff discussed, so exposure to all 25 public games cannot be excluded.

---

## D. Claim checks

1. **"Resets count as actions, and the squared efficiency term in the score makes every wasted action expensive." (attributed to the technical report)** - PARTLY SUPPORTED.
   - Squared term: supported by the report. "Note that level scoring is calculated using the square of efficiency." (4.1); "This adjustment increases the penalty for highly inefficient solutions while preserving partial credit." (4.2).
   - Resets count: NOT in the technical report. It is in Tycho ("It costs one in-play action ... The initialization RESET that creates a play is unscored."; "each take_action, including RESET, spends one scored environment action") and in the exposures paper ("a reset after a game over counts as an action"). Cite those instead.
   - "Every wasted action expensive" is too strong. [INFER] Wasted actions cost nothing while the level is still at the 115% cap (a <= 0.93 h), and nothing in score terms on a level that is never completed. Tycho: "171/183 for Opus 5" completions sit at the cap. The report itself says of the 5x cut-off: "given the power-law decay of the scoring function, the resulting differential is negligible."
2. **"Later levels carry linearly larger weights and compose mechanics from earlier ones."** - SUPPORTED. "the weight for level l is w_l = l" (4.1); "a simple linearly weighted average" (4.2); "Later levels are therefore expected to require the accumulation and integration of concepts learned earlier in the environment." (3.4). Note "expected to": a design intent. The report's formula says n=5 though public games have six or more levels.
3. **"Tycho with Opus 5 completed all 25 public games at 100 RHAE in 6,641 actions."** - SUPPORTED. "An Opus 5 run also reaches 100.00 RHAE (public scorecard), completing all 25 games and all 183 levels in 6,641 actions." (5.1). One run; Opus 5's cutoff is after the public release.
4. **"VISTA reached the same score with no simulation, using stored frames and retrieval."** - PARTLY SUPPORTED. Score: "VISTA achieves a perfect RHAE score of 100.00 ... It uses 7,302 actions in total" (4.2). The paper's own wording is "without program synthesis", not "no simulation". The agent still predicts in language: it "uses this understanding to predict action outcomes and plan subsequent actions", and the prompt asks it to "Build and use a compact, revisable model of the game" and "Before each `play`, briefly state what you expect to see." It also uses two note files and exact pixel readout. Safer wording: "no executable world model or program synthesis".
5. **"In Tycho's matched study on Opus 4.8, the policy with no world model scored 79.07 RHAE and the best model-building policy scored 88.49."** - SUPPORTED. "The direct-reasoning no-world-model baseline reaches 79.07 RHAE ... the builder-delegating orchestrator reaches 88.49." Single 85.36, trigger 83.07. One run each.
6. **"Tycho separates game-over frames from actionable ones and handles resets in an outer protocol."** - SUPPORTED. Definitions 2 and 3; "Terminal, fatal, and animation frames remain separate from ordinary transitions because the actor never chooses an action from them."; "RESET is selected by the actor, handled by the outer harness, and not modeled by transition". Nuance: the protocol does the bookkeeping; the decision to reset is the model's.
7. **"Lehmann and Vahdati measured a standard deviation of 3.99 RHAE points over ten runs of one fixed harness" and used a development and held-out split.** - SUPPORTED. Quotes in C1 and C2. Caveats: 20 held-out games, GPT-5.6 Sol, a model-written harness chosen post hoc, mean 48.53, one of the ten runs a month older.
8. **"Tycho formalizes a game as shared mechanics with a per-level initial state"; "VISTA separates a note that persists across levels from a note for the current level."** - SUPPORTED. Tycho Definition 1: "The mechanics shared by the levels of one ARC-AGI-3 game form a parameterized rendered deterministic Moore machine"; "The parameter theta denotes mechanics shared across the game, while the initial state s_0^l varies by level." VISTA: "GUIDE.md stores reusable knowledge about the game across levels and sessions. WORKING.md stores temporary state and plans for the current level. It is retained across RESETs and context restarts, cleared when the level advances".
9. **"The papers we reviewed treat recovery as plumbing, not as a policy to study."** - SUPPORTED for these five. None varies or measures a reset, undo or replay policy. Closest material:
   - Tycho's prompt contains an untested priced-reset heuristic ("Prefer RESET when the current attempt is unwinnable or clearly more expensive than restarting"), which is R2's rule in prose, left to the model.
   - Tycho reports "unfinished tails" and game-over counts, and one audited run with 3 resets and 74 abandoned transitions; these are descriptive.
   - Tycho's Trigger policy forces a builder call at fatal-reset boundaries, but the studied factor is model repair.
   - VISTA exposes per-attempt history and keeps WORKING.md across resets; not evaluated separately.
   - The exposures paper's explorer returns along known paths and cites Go-Explore; not studied.
   - Lehmann and Vahdati list "recovery" as a harness job and observe model-built "replay systems", without analysis.

---

## E. Design implications (all [INFER] unless a quote is given)

### E1. Budget
1. A 100-action cap per game is small against the benchmark's scale. Summed human baselines per public game run from 171 to 1,843 (median 638). VISTA with Opus 5.0, at 100 RHAE, needed 75 to 1,008 actions per game (median 219) and finished only three games within 100. So a stall "on later levels" at 100 actions is partly the cap itself. Under such a cap R2's price rule will almost always say "do not reset", which leaves little behaviour to compare.
2. Consider a budget tied to the baseline, as the official runs do ("five times the human-baseline median action count per level"), or report the cap as a fraction of each game's summed baseline. Lehmann and Vahdati's self-imposed "100-decision limit" case shows a fixed cap itself being the failure.
3. Decide and state whether a level finished beyond 5h scores zero (Lehmann and Vahdati's definition) or (h/a)^2 (plain formula); check the scorer.

### E2. What a reset really costs
4. Action counts are per level and accumulate over attempts. Return cost after a reset = 1 (RESET) + replayed prefix, all added to the same level's a_l. Automatic replay saves model calls, not scored actions. R2's price should therefore be in two currencies: scored actions and inference.
5. Score sensitivity: a = h gives 100%, 1.5h 44%, 2h 25%, 3h 11%, 5h 4%. But finishing a level also lifts the completion cap and opens later, heavier levels with fresh counters, so finishing inefficiently can still be worth far more than the level's own credit. A price rule based only on the current level's (h/a)^2 will under-value recovery.
6. Guard against accidental full resets: "If no ACTIONs have been issued, the entire game resets. Two consecutive RESETs therefore guarantee a completely fresh game." [SUPP]. The harness should never send RESET twice in a row or as the first command of a level, and should log `full_reset`.
7. After GAME_OVER only RESET is accepted [SUPP], so that reset is forced; separate forced resets from chosen ones in "reset count and timing".
8. Undo: treat as a third option (probably one action per step back) wherever `available_actions` contains 7. Record per game whether it is offered, whether it restores step counters, and whether the scorer counts it; no paper answers these.

### E3. Replay
9. Determinism supports replay: recordings "are replayed under both win and loss conditions, confirming that the engine can serialize and faithfully re-execute action traces"; Tycho rescored whole traces by deterministic replay.
10. Verify each replayed step, as Tycho does for plans: release the next action only while "the observed frame matches the stored hash, and the action remains available", and stop on mismatch.
11. lf52 has "unseeded visual noise", so exact frame hashes differ between identical action sequences there; compare state, level and available actions, or mask the noisy cells. Hash the settled frame, not animation frames.
12. A stored prefix that ran through a life loss or a step-counter drain may not be the shortest way back; store the shortest verified path to the furthest state (the exposures explorer keeps a graph and returns "along known paths").

### E4. R1 stall detection
13. A raw frame hash will rarely repeat: 21 of 69 annotated mechanics are step or budget bars that change on every action. Mask status bars (the exposures explorer does) or the detector never fires.
14. Masked hashes merge distinct hidden states (Tycho Proposition 1: "the current rendered grid and action mask are insufficient whenever two such histories share that visible output"), so expect false alarms in games with hidden counters or scrolling views.
15. The trigger "no new hash and no memory change" will miss the sk48 pattern: 314 actions, plenty of new states and new hypotheses, no level completed, because the goal was wrong. Add a progress-based trigger (actions since the last level completion relative to the level baseline or remaining budget).
16. Many levels end by a draining counter. A stall detector that fires after the counter is nearly spent only converts a death into a reset at the same cost; the threshold should scale with the level's baseline, not be one constant.
17. Forced interventions have a price. Tycho's Trigger policy (harness-forced builder calls, including at fatal-reset boundaries) scored 83.07 against 88.49 for actor-requested calls, with 44.4k versus 24.1k model calls, and five games hit the call limit (difference not statistically clear). Log the calls and cost that R1 adds and cap forced deliberations per level.

### E5. Measures
18. Use VISTA's attempt unit: an attempt runs from level entry or RESET to GAME_OVER, WIN or TERMINAL.
19. Add Tycho's "unfinished tail" (actions after the last completed level) as an objective companion to dead-end loss; it needs no definition of "progress event".
20. Both are censored by the budget ("Trigger's shorter unfinished tails are budget-censored"); compare conditions on levels both completed, as Tycho does, and report tails separately.
21. Count in-level life losses (ls20 respawn) as a third event type besides RESET and GAME_OVER.
22. Cross-check reset counts against the official scorecard's per-environment "reset counts" [SUPP].
23. RHAE alone is a blunt outcome: cap saturation hides efficiency differences for strong play and the completion cap dominates for weak play. Report levels completed, per-level actions and cap counts alongside.

### E6. Repeats and analysis
24. With suite SD near 4 points (20-game mean) and per-game SD near 19, single runs cannot resolve condition effects under about 5 points. Run several repeats per game and condition, pair by game, and treat the action-level recovery measures as primary.
25. Keep Tycho's and Lehmann and Vahdati's split (tune thresholds on tr87, vc33, r11l, bp35, ft09; report on the other 20) so stall thresholds and price rules are not fitted to the reported games. Development gains overstated held-out gains by 5.62 points in their study.
26. State exposure caveats: all 25 games are public and older than our model's training cutoff.
