# ft09 information trace and isolated comparison proposal — September 21, 2026

The next policy call lacked a visible transient signal associated with the
preceding click. This is a demonstrated information omission, **not evidence that
animation handling caused failure or that a memory treatment improves solving**.
No live policy or notebook was changed and no compute was authorized or launched.

## Exact recovery of the historical inspection

The original generator and findings report were absent from the working tree and
reachable path history. A search of 30 unreachable local Git blobs recovered
both with exactly the SHA-256 values in the historical inspection lock:

- `scripts/inspect_phase4_closed_loop_v1.py`:
  `4a3aba9cdcd9c6716c1925ab919feadc30f7be51181a2e72f96beddf952aa9f8`
- `reports/phase4_closed_loop_v1_offline_findings.md`:
  `81ae462e03ad86d14fd9234c4c16a55d3e8bc565062dfb34c3f00055a628ce4a`

The recovered generator ran in a temporary output directory. All 11 regenerated
artifacts matched their historical hashes, as did the two recovered source files.
The original lock and historical outputs were preserved. This new report narrows
the older report's bundled suggestion about coordinates and intermediate frames
to one isolated, unapproved proposal; the historical report is not rewritten.

Reproduce with standard-library Python from the repository root:

```text
python scripts/verify_phase4_inspection_recovery.py
python scripts/analyze_phase4_ft09_information_v1.py
```

## Observation-only evidence

Input archive SHA-256:
`994dc62307777a1adf301986aa2548bb9dad84ab438963d20392736abd493f9d`.
Case: `cl1-02-no_concrete_examples`, **action 2** (one-based), archived record
`cl1-02-no_concrete_examples-step-01.json`, followed by `step-02.json`.
The extractor verifies archive/source hashes and that the next pre-observation is
exactly the preceding post-observation.

Action 2 is ACTION6 at display coordinate `(32,32)`. Relative to the pre-action
frame, the five returned frames contain:

| Returned frame (one-based) | Changed pixels | Numeric color change | Bounding box, x/y inclusive |
|---|---:|---|---|
| 1 | 0 | None | None |
| 2 | 80 | 2 → 0 | (32,32)–(61,61) |
| 3 | 0 | None | None |
| 4 | 80 | 2 → 0 | (32,32)–(61,61) |
| 5 | 0 | None | None |

The changed cells form the lower-right outline, not an 80-cell filled rectangle.
The exact changed coordinates and all numeric grids are retained in
[observation_trace.json](observation_trace.json). The [sequence image](frame_sequence.png)
shows pre-action then all five returned frames; the cyan cross marks the click in
the pre-action image only. Its colors are a display palette, not policy inputs.
No completed level was recorded.

The next request has two messages, system and user. Its user observation contains
`current_grid`, `previous_grid`, and one `recent_final_grids` entry, **all identical
to the pre-action and final returned frame**. `recent_actions` is `[6]`, without
coordinates. History compaction reports two transitions, one retained and one
omitted; the hash is a commitment, not recoverable spatial or temporal content.
There are no prior assistant messages carrying the click. The next response is
again ACTION6 at `(32,32)`.

The current final frame arrived correctly. The lost information is specifically
the two intermediate outline changes. Given only those policy-visible grids,
the model cannot distinguish this returned sequence from one whose frames were
all unchanged. It still could have selected another location using the existing
board. Repetition alone does not establish why it did not.

## Game-source-assisted interpretation — retrospective only

The independently verified development source `ft09/0d8bbf25/ft09.py`, lines
2328–2371, is copied separately in
[source_interpretation_evidence.json](source_interpretation_evidence.json).
Its hash matches the manifest bound into the frozen run.

In that source, a click is mapped to the game grid and checked for `Hkx` or `NTi`
sprites. If neither is selected, a first-level branch can set a four-frame
counter on `zth`; subsequent ticks alternate its nontransparent pixels between
color IDs 0 and 2 and complete the action. This branch is consistent with the
observed flash-and-return sequence. Hidden branch execution was not logged, so
this is a source-supported interpretation rather than a measured branch trace.

