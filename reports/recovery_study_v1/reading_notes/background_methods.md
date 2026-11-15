# Background methods: what they say about recovery (reset, undo, replay)

Reader notes for the recovery study (R0 control, R1 stall detection, R2 priced recovery with automatic prefix replay).
Date read: 2026-11-14. All 13 documents were fetched with `tools/fetch_doc.py` and every title matched the list.
Text copies are in `scratchpad/library/<name>/text.txt` (names: dreamerv3, muzero, planet, rl2, maml, pearl, varibad,
slot_attention, schema_networks, empa, dreamcoder, codeit, sketch).

Conventions used below:
- "DOC:" marks a statement made by the document. Quotes are exact, with the section they come from.
- "INFERENCE:" marks my own reading of what it means for the study. Nothing marked INFERENCE is claimed by a document.
- Figures were not readable (text copies only). Where a claim rests on a figure, I only have the caption and the prose.

Housekeeping: my first fetch loop passed its arguments wrongly and created 12 empty, wrongly named folders in
`library/`; I removed those 12 empty folders and re-ran. No fetch failed after that.

---

## 1. Findings that matter most for the study

### 1.1 EMPA is the only document with an agent-side restart rule, and the only one where humans could restart

DOC (EMPA, Extended Data Figure 9 caption): "The planner always begins a new game in short-term mode, and switches to
other modes when it fails to find a plan within the current search budget. Which mode it switches to depends on whether
it considers itself "stuck". The agent considers itself stuck in short-term mode when it has either lost twice in the
same way, or the game contains no moving objects other than the agent itself (and hence no new possibilities to act
constructively will arise merely by waiting); in each of these cases the planner switches to long-term mode. If the
planner fails but the agent is not stuck, it switches to stall mode for one planning cycle. The agent may also consider
itself stuck in long-term mode, if it has failed to find a plan from a given state more than once, in which case it
restarts the level and doubles its planning budget."

DOC (EMPA, Methods, "Games and human behavioral procedures"): "They were also told that each game had several levels,
and that they needed to complete a level in order to go to the next level, but that they could have the option to
restart a given level if they were stuck, or to forfeit the rest of the game (and any potential earned bonus) if they
failed to make progress after several minutes."

What the text does not contain: any count, timing or comparison of restarts for humans or for EMPA; any statement of
whether a restart costs steps in the learning-efficiency metric; any description of what happens right after a Loss
(the phrase "lost twice in the same way" implies the level is attempted again, but the mechanics are not described).
The word "restart" occurs in exactly those two places in the text.

INFERENCE: EMPA's rule is an escalation ladder, not a single trigger: (a) plan failure with no stuck evidence leads to
one cycle of safe waiting ("stall"); (b) stuck evidence (same loss twice, or a static board) leads to deeper
deliberation; (c) repeated failure of the deeper deliberation from the same state leads to a level restart with a
larger deliberation budget. R1 as planned goes straight from "stall detected" to a forced recovery deliberation, which
corresponds to step (b). EMPA restarts only after deliberation has failed more than once from the same state.
EMPA's triggers are planner failure and repeated identical loss; they are not "N actions without novelty".
EMPA gives no human baseline for restart behaviour, so the study cannot take one from this paper.

### 1.2 A raw state hash is a weak "no progress" signal when anything on the board moves by itself

DOC (EMPA, Methods, "Planning: state pruning"): "The planner ameliorates the exponential explosion of the state space
by using Iterative Width (IW) [62, 63], which prunes states that are not sufficiently different from states previously
encountered in the course of search. This is achieved by defining atoms, logical propositions that can evaluate to
True or False. We indicate the presence of each object in the state with the atom, (object, True), and we use (object,
False) for a known object that is no longer in the game state. We encode the location of each object with the atom,
(object, posx, posy). ... During search, IW prunes any state that fails to make some atom true for the first time in
the search."

DOC (same section): "In games with many moving objects, IW can experience sufficient novelty over a great many states
without the agent needing to make a move; this leads to very inefficient search. To incentivize the agent to move, we
additionally use a penalty on repeated agent positions ... To further reduce IW's sensitivity to moving objects, we do
not generate atoms for the locations of objects hypothesized to be random or whose presence in the game is predicted
to last fewer than 5 seconds, and do not track the location of projectiles produced by the agent."

