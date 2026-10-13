# ARC-AGI-3 research questions and results so far

**Historical results snapshot: October 11, 2026. New research proposal: October 12, 2026.** Completed experiments, qualified study closure and prepared studies are distinguished below. Technical completion means the execution and evidence checks passed; it does not mean the research hypothesis succeeded. Closing a study with a qualification does not waive a failed certification. Private evidence, account details and seed values are excluded.

## Overall research question

| Question | What the work has established | What remains unestablished |
|---|---|---|
| Can an agent use observations, action effects, memory and hypothesis testing to solve ARC-AGI-3 games reliably? | A working bounded runtime; reproducible development experiments; specific control, grounding and history-reading weaknesses. | A solving improvement from the proposed interventions, generalization to unexposed games, and full production certification. |

## Foundations and architecture comparisons

| Study | Research question | Work completed and result | Status |
|---|---|---|---|
| Phase 0: baseline and lifecycle | Can the agent run safely and produce a valid competition artifact? | Implemented bounded execution, legal actions, evidence journals, cleanup and scorecard finalization. Public baseline: **OfficialRHAEPercent 0.08**; pipeline validation only. | Complete. [Record][p0] |
| Phase 0F / M0: representation and model viability | Which observation representation and model can fit the runtime constraints? | Defined ordered-frame evidence and raw/feature boundaries; profiled three FP8 models. Qwen3-VL-30B-A3B became the provisional primary, with 8B as fallback. | Complete runtime comparison; no solving superiority established. [Record][m0] |
| Phase 1: four-cell architecture study | Do engineered features or a tool workspace improve over a stateless raw-observation agent? | Built and ran stateless/workspace × raw/features comparisons, including counterbalanced whole-run validation. Game-performance contrasts tied at zero. | Complete; E1S-R remains provisional primary, E0 fallback. [Record][p1] |
| Phase 2: richer evidence and memory admission | Does the baseline failure identify a specific missing capability worth testing? | Two parent runs reproduced an 80-action trajectory without level completion, including a 75-click streak. No single registered capability was justified. | Closed with **no treatment admitted**; not evidence that memory cannot help. [Record][p2] |
| Phase 3: hypotheses, probes and action queues | Does retained evidence justify a hypothesis store, discriminating probes or action queues? | Reviewed the reproduced failure against E5/E6 admission criteria; neither treatment qualified. | Closed with no treatment; architecture holdout not applicable and not run. [Record][p3] |
| Phase 4: scaling and certification | Can the development pipeline sustain many clients with strict action and lifecycle checks? | V13 handled **110 clients and 7,582 real requests/actions** without policy, parser or transport failures; zero levels completed. | Development lifecycle passed. **110 distinct games on one production scorecard remain uncertified.** [Record][p4] |

## Grounding, controls and closed-loop behavior

| Study | Research question | Main result | Interpretation |
|---|---|---|---|
| Transient-frame comparison | Does exposing an intermediate frame improve subsequent decisions? | Six development episodes, 120 actions; zero levels in both arms. All 57 decisions receiving an exposed frame matched their paired control action. | No demonstrated benefit under this protocol. [Record][transient] |
| Grounding diagnostic | Can the model read cells, localize regions and identify changes? | Exact answers: grid reading **2/4**, localization **0/4**, changes **0/4**. | Technical pass with substantial grounding errors. [Record][grounding] |
| Coordinate diagnostic v2 | Does explicit indexing wording repair coordinate confusion? | Baseline **15/28** correct; explicit indexing **16/28**. | Promotion threshold not met; larger-grid extraction remains a lead. [Record][coordinates] |
| Integrated scaffold v1 → v2 | Does object inventory → target → prediction → feedback support useful actions? | V1 stopped at invalid/truncated inventory. V2 made inventory feasible, then stopped at an invalid first decision; controls executed eight actions with zero progress in each run. | Full scaffold efficacy was **not observed**; output burden and grounding were separated. [V1][integrated1], [V2][integrated2] |
| Paired perception and Stage A inspection | Are images more effective than raw grids for object localization? | Text and image arms each detected **0/11** reference objects at the frozen overlap threshold. Offline overlays inspected localization and coordinate errors. | No demonstrated image advantage on these five correlated boards. [Results][perception], [Inspection][stagea] |
| Stage B structured-target pair | Does committing to one visible target improve target-to-action binding? | Two clicks per arm; zero object contacts, visible changes or completed levels. Target/click consistency passed, but all four changed-frame judgments were wrong. | Consistent coordinates did not establish grounding or solving benefit. [Record][stageb] |
| Prompt-example diagnostic v4 | Do concrete example coordinates contaminate action selection? | On 15 retained initial observations, two games followed the original and relocated example coordinates. | Evidence of example copying in those cases; zero actions dispatched. [Record][diagnostic] |
| Closed-loop prompt comparison | Does removing concrete examples reduce repetition and improve solving? | 15 matched game pairs, 600 actions. Adjacent repeats fell **95.1% → 62.5%**; example-coordinate clicks fell **210/220 → 0/218**. Zero level gains in both arms. | Less repetition, without demonstrated solving improvement. [Record][closedloop] |
| Action-effect history v1 | Does short action/effect history reduce repeats after no observed change? | Six episode pairs, 144 actions; repeats **7/23 → 6/24**; zero levels. | Frozen verdict **inconclusive**; only three pairs supplied eligible opportunities. [Record][history] |

