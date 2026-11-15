# Reading notes: recovery (reset, undo, replay) in exploration and LLM-agent papers

Reader notes for the single-factor recovery study (R0 control, R1 stall detection, R2 priced recovery with automatic replay).
Written 2026-11-14. All quotes are copied from the plain-text copies under
`library/<name>/text.txt`.

Conventions used below:
- "DOC:" marks what the document states (quotes are exact; section given).
- "INFERENCE:" marks my own reading or a design consequence that the document does not state.
- Titles were checked against the list I was given. All eight match. No fetch failed (the first attempt used a shell loop that passed the arguments wrongly; the retry worked for every document).

Versions read: Go-Explore arXiv v6 (16 Sep 2021, the pre-print, not the Nature text); LATS v3 (6 Jun 2024); Reflexion v4 (10 Oct 2023); ReAct v3 (10 Mar 2023); Voyager v2 (19 Oct 2023); BAMCP v4 (18 Dec 2013); Plan2Explore v2 (30 Jun 2020); VIME v4 (27 Jan 2017, PDF).

---

## 1. Go-Explore, "First return, then explore" (2004.12919)

**What it is.** An exploration algorithm family that keeps an archive of visited states grouped into "cells", returns to a chosen archived state, then explores from it; tested on Atari and a simulated robot task.

**How much I read.** Main text in full, Methods 0.1 to 0.9 in full, Supplementary Information 0.10 to 0.19 in full, Extended Data figure and table captions. Skipped: both reference lists and the individual rows of the robotics state-representation tables. Table columns are flattened in the text copy, so the column assignment of table values is as I read it.

### 1.1 How "return" works

There are two variants and they return in different ways.

(a) Returning without a policy: restore the saved simulator state. No actions are executed.
- DOC (main, "The Go-Explore family of algorithms"): "The inner state of any simulator can be saved and restored at a later time, making it possible to instantly return to a previously seen state."
- DOC (Fig. 1 caption): "(b) Return to the selected state, such as by restoring simulator state or by running a goal-conditioned policy."
- DOC (main, robotics): "For this problem, Go-Explore returns by restoring simulator state, explores by taking random actions, and assigns states to cells with an easy-to-provide domain-knowledge-based mapping (Methods)."
- DOC (SI 0.12): "Restoring simulator state is a highly efficient method for returning to previously visited states, as it both removes the need to replay the trajectory towards a previously visited state as well as the need to train a policy capable of doing so reliably."

(b) Policy-based Go-Explore: a goal-conditioned policy executes actions in the environment to get back.
- DOC (main, "Policy-based Go-Explore"): "When returning, instead of restoring simulator state, it is possible to execute a policy conditioned on (i.e. told to go to) the state or cell to return to, which we call policy-based Go-Explore. While returning to a state in this manner is less efficient than restoring simulator state (the actions required to return to a state need to be executed in the environment), there are nevertheless advantages to doing so."
- DOC (Methods 0.7): "In addition, the "go" step now involves executing actions in the environment (as explained below), and each actor independently tracks whether it is in the "go" step or the "explore" step of the algorithm."
- DOC (Methods 0.7): "Here, policy-based Go-Explore relies on its goal-conditioned policy to reach the selected state, which enables it to be applied without assuming access to a deterministic or restorable environment during the exploration phase. It is exceedingly difficult and practically unnecessary to reach a particular state exactly, so instead, the policy is conditioned to reach the cell associated with this state, referred to as the goal cell".
- DOC (Methods 0.7): the policy does not aim at the distant goal directly. "Instead, the actor is iteratively conditioned on the successive cells traversed by the archived trajectory that leads to the goal cell." The archived trajectory is followed in "soft-order": consecutive repeated cells are collapsed, and "given a window size N_w=10, if the agent is supposed to reach a specific goal cell in this trajectory and it reaches that or any of the subsequent 9 cells in this trajectory, the goal is considered met."

(c) Replaying the stored action sequence in the environment is NOT a return method used in this paper.
- The stored action sequences exist. DOC (main): "when returning without a policy, Go-Explore stores and maintains the highest-scoring trajectory (i.e. sequence of actions) to each cell." They are used as demonstrations for the later robustification phase, and (Methods 0.7) by self-imitation actors that "replay the trajectory associated with the cell they select from the archive" in policy-based Go-Explore. That replay is for training the policy, not the mechanism of the "go" step.
- The only mention of replay as a way to return is the SI 0.12 sentence quoted above, which names it as the thing restoring makes unnecessary.
- INFERENCE: our R2 "automatic replay of the stored verified action prefix" corresponds to none of the paper's implemented return methods. It is the third option the paper names but skips: open-loop replay, executed and paid for in the real environment. Do not cite Go-Explore as having tested it.

### 1.2 What it assumes about the environment

- Restore variant: a simulator whose state can be saved and restored, and a deterministic exploration phase. DOC (SI 0.16): "we take advantage of the fact that the deterministic exploration phase is unaffected by reward scale". DOC (Extended Data Table 1 caption): "(b) For the exploration phase, only "Max episode length", "End of episode", and "Action repeat" apply." (my reading: sticky actions, which are in that table, are therefore not applied in the restore-based exploration phase; the policy-based variant does train with sticky actions, SI 0.13). DOC (SI 0.14): Atari games "are inherently deterministic, making it possible to achieve high scores by simply memorizing state-action mappings or a fixed sequence of actions".
- Policy variant: neither determinism nor restorability (Methods 0.7 quote above), but it was "only tested with domain knowledge" (SI 0.17) on two games.
- DOC (main): "Leveraging the ability of simulators to restore states provides many benefits that increase the efficiency of Go-Explore, but it is not a requirement."

### 1.3 Cells, and how a cell to return to is chosen

