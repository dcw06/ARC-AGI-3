# Textbook notes for the recovery study (reset / undo / replay)

Reader notes on four textbooks, read for one question: what do they say that bears on deciding when to reset a level or game, when to undo, and how to get back to the furthest state reached, under a fixed action budget, in an unknown deterministic-looking environment.

## 0. Access, method, conventions

| Book | What was obtained | Status |
|---|---|---|
| Sutton and Barto, *Reinforcement Learning: An Introduction*, 2nd ed. | Full PDF from http://incompleteideas.net/book/RLbook2020.pdf (548 PDF pages). Text copy at `library/sb_rlbook/text.txt`. | Read (selected sections). Book page = PDF page minus 22. |
| Kochenderfer, Wheeler, Wray, *Algorithms for Decision Making* | Full PDF (700 PDF pages; the landing-page link redirects to a file host, fetched from there). Text at `library/dm_book/text.txt`. Build dated 2026-09-20 in the page footer. | Read (selected sections). Book page = PDF page minus 22. |
| Russell and Norvig, *AIMA*, 4th US ed. | Only the public files on aima.cs.berkeley.edu: contents with subsections (`contents.html`), `figures.pdf` (all figure captions and pseudocode figures), `algorithms.pdf` (pseudocode), `Index.pdf`, `Bibliography.pdf`, preface (`newchap00.pdf`); plus the public exercise site (aimacode.github.io/aima-exercises) and the aimacode pseudocode repository. | **Body text NOT read** (not freely available). Section titles, page numbers, figure captions, pseudocode, index entries and bibliography entries are verified. Everything else about this book is labelled "from memory, not verified". |
| LaValle, *Planning Algorithms* | Full PDF `booka4.pdf` (two book pages per PDF sheet). Text at `library/lavalle_book/text.txt`. | Read (selected sections). Page numbers below are the book's own running-header page numbers. |

All paths are under ``.

Conventions used below:

- **[BOOK]** a statement of the book, quoted or closely paraphrased, with section and page.
- **[INFERENCE]** my reading of what it means for the study. Not in the book.
- **[MEMORY]** what I recall of Russell and Norvig's body text. Not verified against the text.
- Quotes are exact except that I restored characters the PDF-to-text step dropped: ligatures (fi, ff), missing spaces in Kochenderfer, minus signs, and Greek letters in two Sutton and Barto formulas (noted where it happens). PDF page rendering was not available in this environment, so formulas were checked against the text layer only.
- Word searches that returned nothing are reported as such; they are searches of the text layer, so a concept expressed in other words could have been missed.

---

## 1. Sutton and Barto (2nd ed., 2018/2020)

### Sections read

- 2.1 A k-armed Bandit Problem (pp. 25–27); 2.6 Optimistic Initial Values (pp. 34–35); 2.7 Upper-Confidence-Bound Action Selection (pp. 35–36); 2.10 Summary and bibliographical remarks (pp. 42–45)
- 3.1 Example 3.3 Recycling Robot (pp. 52–53); 3.3 Returns and Episodes (pp. 54–56, including Exercise 3.7); 3.4 Unified Notation (p. 57); bibliographical remarks to 3.3–3.4 (p. 70)
- 5.2–5.4 exploring starts (pp. 96–100); Exercise 5.12 Racetrack (pp. 111–112)
- 6.4 Example 6.5 Windy Gridworld (p. 130); 6.5 Example 6.6 Cliff Walking (p. 132)
- 8.2 Dyna (pp. 161–166); 8.3 When the Model Is Wrong (pp. 166–168); 8.4 Prioritized Sweeping (opening, pp. 168–169); 8.6 Trajectory Sampling (pp. 174–177); 8.7 Real-time Dynamic Programming (pp. 177–180); 8.8 Planning at Decision Time (pp. 180–181); 8.9 Heuristic Search (pp. 181–183); 8.10 Rollout Algorithms (pp. 183–185); 8.11 Monte Carlo Tree Search (pp. 185–188); bibliographical remarks to 8.3 (p. 192)
- 10.1 Example 10.1 Mountain Car (pp. 244–246)
- 17.2 Temporal Abstraction via Options (pp. 461–464); 17.5 Remaining Issues, curiosity and safety paragraphs (pp. 474–475)

Word searches with no relevant hit in the whole book: "irreversib", "dead end", "dead-end", "backtrack", "value of information", "optimal stopping". "reset" and "restart" occur only in the senses quoted below.

### 1.1 Irreversible actions, dead ends, safe exploration

**Nothing direct.** The book has no definition of an irreversible action or a dead end and no impossibility result. What it has:

- [BOOK] Episodes always end and are always followed by a free reset. 3.3, p. 54: "Each episode ends in a special state called the terminal state, followed by a reset to a standard starting state or to a sample from a standard distribution of starting states. Even if you think of episodes as ending in different ways, such as winning and losing a game, the next episode begins independently of how the previous one ended."
- [BOOK] 3.4, p. 57: episode termination is modelled as "the entering of a special absorbing state that transitions only to itself and that generates only rewards of zero."
- [BOOK] The convergence result for real-time dynamic programming assumes there are no unavoidable dead ends. 8.7, p. 178: RTDP converges to a policy optimal on the relevant states "provided: (1) the initial value of every goal state is zero, (2) there exists at least one policy that guarantees that a goal state will be reached with probability one from any start state, (3) all rewards for transitions from non-goal states are strictly negative, and (4) all the initial values are equal to, or greater than, their optimal values". These are called "stochastic optimal path problems" (p. 178), with the example "minimum-time control tasks, where each time step required to reach a goal produces a reward of −1".
- [BOOK] Safety is named as an open problem, not treated. 17.5, p. 474: "A final issue that demands attention in future research is that of developing methods to make it acceptably safe to embed reinforcement learning agents into physical environments."
- [INFERENCE] Sutton and Barto's default framing hides the study's problem: a failed episode costs nothing extra and the reset is free and automatic. The study's setting (RESET is a chosen action that costs one action, and a game over inside a fixed budget) is not their episodic task.

### 1.2 When to stop and restart; reset as an action with a cost

The book never treats a voluntary reset as an action. Three places come close.

- [BOOK] A forced return to the start inside an episode, paid for in time steps. Exercise 5.12 (Racetrack), p. 111: "The rewards are −1 for each step until the car crosses the finish line. If the car hits the track boundary, it is moved back to a random position on the starting line, both velocity components are reduced to zero, and the episode continues." The same task is used in Example 8.6, p. 179.
- [BOOK] A forced return with an explicit penalty. Example 6.6 (Cliff Walking), p. 132: "Stepping into this region incurs a reward of −100 and sends the agent instantly back to the start." The example's finding is that the on-policy learner "learns the longer but safer path", while Q-learning's "online performance is worse" because it walks the edge and sometimes falls.
- [BOOK] A voluntary recovery action weighed against a forced, penalised one. Example 3.3 (Recycling Robot), p. 52: in the low-battery state the agent can "search", "wait" or "recharge"; "a period of searching undertaken when the energy level is low leaves it low with probability β and depletes the battery with probability 1−β. In the latter case, the robot must be rescued, and the battery is then recharged back to high. Each can collected by the robot counts as a unit reward, whereas a reward of −3 results whenever the robot has to be rescued." The transition table gives "recharge" from low to high with probability 1 and reward 0. (β restored; the symbol was dropped in the text layer.)
- [INFERENCE] The recycling robot is the smallest textbook MDP with the study's structure: continue (risk a forced, costly recovery) or recover now (certain, cheaper, but forgoes progress). The optimal choice there falls out of the ordinary Bellman optimality equation; no special stopping theory is used.
- [BOOK] Termination as part of an extended action. 17.2, p. 461: "To do this we need a notion of course of action that extends over many time steps and includes a notion of termination. A general way to formulate these two ideas is as a policy, π, and a state-dependent termination function, γ, as in GVFs. We define a pair of these as a generalized notion of action termed an option." p. 462: "Options effectively extend the action space." (π and γ restored.)
- [BOOK] Horizon effects in search: 8.9, p. 182: "if the search is all the way to the end of the episode, then the effect of the imperfect value function is eliminated, and the action determined in this way must be optimal."

### 1.3 Returning to a known state and continuing

