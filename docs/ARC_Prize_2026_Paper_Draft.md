# Accurate Feedback Is Not Enough: An Exploratory Study of Action-Effect History in ARC-AGI-3

**Working manuscript — September 25, 2026**  
**Authors and affiliations:** [To be supplied by the authors]  
**Evidence snapshot:** repository commit `13ad6e0`, including archive commit `3e54968`.  
**Intended venue:** ARC Prize 2026 Paper Track; eligibility and submission-format compliance remain unverified.

> Editorial note: This is a first empirical paper draft, not a submission-ready manuscript. Detailed Kaggle requirements were not accessible during drafting. The results below concern a small development experiment, not an official competition score, hidden-set evaluation, or production-scale certification. Future research is explicitly separated from completed work.

## Abstract

Interactive agents must do more than select legal actions: they must use observations of action consequences to improve subsequent decisions. We investigate whether a short, deterministic action-effect history helps a language-model agent avoid ineffective repetition and complete levels in ARC-AGI-3. We compare a corrected common baseline with an otherwise identical agent receiving the four most recent action-effect records, computed from its own observed transitions. The study uses Qwen3-VL-30B-A3B-Instruct-FP8 with text-encoded grid observations on three previously exposed development games, two order-reversed blocks, and a twelve-action horizon per episode. All twelve episodes complete technically, totaling 144 policy calls and 144 dispatched actions, with no invalid outputs or dispatch failures. Neither arm completes any levels. The frozen behavioral outcome is inconclusive: pooled immediate-repeat counts are 7/23 for the baseline and 6/24 for the history arm, but only three game–block comparisons are eligible and the sole reduction rests on one opportunity. Exploratory replay reveals repeated clicks accompanied only by bottom-row pixel changes in one game and alternation between ineffective action types in another. These findings motivate separating observable change, informative exploration, and task progress. We provide a hash-verified archive and deterministic evaluator replay, and outline prospective experiments on evidence interpretation and action selection. The results do not establish a general limitation of feedback or a solving improvement.

## 1. Introduction

An agent interacting with an unfamiliar game must infer what its controls do, identify relevant state changes, and select actions that advance an initially uncertain objective. A valid action is not necessarily useful. Similarly, a changed observation need not indicate progress, and accurate feedback need not be used effectively by the policy.

Our development work encountered a concrete version of this problem: agents repeatedly selected coordinate clicks without completing a level. An offline diagnosis of the starting state of development game ar25 found that all nine tested clicks left the observed frame unchanged, whereas individually tested directional actions changed it. This was not an exhaustive click search, and frame changes did not establish progress. It nevertheless motivated testing whether explicit records of attempted actions and observed effects would improve subsequent action selection.

The present study asks:

> Does a short history of exact actions and mechanically measured effects reduce ineffective repetition or improve level completion compared with the existing action-ID-only history?

The contributions are deliberately limited:

1. A controlled development comparison whose only request-level intervention is an action-effect-history field.
2. A reproducible negative solving result and an inconclusive behavioral result, with explicit denominators and reliability accounting.
3. Exploratory examples showing why pixel change and action diversity can diverge from task progress.
4. An auditable evidence workflow that checks semantic consistency as well as file integrity.

We make no claim of state-of-the-art performance or methodological priority. This draft's literature positioning remains to be completed with verified primary sources.

## 2. Setting and experimental scope

The agent receives text-encoded grid observations and a set of legal actions. It returns a structured action identifier and arguments. In the pinned interface, ACTION6 takes integer coordinates, with x denoting column and y denoting row; the other non-reset actions take empty arguments. Interface legality does not specify an action's game-specific meaning.

Our common prompt makes these argument conventions explicit. It is a new baseline, not the unchanged E1S-R parent used in earlier project phases. The experiment also differs from the earlier R8 diagnostic in horizon, number of cases, and removal of separate model-generated prediction and feedback calls. Consequently, comparisons with R8 are contextual rather than controlled treatment estimates.

We study three development games:

| Game | Role | Initial legal actions |
|---|---|---|
| ar25-0c556536 | Design-informed case | ACTION1–7 |
| s5i5-18d95033 | Additional coordinate-only case | ACTION6 |
| wa30-ee6fef47 | Additional non-coordinate case | ACTION1–5 |

All three had prior model exposure in development. ar25 informed the design. The additional cases were selected from development games using initial control availability and a fixed hash tie-break, excluding two other design-informed diagnostic cases. No H1/H2 holdout was used. These cases do not constitute independent validation.