DOC (EMPA, Methods, "Exploration"): "The module therefore sets exploratory goals of generating interactions between
every pair of classes whose interactions have not yet been observed. In addition, because interactions between the
avatar and other objects can vary as a function of the agentState, exploratory goals between the avatar and other
objects are reset when the agentState changes". And: "The initially large number of exploratory goals decreases as the
model learns more about the game."

INFERENCE: R1 defines a stall as a set number of actions with no new state hash and no memory change. EMPA's authors
hit the matching problem inside their planner: with autonomous or random motion, almost every state is "new", so a
novelty test over whole states never fires. Their fix was to test novelty over an abstraction (which objects exist,
where the controllable and non-random objects are) and to count repeated avatar positions. For R1 this means the
whole-grid hash can fail to detect a stall in any game with moving elements, counters or animations. A second,
coarser progress signal is available in the same paper: a finite list of not-yet-observed interaction types that
shrinks as the agent learns and is re-opened when the avatar's inventory or state changes. This is an analogue of "no
change to the agent's memory".

### 1.3 Meta-RL: what survives a reset is task knowledge, kept separate from position; the return is not free

In RL^2, VariBAD and PEARL an episode reset is imposed by the environment at a fixed horizon. None of the three gives
the agent a reset action, a cost for resetting, or an undo.

DOC (RL^2, Section 2.2): "At the end of an episode, the hidden state of the policy is preserved to the next episode,
but not preserved between trials." And: "The objective under this formulation is to maximize the expected total
discounted reward accumulated during a single trial rather than a single episode."

DOC (RL^2, Section 2.2): "If the episode has terminated, it sets termination flag dt to 1, which otherwise defaults to
0." The flag is part of the policy input.

DOC (RL^2, Section 2.3): "We have also experimented with alternative architectures which explicitly reset part of the
hidden state each episode of the sampled MDP, but we did not find any improvement over the simple architecture
described above."

DOC (RL^2, Section 3.3, maze task, two episodes per trial in training): "The optimal strategy is to explore the maze
efficiently during the first episode, and after locating the target, act optimally against the current maze and target
based on the collected information." Table 3(a), average length of successful trajectories: episode 1 "52.4 ± 1.3"
(small maze) and "180.1 ± 6.0" (large); episode 2 "39.1 ± 0.9" and "151.8 ± 5.9". Table 3(c) "%Improved": "91.7%"
small, "71.4%" large, defined in the caption as "the proportion of mazes where the trajectory length in the second
episode does not exceed the trajectory length in the first episode." The caption also says "These metrics are computed
using the best run among all runs shown in Figure 5", so these are best-case numbers.

DOC (RL^2, Section 3.3): "However, occasionally the agent forgets about where the target was, and continues to explore
in the second episode".

DOC (VariBAD, Section 5.1, gridworld): "Actions are: up, right, down, left, stay (executed deterministically), and
after 15 steps the agent is reset." And: "The best strategy is to explore until the goal is found, and stay at the goal
or return to it when reset to the initial position."

DOC (VariBAD, Appendix C.2): "We implemented task resets by adding a 'done' flag to the states, so that the agent knows
when it gets reset in-between episodes. This allows us to evaluate on multiple rollouts (without re-setting the hidden
states of the RNN) because the agents have learned to handle re-sets to the starting position."

DOC (VariBAD, Appendix C.2): "We hypothesise that the drop of RL2's performance in CheetahVel occurs because it has not
properly learned to deal with environment resets. The sudden change in state space (with includes joint positions and
velocities) could lead to a dramatic shift in the hidden state, which then might not represent the task at hand
properly." And: "For variBAD this is less of a problem, since we train the latent embedding to represent the task, and
only the task. Therefore, the agent does not have to do the inference procedure again when reset to the starting
position, but can rely on the latent task description that is given by the approximate posterior." The authors hedge:
"It might also just be due to implementation details".

DOC (PEARL, Algorithm 2, meta-testing): the context starts empty, a latent z is sampled once per rollout, and after
each rollout "Accumulate context c^T = c^T ∪ D^T_k". Section 1: "the context variables can be sampled and held constant
for the duration of an episode, enabling temporally-extended exploration."

