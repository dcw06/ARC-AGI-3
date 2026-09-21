# Transient-frame v1 — local implementation review

Status: review candidate, GPU disabled, no compute authority or reservation.
This is an E1S-R-derived `arc_action_v12` development variant, not unchanged
E1S-R admission evidence. Neither lower repetition nor exposed animation proves
improved solving. Production certification, production `C_admit`, and exact billing
remain open.

## Isolated change and exact selection contract

The new namespace is `certification/phase4_transient_v1`. The completed closed-loop
revision and recovered inspection generator remain unchanged. Both conditions
use the exact historical no-example system prompt, temperature 0, non-thinking
mode, schema `arc_action_v12`, and a 128-token completion cap. Control has no new
field. Treatment adds only `observation.last_transition_intermediate_grid`.
Previous coordinates, longer history, semantic feedback labels, game code, and
source-derived targets are not added to requests.

Selection uses only the immediately preceding acknowledged transition:

1. Validate the prior final grid and every returned grid. Each must be a nonempty
   rectangular grid, at most 64×64, with integer color IDs 0–15 (booleans rejected).
   Returned sequences must contain 1–64 frames.
2. Any shape difference anywhere in that transition is a hard failure, in both
   arms, including an intermediate frame that would otherwise be ineligible.
   No resizing, truncation, or substitution with null is permitted.
3. Exclude the final returned frame. From the remaining frames, exclude any equal
   to the prior final grid **or** the new final grid, before ranking candidates.
4. Select the candidate with most changed cells relative to the prior final grid.
   Break ties by the earliest zero-based returned-frame index.
5. Return `{grid, frame_index_zero_based, returned_frame_count}`. Return null for
   an initial request, a one-frame sequence, or an empty eligible set. Control
   applies the same shape/sequence guards but omits the field entirely.

Bootstrap and final observation records also receive bounds checks. Post-action
evidence is retained before transition validation; a malformed/shape-changing
transition fails the attempt rather than erasing its acknowledgement. Full
observations, not just the selected frame, remain in the evidence archive.

`protocol.json` and `reports/phase4_transient_v1_protocol.json` freeze this rule and
the six-episode schedule: one development game `ft09-0d8bbf25`, environment seed 0,
three paired request seeds 0/1/2, alternating condition order, 20 actions per
episode. Deterministic decoding may reproduce outputs across seeds; these are
not three independent games. The comparison is exploratory early-progress work.

## Replay and bounded execution

The worker and model service cap policy calls at 120. Independent trajectory
replay retains the historical response, journal, request, progress, scorecard,
deadline, continuity, evidence-inventory, and initial-state checks. Pairing uses
game plus pair index, so the three pairs of one game cannot overwrite each other.

`independent_selection.py` independently filters/ranks frames read from the
content-addressed observation records; it does not call the worker selector or
trust a logged selected-frame claim. It reconstructs the original no-example
request and adds the independently derived field only for the treatment. Thus
changed pixels, false indices, omitted fields, added coordinate history, or wrong
seeds are rejected even if the request and audit hashes are recomputed.

Both the compact canonical request and the default JSON transport serialization
must be at most 65,536 UTF-8 bytes. The selected field is at most 16,384 bytes.
The model-side service applies the actual tokenizer's chat template with
`truncation=False` before transport and enforces prompt + completion ≤65,536
tokens. Server/tokenizer counts must agree after response retention; failure
evidence continues across the model-process bridge. No retry/fallback is added.

The separate compute proposal remains one attempt, 3,600 provider seconds and
3,300 startup-inclusive internal seconds, installation/startup bounds of 900
seconds each, at most 1,200 workload seconds, absolute workload cutoff 3,000,
and a 300-second cleanup reserve. It permits at most 120 policy calls plus one
canary (15,488 completion tokens), six initial bootstraps and no later resets.
Existing 128 MiB evidence, 4 GiB scratch, 128 GiB RAM and 86 GiB VRAM ceilings and
independent cleanup monitoring are preserved. Authorized seconds/attempts are zero.