Source thus suggests the outline is feedback about a nonproductive click and
indicates an interaction distinction between surrounding decoration and tile
targets. **The frames alone do not identify sprite tags, prove a target is
clickable, or provide a winning coordinate.** No game code, sprite tags, expected
answers, hand-picked coordinates, or source-derived feedback labels may enter
live-policy requests or treatment selection. Do not rename a visual change
“invalid click” in the proposed payload.

## Action-relevant missing capability and causal limits

The narrowly identified capability is **conditioning the next decision on an
observable within-action visual change that has disappeared from the final frame**.
A model that recognizes the flash could reconsider the same location or attend
to the highlighted region. It could also misinterpret it, click the outline again,
or still fail to infer useful mechanics. Those alternatives are unresolved.

Other explanations remain plausible: difficulty locating features in textual
64×64 grids, coordinate interpretation, failure to infer interaction rules, weak
adaptation to unchanged final states, or insufficient action budget. Missing click
coordinates are a separate known limitation, not evidence that fixing them or
adding long-term memory is justified by this case. We have neither a model
counterfactual nor a successful alternative action from this inspection.

## One isolated proposal, with bounded comparison

**Proposal only, pending local implementation, review, and separate authorization.**
Add one optional `last_transition_intermediate_grid` to the existing raw
observation. Select the nonfinal returned frame with the most changed cells
relative to the preceding final grid; break ties by earliest frame index. Include
it only if it differs from both pre-action and final grids; otherwise use null.
Select from the immediately preceding action only. Include a neutral sequence
index/count identifying it as a returned intermediate frame. Do not infer
semantics, add coordinates/history, summarize game rules, or change action schema.
This isolates exposure of one transient frame; it is not a general memory system
and does not preserve every animation or its full temporal meaning.

Before any GPU request, implement this in a new development contract and test
locally against archived fixtures: this case must select returned frame 2;
unchanged and final-only-change sequences must yield null; ties, shape changes,
frame limits and payload ceilings must fail or resolve according to an explicit
contract. Regenerate requests from paired identical snapshots to prove only the
new field differs. Count actual model-tokenizer tokens offline, establish the
new maximum prompt size, and preserve exact response/action/trajectory evidence.
These checks are not implemented or claimed passed here.

If those checks pass, the smallest proposed closed-loop comparison is:

- One known development game, `ft09-0d8bbf25`, environment seed 0; three paired
  request seeds (0, 1, 2), with fresh isolated episodes and matched initial states.
- Both conditions use the same frozen no-example system prompt, model, sampling,
  action schema and final-frame/history fields. Control has no additional field;
  treatment has only the transient-frame field. No-example is held constant as
  an experimental control choice, not promoted as a superior policy.
- Alternate condition order across pairs; 20 actions per episode, six episodes,
  maximum 120 policy calls plus one canary. No retries, fallback or later resets.
- Proposed one-attempt ceiling: 3,600 provider seconds, 3,300 startup-inclusive
  internal seconds, with at least 300 seconds reserved for cleanup. Requests
  stop by the 3,000-second cutoff or the action cap, whichever comes first.
  At 128 output tokens per call, total completion ceiling is 15,488 tokens.
  Existing evidence/resource ceilings must be rechecked against the larger input
  before freeze; this report supplies no reservation or launch-ready notebook.
- Record selected frame/index, exact requests and responses, every returned
  frame, initial-state equality, all action bindings, zero-progress outcomes,
  deadlines and independent post-termination cleanup. Missing pairs or failed
  finalization invalidate the comparison; null treatment fields stay in analysis.

Primary outcome: completed-level increase per paired episode. Secondary outcomes:
subsequent non-UI board changes reported as observations (not progress), and
whether the next action changes after a transient-only transition. A different
coordinate or fewer repetitions is not a success criterion by itself. Do not
classify live interactions with privileged game-source tags. Independently evaluate
all pairs, retain failures, and reconcile usage after the single attempt.

This would be an exploratory, known-game early-progress comparison, not a powered
generalization test. Deterministic decoding may yield identical outputs across
request seeds; they are not independent game samples. Any benefit would require
later review rather than automatic policy promotion or automatic follow-up compute.

These configurations are **E1S-R-derived `arc_action_v12` development variants**,
not unchanged historical E1S-R admission evidence. Production one-scorecard /
110-distinct-game certification, production `C_admit`, and exact billing remain
open. The earlier pilot and these offline findings provide no new spending authority.
