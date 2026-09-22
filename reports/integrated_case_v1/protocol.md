# Integrated perception-to-action case study v1

Status: frozen case specification for review. No model calls, environment actions,
compute reservation, notebook approval, or launch authorization. This supersedes
the proposed next isolated indexing study, not any historical evidence lock.

Question: on this already-inspected development board, where is the first
observed consequential break between recognizing visible structure, intentionally
operating a control, predicting its effect, updating from feedback, and making
environment-confirmed progress?

## Case and boundary

Use only `ar25-0c556536`, environment seed 0, initial state from
`cl1-00-no_concrete_examples` in the locked historical archive. `case.json` binds
the archive/member, all initial observation bytes, canonical state hash, and
selected grid. Both arms start in separate fresh environment instances with
identical initial grids, legal controls, state and progress counters. Bootstrap
once per arm; abort the comparison on mismatch, without reset or retry. A GUID
may differ; it cannot substitute for state equality. No exploration beyond eight
actions per arm. Stop at first increased level counter, WIN, GAME_OVER, or cap;
do not continue into another level. Stop both arms on a technical failure and
label the comparison incomplete, retaining any partial evidence.

The development inventory explicitly records prior visual, trajectory and
game-source-assisted inspection. This is eligible only as an inspected
development case, never untouched transfer or a generalization benchmark.
Walkthrough exposure is not established. Existing source interpretations,
human walkthroughs, archived future outcomes and the geometric answer key stay
outside model inputs. No new game-source inspection is needed.

## Conditions and matched quantities

Baseline means the current unpromoted development control: the no-example,
E1S-R-derived `arc_action_v12` policy bound by
`certification/phase4_transient_v2/protocol.json`, control arm. It is not unchanged
historical E1S-R and does not modify `agent/production_main.py`. Preserve its
prompt, observation packing/history compaction, legal-action schema and 128-token
completion limit. Do not elicit explanations from this arm or retrospectively
infer unspoken intentions. Its unavailable diagnostic measures are unobserved.

Structured condition is an explicit scaffold bundle: questions, an external
record of its own declared predictions, and access to all retained frames from
its last transition. It is not a transparent window into baseline reasoning and
does not isolate prompting from extra inference, memory or feedback exposure.
Both arms see raw integer grids; no image rendering, object labels, masks,
coordinate overlays, solution examples, or answer-key corrections are injected.
Record exactly which frames reach each request. Baseline keeps its existing
observation view; structured feedback sees every returned frame in order, with
indices and the pre-action frame. Do not claim a same-information comparison.

Fix Qwen/Qwen3-VL-30B-A3B-Instruct-FP8 revision
`d9748a51ae66354c4dad665aab2c71f26cf2c8cd`, model tree
`052ab27f06c28261e143b8c1638382d107b034692bc0cd1792ec4e02ddab8627`,
vLLM 0.19.0, the repaired pinned tokenizer manifest, temperature 0, seed 0,
non-thinking decoding and raw-grid serialization. Baseline first, structured
second; no result from one enters the other's state. A single fixed order cannot
separate order effects. Eight dispatch attempts per arm; no fallback, RESET,
invalid-action substitution, response repair, extra questions or automatic retry.

## Fixed structured question sequence

These are task specifications to be compiled into exact JSON requests during
implementation, then separately frozen and token-audited before any approval.
All answers are concise observable claims, not unrestricted reasoning traces.
Each claim carries an ID and status `observed`, `hypothesized`, or `uncertain`.

1. Initial inventory (one call, at most 2,048 output tokens): identify at most six
   visible regions by bounding box and row spans of occupied cells. Describe
   outer silhouette separately from internal colors/markings. State at most six
   pairwise translation/rotation/reflection claims, explicitly permitting multiple
   equivalent transformations. List ambiguous segmentations. List the supplied
   legal action IDs and argument requirements, separating command syntax from
   unknown game effects. State at most two tentative goal hypotheses; neither is
   treated as a supplied objective or an established rule.
