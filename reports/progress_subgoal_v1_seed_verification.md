# progress_subgoal_v1 evaluation seed: retention and verification status

Recorded October 9, 2026. The seed is not in this file or anywhere in the repository. The repository holds only its
SHA-256 (`ca1e518c…02aa`, in `research/progress_subgoal_v1/evaluation_seed.json`) and the hash of the question set
built from it (`f93ec44b…e02c`). The machine-readable record is `progress_subgoal_v1_seed_verification.json`.

**Owner rule.** Two-holder retention counts as confirmed only after both holders have each run the check below
independently and successfully. Until then it is not confirmed.

## Actual situation

| Item | Status |
|---|---|
| Copies known | **One.** It was written once on October 2 on the drawing machine, to a git-ignored file in that machine's working copy, and was never committed. (`evaluation_seed.json` says "outside the repository": the file is outside version control, but inside the working folder.) |
| Second copy | None known. Nothing records that the value was passed to a second holder. |
| Holder checks | **0 of 2.** |
| Check on October 3 | A check script ran on the same copy. Its output was not retained. |
| Check on October 9 | The retained copy was checked in a fresh, network-isolated clone of `track4-successor-runtime-v1` at `bd65f09`. It printed `question set matches a fresh build: f93ec44b…e02c`. This shows the copy reproduces the frozen set. It is **not** a holder's independent check. |

**Risk while only one copy exists.** The run reads the committed `probes.json`, so it does not need the seed. The
seed is needed only to re-derive that file independently. If the single copy were lost, nobody could re-derive the
frozen set, and the retention gate could not be met.

## What each holder does

1. Receive the value through a private channel, never through this repository or any shared document.
2. In a clean checkout of `track4-successor-runtime-v1`, run:

   ```
   python scripts/build_progress_subgoal_v1.py --check --seed-file <path to that holder's copy>
   ```

   The script refuses any value whose SHA-256 differs from the committed hash. It must print:

   ```
   question set matches a fresh build: f93ec44bab00453147e8e7e555704b60edc8220e6b5677b89d199ce8fca5e02c
   ```

3. Report the holder (name or role), the date, the commit checked and the printed line. Confirm that you ran the
   check yourself on your own copy, and that you keep the copy outside any repository. Never report the seed.

Each report is added to `holder_checks` in the JSON record. Two-holder retention is confirmed when both entries are
present and both show the expected hash.

The fields of each entry are in the JSON record (`holder_check_entry`). The authorized Track 4 attempt cannot be
reserved or launched until this record holds two such entries from distinct holders and is committed.

## Amendment of October 9, 2026: one holder, two copies

For the authorized Track 4 attempt the owner amended the rule:
- **Rule:** one holder, the owner, keeps **two separately stored copies** outside any repository and personally runs
  the check on each copy.
- **When:** both copy checks are recorded in `copy_checks` (JSON record) before any reservation or launch.
- **Limitation:** the copies are redundant storage, but there is no independent second holder. The owner is a single
  point of failure, and the two checks are not independent verifications.

The copy kept in the drawing machine's working folder does not count, because it is inside a repository folder.

For each copy, report:
- a copy label, such as "copy A" or "copy B";
- the date;
- the commit checked;
- the printed line;
- confirmation that you ran the check yourself, that the copy is outside any repository, and that it is stored
  separately from the other copy.

## Recorded under the amended rule (October 9, 2026, 20:48 UTC)

The owner personally ran the check on both copies, in a fresh clone at `2a80579`. The files the check reads there are
unchanged from the frozen package. Both checks printed
`question set matches a fresh build: f93ec44bab00453147e8e7e555704b60edc8220e6b5677b89d199ce8fca5e02c`.

| Copy | Storage | Outside any repository |
|---|---|---|
| A | Windows filesystem of the owner's computer | yes (verified without reading the seed) |
| B | WSL (ext4) filesystem of the same computer | yes (verified without reading the seed) |

**Status: confirmed under the amended rule (2 of 2 copies).** Limitation: both copies are on one computer, so they
do not protect against losing it. The assistant-run checks in `progress_subgoal_v1_assistant_copy_checks.*` are
supplementary and not counted.