Cells:
- DOC (main): "In practice, non-trivial environments have too many states to store explicitly. To resolve this issue, similar states are grouped into cells, and states are only considered novel if they are in a cell that does not yet exist in the archive (Fig. 1d)."
- DOC (main): "Good state-to-cell-mapping parameters result in a representation that strikes a balance between two extremes: lack of aggregation (e.g. one cell for every frame, which is computationally inefficient) and excessive aggregation (e.g. assigning all frames to a single cell, which prevents exploration)."
- Without domain knowledge (Methods 0.2): the frame is converted to grayscale, downscaled to width w <= 160 and height h <= 210, and pixel depth reduced to d <= 255 levels. w, h, d are re-chosen at intervals by a random search that maximises normalised entropy of how recent frames fall into cells divided by a penalty for missing a target number of cells. The sample is up to 10,000 recently seen frames.
- With domain knowledge (Methods 0.3): Pitfall uses room number and discretised x,y; Montezuma adds keys held and level. "in this work it was extracted from pixels through small hand-written classifiers". Robotics uses gripper position in 0.5 m voxels, touching or grasping flags, whether the object is in the target shelf, door and latch positions.
- Replacement rule. DOC (main): "if a state maps to an already known cell, but is associated with a better trajectory (e.g. higher performing or shorter, see Methods), that state and its associated trajectory will replace the state and trajectory currently associated with that cell." I did not find a more detailed replacement rule in the Methods of this pre-print version.

Selection of the cell to return to:
- DOC (main): "first, it probabilistically selects a state to return to from the archive (Fig. 1a)"; Fig. 1: "guided by heuristics that prefer states associated with promising cells."
- DOC (Methods 0.4): "During the exploration phase, the selection probability of a cell at each step is proportional to its selection weight."
- DOC (Extended Data Table 1): weight W = 1/sqrt(C_seen + 1) for the Atari and robotics runs without a return policy, and W = 1/(0.5 C_steps + 1) for policy-based Atari. "C_seen is the number of exploration steps in which that cell is visited ... C_steps is the total number of steps the agent spend in the cell."
- Montezuma with domain knowledge adds (Methods 0.4) the number of horizontal neighbours in the archive, a key bonus, and the level: W_mont_domain = 0.1^(L-l) (W + W_location), where l is the cell's level and L the highest level in the archive. So cells on the highest level reached are favoured by a factor of 10 per level.
- INFERENCE: Go-Explore does not return to "the furthest state". It samples among all archived cells, weighted towards rarely visited ones (and towards the highest level only when domain knowledge is added). The count-based weight means a cell that has been explored from repeatedly without yielding anything is chosen less often. That is a soft way of leaving a dead end without ever labelling it one.

After returning (Methods 0.4): "once a cell is returned to, exploration proceeds with random actions for a number of steps (100 in Atari, 30 in robotics), or until the end of episode signal is received from the environment." "the probability of repeating the previous action is 95% for Atari and 90% for robotics."

### 1.4 Detachment and derailment

- DOC (abstract): "the main impediment to effective exploration originates from algorithms forgetting how to reach previously visited states ("detachment") and from failing to first return to a state before exploring from it ("derailment")."
- DOC (SI 0.10): "We define detachment as losing track of interesting areas to explore from. Here, "interesting areas to explore from" refers to states for which we have evidence (e.g. a low number of visits) that they could lead to the discovery of new areas of the environment. "Losing track" means that the algorithm stops trying to visit those areas prematurely, despite the fact that they are not thoroughly explored yet."
- DOC (SI 0.10): "We define derailment as when the exploratory mechanisms of the algorithm prevent it from returning to previously visited states."
- DOC (SI 0.10): "as the policy needs to take an increasingly large number of correct actions to reach unexplored areas of the environment, it becomes increasingly likely that a state-agnostic exploration mechanism ... will cause the policy to take one or more exploratory actions that prevent it from reaching the distant state it sought to return to, thus stifling exploration."
- DOC (SI 0.10), the proposed cure: "have an algorithm exhibit separate exploration probabilities depending on whether it is in a well-known area of the environment, meaning the probability of exploratory actions should be low, or in an unknown area of the environment, meaning the probabilities of exploratory actions should be high."
- DOC (main): "By first returning before exploring, Go-Explore avoids derailment by minimizing exploration in the return policy (thus minimizing failure to return) after which it can switch to a purely exploratory policy."
- Evidence offered for derailment in a baseline (SI 0.11): in the robotics intrinsic-motivation control, in 18 of 20 runs "the count associated with the "grasp" step is at least 10x smaller than that associated with the "touch" step".

### 1.5 Robustification and stochasticity

- DOC (main): "returning without a policy also means that this exploration process, which we call the exploration phase, does not produce a policy robust to the inherent stochasticity of the real world. ... After the exploration phase is complete, these trajectories make it possible to train a robust and high-performing policy by Learning from Demonstrations (LfD) ... Because it produces robust policies from brittle trajectories, we call this process the robustification phase".
- DOC (main): "the robustification phase consists of a modified version of the "backward algorithm" ... To ensure that the trained policy becomes robust to environmental perturbations, during robustification stochasticity is added to these environments following current community standards".
- DOC (SI 0.16): the backward algorithm "operates by placing the agent close to the end of the trajectory and running PPO until the performance of the agent matches or exceeds that of the demonstration. Once that is achieved, the agent's starting point is moved closer to the trajectory's beginning and the process is repeated." Ten demonstrations from different exploration runs were used per Atari game.
- DOC (SI 0.14): sticky actions mean "there exists a 25% chance that the current action of the agent is ignored, and the previous action is executed instead"; all reported scores use sticky actions plus up to 30 random no-ops.
- Limits the authors state (SI 0.12): a trajectory found with restores can depend on luck and may be impossible to robustify (the "busy highway" example). Policy-based Go-Explore "can keep track of the success rate towards each cell in the archive ... it is possible to not overwrite cells on the other side of the highway until the policy has learned to return to those cells reliably", but this was not implemented: "studying the effectiveness and exact implementation details of such a mechanic is a topic for future research."
- Scale: exploration ran 2 billion frames on Atari (longer on three games) and robustification 10 billion (Methods 0.6).