2. Before each action (one call, at most 1,024 output tokens): give at most two
   competing effect hypotheses, one intended target as explicit cells/row spans
   or a named region previously defined by those cells (or `no_spatial_target`),
   one legal action object, a specific observable prediction and a distinct
   alternative, and the result that would leave both unresolved. State a short
   subgoal, expected information gained and any prior evidence IDs used. For a
   repeated action state what unresolved distinction the repetition tests. Do not
   include example coordinates, game-specific mechanics or winning moves.
3. After each action, including the last (one call, at most 1,024 output tokens):
   compare the retained pre-frame with every returned intermediate/final frame;
   identify changed cells or a bounded region and describe the observed change.
   Classify each precommitted prediction as supported, contradicted or unresolved
   with frame/cell evidence. Separate correct dispatch, geometric target hit and
   observed game effect. Update the hypotheses and say what next test would follow.
   This feedback response cannot dispatch an action. The next decision must cite
   it, or explicitly say why the same test is still informative.

Prediction fields must be mechanically interpretable where possible: frame
selector (`final` or `any_returned`), region mask, predicate (`no_cell_change`,
`any_cell_change`, `exact_color_at`, `exact_translation_of_mask`, or
`level_counter_increase`), and predicate arguments. Free-text alternatives are
retained and rubric-scored but cannot silently become mechanical truth. Reject
out-of-bounds references; preserve their raw responses as invalid outputs.
Selection/highlight/rotation are hypotheses unless their proposed visible
signature is explicitly defined. Hidden selection cannot be inferred from no
visible change. No credit for verbose or confident unsupported explanations.

## Budget and technical evidence requirements

Maximum: two episodes, 16 dispatch attempts, eight baseline calls, 17 structured
calls (one inventory, eight decisions, eight feedback), plus one startup canary:
26 model calls total. Maximum generated tokens: 19,584 including the 128-token
canary. All calls count even on transport failure or invalid output; no retry.
Early termination reduces calls; record why planned slots were unused.

This freezes an interaction/inference ceiling, not a provider-time proposal.
Provider authorization is zero. Before requesting compute, implementation must
audit the exact initial requests and bounded worst-case adaptive histories with
the actual pinned tokenizer, freeze prompt/payload/context and total inference
limits, and size startup-inclusive wall time from measured startup costs. No
silent truncation of grids or prior predictions is permitted; stop with retained
evidence if admission cannot fit. No old reservation credit is reused.

Retain every request and bounded raw response/hash/counts before validation,
including across the model bridge. Retain intended-target declarations, serialized
and dispatched actions, acknowledgements, all observation frames and counters,
monotonic timestamps, every abort and omission, and a final receipt. Every step
binds its pre-observation, prediction response, dispatch and post-observation.
Freeze startup/install bounds, absolute admission cutoff, cleanup reserve,
monitoring, evidence/resource ceilings and independent process/GPU cleanup in the
later executable protocol. Missing cleanup is a technical failure, not a low
capability score. The runner must be private/unscored; it creates no production
scorecard. Any local environment bookkeeping is retained separately.

## Decision boundary

Use `rubric.md` stage-by-stage, not one opaque total. Report the earliest supported
failure and downstream stages that could not be assessed. Missing intent in the
baseline is unobserved, not incorrect. A scaffold benefit is descriptive evidence
on this case only; extra token/time cost and all bundle differences must accompany
it. Neither diversity, accurate descriptions nor changed pixels count as solving.
Progress/completion requires the environment's counters or terminal state.

No automatic follow-up is authorized. A failure in structure suggests grounding;
correct structure with a missed declared target suggests coordinate mapping;
correct targeting with incorrect predicted effects suggests control discovery;
contradictions not reflected in later choices suggest feedback use; accurate
effects with ineffective sequences suggest goal inference/planning. All remain
investigation leads, not isolated causal diagnoses. At this short horizon, zero
progress is not proof that a capability or scaffold cannot help.

Review this specification and rubric first. Later implementation needs local
scripted trajectories, independent replay, exact prompt/schema and budget locks,
a GPU-disabled notebook, and separate source approval and compute authorization.
Production one-scorecard/110-distinct-game certification, workload-specific
admission limits and exact billing remain separate open gates.
