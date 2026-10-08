# Milestone E: paired control-interface action selection, protocol r1

Status: prepared development probe, CPU review only. No source/use approval, compute
authorization, reservation, upload or GPU launch is created by this package. All
earlier smoke attempts remain consumed, including the successful runtime attempt.

The user selected the paired observation probe before a closed-loop pilot. The
verified model bundle lacks game-engine packages. This package imports no game
engine, dispatches zero game actions and opens zero scorecards.

## Question and frozen sample

Does adding v3's computed control metadata improve action validity on retained
real game observations, and does it change the actions selected? This follows
Track A's interface-usability result in evidence comprehension v3. It does not
test the history intervention, which did not meet its criterion.

Thirty observations come from all 15 `no_concrete_examples` development games in
`evidence/phase4-closed-loop-v1-r1-completed-v1.zip`, selecting steps 0 and 10 of
each episode before observing any new model answer. The frozen source archive
SHA256 is `994dc62307777a1adf301986aa2548bb9dad84ab438963d20392736abd493f9d`.
`cases-lock.json` pins every extracted observation through the case-file digest;
each case also retains the source member name and digest. All 30 observations
have distinct hashes. Grids, legal actions, levels, recent actions, prior frames
and history-compaction fields are retained unchanged. There are no synthetic
observations, action-outcome alterations or history-assistance additions.

These games and trajectories are already exposed development material. The two
contexts per game are correlated. Repeated passes measure repeatability, not
independent samples. This is not a fresh withheld evaluation or production
certification, and no response is selected for its usefulness after the run.

## Controlled comparison

| Arm | Observation | Shared background |
|---|---|---|
| `reference` | retained raw observation | identical system prompt, JSON-format decoder, model and sampling |
| `computed_control_metadata` | reference plus one field of that name | exactly the same |

The added field is the exact v3 Track A deterministic mapping from current
legal IDs to required action data: ID 6 takes integer x/y in 0..63; the other
IDs take empty `{}`. Its description says it is tool-computed and does not use
history. This is assisted interface usability, not unaided reasoning.

The reference is an E1S-R-derived development configuration. The historical
no-example prompt provides its background, with the phrase about a supplied
schema replaced by an explicit object-shape instruction. In both arms, the
historical legal-action-constrained `arc_action_v12` decoder is replaced by
`response_format={"type":"json_object"}`. The earlier decoder enforced legal IDs
and arguments and would make the principal validity measurement automatic.
Both arms receive exactly the same new background. Neither arm is an unchanged
historical baseline, and no comparison with historical performance is claimed.

Temperature 0, seed 0, non-thinking, max_tokens 128, served model
Qwen3-VL-30B-A3B-Instruct-FP8, revision
`d9748a51ae66354c4dad665aab2c71f26cf2c8cd` are shared. Prefix caching is explicitly
disabled for both arms and verified from the server's retained startup
configuration before research. Missing, enabled or conflicting configuration
evidence fails the run. This does not promise bitwise GPU determinism.

Each context is answered under both arms twice: 30 × 2 × 2 = 120 completions.
The first pass alternates reference-first/candidate-first across cases. The
second pass exactly reverses the full first-pass schedule. Case IDs, arm order,
pass numbers and request IDs E000..E119 are frozen in `protocol.json`.

## Scoring and interpretation

The independent scorer reconstructs each expected request and recomputes
validity from raw responses; it ignores runner-supplied validity labels.
Duplicate JSON keys, non-finite constants, wrong object shapes, reset/illegal
IDs, boolean IDs/coordinates, out-of-range coordinates, extra arguments and
missing arguments are invalid. There is no repair, fallback action or retry.

The primary measure is the fraction of contexts producing a valid action in
**both** passes, by arm. Report paired context counts: improved, regressed,
both valid and neither valid. Include the same counts by game (15 clusters),
per-response parsing/shape/ID/argument components, exact repeatability and
valid action/coordinate switches in each pass. No independence-based confidence
interval or arbitrary promotion threshold is attached to these 30 contexts.