INFERENCE for the harness:
- The memory that should survive a reset is the part that describes the game (rules, goal hypotheses, the verified
  action prefix). Position-dependent notes ("I am next to the door") become false at a reset. VariBAD's diagnosis of
  RL^2 is exactly a memory that mixed the two and was corrupted by the reset.
- The agent must be told, in its input, that a reset happened. All three methods either flag it or rebuild the latent.
- RL^2's Table 3 is the closest thing in this set to a measured return cost: a trained memory shortens the second
  episode but does not make the return optimal, and in 8% to 29% of mazes the second episode was longer than the
  first. This supports measuring return cost directly and supports R2's choice to replay a stored prefix instead of
  asking the model to find its way back.
- Table 3(c) gives a ready form for a per-level measure: share of resets after which the return took no more actions
  than the first arrival.

### 1.4 Explore or commit depends on the horizon that is left (principle only; no usable formula)

DOC (VariBAD, Section 2.2): "Note the distinction between the MDP horizon H and BAMDP horizon H+. Although they often
coincide, we might instead want the agent to act Bayes-optimal within the first N MDP episodes, so H+ = N × H. Trading
off exploration and exploitation optimally depends heavily on how much time the agent has left (e.g., to decide whether
information-seeking actions are worth it)."

DOC (VariBAD, Section 2.2): "it takes exploratory actions to reduce its task uncertainty only insofar as it helps to
maximise the expected return within the horizon."

DOC (RL^2, Section 3.2): "We think that the advantage for small n comes from the need for more aggressive exploitation
... our approach should be able to cope with this shortage of samples, and decides to exploit sooner compared to the
reference algorithms."

INFERENCE: this is the textbook justification for R2's rule (compare the cost of reset-and-replay with the action
budget left). The papers obtain the behaviour by training over a task distribution with the total horizon fixed; they
give no closed-form rule, and none of them treats the reset itself as a priced action, so R2's pricing rule has no
direct precedent in this set.

### 1.5 Smaller points

