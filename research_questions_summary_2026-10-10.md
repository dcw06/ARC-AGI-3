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
| **3 — Stagnation supervision** | Does reflection at detected stagnation improve recovery compared with continuation and equally budgeted periodic reflection? | Two technically complete, accepted RTX PRO 6000 sessions: 1,080 policy calls/actions, 40 reflections and two canaries; pooled analysis and subsequent code-review checks completed. Earlier failed attempts preserved. | **Complete; inconclusive.** No levels completed; no demonstrated triggered-reflection advantage. The false-interruption gate is not certifiable, one apparent recovery was a display-counter artifact, and repeated blocks were identical trajectories. [Results][track3results], [Status][trackstatus] |
| **4 — Change, progress and subgoals** | Can the model distinguish observed change, confirmed progress and unsupported causal/subgoal claims; does a safeguard help? | One RTX PRO 6000 attempt; all **5,852** questionnaire calls answered; independent evaluation, cleanup and final deadline passed in **1,091 s**. | **Complete; neither arm qualifies for memory or supervision.** Safeguard effects were mixed. One consumed attempt preserved. [Results][track4] |

**Progress:** Tracks 2, 3 and 4 completed; Track 1 closed with a technical qualification. Track 3's outcome is inconclusive. Completion does not establish an intervention benefit or authorize another GPU attempt.

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

## Human reference collection (October 13, 2026)

| Development step | Scope | Status |
|---|---|---|
| Strategy annotations and object regions | ls20, s5i5, cd82, ft09, ka59 and sc25; first three levels each | Private worksheet with recorded boards, hover coordinates, full target-coordinate sets, parent/child objects, seven answer fields and JSON/ZIP export. Level-1 draft regions added; ft09 has nine 36-point cells per 324-point parent. Owner answers and assistant-proposed regions remain drafts for independent review. |
| Proposed agent baseline | Identify objects, consider legal controls, verify intended effects, infer working rules and actually complete level 1 | Acceptance criteria and budgets still to be finalized. Human success and questionnaire accuracy do not establish agent completion. No model or GPU run launched. |

The [worksheet guide](reports/manual_strategy_worksheet.md) describes annotation provenance and limitations.
Private logs, boards and answers are excluded from this report and GitHub.

**Next baseline plan (October 15, 2026, draft v2):** [RQ2 controls, RQ4 rule discovery and RQ5 first-level solving](research_plan_rq2_rq4_rq5_v1.md).
It separates unchanged-agent gameplay, prompted component tests and assisted comparisons for the six reviewed
first levels. It distinguishes proposals from execution, conditional inference from discovery, technical from
semantic failures, and record validation from engine replay. Diagnostic scores and assistance narrow possible
explanations without uniquely identifying a cause. The six-game acceptance target and 60/20/20 workload split
are retained. This is a draft study design; no model run or launch is authorized by the plan.

