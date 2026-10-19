# Next diagnostic: feedback to an alternative experiment

**Preparation, October 19, 2026.** The live worker, package builder and independent
evaluator are implemented; see the [repair and validation report](reports/feedback_probe_v1_live_preparation_2026-10-19.md).
No real model responses, uploads, approval, reservation or GPU launch are established by this document.
All earlier attempts remain consumed and preserved.

**CPU checks completed:** [preparation results](reports/feedback_probe_v1_preparation_2026-10-19.md):
53 distinct tests passed with no skips; 16 scripted continuations and 16 real-engine
replays passed; all 73 prompt counts matched the pinned CPU processor. These
are integration checks, not real model answers.

**Research question:** After seeing an action and its visible outcome, can the
policy recognize the evidence, select and faithfully execute an alternative
experiment, and use subsequent feedback in its next decisions?

The owner's one-month guide motivates this diagnostic through Days 11–14
(predicted outcomes, informative experiments and matched comparisons), page 6
(replay, new prediction and decision benefit require distinct evidence), and
page 9 (execution feedback and revision). This is our operational application
of those ideas, not a claim that the guide specifies this exact experiment.
The supplied PDF's SHA256 remains
`b8c66993f67c878126166b526bc6efa5125e37e4f2cc324c14706b839da3ecec`.

## Evidence motivating the change

The [completed recent-feedback pilot](reports/recent_feedback_v1_results_2026-10-18.md)
completed 0/6 first levels in each arm. The explicit summary arm repeated one
full action throughout every 24-action episode. On sc25 it predicted no visible
change on twelve decisions (all at step 2 or later), yet selected that click
again. This is some prospective awareness of visible non-change; it does not
prove correct reference to earlier evidence or explain the internal reason for
repetition.

The next diagnostic therefore separates factual reading, action selection,
execution and resulting gameplay. Another unconstrained reflection paragraph
would not identify which connection is failing.

## Frozen checkpoints

Use only the certified run's `recent_raw` trajectories. For each game, select
at most the earliest unchanged checkpoint and the earliest changed checkpoint,
scanning absolute decision steps 2–20. Selection reads only observations and
actions preceding the decision, never the chosen next action, its outcome,
later completion or human solutions.

Unchanged means the latest transition's before, after and current **full
recorded observations** match. Changed means at least one grid cell changed;
interface changes count. States must still be nonterminal with zero completed
levels and at least one available action. Missing strata are reported explicitly.

| Game | Unchanged checkpoint | Changed control |
| --- | --- | --- |
| ls20 | None eligible | Step 2 |
| s5i5 | None eligible | Step 2 |
| cd82 | Step 2 | Step 3 |
| ft09 | Step 2 | None eligible |
| ka59 | Step 2 | Step 3 |
| sc25 | Step 2 | None eligible |

There are **8 checkpoints: 4 unchanged and 4 changed**, across six exposed
development games. Adjacent checkpoints in cd82/ka59 overlap and are correlated;
neither checkpoints nor individual calls are independent game replications.

In the existing cd82/ka59 trajectories, repeating an action after an unchanged
outcome subsequently changes the grid. Those later observations are not used
for selection or supplied as hints. They provide a retained warning against
turning observed non-change into a universal action ban.

## Three separate questions

| Component | Inputs and intervention | What is scored |
| --- | --- | --- |
| Recognition | One separate stateless question per checkpoint; original displayed evidence and current listed controls | Latest historical action/step, visible change, current-grid match to prior before-grid, and current legal action IDs |
| Baseline policy | Original policy request, recent two-transition history and reviewed initial geometry | One legal full action per call, same original output contract |
| Probe policy | Same baseline request plus one fixed short probe instruction | Up to four decisions under the same budget; legal alternatives and justified repeats both remain allowed |

Recognition answers and scores never enter either policy conversation, memory
or execution input. Reference keys are separate private files and are excluded
from the model-input inventory. Recognition permits unknown judgments and null
unreadable action/control fields. These are uncovered and incorrect on the full
denominator, with coverage reported separately; invalid replies remain counted.
Copying the legal-action list does not establish understanding of control meaning.

Both policy conditions retain the same Qwen model/revision, 448×448 rendering,
temperature/seed, historical starting geometry, two-transition window and
three-field response contract. The probe changes only one constant instruction.
There is no extra reflection call, repair, action override, hard repetition ban,
game-specific rule or human control explanation.

Restore each checkpoint using a fresh seed-0 reset and its exact recorded prefix,
checking every full observation. Equal screenshots cannot substitute for restoring
hidden state. Maintain absolute decision steps and original history; do not reset
the policy's step counter or silently update old geometry. Conditions receive
alternating fixed order across checkpoints. Stop on completion, game over,
invalid output, interruption or four newly dispatched actions.

## Measures and interpretation

| Measure | Supported interpretation |
| --- | --- |
| Recognition correctness and coverage, field by field | Ability to read these displayed facts; no automatic composite promotion threshold |
| Full action differs from previous action | A different control or target was selected; coordinates are part of identity |
| Faithful dispatch and matched restored prefix | Execution matches the recorded choice and checkpoint |
| Repeats after unchanged feedback, with grid-context strata | Descriptive response pattern; repetition is not automatically a failure |
| Predictions made before acting | Coverage and accuracy conditional on asserting; unknown is retained |
| First-level completion within the short continuation | Direct local gameplay outcome; diversity or changed pixels alone does not qualify |
| Requests, input/output tokens, resets and replay actions | Cost of the intervention and of evaluation, reported separately |

Changed controls prevent treating every checkpoint as an unchanged-action case.
They do not make changed and unchanged strata causally comparable across games.
Report the paired conditions by game and stratum. Four-action continuation is a
local diagnostic, not evidence of solving whole games or generalizing to new
mechanics. If alternatives improve outcomes, a later matched diversification
comparator is needed to attribute the benefit specifically to informative probes.

## Preparation and prospective ceilings

The source and private CPU fixtures are bound by
[protocol.json](research/feedback_probe_v1/protocol.json), an externally pinned
certified source evaluation, the whole-run evidence digest, and a CPU draft lock.
The builder verifies those before selection; evaluators independently reconstruct
the full requests, prefix observations, actions, terminal reasons and totals.

| Proposed future experiment maximum | Count |
| --- | ---: |
| Recognition generations | 8 |
| Policy generations | 64 |
| Startup canary | 1 |
| Total generations | 73 |
| Prefix restoration dispatches | 36 |
| New continuation dispatches | 64 |
| Bootstrap resets | 16 |
| Total offline actions including restoration | 116 |
| Local scorecards | 16 |

Independent engine replay adds its own CPU-only actions and scorecards; those
are not hidden in the study totals. The prospective 16 scorecards exceed the old
attempt's 12-card scope. No previous authorization or consumed reservation covers
this experiment. The live package seals the immutable image and versioned input
bindings. Actual provider attachment/access checks, final package approval and
new compute authorization are required before launch.

Current source includes strict recognition scoring, injectable continuations,
an independent content auditor, source/input sealing, a scripted loopback HTTP
rehearsal and a pinned native-processor audit. CPU guards cover hidden/delayed
effects where repetition succeeds, restoration drift, invalid answers, deadline
closure and interrupted evidence. A CPU rehearsal demonstrates integration only;
its scripted responses cannot establish model accuracy or decision improvement.