- Prediction-error monitoring as a guard on replay. DOC (EMPA, Methods, "Planning: prediction-error monitoring and
  re-planning"): "After each action, the agent compares the true s_{t+1} to the predicted ŝ_{t+1}. If the agent's own
  position is not as predicted, or if the agent is too close to a dangerous object whose position was not as predicted,
  the planner is run again; otherwise, the agent continues execution of the action sequence." INFERENCE: R2's automatic
  replay of a stored prefix is open-loop execution of a plan. The same check applies: compare each observed state with
  the state stored when the prefix was recorded and stop the replay at the first mismatch. EMPA and Schema Networks
  both assume deterministic dynamics (Schema Networks, Section 6: "the dynamics of the environments are deterministic");
  prefix replay depends on the same assumption.
- Irreversible states exist in the EMPA game set and restart is the only way out. DOC (EMPA, Supplementary, game
  descriptions): Sokoban Variant 2, "Filling certain holes makes the levels unwinnable."; Watergame Variant 1,
  "destroying the wrong pieces of dirt makes levels unwinnable."; Bait Variant 1, "Filling the wrong holes can make it
  impossible to remove certain boxes from the game board." DOC (Methods, "Learning efficiency"): there were "two games
  (Boulderdash 2 and Sokoban) on which EMPA obtained an efficiency score greater than 0 fewer than three times", and
  the Figure 3 caption excludes "one game ... on which no run of EMPA progressed beyond the first level". The paper
  does not say why EMPA failed on these games. INFERENCE: I cannot tell from the text whether restart handling played a
  part.
- Reset policy is treated as a confound when comparing systems. DOC (DreamerV3, Results, Atari100k): "EfficientZero 44
  holds the state-of-the-art by combining online tree search, prioritized replay, and hyperparameter scheduling, but
  also resets levels early to increase data diversity, making a comparison difficult."
- Death avoidance compared with humans. DOC (EMPA, main text): "people typically interact with objects that result in
  immediate loss only a handful of times across all episodes (Figure 6B). EMPA behaves similarly ... In contrast, DDQN
  typically interacts hundreds or thousands of times with deadly objects before it learns to avoid them". This is a
  human comparison of deaths, not of restarts.
- Terminology traps. "Replay" in MuZero, DreamerV3, DreamCoder and CodeIt means re-using stored experience for
  training. "Backtracking" in Schema Networks is a backward inference pass inside the planner ("This step is akin to
  Viterbi backtracking"). "undoAll" in EMPA is a VGDL interaction type in a list, not an agent action. None of these
  is the study's replay or undo.

---

## 2. Per-document notes

### DreamerV3 — arXiv 2301.04104 (v2, 17 Apr 2024), "Mastering Diverse Domains through World Models"
1. What it is: a general model-based RL algorithm that trains an actor and critic inside a learned world model.
   Read: abstract, introduction, world model learning, critic learning, first half of actor learning, all of Results,
   Previous work, Conclusion, Methods (the HTML holds only "Baselines"). Skipped: rest of actor learning, "Robust
   predictions", references. The supplementary material is not in the HTML and was not read.
2. Recovery: termination is a predicted variable. DOC (World model learning): "we predict rewards r_t and episode
   continuation flags c_t ∈ {0,1}". The flag multiplies the discount in the return target (Eq. 5, written out from the
   formula: R^λ_t = r_t + γ c_t((1−λ)v_t + λR^λ_{t+1})), so a predicted episode end removes all later value. DOC (Minecraft):
   "Episodes last until the player dies or up to 36000 steps equaling 30 minutes". DOC (Critic learning): "we select
   actions by sampling from the actor network without lookahead planning." No agent-chosen reset, no undo, nothing
   carried across episodes except trained weights and the replay buffer. The EfficientZero remark (1.5) is the only
   mention of resetting as a procedure.
3. Usable without training: no. The one idea that carries over is to treat "this state ends the episode" as something
   the agent predicts explicitly.

### MuZero — arXiv 1911.08265 (v2), "Mastering Atari, Go, Chess and Shogi by Planning with a Learned Model"
1. What it is: tree search over a learned latent model. Read: abstract, introduction, prior work, Section 3,
   Appendices A, B, C, D, G, H, I. Skipped: Section 4 results, conclusions, Appendices E and F, score tables.
2. Recovery: DOC (Appendix A): "Terminal nodes. AlphaZero stopped the search at tree nodes representing terminal
   states and used the terminal value provided by the simulator instead of the value produced by the network. MuZero
   does not give special treatment to terminal nodes and always uses the value predicted by the network. Inside the
   tree, the search can proceed past a terminal node - in this case the network is expected to always predict the same
   value. This is achieved by treating terminal states as absorbing states during training." DOC (Appendix I): episodes
   are "limited to the standard 30 minutes or 108,000 frames per episode". No reset decision, no undo, no return to a
   prior state. "Reanalyze" (Appendix H) re-runs search on stored steps for training targets only.
3. Usable without training: no. Search over a learned model has no counterpart in a harness with no simulator.

### PlaNet — arXiv 1811.04551 (v5), "Learning Latent Dynamics for Planning from Pixels"
1. What it is: a latent dynamics model with planning by the cross-entropy method. Read: abstract, introduction,
   Section 2 (Algorithm 1, problem setup, planning), related work, discussion. Skipped: Sections 3 to 5 and the
   appendices (keyword search only).
2. Recovery: nothing. Algorithm 1 calls "env.reset()" at the start of each fixed-length data-collection episode. DOC
   (Section 2): "We use model-predictive control ... to allow the agent to adapt its plan based on new observations,
   meaning we replan at each step." Continuous control tasks with no terminal failure.
3. Usable: no.

### RL^2 — arXiv 1611.02779 (v2, PDF), "RL2: Fast Reinforcement Learning via Slow Reinforcement Learning"
1. What it is: a recurrent policy trained so that its hidden state acts as a learning algorithm within a trial of
   several episodes on one task. Read: the whole paper including the appendix (14 pages), not the reference list.
2. Recovery: see 1.3 and 1.4. Summary of statements: a trial is "a series of episodes of interaction with a fixed MDP";
   each episode starts from a fresh draw of the initial state; a termination flag is an input; the hidden state is
   "preserved to the next episode, but not preserved between trials"; the objective is reward over the whole trial;
   partially resetting the hidden state at episode ends gave no improvement; in the maze the second episode is shorter
   on average but not always, and "occasionally the agent forgets". DOC (Discussion): "doing this also ignores the
   underlying episodic structure. We expect algorithms and policy architectures that exploit the problem structure to
   significantly boost the performance." Episode length is fixed by the environment (tabular MDPs "T = 10"; maze
   "horizon up to 250"). No reset action, no reset cost, no death state distinct from episode end.
