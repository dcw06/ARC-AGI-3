# Textbook notes for the recovery study (reset / undo / replay; R0, R1, R2)

Reader's notes from six textbooks. Every item is tagged:

- **[BOOK]** = what the book says (quotes are exact, from the plain-text conversion of the fetched copy; maths symbols may be flattened).
- **[INFERENCE]** = my application to the study. Not in the book.

Formulas were read from extracted text only (PDF page rendering was not available on this machine), so equation typography was not checked visually.

Editions read (all fetched 2026-11-14):

| Short name | Edition fetched | Page mapping used |
|---|---|---|
| PML1 | Murphy, *Probabilistic Machine Learning: An Introduction*, online version dated April 18, 2025 (860 PDF pages) | book page = PDF page - 30 |
| PML2 | Murphy, *Probabilistic Machine Learning: Advanced Topics*, online version dated December 10, 2025 (1,370 PDF pages) | book page = PDF page - 34 |
| UDL | Prince, *Understanding Deep Learning*, release v5.0.3 (file dated 02/09/26, 541 PDF pages) | book page = PDF page - 14 |
| ECI | Peters, Janzing, Schölkopf, *Elements of Causal Inference*, MIT Press 2017 open-access PDF (289 PDF pages) | book page = PDF page - 17 |
| DL | Goodfellow, Bengio, Courville, *Deep Learning*, HTML chapters (ch. 3, 5, 11 and contents) | printed page numbers embedded in the HTML |
| MML | Deisenroth, Faisal, Ong, *Mathematics for Machine Learning*, draft dated 2024-01-15 (417 PDF pages) | book page = PDF page - 6 |

Page numbers below are book pages. Online editions of PML1/PML2/UDL are revised from time to time, so page numbers can drift by a page or two against other printings; section numbers are the stable reference.

---

## 1. Murphy, PML2 (Advanced Topics) — the most useful book for both halves

### Sections read
3.3.2 (p.73-74), 3.3.5 (p.80-82), 3.6 intro and 3.6.2 (p.108, 111-114), 3.10 (p.131-140), 4.2.4.2 (p.152-153), 6.6.4.3 (p.304), 6.7.1 (p.304-306), 6.7.3 opening (p.307), 19.2.4 (p.740), 33.4.2.2 (p.1095-1096), 34.1 (p.1105-1107), 34.2 (p.1112-1115), 34.3 (p.1115-1120), 34.4 (p.1120-1128), 34.5 (p.1128-1133), 34.7.1-34.7.2 (p.1137-1139), 35.1 (p.1145-1150), 35.2.5.2 (p.1153-1154), 35.4 intro, 35.4.1, 35.4.2 (p.1164-1166), 35.4.6 and 35.5 intro, 35.5.1.1 (p.1171-1172), 36.1 (p.1185-1186), 36.2.3-36.2.4 (p.1190-1194), 36.3 (p.1194-1195), 36.4.1 opening (p.1195-1196), 36.4.3-36.4.4 (p.1203-1204), 36.6 (p.1216-1219), 36.7 intro and 36.7.1 (p.1219-1220).

Not read: the rest of the book (inference algorithms, generative models, etc.), 34.6 planning algorithms in detail, 35.2-35.3 and 35.6 in detail, 36.4.2, 36.4.5, 36.5, 36.7.2, 36.8.

### 1a. Recovery decision

**Expected-utility framing (34.1, p.1105-1107).**
- [BOOK] "The goal is to define a policy, also called a decision procedure, which specifies which action (decision) to take in response to each possible observation or dataset, a = δ(x), so as to minimize the expected loss, also called the risk." (34.1.1, p.1105)
- [BOOK] The optimal Bayesian policy picks, for each observation, the action with the highest posterior expected utility: "This is called the maximum expected utility principle." (34.1.3, p.1107)
- [INFERENCE] R2's price rule is an expected-utility comparison: reset when E[progress | reset, replay cost L, budget left B - 1 - L] exceeds E[progress | continue, budget left B]. The book gives the frame, not the numbers; the two expectations have to come from the harness's own estimates (probability the current state is a dead end, length of the verified prefix).

**Value of information (34.2.3, p.1114-1115).**
- [BOOK] Oil-wildcatter example: without the test MEU = 20, with it 32.2. "So the improvement in utility if you do the test (and act optimally on its outcome) is $12.2. This is called the value of perfect information (VPI). So we should do the test as long as it costs less than $12.2."
- [BOOK] VPI = MEU(G + S → D) - MEU(G) (eq. 34.30).
- [INFERENCE] An undo or a probing action in a suspected dead end is a "test" with a price in actions. It is worth taking only if it can change the reset/continue decision; if every plausible outcome leads to the same decision its value is zero. A forced "recovery deliberation" (R1) costs no game actions, so its VPI only has to exceed its token cost and any side effect on the model's later play.

**Test-then-commit under a finite budget (34.3, p.1115-1120).** This is the closest thing in any of the six books to a priced decision with a known horizon.
- [BOOK] "The fundamental tradeoff is that using larger values of n1 and n0 will help you collect more data and hence be more confident in picking the best action, but this incurs an opportunity cost, because the testing phase involves performing actions that may not result in the highest reward." (p.1115)
- [BOOK] On the gain from testing: "this gain can only be accrued for a smaller number of people, as shown by the N - 2n prefactor. (This is a consequence of the explore-exploit tradeoff.)" (34.3.1.2, p.1117)
- [BOOK] Optimal test size n* ≤ √N · σ/(2τ) (eq. 34.43): "the optimal sample size n* increases as the observation noise σ increases ... However, the optimal sample size decreases with τ, since a prior belief that the effect size δ = µ1 - µ0 will be large implies we expect to need less data to reach a confident conclusion." (p.1117)
- [BOOK] Best-arm identification "is arguably the wrong objective, since it is usually not worth spending money on collecting a large sample size to be confident that δ > 0 (say) if the magnitude of δ is small." (34.3.1.4, p.1118)
- [INFERENCE] Two consequences for R2. (i) The value of a reset scales with the budget left after paying for it (the "N - 2n" factor): late in a 100-action game a reset-and-replay that costs 1 + L actions leaves little to exploit, so the rule should become more reluctant as the budget shrinks and should never fire when 1 + L ≥ B. (ii) The amount of exploration worth doing before committing grows only like the square root of the horizon; with a 100-action cap, long diagnostic probing is hard to justify.

