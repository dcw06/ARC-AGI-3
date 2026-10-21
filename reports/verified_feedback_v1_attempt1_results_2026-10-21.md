# Verified executed feedback v1: attempt 1 results

**Technically complete and independently validated; forecast interpretation
corrected after review.** Second-decision candidate-effect accuracy was **8/16**
with feedback versus **6/16** with the existing summary. The entire net gain
concerns the action just executed, whose previous effect is supplied in the
feedback block. Its 5/8 accuracy exactly matches a simple persistence rule:
predict that action's next effect will be the same as its last effect. The
selected second action was unchanged in all eight matched pairs. These results
do not establish improved prediction beyond that rule or improved action choice.

## Research question and comparison

Does an explicit verified receipt of the preceding executed action and its
immutable forecast help the policy forecast and choose its next action?
Both conditions receive the same images, recent transitions, computed summary,
historical geometry and fixed candidate actions. Only the verified-feedback
condition receives the additional receipt at the second decision. The receipt
contains the preceding action, original forecast, observed changed-cell count
and category, visible-change status and matched/mismatched/unknown comparison.
It contains no unexecuted candidate outcome, future frame or recommended action.

Each of the eight checkpoints was restored separately for both conditions, with
two new policy decisions per condition. All eight first parsed answers matched,
and all eight second-decision before-states matched. No divergent-state pairs
were discarded. The frozen model, dataset copy and immutable runtime were the
same as in the preceding format pilot.

## Main descriptive results

Each phase has eight answers and two candidate-effect forecasts per answer.
All scheduled slots are retained in the denominator.

| Measure | Summary only | Verified feedback |
| --- | --- | --- |
| Valid first answers | 8/8 | 8/8 |
| Correct first-decision candidate forecasts | 9/16 | 9/16 |
| Valid second answers | 8/8 | 8/8 |
| Correct second-decision candidate forecasts | 6/16 (37.5%) | 8/16 (50.0%) |
| Incorrect second-decision candidate forecasts | 10/16 | 8/16 |
| Unknown / invalid / unreached second forecasts | 0 / 0 / 0 | 0 / 0 / 0 |
| Repeated the first selected action at the second decision | 8/8 | 8/8 |
| New first-level completions within the two-action condition cap | 0/8 | 0/8 |

The net forecast difference is two of sixteen slots, or 12.5 percentage points.
Forecast vectors differed in three of eight matched second decisions. Selected
full actions differed in zero of eight. Changing a forecast or repeating an
action is not itself evidence of a better choice; reference effects measure
pixel-change extent, not usefulness or progress toward a solution.

### Per-action split and persistence baseline

The two candidates are unchanged across both decisions, and every condition
repeats its first selected full action. Consequently, one of the two scored
second-decision forecasts concerns the same action whose preceding outcome is
explicitly supplied. The backward-looking copying caveat therefore also applies
to this component of the headline forward-looking measure.

| Second-decision forecast measure | Summary only | Verified feedback |
| --- | --- | --- |
| Repeated-action forecast equals its preceding observed effect | 5/8 | 8/8 |
| Repeated-action forecast correct on its next execution | 3/8 | 5/8 |
| Other-action forecast correct | 3/8 | 3/8 |
| Persistence baseline correct for the repeated action | 5/8 | 5/8 |

In all three cases whose forecasts change, the repeated-action forecast moves
to the supplied label. Two become correct; one remains wrong because that
action's effect changed at the next state. Forecasts for the other action have
one gain and one loss. Thus the whole net increase is accounted for by the
repeated-action component, with no accuracy advantage over persistence on that
component and no net gain on the other action. The evidence is consistent with
copying the observed-effect label; it does not identify an internal mechanism.

This split is a post-run interpretive audit, not a newly preregistered endpoint
or a change to the original forecasts, scoring or attempt status. A future
design should report the other-action forecasts separately and use new second-
decision candidates when testing transfer beyond repeating an observed effect.
It would need its own review and authorization.

| Game | Checkpoint | Correct second forecasts: summary | Correct second forecasts: verified | Second action differs between conditions? |
| --- | --- | --- | --- | --- |
| ls20 | board-01-step02 | 0/2 | 1/2 | No |
| s5i5 | board-02-step02 | 2/2 | 2/2 | No |
| cd82 | board-03-step02 | 1/2 | 1/2 | No |
| cd82 | board-03-step03 | 0/2 | 0/2 | No |
| ft09 | board-04-step02 | 2/2 | 2/2 | No |
| ka59 | board-05-step02 | 1/2 | 1/2 | No |
| ka59 | board-05-step03 | 0/2 | 0/2 | No |
| sc25 | board-06-step02 | 0/2 | 1/2 | No |