### 1.6 Cost of returning, and whether it is counted

- Restore variant: the frames that would have been needed to get back are not executed and not counted. DOC (SI 0.17): "While Go-Explore does "skip" frames by reloading simulator state, we argue that these frames would also be skipped in almost any scenario where Go-Explore is practically applied, as it should be possible to save and restore the state of a modern simulator."
- DOC (Methods 0.6): "In this work, sample complexity is always reported in terms of raw Atari frames, so that the number of actions can be obtained by dividing by 4."
- Policy variant: returning is executed in the environment, so its frames are part of the frame count, and the authors argue it is not pure overhead. DOC (Extended Data Fig. 7 caption): "the number of cells that are discovered while returning is about twice that of the cells discovered when taking random actions after returning, indicating that the frames spent while returning to a previously visited cell are not just overhead required for moving towards the frontier of yet undiscovered states and training the policy network, but actually provide a substantial contribution towards exploration as well." DOC (Methods 0.7): "no distinction is made between data gathered during the "go" step and data gathered during the "explore" step, meaning policy-based Go-Explore can discover new cells or update existing cells while returning."
- Scale of the policy variant: 97,728 points on Montezuma "after 12 billion frames" (SI 0.13, 0.17).
- The paper gives no per-return cost, no rule for when returning is worth its cost, and nothing that prices a reset.

### 1.7 Stall handling inside Go-Explore (directly relevant to R1)

Policy-based Go-Explore has an explicit no-progress counter with two stages (Methods 0.7):
- DOC: "If the agent fails to reach the current goal for some number of steps e^T_t (defined below), this entropy term is increased", where "t-hat is the number of steps the agent has taken since it last reached a goal (for returning) or discovered a new cell (for exploring)".
- DOC: "While executing the "explore" step, the threshold e^T_t has a fixed value of 50. While returning, the threshold e^T_t equals the number of actions that the followed trajectory required to move from the previously reached goal cell to the current goal cell."
- DOC: "Lastly, to prevent actors from spending many time steps without making any progress (possibly because the agent reached a state from which further progress is impossible), we terminate the episode early if the current goal is not reached within 1,000 steps after we have started to increase entropy (while returning), or if no new cells are discovered for 1,000 steps (while exploring)."
- DOC: "Whenever the current exploration goal is reached, or if the goal is not reached for some number of steps (here 100), a new exploration goal is chosen."
- DOC (SI 0.13): "This entropy increases the exploration performed by policy-based Go-Explore only when necessary, thus largely avoiding the problem of derailment."

Unrecoverable states are acknowledged (Methods 0.5, robotics control): "Because it is possible (though rare) for the agent to place the object out of reach, a per-episode time limit is necessary to ensure that not too many training frames are wasted on such unrecoverable states."

A caution about what "best state" means (Methods 0.5): tracking the maximum score across all cells "fails in games where rewards can be negative (e.g. Skiing): in these cases, it is possible that the maximum scoring cell in the archive inevitably leads to future negative rewards, and is therefore not a good representation of the maximum score achievable in the game."

A side observation on cheap deaths (SI 0.18): "Because there are no penalties for losing a life, policy-based Go-Explore learns to sacrifice lives in order to bypass hazards or to return to the entrance of a room more quickly."

Reporting practice (Methods 0.1, 0.5): scores averaged over 50 exploration runs for the focus games; "To avoid cherry-picking lucky rollouts that can bias scores upward substantially, we also exclude work that only provided the maximum score achieved in an entire run".

---

## 2. LATS, Language Agent Tree Search (2310.04406)

**What it is.** Monte Carlo tree search over an LLM agent's thought and action steps, with an LLM value function and self-reflection, tested on HotPotQA, HumanEval and MBPP, WebShop, Game of 24.

**How much I read.** All of the main text, Appendix A to D in full, and the prompt appendices E to G. Skipped: the reference list.

### 2.1 What it assumes about reverting

- DOC (Sec. 1): "Our key insight underpinning LATS is adapting Monte Carlo Tree Search (MCTS), inspired by its success in model-based reinforcement learning (Silver et al., 2017) and the observation that many LM tasks allow reverting to earlier steps, to language agents".
- DOC (Sec. 2, "Tree-based search"): "Note that though tree-based search necessitates an environment model that can expand from an arbitrary state (Vodopivec et al., 2017), often requiring extra training in RL (Hafner et al., 2023), such a problem does not exist for most LM tasks. This is because we can conveniently revert to any state by setting the input to be the context and the corresponding previous output from the LM for many tasks."
- DOC (Sec. 3.1): "In this paper, consistent with other LM agent methods such as ReAct and Reflexion (Shinn et al., 2023), we focus on decision-making tasks where reverting between iterations is feasible."
- DOC (Sec. 3.2): "Normally, the major shortcoming of MCTS is that it requires an environment model to undo previous steps and form a searching tree, which could be a strong assumption. However, this limitation does not exist for many LM tasks, as we can conveniently reset to any step by simply copy-pasting historical text input. Such a special property is the key motivation of our work."
- DOC (Sec. 4.2): "While standard MCTS and RAP (Hao et al., 2023) rely on internal dynamics models to facilitate simulation, LATS uses environment interaction and does not require a world model."

### 2.2 Is reverting free?

