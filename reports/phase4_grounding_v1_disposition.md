# Grounding v1 R1: technical pass, limited diagnostic correctness

Kaggle version 1 completed. All 24 downloaded files passed their retained length
and SHA-256 checks. Frozen independent replay passed, including request bindings,
token parity, deadlines, process/GPU cleanup, and dependency/source removal.
No environment actions or scorecards were performed. Diagnostic correctness is
separate from this technical pass.

| Task | Exact answers | Malformed |
|---|---:|---:|
| Grid reading | 2/4 | 0 |
| Unique-region localization | 0/4 | 0 |
| Frame changes | 0/4 | 0 |

All twelve planned responses were received; zero transport failures. By source
game: ar25 1/3, ft09 1/3, ls20 0/3, sc25 0/3. These are four correlated development
source groups, not twelve independent generalization trials.

## Concrete errors and interpretation

The two incorrect grid-reading answers (g08, g11) equal the color at the transposed
coordinate. This is consistent with axis confusion but does not establish the
model's internal cause; the same numeric color may also occur elsewhere.

Every localization response had wrong bounds and first-cell coordinates. The
reported region counts match, but the area was explicitly supplied in each
question: this is not independent evidence of successful region extraction.

The unchanged ar25 frame pair (g03) incorrectly elicited four changed cells and
non-null bounds/colors. The ft09 transient case (g06) actually contains 80 changed
cells within inclusive bounds `(32,32)-(61,61)`, color 2 to 0. The model instead
reported one changed cell, bounds `(27,27)-(31,31)`, color 12 to 5. Both other
changed-frame cases also had incorrect counts, bounds, coordinates, and colors.

These results support investigating basic raw-grid grounding before attributing
ineffective gameplay to planning or memory. They do not prove a universal inability
to perceive, discover mechanics, or solve games. They do not measure geometry,
intentional action dispatch, or a representation treatment's benefit.

The smallest useful next proposal is a paired coordinate-orientation diagnostic:
predeclare asymmetric cells and their transposes, including boundary/interior
locations, with mechanically distinct answers and source-group scoring. Build and
test it offline before proposing model calls. A same-information image comparison
remains a separate candidate, not something to bundle with coordinate hints,
memory, or planning changes. No follow-up run or policy promotion is authorized.

## Evidence, replay, and accounting

`phase4_grounding_v1_final_replay.json` retains the independent case/field scores,
task/game summaries, token counts, and per-call service latency. The twelve
diagnostic calls used 135,212 prompt tokens and 430 completion tokens; these totals
exclude the separately retained startup canary. Notebook elapsed time was
831.708596911 seconds, within the 1,680-second internal lifecycle cap.

`evidence/phase4-grounding-v1-r1-completed.zip` contains 32 files: downloaded
outputs and console log, provider observations, and approval/launch/reservation
receipts. Archive/member checksums are in
`phase4_grounding_v1_completed_archive.json`; original download checksums are in
`phase4_grounding_v1_download.json`.

Read-only reproduction with the project's Python 3.12 CPU environment:

```bash
python scripts/replay_phase4_grounding_v1_completed.py
```

This verifies frozen source bindings and archive members, reconstructs cases from
the committed source-observation archive, and replays in a temporary directory.
No ignored downloads, model weights, credentials, or GPU are required.

SDK-reported account usage increased from 3,883.525 to 4,724.817 seconds:
841.292 seconds. This is an account-level observation, not an attempt-specific
invoice. Raw duration strings remain malformed and allowance values disagree
with SDK conversion. Exact billed usage remains unknown. Provider-reserved time
is now zero; the local 1,800-second reservation remains consumed and unchanged.
Unused nominal time grants no further authority.

The transient experiment stays closed with no demonstrated benefit. Production
one-scorecard/110-distinct-game certification, workload-specific admission limits,
and exact accounting remain open. This diagnostic does not complete Phase 4.
