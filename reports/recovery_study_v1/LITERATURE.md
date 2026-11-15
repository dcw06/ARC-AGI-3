# Reading record for the recovery study

Read 2026-11-14 by six AI readers, each given one group of documents and the same questions. Their full
notes, with quotations and section numbers, are in `reading_notes/`. I have not re-read the sources
myself; where a reader could not read a text, that is said below.

"Recovery" here means deciding when to reset or undo, and getting back after a reset or game over.

## Sentences in the plan that need changing

| Plan sentence | What the sources say | Suggested wording |
|---|---|---|
| "Resets count as actions, and the squared efficiency term in the score [1] makes every wasted action expensive." | The technical report gives the squared term but does not say resets count; Tycho and the exposures paper do. A level keeps the 115 cap until its actions pass about 0.93 of the baseline, and an unfinished level scores zero whatever it used. | "Resets count as actions [12], and the level score falls with the square of actions once they pass about 0.93 of the level's baseline [1]." |
| "VISTA reached the same score with no simulation, using stored frames and retrieval [7]." | VISTA reports 100.00 in 7,302 actions "without program synthesis". Its agent still predicts action outcomes from its notes. | "... with no program synthesis ..." |
| "Go-Explore showed the value of returning to a known good state before exploring further [4]." | True, but replay is not how it returns: it restores saved simulator state (not counted) or uses a learned goal-conditioned policy trained over billions of frames. Stored action sequences serve as demonstrations for later training. | Keep the sentence; do not cite it for replay that is paid for in actions. |
| "Language Agent Tree Search backtracks freely because its environments reset at no charge [19]." | LATS assumes the environment can be reverted and counts no cost; it calls the environment cost "trivial" for its benchmarks and lists the assumption as a limitation. | "LATS assumes the environment can be reverted to any earlier state and counts no cost for doing so [19]." |
| "The textbook treatment is online search with irreversible actions and dead ends [13] and online planning under uncertainty [10]." | Russell and Norvig 4.5 is the right section; its body text was not available to read. From the reader's memory, unverified, it defines the problem and then restricts itself to "safely explorable" spaces. Kochenderfer chapter 9 assumes a known model; unknown models are chapters 15 and 16. LaValle (12.2, 12.3) is the best source on the cost of going back. | "... online search with dead ends [13], planning under model uncertainty [10, ch. 15-16], and the cost of physical backtracking (LaValle)." |
| "Exploration under a known horizon is standard material in Sutton and Barto [16] and Kochenderfer et al. [10]." | Kochenderfer 15.1 and 15.5: yes. Sutton and Barto acknowledge the dependence in one sentence (2.1) and call the computation beyond the book's scope. | Cite Kochenderfer for the method; cite Sutton and Barto only as acknowledging the dependence. |
| "In Bayes-adaptive reinforcement learning the best exploration policy depends on the remaining horizon [6, 20]." | VariBAD says so directly. BAMCP is infinite-horizon and discounted and says nothing about a remaining budget. | Cite [20] only. |
| "ARC Prize now reports a Standard harness and a Provider Adapter harness separately; the adapter differs by ..." | Fair, with two gaps: the policy gives the two features as examples ("such as"), and the Standard harness also lets the model carry notes it chooses to keep. | Add both points. |
| "the papers we reviewed treat recovery as plumbing, not as a policy to study" | Holds for every paper read. Nearest prior work is listed in the next section. One cited paper outside the list (Rudakov et al. 2025, navigating back to recorded frontier states) was not read. | Keep, and name the nearest prior work. |

Supported as written: level weights growing with level number; Tycho at 100 in 6,641 actions; 79.07 against
88.49 on Opus 4.8 (one run each); Tycho's separate game-over frames and outer reset handling; the standard
deviation of 3.99 over ten runs (a GPT-5.6 Sol harness on 20 held-out games; development games tr87, vc33,
r11l, bp35, ft09); Tycho's shared mechanics and VISTA's two notes.

Also found: the Opus 5.5 results page listed in the reading has no ARC-AGI-3 result for any effort level.

## Nearest prior work on recovery

