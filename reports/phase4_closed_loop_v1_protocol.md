# Closed-loop development comparison v1

Status: protocol proposal frozen for review; no compute authorized or reserved.
This is preparation, not an executable GPU notebook. A separately reviewed runner
and notebook must implement these requirements before source approval and launch.

## Question and matched design

Does removing concrete action examples improve actual early game progress, rather
than merely changing click coordinates? Compare original v13 `arc_action_v12`
system prompt against the exact `no_concrete_examples` text used in diagnostic v4.
Both are E1S-R-derived policies; neither is unchanged historical E1S-R.

Use all 15 development games from the frozen diagnostic proposal, sorted by game
ID, without selecting only the two example-copying cases. One fresh episode per
game per arm: 15 pairs, 30 episodes. Environment seed 0 and request seed 0 in both
arms; temperature 0 and non-thinking decoding. This is one matched seed, not a
seed robustness study. Alternate baseline-first/no-example-first by sorted game
index (8 versus 7 pairs). Run each pair adjacently and sequentially, with a single
shared model service and no concurrent model calls. Do not adapt order to results.

Each episode has an identical cap of 20 attempted non-reset decisions/dispatches.
Initial bootstrap is counted separately. Stop naturally on WIN or GAME_OVER;
unused actions are not redistributed. No later reset, retry, resampling, fallback,
action substitution or policy tuning. The existing historical terminal loop has
a fallback policy and the old workload enforces 110 clients: neither may be reused
unchanged. A new closed-loop runner must fail on invalid proposals instead.

Model/artifact, Linux/Python/torch/vLLM/transformers split environments, raw-grid
representation, recent-transition limit 1, visible history-compaction accounting,
strict action schema and legal-action validation stay matched. Retain the exact
two system prompts in the machine protocol. At each step both variants applied
to the same request must differ only in system text. Across actual arms, later
observations/history can diverge because actions differ; never replay stale initial
requests or force identical trajectories. No memory sharing between episodes.
Frame/history bytes and game package versions are bound to the freeze manifest.

Require equal initial canonical observations, frame hashes, legal actions and
level counters for each game/seed pair. A mismatch invalidates the comparison;
do not retry with a different seed. Use isolated local OFFLINE environments and
development scorecards, at most one per episode (30), never production scorecards.
Retain open/bootstrap/finalize/close receipts; no ambiguous lifecycle operation is
silently counted as completed.

## Measures and analysis declared before execution

Primary: completed-level increase from initial to final observation per episode,
and paired no-example minus baseline difference for each game. Report paired
wins/ties/losses in level increase, sum of level increases, and episodes ending WIN.
Also retain every level-counter change and the step/time of first positive change.
Do not merge seed/arm episodes into a single production scorecard or normalize
against a production action budget. A successful technical run with zero completed
levels is a valid negative solving result.

Secondary, from acknowledged dispatches only:

- Number of actual transitions and entered/acknowledged/ambiguous dispatch counts.
- Canonical-observation change rate and rendered-final-frame change rate, separately.
  Changes in pixels/metadata are not automatically useful progress or hidden-state change.
- Consecutive identical `(action_id, action_data)` pairs divided by `max(n-1,0)`,
  longest identical-action streak, and repeated actions after an unchanged observation.
  Repeated actions may be appropriate; these are diagnostics, not success criteria.
- Action distribution, distinct click coordinates, clicks at (12,34), total actions,
  game-over frequency, request tokens/latency and time/action to first level increase.
- Public game-specific progress fields only if exposed and defined before execution;
  otherwise mark unavailable. Do not invent a pixel-based or model-judged progress score.

Report all 15 pairs with initial and final state/counters and all terminal reasons.
Use per-game paired differences as the analysis unit, not 600 correlated actions.
No broad significance or generalization claim from one seed and 15 known games.
No preference for the no-example prompt solely because its actions are more diverse.
Any recommendation for a larger experiment requires observed level progress plus
inspection of retained transitions; this protocol authorizes no follow-up experiment.

## Evidence and fail-closed behavior

