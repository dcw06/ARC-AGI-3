# Initial geometry assistance — completed r5 attempt 3

**Technically complete; no first-level completion in either arm.** The
independent evaluator passed lifecycle certification, all retained requests
and responses, native token accounting and all 12 real-engine episode replays.
The study found no completion advantage from reviewed starting geometry within
the 24-action budget. This is one pair per exposed development game, not a
general finding that geometry assistance cannot help.

| Research question | Test |
|---|---|
| Does reviewed starting geometry improve short gameplay over retained automatic geometry? | Same Qwen model and policy; six games; one automatic/reviewed pair per game; 24 actions per episode |
| What geometry was supplied? | Starting-frame occupied cells, bounding boxes and occupied anchors; no object roles, control meanings or rules; geometry explicitly marked historical |
| Primary outcome | First-level completion within 24 actions |

## Outcomes

| Measure | Automatic geometry | Reviewed geometry |
|---|---:|---:|
| First-level completions | **0/6** | **0/6** |
| Episodes reaching the action cap | 6/6 | 6/6 |
| Policy calls / dispatched actions | 144 / 144 | 144 / 144 |
| Invalid answers | 0 | 0 |
| First click inside a reviewed object, among first actions that were clicks | 4/5 | 5/5 |
| First click inside a supplied mask | 4/5 | 5/5 |
| First click exactly on a supplied anchor | 4/5 | 4/5 |
| “Unknown” visible-change predictions | 144/144 | 144/144 |
| Accuracy on non-abstaining visible-change predictions | Undefined: no such predictions | Undefined: no such predictions |

The first-click difference is one game, **ft09**. Both ls20 first actions were
not clicks and are excluded from those denominators. In the reviewed arm,
clicking inside a supplied object can be direct use of its cells/anchor; it is
not evidence of independent object discovery. Even a valid object hit need not
select a useful control or induce a change.

| Game | First level, automatic / reviewed | First click on reviewed object, automatic / reviewed | Distinct full actions, automatic / reviewed |
|---|---|---|---|
| ls20 | No / No | Not applicable / Not applicable | 3 / 3 |
| s5i5 | No / No | Hit / Hit | 1 / 1 |
| cd82 | No / No | Hit / Hit | 1 / 1 |
| ft09 | No / No | Miss / Hit | 1 / 1 |
| ka59 | No / No | Hit / Hit | 4 / 1 |
| sc25 | No / No | Hit / Hit | 1 / 1 |

“Distinct full actions” includes click coordinates, not just action IDs. In
each s5i5, cd82, ft09 and sc25 episode, the agent repeated one click coordinate
for all 24 actions. The reviewed ka59 episode did too. In ls20, each arm issued
action IDs 1, 2 and 3 eight times each. These are descriptive diagnostics of
limited exploration, not a separately preregistered success criterion.

All ft09 and sc25 actions left the final grid unchanged, including the reviewed
ft09 clicks that landed on an object. Other visible changes can include UI
updates; they do not by themselves establish useful object manipulation or
progress. All 288 policy predictions were “unknown”, so no predictive accuracy
or rule-understanding success follows from this run.

## Technical completion

| Check | Verified result |
|---|---|
| Package | Private r5, lock `fe5d0ddaa3ffceeeb0e548c0c186eb24ccab5bd2ac649b2f84b0a818ca3299fb` |
| Provider | Version 1; COMPLETE; exact saved source, authority, settings and return marker retained |
| Accelerator | One NVIDIA RTX PRO 6000 Blackwell Server Edition |
| Notebook lifecycle through return witness | 537.543 s, below the 3,300 s worker deadline |
| Model traffic | 289 counted HTTP/generation requests: one canary and 288 policy calls; within 300 HTTP / 289 generation limits |
| Game work in GPU job | 288 dispatches + 12 resets = 300 offline actions; 12 local scorecards; no online game calls or leaderboard submission |
| Dependencies | 174 publisher wheels and 31 competition game wheels verified before installation; isolated pinned interpreters |
| Cleanup | Owned groups absent; zero remaining GPU processes; temporary environments and extracted source removed |
| Collection integrity | All 35 downloaded provider files match the retained download manifest; all 33 runtime-manifest members match |
| Native token replay | All 289 requests match independent CPU replay with Transformers 4.57.6 and the pinned Qwen processor inputs |
| Independent game replay | All 12 initial states and 288 retained transitions reproduce with exact game/wheel pins |
| Local evaluation environment | GPU disabled, network namespace restricted to loopback; owned processes and temporary interpreter cleaned up |

The 537.543 s duration is the notebook lifecycle, not a measurement of the
entire allocation/mounting/release interval. The approved time policy permits
provider overhead beyond the requested session hour. Independent CPU validation
separately replayed the 300 offline actions with 12 local scorecards; it made
no new model requests, GPU job or online game calls.

The earlier two SSL submission attempts and this completed attempt are all
consumed and preserved. No automatic retry occurred, and collection/evaluation
made zero Kaggle writes. The smaller package's successful submission resolves
the observed upload failure for this attempt; it does not supply another
compute authorization.

## Interpretation

Reviewed initial geometry improved this small first-click diagnostic, but did
not improve the primary completion outcome. The repeated actions and universal
prediction abstention motivate studying control discovery, feedback-driven
action changes and loop avoidance before another geometry-only gameplay run.
That is a proposed successor question, not an established cause of failure or
authorization to change the policy and rerun it.

The comparison concerns the complete initial representation: automatic inventory
omissions, including the invalid automatic ls20 inventory, remain part of the
automatic arm. It does not isolate boundary accuracy from discovery coverage.
There are six exposed starting states, no independent replicate per game, and
no hidden-game or competition-score claim. Correct object contact is not a
substitute for learning which controls matter or solving a level.

## Evidence and privacy

Raw logs, images embedded in requests, provider snapshots, approvals and
evaluations remain private and git-ignored. This report publishes aggregates
only. The evaluator binds the exact input evidence digest; its episode-level
content-only flags are deliberately separate from the passing whole-run
lifecycle certification.

| Retained private record | SHA256 |
|---|---|
| Independent evaluation | `a20a50032a357bd6042bcdf4c6bd40b05c4f260eef697f9d2cab867c8327e9a4` |
| Native token replay | `6721e19405f680ad06757980444038de6852e5f37ad90ee5a1fac169a176d352` |
| Download manifest | `1f2dd638616a43dcea33a4a32a6d746e163578577ec82d150bee25cd4a653344` |
| Aggregate results | `e2f637f72455daa9038d3623c3155f2ebe8a287fbc307f9bfd25b074c3d36d05` |
| Exact evaluated evidence-set digest | `c82fa21225031c35a53404186675be682b5b989becb3a64543b5f6b1b4c9e496` |

Records are under the main workspace's
`.cache/github-review/initial-geometry-small-package-2026-10-18/collection-r5-attempt3-r1/`;
downloaded originals and provider support files are under `.cache/igresult5/`.