The paper never says "free" or "no charge". What it says about cost:
- DOC (Appendix B, "Computational cost"): "Additionally, there exists a minor cost from querying the environment, which we find to be trivial for the environments we study. Most LM-based environments involve API-based tools, which are inexpensive and fast to use."
- All cost accounting is in LLM terms: number of sampled trajectories k, nodes expanded n per step, tokens (Sec. 5.4, Tables 9 and 10: "sample complexity (i.e., asymptotic token cost)"). No table counts environment steps or reverts, and no budget is charged for them. The stopping rule is "until the task is successfully completed or a computational limit is reached after sampling k trajectories" (Sec. 4.2), with k = 50 (HotPotQA), 30 (WebShop, Game of 24), 8 (programming), n = 5 children per expansion.
- The mechanism of reverting a stateful environment such as WebShop is not described beyond the two sentences above ("setting the input to be the context", "copy-pasting historical text input").

### 2.3 What the authors say where reverting is not possible

- DOC (Sec. 6, "Limitations and future directions"): "Second, LATS assumes the ability to revert to earlier states in decision-making environments, which may not be universally applicable in all possible environments." and "Finally, the reversion property is feasible in many real-world applications".
- DOC (Appendix B): "Assumption of environment reversion in decision-making. Since our method is based on Monte Carlo Tree Search and is model-free, one limitation of LATS on decision-making tasks is that it requires the agent to be able to revert to earlier states in the environments. However, this reversion property is feasible in many real-world environments and applications (despite being not universally applicable in all possible environments), including programming (HumanEval [Chen et al., 2021]), web search (WebShop [Yao et al., 2022]), text-based manipulation tasks (Alfworld [Shridhar et al., 2020]), and LMs with tool use (ToolBench [Qin et al., 2024]). Therefore, we believe that leveraging the reversion property is not a shortcoming but rather a feature".
- DOC (Appendix B): "Moreover, some environments might not easily support rollbacks to previous states. However, the design of LATS is flexible and can be adjusted to various resource constraints."
- They offer no method for the non-revertible case.

### 2.4 Check of the plan's sentence

Plan sentence: "Language Agent Tree Search backtracks freely because its environments reset at no charge".

Verdict: the substance is supported, the wording is stronger and slightly different from the paper.
- Supported: LATS requires reverting to earlier states and charges nothing for it. Its budgets and cost tables count LLM samples, nodes and tokens only.
- Not literally stated: "at no charge". The authors' words are "a minor cost from querying the environment, which we find to be trivial for the environments we study" (Appendix B).
- Different operation: the paper's assumption is reverting to any earlier state ("revert to any state", "reset to any step"), which is stronger than a reset to the start.
- Suggested wording that the quotes support: "LATS assumes the environment can be reverted to any earlier state and counts no cost for doing so; its authors describe the cost of querying the environment as 'trivial for the environments we study' and list the reversion assumption as a limitation (Sec. 6, Appendix B)."

### 2.5 Other points bearing on recovery

- Reflection is triggered only at failed terminal nodes. DOC (Sec. 4.2): "Upon encountering an unsuccessful terminal node, p_theta is prompted with the trajectory and final reward to provide a verbal self-reflection ... We store both failed trajectories and corresponding reflections in the memory." There is no stall detector inside a trajectory other than the depth limit (7 or 6 on HotPotQA, 15 WebShop, 8 programming, 5 Game of 24).
- DOC (Appendix C, depth ablation): "We find that most questions can be answered within four steps, and using a greater number of steps tends to force the agent into local minima and rarely improves success."
- DOC (Sec. 5.3, WebShop): "Similar to Shinn et al. (2023), we find that generated reflections are often generic and do not provide useful feedback, resulting in a tendency for the agent to become stuck in local minima."
- Reflection ablation (Sec. 5.4): removing self-reflection drops HotPotQA exact match from 0.63 to 0.58.
- I found no report of variance across repeated runs.

---

## 3. Reflexion (2303.11366)

**What it is.** An LLM agent that, after a failed trial, writes a verbal self-reflection, stores it, and retries the task from the start with the reflections in context.

**How much I read.** All of the main text and Appendices A to D. Skipped: the reference list.

### 3.1 What triggers a reflection or a new trial

- Decision-making (AlfWorld), DOC (Sec. 4.1): "AlfWorld tasks naturally require a self-evaluation step as the environment can only signal if a task is complete. To achieve fully autonomous behavior, we implement two self-evaluation techniques: natural language classification using an LLM and a hand-written heuristic. The heuristic is simple: if the agent executes the same action and receives the same response for more than 3 cycles, or if the number of actions taken in the current environment exceeds 30 (inefficient planning), we self-reflect. In the baseline runs, if self-reflection is suggested, we skip the self-reflection process, reset the environment, and start a new trial. In the Reflexion runs, the agent uses self-reflection to find its mistake, update its memory, reset the environment, and start a new trial."
- So the trigger ends the trial: detection leads to reflection, then an environment reset, then a fresh trial. The baseline arm uses the same trigger and the same reset but skips the reflection.
- HotPotQA, DOC (Sec. 4.2): "between trials, we use exact match answer grading using the environment to give a binary success signal to the agent. After each trial, the self-reflection loop is employed".
- Programming (Sec. 4.3): failure on self-generated unit tests (at most 6 tests).

### 3.2 How many trials

- AlfWorld: 12. DOC (Sec. 4.1 Results): "ReAct + Reflexion learns to solve additional tasks by learning in 12 consecutive trials. In the ReAct-only approach, we see that performance increase halts between trials 6 and 7."
- HotPotQA, DOC (Sec. 4.2 Results): "we allowed the agent to gather experience and retry on failed tasks until it produced 3 consecutive failed attempts on the particular task."
- WebShop, DOC (Appendix B.1): "after only four trials, we terminate the runs as the agent does not show signs of improvement".
- Algorithm 1 loops "while M_e not pass or t < max trials" (as printed).
- Trials are not charged against any budget. Results are plotted against trial number.