## 3. Method

### 3.1 Policy and controlled comparison

Both arms use Qwen3-VL-30B-A3B-Instruct-FP8 served through vLLM 0.19.0 on one RTX Pro 6000. Decoding uses temperature 0, request seed 0, thinking disabled, and a 128-token completion cap. The common prompt requests a compact action without a rationale; no extra reasoning call is added to the candidate.

The baseline includes the existing grid observation bundle, legal actions, level and state information, history-compaction metadata, and action-ID-only recent history. The candidate receives those same fields plus `action_effect_history`. Removing that field reconstructs the corresponding baseline request for the same supplied observation. During closed-loop execution, however, the arms can reach different states, so their later requests are not expected to remain identical.

### 3.2 Deterministic action-effect records

For each dispatched action, a deterministic tool records its identifier and coordinates, acknowledgement status, measured frame changes, and level change. It distinguishes whether any returned frame differs from the pre-action frame from whether the final returned frame differs. This distinction accommodates transient changes followed by a return to the original observation.

The policy sees at most four records from its own current episode segment. A reset or level transition starts a new segment. Records contain no reviewer object labels, offline-probe results, recommended actions, or hidden engine state. Failed and unknown dispatch outcomes have null effect fields rather than being described as no change.

The records are evidence about observations, not assertions of causality or utility. Their numerical accuracy does not establish that the policy understands them.

### 3.3 Schedule and stopping

The design contains two blocks, each with one baseline/history pair per game. Block 1 runs ar25, s5i5, then wa30, with baseline before history. Block 2 reverses both game order and within-pair arm order. Each episode uses a fresh environment, scorecard, and policy context, with environment seed 0.

Both blocks use request seed 0. Block 2 is an order-reversed replication, not an independent sampled seed. A shared model service can retain service-level state, including cache effects, despite episode isolation.

Each episode permits at most twelve dispatched actions and one policy call per action. It stops on win, game over, invalid output, or failed/unknown dispatch; retries, fallback actions, and deliberate restarts are not part of this intervention. Level completion alone does not end an episode.

The authorized attempt ceiling was 3,600 seconds. The internal first-cell deadline was 3,300 seconds, including installation, startup, execution, evidence writing, and cleanup. Pair admission used a frozen 300-second allowance; this estimate did not override the hard deadline. Interrupted work was required to remain in reliability reporting.

### 3.4 Outcome definitions

**Solving:** levels completed and episode wins. Action diversity and pixel change do not count as solving.

**Immediate repetition:** an opportunity occurs when the preceding acknowledged action produced no final-frame change and no level progress, and the next decision is in a comparable observed state. Comparable states use identical final-frame hashes and level counts. A repeat uses the same action identifier and arguments. This is an observable-state definition, not proof that hidden game state is identical.

For repeat count R and opportunity count O, the rate is R/O when O is positive and is undefined when O is zero. Zero opportunities are not reported as a zero repetition rate.

The frozen comparison requires a positive baseline repetition rate for eligibility. A reduction requires the history rate to be at most half the baseline rate. Eliminating opportunities is reported separately rather than automatically counted as reduction. The overall favorable behavior class requires reduction in at least two of three games in each block, with all pairs complete and no qualifying worsening. Reliability failures take precedence over favorable repetition classifications. Full precedence and worsening rules remain in the archived protocol.

The frozen solving-signal rule requires more levels in the history arm in both blocks for at least two games. These are decision rules for an exploratory study, not significance tests.

### 3.5 Evidence and replay

The independent evaluator rebuilds requests from preceding observations, recomputes effect records, checks response and token constraints, and validates dispatch and episode accounting. It also checks terminal-state consistency, scorecard closure, and cleanup evidence.

The archive contains 55 files: 42 returned output files plus associated approval, launch, and evaluation records. File hashes bind the archive contents; evaluator replay adds semantic checks beyond those hashes. A visual replay is generated from the same archive. It shows observed frames only, without invented intermediate animation.

Reproducing the evaluation means recomputing it from fixed archived evidence. It does not mean a fresh model run will reproduce the same actions.

## 4. Results

### 4.1 Completion and reliability

All six pairs and twelve episodes completed, totaling 144 policy calls and 144 acknowledged actions. Every episode reached its twelve-action cap. Neither arm completed a level. Both arms recorded zero invalid outputs, dispatch failures, interruptions, and closure failures.

The independent evaluator classified the study as technically complete, behaviorally inconclusive, and having no demonstrated solving improvement.

