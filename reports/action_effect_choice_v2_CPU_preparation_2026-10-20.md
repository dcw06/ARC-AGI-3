# Phase-explicit action-effect choice: prospective CPU preparation

The completed v1 attempt is preserved. This successor addresses its procedural
output failures before another scientific comparison. CPU checks establish
software compatibility, not improved forecasts or gameplay. No new GPU job,
Kaggle upload, reservation or launch has been made for this successor.

## Change and interpretation

| Item | Prospective change |
| --- | --- |
| Study phase | Explicit integer `study_decision_index`: 0 for the first study decision, 1 for the second. Restored game actions have a separate count. The builder verifies their relationship. |
| First decision | Both retrospective fields are constrained to `not_applicable`, even when the restored game history shows changes. |
| Second decision | Carries the unchanged first-study answer and selected action/forecast; retrospective fields have their own permitted string enums. |
| Decoder | Replaces JSON-syntax-only mode with phase-specific closed-object JSON schemas. Forecasts remain strings: `none`, `1_to_4`, `5_to_64`, `65_plus`, `unknown`. |
| Scientific contract | Same images, factual summaries, eight checkpoints, candidate selection, arm order, generation settings, strict parser, scoring and stop rules. Only the fixed arm instruction differs between arms. |
| Old results | No repair or reclassification. Rechecking the 17 retained study replies still gives 2 valid and 15 invalid. All 434 files in the preservation inventory match their earlier hashes. |

Constraining first-decision retrospective fields is a **host-enforced procedural
rule**, not evidence of model understanding. Second-decision schemas restrict
syntax and enums; they do not encode the correct observed outcome or whether a
forecast matched. The decoder still permits incorrect substantive answers, which
the unchanged evaluator must score normally. An unknown forecast is never
promoted to a correct forecast.

The native `response_format` construction follows the
[vLLM 0.19 structured-output interface](https://docs.vllm.ai/en/v0.19.0/examples/online_serving/structured_outputs/).
The retained CPU check also tests the installed 0.19.0 implementation rather than
assuming documentation establishes compatibility.

## CPU verification

| Check | Result |
| --- | --- |
| Original and successor tests | **35 passed**, 0 failures, errors or skips; 14 successor tests |
| Closed-schema semantic coverage | All 500 permitted answer combinations also pass the unchanged strict parser |
| Native vLLM 0.19.0 / xgrammar 0.1.34 | Both phase schemas accepted; 50 first-phase and 450 second-phase canonical answers admitted; 68 adversarial answers rejected, including wrong phase, numeric/string zero, missing/extra fields, duplicates and truncation |
| Full request conversion | 208 wrapper-to-sampling checks: 16 sealed initial requests plus 192 rehearsal/audit requests, covering both phases |
| Real offline engines | 16 conditions, 32 scripted completions, 16 deterministic trajectory replays and 48 fresh candidate-reference branches; all 80 engines closed |
| Native Qwen token accounting | 192 audited requests; maximum **5,224 / 8,192** prompt tokens, with the unchanged 256-token completion cap |
| CPU lifecycle | Completed in 354 seconds under the 1,500-second external watchdog; all owned groups absent and temporary environments removed |
| Inference staging | 18 sealed files; inputs rebuild exactly; rehashed wrong-phase requests and extra reference files are refused |
| Original attempt | 434 files unchanged; 17 old study replies retain their original 2-valid / 15-invalid classification |

The native check uses the pinned installed vLLM/Transformers interpreter,
local tokenizer/processor files, and default `auto` structured-output selection,
which selected xgrammar. It checks canonical serializations covering every
semantic answer, not every equivalent JSON spelling. No model weights were
loaded and CUDA was not initialized. The real-engine replies were scripted;
their successful forecasts or scores cannot be called neural performance.

The first local Linux setup check passed the tests, then stopped because the
model interpreter has no pip module. Its failure and successful cleanup receipt
are retained. The subsequent check uses the already installed pip driver for an
offline, hash-pinned installation; no model or GPU attempt was consumed.

## Small format-only pilot proposed next

| Limit | Proposal, not compute authorization |
| --- | --- |
| Cases | Original checkpoint ordinals 0 and 1, both instruction arms: 4 conditions |
| Decisions | At most 2 per condition; 8 study generations plus 1 startup canary |
| Output and input | At most 256 new tokens per reply; prompt cap 8,192 |
| Offline game effects | At most 4 resets, 8 restored-prefix actions and 8 new actions: 20 including resets; 4 local scorecards |
| Online effects | Zero online game calls, leaderboard submissions or automatic retries |
| Assessment | End-to-end request acceptance and format validity, retaining every scheduled, reached and unreached phase |

These are the first two inventory entries, not cases selected for favorable model
or branch outcomes. Both phases must actually be reached in all four conditions
to claim complete format coverage. A terminal or illegal-candidate stop remains
missing coverage; do not force continuation or replace the case. Format success
alone would establish neither an arm advantage nor gameplay improvement.

A future live pilot still requires a bounded runner with independent evaluation,
an exact private package, current source/attachment/use checks, and fresh
lock-bound authority and reservation. Earlier approvals and consumed attempts
do not transfer. A full eight-checkpoint comparison would be a separate later
decision.

## Reproduction and bindings

`python scripts/derive_action_effect_choice_v2.py --check` verifies the three
derived files against hash-pinned v1 parents. Prepare with
`scripts/prepare_action_effect_choice_v2.py`; its input checkpoint file must match
the protocol's external pin. `scripts/rehearse_action_effect_choice_v2.py`
requires an owned, watchdog-protected, loopback-only Linux CPU environment and
the pinned game interpreter. It retains scripted requests, deterministic game
replays and independent reference branches separately from inference inputs.

Run `scripts/check_action_effect_choice_v2_structured_outputs.py --help` for the
native check, using the pinned vLLM interpreter, local tokenizer, sealed inputs
and rehearsal request audit. No model weights are loaded. The 35 interface,
flow, scoring and preparation tests use the pinned CPU environment with
`jsonschema` available.

| Binding | SHA256 |
| --- | --- |
| Prepared inference manifest | `97d689d691d120c15d632563eb94b7dd8b3a194e02339083ffb9f10a6fcba103` |
| CPU-only complete source archive (121 source files) | `48028ac74581782258470bd5f32f54e901e05a67b09685f1f7a91d906e2568d9` |
| Native grammar/request receipt | `31077efbe052b0a9c1fa1f566bc5b478544b6edef84b95c173dc40c32713a034` |
| Native token receipt | `84826014f0f29d4df0941fb9bfbd350ccd5be95e395ab930489eb11a798a4ab1` |
| Real-engine rehearsal receipt | `004da10404d3b5ad0ce942762ff2000c3dc67d9de8253ef6e877c59db03bacce` |
| CPU lifecycle receipt | `601463b4c2c9022b9a46c28995c0ca85ee54237cd579515a0d4267f029bbc822` |
| Old-attempt preservation receipt | `f0c9549d8e0661383816b2f4cea93761f7102670175cecf620747206b7cf1268` |
| Prospective v2 protocol | `afd506e0b68ccb930b12edd412955b768dae8cf399d6dff8c6e47d1b47750fda` |

Raw game observations, requests, reference keys, historical model replies and
CPU logs remain in the private, git-ignored workspace. Public records contain
source, aggregates and hashes only.