## Evidence comprehension and observation probes

| Study | Research question | Main result | Decision / limit |
|---|---|---|---|
| Comprehension v1 | Can the model read legal controls and identify actions already tried without effect? | 1,308 answered calls. Available-action accuracy **0.955**; coordinate availability **0.568**; tried-unchanged **0.341**. | Prerequisites for evidence-guided action selection not met. [Record][ec1] |
| Comprehension v2: controls | Does an explicit instruction to intersect the control rule with legal actions help? | Legal-coordinate accuracy **0.517 → 0.883**. | Improved, but below the **0.90** criterion; not promoted. [Record][ec2] |
| Comprehension v2: history | Do information-equivalent normalized records improve history reasoning? | Outcome classification **0.819 → 0.895**; observed effects **0.762 → 0.866**; tried-unchanged **0.533 → 0.525**. | Better entry reading did not repair multi-entry reasoning; not promoted. [Record][ec2] |
| Comprehension v3: computed controls | Does deterministic control metadata make legal-coordinate selection reliable? | Accuracy **0.859 → 1.000**. | Clear interface improvement; the tool supplies the tested relationship. [Record][ec3] |
| Comprehension v3: history eligibility | Does marking eligible history entries repair tried-unchanged selection? | Accuracy **0.477 → 0.664**; qualifying-step selection **0.367 → 0.625**. | Improved but below the **0.70** floor, even with tool assistance. [Record][ec3] |
| Comprehension v3: matched history alteration | Can irrelevant action history interfere with legal-control answers? | Replacing ACTION6 history events fixed **16/60** reference answers and broke none. | Evidence of history interference within these synthetic cases. [Record][ec3] |
| Action-selection probe v1 | Does computed control metadata improve legal responses on retained real observations? | 30 contexts from 15 development games; valid in both passes: reference **11/30**, metadata **24/30**. | 14 improved, one regressed; zero game actions. [Record][probes] |
| Action-selection probe v2 | Does the advantage persist with a shared explicit output contract? | Reference **30/30**, metadata **29/30**. | No metadata advantage here. Cross-run changes do not isolate the contract's causal effect; legality is not usefulness. [Record][probes] |

Comprehension v2 and v3 answered all **8,004** and **6,054** scheduled calls respectively; both were technically complete. Their withheld instances test the synthetic generator, not general game-solving ability.

## The four current research tracks

| Track | Research question | Work completed | Current scientific status |
|---|---|---|---|
| **1 — Structured hypothesis testing** | Does explicit hypothesis → discriminating action → feedback improve action selection and completed levels? | Two RTX PRO 6000 sessions, each with 145 model requests and 144 offline actions; pooled analysis and post-fix evidence audit. Original setup failure and all consumed attempts preserved. | **Closed with technical qualification (recorded owner decision).** No demonstrated solving improvement; action selection inconclusive. Original evaluator passed both sessions; post-fix certification fails F1 because finalization evidence is missing. Blocks were identical, not independent replicates. [Results][track1], [Audit][track1audit], [Closure][trackstatus] |
| **2 — Evidence-linked memory** | Does deterministic, evidence-linked memory preserve accessible facts beyond recent history, better than state-keyed raw retrieval at a common budget? | Draw 2 used after the final design freeze; two technically valid RTX PRO 6000 sessions answered all **5,760** study calls; registered pooled analysis completed once. Draw 1 retired and preserved. | **Stage 1 complete.** Memory preserves access versus recent history; no advantage over state-keyed retrieval demonstrated. Unsupported-claim margin and comprehension floor met. Owner nonce publication remains outstanding for reproducibility. [Results][track2] |
| **3 — Stagnation supervision** | Does reflection at detected stagnation improve recovery compared with continuation and equally budgeted periodic reflection? | Frozen detector, three-arm design, independent evaluator, CPU checks and scripted engine rehearsals. | **No successor GPU study.** The selected controls cannot certify the proposed false-interruption claim; claim scope and audit decisions remain open. Earlier failed attempt preserved. [Protocol][track3], [Limits][track3limits] |
| **4 — Change, progress and subgoals** | Can the model distinguish observed change, confirmed progress and unsupported causal/subgoal claims; does a safeguard help? | One RTX PRO 6000 attempt; all **5,852** questionnaire calls answered; independent evaluation, cleanup and final deadline passed in **1,091 s**. | **Complete; neither arm qualifies for memory or supervision.** Safeguard effects were mixed. One consumed attempt preserved. [Results][track4] |

