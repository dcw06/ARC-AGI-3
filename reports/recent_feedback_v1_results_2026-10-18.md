# Recent-feedback comparison: completed pilot

The run is independently technically complete. The explicit factual summary
did not improve first-level completion or reduce repetition in this pilot.
Both interfaces completed **0 of 6 first levels** within 24 actions per episode.

Both arms received identical owner-reviewed starting geometry and the same
policy, model, controls and two-transition image history. `recent_summary`
added only deterministic facts computed from that already displayed feedback.
There were six paired exposed development starts, with balanced arm order.

| Measure | Recent images/text (`recent_raw`) | Same evidence plus summary (`recent_summary`) |
| --- | ---: | ---: |
| First-level completions | 0/6 | 0/6 |
| Policy calls / dispatched actions | 144 / 144 | 144 / 144 |
| Invalid outputs | 0 | 0 |
| Same full action as immediately previous action | 115/138 (83.3%) | 138/138 (100%) |
| Repeat of an action with unchanged feedback in the last two displayed transitions | 78/78 | 95/95 |
| Above, prior before-grid equals current grid | 62/62 | 79/79 |
| Above, prior before-grid differs from current grid | 16/16 | 16/16 |
| Distinct full actions, summed across episodes | 8 | 6 |
| Dispatched steps with any visible grid change | 78/144 | 60/144 |
| Asserted visible-change predictions | 0/144 | 33/144 (22.9%) |
| Correct assertions, conditional on asserting | Not estimable (0 assertions) | 23/33 (69.7%) |
| Unknown predictions | 144/144 | 111/144 |
| Realized prompt tokens | 433,053 | 462,403 |
| Realized completion tokens | 3,705 | 3,552 |

An eligible decision is counted once, even when two displayed transitions
qualify. Full-action equality includes click coordinates. No decision was
unexecuted. Grid equality is only a visible-context comparison; it does not
establish identical hidden state. Realized token totals include different
trajectories and are not an isolated estimate of summary-text overhead.

## Per-game breakdown

Every episode reached its 24-action cap without completing level 1.

| Game | Distinct full actions: raw / summary | Consecutive repeats: raw / summary (out of 23) | Visible changes: raw / summary (out of 24) |
| --- | ---: | ---: | ---: |
| ls20 | 3 / 1 | 0 / 23 | 24 / 6 |
| s5i5 | 1 / 1 | 23 / 23 | 24 / 24 |
| cd82 | 1 / 1 | 23 / 23 | 15 / 15 |
| ft09 | 1 / 1 | 23 / 23 | 0 / 0 |
| ka59 | 1 / 1 | 23 / 23 | 15 / 15 |
| sc25 | 1 / 1 | 23 / 23 | 0 / 0 |

The summary arm dispatched one identical full action throughout each episode.
On ft09 and sc25, both arms repeated a single click despite all 24 actions
producing no final-grid change. Visible change elsewhere can include interface
changes and is not evidence of useful movement or progress. Repetition alone
is not universally wrong, but neither interface converted these trajectories
into a first-level completion within the tested budget.

The summary elicited more predictions, including ten incorrect assertions.
That is not evidence of better calibration or effective action adaptation.
The clearest retained failure is continued use of unchanged actions even when
the available feedback, including explicit summary facts, supports recognizing
the lack of visible effect.

## Technical validation

| Check | Result |
| --- | --- |
| Provider | Version 1 COMPLETE; saved source, authority, private settings, immutable image and attachments verified |
| Actual GPU | One NVIDIA RTX PRO 6000 Blackwell Server Edition |
| Bounded notebook lifecycle | 561.32 s from bootstrap; below 3,300 s worker limit; provider allocation/mounting/release overhead is separate |
| Counted effects | 289 HTTP generations: 288 policy calls plus one canary; 288 play actions plus 12 resets; 12 local scorecards |
| Installation | All 174 publisher wheels and 31 competition game wheels verified before the corresponding offline installations |
| Evidence | 35 downloaded files hash-verified; 33 runtime-manifest members verified; exact final return marker present once |
| Independent request audit | Full frozen requests, observations and added summary arithmetic reconstructed for all episodes |
| Independent native tokens | All 289 prompt counts independently match Transformers 4.57.6 |
| Independent games | All 12 action sequences replayed in a fresh isolated offline interpreter with matching observations |
| Terminal/accounting checks | All action caps, final states, request/dispatch totals and worker summaries re-derived |
| Cleanup | Owned groups absent, zero GPU processes, temporary interpreters and extracted source removed |
| Local validation cost | GPU-disabled independent replay and installation took 136.70 s; no neural requests, GPU launch or provider writes |
| Analysis checks | Six targeted tests cover full-action identity, duplicate candidates, context strata, two-transition window, missing actions and unknown predictions |

The descriptive analysis producer was added after collection to implement the
already frozen metrics. It did not alter the protocol, live package, observations
or independent technical evaluator. It refuses an evaluation bound to different
run evidence, inputs or review lock. Its source and output hashes are retained.

## Limits and next research implication

This is one pair per exposed development game, with assistance from reviewed
initial geometry, at one 24-action budget. It does not establish independent
object discovery, general inability to learn controls, or a general negative
effect of summaries. Different trajectories also limit interpretation of token
and visible-change totals.

The supported next question is whether a policy can turn a recorded action and
its observed effect into a different, valid next experiment. A controlled test
should distinguish recognizing unchanged feedback from choosing and executing
an alternative legal control or target. This run supplies no evidence that a
longer factual summary alone solves that decision problem.

The attempt is consumed and preserved. No rerun or new GPU job was launched
during collection or analysis. Raw outputs, approvals, source snapshots and
provider receipts remain private; this report contains sanitized aggregates.

## Reproduction anchors

| Artifact | SHA256 |
| --- | --- |
| Exact private r2 review lock | `fd778424ce3ab9994a4608e020a9f9b0a5b7aaa8721e695e83f8c75ceedd9bc9` |
| Frozen live protocol | `6815c085e9a362a097894f7f3cd5fae02ad70e420cf3b29b6522f2c449a3b04e` |
| Retained run evidence digest | `8f4a01b0f5b206f861ad169f2dd94c5ef2dc115c83c0785cfef5c5f3ea4403c7` |
| Independent technical evaluation | `87ea70eef1454d2a7ede72d79b0c1190a9b11d5c96706b133c3bbc06c53e7391` |

Use [analyze_recent_feedback_v1.py](../scripts/analyze_recent_feedback_v1.py)
with the private run, inputs, review lock, independent evaluation and evaluator
lifecycle receipt. [analysis.py](../research/recent_feedback_v1/analysis.py)
implements the frozen descriptive counters. The exact live source was published
in `0a0a6d7`; the prelaunch review is retained separately from these outcomes.
