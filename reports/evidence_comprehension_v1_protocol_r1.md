# Evidence comprehension v1: protocol draft (for review; no compute authorized)

**Status:** draft. The frozen probe set, answer keys, scorer and tests are built and pass
offline. Nothing has been sent to a model. The live runner and review package have not been
built; they follow only after this protocol is reviewed. No GPU reservation, upload or launch.

## Question

Roadmap step 1: **can the agent read its own controls and action-effect evidence?** The
action-effect history experiment gave the model accurate evidence and showed no solving
improvement. Before testing any intervention that relies on that evidence, we check whether the
model can answer factual questions about it. The model never chooses an action here, and no game
is played.

Success means accurate answers from the model across cases. It does not mean passing the tests
for the code that builds the records; those tests only establish that the answer keys are right.

## Question families

Each question maps to one of the research questions in step 1.

| Family | Research question | Asks | Answer |
|---|---|---|---|
| `available_actions` | Available vs unavailable actions | Which action_ids can be chosen next? | set of ids |
| `coordinate_actions` | Which actions need coordinates | Which choosable ids need x and y? | set of ids |
| `recall_action` | Recover the exact action from history | The exact action at step *s*, or the latest | action, or `not_shown` |
| `outcome_class` | No-change vs failed/unknown; transient vs final | The outcome of step *s* | one of 5 outcome labels, or `not_shown` |
| `observed_effect` | An effect is unknown until observed | What the history shows for exactly this action | outcome label, or `not_observed` |
| `tried_unchanged` | Bridge to step 3: what already failed here | Exact actions tried on the still-current frame without changing it | set of actions |

Outcome labels are `final_frame_changed`, `changed_then_returned`, `acknowledged_no_change`,
`dispatch_failed` and `outcome_unknown`. Each question defines them. Every answer is constrained
by a strict JSON schema, and each request asks one question.

## Contexts and conditions

- **evidence_only:** 462 probes in 44 contexts, with no grids.
  - 36 contexts are seeded synthetic histories.
  - 8 are hand-designed, each built around one distinction, and ask about every shown step.
  - Records come from the real record code, applied to the action-effect fixtures.
  - The observation format is the live one: `legal_actions`, `recent_actions` and the
    `action_effect_history` field with its live description text.
  - Deliberate variations: exact repeats, near-miss clicks (±1 cell), history entries whose
    action_id is not currently available, histories longer than the 4 shown entries, and empty
    histories.
- **full_observation:** 182 probes in 18 contexts. Each context is the exact observation the live
  history arm received: grids, history and everything else. They come from the hash-verified
  archive, from the block-1 history episodes of ar25, s5i5 and wa30 at decisions 0, 3, 5, 7, 9
  and 11. The live run only produced acknowledged outcomes, so this condition covers fewer
  outcome kinds.

The system prompt is a one-sentence answering instruction followed by the live control text,
verbatim. The model is told exactly what it was told about its controls in the live run.

## Answer keys

Every key is computed twice:
1. from the history entries shown to the model (`probes.py`);
2. from raw frames and dispatch outcomes, by `independent.py`. That module imports nothing: it
   recounts cell changes, rebuilds the shown window, and answers each question with separate
   logic. For real contexts, it works from the archived engine steps rather than the request.

The build fails on any disagreement. The tests check that:
- a fresh build is byte-identical to the frozen set;
- every key is valid under its schema;
- real contexts equal the archived requests;
- requests contain only the observation and the question;
- coverage minimums are met.

The probe set is `research/evidence_comprehension_v1/probes.json`, SHA-256 in
`reports/evidence_comprehension_v1_probe_summary.json`.

## Shortcut baselines

Several shortcuts can score well without reading the evidence correctly. Their accuracy on the
probe set is computed now, before any model answers exist. In evidence_only:

| Family | Best shortcut | Accuracy |
|---|---|---|
| available_actions | ids seen in history | 0.136 |
| coordinate_actions | always `[6]` | 0.500 |
| recall_action | always the latest entry | 0.536 |
| outcome_class | the latest entry's outcome | 0.281 |
| observed_effect | ignore coordinates (same action_id counts) | 0.698 |
| tried_unchanged | every no-change entry, ignoring later changes | 0.568 |

In full_observation, some shortcuts are strong (tried_unchanged 0.944, outcome_class 0.769),
because the real run has few outcome kinds.

## Pre-registered analysis

Accuracy is reported per condition and family, with Wilson 95% intervals. Invalid or missing
answers count as wrong.

- **Understands** a family: accuracy ≥ 0.90 **and** the Wilson lower bound is above the family's
  best shortcut.
- **Does not understand**: accuracy < 0.70, **or** the Wilson lower bound is at or below the best
  shortcut.
- Otherwise: **partial**.
- A family whose best shortcut is ≥ 0.90 in a condition is **not diagnostic** there. It is
  reported, but not classified.

Strata are reported separately and never pooled away:
- near-miss clicks;
- absent steps;
- empty histories;
- history containing unavailable ids;
- dimension changes (see the known issue below);
- designed versus generated contexts.

**Grids versus no grids.** Accuracy in full_observation minus evidence_only is reported for the
shared families. It is descriptive only, because the two conditions use different contexts.

**Repeatability.** There are two passes over all 644 probes, with prefix caching disabled. The
second pass runs in reverse order. Per-probe answer agreement is reported. In the action-effect
history run, byte-identical requests got different answers at temperature 0, so this measures
that variance with caching ruled out. Scores are reported per pass. A probe counts as correct
only if both passes are correct, and pass-1-only accuracy is also given.

## How the result feeds the next step

- **observed_effect, outcome_class and tried_unchanged understood in evidence_only:** the evidence
  is readable, and step 3 (evidence-guided action selection) is the next intervention.
- **Any of them not understood:** the evidence presentation is the first thing to fix. Step 3
  would be premature, since a policy cannot use evidence it misreads.
- **Understood without grids but not with them:** the grids are distracting the model from the
  evidence. That is a presentation problem to address before step 3.

## Known issue measured, not fixed

The live history description says `null means the dispatch failed or its outcome is unknown`.
For an acknowledged action whose returned frame changed dimensions, though, the record holds a
per-frame count of `null` while `final_frame_changed` is `true`. The live description is kept
unchanged here, because it is what the live model saw. The dimension-change stratum measures
whether the model is misled. Any correction belongs to a later, separately reviewed version.

## Guardrails

- The bottom-row pattern seen in s5i5 and wa30 remains a hypothesis. Nothing here masks it or
  reinterprets the completed experiment.
- The probes never recommend an action, and no answer is fed back into any policy.
- Development cases only. The archived real contexts come from games the model has seen before,
  which is fine for reading comprehension, but these results say nothing about generalization.

## Budget (estimate; to be finalized with the pinned tokenizer)

The total is 1,288 calls: 644 probes in each of two passes. The estimated prompt tokens per pass
are ~1.21 M for evidence_only and ~4.52 M for full_observation, so ~11.5 M for both passes. That
is scaled from the archived run's measured tokens per character. The largest request is ~27 k
tokens. Wall time should be around 1,500 s, including the 403 s model startup and serial calls at
the latency the archived run measured. The proposal will be ≤ 3,600 s with one attempt, and the
live path would reuse the reviewed action-effect-history host, supervisor and evidence stack.

## Decisions for the reviewer

1. The pre-registered thresholds (0.90, 0.70, above the best shortcut) and the
   non-diagnostic rule.
2. Whether to keep both conditions, or run evidence_only alone first. That would be about 21% of
   the prompt tokens: ~1.2 M of ~5.7 M per pass.
3. Two passes with prefix caching disabled, or one pass.
4. Whether roadmap step 2 (progress versus visible change) should be a separate probe set, as
   proposed, rather than folded into this one.