- [BOOK] There is no treatment of returning to a frontier state after a reset. The nearest idea, starting episodes anywhere, is declared unavailable in real interaction. 5.2, p. 96: "The assumption of exploring starts is sometimes useful, but of course it cannot be relied upon in general, particularly when learning directly from actual interaction with an environment. In that case the starting conditions are unlikely to be so helpful."
- [BOOK] A stored table of verified transitions is the Dyna-Q model, valid under determinism. 8.2, p. 162–163: "The model-learning method is also table-based and assumes the environment is deterministic. After each transition S_t, A_t → R_{t+1}, S_{t+1}, the model records in its table entry for S_t, A_t the prediction that R_{t+1}, S_{t+1} will deterministically follow. Thus, if the model is queried with a state–action pair that has been experienced before, it simply returns the last-observed next state and next reward as its prediction." The pseudocode line (p. 164) reads "Model(S, A) ← R, S′ (assuming deterministic environment)".
- [BOOK] When such a model is wrong: 8.3, p. 166: "When the model is incorrect, the planning process is likely to compute a suboptimal policy." And: "In some cases, the suboptimal policy computed by planning quickly leads to the discovery and correction of the modeling error. This tends to happen when the model is optimistic".
- [BOOK] An option has a model with two parts, so a multi-step course of action can be planned with as if it were one action. 17.2, p. 462: "For options, the appropriate model is again of two parts, one corresponding to the state transition resulting from executing the option and one corresponding to the expected cumulative reward along the way." Equation (17.4), p. 463, is the Bellman equation over options, v_π(s) = Σ_ω π(ω|s) [ r(s, ω) + Σ_{s′} p(s′|s, ω) v_π(s′) ], and the text gives value iteration with options, v_{k+1}(s) = max over ω in Ω(s) of [ r(s, ω) + Σ_{s′} p(s′|s, ω) v_k(s′) ].
- [INFERENCE] "RESET then replay the verified prefix" is an option in this sense with a known model when the game is deterministic: reward part = −(1 + prefix length), transition part = the restored state with probability 1. That lets the reset decision be written as an ordinary comparison of option values (section 7 below).

### 1.4 Detecting lack of progress

- [BOOK] A policy that stops making progress never ends an episode; online methods notice within the episode. Example 6.5, p. 130: "Note that Monte Carlo methods cannot easily be used here because termination is not guaranteed for all policies. If a policy was ever found that caused the agent to stay in the same state, then the next episode would never end. Online learning methods such as Sarsa do not have this problem because they quickly learn during the episode that such policies are poor, and switch to something else."
- [BOOK] A mis-specified objective removes any pressure to make progress. Exercise 3.7, p. 56: a maze robot rewarded +1 for escaping and 0 otherwise, as an undiscounted episodic task, "is showing no improvement in escaping from the maze. What is going wrong?"
- [BOOK] Time since last tried, as an exploration bonus. 8.3, p. 168 (Dyna-Q+): "This agent keeps track for each state–action pair of how many time steps have elapsed since the pair was last tried in a real interaction with the environment." "if the modeled reward for a transition is r, and the transition has not been tried in τ time steps, then planning updates are done as if that transition produced a reward of r + κ√τ, for some small κ. This encourages the agent to keep testing all accessible state transitions and even to find long sequences of actions in order to carry out such tests. Of course all this testing has its cost". (κ, τ restored.)
- [BOOK] Visit counts in action selection. 2.7, p. 35–36: UCB selects argmax of Q_t(a) + c·sqrt(ln t / N_t(a)), where "N_t(a) denotes the number of times that action a has been selected prior to time t".
- [BOOK] Optimistic values push the agent away from visited states. Example 10.1, p. 246: "All the states visited frequently are valued worse than unexplored states, because the actual rewards have been worse than what was (unrealistically) expected. This continually drives the agent away from wherever it has been, to explore new states, until a solution is found."
- [BOOK] Limits of optimism: 2.6, p. 34–35: optimistic initial values are "a simple trick" whose "drive for exploration is inherently temporary".
- [BOOK] Worst-case exploration: bibliographical remarks 8.3, p. 192: E3 and R-max assume "all incompletely explored choices are assumed maximally rewarding and optimal paths are computed to test them"; they "are guaranteed to find a near-optimal solution in time polynomial in the number of states and actions. This is usually too slow for practical algorithms but is probably the best that can be done in the worst case."
- [BOOK] Novelty as intrinsic reward is named as future work: 17.5, p. 474: "intrinsic reward can, among other possibilities, signal the receipt of unexpected, novel, or otherwise interesting input".
- [INFERENCE] None of these is a stall detector that triggers a reset. They are ways of making revisits unattractive so that the agent leaves the region by ordinary actions.

### 1.5 Dependence of exploration on the remaining budget

- [BOOK] Stated once, clearly. 2.1, p. 26: "If you have many time steps ahead on which to make action selections, then it may be better to explore the nongreedy actions and discover which of them are better than the greedy action." And: "In any specific case, whether it is better to explore or exploit depends in a complex way on the precise values of the estimates, uncertainties, and the number of remaining steps."
- [BOOK] And then set aside. 2.1, p. 27: "In this book we do not worry about balancing exploration and exploitation in a sophisticated way; we worry only about balancing them at all."
- [BOOK] The exact finite-horizon solution is described in one paragraph and declared out of scope. 2.10, p. 43: "In the Bayesian setting it is even conceivable to compute the optimal balance between exploration and exploitation. ... This evolving distribution becomes the information state of the problem. Given a horizon, say of 1000 steps, one can consider all possible actions, all possible resulting rewards, all possible next actions, all next rewards, and so on for all 1000 steps. ... But the tree of possibilities grows extremely rapidly ... It is generally not feasible to perform this immense computation exactly, but perhaps it could be approximated efficiently. This approach would effectively turn the bandit problem into an instance of the full reinforcement learning problem. ... But that is a topic for research and beyond the scope of this introductory book." The Gittins index is mentioned in the same summary (p. 43) as tractable "in certain important special cases" and as not generalising "to the full reinforcement learning problem".
- [BOOK] The book's own task taxonomy is not finite-horizon. Bibliographical remarks 3.3–4, p. 70: the MDP literature distinguishes "(1) finite-horizon tasks, in which interaction terminates after a particular fixed number of time steps; (2) indefinite-horizon tasks ...; and (3) infinite-horizon tasks ... Our episodic and continuing tasks are similar to indefinite-horizon and infinite-horizon tasks, respectively".

### 1.6 Formal framing useful for a priced-recovery rule

- Bellman optimality over an action set that includes a recovery action (Example 3.3 is the worked case).
- Options with termination and a two-part model, and value iteration over options (17.2, pp. 461–463).
- Minimum-time (stochastic shortest path) formulation with −1 per step and the condition that a goal-reaching policy exists (8.7, p. 178).
- Decision-time planning and rollouts for estimating the value of each alternative from the current state (8.8–8.11). 8.10, p. 184: "the aim of a rollout algorithm is to improve upon the rollout policy; not to find an optimal policy." 8.11, p. 185: MCTS "can be effective for single-agent sequential decision problems if there is an environment model simple enough for fast multistep simulation." [INFERENCE] These need a model to simulate with; with unknown rules the agent has only its learned or hypothesised model.

---

## 2. Kochenderfer, Wheeler and Wray (2022)

### Sections read

- 1.1 and 1.6.3 (pp. 1–2, 15) for the book's four kinds of uncertainty; Part III opening (p. 297)
- 6.6 Value of Information (pp. 119–122)
- 7.1 Markov Decision Processes (pp. 133–136)
- Chapter 9 Online Planning: 9.1 Receding Horizon Planning (pp. 181–182), 9.2 Lookahead with Rollouts (p. 183), 9.3 Forward Search (pp. 183–185), 9.5 Sparse Sampling (p. 187), 9.6 Monte Carlo Tree Search (pp. 187–197), 9.7 Heuristic Search (p. 197), 9.8 Labeled Heuristic Search (pp. 197–200), 9.9 Open-Loop Planning (pp. 200–208), 9.10 Summary (pp. 208–209)
- Chapter 15 Exploration and Exploitation, all (pp. 299–315, including exercise solutions)
- 16.1 (p. 317), 16.3 Exploration (pp. 321–325), 16.4 opening (p. 326), 16.5 Bayes-Adaptive MDPs (pp. 329–330), 16.6 Posterior Sampling (pp. 330–331), 16.7 Summary (p. 332)
- 21.1 QMDP paragraph on information gathering (p. 429)
- Appendix E.1 Search Problems (p. 599); Appendix F.7 Crying Baby (pp. 615–617) and F.8 Machine Replacement (pp. 617–619)

Word searches with no relevant hit: "irreversib", "dead end", "dead-end", "backtrack", "unrecoverable". "reset" and "restart" occur only in unrelated senses (random restart in structure search; a simulation that "resets to the initial state every 10 steps" in a multiagent example, p. 525).

### 2.1 Irreversible actions, dead ends, safe exploration

**Nothing.** The book has no treatment of irreversible actions, dead ends, or exploring safely. The only neighbouring remarks:

- [BOOK] E.1, p. 599: "When there are no valid actions, the state is considered to be absorbing and yields zero reward for all future time steps. Goal states, for example, are typically absorbing."
- [BOOK] 9.1, p. 181: "In other problems, greater planning depths may be necessary so that our planner can be driven toward goals or away from unsafe states".

### 2.2 When to stop and restart; value of information; reset as an action