### 3.3 What carries over between trials

- Only the reflection text. DOC (Sec. 3, "Memory"): "the trajectory history serves as the short-term memory while outputs from the Self-Reflection model are stored in long-term memory."
- DOC (Sec. 3): "In practice, we bound mem by a maximum number of stored experiences, Omega (usually set to 1-3) to adhere to max context LLM limitations." AlfWorld: "we truncate the agent's memory to the last 3 self-reflections (experiences)." Programming: "a max memory limit of 1 experience."
- No action sequence is stored or replayed. After the reset the agent acts again from the initial state, guided by the reflections. In the Appendix B example the second trial is shorter because the reflection named the right location, not because anything was replayed.
- Ablation (Sec. 4.2 Analysis): carrying over the last trajectory itself ("episodic memory") helps less than a reflection; "self-reflection improves learning by an 8% absolute boost over the episodic memory learning advantage."

### 3.4 Results and limits that bear on recovery

- DOC (Sec. 4.1 Results): "ReAct + Reflexion significantly outperforms ReAct by completing 130 out of 134 tasks using the simple heuristic to detect hallucinations and inefficient planning."
- DOC (Sec. 4.1 Analysis): "A common error in baseline failed AlfWorld trajectories is when an agent thinks that it has possession of an item but does not actually have the item. The agent proceeds to execute several actions in a long trajectory and is not able to backtrack its actions to find the mistake."
- DOC (Sec. 4.1 Analysis): the reset-only baseline shows "a ReAct-only agent converging at a hallucination rate of 22% with no signs of long-term recovery." DOC (Sec. 4.2): "ReAct-only, CoT-only, and CoT (GT)-only implementations fail to probabilistically improve on any tasks, meaning that no failed tasks from the first trial from any of the baseline approaches were able to be solved in subsequent trials using a temperature of 0.7".
- DOC (Appendix B.1): "We conclude that Reflexion is unable to solve tasks that require a significant amount of diversity and exploration."
- DOC (Sec. 5): "it may still succumb to non-optimal local minima solutions."
- DOC (Sec. 4.3 ablation): without a reliable evaluator "the agent must participate in all iterations of the run without the option to return early, performing harmful edits to the implementation." Accuracy fell to 52% against a 60% baseline.

---

## 4. ReAct (2210.03629)

**What it is.** Prompting an LLM to interleave free-text thoughts with environment actions; tested on HotPotQA, FEVER, ALFWorld, WebShop.

**How much I read.** Abstract, Sections 1 to 6 in full, Appendix A (including A.3), B.2, the headers of the D.2 ALFWorld trajectories, and the start of E.1. Skipped: the prompt appendix C, the FEVER and WebShop trajectories in D, most of the example trajectories in E.1, and the reference list.

Findings:
- No stall detector, no reset or retry, and no reuse of a verified action sequence inside the agent. Each task is one attempt.
- A fixed step cap with a hand-off to another method, justified from data. DOC (Sec. 3.2): "ReAct -> CoT-SC: when ReAct fails to return an answer within given steps, back off to CoT-SC. We set 7 and 5 steps for HotpotQA and FEVER respectively as we find more steps will not improve ReAct performance". Footnote 3: "Of all trajectories with correct final answers, those with 7 steps on HotpotQA and 5 steps on FEVER only take up 0.84% and 1.33% respectively."
- Loops are named as the characteristic failure. DOC (Sec. 3.3): "we note that there is one frequent error pattern specific to ReAct, in which the model repetitively generates the previous thoughts and actions, and we categorize it as part of "reasoning error" as the model fails to reason about what the proper next action to take and jump out of the loop". Footnote 6: "We suspect that this could be due to the sub-optimal greedy decoding procedure". Table 2 puts "Reasoning error" ("Wrong reasoning trace (including failing to recover from repetitive steps)") at 47% of sampled ReAct failures on HotPotQA.
- DOC (Sec. 3.3): "Non-informative search, which counts for 23% of the error cases, derails the model reasoning and gives it a hard time to recover and reformulate thoughts."
- DOC (Appendix D.2.2, action-only agent): "From there on, the model is unable to recover, and is stuck repeating the same sequence of commands."
- Recovery by outside intervention only. DOC (Appendix A.3): "by simply removing a hallucinating sentence in Act 17 and adding some hints in Act 23, ReAct can be made to change its behavior drastically to align with these human thought edits and succeed in the task."
- Spread: ALFWorld success over six prompt variants was 57% on average and 71% for the best (Table 3); the worst ReAct trial was 48% (Sec. 4 Results).
- I did not find an ALFWorld per-episode step limit in the parts I read.

---

## 5. Voyager (2305.16291)

**What it is.** A GPT-4 agent for Minecraft that writes code as actions, with an automatic curriculum, a skill library of verified programs, and an iterative prompting loop.

**How much I read.** Abstract, Sections 1 to 2.3 in full, 3.1 to 3.4, Section 4, Appendix A.1 (pseudocode), A.3.1 to A.3.3, B.1 to B.3. Skipped: the full prompts (A.3.4, A.4, A.5), Section 3.5 beyond a skim, related work, B.4 item lists, and the reference list.