Before each inference retain episode/game/arm/seed/step identity, full request and
hash, pre-observation reference and legal-action schema. Before response validation
retain bounded UTF-8 body (8,192 bytes), full body hash/size, request hash, local and
server token counts. Preserve structured failures through the model-process bridge;
canary evidence must survive before bridge readiness. Strict count/schema validation
remains mandatory. After dispatch retain decision ID, attempted action, journal
outcome, pre/post canonical hashes, all lossless frames and public metadata,
level counts and timestamp. Validate trajectory continuity and hash references.

Use content-addressed lossless observations to avoid duplication, with independently
reconstructable histories and request hashes. Full evidence is required for every
acknowledged transition: no sampling or silent omission. Mutable evidence ceiling
128 MiB, including temporary atomic writes and logs: control 4, monitor 16,
worker/requests/observations 88, evaluation 12, logs 8 MiB. This is a proposed
closed-loop allocation, not the existing diagnostic's 64 MiB limit. Preflight must
test the new allocation. Per-request/observation record at most 1 MiB; bridge
failure frame at most 64 KiB. Preserve a reserved 4 KiB failure receipt per component.
At evidence/deadline exhaustion stop admission, retain partial evidence and clean up;
do not truncate observations, silently drop pairs or launch a continuation.

Stop the entire attempt on transport/token/schema/dispatch/initial-pair mismatch,
unknown outcome, monitor failure or resource overflow. At natural GAME_OVER/WIN
finalize that episode and continue the fixed schedule. Any other incomplete episode
prevents a complete-comparison pass. Partial pairs remain visible and descriptive;
do not exclude them and report a selected surviving subset as the main result.

## Proposed compute budget, separate from approval

One future private offline RTX PRO 6000 attempt, maximum 3,600 provider seconds;
zero GPU seconds currently authorized and no reservation. First-cell internal
deadline 3,300 seconds includes installation, model startup, workload, evaluation
and all cleanup. Installation deadline 900 seconds; model startup cap 900 seconds;
workload at most 1,200 seconds and ending before first-cell 3,000 seconds; final
300 seconds reserved for cleanup/finalization. An individual request must finish
before the workload cutoff. Per-request timeout 120 seconds, bridge timeout 180.
Durations are ceilings, not a guarantee all 30 episodes fit; no automatic extension.

At most 600 policy requests plus one startup canary = 601 completions, each at
most 128 tokens (76,928 output tokens total). At most 600 action dispatch attempts,
30 initial bootstraps, 30 scorecard opens and 30 closes. Unknown entered dispatches
consume budget and are not replayed. No model inference for scoring or analysis.
Stop allocating decisions once any global/episode count limit is reached.

Pinned service context 65,536 tokens with 128-token output reserve; no request above
65,408 prompt tokens. RAM 128 GiB, VRAM 86 GiB, scratch 4 GiB. Monitor at 0.25 seconds,
maximum one-second sample gap, through process termination. Independent GPU cleanup
must work if the monitor dies. Require game/scorecard finalization, child-group
termination, scratch/dependency/source removal, final receipt hashes and bounded
notebook publication before acceptance. Provider timeout remains an outer limit.

## Required gates before any launch

1. Review this protocol, schedule, exact prompts, metrics and separate budget proposal.
2. Implement a new runner; test closed-loop transition feedback, matched initial
   state, no fallback/reset/retry, count limits, incomplete pairs, response retention,
   evidence exhaustion, deadlines and cleanup faults locally. Replay scripted
   episodes only as CPU validation, never label them solving evidence.
3. Freeze a new GPU-disabled notebook and all runtime/source/protocol hashes;
   independently inspect the unpacked package and review acceptance/evidence checks.
4. Obtain separate explicit source approval and one-attempt compute authorization;
   record a fresh reservation and exclusive claim, then submit once.
5. Download terminal evidence, independently evaluate, archive with hashes, and
   reconcile provider observations. Exact per-attempt billing is not established
   by aggregate quota; retain discrepancies and never infer reusable credit.

No diagnostic rerun, full pilot, production certification, advanced scheduling or
production C_admit is part of this preparation. Exact billing and the production
one-scorecard/110-distinct-game gate remain open.