### 4.2 Repetition outcomes

| Block | Game | Baseline repeats/opportunities | History repeats/opportunities | Frozen pair class |
|---|---|---:|---:|---|
| 1 | ar25 | 3/11 | 3/11 | Not reduced |
| 1 | s5i5 | 0/0 | 0/0 | Ineligible |
| 1 | wa30 | 0/0 | 0/1 | Ineligible |
| 2 | wa30 | 1/1 | 0/1 | Reduced |
| 2 | s5i5 | 0/0 | 0/0 | Ineligible |
| 2 | ar25 | 3/11 | 3/11 | Not reduced |

The pooled descriptive rates are 7/23 (0.304) and 6/24 (0.250). Only three comparisons are eligible; the only reduction is based on one opportunity. Pooling mixes game-specific trajectories and treatment-dependent denominators. We therefore do not interpret the pooled difference as a reliable treatment effect, and do not treat individual actions as independent experimental samples.

### 4.3 Runtime and accounting

Rounded recorded times were 403 seconds for model startup, 735 seconds for the supervisor, and 737 seconds from the first cell. These are nested measurements, not additive costs. The observed account-wide GPU quota-counter increase was approximately 747.6 seconds. Exact per-attempt charged GPU time was unavailable; the counter delta is not presented as an independently verified billing receipt.

## 5. Exploratory trajectory analysis

The following findings are post hoc. They do not replace the frozen evaluation.

**Small changes can remove repetition opportunities without demonstrating progress.** In s5i5, every action changed one or two bottom-row cells. The history arm clicked the same coordinate, (11,10), twelve times per episode. Because the raw final frame changed, the no-change repetition metric produced no opportunities. The spatial pattern is consistent with a counter-like display, but the archive alone does not establish its causal role or irrelevance. This example exposes a boundary of the metric, not an error in the raw pixel comparison.

**Switching action types can leave the agent equally stuck.** In ar25, the history arm alternated clicks with ACTION7; neither produced observed changes. The action-type repetition count fell from eight to zero per episode, while exact immediate repeats remained three out of eleven opportunities and level completion remained zero. Thus, a favorable movement in an auxiliary metric would not have demonstrated improved solving.

**Broader action coverage can remain unproductive.** In wa30, the history arm cycled through ACTION1–5. Greater action diversity did not produce a completed level within the horizon.

**Temperature zero did not imply identical service outputs.** The wa30 baseline's first requests were byte-identical between blocks, yet responses differed. The cause was not isolated. This observation cautions against interpreting the two blocks as deterministic duplicates or as an adequate estimate of run-to-run variability.

## 6. Discussion

The experiment distinguishes three requirements that should not be conflated:

1. Accurate records of observations and dispatched actions.
2. Correct interpretation of those records.
3. Action selection that converts interpretation into progress.

The evidence supports the first requirement for this run, but does not identify which later requirement explains the lack of improvement. The model may overlook history, misinterpret effects, fail to generate useful alternatives, or remain limited by perception or objective inference. The present design does not discriminate among those mechanisms.

The study also illustrates a measurement problem: defining ineffective repetition exclusively through unchanged pixels misses repeated actions accompanied by small display changes. The remedy should not be to retrospectively delete those pixels and claim a better result. A future study should preserve raw differences and separately validate any task-relevance abstraction. A supposedly incidental region could encode remaining resources or other essential information.

Technical reliability is necessary for interpreting agent behavior but is not solving competence. Successful cleanup, replay, and accounting cannot substitute for completed levels. Conversely, the absence of progress in this short study does not establish that action-effect feedback is generally ineffective.

## 7. Limitations

- Three previously exposed development games provide no hidden-set generalization evidence.
- The design-informed ar25 case introduces explicit selection dependence.
- Twelve actions may be insufficient for meaningful progress in some games; horizon adequacy was not demonstrated.
- One model, one representation, one prompt family, and one short history length were tested.
- Identical seeds and order reversal do not provide independent samples, and service variability remains unquantified.
- Repetition denominators depend on observed trajectories and can exclude changed-but-unproductive actions.
- Identical grids can conceal different internal state; changed grids can include changes unrelated to the chosen action.
- Behavioral differences are descriptive; this study is not powered to establish equivalence or a small treatment effect.
- No object-grounding, causal-model, subgoal, recovery, or deliberate-restart intervention was evaluated here.
- This is neither a scored competition submission nor production one-scorecard/110-distinct-game certification.

## 8. Prospective research program