| Source | What it does |
|---|---|
| "Do Coding Agents Need Executable World Models ..." (2607.15439), 8.1 | A "trouble prompt": at a reset after game over, if more than 50 further actions have accumulated on the level, the controller sends an extra prompt first. Introduced together with a faster client, so its effect was not isolated. The agent is forbidden to reset by itself. |
| "Executable World Models ..." (2605.05138) | The controller owns the reset; it normally happens only after game over, though the agent occasionally reset by itself. Notes one case where a reset before any action restarted the whole game. Reports actions spent on the final unsolved level, a level-sized version of dead-end loss. |
| OPINE-World (2607.01531) | A stop rule only: 2,000 actions per game, or a stall of more than 500 actions on a level. |
| Tycho (2607.28287) | The model decides, and a RESET costs one action. One prompt line: "Prefer RESET when the current attempt is unwinnable or clearly more expensive than restarting." Never varied. One audited run: 3 resets and 74 abandoned transitions in 478 actions on ls20. Its harness-triggered policy scored 83.07 against 88.49 for model-requested, with nearly twice the calls. That is one run each, the difference is not statistically clear (interval -6.73 to 16.44), and the forced step is model building, not a reset decision; it is a weak caution about forced deliberation. |
| Exposures paper (2611.12324) | No language model. Resets only after game over; its explorer "returns along known paths to states with untried actions"; its state key masks the status bars, and 21 of 69 annotated mechanics are step or budget bars. |
| Reflexion (2303.11366) | A stall rule that ends the trial: the same action with the same response more than 3 times, or more than 30 actions. Resets are free there. With the rule but without reflection, results stopped improving. |
| Go-Explore (2004.12919) | A stall rule inside exploration, in the policy-based variant: explore harder after 50 steps with no new cell, end the episode after 1,000. Cells are coarse on purpose; one cell per frame is warned against. |
| Theory-based RL, EMPA (2107.12544) | The only agent-side restart rule found, in two steps. When it has "lost twice in the same way", or nothing but the agent moves, the planner switches to a longer-horizon mode. If that mode then fails to find a plan from a state more than once, "it restarts the level and doubles its planning budget". People in that study could restart a level; how often they did is not reported. It also says that with many moving objects its search "can experience sufficient novelty over a great many states without the agent needing to make a move". |
| LaValle, 5.4.3 | A stall counter that escalates to a random walk and then backtracks, with the warning that its parameters "had to be adjusted for each problem". |

None of these varies a reset policy, measures one, or replays a stored action sequence in the environment
at a cost in counted actions. The closest numbers are Tycho's audit of one ls20 run and the actions on the
final unsolved level in 2605.05138.

## What the reading changed in the design

1. **Mask the status bars before hashing.** Three sources say a raw frame hash is new on every action
   (exposures paper, OPINE-World, EMPA). Done: the tracker estimates counter cells and ignores them.
2. **A board-novelty signal will miss the documented stalls.** The long stalls reported in the papers
   (1,008 actions on sk48 level 1; 1,320 on tr87 level 2) kept producing new states and new notes. A
   level-action signal scaled to the baseline was added.
3. **"No memory change" must mean a change of substance.** Compared as claims and statuses, not wording.
4. **Check every replayed action against the stored board and stop at the first difference** (EMPA's
   prediction check; open-loop plans are exact only under determinism in all three planning books).
   Done. One paper reports unseeded visual noise in lf52 that breaks frame equality.
5. **Never reset before the first action of an attempt, never twice in a row** (official documentation
   and 2605.05138). Done, and enforced again in the audit.
6. **The furthest state may be the dead end.** The model, not the harness, chooses how much of the ended
   attempt to replay, and the fatal last action is never offered.
7. **R2 is a bundle.** Two readers and one paper (2607.15439, about its own bundled change) make the
   point. R2a and R2b were added.
8. **A forced question may not help.** Reflexion's reset without reflection stopped improving, and
   Tycho's forced mode did no better than model-requested (weak evidence: one run each, and about model
   building). Every check and what followed it is logged so false alarms can be counted.