**Progress:** Tracks 2 and 4 completed; Track 1 closed with a technical qualification; Track 3 remains pending. No new GPU attempt follows from closure.

## Track 1: findings and closure qualifications

| Question / check | Result | Brief reading |
|---|---|---|
| Does the treatment improve solving? | Zero levels in every game, arm and block. | No solving claim on these three exposed development games. |
| Does it improve action selection? | Only ls20 differs: untested action-type rate **0.316 baseline / 0.125 candidate**. | Frozen comparison is inconclusive; the candidate explored less in that game. |
| Are candidate predictions accurate? | **0.000** in all three games. | Structured procedure did not establish accurate effect prediction. |
| Are the two blocks independent evidence? | Actions and raw responses match exactly across sessions. | A determinism check, not an independent replicate. |
| Does retained evidence pass the repaired checks? | Operator's post-fix audit passes request reconstruction, event accounting, canary bounds and F2–F6; scientific aggregates unchanged. | This summary reports that audit; it does not independently reproduce it. |
| Is the lifecycle technically certified? | Original evaluator: complete. Post-fix evaluator: **incomplete (F1)**, missing guarded finalization evidence. | Recorded margins over 2,400 s make an overrun unlikely; they do not certify finalization. |
| What does closure mean? | Owner recorded closure with the qualifications above. | Preserve the findings and all attempts; do not relabel the post-fix certification as passed or authorize another run. |

## Track 2: completed Stage 1 comparison

| Measure | Result | Brief reading |
|---|---|---|
| Old-evidence accuracy: recent / retrieval / memory / full history | **0.000 / 0.900 / 0.892 / 1.000** | Availability explains most of the difference; memory is near its 0.900 exact-reader ceiling. |
| Memory minus recent history | **+0.892**, 95% CI **[+0.875, +0.900]** | Preserves access to old evidence. |
| Memory minus state-keyed retrieval | **−0.008**, 95% CI **[−0.025, 0.000]** | No advantage demonstrated; not proof of equivalence. |
| Unsupported claims: memory minus recent | **−0.012**, 95% CI **[−0.016, −0.010]** | Both frozen margin thresholds met. |
| Reading accuracy when evidence is available | **0.979–0.997**, floor **0.80** | Comprehension floor met. |
| Repeat stability | **576/576** identical answers. | Stable under deterministic decoding. |
| Reproducibility handoff | Withheld nonce publication still outstanding. | Owner action; no seed value is included here. |

The registered verdict is **`memory_preserves_access_not_shown_over_retrieval`**. This synthetic reading study does not establish improved game solving.

## Track 4: what the completed comparison found

| Measure | A: computed record | B: A + safeguard | Brief reading |
|---|---:|---:|---|
| Invalid outputs | 0/2,790 | 0/2,790 | Format reliability was perfect. |
| Families meeting criterion | 2/8 | 2/8 | Overall comprehension readiness failed. |
| Over-claim gates passed | 1/5 | 1/5 | Neither arm passed all safeguards. |
| Uncertainty recall; required ≥0.90 | 0.736 | 0.708 | Both missed uncertain cases. |
| Over-hedging; cap 10% | 7.4% | 10.03% | Safeguard narrowly exceeded the cap. |
| Unsupported causal / usefulness claims | 16/169; 5/115 | 10/169; 0/115 | Some unsupported claims decreased. |
| False “no progress” / false progress | 38/180; 0/125 | 76/180; 3/125 | Other errors increased. |
| Eligible for memory or supervision | **No** | **No** | Selective correction was not demonstrated. |

These are one model-artifact attempt on synthetic instances. Equality of its weights with the earlier Kaggle Model attachment was not established.

## Supporting research questions

| Question | Work completed | Current boundary |
|---|---|---|
| Can experiments use an exact, reproducible offline runtime? | Pinned-image CPU installation checks; direct-publisher GPU smoke test; mounted-wheel hashing, hash-pinned installation and model-tree verification. | Verified for the reviewed runtime and private scope, not arbitrary environments. |
| Can timeout/interruption evidence be trusted? | Protected spawn-to-ownership registration; installer/import descendant process-group cleanup; bounded finalization with a pending barrier and interruption regressions; public r8/private r9 review snapshots rebuilt. | Repaired controller fails overruns while allowing emergency cleanup. Track 1's earlier runs lack the new finalization certification. |
| Can the proposed wheel bundle be redistributed? | 174-artifact inventory; CUTLASS/NVIDIA evidence, Apache NOTICE checks, native-library tracing, metadata checks, worksheet revisions and per-row suggestions. | **174 redistribution decisions remain unresolved.** Private direct-publisher use is a separately scoped assessment. [Worksheet][worksheet], [Decisions][decisions] |
| Can study results be independently reconstructed? | Hash-bound packages, protocols and evaluators; retained failed attempts; archive replay; CPU rehearsals; mandatory runtime-probe checks. | CPU rehearsal is not model evidence. A completed run does not establish a successful intervention. |
| Have we demonstrated general solving improvement? | Development comparisons and synthetic diagnostics identified concrete weaknesses and some interface improvements. | **No.** No qualified new architecture has demonstrated an unexposed-game advantage; production certification remains open. |