**Exploration versus exploitation (34.4, p.1120-1128; 35.1.5, p.1148-1150).**
- [BOOK] "If the agent starts exploiting an incorrect model too early, it will collect suboptimal data, and will get stuck in a negative feedback loop" (34.4.3, p.1122).
- [BOOK] The exact solution is a belief-state MDP: the belief state "is a finite sufficient statistic for the history" and "bt = BayesRule(bt-1, at, rt)" (34.4.4, p.1122-1124); "computing the optimal policy for general contextual bandits is intractable" (p.1124).
- [BOOK] For MDPs: "The Bayes optimal solution to the exploration-exploitation tradeoff can be computed by formulating the problem as a special kind of POMDP known as a Bayes-adaptive MDP or BAMDP" ... "For small problems, we can solve the resulting augmented MDP optimally. However, in general this is computationally intractable." (35.1.5.4, p.1149-1150)
- [BOOK] Count-based exploration bonus r̃ = r + α/√N(s,a), "where Ns,a is the number of times action a has been taken in state s" (35.1.5.3, eq. 35.2, p.1149); continuous states handled "through the use of hashing".
- [BOOK] Regret: "If the agent under-explores and converges to choosing a suboptimal action ... then a linear regret is suffered ... On the other hand, if the agent over-explores ... the agent also suffers a linear regret." (34.4.7, p.1128)
- [INFERENCE] R1's trigger ("no new state hash and no change to memory for k actions") is exactly "the augmented state (environment state, belief) of a Bayes-adaptive MDP has stopped moving". In that formulation an action that changes neither the state nor the belief buys nothing, and here it costs one action, so it is dominated. That is a principled reading of the stall rule. The book also shows the threshold is a two-sided trade-off (reset too early and too late both cost), which is why k must be tuned and why it should be tuned on separate games.
- [INFERENCE] The state hash plays the role of the visit count in eq. 35.2. If the hash includes fields that change on every action (a step counter, an animation frame) the count never repeats and the stall detector never fires.

**Episodes, terminal states and horizon (34.5.3, p.1130-1131).**
- [BOOK] "the agent is in an episodic task, if its interaction terminates once the system enters a terminal state or absorbing state" ... "Note that we can convert an episodic MDP to a continuing MDP by redefining the transition model in absorbing states to be the initial-state distribution p0. Finally, if the trajectory length T in an episodic task is fixed and known, it is called a finite horizon problem." (p.1130-1131)
- [BOOK] "the discount factor reflects the assumption that there is a probability of 1 - γ that the interaction will end at the next step. For finite horizon problems, where T is known, we can set γ = 1, since we know the life time of the agent a priori." (p.1131)
- [INFERENCE] The book treats a reset as something that happens after termination, at no cost. It does not treat reset as a costed action the agent may choose mid-episode, which is the ARC-AGI-3 case. The closest fit is a single finite-horizon problem of length 100 in which RESET is an ordinary action with a transition to the level start and GAME_OVER is a state from which only RESET is useful. In a finite-horizon problem the best action depends on the steps remaining, which again supports making R2's rule a function of the budget left.

**Restart in local search (6.7.1, p.304-306)** — the only explicit restart arithmetic found in the six books.
- [BOOK] "whenever we reach a local maximum, we start again from a different random starting point. This is called random restart hill climbing ... If each hill-climbing search has a probability of p ≈ 0.14 of success, then we expect to need R = 1/p ≈ 7 restarts until we find a valid solution ... Let N1 = 4 be the average number of steps for successful trials, and N0 = 3 be the average number of steps for failures. Then the total number of steps on average is N1 + (R - 1)N0 = 4 + 6 × 3 = 22." (6.7.1.1, p.305)
- [BOOK] "Hill climbing will stop as soon as it reaches a local maximum or a plateau. Obviously one can perform a random restart, but this would ignore all the information that had been gained up to this point." (6.7.1.2, p.305)
- [BOOK] Algorithm 6.6 (tabu search, p.306) keeps a counter "c := 0 // counts number of steps with no progress", resets it on improvement, and stops when c reaches cmax; a tabu list of recently visited states "forces the algorithm to explore new states".
- [INFERENCE] Algorithm 6.6 is R1 in miniature: a no-progress counter with a threshold plus a memory of visited states. The restart formula gives the cost model for R2: expected actions ≈ N1 + (R - 1)(N0 + return cost), where N0 is the dead-end loss per failed attempt. Both of the study's cost outcomes appear in it directly. The "ignores all the information" sentence is the argument for replaying a verified prefix and keeping the memory across the reset rather than restarting blind.
- [BOOK] Also 6.6.4.3 (p.304): "we may choose to terminate expensive trials (queries) early, if the results of their cheaper proxies suggest they will not be worth running to completion".

**Planning with a model instead of acting (35.4, p.1164-1166; 35.4.6, p.1171).**
- [BOOK] Model-based RL "can significantly reduce the amount of real-world data that the agent needs to collect, since it can 'try things out' in its imagination (i.e., the models), rather than having to try them out empirically." (p.1164)
- [BOOK] MPC: "wait until we know what state we are in ... then use a model to predict future states and rewards that might follow for each possible sequence of future actions ... We then take the action that looks most promising, and repeat the process at the next step." (35.4.1, p.1164)
- [BOOK] "The main challenge with MBRL is that errors in the model can result in poor performance of the resulting policy" (35.4.6, p.1171); "a small estimation error in the simulator has a compounding effect in long-horizon problems" (35.5.1.1, p.1172).
- [INFERENCE] Automatic replay is open-loop execution of a stored plan. It is safe only where the game is deterministic along the prefix; the harness should verify the state hash after each replayed action and stop replaying at the first mismatch, because errors compound.