## Local validation evidence

The clean-checkout regression copies only committed files/archives, supplies no
ignored `reports/runs` tree, and regenerates all 11 inspection artifacts. The
wrapper stages hash-checked game files in a private temporary checkout, restores
module globals afterward, and leaves the recovered generator and historical lock
unchanged. Its updated bytes are bound in this new review, superseding only the
wrapper binding in the earlier information-trace receipt; that old receipt is
preserved as history.
On Linux the wrapper also restores the generated text files' historical CRLF
newlines, but only when that conversion exactly matches the locked SHA-256.
Retained files and the generator are never normalized or rewritten.

Transient regressions cover null/eligible cases, filter-before-rank, earliest ties,
shape/palette/count errors, matched builder requests at all three seeds, independent
negative mutations, incomplete pairs, token boundaries/mismatch retention,
deadlines/cancellation, evidence exhaustion, cleanup failure, and the full
six-episode 120-action cap. Supervised CPU lifecycle replay and actual local
`ft09` integration completed six episodes and 120 scripted calls. These are
integration checks, not model-performance results. See
`reports/phase4_transient_v1_local.json` and `evidence/phase4-transient-v1-local.zip`.

The real tokenizer files were downloaded at frozen revision
`d9748a51ae66354c4dad665aab2c71f26cf2c8cd`, archived without model weights, and
hash-bound in `tokenizer_manifest.json`. Transformers 4.57.6/tokenizers 0.22.2
reproduced **all 600** retained target tokenizer counts. For 600 matched archived
control/treatment requests, 177 treatment fields were nonnull; removing the one
field restored each control request exactly. Maximum control prompt: 36,053
tokens; treatment: 43,668; maximum increase: 10,862; largest compact treatment
request: 45,928 bytes. No truncation occurred. See
`reports/phase4_transient_v1_token_audit.json` for all per-request counts/hashes.

This local audit used a CPU Windows Python 3.11 environment; it is not another
Linux/Python 3.12/vLLM validation. Matching historical counts is supporting evidence,
not a substitute for target token parity or proof of a worst-case future bound.
The model startup path checks tokenizer file hashes and every future request is
budget checked. A future target failure remains a failure, not a reason to resize
or silently omit the treatment.

Reproduce the main checks:

```text
python -m unittest tests.test_phase4_inspection_archive_restore
python -m unittest tests.test_phase4_transient_v1
python scripts/check_phase4_transient_local.py
python scripts/verify_phase4_transient_local.py
python scripts/audit_phase4_transient_tokens.py
```

The transient test/CPU runner requires the existing Linux game environment. The
token audit requires Transformers 4.57.6, tokenizers 0.22.2 and Jinja2 3.1.6; the
archived tokenizer is read locally. The CPU runner creates its evidence archive
exclusively and will not overwrite an existing run. Review-notebook source/artifact
bindings and final validation results are recorded separately after packaging.

The first GPU-disabled snapshot (`phase4-transient-v1-review-r1`) preceded a final
regression fix: the independent frame-validation function shadowed the evidence
inventory variable. Tests caught the error, and the import now uses a distinct
name. R1 is retained for provenance and is **superseded, not accepted**. R2 passed
the runtime/package checks, but its inspection wrapper still needed explicit
historical-newline reproduction on Linux. R2 is also superseded. The final review
candidate is R3, including that portability repair and both-platform checks.

## Review disposition

Package a new private/offline GPU-disabled notebook; do not toggle an existing
notebook. Its authority gate unconditionally rejects live execution. Even old
approval sidecars cannot authorize this scope. A later reviewed approval/reservation
revision is required before any upload or GPU launch.

This work only prepares the proposed six-episode comparison. Both prompts remain
the same no-example prompt; no prompt is promoted. No privileged source information
enters policy requests. Level progress is the primary outcome; a changed next
action, transient exposure, or reduced repetition alone cannot establish benefit.