- [BOOK] Value of information, definition. 6.6, p. 121, equation (6.9): VOI(O′ | o) = ( Σ_{o′} P(o′ | o) EU*(o, o′) ) − EU*(o). "In other words, the value of information about a variable is the increase in expected utility if that variable is observed."
- [BOOK] 6.6, p. 121: "The value of information is never negative. The expected utility can increase only if additional observations can lead to different optimal decisions. If observing a new variable O′ makes no difference in the choice of action, then EU*(o, o′) = EU*(o) for all o′, in which case equation (6.9) evaluates to 0."
- [BOOK] A stopping rule for information gathering. 6.6, p. 122: "If there are costs associated with making different observations, then these costs are subtracted from the value of information when determining which variable to observe. The process continues until it is no longer beneficial to observe any more variables. The optimal action is then chosen. This greedy selection of observations is only a heuristic; it may not represent the truly optimal sequence of observations. The optimal selection of observations can be determined by using the techniques for sequential decision making introduced in later chapters."
- [BOOK] A costly restore-to-known-good action, with a horizon-dependent optimal policy. Appendix F.8, pp. 617–619 (machine replacement, a POMDP with states = number of failed components): the four actions are manufacture, examine, "interrupt, interrupt production, inspect, and replace failed components", and "replace, replace both components after interrupting production." Costs, p. 619: "Interrupting the line costs 0.5 to inspect the machine, causes no product to be made, and incurs a cost of 1 for each broken component. Simply replacing both components always incurs a cost of 2, but it does not have an inspection cost." p. 617: "The optimal policy for certain horizons even has disjoint regions in which the same action is optimal". p. 619: "Optimal policies for increasing horizons are shown in figure F.12."
- [INFERENCE] Machine replacement is the closest thing in the four books to "a reset as a priced action chosen under uncertainty about whether the current state is bad". Its lesson for the study: the optimal reset region depends on both the belief that the state is bad and the number of steps left, and is found by solving the sequential problem, not by a fixed threshold.
- [BOOK] Whether an information-gathering action is worth taking depends on the horizon. Appendix F.7, p. 617 (figure F.10 caption): "This infinite horizon solution does not recommend singing for any belief state. As shown in figure 20.3, it is optimal to sing in some finite-horizon versions of this problem." 21.1, p. 429: the QMDP approximation can "poorly approximate the value of information-gathering actions, which are actions that significantly reduce the uncertainty in the state."
- [BOOK] Commit rules for bandits. 15.3, p. 303: "Another strategy is explore-then-commit exploration (algorithm 15.4), where we select actions uniformly at random for the first k time steps. From that point on, we choose a greedy action. Large values for k reduce the risk of committing to a suboptimal action, but we waste more time exploring potentially suboptimal actions."
- [BOOK] Planning-depth effect. Example 9.1, p. 182: with depth 10 the planner advises only within 10 s of collision, which "compromises safety"; "There is no motivation to plan deeper than d = 40".

### 2.3 Returning to a known state and continuing

- [BOOK] No treatment of backtracking, of the cost of returning, or of replay in the study's sense. (17.7 "Experience Replay" is about reusing stored transitions for learning updates and is unrelated.)
- [BOOK] A stored action sequence is an open-loop plan. 9.9, p. 200: "Open-loop plans can be represented as a sequence of actions up to a depth d." p. 203: "This type of planning gains this efficiency by not accounting for future information." Example 9.9 (p. 203) shows an open-loop plan worth 20 against a closed-loop plan worth 30 when one transition is stochastic. 9.9.1, p. 204: under "deterministic dynamics" the plan is exact; "Replanning after every step can help compensate for stochasticity or unexpected events."
- [BOOK] Receding horizon. 9.1, p. 181: "we plan from the current state to a maximum fixed horizon or depth d. We then execute the action from our current state, transition to the next state, and replan."
- [INFERENCE] Automatic replay of a verified prefix is open-loop execution. Kochenderfer supports it exactly when the dynamics are deterministic, and points to checking the state after each step otherwise.

### 2.4 Detecting lack of progress

- [BOOK] Visit counts. 9.6, p. 189, equation (9.1): Q(s, a) + c·sqrt(log N(s) / N(s, a)), "where N(s) = Σ_a N(s, a) is the total visit count to s"; "With N(s, a) in the denominator, the exploration bonus is higher for actions that have not been tried as frequently."
- [BOOK] Under-explored state–action pairs. 16.3, p. 323 (R-MAX): "State-action pairs with fewer than m visitations are considered underexplored." Their reward is set to r_max and they are modelled as self-loops (equations 16.3–16.4), so "underexplored states have value r_max/(1 − γ), providing an incentive to explore them."
- [BOOK] Why per-state exploration rules are not enough. 16.3, p. 323: "A limitation of the exploration strategies discussed in the previous chapter is that they do not reason about exploring actions from states besides the current one. For instance, we might want to take actions that bring ourselves into an area of the state space that has not been explored."
- [BOOK] A zero-information test: the value-of-information statement in 6.6, p. 121, quoted above.
- [INFERENCE] The R1 trigger (no new state hash and no memory change for n actions) says that neither the state nor the belief has moved. In the Bayes-adaptive model below, that is the pair (s, b) cycling. The book has no such detector; it has the ingredients (counts, belief state, zero value of information).

### 2.5 Dependence of exploration on the remaining budget or horizon

This is where the book is strongest.

- [BOOK] 7.1, p. 135: "In finite horizon problems, however, it may be beneficial to select a different action depending on how many time steps are remaining. For example, when playing basketball, it is generally not a good strategy to attempt a half-court shot unless there are only a couple of seconds remaining in the game. We can make stationary policies account for time by incorporating time as a state variable."
- [BOOK] The bandit is posed with a known horizon. 15.1, p. 299: "Pulling an arm costs nothing, but we have only h pulls. A bandit problem can be framed as an h-step MDP with a single state, n actions, and an unknown, stochastic reward function R(s, a)".
- [BOOK] Optimal exploration for a known horizon by dynamic programming over belief states. 15.5, p. 306: the win/loss counts "represent a belief state"; "We can construct an MDP whose states are vectors of length 2n that represent the agent's belief over the n-armed bandit problem. Dynamic programming can be used to solve this MDP to obtain an optimal policy". Equation (15.6), p. 308, gives Q* as posterior win probability times (1 + U* of the updated counts) plus loss probability times U* of the updated counts. p. 309: "We can compute Q* for the entire belief space, as we have assumed a finite horizon h. We start with all terminal belief states with Σ_a(w_a + ℓ_a) = h, where U* = 0. We can then work backward". "Although this dynamic programming solution is optimal, the number of belief states is O(h^{2n})."
- [BOOK] The infinite-horizon discounted version has the Gittins index. 15.5, p. 309: it "can be solved efficiently using the Gittins allocation index, which can be stored as a lookup table".
- [BOOK] 15.7, p. 311: "Dynamic programming can be used to derive optimal exploration strategies for finite horizons, but these strategies can be expensive to compute."
- [BOOK] Tuned heuristics change with the horizon. Solution to Exercise 15.1, pp. 311–312: "the effectiveness of the parameterization depends on the problem horizon, so several different depths are shown"; "Quantile exploration performs better with longer horizons".
- [BOOK] Exploration rate should fall over time. 15.3, p. 303: "The ε-greedy method maintains a constant amount of exploration, despite there being far more uncertainty earlier in the interaction with the bandit than later."

### 2.6 Formal framing useful for a priced-recovery rule

- [BOOK] Unknown rules as a known, larger MDP. 16.5, p. 329: "We can formulate the problem of acting optimally in an MDP with an unknown model as a higher-dimensional MDP with a known model. This MDP is known as a Bayes-adaptive Markov decision process". "A state in a Bayes-adaptive MDP is a pair (s, b) consisting of the current state s in the base MDP and a belief state b." Equation (16.10): U*(s, b) = max_a ( R(s, a) + γ Σ_{s′} P(s′ | s, b, a) U*(s′, τ(s, b, a, s′)) ), where τ is the deterministic Bayes update of the belief. p. 330: "We can, however use the approximation methods of chapter 8 or the online methods of chapter 9."
- [BOOK] 16.4, p. 326: "Bayesian methods balance exploration and exploitation without having to rely on heuristic exploration policies." 16.6, p. 330: posterior sampling as the cheap approximation: "we draw a sample θ from the current belief b and then solve for the best action, assuming that θ is the true model."
- [BOOK] Time as a state variable (7.1, p. 135, quoted above) and terminal rewards "by explicitly including the horizon in the problem state" (F.8 footnote, p. 617).
- [INFERENCE] Put together: hyper-state (s, b, actions left), RESET as one more action whose outcome is known, and the Bellman equation (16.10) with γ = 1 and a finite horizon. Section 7 writes this out.

### 2.7 Where "online planning" sits in this book (matters for the plan's citation)

- [BOOK] The book is organised around four kinds of uncertainty (1.1, p. 2): "outcome uncertainty, where the effects of our actions are uncertain, model uncertainty, where our model of the problem is uncertain, state uncertainty, where the true state of the environment is uncertain, and interaction uncertainty".
- [BOOK] Chapter 9 Online Planning is in Part II, where the model is known. Part III opening, p. 297: "In our discussion of sequential decision problems thus far, we have assumed that the transition and reward models are known. In many problems, however, these models are not known exactly, and the agent must learn to act through experience." Chapter 9 opening, p. 181: "This chapter discusses online planning methods that find actions based on reasoning about states that are reachable from the current state." Rollouts and MCTS there use "a generative model" (9.2, p. 183).
- [INFERENCE] So "online planning under uncertainty [Kochenderfer et al.]" is accurate for outcome uncertainty with a known or simulable model (chapter 9). For unknown rules the right pointers are chapters 15–16, and 16.5 is the bridge (it says the online methods of chapter 9 can be applied to the Bayes-adaptive MDP). Chapter 22 does the same for state uncertainty.