**InternVL identification probe (October 15, 2026):** [Preparation and scoring design](reports/internvl_object_identification_v1_preparation.md).
Six private initial-board image requests are prepared as a prompted component test, with separate
whole-region/part localization scoring and obstacle candidates explicitly distinguished from verified collision
behavior. The model revision is pinned; public code uses synthetic tests and private references stay git-ignored.
The timm supplement is now hash-pinned, a tiny random-model CPU rehearsal passes, and all 24 pinned model files
(17.07 GB) are verified locally. All six actual images pass preprocessing checks; no pretrained inference result
is available. The owner has amended the Kaggle time policy: requested 3,600-second session timeout and
a 3,300-second worker limit, accepting provider overhead beyond one hour. Isolated installation
and CPU execution pass on the pinned Kaggle image; full checkpoint loading and GPU inference remain unverified. The corrected input
dataset is private and ready at version 2 (version 1 preserved); private model version 1 is also ready. Provider
privacy/name/size checks pass. The owner-approved CPU-only check completed once: **216 mounted file hashes match**,
including all 174 original wheels; worker verification took **185.1 s**. Reviewed source/private/offline/accelerator
and image settings match. The pull API omits dataset-version labels; intended versions and actual bytes match.
A support question is drafted but not sent; no GPU job or pretrained-model inference is launched.
**October 16 update:** a separate private CPU installation-check packet was owner-approved and submitted once.
It rehashes all mounts, installs the unchanged 174 pins plus timm into a fresh offline venv,
checks dependency versions/imports, and exercises only a tiny random model on CPU. Proposed limit:
1,800 s session timeout, 1,700 s worker including 120 s cleanup reserve, one attempt, no retries.
Read-back confirms the exact source/image and CPU/private/offline settings; final status is COMPLETE.
All 216 mounted hashes and 175 installed versions match; tiny random-model CPU execution and
cleanup pass, with a post-write witness and independent audit. Worker time: 423.9 s (7m 4s),
not total job time. The single attempt is consumed, with no retries.
[CPU installation results](reports/internvl_object_identification_v1_cpu_install_results.md).
**Final live preparation (October 16):** [readiness report](reports/internvl_object_identification_v1_prelaunch_readiness_2026-10-16.md)
and [time amendment/design r2](reports/internvl_object_identification_v1_protocol_r2.md) bind the
six-request worker, supervisor and replay. All 84 native Linux tests pass, including the active
finalization timer and exact outgoing-notebook/settings guards. The private live template rebuilds
byte-identically with the same image and versioned sources; it refuses before installation or GPU
queries until approval is bound to its exact review hash. Only a declared literal authority-data
cell may be populated after approval; the program, metadata and runtime remain fixed.
The earlier scoped-use approval and pending reservation are preserved, not relabelled as approval
or an active reservation for this new package. The old full-job-cap support draft remains unsent;
provider confirmation is no longer required by the amended budget. The first launch's
exact-hash approval and consumed reservation are retained with its failure evidence.
[External operator repairs](reports/internvl_object_identification_v1_operator_fixes_2026-10-16.md)
close request serialization/target, preflight binding, one-use consumption and readback gaps.
All 20 operator regressions pass on Linux and with optimized Python, in addition to the
84 retained runtime/lifecycle cases. The approved notebook/runtime hash is unchanged.
A fresh passing preflight and single-use claim still precede any future submission.
**Attempt 1 outcome:** the single authorized submission is now ERROR. Saved source and
requested configuration match review, but the first GPU identity command exited 12 because
`libnvidia-ml.so` was unavailable to it. Dataset verification, installation, model loading
and generations never began. The environment omits `LD_LIBRARY_PATH`; a synthetic CPU
loader reproduction supports that failure mechanism, without proving the actual provider
driver was present. Tracked child cleanup passed; GPU cleanup and allocated hardware
remain unverified. The attempt is consumed and preserved, with no retries and no object
score. [Failure record](reports/internvl_object_identification_v1_attempt1_failure.md).
**Repair prepared:** [driver environment fix](reports/internvl_object_identification_v1_driver_env_fix_2026-10-16.md)
retains the required absolute loader paths and adds startup diagnostics. A CPU-only
probe fails through the consumed supervisor and succeeds through the corrected one.
All 108 Linux tests pass; the private successor rebuilds identically and preserves the
consumed history. **Successor submitted once (October 16, 16:51 UTC):** fresh exact-hash
approval, read-only preflight, SDK dry check and a unique single-use claim passed.
Saved version 1 matches the sealed package and requested private RTX configuration;
the attempt is now COMPLETE. Retained evidence verifies one actual RTX PRO 6000,
six pretrained generations, all mounted hashes and cleanup in about 511 worker seconds.
**Identification result: 0/6 valid responses.** Each includes out-of-range coordinates;
the frozen scorer rejects each whole response. This does not establish usable object
localization or obstacle mechanics. Independent token replay passes for all six calls;
the attempt is technically complete, with no repair or additional generation.
[Completed results](reports/internvl_object_identification_v1_results_2026-10-16.md).

**MolmoPoint completed cued-localization test (October 16):** added the separate native-pointing
adapter for `allenai/MolmoPoint-8B`, pinned to `188130f961c8e0888a34e11121a1423c461a01ba`.
Decoded original-image pixels map deterministically to board cells. The owner chose
**plain 448-by-448 nearest-neighbor images with no overlay** for the first test:
six predeclared visual targets, seven pixels per cell and exact occupied-cell hits.
The incomplete-point decoder gap is fixed and reproduced against `5227344`;
117 relevant Linux tests pass. All 33 pinned checkpoint files, including the eight weight
shards, were acquired and verified; the hosted copy also retains the full Apache text.
The private datasets, final package and scoped approval were completed, then one authorized
RTX PRO 6000 attempt ran with an isolated 48-package runtime. All 220 mounted hashes matched.
**Result: 6/6 valid responses and 6/6 exact target hits**, with six normal single-point outputs,
148 completion tokens and a 307.486-second worker lifecycle. Independent CPU replay,
post-write finalization and process/GPU cleanup all pass. The attempt is consumed and preserved;
no retry or game action occurred. This establishes cued localization on these exposed frames;
object discovery, similar-object grouping, obstacle mechanics and gameplay remain untested.
It is not a controlled model comparison with the different InternVL inventory task.
[Completed results](reports/molmopoint_targeted448_results_2026-10-16.md).
[Runtime preparation](reports/molmopoint_targeted448_runtime_preparation_2026-10-16.md). [Targeted input design](reports/molmopoint_targeted448_draft_2026-10-16.md),
[integration and limits](reports/molmopoint_identification_v1_integration_2026-10-16.md).
[Decoder fix and regressions](reports/molmopoint_decoder_sequence_fix_2026-10-16.md).