Findings:
- Giving up is a fixed retry count. DOC (Sec. 2.3): "If the agent gets stuck after 4 rounds of code generation, then we query the curriculum for another task." Pseudocode (A.1): "# try at most 4 rounds before moving on to the next task", followed by `curriculum_agent.add_failed_task(task)`.
- The failed task is recorded and may come back. DOC (Sec. 2.1): the curriculum prompt includes "Previously completed and failed tasks, reflecting the agent's current exploration progress and capabilities frontier". DOC (Sec. 4): "there are still cases where the agent gets stuck and fails to generate the correct skill. The automatic curriculum has the flexibility to reattempt this task at a later time."
- The decision to move on rests on a verifier. DOC (Sec. 3.4): "Self-verification is the most important among all the feedback types. Removing the module leads to a significant drop (-73%) in the discovered item count. Self-verification serves as a critical mechanism to decide when to move on to a new task or reattempt a previously unsuccessful task."
- Reuse of verified sequences. DOC (Sec. 1): the loop "repeats the process until a self-verification module confirms the task completion, at which point we commit the program to the skill library". DOC (Fig. 4): "Each time GPT-4 generates and verifies a new skill, we add it to the skill library". Only verified programs are stored. DOC (Sec. 3.4): "Voyager w/o skill library exhibits a tendency to plateau in the later stages."
- A no-progress trigger appears in a baseline. DOC (B.2, AutoGPT re-implementation): "If three consecutive subgoals do not result in acquiring a new item, we replan by rerunning the task decomposition."
- Death costs almost nothing and there is no reset. DOC (B.1): "If the bot dies, it is resurrected near the closest ground, and its inventory is preserved for uninterrupted exploration."
- The budget is counted in prompting iterations (160, or 50 for zero-shot tests), not environment actions. Three runs per condition.
- Verification can be wrong. DOC (Sec. 4): "Occasionally, self-verification module may also fail, such as not recognizing spider string as a success signal of beating a spider."

---

## 6. BAMCP (1205.3109)

**What it is.** Monte Carlo tree search for Bayes-adaptive planning: at each real step, sample one model from the posterior per simulation and search over future histories.

**How much I read.** Abstract and Sections 1 to 7 in full, the supplementary note "BAMCP versus Gittins indices" and the figure captions S1 to S5. Skipped: the proof of Theorem 1, the inference details for the infinite grid, and the reference list.

Findings:
- The paper has no finite budget and nothing explicit on how the remaining horizon changes the value of exploring. The setting is infinite-horizon and discounted; the discount is what prices exploration. DOC (Sec. 1): "The discount factor pressures the agent to favor short-term rewards, but potentially costly exploration may identify better rewards in the long-term. This conflict leads to the well-known exploration-exploitation trade-off."
- How information is valued. DOC (Sec. 1): "augment the regular state of the agent with the information it has acquired about the dynamics. ... The agent starts in the belief state corresponding to its prior and, by executing the greedy policy in the BAMDP whilst updating its posterior, acts optimally (with respect to its beliefs) in the original MDP." There is no separate novelty bonus: an informative action is worth exactly the extra discounted reward it is expected to enable later (Eq. 2).
- The lookahead is cut where the discount makes the rest negligible. DOC (Sec. 3.2): the rollout runs "to some fixed depth (determined using the discount factor)"; Algorithm 1: "if gamma^d Rmax < epsilon then return 0". Experiments use gamma = 0.95.
- The authors note a mismatch between what is optimised and what is scored. DOC (Sec. 5.1): "we measured the total undiscounted reward over many steps. ... In fact, we are optimising a different criterion – the discounted reward from the start state – and so we might expect this evaluation to be unfavourable to our algorithm."
- Stopping exploration can be optimal. DOC (supplementary, Fig. S5): "finding good rows can be expensive so the agent might settle on sub-optimal rows (as in Bandit problems where the Bayes-optimal agent might settle on sub-optimal arm if it believes it likely is the best arm given past data)."
- Over-exploration as a failure of bonus-style methods. DOC (Sec. 4): BOSS algorithms "are generally quite robust, but suffer from over-exploration." DOC (Sec. 5.1): "If more samples are employed to build the merged model, SBOSS actually becomes too optimistic and over-explores, degrading its performance." DOC (Sec. 4), on BEB: "behavior in the early steps of exploration is very sensitive to the precise exploration bonuses".
- The planner's own simulations run in sampled models, not the real environment, so they cost no real actions. The domains mention a "reset state" (Grid5) but resets are not priced.

INFERENCE: the document supports the principle "exploration is worth only what it is expected to return within what remains", through discounting. It does not state the finite-budget version. If the plan cites BAMCP for "the remaining budget changes the value of exploring", say that this is the finite-horizon reading of the Bayes-adaptive formulation, not a result in the paper.

---

## 7. Plan2Explore (2005.05960)

**What it is.** A reward-free exploration agent that trains a latent world model and plans, inside the model, towards states where an ensemble of one-step predictors disagrees.

**How much I read.** Abstract and Sections 1 to 7 in full. Skipped: the appendix and the reference list.

Findings:
- Nothing on resets, the remaining horizon or an action budget. The exploration phase has a fixed length (1M steps, or 1000 episodes in the few-shot setting) with 1000-step episodes.
- A novelty measure that goes to zero when there is nothing left to learn. DOC (Sec. 1, "Challenges"): "An ideal exploration objective should seek out inputs that the agent can learn the most from (epistemic uncertainty) while being robust to stochastic parts of the environment that cannot be learned accurately (aleatoric uncertainty). This is formalized in the expected information gain (Lindley, 1956), which we approximate as the disagreement in predictions of an ensemble of one-step models. ... The disagreement is positive for novel states, but given enough samples, it eventually reduces to zero even for stochastic environments because all one-step predictions converge to the mean of the next input".
- DOC (Sec. 3.1): "Once the data is added to the training set, however, the models will converge towards more similar predictions, and the disagreement decreases. Eventually, once the whole environment is explored, the models should converge to identical predictions." And: "The intrinsic reward is non-stationary ... once certain states are visited by the agent and the model gets trained on them, these states will become less interesting for the agent".
- Retrospective versus expected novelty. DOC (Sec. 1): "This approach misses out on efficiency by operating retrospectively, that is, the novelty of inputs is computed after the agent has already reached them. ... Hence, it seeks out previously novel inputs that have already been visited and would not be novel anymore. Instead, one should directly seek out future inputs that are expected to be novel." DOC (Sec. 5.4): the one-step "Retrospective Disagreement" baseline does worse; "Our agent achieves superior performance".
- DOC (Sec. 3.2): information gain equals total uncertainty minus expected data noise: "the information gain corresponds to the epistemic uncertainty, i.e. the reducible uncertainty of the model".