**Selecting on noisy estimates (35.2.5.2, p.1153-1154).**
- [BOOK] "the optimizer's curse ... or the maximization bias. The problem refers to the simple statistical inequality, E[max_a X_a] ≥ max_a E[X_a] ... if we pick actions greedily according to their random scores {X_a}, we might pick a wrong action just because random noise makes it appealing." The fix: "use two separate Q-functions, Q1 and Q2, one for selecting the greedy action, and the other for estimating the corresponding Q-value."
- [INFERENCE] Applies twice: to the agent (the "furthest state reached" may be a lucky or dead-end state, so replaying to it is not automatically right), and to the study (the stall threshold that looked best on a few noisy runs will look worse on fresh games; select on the development games, estimate on the reporting games).

### 1b. Experimental design

**Randomised experiments identify the effect (36.3, p.1194-1195).**
- [BOOK] "Because random assignment does not depend on any property of the units in the study, there are no causes of treatment assignment, and hence also no common causes of Y and A." Then P(Y|do(A = a)) = P(Y|a) and the estimator is the difference of group means (eq. 36.17).
- [BOOK] "Randomized control trials are the gold standard for estimating causal effects. This is because we know by design that there are no confounders that can produce alternative causal explanations of the data."
- [BOOK] Limits: "it may be difficult to ensure that the participants in an RCT are representative of the population where the treatment will be deployed."
- [BOOK] "every causal identification strategy relies on assumptions that have some content that cannot be validated in the observed data." (36.2.3, p.1192)
- [BOOK] Average effects versus individual counterfactuals: "the key dividing line between counterfactual and interventional queries is whether the query requires knowing the joint distribution of potential outcomes within individuals" (36.2.4, p.1193).
- [INFERENCE] The study sets the condition itself, so the average effect of R1 against R0 on the fixed game list is identified, provided nothing else differs between arms (model snapshot, harness commit, prompts outside the factor, action cap, run date). "Would this particular R0 run have finished the level had it reset at step 40" is a counterfactual about one run and is not identified by the arm means. The result holds for the games on the list; the book's representativeness caveat applies to any wider claim.

**Before/after comparisons (36.6, p.1216-1217).**
- [BOOK] Difference in differences assumes a "time-specific effect that applies to all units" and removes it by comparing the change in the treated group with the change in an untreated group.
- [INFERENCE] Comparing new R1/R2 runs with the earlier 100-action run would mix the factor with whatever changed over time. R0 has to be run again alongside R1 and R2, in interleaved order.

**Placebo and negative-control checks (36.7.1, p.1220).**
- [BOOK] "the estimation procedure we use for estimating the COVID effect should, when applied to HPV, yield τ̂ ≈ 0 ... If this does not happen, then we may suspect that there are still some confounding factors lurking". Also a "null outcome" known not to be affected by the treatment.
- [INFERENCE] Negative-control outcome for this study: behaviour before the first stall trigger could fire (for example actions used on level 1 when it is solved without any stall). R0, R1 and R2 should have the same distribution there. A difference means the arms differ in something other than the factor.

**Design advice written for user studies but general (33.4.2.2, p.1095-1096).**
- [BOOK] "Independent and dependent variables, hypotheses, and inclusion and exclusion criteria must be clearly defined prior to the start of the study." ... "one could decide, in advance, to exclude data from any participant".
- [BOOK] Baselines should include a "placebo explanation (an explanation that provides no information)".
- [BOOK] "Broadly speaking, randomization marginalizes over potential confounds ... randomization in the order of tasks marginalizes out learning effects. Matching and repeated measures reduce variance."
- [BOOK] "Comparisons of task performance within subjects will have lower variance but a potential bias from learning effects from the first task to the second. Comparisons across subjects will have higher variance".
- [BOOK] "It is essential to choose the right test and multiple hypothesis correction to avoid inflated significance values while retaining power."
- [INFERENCE] Games are the "subjects". Running every game under every condition is the within-subject (matched) design. The usual price, carry-over, does not arise because weights are frozen, as long as no memory, cache or log from one run is visible to another. A placebo arm here would be a forced deliberation that is not triggered by a stall (same prompt, at matched but unrelated times); without it, R1 against R0 measures "stall-triggered deliberation" and "being interrupted with an extra prompt" together.

**Testing and estimation (3.10, p.131-140; 3.3.5, p.80-82).**
- [BOOK] "despite its widespread use, p-values and NHST have many problems ... We shall therefore avoid using this approach in this book." (3.10.1, p.132)
- [BOOK] Parameter-estimation approach with a region of practical equivalence: "This is not only computationally simpler, but is also allows us to quantify the effect size ... rather than merely accepting or rejecting a hypothesis." (3.10.2.3, p.133)
- [BOOK] Paired test: "define yn = y2n - y1n, which we model using yn ∼ N(µ, σ2). We can then test whether µ = 0 using the t-test; this is called a paired sample t-test." (3.10.2.7, p.135). With a non-informative prior "the Bayesian credible interval will be the same as the frequentist confidence interval in this simple setting" (3.10.2.6, p.134); weakly informative priors and a Student likelihood ("more robust to outliers") are suggested.
- [BOOK] Rank-based substitutes are only accurate for moderate N: Table 3.2 (p.137) gives "N > 14" for the Wilcoxon signed-rank approximation and "N > 11" for Mann-Whitney U.
- [BOOK] Several nominal predictors: mean = µ + Σ αj + Σ βk + Σ γjk with sum-to-zero constraints; "We are interested in testing whether γ = 0, meaning there is no interaction effect ... we can also use a Bayesian approach and just compute p(θ|D)." (3.10.3.5, p.140)
- [BOOK] Bootstrap: "In cases where the estimator is a complex function of the data, or when the sample size is small, it is often useful to approximate its sampling distribution using ... the bootstrap" (3.3.2, p.73).
- [INFERENCE] The design is a two-factor layout (game × condition) with replication; the γ terms are "the effect of recovery differs by game", which is likely here and should be reported, not averaged away silently.