---

## 3. Russell and Norvig (AIMA, 4th US ed., 2020/2021)

**Body text not read.** Verified material only: contents, index, figure captions, pseudocode, bibliography. Memory material is marked.

### What the public files establish

Sections and pages (from `contents.html`):

- 4.5 Online Search Agents and Unknown Environments, p. 134; 4.5.1 Online search problems, p. 135; 4.5.2 Online search agents, p. 137; 4.5.3 Online local search, p. 138; 4.5.4 Learning in online search, p. 140; chapter 4 bibliographical notes, p. 142
- 11.5 Planning and Acting in Nondeterministic Domains, p. 365; 11.5.3 Online planning, p. 371
- 16.6 The Value of Information, p. 547; 16.6.1 A simple example; 16.6.2 A general formula for perfect information, p. 548; 16.6.3 Properties of the value of information, p. 549; 16.6.4 Implementation of an information-gathering agent, p. 550; 16.6.5 Nonmyopic information gathering, p. 551
- 17.1.1 Utilities over time, p. 564; 17.2.4 Online algorithms for MDPs, p. 578; 17.3 Bandit Problems, p. 581; 17.3.1 Calculating the Gittins index, p. 583; 17.3.2 The Bernoulli bandit, p. 584; 17.3.3 Approximately optimal bandit policies, p. 585; 17.3.4 Non-indexable variants, p. 586
- 22.3 Active Reinforcement Learning, p. 797; 22.3.1 Exploration, p. 797; 22.3.2 Safe exploration, p. 799

Index entries (from `Index.pdf`): "dead end, 135"; "irreversible action, 136, 799"; "competitive ratio, 135"; "exploration ... safe, 136"; "safe exploration, 960"; "absorbing state, 799"; "mapping problem, 135"; "online search, 134, 134–141, 144–145"; "ONLINE-DFS-AGENT, 137"; "random walk, 138"; "optimism under uncertainty, 139"; "LRTA*, 139, 145, 365, 580"; "LRTA*-AGENT, 140"; "replanning, 365, 371–374, 383"; "execution monitoring, 372, 371–374, 383"; "value of information, 547–553, 557, 589, 1019"; "myopic policy, 550"; "treasure hunt, 551"; "horizon (in MDPs), 565"; "nonstationary policy, 565"; "horizon effect, 158"; "Gittins index, 583"; "stopping time, 583"; "exploration bonus, 585"; "upper confidence bound (UCB), 585"; "Thompson sampling, 586"; "bandit superprocess (BSP), 586"; "selection problem, 586"; "exploration function, 799, 802"; "optimistic prior, 798"; "metareasoning, 173"; "value of computation, 1019". The index has **no entry** for "optimal stopping", "secretary problem" or "safely explorable".

Figure captions and pseudocode (from `figures.pdf` and `algorithms.pdf`), exact:

- Figure 4.18: "A simple maze problem. The agent starts at S and must reach G but knows nothing of the environment."
- Figure 4.19: "(a) Two state spaces that might lead an online search agent into a dead end. Any given agent will fail in at least one of these spaces. (b) A two-dimensional environment that can cause an online search agent to follow an arbitrarily inefficient route to the goal. Whichever choice the agent makes, the adversary blocks that route with another long, thin wall, so that the path followed is much longer than the best possible path."
- Figure 4.20 (ONLINE-DFS-AGENT): persistent tables "result, a table mapping (s, a) to s′", "untried, a table mapping s to a list of untried actions", "unbacktracked, a table mapping s to a list of states never backtracked to". Core lines: "if untried[s′] is empty then / if unbacktracked[s′] is empty then return stop / else a ← an action b such that result[s′, b] = POP(unbacktracked[s′]) / else a ← POP(untried[s′])". Caption: "An online search agent that uses depth-first exploration. The agent can safely explore only in state spaces in which every action can be “undone” by some other action."
- Figure 4.21: "An environment in which a random walk will take exponentially many steps to find the goal."
- Figure 4.22: "Five iterations of LRTA* on a one-dimensional state space. Each state is labeled with H(s), the current cost estimate to reach a goal, and every link has an action cost of 1."
- Figure 4.23 (LRTA*-AGENT): "H[s] ← min over b in ACTIONS(s) of LRTA*-COST(s, b, result[s, b], H)"; "LRTA*-COST ... if s′ is undefined then return h(s) else return problem.ACTION-COST(s, a, s′) + H[s′]". Caption: "LRTA*-AGENT selects an action according to the values of neighboring states, which are updated as the agent moves about the state space."
- Figure 11.12: "At first, the sequence “whole plan” is expected to get the agent from S to G. The agent executes steps of the plan until it expects to be in state E, but observes that it is actually in O. The agent then replans for the minimal repair plus continuation to reach G."
- Figure 16.8: "Three generic cases for the value of information. In (a), a1 will almost certainly remain superior to a2, so the information is not needed. In (b), the choice is unclear and the information is crucial. In (c), the choice is unclear, but because it makes little difference, the information is less valuable."
- Figure 16.9 (INFORMATION-GATHERING-AGENT): "j ← the value that maximizes VPI(E_j) / C(E_j); if VPI(E_j) > C(E_j) then return Request(E_j) else return the best action from D". Caption: "Design of a simple, myopic information-gathering agent. The agent works by repeatedly selecting the observation with the highest information value, until the cost of the next observation is greater than its expected benefit."
- Figure 17.12: "(a) A simple deterministic bandit problem with two arms. ... (b) A more general case of the bandit in (a), where the first arm gives an arbitrary sequence of rewards and the second arm gives a fixed reward λ."
- Figure 17.13: "(a) The reward sequence M = 0, 2, 0, 7.2, 0, 0, 0, . . . augmented with a choice to switch permanently to a constant arm M_λ at each point. (b) An MDP whose optimal value is exactly equivalent to the optimal value for (a), at the point where the optimal policy is indifferent between M and M_λ."
- Figure 22.6: a greedy ADP agent "converges quickly, after just eight trials, to a suboptimal policy". Figure 22.8 (Q-LEARNING-AGENT) keeps "N_sa, a table of frequencies for state–action pairs" and selects "argmax_{a′} f(Q[s′, a′], N_sa[s′, a′])" with an exploration function f.

Bibliography (from `Bibliography.pdf`) contains the following works. The page numbers are from the author index, which lists authors, not works, so the match of page to work is my reading (chapter 4 notes are pp. 142–145, chapter 17 notes pp. 596–598, chapter 22 notes pp. 819–821): Deng and Papadimitriou (1990) "Exploring an unknown graph" (Deng indexed at p. 144); Papadimitriou and Yannakakis (1991) "Shortest paths without a map" (Yannakakis at p. 144); Korf (1990) "Real-time heuristic search" (Korf at p. 145); Koenig (2000) "Exploring unknown environments with real-time search or reinforcement learning" and Koenig (2001) "Agent-centered search" (Koenig at p. 145); Sturtevant and Bulitko (2016) "Scrubbing during learning in real-time heuristic search" (Bulitko at p. 145); Katehakis and Veinott (1987) "The multi-armed bandit problem: Decomposition and computation" (Katehakis at p. 597 only); Ferguson (2001) "Optimal Stopping and Applications" (Ferguson is indexed at pp. 176, 597, 748 for four different works; p. 597 is the chapter 17 notes and is the likely place for this one); Hans et al. (2008) "Safe exploration for reinforcement learning" (Hans at p. 821 only).

Public exercises (aimacode exercise site, chapter "advanced search"), relevant items: an exercise framing a 3×3 unknown maze as offline search in belief-state space, ending "interleaving of search and execution is not strictly necessary even in unknown environments"; Exercise 16: "Like DFS, online DFS is incomplete for reversible state spaces with infinite paths."; Exercise 17: "Relate the time complexity of LRTA* to its space complexity."

### 3.1 Irreversible actions, dead ends, safe exploration

Verified: the topics are in 4.5.1 (dead end p. 135, competitive ratio p. 135, irreversible action p. 136, safe exploration p. 136) and 22.3.2 (irreversible action and absorbing state p. 799); the impossibility claim in the Figure 4.19 caption ("Any given agent will fail in at least one of these spaces"); the adversary construction in 4.19(b); and the restriction in the Figure 4.20 caption.

[MEMORY] (4.5.1, wording approximate) An online search agent knows only the legal actions in a state, the step cost once the outcome is known, and the goal test; "the agent cannot determine RESULT(s, a) except by actually being in s and doing a." The competitive ratio compares the agent's actual path cost with the cost of the best path had it known the space in advance. A dead end is a state from which no goal state is reachable. "In general, no algorithm can avoid dead ends in all state spaces", shown by an adversary argument on the two spaces of Figure 4.19(a), which look identical until the agent has committed. Some actions are irreversible, leading to a state from which no action leads back. A state space is "safely explorable" if some goal state is reachable from every reachable state; spaces with only reversible actions, such as mazes and the 8-puzzle, are safely explorable. Even in safely explorable environments no bounded competitive ratio can be guaranteed if there are paths of unbounded cost, so performance is usually stated in terms of the size of the whole state space.

