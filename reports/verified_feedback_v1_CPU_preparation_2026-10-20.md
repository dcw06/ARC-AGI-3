# Verified executed feedback v1: CPU preparation

The CPU-only successor is implemented and checked. It computes verified
feedback about the preceding executed action and compares two request layouts.
**No new model inference, Kaggle call or GPU launch occurred.** Live execution
is disabled; there is no new private live package or compute authority.

The [completed pilot's diagnosis](action_effect_choice_v2_feedback_diagnosis_2026-10-20.md)
found that the model abstained despite receiving both observed cell counts and
its original forecast. This successor tests whether an explicit verified
feedback block helps subsequent forecasting and action selection. It does not
award understanding credit for copying labels supplied by the host.

## Prospective comparison

| Setting | Summary only | Verified feedback |
| --- | --- | --- |
| Original checkpoints | Eight original exposed checkpoints | Same checkpoints, including overlapping prefixes |
| Candidate actions, images, initial geometry and recent summary | Existing construction | Identical construction |
| System/decision instruction | Existing v2 neutral-choice instruction | Identical instruction |
| First-decision request | No previous study feedback | Identical request |
| Second-decision request | Existing summary and original selected forecast | Same request plus one verified executed-feedback block |
| Output schema and settings | V2 phase-specific schema; temperature 0, seed 0, 256 new tokens, 8,192 prompt tokens | Identical schema/settings |
| Model | Pinned Qwen3-VL-30B-A3B-Instruct-FP8 | Same model/revision |

Only inclusion of the second-decision block varies. It adds explicit derived
labels and tokens, so this is a presentation-package comparison, not an isolated
reasoning mechanism. Candidate A/B assignment and condition order are balanced
over the original inventory using the existing deterministic rules. Future first
answers are collected separately; identical first prompts do not guarantee
identical answers or resulting states. Divergent states must be reported, not
filtered away or described as an identical-state comparison.

The prospective protocol is [protocol.json](../research/verified_feedback_v1/protocol.json).
Its planning ceiling is 32 study generations plus one startup canary, 16 resets,
36 prefix actions, at most 32 new actions and 16 local scorecards. These are
planning values, **not authorization**. No automatic retry, online game call or
leaderboard submission is provided.

## Implemented behavior

| Component | Behavior |
| --- | --- |
| Pre-action forecast envelope | Records the original parsed answer, full selected action, event index and before-state hash; the flow journals its hash before dispatch admission |
| Executed feedback | Checks the retained forecast/transition pins, exact event identity, click coordinates, original answer, and before/after/current observations |
| Pixel arithmetic | Counts all changed native cells, including interface changes, then derives the frozen extent category and original-forecast comparison |
| Unknown forecasts | Preserve an original unknown comparison while still reporting an observed change when frames establish it |
| Missing or inconsistent evidence | Refuse rather than fabricate a receipt or silently substitute another action's result |
| Display binding | Verify the actual last before/after PNGs and current image against the event before constructing either second-decision request |
| Request contrast | Append only observed facts in the treatment condition; preserve all other request fields |
| Future information | No unexecuted outcomes, future images, reference keys, progress labels or recommended actions enter the block |
| Scoring | Old scores/parsers remain unchanged; supplied retrospective labels are copying/consistency diagnostics, not a new model-understanding endpoint |

Hashes bind records; they do not by themselves establish truthful execution or
pre-dispatch acquisition. A future independent live evaluator must rebuild the
envelopes from retained raw replies and event journals, verify ordering, and
independently replay the game transitions. This preparation does not claim that
the old runtime emitted the new envelope.

## Verification

| Check | Result |
| --- | --- |
| New Windows contract tests | 24 passed |
| Linux successor and predecessor contract suite | **66 passed, 0 failures/errors/skips** |
| Boundary cases | 0, 1, 4, 5, 64, 65 and 4,096 changed cells; strict types and out-of-range rejection |
| Provenance faults | Changed forecast pins, transition pins, event indices, before/current states and click coordinates refused |
| Failure/admission faults | Forecast-journal failure prevents dispatch; late response or journal completion cannot admit an action; invalid replies are not repaired or retried |
| Early terminal state | Missing second phase preserved, no replacement or forced continuation |
| Prepared inference inventory | 18 files: original checkpoints, fixed candidate/order data and 16 first requests; no later prompts or reference keys |
| Actual offline game rehearsal | All 16 conditions reached both phases; 32 scripted play completions |
| Independent scripted trajectory replay | 16 additional replays; rebuilt requests and full event sequences matched |
| CPU engine effects including replay | 32 boots, 136 dispatches and 32 closes; separate from any proposed GPU budget |
| Native token audit | 32 actual scripted request bodies; maximum **5,282/8,192**, pinned Transformers 4.57.6 |
| Historical feedback reconstruction | All four retained traces reproduce the ls20 mismatches and s5i5 matches; two distinct historical cases, not four independent replications |
| Completed attempts | All 456 inventoried files unchanged: earlier 434 plus the completed pilot's 22 evaluated files |
| CPU lifecycle | 176.36 seconds within a 1,500-second outer bound; owned groups absent and temporary environment removed |
| Existing derivations | All 3 CPU v2 and 18 live v2 derived files still match their pinned parents |

The first Linux harness invocation encountered a checkout import-path mistake,
failed before game/model work, and removed its owned processes and temporary
source tree. That evidence is retained. The corrected harness uses a separate
output directory and explicitly selects the extracted source tree. The source
archive is unchanged between these harness checks.

Historical reconstruction is explicitly post-hoc CPU arithmetic and presentation
checking. It neither changes any old reply/score nor certifies historical
pre-dispatch journaling. The actual new CPU flow separately exercised the
journal-before-dispatch ordering. Scripted replies, game replay and token checks
demonstrate software behavior; they are not model performance results.

## Exact preparation and remaining work

| Artifact | SHA256 |
| --- | --- |
| CPU source archive | `7b17d94473290f0e5b0fdb6923a7a45e2376aff63ad807f6f16a5305794c72ce` |
| Prepared input manifest | `8688192a13707ab5efcce1d3af669b080ca7ca109cbf7b51f00e2a2b3559d575` |
| CPU lifecycle | `478fb687352b88b834e4c43066697d776992d36baa7f947b5f9a7fd3b2e5c6fa` |
| Actual-game/token rehearsal | `d3df1ec80455b74eaec30ac1a7010d9f62ce4c4f27b17d86f10d71dc2ff4188f` |
| Historical reconstruction | `269024074b12ce211f62f8ee21527982d5aadaca7f65b3f01372f3143cbdef1b` |

Private artifacts remain under
`.cache/github-review/verified-feedback-v1-2026-10-20/`, with successful checks
and inputs under `CPU-check-r2/`. They were not uploaded. The first-request
manifest is a CPU preparation lock, not a live-package review lock.

Before inference, still implement and review the bounded live runner and
independent evaluator, including raw-reply/forecast/transition ordering,
reference-branch scoring, missing-phase denominators and exact run binding.
Then verify the production request/backend path, build and review the exact
private package and scope, and obtain fresh lock-bound compute authorization
and a single-use reservation. Earlier authorizations remain consumed.

Subsequent update: the bounded runner, independent evaluator and exact local
private package are now [implemented and checked](verified_feedback_v1_live_preparation_2026-10-20.md).
Fresh authorization, reservation and launch remain unperformed. This CPU
preparation record and its source/input pins are preserved unchanged.