**Partial pooling across groups (3.6, p.108-114).**
- [BOOK] "Inferring p(θj|Dj) independently for each group j can give poor results if Dj is a small dataset ... A hierarchical Bayesian model lets us borrow statistical strength from groups with lots of data" (p.108).
- [BOOK] "having Nj observations yij each with variance σ2 is like having one measurement ȳj ... with variance σ2j ≜ σ2/Nj" (3.6.2, p.111).
- [BOOK] Eight schools: "school 0 has an unusually large improvement (28 points) compared to the overall mean, suggesting that the estimating θ0 just based on D0 might be unreliable"; posterior mean = wj·µ + (1 - wj)·θ̂j with wj = σ2j/(σ2j + τ2); "there is more shrinkage for groups with smaller measurement precision (e.g., due to smaller sample size)" (p.112).
- [INFERENCE] This is the nearest any of the books comes to regression to the mean: an extreme per-game result from three runs is partly noise and should be shrunk. A hierarchical Gaussian model over per-game effects is the natural second analysis.

**Selection (4.2.4.2, p.152-153; 19.2.4, p.740).**
- [BOOK] Two-coin example: recording only trials with at least one head makes the coins look dependent; "the correlation is due to conditioning on a hidden common effect ... This is called selection bias."
- [INFERENCE] Return cost exists only for runs that reset, and reset frequency is itself changed by the condition. Comparing mean return cost "among runs that reset" across R0, R1, R2 conditions on a post-treatment event and can mislead. Report it per run over all runs (zero when there was no reset), or alongside the reset rate.

**Off-policy evaluation (35.5 intro, p.1171).**
- [BOOK] "If we are to estimate J(π) ... but the trajectories are generated by a different policy π′, simply averaging rewards in the data gives us J(π′), not J(π)."
- [INFERENCE] Existing R0 logs cannot stand in for R1/R2 runs; they can only describe R0 (for example its dead-end loss), and that description should be used for tuning on development games only.

### Nothing found in PML2 on
Optimal stopping as a topic, cost of resets chosen by the agent, regression to the mean by name, sample-size/power formulas for hypothesis tests (only the A/B decision-theoretic sizing above).

---

## 2. Murphy, PML1 (Introduction)

### Sections read
1.2.3 end (p.13), 4.5.4-4.5.5 (p.124-126), 4.6.5.2 (p.145), 4.7.1-4.7.6 opening (p.154-160), 5.1.1 (p.167-169), 5.2.1 (p.179-181), 5.2.6 (p.187-189), 5.5 (p.198-203). Keyword search found no bandit, reinforcement-learning-method, optimal-stopping or causal-design material. "Regression to the mean" occurs once (13.6.2) in an unrelated sense (mixture models).

### 2a. Recovery decision
- [BOOK] Bayesian decision theory with a loss matrix and the "maximum expected utility principle" (5.1.1, p.167-168). Worked example: "if we reduce the cost of the drug from 8 units to 5, then the optimal policy changes" and the policy also changes with test reliability (p.168-169).
- [BOOK] "So far, we have implicitly assumed that the agent is risk neutral." (p.169)
- [INFERENCE] Same frame as PML2 34.1; the worked example shows that the reset threshold must move with the price of a reset (replay length) and with how reliable the stall signal is. Risk neutrality is a real assumption: the score penalises action counts, so a rule that maximises expected levels is not automatically the one that maximises expected score. Otherwise little here on recovery.

### 2b. Experimental design — this is where PML1 is useful
**Comparing two systems (5.2.6, p.187-189).**
- [BOOK] "we are often more interested in estimating an effect size, which is the difference in magnitude between two parameters, rather than in deciding if an effect size is 0 (null hypothesis) or not ... the latter is called a point null hypothesis, and is often regarded as an irrelevant 'straw man'". (p.187)
- [BOOK] "even if this probability is large, the improvement may be not be practically significant. So it is better to compute a probability such as p(∆ > ϵ|D) or p(|∆| > ϵ|D), where ϵ represents the minimal magnitude of effect size that is meaningful for the problem at hand." (p.187)
- [BOOK] "Since the classifiers are applied to the same data, we can use a paired test for comparing them, which is more sensitive than looking at average performance, since the factors that make one example easy or hard to classify (e.g., due to label noise) will be shared by both methods. Thus we will work with the differences, di = e1i - e2i." (5.2.6.1, p.187-188)
- [BOOK] With an uninformative prior, p(∆|d) = T_{N-1}(∆ | µ, s²/N), µ the mean difference, s² the unbiased variance of the differences (p.188).
- [BOOK] "An alternative to a formal test is to just plot the posterior p(∆|d) ... (In fact, an even simpler approach is to just make a boxplot of the data, {di}, which avoids the need for any formal statistical analysis.)" (p.188)
- [BOOK] For rates on separate samples: Beta posteriors for each rate and p(∆ > ϵ|D) by one-dimensional integration (5.2.6.2, p.188). Example with small counts: "It seems that there is a difference, but the sample size is low, so we cannot be sure. Hence we will represent our uncertainty by computing p(∆|D)" (p.189).

**Bootstrap and intervals (4.7.3-4.7.5, p.156-159).**
- [BOOK] "In cases where the estimator is a complex function of the data (e.g., not just an MLE), or when the sample size is small, we can approximate its sampling distribution using a Monte Carlo technique known as the bootstrap." ... "generate each D̃(s) by sampling N data points with replacement from the original dataset." (p.156-157)
- [BOOK] "When N = 10, we see that the sampling distribution is asymmetric, and therefore quite far from Gaussian" (p.157). "So one can think of the bootstrap distribution as a 'poor man's' posterior" (p.157).
- [BOOK] Gaussian interval θ̂ ± 2·se; if that approximation is poor, use bootstrap quantiles of θ̂(D) - θ̂(D(s)) (4.7.4, p.158).
- [BOOK] "the frequentist approach just means that the procedure for generating CIs will contain the true value 95% of the time" (4.7.5, p.158); the Wald interval gives (0, 0) from a single zero observation and "can behave badly even for large N" (p.159).
- [INFERENCE] The bootstrap described resamples independent data points. Here runs are nested in games, so the unit to resample is the game (then runs within the game). With a handful of games there are few distinct resamples and the interval is rough; the book does not discuss this, it is my caution.