[MEMORY] (4.5.3) LRTA* "is guaranteed to find a goal in any finite, safely explorable environment"; it is not complete for infinite spaces; it "can explore an environment of n states in O(n²) steps in the worst case".

[MEMORY] (22.3.2) The earlier exploration discussion assumed the agent may explore freely. In real settings many actions are irreversible, and in the worst case the agent enters an absorbing state where no action has any effect and no reward is received. The section discusses Bayesian reinforcement learning (a prior over models, the exploration problem as a belief-state problem) and robust-control style criteria that avoid policies that could be disastrous under some plausible model.

### 3.2 When to stop and restart; value of information; reset as an action

Verified: the myopic information-gathering stopping rule (Figure 16.9 and caption); the three cases of Figure 16.8; the existence of 16.6.5 on nonmyopic information gathering with a "treasure hunt" problem (p. 551); the Gittins index with a "stopping time" (p. 583) and the construction of Figure 17.13; that Ferguson's optimal-stopping text is in the bibliography (its citation is probably in the chapter 17 notes, p. 597); that the index has no "optimal stopping" entry.

[MEMORY] (16.6.2) VPI(E_j) = ( Σ over values e_j of P(E_j = e_j) · EU(best action given e_j) ) − EU(best action now). "Information has value to the extent that it is likely to cause a change of plan and to the extent that the new plan will be significantly better than the old plan." Properties: nonnegative in expectation, not additive, order-independent.

[MEMORY] (17.3) The Gittins index of an arm is the maximum over stopping times of expected discounted reward up to the stopping time divided by expected discounted time; pulling the arm with the highest index is optimal for the discounted infinite-horizon bandit. 17.3.1 computes the index by turning the arm into an MDP in which, at every step, the agent may continue or go back to the arm's initial state (the "restart" formulation of Katehakis and Veinott), which I believe is what Figure 17.13(b) shows. The verified caption says only that (b) is "An MDP whose optimal value is exactly equivalent" at the indifference point.

[MEMORY] (4.5.3) Hill climbing is already an online algorithm, but "random restarts cannot be used, because the agent cannot teleport itself to a new start state" (wording approximate; the 3rd edition says "transport"). A random walk is offered instead and shown to be exponentially slow in Figure 4.21.

[INFERENCE] This last point matters for the plan's wording. Russell and Norvig's online search has **no reset**. Their agent must walk back. The study's game has a reset that costs one action plus the replay. So the book supplies the problem statement (unknown deterministic environment, dead ends, irreversible actions, competitive ratio) but not the decision the study is about. The nearest decision-theoretic device in the book is the continue-or-restart MDP used for the Gittins index, and it is used there for a different purpose.

[MEMORY] "Horizon effect" (index p. 158) is the game-search sense: a depth-limited search pushes an unavoidable loss beyond its horizon with delaying moves. It is not about finite budgets.

### 3.3 Returning to a known state and continuing

Verified: ONLINE-DFS-AGENT backtracks physically using the `unbacktracked` table and stops when it is empty; it needs every action to be undoable (Figure 4.20 caption); replanning from an unexpected state as "minimal repair plus continuation" (Figure 11.12 caption); execution monitoring at pp. 371–374.

[MEMORY] (4.5.2) Offline algorithms "explore their model of the state space, while online algorithms explore the real world"; A* can jump between distant nodes because expansion is simulated, whereas "an online algorithm can discover successors only for a state that it physically occupies", which is why depth-first order is natural. When all actions in a state have been tried, "the agent has to backtrack in the physical world". In the worst case online DFS traverses every link exactly twice, which is optimal for exploration but can give an arbitrarily bad competitive ratio for goal finding; an online iterative-deepening variant fixes this, with a small constant ratio on uniform trees. Because of how it backtracks, ONLINE-DFS-AGENT "works only in state spaces where the actions are reversible"; more complex algorithms work in general spaces but none has a bounded competitive ratio.

[MEMORY] (11.5.3) Three levels of execution monitoring: action monitoring (check preconditions before each action), plan monitoring (check the remaining plan still works), goal monitoring (check whether a better set of goals is available). Repairing a plan back onto the original track is contrasted with replanning from scratch.

### 3.4 Detecting lack of progress

Verified: `untried` and `unbacktracked` bookkeeping; LRTA* cost estimates H(s) that are raised as states are revisited (Figure 4.22 shows five iterations escaping a local minimum on a line; pseudocode in Figure 4.23); "optimism under uncertainty" (p. 139); random walk exponentially slow (Figure 4.21); frequency table N_sa and exploration function in the reinforcement learning agent (Figure 22.8); the greedy agent that stops improving (Figure 22.6).

[MEMORY] (4.5.3) In LRTA*, untried actions are assumed to lead straight to the goal at the least possible cost h(s); this "optimism under uncertainty" pushes the agent toward untried actions, and repeated visits raise H in a local minimum until the agent leaves. (22.3.1) The exploration function is f(u, n) = R+ if n < N_e, else u: an optimistic value until a state–action pair has been tried N_e times.

### 3.5 Dependence on the remaining budget or horizon

Verified: "horizon (in MDPs), 565" and "nonstationary policy, 565" in 17.1.1.

[MEMORY] (17.1.1) With a finite horizon the optimal action in a state can depend on the time left, so the optimal policy is nonstationary. The 4×3 example: from (3,1) with 3 steps left the agent must head straight for the +1 state and risk the −1; with 100 steps left it can take the safe route.

[MEMORY] The Gittins result is for discounted infinite-horizon bandits; 17.3.3 covers regret bounds, UCB and Thompson sampling for the general case.

### 3.6 Formal framing

Verified building blocks: the VPI stopping rule (cost against expected benefit), the Gittins construction via an equivalent MDP, LRTA*'s learned cost-to-go H(s), nonstationary policies under finite horizons. [INFERENCE] LRTA*'s rule "move to the neighbour minimising step cost plus H" extends directly to an action set containing RESET with cost 1 and successor the level start (or, with replay, cost 1 + L and successor the restored state).

---

## 4. LaValle, *Planning Algorithms* (2006)

### Sections read

- 2.2 Searching for Feasible Plans (pp. 32–39, including iterative deepening p. 39); 2.3 Discrete Optimal Planning, 2.3.1–2.3.3 (pp. 43–56, selectively)
- 5.4.3 Randomized Potential Fields (pp. 225–226)
- 8.1 Motivation (pp. 369–371); 8.2.1 Defining a Feedback Plan (pp. 371–374); 8.2.2 Feedback Plans as Navigation Functions (pp. 375–376)
- Chapter 10 opening (pp. 495–496); 10.1.1 Model Definition (pp. 496–499); 10.1.3 A Plan and Its Execution (pp. 505–507); 10.2.1 Value Iteration, convergence issues and Example 10.6 (pp. 511–514); 10.4.1 Reinforcement learning, general philosophy (pp. 527–530)
- 12.1.1 The Information Space as a Big State Space (pp. 634–636); 12.2.1 passage on lazy search, reroute paths and information improvement (pp. 644–646); 12.3.1 Grid Problems, including maze searching (pp. 655–662); 12.3.2 Stentz's Algorithm D* (pp. 662–667); 12.3.3 Planning in Unknown Continuous Environments: bug algorithms, competitive ratios, lost-cow problem (pp. 667–673)
- 14.1 passage on symmetric systems (p. 794); 14.1.3.2 The region of inevitable collision (pp. 796–797)

Word searches with no hit: "value of information", "information gathering". "reset" and "restart" occur only inside the randomized potential field description.

### 4.1 Irreversible actions, dead ends, safe exploration

