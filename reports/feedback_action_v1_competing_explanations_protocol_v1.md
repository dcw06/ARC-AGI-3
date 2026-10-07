# Competing explanations: Track 1 amendment v1

**Status: development proposal only.** This amendment authorizes no model call, reservation, GPU run, package lock, or change to frozen Track 1 evidence. The parent protocol remains a draft without compute authority.

## Question and challenge set

When an agent is uncertain about a game mechanic, does explicitly testing competing explanations improve action selection with fewer wasted actions?

`research/feedback_action_v1/competing_explanations_v1.json` contains four synthetic development-only cases. Each public prompt includes the observed board, legal actions, `transition_evidence_v2` action-effect view, competing explanations, and a fixed probe plan. Raw history is kept separate from `evaluator_only`; the answer key contains the hidden synthetic mechanisms, expected outcome classes, what each outcome supports, and what remains unknown. The generator rejects worlds whose pre-probe raw history or evidence view differs.

| Case | Explanations | Diagnostic probe | Caution |
|---|---|---|---|
| Ineffective click | correct ACTION6 at wrong position; wrong action type at tested position | change action type while holding coordinates fixed | a no-change outcome can still have other causes |
| Blocked movement | local wall blocks the tried direction; movement is unavailable in this state | try another legal direction | success shows some movement works, not that the wall was the sole cause |
| Delayed effect | third consecutive action has an effect; action is ineffective | repeat twice, observing after each call | two more no-change outcomes do not exclude a longer delay or precondition |
| Level rule shift | prior ACTION4 rule persists; the rule was level-specific | test ACTION4 after the level boundary | a changed frame is not proof of objective progress or learning |

## CPU checks

The answer checker replays both hidden worlds through the offline synthetic engine, rebuilds the action-effect view from raw transitions, and derives probe outcomes from observed frames and level counts. It checks that the hypotheses are observationally identical before the probe, the planned probe separates their predictions, and no oracle answer leaks into the public prompt.

Run from the Track 1 checkout:

```bash
python -m research.feedback_action_v1.competing_explanations --check
python -m unittest -v tests.test_feedback_action_v1_competing_explanations
```

These are scripted CPU diagnostics, not real-game results. They do not certify generalization.

## Proposed baseline comparison

The existing Track 1 candidate bundles a procedure, required hypothesis block, carried statement, and a larger completion cap. Comparing that candidate directly with the existing baseline cannot attribute an effect specifically to competing-explanation testing. For a causal comparison, create a new reviewed protocol version: keep the baseline behavior and explicit-hypothesis candidate identical in model, evidence view, engine, seed, action cap, decision-call cap, completion-token cap, schedule, and stop rules; change only whether the policy must enumerate at least two explanations, predict probe outcomes, choose a discriminating available action, and revise its rule after observing the result. Normalize the token cap in both arms and publish the new exact source before any run.

Pair from identical initial states and keep **24 dispatched actions and at most 32 model calls per episode in each arm**. Invalid outputs consume calls, not actions; failures and unknown outcomes remain in denominators. The two arms receive the same per-episode budget and evidence. Protocol review, compute approval, and reservation are separate prerequisites; none is granted here.

## Measures and failure examples

- **Mechanic prediction accuracy:** score a pre-probe prediction against the hidden mechanism separately from task completion.
- **Hypothesis revision accuracy:** after each outcome, score whether the agent retains, rejects, or marks each explanation unresolved according to the oracle. Do not count mere verbal acknowledgment as revision.
- **Probe discrimination:** whether the chosen action's predicted outcomes partition the currently plausible explanations; report probe actions and model calls used.
- **Next-transition prediction:** compare predicted visual effect and progress status with the next raw transition.
- **Task result:** completed levels, reported separately. A board change alone is not progress.
- **Action accounting:** classify each opportunity as task progress, hypothesis-discriminating information, both, or neither. No observed change is not automatically a wasted action: it may test a blocked direction or be the expected first step of a delayed effect.
- Report per-episode numerators, denominators, failures, unknowns, and undefined rates. Do not remove invalid calls from an opportunity denominator or call an untested mechanism a miss.

Examples that must not be scored as learning: repeating a blocked click cannot distinguish position from action type; a second no-change delayed-switch observation does not prove ineffectiveness; moving in a new direction after a wall bump does not prove the wall caused the first no-op; and moving the board after a level change does not prove the old rule still advances the objective. Prediction, revision, probe value, and level completion remain distinct outcomes.