**Independent discovery and boundaries: completed pilot (October 16):**
[Results](reports/object_discovery_boundaries_v1_results_2026-10-16.md).
Can the model find whole objects without target cues, and can a pixel tool
recover their occupied cells? One attempt used six plain 448px development
boards, native pointing and same-color connected-component masks.

| Measure | Result |
|---|---|
| Valid outputs | 5/6; ls20 reached the 4,096-token cap and receives no partial credit |
| Whole-object masks matching at IoU ≥ 0.5 | 7/37 (18.9% recall); 7/22 proposals match |
| Exact whole-object masks | 3/37 (8.1%) |
| Seed containment, post-hoc diagnostic | Distinct valid seeds inside 18/37 listed whole objects; not boundary correctness |
| Runtime | COMPLETE on one RTX PRO 6000; 490.145-second worker lifecycle; cleanup and independent replay pass |
| Qualification | Provider-generated slug differs from requested identity; the deployment warning remains failed and preserved |

The 37 whole objects and 57 parts came from the owner's confirmation of all
94 unchanged masks and six inventories; one owner review, not independently
established universal object truth. Parts are not pooled into the whole-object
score. This pipeline does not yet demonstrate reliable independent boundaries.
Discovery coverage, semantic grouping and the ls20 length-limited output need
work. The consumed attempt remains preserved; no retry or further GPU attempt
is authorized by these results. [Study plan](research_plan_object_discovery_boundaries_v1.md).

**SAM 2.1 extractor comparison (October 16):**
[Results](reports/sam21_retained_seed_boundaries_v1_results_2026-10-16.md).
Keeping the same 22 valid MolmoPoint seeds and the same reviewed images/masks,
SAM 2.1 Hiera-Large improved mask matching from **7/37 to 12/37** and exact
masks from **3/37 to 6/37**. Highest SAM-predicted quality selected the mask;
references were used only afterward for scoring. Original pixel seeds were
not rounded or corrected. No new MolmoPoint generations or GPU jobs occurred:
five image forwards completed locally on CPU in 104.247 seconds, and saved-logit
replay passed. A loader-only failed CPU attempt is preserved. ls20 remains
invalid, ft09 remains at zero matches, and missing seeds cannot be recovered
by replacing the mask extractor. This improves boundary extraction on these
exposed development frames; reliable object discovery and gameplay remain unshown.
The [empty-mask scoring integration fix](reports/sam21_empty_mask_scoring_fix_2026-10-16.md)
preserves failed empty proposals in the denominator. Its 73 Linux checks pass;
all original nonempty-mask scores are unchanged, with no new inference.

**Controllable-granularity segmentation (October 16):**
[Implementation and remaining runtime work](reports/granularity_segmentation_integration_2026-10-16.md).
UnSAMv2 / UnSAMv2+ and Semantic-SAM now have separate retained-point and
automatic whole-image adapters. Each granularity is evaluated separately;
automatic discovery processes ls20 without requiring MolmoPoint seeds.
Raw-mask replay and the existing whole-object scorer are connected. Synthetic
CPU checks alone do not establish model accuracy. Checkpoint acquisition is now
complete; backend-specific runtime qualification is summarized below. No new
GPU job ran.
The [upstream contract corrections](reports/granularity_upstream_contract_fixes_2026-10-16.md)
validate the four pinned legacy links, enforce UnSAMv2's single returned mask,
and disable redundant Semantic-SAM backbone downloads. One-image smoke mode
is implemented. [Checkpoint preparation and one-image results](reports/granularity_runtime_preparation_2026-10-16.md)
now record real UnSAMv2 / UnSAMv2+ seeded and automatic CPU inference on sc25 at
granularity 0.1: all four runtime checks and saved-output replays pass, but none
matches a reviewed whole object at IoU ≥ 0.5. All three checkpoints are acquired
and byte-pinned; Semantic-SAM's isolated dependencies, native extension builds
and offline imports now pass. Its portable runtime also passes clean-prefix
relocation, native imports and all 99 version checks. Model construction and CUDA inference remain
pending. The six-board comparison has not started. The Linux CPU suite passes
101 tests without failures or skips; no GPU job was launched. The owner has
approved private staging only. The first upload was interrupted after WSL
restarted and is preserved. The separately authorized Windows attempt transferred
all 12 files and received a successful creation response, but verification still
returns 403 and the dataset is absent from the owner catalogue. It stopped
without retry; attachment verification and final GPU-package review remain pending.