3. Usable without training: the design pattern only (carry memory across resets, flag the reset, score the whole
   trial). The mechanism itself is weights trained over a task distribution and does not transfer.

### MAML — arXiv 1703.03400 (v3), "Model-Agnostic Meta-Learning for Fast Adaptation of Deep Networks"
1. What it is: learns an initialisation that adapts in a few gradient steps. Read: abstract, introduction, 2.1, start
   of 2.2, first part of 3.2, 5.3, 6. Skipped: the rest.
2. Recovery: nothing. Fixed horizon H per rollout; adaptation is by gradient steps between batches of rollouts.
3. Usable: no. It needs weight updates.

### PEARL — arXiv 1903.08254 (v1), "Efficient Off-Policy Meta-Reinforcement Learning via Probabilistic Context Variables"
1. What it is: off-policy meta-RL with a latent task variable inferred from collected transitions. Read: the whole
   main text and Appendix A, not the reference list.
2. Recovery: what is carried across episodes is the set of transitions seen so far (the "context"); the task belief is
   recomputed from it and one sample is held fixed for a whole episode (quotes in 1.3). DOC (Section 4.1): "an encoding
   of a fully observed MDP should be permutation invariant: if we would like to infer what the task is, identify the MDP
   model, or train a value function, it is enough to have access to a collection of transitions {s_i, a_i, s'_i, r_i},
   without regard for the order in which these transitions were observed." DOC (Section 1): "our method adapts by
   sampling "task hypotheses," attempting those tasks, and then evaluating whether the hypotheses were correct or not."
   DOC (Section 6.3): "With no stochasticity in the latent context variable, the only stochasticity comes from the
   policy and is thus time-invariant, hindering temporally extended exploration." All tasks have "horizon length 200";
   resets are exogenous. VariBAD's criticism (VariBAD Section 5.2 and Appendix C.3): PEARL "only starts performing well
   starting from the third episode" and "acts according to the current sample, which in the first two rollouts can mean
   walking in the wrong direction."
3. Usable without training: a pattern, with a warning attached. Pattern: commit to one hypothesis for a whole attempt
   and revise only at the episode boundary. Warning from VariBAD: this wastes whole attempts when the hypothesis is
   wrong, which is expensive when every action and every reset is counted. INFERENCE: order-free transition memory is
   enough for inferring rules but not for replay, which needs the ordered action prefix; the two memories have
   different requirements.

### VariBAD — arXiv 1910.08348 (v2), "VariBAD: A Very Good Method for Bayes-Adaptive Deep RL via Meta-Learning"
1. What it is: meta-learned approximate Bayes-adaptive policy conditioned on a latent task posterior. Read: the whole
   main text; Appendix B.1 and B.3, C.1 to C.5. Skipped: Appendix A derivation (glanced at), hyperparameter tables,
   references.
2. Recovery: see 1.3 and 1.4. Further statements:
   - DOC (Section 2.2): "In a BAMDP, the belief is over the transition and reward functions, which are constant for a
     given task." The belief update does not depend on where the agent stands, so it passes through a reset untouched.
   - DOC (Figure 1 caption): "The Bayes-optimal agent matches this behaviour from the second episode, whereas posterior
     sampling needs six rollouts."
   - DOC (Section 1, on posterior sampling): "Doing so is much less efficient since the agent's uncertainty is not
     reduced optimally (e.g., states are revisited)."
   - DOC (Section 5.1): "once the agent finds the goal, the posterior concentrates: the variance drops close to zero,
     and the mean settles on a value."
   - DOC (Appendix B.3): "the performance of RL2 drops again after the fourth episode: this is likely due to
     instabilities in the 128-dimensional hidden state. VariBAD's latent representation, the approximate task
     posterior, is concentrated and does not change with more data."
   - DOC (Section 4): "Non-Bayesian methods for exploration are often used in practice, such as other exploration
     bonuses (e.g., via state-visitation counts) or using uninformed sampling of actions ... Such methods are prone to
     wasteful exploration that does not help maximise expected reward."
   - DOC (Section 6): the decoder could be used "to get a sense for how wrong the predictions are (which might indicate
     we are out of distribution, and further training is necessary)."
   - A discrepancy inside the document: Section 5.1 prints "H+=4×H=45" with H=15; Appendix B.3 prints "H+=4×H=60".
   Resets are exogenous and fixed-length ("after 15 steps the agent is reset"). No reset action or price.