**Power and p-values (5.5.2-5.5.4, p.199-202).**
- [BOOK] For a test of a Gaussian mean with known σ: critical value x* = zα·σ/√N + µ0; type II error β(µ1) = p(X̄ < x* | H1); "We define the power of a test as 1 - β(µ1); this is the probability that we reject H0 given that H1 is true" (p.199-200).
- [BOOK] Permutation test: "to test if they are the same ... we can use the non-parametric permutation test, which makes no assumptions about the distribution." (5.5.3, p.201)
- [BOOK] "a p-value of 0.05 does not mean that the alternative hypothesis H1 is true with probability 0.95." (p.201) With a 5% type I rate, 80% power and a prior that 90% of treatments are ineffective, "p(H0|'significant') = 0.36" (p.202). "Thus we should distrust claims of statistical significance if they violate our prior knowledge." (p.202)
- [INFERENCE — derived from the book's formulas, not stated in it] Setting power to 1 - β gives N = (zα + zβ)²·σ²/δ² for a one-sample or paired test (σ = SD of the differences, δ = effect to detect), and twice that per arm for two independent arms. With one-sided α = 0.05 and 80% power the multiplier is about 6.2; two-sided, about 7.9. See section 7 for what this means for three repeats.

**Tuning versus reporting (1.2.3, p.13; 4.5.4-4.5.5, p.124-126).**
- [BOOK] "In practice, we need to partition the data into three sets, namely the training set, the test set and a validation set; the latter is used for model selection, and we just use the test set to estimate future performance ..., i.e., the test set is not used for model fitting or model selection." (p.13)
- [BOOK] "if the size of the training set is small, leaving aside 20% for a validation set can result in an unreliable estimate" (4.5.5, p.125).
- [BOOK] Standard error se(µ̂) = σ̂/√N; "σ measures the intrinsic variability of Ln across samples, whereas se(µ̂) measures our uncertainty about the mean" (4.5.5.1, p.126). One-standard-error rule: "pick the value which corresponds to the simplest model whose risk is no more than one standard error above the risk of the best model" (p.126).
- [INFERENCE] The study's development/reporting split is the validation/test split. With few development games the best-looking stall threshold is only weakly determined; the one-standard-error rule suggests choosing the simplest or most conservative threshold among those within noise of the best, then freezing it.

**Hierarchical priors (4.6.5.2, p.145).** [BOOK] one paragraph, pointing to PML2: "This is useful when we have multiple related parameters that need to be estimated (e.g., from different subpopulations, or muliple tasks)".

---

## 3. Peters, Janzing, Schölkopf, ECI

### Sections read
1.3 (p.5-7), 2.1 (p.16-21), 6.3 (p.88-96), 6.5.1 Remark 6.29 and Example 6.30 (p.104-105), 6.6 opening to Definition 6.39 (p.109-114), 6.8 (p.120-122), 6.9 (p.122-126), 8.2 (p.159-167), 9.1-9.2 (p.171-175), Appendix A.2 opening (p.216-217).
Not read: chapters 4, 5, 7, 10 (structure learning, time series), 6.7 do-calculus, 6.10-6.11, 9.3-9.5.

### 3a. Recovery decision
Only section 8.2 touches it.
- [BOOK] "In episodic reinforcement learning, the state is reset after a finite number of actions" (8.2.2, p.162). Resets are part of the environment's protocol, not a decision of the agent.
- [BOOK] Off-policy estimate of a new strategy from data gathered under another (eq. 8.4): valid "As long as this strategy assigns a positive probability to any action"; "In practice, the estimator (8.4) often has large variance; in continuous settings the variance may even be infinite." (p.163) and "the condition of the non-vanishing densities is indeed necessary" (p.167).
- [BOOK] Proposition 8.1 (state simplification, p.164-165): if a function F = f(S) keeps everything that matters for reward and for the transitions between simplified states, "the optimal strategy ... depends only on Fj and not on Sj"; useful "if Fj takes fewer values than Sj".
- [BOOK] "we believe that causality could play a role when transferring knowledge between different tasks in reinforcement learning (e.g., when progressing to the next level in a computer game ...); however, we are not aware of any such result." (p.160)
- [INFERENCE] (i) R0 never forces a deliberation, so the forced action has probability zero under R0 and reweighting R0 logs cannot estimate R1 or R2; fresh runs are required. (ii) Proposition 8.1 states when a coarser state is enough. It is the condition the state hash should meet: drop fields that affect neither progress nor transitions, keep everything that does. Too fine a hash hides stalls; too coarse a hash reports stalls that are not there.

### 3b. Experimental design — the core contribution of this book
**What an intervention is and what it identifies.**
- [BOOK] Definition 6.8 (p.88-89): an intervention replaces one or several structural assignments and yields a new distribution; "In general, intervention distributions differ from the observational distribution."
- [BOOK] Definition 6.12 (p.91): "there is a total causal effect from X to Y if and only if X and Y are dependent in P^{C;do(X := Ñ_X)} for some random variable Ñ_X" (wording of the independence symbol flattened).
- [BOOK] Example 6.15 (p.92-93): "The definition of a causal effect is implemented in randomized trials." ... "If we then still find a dependence between the treatment and recovery, we conclude that T has a total causal effect on the recovery."
- [BOOK] Figure 6.3 caption (p.93): "The randomization over T removes the influence of any other variable on T, and thus there cannot be any hidden common cause between T and R."
- [BOOK] Same example, on separating two routes of influence: "In pharmaceutical studies, we are more interested in the biochemical effect than the placebo effect. We therefore restrict the randomization to be supported on placebo and drug of interest ... If we then still see a dependence between treatment T and recovery R, this must be due to a biochemical effect." (p.93)
- [BOOK] Proposition 6.14 (p.92): "(i) If there is no directed path from X to Y, then there is no total causal effect. (ii) Sometimes there is a directed path but no total causal effect."
- [BOOK] "interventions on single nodes, correspond to the standard version of randomized experiments." (6.8, p.121) and, when distributions are not strictly positive, "One may then have to consider simultaneous interventions on several nodes (e.g., double knockout gene experiments)" (p.122).
- [INFERENCE] What each contrast identifies:
  - R1 - R0 = total effect of "stall detector + forced deliberation" as one package. It includes any effect of merely being interrupted (the "placebo" route). It does not say which route matters.
  - R2 - R1 = total effect of "price rule + automatic replay" given that stall detection is present. Two components change together, so their separate effects, and whether one only works with the other, are not identified. A 2×2 (price rule on/off × auto-replay on/off) would be needed; the "double knockout" remark is the book's nearest statement.
  - R2 - R0 = effect of the whole bundle.
  - A zero difference in score does not show the mechanism is inert (Proposition 6.14 (ii)): R1 can cut dead-end loss and add reset cost in equal measure. This is the reason to report dead-end loss, return cost and reset count next to the score.

**Changing one component leaves the others alone — an assumption, not a fact.**
- [BOOK] "we can intervene on one mechanism without affecting the others. Changing a mechanism will change its input-output behavior, and thus the inputs other mechanisms downstream might receive, but we are assuming that the physical mechanisms themselves are unaffected by this change." (2.1, p.20)
- [BOOK] "If we intervene on a variable, then the other mechanisms remain invariant" (6.6, p.109).
- [BOOK] "not all systems will satisfy it. For instance, if the mechanisms that an overall system is composed of have been tuned to each other by design or evolution, this independence may be violated." (2.1, p.19)
- [INFERENCE] The harness is a designed system whose parts were tuned together (prompts, memory format, action cap). Adding a forced deliberation can change how the model uses its memory or how long its context grows. The study still identifies the effect of the change as implemented; the claim "it works because of stall detection" needs the mechanism measures to back it.

**Potential outcomes (6.9, p.122-126).**
- [BOOK] "The 'fundamental problem of causal inference' [Holland, 1986] states that for each unit u we can observe either Bu(t = 1) or Bu(t = 0) and never both of them at the same time." (p.123)
- [BOOK] SUTVA "states that the units do not interfere (e.g., the potential outcome of a unit does not depend on which treatment any other unit received) ...; furthermore it requires that the potential outcomes do not depend on how or why the treatment has been received." (p.123)
- [BOOK] In a completely randomised experiment the difference of the two group means "is an unbiased estimator" of the average causal effect (Neyman; eq. 6.26, p.124; the indices in the extracted formula looked swapped, so I give it in words).
- [BOOK] "Working with settings, in which the average causal effect is zero but the individual causal effects are non-zero, seems to be easier for potential outcomes." (p.126)
- [INFERENCE] A game can be replayed under every condition, which gets round the fundamental problem at the level of the game, but each run is still a separate noisy draw, so only averages are comparable. Non-interference means no state shared between runs (memory files, caches, replay stores). The average effect across games may be near zero while individual games move in opposite directions; show per-game effects.

**Confounding, Simpson's paradox, selection.**
- [BOOK] Definition 6.39 (p.113): the effect is confounded when p^{do(X := x)}(y) ≠ p(y|x).
- [BOOK] Kidney stones (Examples 6.16, 6.37; Table 6.1, p.94-95, 111-112): treatment a is better within small stones and within large stones yet worse overall, because "treatment a had to deal with many more of these difficult cases". Simple conditioning "has even the opposite sign" of the average causal effect (p.112).
- [BOOK] "Simpson's paradox is not so much of a paradox but rather a warning of how sensitive causal reasoning can be with respect to model misspecifications." (9.2, p.175) "In some situations, we can infer the DAG from the protocol describing the acquisition of the data." (p.175)
- [BOOK] "It is sometimes believed that one should make the adjustment set as large as possible ... This is, however, not always a good idea" (p.113).
- [BOOK] Remark 6.29 (p.104): "it might be that we have implicitly conditioned on a third variable (selection bias)"; Example 6.30 (Berkson) shows independent causes becoming dependent once the sample is selected on their common effect.
- [BOOK] Significance is not the point of a causal comparison and depends on sample size: "By multiplying each entry in Table 6.1 by a factor of 10, the results would become statistically significant." (p.95)
- [INFERENCE] Compare within game, then average across games with weights fixed in advance; never pool raw action or reset counts across games of different difficulty. If the number of runs per game differs between conditions (crashes, exclusions), the pooled comparison can reverse, as in the kidney-stone table. Selecting the games to study by a past outcome (R0 did badly) is conditioning on a noisy effect: fix the list first and re-run R0.

**Multiple testing and non-rejection.**
- [BOOK] Dependences may be spurious when "they may be the result of a search procedure over a large number of pairs of random variables that was run without a multiple testing correction." (1.3, p.7)
- [BOOK] A.2 (p.216): when the null is not rejected this "does not necessarily mean much (it could be that the sample size n was too small to detect the dependence between X and Y)."
- [INFERENCE] Several outcomes × three contrasts × per-game looks is a search; name one primary outcome and contrast in advance. A null result from three repeats on a few games is not evidence of no effect.

### Nothing found in ECI on
Decision theory, optimal stopping, bandits, paired tests, bootstrap, power calculations, regression to the mean. It explicitly says the statistical-significance side "is not discussed here" (6.8, p.121).

---

## 4. Prince, UDL

### Sections read
8.5-8.6 and chapter 8 notes (p.132-136), chapter 19 in full except the policy-gradient derivations: intro and 19.1-19.3 (p.374-386), 19.4.1 end and 19.4.2 (p.388-389), 19.7-19.8 and notes (p.395-399).

### 4a. Recovery decision — thin
- [BOOK] "the agent must balance exploring the environment ... with exploiting what it already knows ... This is termed the exploration-exploitation trade-off." (p.374)
- [BOOK] "A stationary policy depends only on the current state. A non-stationary policy also depends on the time step." (19.1.5, p.378)
- [BOOK] Footnote (p.382): "An episode is a trajectory that starts in an initial state and ends in a terminal state".
- [BOOK] "One solution is to use exploring starts. Here, episodes with all possible state-action pairs are initiated, so every combination is observed at least once. However, this is impractical if the number of states is large or the starting point cannot be controlled." (19.3.2, p.385)
- [BOOK] DQN on Atari: "On other games like 'Montezuma's Revenge,' it barely made any progress. This game features sparse rewards and multiple screens with quite different appearances." (p.388)
- [BOOK] Maximisation over noisy values "leads to a systematic bias in the estimated action values" (19.4.2, p.388).
- [BOOK] The chapter says what it leaves out: "This chapter has only discussed simple methods for exploration ..." and model-based RL is "not discussed" (notes, p.399).
- [INFERENCE] With a fixed action cap the right recovery rule is non-stationary in Prince's sense (depends on steps left). ARC-AGI-3 is a case where "the starting point cannot be controlled": the only way back to a deep state is to replay actions, which is why return cost is a real cost. Nothing on resets as decisions, budgets, or value of information.

### 4b. Experimental design — only the validation/test rule
- [BOOK] "we do not measure their performance on the test set; this would admit the possibility that these hyperparameters just happen to work well for the test set but don't generalize to further data. Instead, we introduce a third dataset known as a validation set." (8.5, p.133)
- [BOOK] "The noise level is high since each training/validation cycle uses a stochastic training algorithm; we expect different results if we train a model twice with the same hyperparameters." (notes, p.135)
- [BOOK] Hyperband: bad configurations need not be run "to the end" (p.136).
- Nothing on comparing two systems statistically, intervals, or causal design.

---

## 5. Goodfellow, Bengio, Courville, DL

### Sections read
Contents; 5.1.3 closing remark on reinforcement learning (p.104); 5.3 and 5.3.1 (p.118-121); 5.4.3 (p.125-126); chapter 11 introduction and 11.1 (p.416-419), skim of 11.4-11.6. Chapter 3 (probability) fetched and skimmed: definitions only, nothing specific to this study.

### 5a. Recovery decision — nothing
- [BOOK] "reinforcement learning algorithms interact with an environment, so there is a feedback loop between the learning system and its experiences. Such algorithms are beyond the scope of this book." (5.1.3, p.104)

### 5b. Experimental design — basic statistics only
- [BOOK] "It is important that the test examples are not used in any way to make choices about the model, including its hyperparameters." (5.3, p.119)
- [BOOK] "Since the validation set is used to 'train' the hyperparameters, the validation set error will underestimate the generalization error" (p.119).
- [BOOK] "when the same test set has been used repeatedly to evaluate performance of different algorithms over many years ... we end up having optimistic evaluations with the test set as well." (p.119)
- [BOOK] "A small test set implies statistical uncertainty around the estimated average test error, making it difficult to claim that algorithm A works better than algorithm B on the given task." (5.3.1, p.120)
- [BOOK] Standard error of the mean SE(µ̂m) = σ/√m (eq. 5.46); both common estimates of σ "tend to underestimate the true standard deviation" (p.126). 95% interval µ̂ ± 1.96·SE (eq. 5.47).
- [BOOK] "it is common to say that algorithm A is better than algorithm B if the upper bound of the 95 percent confidence interval for the error of algorithm A is less than the lower bound of the 95 percent confidence interval for the error of algorithm B." (p.126)
- [BOOK] Methodology: "determine which performance metric to improve ahead of time, then concentrate on improving this metric. Without clearly defined goals, it can be difficult to tell whether changes to a machine learning system make progress or not." (11.1, p.419). Also "Instrument the system well to determine bottlenecks in performance" and "make incremental changes ... based on specific findings from your instrumentation" (p.416-417).
- [INFERENCE] The non-overlapping-intervals rule is an unpaired and conservative criterion; with games as matched units the paired analysis (PML1 5.2.6.1) is more sensitive. With m = 3 the estimate of σ is poor and biased low, so a per-game "mean ± 1.96·SE" from three runs overstates precision; a t multiplier (4.30 for 2 degrees of freedom) is the honest one. (The t multiplier is from memory, not from this book.)

---

## 6. Deisenroth, Faisal, Ong, MML

### Sections read
6.4.2-6.4.4 (p.191-194), 8.2.3-8.2.5 (p.262-265), 8.6 opening and 8.6.1 (p.283-285). Keyword search: reinforcement learning, hypothesis testing and causal inference appear only as passing mentions or references.

### 6a. Recovery decision — nothing.

### 6b. Experimental design — a few identities
- [BOOK] V[x - y] = V[x] + V[y] - Cov[x, y] - Cov[y, x] (eq. 6.49, p.193).
- [BOOK] The empirical covariance with 1/N "is a biased estimate. The unbiased (sometimes called corrected) covariance has the factor N - 1 in the denominator" (margin note, p.192).
- [BOOK] "It is important for the user to not cycle back to a new round of training after having observed the test set." (8.2.3, p.262); margin note: "Even knowing only the performance of the predictor on the test set leaks information (Blum and Hardt, 2015)."
- [BOOK] Nested cross-validation: inner loop chooses, outer loop estimates (8.6.1, p.284). "The standard error is defined as σ/√K, where K is the number of experiments and σ is the standard deviation of the risk of each experiment." (margin, p.284)
- [BOOK] "An alternative to cross-validation is bootstrap and jackknife" (8.2.5, p.265), reference only.
- [INFERENCE] Eq. 6.49 is why pairing by game helps: game difficulty is shared by both arms, the covariance is positive, and the variance of the difference falls. Use N - 1 when computing run-to-run SD from three runs.

---

## 7. Synthesis for the study (all [INFERENCE] unless a source is cited)

### 7.1 Recovery decision
1. The books supply a frame, not a rule. Frame: maximise expected utility given current beliefs (PML1 5.1.1, PML2 34.1); pay for information only up to its value (PML2 34.2.3); the worth of any corrective step scales with the budget left after paying for it (PML2 34.3.1.2); the exact answer is belief-state planning and is intractable (PML2 34.4.4, 35.1.5.4), so thresholds and bonuses are the practical tools (PML2 34.4.5, 35.1.5.3).
2. R1's trigger has a clean reading: neither the state nor the belief has changed, so further identical play is pure cost. Its closest textbook relative is the no-progress counter in tabu search (PML2 Algorithm 6.6).
3. R2's price rule should depend on three numbers: actions left B, replay length L, and the chance p that the current position is recoverable. A defensible first form from the restart arithmetic (PML2 6.7.1.1): reset when the expected actions to make progress from here exceed 1 + L plus the expected actions to make progress after a clean return, and never when 1 + L ≥ B.
4. Replay rather than blind restart is supported by PML2 p.305 ("would ignore all the information that had been gained"). Replay is open-loop, so check each replayed step (PML2 35.4.6, 35.5.1.1).
5. "Furthest state reached" can be a noisy maximum (PML2 35.2.5.2; UDL 19.4.2). Returning to it is not automatically the best target.
6. No book treats reset as a costed action chosen inside an episode, undo, or optimal stopping. For those, the six books are the wrong source.

### 7.2 What the design identifies
- R1 - R0: package effect of detector plus forced deliberation (interruption included).
- R2 - R1: joint effect of price rule plus automatic replay, given detection. Not separable without a 2×2.
- Averages over the fixed game list only; per-run counterfactuals are not identified (PML2 36.2.4; ECI 6.9).
- Conditions for a clean reading: identical model snapshot, harness commit, prompts (outside the factor), cap and game list across arms; interleaved or randomised run order; no shared state between runs (ECI SUTVA p.123; PML2 33.4.2.2).

### 7.3 Recommended analysis for few repeats per game and condition
1. **Unit = game.** For each reporting game g and condition c, average the R (≥3) runs: ȳ(g,c). Form per-game differences d(g) = ȳ(g,R1) - ȳ(g,R0), and likewise R2 - R1 and R2 - R0. (PML1 5.2.6.1; PML2 3.10.2.7; MML eq. 6.49.)
2. **Primary result = effect size with an interval, not a verdict.** Mean of d(g) with the Student interval on G - 1 degrees of freedom, which is also the Bayesian posterior T(G-1)(∆ | mean d, s²/G) under an uninformative prior (PML1 p.188). Report P(∆ > ε) for a smallest effect ε that matters, set in advance (PML1 p.187).
3. **Show every d(g)** in a dot or box plot (PML1 p.188) and the three raw runs per cell.
4. **Distribution-free check:** exact sign-flip permutation test on the d(g) (permutation tests: PML1 5.5.3). With G games the smallest possible two-sided p is 2/2^G: 0.125 for 4 games, 0.031 for 6, 0.008 for 8. Fewer than 6 reporting games cannot reach 0.05 two-sided by this test whatever happens.
5. **Second analysis:** hierarchical Gaussian model with game effects, condition effects and a game × condition term, partial pooling across games (PML2 3.6.2, 3.10.3.5). Report the spread of per-game effects, not only the mean.
6. **Report noise explicitly:** pooled run-to-run SD within a cell (σw, N - 1 denominator) and SD of d(g) across games.
7. **Sensitivity before running** (derived from PML1 5.5.2; PML2 eq. 34.46 has the same structure):
   - games needed ≈ (zα + zβ)² · (SD of d / δ)²; multiplier ≈ 6.2 (one-sided 5%, 80% power) or 7.9 (two-sided). To detect an effect equal to one SD of the per-game differences takes roughly 8 to 10 games once the small-sample t correction is allowed for; half an SD takes 25 to 30.
   - Var of the mean difference ≈ (τd² + 2σw²/R)/G, where τd is the SD of true per-game effects. Extra repeats only shrink the second term; if effects differ by game, more games help more than more repeats.
   - Inside one game, 3 against 3 independent runs has a standard error of 0.82·σw, so only effects of about 2σw or more are detectable there. Per-game claims from three repeats should be descriptive.
8. **Outcomes:** one primary outcome and one primary contrast named in advance (DL p.419; PML2 p.1095-1096; ECI p.7). Treat dead-end loss, return cost, reset count and timing as mechanism measures. Define return cost and dead-end loss for every run (zero when no reset), or always pair them with the reset rate, to avoid conditioning on a post-treatment event (ECI Remark 6.29; PML2 4.2.4.2).
9. **Bounded counts** (levels completed is a small integer): the Gaussian model is rough. Either bootstrap by resampling games and then runs within games (PML1 4.7.3; rough with few games), or analyse "level k completed" as a rate with Beta posteriors (PML1 5.2.6.2).
10. **If the goal is a decision** (which harness to keep) and not a claim, PML2 34.3 says "pick the winner" is the optimal rule in the symmetric case and that hypothesis-test sizing "may often recommend sample sizes that are much larger than necessary" (p.1119-1120). State which of the two the study is for.

### 7.4 Cautions
- **Tuning on reporting games.** DL p.119, UDL p.133, PML1 p.13, MML p.262 all say the same thing. Freeze the stall threshold and price rule on the development games before any reporting-game run; do not go back after seeing reporting results. With few development games prefer a conservative setting within noise of the best (PML1 4.5.5.1).
- **Selection on noise.** E[max] ≥ max E (PML2 35.2.5.2). The chosen threshold's development score is optimistic; so is "best of three runs". Report means, never best runs.
- **Regression to the mean.** Not treated by name in any of the six books. The nearest material is shrinkage in hierarchical models (PML2 3.6.2), the optimizer's curse, and selection bias (ECI 6.29-6.30). Application: games picked because the earlier run stalled on them will tend to do better on any re-run, including R0. The earlier run must not serve as the R0 baseline; R0 must be re-run in the same batch.
- **Time confound.** Do not compare against runs from another date or harness version (PML2 36.6).
- **Pooling across games.** Compare within game first (ECI kidney stones, p.94-95, 111-112).
- **Post-hoc measures and many looks.** ECI p.7; PML2 p.1096. A "significant" result on a secondary measure found after the fact deserves the PML1 p.202 treatment: with low prior odds, most such findings are false.
- **Null results.** Three repeats on a few games cannot show absence of an effect (ECI p.216).
- **Negative control.** Pre-trigger behaviour should match across arms (PML2 36.7.1). A placebo arm (deliberation not tied to stalls) would separate interruption from detection (ECI Example 6.15; PML2 p.1095).

### 7.5 Coverage in one line each
- PML2: strong on both halves (decision theory, VPI, A/B sizing, bandits, BAMDP, restarts in local search, RCTs, placebo checks, paired and hierarchical analysis).
- PML1: little on recovery beyond basic decision theory; strong on comparing two systems (paired Bayesian t-test, ROPE, bootstrap, permutation test, p-value cautions, validation/test).
- ECI: nothing on the decision itself apart from 8.2; the main source for what a single-factor or bundled intervention identifies, randomisation, SUTVA, Simpson's paradox, selection bias.
- UDL: introductory RL only; one useful remark on exploring starts; validation/test rule.
- DL: no RL; validation/test rule, standard error, "choose the metric ahead of time".
- MML: no RL or testing; variance of a difference, standard error, test-set leakage.
