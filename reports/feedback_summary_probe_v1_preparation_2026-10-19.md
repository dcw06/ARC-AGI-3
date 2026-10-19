# Feedback recognition and transfer: CPU preparation

**CPU preparation is complete. No new model inference, Kaggle upload, reservation or GPU launch occurred.** The next question is whether the model can read the previously tested factual feedback summary at the same checkpoints, and whether its availability changes the next full action.

## Why this diagnostic

| Retained study | What it established | Remaining question |
| --- | --- | --- |
| [24-action recent feedback](recent_feedback_v1_results_2026-10-18.md) | The summary did not improve first-level completion or repetition; both arms solved 0/6 | Did the model correctly read the summary? |
| [Checkpoint probe](feedback_probe_v1_attempt2_results_2026-10-19.md) | All recorded actions/controls read correctly; all four changed checkpoints missed; seven of eight paired sequences identical | Would explicit observable facts improve recognition, and would action selection respond? |

This reuses the original two-transition summary exactly. It is a narrower recognition/transfer diagnostic, rather than another full-game test of whether a factual summary alone solves the games.

## Frozen comparison

| Setting | Both conditions | Summary condition only |
| --- | --- | --- |
| Starting states | Same eight exposed checkpoints across six games, no new selection | None |
| Visual input | Original 64x64 arrays rendered at 448x448, no overlays | None |
| Geometry | Same historical owner-reviewed initial inventory | None |
| Policy | Same original policy and output contract, temperature 0, seed 0 | No extra probe instruction |
| Feedback | Same two displayed transitions | Existing deterministic counts, inclusive change bounding boxes, displayed metadata and current-grid comparisons |
| Recognition | Separate stateless question per condition/checkpoint; original five fields and scorer | Same summary appended before the unchanged factual question |
| Continuation | Fresh seed-0 reset and exact prefix; at most four new actions | Summary recomputed from displayed images at every decision |
| Condition order | Alternates by original checkpoint ordinal | Same paired order for recognition and policy |

Recognition replies never enter policy requests or engine inputs. All conditions run regardless of whether a recognition answer is correct. Incorrect, unknown and invalid answers stay in their full denominators. The summary is computed from visible evidence; it supplies no hidden rules, object functions, preferred actions or future outcomes.

## Measurements and reading

| Measure | Interpretation |
| --- | --- |
| Paired recognition by field and changed/unchanged stratum | Summary-assisted correctness means reading supplied computed facts; it does not establish unassisted visual perception |
| First full action, including click coordinates | Compare from an exactly matched restored checkpoint |
| Four-action sequences and feedback-response counters | Descriptive continuation behavior; denominators can diverge after the first action |
| First-level completion | Report separately from diversity, changed pixels and prediction accuracy |
| Correct recognition with unchanged/unsuccessful policy | Supports a descriptive separation between factual reporting and observed action use; no causal mediation claim |
| Incorrect summary-assisted recognition | Leaves a reading/interface problem unresolved; cannot diagnose intelligent probing from gameplay alone |

There is no composite pass threshold or promotion criterion. Eight correlated exposed checkpoints, overlapping cd82/ka59 prefixes and one deterministic run cannot establish generalization. The intervention adds text and tokens; it does not isolate arithmetic from redundancy or wording.

## Prospective model-run ceilings

| Item | Maximum |
| --- | ---: |
| Recognition generations | 16 |
| Policy generations | 64 |
| Startup canary | 1 |
| Counted model HTTP requests / generations | 81 |
| Prompt / new tokens per study request | 8,192 / 256 |
| Reset / retained-prefix / new-action dispatches | 16 / 36 / 64 |
| Offline actions including resets | 116 |
| Local scorecards | 16 |
| Online game calls / competition submissions / automatic retries | 0 / 0 / 0 |

These are proposed counts, not compute authorization. Any future live package still needs an independent lifecycle/transport evaluator, exact private bindings and scoped-use review, a fresh package-bound authorization, and a single-use reservation/claim. Earlier 73-request approval does not cover this 81-request diagnostic.

## CPU validation

| Check | Result |
| --- | --- |
| Linux unit/fault checks | 71 distinct tests passed, no failures or skips; includes 18 new diagnostic tests |
| Preparation mutations | Seven faults rejected, including re-sealed forged summaries/requests, substituted checkpoint/order and reference-key allowlist leakage |
| Rebuild | All 44 prepared artifact files reproduce byte for byte |
| Inherited evidence | Completed attempt source lock, input manifest, exact checkpoint bytes, evaluator output and whole-run digest verified before preparation |
| Scripted HTTP integration | 81 completions: one canary, 16 recognition replies and 64 policy replies |
| Actual offline games | 16 restored continuations plus 16 independent engine replays, all matched |
| Accounting per play/replay phase | 16 resets, 36 prefix and 64 continuation dispatches; 16 local scorecards |
| Combined CPU playback/replay cost | 232 offline actions including resets; 32 local scorecards |
| Pinned native audit | Transformers 4.57.6: all 32 prepared and 81 scripted request counts checked; maximum 4,886 / 8,192 |
| Final CPU owner lifecycle | 166.20 s including fresh offline installation, tests, rehearsal and cleanup |
| Cleanup and network | Owned groups absent, temporary interpreter/source removed; GPU disabled, loopback-only namespace |
| Previous source | All 64 completed-attempt review sources unchanged |

The CPU answer server intentionally returns reference recognition answers and scripted legal actions. Its perfect recognition and continuation results test integration only and are not new model-performance evidence. It and the private keys must be excluded from any live execution payload. An initial local test-wrapper failure and earlier draft snapshots remain retained; only final r3 receipts support this validation claim.

## Artifacts and reproduction

| Artifact | SHA256 |
| --- | --- |
| Private CPU draft lock r3 | `eb08c99a4bbb910dc3b6c51776fae7cb3bea64efa1528fad8a91bc107efff380` |
| Prepared manifest | `2b76f14635a0a69655d9f6784700f2ff4a432e81d66bead5b802a1f6718e32ed` |
| Frozen diagnostic protocol | `a5897001cbc6d97ffbe8f7f086d7a73b240d5b3dfdd5a5ac13b62926ed1db312` |
| Connected CPU rehearsal receipt | `e2588c7b171cc6b8a05be8850193bd157085b0a0e310ebbfaa079c75f92564fb` |
| Pinned scripted token receipt | `06692d1e8fcdb7d6c30e81138ae932831f04eafb9b7cdc4c6db080e79e31a347` |

Use [prepare_feedback_summary_probe_v1.py](../scripts/prepare_feedback_summary_probe_v1.py) with the retained source run, source inputs, private review and independent evaluation. It verifies externally frozen provenance before deriving inputs. The prepared model requests and source inventory are checked against the external draft-lock pin by [preparation.py](../research/feedback_summary_probe_v1/preparation.py). Use [rehearse_feedback_summary_probe_v1.py](../scripts/rehearse_feedback_summary_probe_v1.py) inside an externally supervised GPU-disabled Linux process group with loopback-only networking, then audit every request using [audit_feedback_summary_probe_tokens_v1.py](../scripts/audit_feedback_summary_probe_tokens_v1.py) with the pinned CPU processor. The future inference allowlist has only the derived checkpoints and 32 prepared requests; reference keys remain separate.

This is a non-launchable CPU snapshot. No private live notebook, current scope approval, compute authorization, reservation or launch claim exists for this diagnostic. All prior GPU attempts remain preserved.