3. Usable without training: the concepts (belief about the game kept apart from position; explore only while it pays
   within the remaining horizon; a belief that has stopped changing is the sign to stop exploring). The trained
   encoder, decoder and policy do not transfer, and the paper notes the lack of formal guarantees.

### Slot Attention — arXiv 2006.15055 (v2), "Object-Centric Learning with Slot Attention"
1. What it is: an attention module that extracts object slots from images. Read: abstract, introduction, opening of
   Methods, conclusion. Skipped: the rest (keyword search only).
2. Recovery: nothing. It is a perception module on static images with no agent, episode or action.
3. Usable: no. It is a trained module.

### Schema Networks — arXiv 1706.04317 (v2), "Schema Networks: Zero-shot Transfer with a Generative Causal Model of Intuitive Physics"
1. What it is: learned local cause-effect rules over object entities, with planning as inference, tested on Breakout
   variants. Read: the whole paper including both appendices, not the reference list.
2. Recovery: almost nothing. Planning looks ahead over a fixed window and repeats after acting. DOC (Section 4.3): "At
   a high-level, planning proceeds as follows: Identify feasible desirable states (activating positive rewards and
   deactivating negative rewards), clamp their value to our desires by adding a unary potential to the factor graph,
   and then find the MAP configuration of the resulting graph." And: "Then we perform the actions found by the planner
   and repeat." DOC ("Avoiding negative rewards"): "If no positive reward was feasible, we backtrack from the earliest
   predicted negative reward." "Backtracking" is a backward pass in inference, not an environment undo. Episodes are
   capped by frame count ("Episodes were limited to 2500 frames"). Losing the ball is a negative reward; there is no
   treatment of death, restart or game over as a decision. DOC (Section 6): "the dynamics of the environments are
   deterministic; and there is no uncertainty in the observed entity states."
