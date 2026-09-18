# Action-selection investigation: retained v13 evidence

The first offline investigation found highly repetitive action selection and a strong association with the concrete examples in the system prompt. No model calls, game actions, GPU session, or policy deployment were performed. The validated runtime and historical sources are unchanged.

## Observed behavior

| Measure | Retained evidence |
| --- | --- |
| Clients / distinct games | 110 / 15 |
| Actions | 7,582 |
| Actions chosen | ACTION1: 2,320; ACTION6: 5,262; no other action IDs |
| Clicks at the prompt example `(12,34)` | 5,119 / 5,262 = 97.28% |
| Consecutive identical action-and-data pairs | 7,247 / 7,472 = 96.99% |
| Clients using one action-and-data pair throughout | 64 / 110 |
| Longest identical-action streak | 80 actions |
| Actions with unchanged canonical observation hash | 4,044 / 7,582 = 53.34% |
| Terminal reasons | 35 game-over; 75 action-cap |
| Completed levels | 0 |

The prompt explicitly illustrates ACTION6 with `(12,34)` and an empty-data ACTION1. Those are the two action IDs used. Most clicks use the illustrated coordinates despite the instruction that they are only examples. This makes example anchoring/copying a strong diagnostic hypothesis. It is not a causal finding: game affordances, numerical-grid grounding, constrained-decoder/model preferences and the terse response policy could also contribute. Successful response bodies were not retained, so this analysis describes dispatched actions, not verbatim model output.

The observation hash covers rendered frame bytes and public observation metadata. Identical hashes indicate unchanged canonical observations, not proof that hidden game state was unchanged. Changed hashes also do not establish useful progress: rendering, animation or other metadata can change while no level is completed. Repeated actions can be appropriate in some games; their prevalence here must be interpreted together with zero completed levels, not as a universal rule to ban repeats.

All action/dispatch journal pairs were checked for acknowledged status and matching action IDs, decision IDs and post-state hashes. The worker evidence was read from the hash-verified portable v13 archive. The 64 retained prompt samples all match request hashes in the worker ledger; they cover 64 clients, 15 starting grids, and no prior transitions. They are an early-completion sample, not a randomized sample or full trajectories. Counts of repetitions and actions use the full dispatch audit; prompt-grounding conclusions are limited to the retained samples.

Detailed per-client, per-game, coordinate-frequency and prompt-sample records: `reports/phase4_action_selection_analysis.json`. Reproduction: `scripts/analyze_phase4_action_selection.py`. Two regression tests passed for sequence counting and prompt-probe isolation.

## Prepared experiment: example sensitivity

`reports/phase4_action_selection_probe_proposal.json` contains 45 exact, hashed requests derived from one retained initial observation for each of the 15 games. Three paired arms:

1. **Baseline:** unchanged v13 request and system prompt.
2. **Relocated example:** replace only the illustrated click `(12,34)` with `(47,9)`. Keep the ACTION1 example, coordinate bounds and schema unchanged.
3. **No concrete examples:** remove the concrete ACTION6 and ACTION1 example objects and the example-coordinate explanatory sentence. Retain explicit format rules, required integer coordinates, legal-action restriction and the exact same JSON schema.

The model, observation, legal-action schema, temperature, seed, completion cap and non-thinking setting are unchanged. Arm order rotates deterministically across sorted games. There are 45 planned completions, at most 128 tokens each (5,760 completion tokens total), zero environment actions and no retries. Baseline is rerun as a paired control; historical dispatches are not assumed to be exact response matches to these sampled request objects. This is a development-only diagnostic protocol, not a replacement policy or a solving benchmark.

Predeclare analysis before execution:

- Retain complete request/response hashes and bounded response bodies, token usage, legality and schema-validation results. A schema/transport failure stops the probe and is reported, not retried or coerced. Use the pinned serving environment and startup canary; canary calls and installation/startup overhead must be included separately in any eventual execution budget.
- For observations permitting ACTION6, report baseline `(12,34)` frequency, relocated-arm `(47,9)` frequency, paired coordinate changes, and action-type switches. List per-game outcomes; 15 observations with deterministic decoding do not support a broad performance guarantee. A shift toward the relocated example supports prompt-example sensitivity; failure to shift weakens that specific hypothesis but does not prove observation grounding.
- For the no-example arm, report unchanged-action rate relative to baseline, coordinate diversity and schema validity. More diverse actions alone are not improvement and do not justify deployment.
- If an arm appears promising, propose a separately scoped short closed-loop comparison on the same development games with matched seeds/action budgets. Use completed levels, per-game progress, repeated-action streaks and unchanged-observation rates; retain observations sufficient to inspect the chosen locations. Do not tune against holdout games or move directly to production certification.

Execution remains **not authorized and not started**. No GPU time budget is inferred from the small completion count: offline installation and model loading dominate a fresh session and need their own reviewed bounded lifecycle, cleanup, reservation and authorization. Next decision: review this focused probe before implementing or launching its target runner. Advanced scheduling remains out of scope because this evidence identifies an action-selection problem, not an allocation failure.