An invalid action is an observed scientific outcome and counts as invalid; it
does not by itself make the technical run fail. HTTP errors, malformed server
envelopes, unfinished/truncated completions, unexpected model identity, invalid
usage/context budgets, missing/duplicate/reordered responses, request drift,
timeouts and failed cleanup make the run technically incomplete or failed.
Partial responses and request intents are retained; there is no complete
scientific verdict without all 120 answers. A technically passing run need not
favor the candidate.

Every complete comparison is labelled
`development_diagnostic_only_no_policy_promotion`. If both arms are at ceiling,
validity cannot discriminate them; action switches are descriptive. If validity
improves without regressions, the result motivates a separately reviewed
closed-loop pilot. Mixed or worse validity motivates diagnosis first. No action
usefulness oracle, level-progress claim, solving claim, history-intervention
adoption or policy promotion follows from this probe.

## Runtime proposal and lifecycle

Reuse the pinned Kaggle image and hash-pinned 174-wheel publisher installation
from the successful smoke runtime. The model is consumed from the separately
verified private version-1 dataset with full binary tree digest
`b480ad92cda91474084c795d2ff64b07a6c477909b22d2784d24abf8fb4ef7df`.
Public protocol account/model-location placeholders are intentional; the exact
resolved package is retained privately for review.

Proposed compute: **one RTX PRO 6000, at most 3,600 seconds, at most 131 counted
HTTP requests, one attempt, zero automatic retries**. This is a new proposal;
the earlier smoke authorization of at most 12 requests cannot cover it.
The internal deadline is 3,420 seconds; admission closes at 3,120 seconds,
reserving 300 seconds for cleanup. Research has its own 1,500-second ceiling,
bounded by the earlier admission cutoff. Every request uses an absolute
watchdog deadline of at most 60 seconds during research. Runtime checks retain
3 startup + 4 compatibility + at most 4 cancellation HTTP requests; their 11
calls are included in 131. The two explicitly planned cancellation metrics
observations are counted; they are not retries of an experiment or attempt.

The pinned offline tokenizer audit counts all 60 distinct requests and checks
both passes: 2,128,220 scheduled prompt tokens, maximum 36,120, below the 60,000
prompt ceiling and 65,536 context limit with the 128-token output cap. The audit
uses Transformers 4.57.6/tokenizers 0.22.2 and verifies all six tokenizer-file
hashes. Its result and request hashes are embedded in the review source lock.

`control_interface_action_selection_v1_budget.json` uses explicit assumed rates
of 5, 10 and 20 seconds per research call, with a separate 1,000-second runtime
allowance. These are planning scenarios, not forecasts. The 20-second scenario
exceeds the research ceiling. Historical calls used different decoder/cache
settings; small smoke prompts do not predict this workload's throughput. Slow
runs stop, retain incomplete evidence and clean up. Phase ceilings are upper
limits, not promises that all maxima fit when added together.

Scoped derivatives preserve the smoke controller's protected PID/process-group
ownership, installation descendants, request watchdogs, cancellation,
termination/reaping, GPU cleanup, environment/source removal, evidence
finalization and explicit final deadline before a passing verdict. Emergency
termination stays possible after an overrun; it cannot restore a passing
verdict. Original smoke sources and r10 snapshot remain unchanged.

## Review and reproduction

The GPU-disabled r1 snapshot binds all research Python files, protocol, cases,
case lock, derivation record, tokenizer audit, trusted inputs and the complete
shared smoke Python closure. Preparation creates no authority sidecars. The
new scope requires its own exact source review, account/attachment evidence,
scoped direct-use assessment, compute authorization and fresh reservation.
No previous source approval or consumed attempt is carried forward.

CPU checks exercise field isolation, strict independent scoring, incomplete and
tampered evidence, exact schedule, token/context limits, cache configuration,
request caps, restored cleanup clock after a research overrun, and actual
fixture installation/local HTTP including semantic-invalid, truncation and
timeout paths. They use scripted responses and establish no model performance.

```text
python scripts/build_control_interface_action_selection_v1.py --check
python scripts/control_interface_action_selection_package.py review-check --revision 1
python scripts/run_control_interface_action_selection_checks.py
```

The review check requires Linux and stops before any installation, GPU query or
model use. Token auditing separately requires the retained exact tokenizer and
its pinned CPU environment. No Kaggle launch command is provided or invoked by
this preparation.