3. Usable without training: the feasibility idea only. The planner asks whether any action sequence in the window can
   reach a positive reward ("It will be 0 if no global assignment ... can lead to activate the reward, or 1 if it is
   feasible"). INFERENCE: "no positive outcome is reachable from here under my current rules" is a possible question
   for the R1 recovery deliberation, but a language model can only estimate it, not compute it.

### EMPA — arXiv 2107.12544 (v1), "Human-Level Reinforcement Learning through Theory-Based Modeling, Exploration, and Planning"
1. What it is: an agent that infers a symbolic game description (VGDL), explores to resolve its uncertainty and plans
   by search in its own simulator; compared with 300 human players on 90 games of 4 to 6 levels each. Read: the whole
   text (main, Methods, Supplementary game descriptions, heuristics, Extended Data captions), not the reference list.
   Figures themselves were not readable.
2. Recovery: see 1.1, 1.2 and 1.5. Further statements:
   - Loss states in planning. DOC ("Planning: intrinsic rewards"): "All planner modes return a plan if a goal state is
     reached, and they stop searching states that stem from loss states, so R_g(s,θ) is effectively ∞ for Win states,
     −∞ for Loss states, and 0 otherwise."
   - Modes and budgets. DOC ("Planning: modes and metacontroller"): long-term mode "searches up to a limit of 1,000
     imagined states in order to find such a plan, and this limit progressively doubles over repeated failures to find
     successful plans." "Stall mode simply returns short plans that do not result in Loss states, and searches only up
     to 50 nodes to find such plans; this mode is only run when the other two modes have failed to return a
     satisfactory plan."
   - Win and loss conditions are learned. DOC ("Model learning: Bayesian inference"): "For the termination rules we
     maintain a superset of possible explanations, which the planner tries to simultaneously satisfy." DOC
     ("Exploration"): "the only states that are informative about termination rules for any hypothesis are ones where
     count(c_j)==0 for some class c_j."
   - What is carried forward. The model posterior is conditioned on all observed states and actions (Eq. 1). DOC
     (Extended Data Figure 1 caption): "The agent's knowledge generalizes to any board layout that contains the same
     object types." INFERENCE: the learned model therefore survives a level restart; the text does not say so in those
     words. After a restart EMPA plans afresh with a doubled budget; there is no stored action prefix and no replay.
   - Start-of-level behaviour. DOC ("Planning: prediction-error monitoring and re-planning"): "the agent waits for a
     small number of time-steps before attempting to move in a new game, and at the beginning of a new level ... We set
     these waiting thresholds at 15 and 5 steps".
   - Over-exploration relative to humans. DOC (main text): "EMPA doesn't know that games almost always have exactly one
     win condition, so after finding one way to win a game it may continue to explore new ways of winning, whereas
     humans tend to win more efficiently by exploiting a single already-known win condition."
   - Metric and repeats. DOC: learning efficiency κ is defined as (levels completed / levels in game) × (levels
     completed / steps to completion) (written out from the formula);
     "we use agent steps, rather than environment steps, as our metric"; "Results reported for EMPA were averaged over
     ten runs with different random seeds"; Figure 3 shows "bootstrapped 95% confidence intervals for 10 runs".
   - Ablation detail. DOC ("EMPA ablations: exploration"): a variant "re-sets the long-term planning node budget to its
     initial value after any level forfeit." "Level forfeit" is not defined elsewhere in the text.
3. Usable without training: yes, as rules, more than any other document here. (a) An escalation ladder before a reset.
   (b) "Lost twice in the same way" as a stuck signal; it needs a definition of "same way". (c) A static board means
   waiting cannot help. (d) More deliberation budget after a restart. (e) Novelty over an abstraction that ignores
   random and short-lived elements. (f) Per-step comparison of observed and expected state while executing a stored
   plan. Does not transfer: EMPA's triggers rest on a planner searching a simulator of its own learned model, and the
   harness has no simulator; EMPA is given the object-level state and a restricted hypothesis space; the text does not
   charge a restart as an action, whereas RESET costs an action in ARC-AGI-3.

### DreamCoder — arXiv 2006.08381 (v1), "DreamCoder: Growing generalizable, interpretable knowledge with wake-sleep Bayesian program learning"
1. What it is: program induction with a learned library and a neural search guide. Read: abstract, introduction, start
   of the wake/sleep overview. Skipped: the rest (keyword search only).
2. Recovery: nothing. No environment, episodes or actions. "Replay" means retraining on solved tasks.
3. Usable: no.

### CodeIt — arXiv 2402.04858 (v2), "CodeIt: Self-Improving Language Models with Prioritized Hindsight Replay"
1. What it is: a language model trained iteratively to write programs for static ARC tasks, with hindsight relabeling.
   Read: abstract, introduction, Section 2. Skipped: experiments, related work, appendices (keyword search only).
2. Recovery: nothing. Static input-output grid tasks ("three attempts or fewer"), not interactive games. "Replay" is a
   training buffer. The method fine-tunes the model.
3. Usable: no. It requires weight updates.

### Combinatorial Sketching for Finite Programs — ASPLOS 2006 (author copy PDF, 12 pages)
1. What it is: program synthesis by filling holes in a partial program with a SAT-based synthesize-and-verify loop.
   Read: abstract and introduction (pages 1 to 2). Skipped: the rest (keyword search only). Part of the PDF text layer
   is garbled (author e-mail line), the body is readable. The publisher page was not tried because the author copy
   worked.
2. Recovery: nothing. DOC (Introduction): "Our solver for this problem uses a counterexample-driven iteration over a
   synthesize-verify loop built from two communicating SAT solvers."
3. Usable: no.

---

## 3. What this set does not provide

- No document makes the reset an action with a price that the agent weighs against its remaining budget.
- No document replays a stored action sequence to regain a state after a reset or a loss.
- No document reports human restart counts or timing. EMPA gave humans a restart option and reports nothing on its use.
- No document measures anything like dead-end loss (actions between last progress and the reset).
- Every learned mechanism here (recurrent hidden state, task posterior, world model, value network, fine-tuned
  language model) needs training on a task distribution and so cannot be used with frozen weights on unseen games.