- [BOOK] Unreachable goals are encoded as infinite cost. 2.3.1, p. 44: plans "that do not reach X_G are penalized with infinite cost so that they are eliminated automatically in any optimization steps"; "L(π_K) = ∞ means not feasible". Example 2.5, p. 53: "Since d is not reachable from e, G*(e) = ∞."
- [BOOK] A navigation function marks dead ends and guarantees progress elsewhere. 8.2.2, p. 375: a potential function φ is a (feasible) navigation function if "1. φ(x) = 0 for all x ∈ X_G. 2. φ(x) = ∞ if and only if no point in X_G is reachable from x. 3. For every reachable state, x ∈ X \ X_G, the local operator produces a state x′ for which φ(x′) < φ(x)." p. 376: "The second condition requires that ∞ serves as a special indicator that the goal is not reachable from some state. The third condition means that the potential function has no local minima except at the goal. This means that the execution of the resulting feedback plan will progress without cycling and the goal region will eventually be reached."
- [BOOK] A finite penalty for failure is allowed. 10.1.1, p. 498: "For problems that involve probabilistic uncertainty, it is sometimes appropriate to assign a high, finite value for l_F(x_F) if x_F ∉ X_G, as opposed to assigning an infinite cost for failing to achieve the goal."
- [BOOK] Possibly reachable against guaranteed reachable. 10.2.1, p. 512: "To be possibly reachable from some initial state, there must exist a plan, π, for which there exists a sequence of nature actions that will lead the state into the goal set. To be guaranteed reachable, the goal must be reached in spite of all possible sequences of nature actions."
- [BOOK] Doomed states: the region of inevitable collision. 14.1.3.2, p. 796: "This is the set of states from which entry into X_obs will eventually occur, regardless of any actions that are applied. ... Clearly the robot is doomed." p. 797: "There may be large parts of the state space that are never worth exploring because they lie in X_ric. Unfortunately, there is no practical way at present to accurately determine whether states lie in X_ric." p. 796 also distinguishes the trapped case: a forward-only car "unable to back its way out of a dead-end alley" can avoid collision by stopping; "This case appears more like being trapped and technically does not fit under the definition of X_ric."
- [BOOK] Reversibility as a system property. 14.1, p. 794: a system is symmetric if any trajectory from x_I to x_G can be retraced in reverse; "it is possible for a symmetric system to reverse any motions. This is usually not possible for systems with drift."
- [BOOK] Competitive ratio, definition and a negative result. 12.3.3, p. 672, equation (12.28): the maximum over environments e of (cost of executing the plan that does not know e in advance) divided by (cost of executing the plan that knows e in advance). "Since E is infinite, many plans fail to produce a finite competitive ratio. The bug algorithms, while elegant, represent such an example. Imagine a goal that is very close, but a large obstacle boundary needs to be explored."
- [BOOK] The lost-cow problem. 12.3.3, pp. 672–673: "If the cow is told that the gate is exactly distance 1 away, then it can move one unit in one direction and return to try the other direction if the gate has not been found. The competitive ratio in this case ... is 3. What if the cow is told only that the gate is at least distance 1 away? In this case, the best strategy is a spiral search, which is to zig-zag back and forth while iteratively doubling the distance traveled in each direction ... The competitive ratio for this strategy turns out to be 9, which is optimal. This approach resembles iterative deepening, which was covered in Section 2.2.2."
- [INFERENCE] LaValle gives the vocabulary for the study's two kinds of bad state: a state from which the goal is unreachable (φ = ∞; "trapped") and a state from which game over is unavoidable (X_ric; "doomed"). He also says such states cannot in general be recognised in advance, which is the reason a detector plus a priced decision is needed instead of a test.

### 4.2 When to stop and restart

- [BOOK] A stop action exists in the formal model. 2.3, p. 43: "a termination action will be introduced, which intuitively indicates when it is time to stop the plan and fix the total cost." 2.3.2, p. 51: "Each U(x) contains the special termination action, u_T. If u_T is applied at x_k, then the action is repeatedly applied forever, the state remains unchanged, and no more cost accumulates."
- [BOOK] Discarding work and starting again from the root can be cheap. 2.2.2, p. 39 (iterative deepening): "If the goal is not found, then the previous work is discarded, and depth first is applied to find all states of distance i + 1 or less from x_I. ... once the commitment has been made to reach level i + 1, the cost of all previous iterations is negligible."
- [BOOK] A turn-back rule with a proven bound: the doubling strategy of the lost-cow problem (pp. 672–673, quoted above).
- [BOOK] Expected cost of a try-again loop. Example 10.6, p. 513: a plan whose transition graph has a cycle taken with probability 1/2 each time: "With probability 1/2, the cost to reach x_G is 3. With probability 1/4, the cost is 7. With probability 1/8, the cost is 11. Each time another cycle is taken, the cost increases by 4, but the probability is cut in half." The series gives G_π(x_I) = 3 + 4·Σ_{i≥1} 2^{−i} = 7. p. 514: "if nondeterministic uncertainty is used, then the value iterations do not converge because, in the worst case, nature will cause the state to cycle forever."
- [BOOK] A stall counter that escalates. 5.4.3, pp. 225–226 (randomized potential field planner, a three-mode machine): "After some number of tries (another parameter), if the LPM is unsuccessful at reducing g, then the mode is changed to random walk because the best-first search is stuck in a local minimum of g." "A parameter K determines the maximum number of attempted random walks (a reasonable value is K = 20 [71]). If best first fails after K random walks have been attempted, then the backtrack mode is entered. The backtrack mode selects a vertex at random from among the vertices in V that were obtained during a random walk. Following this, the counter is reset, and the mode is changed back to best first." p. 225: "The main drawback, however, was that the method involved many heuristic parameters that had to be adjusted for each problem."
- [INFERENCE] The randomized potential field planner is a planner searching a model, so its backtracking is free. It is still the closest textbook precedent for R1's design (count failures to improve, then force a different mode), and LaValle's verdict on it is a warning about the stall threshold: such thresholds are problem-specific.
- LaValle has **no** treatment of a reset as an action with a cost, and no value-of-information section.

### 4.3 Returning to a known state and continuing

This is where LaValle is most useful.

- [BOOK] The cost of returning is named and said to change the search problem. 12.2.1, pp. 645–646: "Previously, the search could continue from any state that has been explored previously without any additional cost. In the current setting, there are two issues: Reroute paths: Most search algorithms enable new states to be expanded from any previously considered states at any time. For the lazy approach, the robot must move to a state and apply an action to determine whether a new state can be reached. The robot is capable of returning to any previously considered state by using its odometric coordinates. This induces a cost that does not exist in the previous search problem. Rather than being able to jump from place to place in a search tree, the search is instead a long, continuous path that is traversed by the robot. Let the jump be referred to as a reroute path." p. 646: "The implication of these issues is that the search algorithm should take into account the cost of moving the robot and that the search graph is directed."
- [BOOK] Knowledge survives the return. 12.2.1, p. 646 ("Information improvement"): "even though the I-state may be different when returning to the same position, it will always be at least as good as the previous one. ... Information always improves in this version of the localization problem."
- [BOOK] Standard search assumes free jumps. 12.3.1, p. 660: with A* on an unknown grid "the reroute costs are not being taken into account. ... For the unfortunate robot that went first, a substantial amount of exploration steps might have been wasted because A* is not designed for exploration during execution. Even though the search algorithms in Section 2.2 assumed that the search graph was gradually revealed during execution, as opposed to being given in advance, they allow the current state in the search to jump around arbitrarily. In the current setting, this would require teleporting the robot to different parts of the environment." For map building: "A simple algorithm that solves the problem while avoiding excessive rerouting is depth-first search" (p. 660).
- [BOOK] Replanning as costs are discovered. 12.3.2, pp. 662–666: Stentz's D* "dynamically updates cost values as the cost terms are learned during execution" (Figure 12.18 caption); p. 665: "At any time during execution, the robot motions are optimal given the current information about the costs". p. 666: "it takes a guess and assumes that one particular environment in the nondeterministic I-state is the correct one. As cost mismatches are discovered ... the guess is changed".
- [BOOK] A bound that depends on being able to recall the path back. 12.3.3, pp. 668–669 (Bug1): after circling an obstacle the robot must "return to the point at which the goal was closest". Total distance is at most d + (3/2)·Σ p_i (equation 12.25). "This bound relies on the fact that the robot can always recall the shortest path along the boundary to the point from which it needs to leave. ... If this was not possible, then the 3/2 would have to be replaced by 2".
- [BOOK] Action sequences against feedback. Chapter 10 opening, p. 495: "feedback is required, as opposed to specifying a plan as a sequence of actions, which sufficed in Chapter 2. This was only possible because actions were predictable." 8.1, p. 370: even with a model that admits no uncertainty, "a feedback plan is constructed to ensure that it knows which action to apply, just in case it happens to be in some unexpected state during execution."
- [INFERENCE] The study's "return cost" is LaValle's reroute-path cost. A reset game changes its shape: the return to any state on the verified prefix costs 1 + (its depth), whatever the current state, including from a dead end. The Bug1 remark is direct support for storing the verified prefix: the bound is better when the way back is remembered. The chapter 10 and 8.1 passages say when blind replay is legitimate (predictable actions) and that the state should still be checked on the way.

### 4.4 Detecting lack of progress

- [BOOK] Track visited states or cycle forever. 2.2, p. 32: "To be systematic, the algorithm should keep track of states already visited; otherwise, the search may run forever by cycling through the same states. Ensuring that no redundant exploration occurs is sufficient to make the search systematic." p. 33: "Virtually any search algorithm is systematic, provided that it marks visited states to avoid revisiting the same states indefinitely."
- [BOOK] States with no new leads. 2.2.1, p. 33: "Dead: States that have been visited, and for which every possible next state has also been visited. ... In a sense, these states are dead because there is nothing more that they can contribute to the search; there are no new leads that could help in finding a feasible plan." "Alive: States that have been encountered, but possibly have unvisited next states." (This "dead" is not a dead end.)
- [BOOK] The cost of checking for repeats. 2.2.1, p. 34: "A good hashing scheme or another clever data structure can greatly alleviate this cost"; allowing repeated states risks that "the search may not terminate at all, even if the graph is finite."
- [BOOK] Progress as strict decrease of a potential: navigation-function condition 3 (p. 375–376, quoted above).
- [BOOK] Loop prevention with a remembered best. 12.3.3, p. 669 (Bug2): "As expressed so far, it is possible that infinite cycles occur. Therefore, a small modification is needed. The robot remembers the distance to the goal from the last point at which it departed from the boundary, and only departs from the boundary again if the candidate point that is closer to the goal."
- [BOOK] Loop prevention with very little memory. 12.3.1, pp. 660–661 (maze searching, Blum and Kozen): "It is important only to ensure that the robot does not become trapped in an infinite loop before covering all tiles. It was shown in [119] that any maze can be searched using space that is only logarithmic in the number of tiles."
- [BOOK] Stall counters: the randomized potential field planner (pp. 225–226, quoted above).
- [INFERENCE] R1's first condition (no new state hash) is LaValle's test for a search that has stopped being systematic: every recently reached state is already visited. R1's second condition (no memory change) corresponds to no change in the information state.