The next experiment should isolate the transition from accurate feedback to action choice, rather than adding a full planning architecture at once.

First, construct frozen diagnostic fixtures testing whether the model can recover the attempted action, coordinates, observed effects, and uncertainty from a record. These should include transient changes and unknown outcomes. Model comprehension must be measured with actual model responses, not inferred from fixture unit tests.

Second, compare history alone with a separately frozen instruction to consider previously ineffective attempts and informative legal alternatives. Do not reveal the ar25 probe results. Preserve useful repetition, charge all exploration to the budget, and keep completion as the solving outcome.

Third, independently evaluate object localization, contours, color-invariant geometry, reflection, and temporal correspondence before integrating a perception tool. Subsequent experiments can test action-effect hypotheses, verified subgoals, failure attribution, and recovery.

Finally, study deliberate restarting as a budgeted choice. The agent must learn what resets and what persists, explain why another attempt should differ, and be evaluated on total completion including failed attempts. Neither death nor no-change actions should receive an unexamined universal penalty: both can occur during informative exploration or rational recovery.

These are proposals, not results or claims of implemented capability.

## 9. Conclusion

In a bounded three-game development study, adding accurate recent action-effect records did not demonstrate improved level completion. The behavioral result was inconclusive, despite technically complete execution and reproducible evaluation. Archived trajectories show that action diversity, pixel changes, and reduced action-type repetition can occur without progress. The immediate research need is to test how an agent interprets evidence and uses it to choose informative actions, while keeping reliability, behavior, and solving outcomes distinct.

## Artifact and source notes

The following repository artifacts support this draft at commit `13ad6e0` of [dcw06/ARC-AGI-3](https://github.com/dcw06/ARC-AGI-3/tree/13ad6e0):

- `reports/action_effect_history_v1_results.md`: result summary and exploratory observations.
- `reports/action_effect_history_v1_live_evaluation.json`: independent evaluation, episode metrics, and final classifications.
- `reports/action_effect_history_v1_protocol.md`: design and metric definitions. Its draft header is historical; use the approval/launch records and frozen review-r3 lock to establish the executed version's authority.
- `research/action_effect_history_v1/contract.py`: common prompt, history construction, and request settings.
- `evidence/action-effect-history-v1-complete.zip` and `reports/action_effect_history_v1_archive.json`: archived evidence and inventory.
- `scripts/archive_action_effect_history_v1.py`: integrity verification and evaluator replay.
- `scripts/build_action_effect_history_v1_replay.py` and `reports/action_effect_history_v1_replay/index.html`: visual replay generator and generated page.

Archive SHA-256: `a67b69557d835f8076e3b80674c29c0032b95ec2dbd9a70f032ed85af54654cb`.

From the matching source revision with its dependencies installed:

```bash
python -m scripts.archive_action_effect_history_v1 replay
python -m scripts.build_action_effect_history_v1_replay --check
```

Public accessibility, redistribution permissions, and clean-checkout dependency installation must be checked before an artifact-availability claim is made in the final paper. A private visual-replay link is not a substitute for reviewer-accessible artifacts.

## Editorial checklist before submission — remove from final manuscript

- Verify the [official paper-track requirements](https://www.kaggle.com/competitions/arc-prize-2026-paper-track), including eligible subject matter, judging criteria, required submission method, deadlines/timezone, page limit, template, anonymity, artifact policy, and AI-assistance disclosure requirements. No specific requirement is asserted here.
- Confirm whether this focused negative-result study fits the track, or whether the paper needs a larger conceptual contribution and additional prospective evidence.
- Add verified primary-source citations for ARC-AGI-3, the exact model and serving system, and closely related work on interactive feedback, exploration, and hierarchical planning. Do not assert novelty until this review is done.
- Supply author names, affiliations, contribution statements, funding/conflicts, and an accurate disclosure of AI assistance where appropriate or required.
- Add two archive-derived figures: the isolated intervention and paired trajectory examples. Label every post-hoc annotation; do not draw unobserved intermediate frames.
- Have a teammate reproduce the archive and page from the pinned revision in a clean environment.
- Verify all numerical statements against the machine-readable evaluation; retain undefined rates as undefined.
- Audit any released evidence for credentials, personal data, and redistribution restrictions.
- Do not describe the earlier 0/11 text/image diagnostic as level-completion evidence without first establishing its scoring definition; it is deliberately excluded from this draft's quantitative results.
- Decide whether to submit this bounded study or extend it with one prospectively frozen action-selection experiment. Do not retrofit new outcomes into the original protocol.