9. **Game as the unit, paired by game, primary outcome named first, thresholds frozen on development
   games** (Murphy, Goodfellow, Peters; OPINE-World's own analysis). In the pilot design.
10. **Do not use the earlier stalled run as the control.** Selection on a bad outcome guarantees apparent
    improvement. The pilot re-runs the control from the same start.

## What was read

Depth: **full** = whole text; **parts** = the sections named by the reader; **not read** = could not be read.

### ARC-AGI-3 papers on the list

| Document | Depth | Use for this study |
|---|---|---|
| ARC-AGI-3 technical report (2603.24621) | full | Scoring formula, level weights, humans could reset a level at any time, 5x baseline action budget. Silent on whether resets count and on game over. |
| Tycho (2607.28287) | full | Resets count; model decides; no stall rule or replay; 6 to 20 game overs per 25-game run. |
| VISTA (2610.02200) | full | RESET is an ordinary action; attempt defined from level entry or RESET to game over or win. |
| How Many Exposures Does a World Model Need? (2611.12324) | full | Masked state key; return along known paths; resets counted in the action total. |
| Can LLMs Improve Their Own Harness? (2610.30499) | full | Run-to-run spread; development and held-out split; names recovery as a harness job without analysing it. |

Also read by that reader, outside the list: four official documentation pages (methodology, actions,
reset, scorecards), because the papers do not say what RESET restores.

### Added during the planning conversation

| Document | Depth | Use |
|---|---|---|
| Go-Explore (2004.12919) | full, pre-print version | See above. |
| Executable World Models ... (2605.05138) | full | Controller-owned reset; reset counts against the budget; whole-game restart hazard. |
| Do Coding Agents Need ... (2607.15439) | main text and prompt appendix; tables skimmed | Trouble prompt; actions after game over are not free; "a single playthrough per game cannot estimate run-to-run variability". |
| OPINE-World (2607.01531) | main text and most appendices | Stall stop rule; paired per-game analysis; scoring formula as used by the scorer. |
| Rethinking the Evaluation of Harness Evolution (2607.12227) | main text, appendices A-B | Evolved harnesses gave no held-out gain; calls for matched budgets and held-out evaluation. |
| Self-Harness (2606.09498) | full | Not about ARC-AGI-3. Accept a change only if neither split regresses. |
| HarnessDev (2609.01437) | main text, appendix B | Not about ARC-AGI-3. The same commit varies by about 4.75 points; most measured gains were inside that band. |
| ARC Prize testing policy | full | Harness definitions; one run per result, no averaging; no rule on action limits or resets. |
| Claude Opus 5.5 results page | full, including embedded data | No ARC-AGI-3 result. |

### Background papers on the list

| Document | Depth | Use |
|---|---|---|
| Language Agent Tree Search (2310.04406) | full | Assumes free reversion; see above. |
| Reflexion (2303.11366) | full | Stall rule; what carries over between trials. |
| ReAct (2210.03629) | parts | Names repetition loops as its typical failure; set its step cap from data. |
| Voyager (2305.16291) | parts | Gives up after 4 rounds; stores only self-verified programs. |
| BAMCP (1205.3109) | parts | Infinite-horizon; nothing on resets or budget. |
| Plan2Explore (2005.05960) | parts | Expected novelty rather than novelty after arrival. Nothing on resets. |
| VIME (1605.09674) | parts | Information gain as change in belief. Nothing on resets. |
| RL^2 (1611.02779) | full | What survives a reset; the second episode is shorter but not free. |
| VariBAD (1910.08348) | main text, two appendices | "Trading off exploration and exploitation optimally depends heavily on how much time the agent has left." |
| PEARL (1903.08254) | main text, one appendix | Holds one hypothesis per episode; costly when resets are priced. |
| MAML (1703.03400) | parts | Nothing relevant. |
| Theory-based RL, EMPA (2107.12544) | full | See above. |
| Schema Networks (1706.04317) | full | Nothing on death or restart. |
| DreamerV3 (2301.04104) | parts of the main text | Treats another system's early resets as a confound. |
| MuZero (1911.08265) | parts | Nothing relevant. |
| PlaNet (1811.04551) | parts | Nothing relevant. |
| Slot Attention (2006.15055) | parts | Nothing relevant. |
| DreamCoder (2006.08381) | parts | Nothing relevant. |
| CodeIt (2402.04858) | parts | Nothing relevant. |
| Combinatorial Sketching (author copy) | parts | Nothing relevant. |

### Textbooks

Books were not read whole. Each reader found the contents, chose the sections that could bear on the
study, and read those.

| Book | Depth | Use |
|---|---|---|
| Kochenderfer, Wheeler and Wray, Algorithms for Decision Making | parts: ch. 6, 7, 9, 15, 16, app. F | Finite-horizon exploration; value of information; Bayes-adaptive frame; a replacement problem whose best policy changes with the horizon. |
| LaValle, Planning Algorithms | parts: ch. 2, 5, 8, 10, 12, 14 | Cost of returning to an earlier state; states from which the goal cannot be reached and why they cannot be recognised; lost-cow doubling; stall counter. |
| Sutton and Barto, Reinforcement Learning | parts: ch. 2, 3, 5, 6, 8, 10, 17 | Options with termination; one worked example of a voluntary recharge against a forced rescue. Little on horizon. |
| Russell and Norvig, Artificial Intelligence | **body not read** (not public). Contents, index, figure captions and pseudocode only | Section 4.5 is where dead ends and irreversible actions are defined. Anything beyond the captions is from the reader's memory and marked so in the notes. |
| Murphy, Probabilistic Machine Learning: Advanced Topics | parts: ch. 3, 6, 33, 34, 35, 36 | Expected utility; value of information; test-then-commit under a budget; restart arithmetic; randomised comparison. |
| Murphy, Probabilistic Machine Learning: An Introduction | parts: ch. 4, 5 | Paired comparison of two systems; bootstrap; permutation test; cautions on p-values. |
| Peters, Janzing and Schölkopf, Elements of Causal Inference | parts: ch. 2, 6, 8, 9.1-9.2, app. A | What a set condition identifies; bundled interventions; Simpson's reversal; selection. |
| Prince, Understanding Deep Learning | parts: ch. 8, 19 | Introductory reinforcement learning only; the validation and test rule. |
| Goodfellow, Bengio and Courville, Deep Learning | parts: ch. 5, 11 | Test data must not choose settings; choose the metric first. Says reinforcement learning is outside its scope. |
| Deisenroth, Faisal and Ong, Mathematics for Machine Learning | parts: ch. 6, 8 | Variance of a difference; nothing on the decision. |

No textbook treats a reset as an action with a cost, or reset-then-replay as a method.

## Limits of this record

- Readers worked from text copies. Figures were not seen; formulas were read from extracted text.
- Russell and Norvig's body text was not read.
- The Go-Explore copy is the arXiv pre-print, not the journal text.
- One reader's quotes were not cross-checked by another. The quotations in this file are the readers'.
- An independent checker compared the two tables at the top with the notes and the wording was corrected
  where it said more than the notes do. It checked the depth column for 17 of the 44 documents.