---

## 8. VIME (1605.09674)

**What it is.** An intrinsic reward equal to the information gained about a Bayesian neural-network dynamics model, added to the task reward.

**How much I read.** Sections 1 to 5 in full (pages 1 to 8). Skipped: the appendix (pages 9 to 11) and the reference list. PDF text only; equations are partly garbled.

Findings:
- Nothing on resets or on how the remaining horizon changes the value of exploring. The setup is "a finite-horizon discounted Markov decision process" (Sec. 2.1), but the exploration weight eta is a fixed hyperparameter that does not depend on time left.
- Definition of information gain as belief change. DOC (Sec. 1): agents "take actions that result in states they deem surprising—i.e., states that cause large updates to the dynamics model distribution." DOC (Sec. 2.2): "the KL divergence from the agent's new belief over the dynamics model to the old one ... This KL divergence can be interpreted as information gain." Reward: r'(s_t, a_t, s_t+1) = r(s_t, a_t) + eta D_KL[p(theta | xi_t, a_t, s_t+1) || p(theta | xi_t)] (Eq. 3).
- The measure is used relatively, not absolutely. DOC (Sec. 2.5): "we normalize it by division through the average of the median KL divergences taken over a fixed number of previous trajectories. Rather than focusing on its absolute value, we emphasize relative difference in KL divergence between samples. This accomplishes the same effect since the variance of KL divergence converges to zero, once the model is fully learned."
- Exploration weight trade-off. DOC (Sec. 3): "Setting eta too high clearly results in prioritizing exploration over getting additional external reward. Too low of an eta value reduces the method to the baseline algorithm".
- Raw prediction error is a worse signal than belief change. DOC (Sec. 3): "using l2 errors does not perform well. In contrast, VIME performs much better".
- Link to compression (Sec. 2.4): the same quantity is "compression improvement", how much shorter the history can be described after the update.

---

## 9. Design implications (all INFERENCE unless a quote is attached)

### 9.1 R1, stall detection

Signals:
1. "No new state hash" is the exact-state extreme of Go-Explore's cell idea, and Go-Explore warns against it: "lack of aggregation (e.g. one cell for every frame ...)" on one side, "excessive aggregation" on the other. A raw 64x64 hash will count any changed pixel as new. A move counter, energy bar, timer or animation in the frame would make every frame new, and the detector would never fire. Aimless but non-repeating wandering has the same effect. Decide before the runs which abstraction the hash is taken over (for example, mask the regions that change on every action), record both the raw and the abstracted hash, and state the choice with the results.
2. Add the repetition signal that Reflexion used and ReAct documents as the typical failure: the same action with the same response more than a set number of times, or a short cycle of states.
3. "No change to the agent's memory" is the discrete analogue of VIME's information gain (belief change) and Plan2Explore's disagreement (zero when nothing more can be learned). Two cautions. First, VIME uses the quantity relative to its recent median, not as zero or non-zero; an LLM memory can be reworded without any gain in information, so "any edit" overstates learning. Count only changes of substance, for example a hypothesis confirmed, refuted or added. Second, Plan2Explore's point about retrospective novelty applies: a stall detector fires only after the actions are spent. The forced deliberation is where expected information should be weighed (what untested action or hypothesis remains from here, and what would it buy).
4. Go-Explore keeps different no-progress counters for returning and for exploring (steps since the last goal was reached, versus steps since the last new cell). In R2 the automatic replay will produce no new hash and no memory change by construction. The R1 counter must be suspended during replay, and replay needs its own check (did the replayed step produce the stored state).

Thresholds, with their precedents:
- Reflexion: same action and same response "for more than 3 cycles", or more than 30 actions in the task.
- Voyager: 4 rounds of code generation; its AutoGPT baseline replans after 3 consecutive subgoals with no new item.
- Go-Explore (policy-based): escalate after 50 steps with no new cell, give up the current exploration goal after 100, terminate after 1,000. While returning, the escalation threshold is the number of actions the stored trajectory needed for that segment.
- ReAct: the cap was set from the distribution of successful trajectory lengths (under 1.4% of correct trajectories reached the cap).
- None of these numbers transfers as a number. The Go-Explore ones sit inside budgets of billions of frames, and Reflexion's 30 is a third of our whole 100-action cap. What transfers is the method: (i) ReAct's, set the threshold from our own data, for example a high percentile of the gap between successive progress events in levels that were completed; (ii) Go-Explore's, scale the allowed slack to the known length of the segment.
- Go-Explore's two-stage response (first explore harder, only later terminate) matches R1 as planned: the trigger forces a deliberation, not a reset. Reflexion's trigger forces a reset. If R1 is described with a citation to Reflexion, note this difference.

Risks:
- A forced step without a reliable signal can hurt. Reflexion's ablation without the test evaluator fell below baseline ("performing harmful edits"), and Voyager lost 73% of discovered items without self-verification. If the R1 trigger has many false alarms, the forced deliberations may push the model to abandon a workable line. Log every trigger with what the model then did, so false alarms can be counted afterwards.
- A reset without new information helps little. In AlfWorld, Reflexion's reset-only baseline improved until trials 6 to 7 and then stopped; in HotPotQA the retry-only baselines solved nothing further ("no failed tasks from the first trial from any of the baseline approaches were able to be solved in subsequent trials"). Make sure the deliberation writes down what the dead end was before any reset, and measure whether the post-reset run repeats it.