### 4.5 Dependence on the remaining budget or horizon

- [BOOK] 10.1.3, pp. 505–506: "For some problems, particularly when K is fixed at some finite value, a stage-dependent plan may be necessary. This enables a different action to be chosen for every stage, even from the same state. ... A stage-dependent plan is defined as π : X × K → U."
- [BOOK] 2.3.1, pp. 44–46: optimal fixed-length (K-stage) plans by backward value iteration, G*_k(x_k) = min over u_k of { l(x_k, u_k) + G*_{k+1}(x_{k+1}) } (equation 2.11); p. 46: "some states receive an infinite value only because they are not reachable; a (K − k)-step plan from x_k to X_G does not exist."
- [BOOK] 10.4.1, p. 530: "One of the main issues is exploration vs. exploitation. Some repetitive exploration of the state space is needed to gather enough data that reliably estimate the model. ... Focusing too much on exploration will not optimize costs. Focusing too much on exploitation may prevent useful solutions from being developed".
- LaValle has nothing specific on how exploration should change with the budget beyond the stage-dependent plan.

### 4.6 Formal framing

- [BOOK] Unknown environment as a known problem over information states. 12.1.1, p. 634–635: a problem with unknown state "can be converted using derived I-states into a problem under Formulation 10.1 ... by treating the I-space as a big state space in which each state is an I-state in the original problem formulation." 12.3.1, p. 655: the state is taken as "(p, d, e), in which e represents the particular environment that contains the robot."
- [BOOK] Cost-to-go recursions: deterministic (2.11), probabilistic (10.46): G*_k(x_k) = min over u_k of { l(x_k, u_k) + Σ_{x_{k+1}} G*_{k+1}(x_{k+1}) P(x_{k+1} | x_k, u_k) }.
- [BOOK] Geometric retry cost (Example 10.6).
- [BOOK] Worst-case yardstick: competitive ratio (12.28).

---

## 5. Synthesis by question

### Q1. Irreversible actions, dead ends, safe exploration

| Item | Source | Status |
|---|---|---|
| Dead end, irreversible action, competitive ratio as terms in online search | R&N 4.5.1, pp. 135–136 | location verified; definitions from memory |
| "Any given agent will fail in at least one of these spaces" (no algorithm avoids dead ends in all unknown spaces) | R&N Figure 4.19(a) caption | verified |
| Arbitrarily inefficient route even without dead ends (adversary with walls) | R&N Figure 4.19(b) caption | verified |
| Safe depth-first exploration needs every action to be undoable | R&N Figure 4.20 caption | verified |
| "Safely explorable" = a goal is reachable from every reachable state; LRTA* finds a goal in any finite safely explorable space, O(n²) steps | R&N 4.5.1, 4.5.3 | from memory |
| Safe exploration in reinforcement learning; absorbing states | R&N 22.3.2, p. 799 | location verified; content from memory |
| Goal unreachable ⇔ infinite cost-to-go; navigation function | LaValle 2.3.1 p. 44; 8.2.2 pp. 375–376 | verified |
| Doomed states (region of inevitable collision), not practically recognisable | LaValle 14.1.3.2 pp. 796–797 | verified |
| Competitive ratio definition; many plans have no finite ratio; lost cow 3 and 9 | LaValle 12.3.3 pp. 672–673 | verified |
| RTDP needs a policy that reaches the goal with probability one from every start | S&B 8.7 p. 178 | verified |
| Nothing | Kochenderfer | searched |

### Q2. When to stop a line and restart; reset as a priced action

- No book treats a voluntary reset to the start as an action with a cost in an exploration setting. This is a gap in all four.
- Closest models: S&B recycling robot (Example 3.3, p. 52); Kochenderfer machine replacement (F.8, pp. 617–619); R&N's continue-or-restart MDP for the Gittins index (17.3.1, memory; Figure 17.13 verified); S&B racetrack and cliff (forced return to start, pp. 111, 132).
- Stopping rules that exist: gather information while its value exceeds its cost (R&N Figure 16.9, verified; Kochenderfer 6.6, p. 122), both flagged as myopic or heuristic; doubling excursions for the lost cow (LaValle, p. 673), optimal with ratio 9; explore-then-commit (Kochenderfer 15.3, p. 303); stall counter then backtrack (LaValle 5.4.3, p. 226).
- Value of information: Kochenderfer equation (6.9), p. 121; R&N 16.6 (formula from memory). Not in S&B (no hit) or LaValle (no hit).

### Q3. Returning to a known state

- Physical backtracking and its cost: R&N 4.5.2 (pseudocode verified, analysis from memory); LaValle reroute paths (pp. 645–646) and "teleporting" (p. 660), verified.
- Remembering the way back improves the bound: LaValle Bug1, p. 669, verified.
- Replay as an open-loop plan, exact only under deterministic dynamics: Kochenderfer 9.9, pp. 200–204; LaValle chapter 10 opening, p. 495; S&B Dyna-Q deterministic model, pp. 162–164.
- Check the state while executing; repair when it diverges: LaValle 8.1, p. 370; R&N Figure 11.12 (verified) and execution monitoring pp. 371–374 (memory).
- Knowledge is kept across the return: LaValle p. 646.
- No book describes "reset, replay to the frontier, then explore" as a method.

### Q4. Detecting lack of progress

- Visited-state bookkeeping: LaValle 2.2 pp. 32–34 (verified); R&N `untried` and `unbacktracked` tables (verified).
- Counts and recency: S&B UCB p. 35, Dyna-Q+ p. 168; Kochenderfer UCB1 p. 189, R-MAX p. 323; R&N N_sa and exploration function (Figure 22.8 verified).
- Learned cost-to-go that rises on revisits: R&N LRTA* (Figures 4.22–4.23 verified; mechanism from memory); S&B Mountain Car p. 246.
- Monotone progress measures: LaValle navigation function p. 375; Bug2 p. 669.
- Stall counter with escalation: LaValle 5.4.3 p. 226.
- Zero value of information as a test: Kochenderfer p. 121.
- None of the books uses "the agent's memory did not change" as a signal. The nearest formal object is the belief or information state (Kochenderfer 16.5; LaValle 12.1.1).

### Q5. Budget or horizon dependence

- Principle: Kochenderfer 7.1 p. 135; LaValle 10.1.3 pp. 505–506; R&N 17.1.1 p. 565 (location verified, content from memory); S&B 2.1 p. 26 (one sentence).
- Worked treatment for exploration: Kochenderfer 15.1 and 15.5 (pp. 299, 306–309), Exercise 15.1 (pp. 311–312), F.7 and F.8 (horizon-dependent information gathering and replacement).
- Explicitly not treated: S&B (pp. 27, 43).

### Q6. Formal framing for priced recovery

- Bayes-adaptive MDP with (s, b): Kochenderfer 16.5, equation (16.10). Same idea: S&B "information state" p. 43; LaValle I-space as a big state space pp. 634–635.
- Budget as a state variable: Kochenderfer p. 135; LaValle stage-dependent plan p. 505.
- Reset-and-replay as an extended action with a known model: S&B options, 17.2, equation (17.4).
- Cost-to-go comparison with infinite cost for dead ends: LaValle (2.11), (10.46), navigation function; S&B stochastic optimal path problems p. 178.
- Expected cost with retries: LaValle Example 10.6.
- Value of information: Kochenderfer (6.9).

---

## 6. Check of the plan's two assertions

**Assertion A.** "The textbook treatment is online search with irreversible actions and dead ends [Russell and Norvig] and online planning under uncertainty [Kochenderfer et al.]"

- Russell and Norvig half: **supported as a pointer to the setting, with one correction.** 4.5 "Online Search Agents and Unknown Environments" (pp. 134–141) is the right section; the index puts "dead end" at p. 135 and "irreversible action" at pp. 136 and 799; the Figure 4.19 and 4.20 captions state the impossibility result and the reversibility requirement (verified). The correction: that section treats dead ends as something no agent can always avoid and then restricts attention to safely explorable spaces. It does not treat recovery, and its agent has no reset (memory: "random restarts cannot be used, because the agent cannot teleport itself to a new start state"). So it is the textbook treatment of the *problem*, not of the reset decision. Add 22.3.2 (safe exploration, p. 799) to the citation. A reader who checks the citation will not find reset-or-continue analysed there.
- Kochenderfer half: **only partly supported.** Chapter 9 "Online Planning" exists and covers receding-horizon planning, rollouts, forward search, MCTS, heuristic search and open-loop planning (pp. 181–209). But it sits in Part II, where "the transition and reward models are known" (p. 297); its uncertainty is outcome uncertainty. Unknown rules are Part III: chapter 15 and 16.3–16.6, with 16.5 linking back to chapter 9 (p. 330). And the book says nothing on irreversible actions, dead ends, resets or backtracking. Suggested wording: "online planning (Kochenderfer et al., ch. 9) and planning under model uncertainty (ch. 15–16, especially the Bayes-adaptive MDP of 16.5)".
- Missing from the sentence and arguably the best single source for the return-cost side: LaValle 12.2.1 and 12.3 (reroute paths, competitive ratio, lost cow), and 14.1.3.2 for doomed states.