## Supplied-feedback consistency diagnostics

| Second-answer field | Summary only | Verified feedback |
| --- | --- | --- |
| Correct preceding visible-change report | 1/8 | 8/8 |
| Correct check of the original selected forecast | 1/8 | 8/8 |

These fields are supplied in the intervention receipt. Their scores are
copying/consistency diagnostics only and earn **no model-understanding credit**.
The summary-only condition answered unknown on both fields in seven cases;
ft09 was correct in both conditions. The intervention therefore established
that the model can repeat the supplied labels. The forward-looking per-action
audit above shows why the small aggregate change also does not establish
prediction beyond persistence. It did not change the observed action selections.

## Runtime and independent validation

| Check or resource | Observed result |
| --- | --- |
| Provider status and version | COMPLETE, version 1 |
| Allocated GPU | One NVIDIA RTX PRO 6000 Blackwell Server Edition |
| Recorded lifecycle | 1,519.34 s (25 min 19 s), below the 3,300 s worker limit |
| Model generations / counted model HTTP requests | 33/33 ceiling: one canary and 32 study replies |
| Valid study replies | 32/32 |
| Largest completion / finish reasons | 53 tokens; all 33 generations stopped normally |
| Native prompt audit | All 33 counts independently matched; maximum 5,282/8,192 |
| Total prompt / completion tokens | 117,537 / 1,494 |
| Offline actions | 84/84 ceiling: 16 resets, 36 prefix actions, 32 continuation actions |
| Local scorecards | 16/16, all closed |
| Online game calls / online scorecards / leaderboard submissions | Zero |
| Condition stops | All 16 at the two-action cap |
| GPU cleanup | Verified; zero GPU processes remaining |
| Sources and temporary environment | Removed within the bounded lifecycle |
| Evidence collection | 43 original files, 3,027,018 bytes, all download hashes checked |
| Runtime evidence manifest | 41 files checked, exact final return witness and provider log marker |
| Independent replay | Every request and retained transition rebuilt; 80 CPU engine boots/closes and 308 dispatches, including reference branches |
| Historical evidence | All 456 inventoried files unchanged |
| Collection/evaluation provider writes or new GPU jobs | Zero |

Independent evaluation used the exact hash-pinned prelaunch source archive,
the pinned native processor and freshly installed hash-verified offline game
dependencies. CPU replay ran in a network-isolated environment with GPU use
disabled. It verified its process cleanup and temporary-environment removal.
Provider completion, saved source/settings, launch authority, lifecycle receipts,
prompt counts, full requests, action coordinates, observations, engine accounting
and reference scores all passed. No reply was salvaged, replaced or regenerated.

## Bindings and retained records

| Record | SHA256 |
| --- | --- |
| Final private review lock | `3a1aa3e4295c79c76dbf8728e0b29e493d0a01bc74fd6d6ad8e10b8605d66e0a` |
| Live inference input manifest | `af141118f37bbc41771d72de430d4bb520d8f4002c3b4910c8febceeb30883ad` |
| Independent evaluation | `440b7078d88e13c2bab1c1dc15623382d61f996b7937ccd692419ad9d7bb6de5` |
| Evaluated run evidence inventory | `41acebe93924ccf1e4e34d3fc1b072bd2505a539fb66d27428741a1e6e2f5634` |
| Retained model transport | `71b279aad40b34d1a052a67ba2d62f2aa3fda5f1f8b7c0e687dbcb2b558f627f` |
| Exact prelaunch CPU source archive | `c321c88ba28cd748a3eb9c9384924a6b3ae0a386a91420e40944008cfe8e0aea` |

The reviewed sources were published at `bf79c9e`; the launch record followed at
`fd84b2e`. Private raw outputs, provider evidence, approvals and CPU replay remain
under the git-ignored `verified-feedback-live-v1-2026-10-20/collection-attempt1-r1/`
workspace and `.cache/vf1result1/`. Only sanitized results are published here.
The one attempt is consumed and preserved; no retry or additional GPU run was
launched or authorized by collecting these results.

Eight checkpoints across six games, including repeated checkpoints within two
games, do not provide eight independent games or held-out evidence. This test
does not establish learning, a reasoning mechanism, generalization, independent
object discovery, improved control use or game-solving ability. A completed
software lifecycle and valid answer format do not establish those capabilities.