## New proposal: object grounding and similarity (October 12, 2026)

| Draft research question | Brief purpose | Status |
|---|---|---|
| Can the agent localize a specified object and choose legal actions that affect it using observed feedback? | Separate apparent background clicks from control-selection and mechanic-understanding failures. | Proposal only; no new experiment authorized. |
| Can it find objects with matching visual structure across position, color or orientation changes? | Test matching with explicit rules and distractors; distinguish appearance from shared function. | Proposal only; references and protocol still to be defined. |

The replay used directional action IDs in two games; s5i5 offered only clicks. The draft therefore evaluates control
choice against each observation's available controls. Full questions, retained action counts and proposed measurements:
[object grounding and similarity proposal](research_questions_object_grounding_similarity_2026-10-12.md).

## Source snapshot

| Collection | Revision used |
|---|---|
| Historical studies, comprehension, runtime and observation probes | `wheelhouse-replacement-audit` — `5a21dd3` |
| Track 1 results, post-fix audit and qualifications | `track1-successor-runtime-v1` — `abb97ed` |
| Track 2 completed Stage 1 analysis and corrected interpretation | `track2-successor-runtime-v1` — `e5b0830` |
| Track 3 preparation | `track3-successor-runtime-v1` — `12adf90` |
| Track 4 completed result | `track4-successor-runtime-v1` — `37748fe` |
| Four-track status and recorded qualified closure | `track-resumption-v1` — `510a180` |

[p0]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/phase0_status.md
[m0]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/phase0f_m0_status.md
[p1]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/phase1_status.md
[p2]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/phase2_execution_status.md
[p3]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/phase3_status.md
[p4]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/phase4_v13_pilot_status.md
[transient]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/phase4_transient_v2_disposition.md
[grounding]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/phase4_grounding_v1_disposition.md
[coordinates]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/phase4_coordinates_v2_disposition.md
[integrated1]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/phase4_integrated_v1_disposition.md
[integrated2]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/phase4_integrated_v2_disposition.md
[perception]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/phase4_perception_v1_r2_disposition.md
[stagea]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/perception_stage_a_v1_findings.md
[stageb]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/perception_stage_b_r8_disposition.md
[diagnostic]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/phase4_diagnostic_v4_results.md
[closedloop]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/phase4_closed_loop_v1_results.md
[history]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/action_effect_history_v1_results.md
[ec1]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/evidence_comprehension_v1_results.md
[ec2]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/evidence_comprehension_v2_results.md
[ec3]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/evidence_comprehension_v3_results.md
[probes]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/control_interface_action_selection_v1_v2_results_2026-10-08.md
[track1]: https://github.com/dcw06/ARC-AGI-3/blob/abb97ed30312fb35fdcc47ff098f797628d2c67a/reports/feedback_action_v1_results.md
[track1audit]: https://github.com/dcw06/ARC-AGI-3/blob/abb97ed30312fb35fdcc47ff098f797628d2c67a/reports/feedback_action_v1_post_fix_audit.md
[trackstatus]: https://github.com/dcw06/ARC-AGI-3/blob/510a180704f0ad7573c12e7e096ccb5ccc83b6bd/reports/four_track_resumption/status_2026-10-09.md
[track2]: https://github.com/dcw06/ARC-AGI-3/blob/e5b0830e7c7dddfad366fc52aabed35079a9f1a6/reports/evidence_memory_v1_stage1_results.md
[track3]: https://github.com/dcw06/ARC-AGI-3/blob/12adf90c9047f40bfab183304034a79ff457b756/reports/stagnation_supervision_v1_protocol_v2.md
[track3limits]: https://github.com/dcw06/ARC-AGI-3/blob/12adf90c9047f40bfab183304034a79ff457b756/reports/stagnation_supervision_runtime_v2_owner_questions.md
[track4]: https://github.com/dcw06/ARC-AGI-3/blob/37748fec1551eda1b7706a8814e46b5d75a3ae13/reports/progress_subgoal_v1_runtime2_attempt1_results.md
[worksheet]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/wheelhouse_redistribution_decision_worksheet_r4.md
[decisions]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/wheelhouse_redistribution_decisions.csv