**Assertion B.** "Exploration under a known horizon is standard material in Sutton and Barto and Kochenderfer et al."

- Kochenderfer: **supported.** 15.1 p. 299 ("we have only h pulls"; "an h-step MDP"), 15.5 pp. 306–309 (optimal finite-horizon exploration by dynamic programming over belief states), 15.7 p. 311, Exercise 15.1 pp. 311–312, and 7.1 p. 135 for the general principle.
- Sutton and Barto: **weak.** The book states the dependence in one sentence (2.1, p. 26) and sketches the finite-horizon Bayesian computation in one paragraph (2.10, p. 43), then says it does "not worry about balancing exploration and exploitation in a sophisticated way" (p. 27) and that the computation is "beyond the scope of this introductory book" (p. 43). Its tasks are episodic or continuing, not fixed-horizon (p. 70). Cite it as acknowledging the dependence, not as treating it. Better second citations for the principle: Russell and Norvig 17.1.1 (p. 565, nonstationary policies) and LaValle 10.1.3 (pp. 505–506, stage-dependent plans).

---

## 7. Proposed formal statement of the reset decision

Everything in this section is **[INFERENCE]** assembled from the cited pieces. No book states it.

### Setting

- One level with an unknown transition function f, treated as deterministic and fully observed. Level start s₀. Every action costs 1, RESET included. B actions remain.
- b: the agent's belief about the rules (its hypothesis memory).
- Verified prefix P = (a₁, …, a_L) with known intermediate states s₁, …, s_L. Any s_k on it can be restored at cost 1 + k (RESET, then k replayed actions).
- Undo, where the game has it, is one more action with cost 1 and a known successor; it is the k = (current depth − 1) case without the reset.

### Exact problem

A finite-horizon Bayes-adaptive MDP on (s, b, B) (Kochenderfer equation 16.10, with time as a state variable, 7.1 p. 135; LaValle's stage-dependent plan over the information space):

- U(s, b, 0) = 0
- U(s, b, B) = max of
  - for each ordinary action a: Σ_{s′} P(s′ | s, b, a) · [ r + U(s′, τ(s, b, a, s′), B − 1) ]
  - RESET: U(s₀, b, B − 1)

RESET leaves b unchanged: knowledge survives (LaValle p. 646).

Reset-and-replay to s_k is an option ω_k with a known model (S&B 17.2): cost 1 + k, lands in s_k with probability 1. Its value is U(s_k, b, B − 1 − k), defined only if B > 1 + k.

### Decision rule

Reset and replay to s_k if and only if

  max over k with B > 1 + k of U(s_k, b, B − 1 − k)  >  max over ordinary actions a of Q(s, b, B; a).

The restore point k is part of the decision. The furthest verified state is not automatically the best one (it may itself be past the mistake).

### Two usable reductions

1. **Cost-to-go form** (budget not binding; objective = fewest actions to finish the level). Let G(x) be the expected actions to finish from x under the agent's continuation policy and belief, with G(x) = ∞ if x is a dead end (LaValle's φ = ∞). Reset to s_k iff

  G(s) > 1 + k + G(s_k).

 If the agent only has a probability q that the current line is dead, and W is the expected number of further actions wasted before that is recognised or the game ends, then continuing costs (1 − q)·G_live(s) + q·(W + 1 + k + G(s_k)), and the rule becomes

  G_live(s) + (q / (1 − q))·W  >  1 + k + G(s_k).

 W is the study's dead-end loss; 1 + k is its return cost. The stall detector of R1 is evidence that raises q.

2. **Budget form** (objective = levels completed at a fixed budget). Let F(x, n) be the probability, under b, of finishing the level from x within n actions. Reset to s_k iff

  F(s_k, B − 1 − k) > F(s, B),

 and never when B ≤ 1 + k. As B shrinks, F(s_k, B − 1 − k) falls toward zero before the reset becomes impossible, and the value of exploring falls with it (S&B p. 26; Kochenderfer pp. 135, 309). A rule that ignores B will still order resets late in the run, when too few actions would be left after the replay to finish the level.

### Value-of-information term

Continuing a doubtful line can still pay if it changes b in a way that shortens the work after the reset. In the exact problem this is inside U through τ. A myopic check (Kochenderfer 6.6; R&N Figure 16.9): if the outcomes of the next few actions cannot change either the restore decision or the plan after it, their information value is zero and only the cost-to-go inequality matters. R1's trigger (no new state, no memory change) is an empirical sign that this value has been zero for n actions.

### When the quantities cannot be estimated

The only worst-case rule the books give for "how far to go before turning back" is the lost cow's doubling (LaValle p. 673, ratio 9, optimal for that problem) and iterative deepening (LaValle p. 39; R&N online iterative deepening, memory). The analogue here is to let the allowed number of non-progress actions grow geometrically with the return cost or with each failed attempt, instead of a fixed threshold. This is a suggestion by analogy; none of the books proves anything for the reset setting.

### Assumptions the statement needs

1. **Determinism and full observability within a level.** Otherwise the replayed prefix is not guaranteed to land in s_k (Kochenderfer 9.9, Example 9.9; LaValle p. 495; S&B p. 164). Guard: compare the state after each replayed action with the stored one and stop on a mismatch (LaValle 8.1 p. 370; R&N execution monitoring).
2. **Reset semantics.** RESET returns to the level start at cost 1, is available from every state including game over, and carries no hidden state forward. If a game over forces a restart of the whole game, k must include the earlier levels' solutions.
3. **Additive unit costs and a hard budget**, so the problem is finite-horizon and the policy may depend on B.
4. **The level is solvable from s₀ within the remaining budget.** With RESET available everywhere this makes the augmented space safely explorable in Russell and Norvig's sense (memory) and satisfies RTDP's condition (2) (S&B p. 178). Put differently, RESET is what turns a space with dead ends into one without them, at a price.
5. **Estimates of G or F and of q exist.** The books give no way to get them without a model. They have to come from the agent's own model or from data across runs. Dead ends cannot be recognised with certainty in an unknown environment (R&N Figure 4.19; LaValle p. 797), so q is a judgement.
6. **Stationary rules**: what was verified stays true (S&B 8.3 on models that become wrong).

### A point about R2's design

In these terms R2 changes two things at once: the decision rule (when to reset) and how the return is executed (automatic replay). The books treat them separately: the first is a value comparison, the second is the reroute cost. Automatic replay does not reduce the return cost in actions (each replayed action still counts); it removes errors and deliberation during the return. If R2 beats R1, the measures "return cost" and "reset timing" are what can separate the two effects.

---

## 8. Mapping of the study's measures to textbook concepts

| Study measure | Nearest textbook concept | Source |
|---|---|---|
| Dead-end loss | Time spent in states from which the goal is unreachable or failure is unavoidable (φ = ∞; X_ric); steps "wasted" by an agent not designed for exploration during execution | LaValle pp. 375–376, 796–797, 660; R&N 4.5.1 |
| Return cost | Reroute path cost; physical backtracking | LaValle pp. 645–646; R&N 4.5.2 |
| Reset count and timing | No direct counterpart. Nearest: number of cycles in a retry loop (LaValle Example 10.6); number of excursions in the lost-cow strategy | LaValle pp. 513, 673 |
| Score at fixed budget | Finite-horizon return; competitive ratio against an agent that knows the environment (the human baseline plays a similar role) | Kochenderfer 7.1; LaValle (12.28); R&N p. 135 |
| Stall (R1 trigger) | Non-systematic search (revisiting visited states); no decrease of a navigation function; zero value of information | LaValle pp. 32–33, 375; Kochenderfer p. 121 |

---

## 9. Not found, or not read

- Russell and Norvig body text: not read. All statements about what sections 4.5, 11.5.3, 16.6, 17.1.1, 17.3 and 22.3 say beyond captions, pseudocode, contents and index are from memory and should be checked against a copy of the book before being quoted. In particular the phrases "safely explorable", the O(n²) bound for LRTA*, the "cannot teleport" sentence, the VPI formula and the restart construction for the Gittins index.
- A reset as a priced, voluntary action in an exploration problem: not in any of the four books.
- Replay to a frontier after a reset as a method: not in any of the four.
- Optimal stopping as a topic: not in Sutton and Barto, Kochenderfer or LaValle (no hits). In Russell and Norvig only a bibliography entry (Ferguson) and "stopping time" inside the Gittins index definition (index, p. 583).
- Ski-rental style rent-or-buy analysis, which would be the natural competitive model for "keep trying or pay to reset": not in any of the four (my observation; not searched beyond the words "competitive ratio").
- Formulas were checked against the PDF text layer only; page images could not be rendered here.