### 9.2 R2, pricing a reset and automatic replay

What does not transfer:
- LATS: every expansion presumes a revert that is not charged. In our setting, reverting to a node at depth d costs one RESET plus d replayed actions, so expanding n children of that node costs about n x (d + 2) counted actions. With n = 5 this exhausts a 100-action cap in a few expansions. Tree search in the real environment is only affordable to depth one where a game offers an undo action (act, look, undo: two actions per probe).
- Reflexion: up to 12 trials of up to 30 actions each, all resets uncharged. One Reflexion-style task could use several times our whole cap.
- Voyager: death preserves the inventory and budget is counted in LLM calls.
- Go-Explore with restores: the return is explicitly not counted ("skip" frames). Policy-based Go-Explore does pay for returns but learns its return policy over billions of frames, and benefits from discoveries made on the way back. An exact replay of a known prefix in a deterministic game discovers nothing, so for us the return is pure cost.
- Robustification: needs training at a scale we do not have. Its lesson is narrower and does transfer: a stored action sequence is "brittle" and valid only under determinism.
- BAMCP's planning simulations are free because they run in a sampled model. Any "simulate before acting" step for us is free only if it happens in the model's head.

What does transfer:
1. Store the shortest verified action sequence per checkpoint and replace it when a shorter one is found (Go-Explore's archive rule: "higher performing or shorter"). Shorter prefixes directly lower every later return cost.
2. Verify during replay. Go-Explore's open-loop trajectories are reliable only because its exploration phase is deterministic; its SI proposes tracking "the success rate towards each cell" where it is not. Check the state after each replayed action (or at set checkpoints) against the stored one, stop the replay on a mismatch and hand control back to the model. Record replay divergences as a measure. Establish per game whether replay is deterministic before the main runs.
3. Do not assume the furthest state is the right place to return to. Go-Explore samples return cells and warns that the best-scoring cell can be one that "inevitably leads to future negative rewards"; its robotics task has "unrecoverable states". If the dead end was entered by an irreversible action at step j, replaying the whole prefix puts the agent back in the dead end and pays for it. "Verified" should mean verified as progress (for example, a level completion confirmed by the environment), not merely "was executed". Within a level, the deliberation should choose the cut point of the prefix.
4. The price rule. The Bayes-adaptive view (BAMCP) is that an exploratory or recovery step is worth only the reward it is expected to enable in what remains; the paper gives this through discounting, not a budget, so the finite-budget form is ours. With B actions left, a reset costing 1 and a replay of L actions, a reset can pay only if B - 1 - L exceeds a plausible minimum number of actions to gain something from the restored state. Late in the budget the rule should forbid resets. BAMCP's note that a Bayes-optimal agent "might settle on sub-optimal" options is the same point.
5. Compare the reset with the alternatives at their action prices: an undo (one action per step undone, where available), walking back by hand, or the reset plus replay. Go-Explore's agent learned "to sacrifice lives ... to return to the entrance of a room more quickly" when deaths were free. A one-action RESET can likewise be the cheapest way back to a level start, and the rule should allow that case.
6. The score compares actions per level with a human baseline, so replayed actions count against the level they are spent on even when the budget can afford them. Whether the price rule should use budget left, score effect, or both is a choice to fix before the runs.

### 9.3 Measures

- Dead-end loss corresponds to Go-Explore's counter "number of steps the agent has taken since it ... discovered a new cell", read at the moment of reset or game over. It needs the same fixed definition of a progress event as the R1 signal, chosen before the runs. Report it separately for resets the model chose, resets that followed an R1 trigger, and game overs. Also report the actions between an R1 trigger and the following reset.
- Return cost. Go-Explore's two failure names map onto it: derailment is a return that takes more actions than the known prefix (report return cost divided by the stored prefix length), and detachment is never getting back (report the share of resets after which the furthest state was not regained within the budget). Under R2 with a deterministic game the ratio is 1 by construction, so R1 versus R2 on this measure is partly mechanical. The informative comparisons are levels completed and score at the fixed budget.
- "Regained the furthest state" needs an abstraction too. Go-Explore: "It is exceedingly difficult and practically unnecessary to reach a particular state exactly", so it tests the cell. A model returning by hand in R0 or R1 may reach an equivalent state with a different exact hash; under an exact-hash test its return cost would be overstated or undefined.
- If R2 lets the model cut the prefix short of the furthest state (9.2 point 3), the return-cost measure must be defined for the chosen target, with the furthest state reported separately.
- Add: number of replay divergences; whether the post-reset trajectory re-enters the same dead end; false-alarm rate of the R1 trigger.
- Spread. Go-Explore averages over 5 to 100 runs and excludes work reporting only a best run; ReAct's ALFWorld numbers differ by 14 points between the mean and the best of six prompt variants (57 versus 71) and by 23 between worst and best. Report the mean and the full spread across repeats for each condition, never the best run. Voyager used three runs; I found no spread reported in LATS.

### 9.4 Wording to fix in the plan

- LATS: replace "backtracks freely because its environments reset at no charge" with wording tied to the quotes in 2.4.
- Go-Explore: do not attribute action replay as a return method to the paper; it returns by restoring simulator state (uncounted) or by a learned goal-conditioned policy (counted).
- BAMCP, Plan2Explore, VIME: none of them prices a reset or varies the remaining budget. Cite them only for the definition of information gain as belief change (VIME, Plan2Explore) and for valuing exploration by its expected future return (BAMCP).