**October 17 scoring audit:** the [three evaluation fixes and retained-evidence audit](reports/granularity_evaluation_integrity_fixes_2026-10-17.md)
integrate the owner scoring policy, require an externally pinned reference
manifest and bind SAM seed frames to actual PNG bytes. All six retained SAM
boards pass the evidence audit; saved logits and all four UnSAM smoke outputs
replay under the committed retrospective freeze. Totals remain SAM 12/37 matches
and 6 exact, components 7/37 and 3 exact, and each UnSAM smoke 0/6. No new inference
or GPU work occurred; the audit does not make the historical freeze prospective.

**October 18 next experiment:** [initial geometry assistance](reports/initial_geometry_assistance_v1_preparation_2026-10-18.md)
compares retained automatic geometry with owner-reviewed starting geometry in
short paired episodes. All six initial boards and 12 two-action CPU rehearsals
replay exactly; the latest suite has 70 passing regressions without skips.
The [r2 provenance correction](reports/initial_geometry_automatic_provenance_fix_2026-10-18.md)
adds committed reconstruction of the automatic arm from native pointing and raw
SAM evidence, with protocol-bound hashes and 43 passing CPU regressions.
These use a scripted policy, with no LLM gameplay results. The bounded live
runner and private review r4 are now prepared; fresh lock-bound gameplay
approval and single-use launch authority remain pending.
[Review fixes](reports/initial_geometry_assistance_v1_preparation_2026-10-18.md#review-fixes-october-18)
now record deadline and exception stops, keep a completion observed before the
deadline, report supplied-geometry click rates and pin the game receipt. 41
regressions pass, and the real-engine rehearsal reproduces all 12 r2 traces with
the fixed code. Both branches are now integrated: 54 combined CPU regressions
pass, and a fresh 12-episode rehearsal with provenance-checked r2 inputs replays
exactly. The [live-runtime checks](reports/initial_geometry_live_runtime_2026-10-18.md)
also connect actual HTTP, native token accounting and the isolated game
interpreter: 12 episodes and independent engine replays pass with scripted
replies. The pinned Transformers 4.57.6 audit passes 24 prompts with at most
six images and 4,609 input tokens. SDK dry checks and read-only account,
quota, dataset-version, inventory and privacy checks pass. No GPU submission,
reservation or claim has been made for this experiment.

## Source snapshot

| Collection | Revision used |
|---|---|
| Historical studies, comprehension, runtime and observation probes | `wheelhouse-replacement-audit` — `5a21dd3` |
| Track 1 results, post-fix audit and qualifications | `track1-successor-runtime-v1` — `abb97ed` |
| Track 2 completed Stage 1 analysis and corrected interpretation | `track2-successor-runtime-v1` — `e5b0830` |
| Track 3 completed analysis and post-review verification | `track3-successor-runtime-v1` — `f5c7bae` |
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
[trackstatus]: https://github.com/dcw06/ARC-AGI-3/blob/a7ef60b3dda93f6daf0eab408bf8476138f87fe2/reports/four_track_resumption/status_2026-10-09.md
[track2]: https://github.com/dcw06/ARC-AGI-3/blob/e5b0830e7c7dddfad366fc52aabed35079a9f1a6/reports/evidence_memory_v1_stage1_results.md
[track3]: https://github.com/dcw06/ARC-AGI-3/blob/12adf90c9047f40bfab183304034a79ff457b756/reports/stagnation_supervision_v1_protocol_v2.md
[track3limits]: https://github.com/dcw06/ARC-AGI-3/blob/12adf90c9047f40bfab183304034a79ff457b756/reports/stagnation_supervision_runtime_v2_owner_questions.md
[track3results]: https://github.com/dcw06/ARC-AGI-3/blob/f5c7bae/reports/stagnation_supervision_v1_results.md
[track4]: https://github.com/dcw06/ARC-AGI-3/blob/37748fec1551eda1b7706a8814e46b5d75a3ae13/reports/progress_subgoal_v1_runtime2_attempt1_results.md
[worksheet]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/wheelhouse_redistribution_decision_worksheet_r4.md
[decisions]: https://github.com/dcw06/ARC-AGI-3/blob/5a21dd339d22ec6e13307722b42dcef0882f6829/reports/wheelhouse_redistribution_decisions.csv
