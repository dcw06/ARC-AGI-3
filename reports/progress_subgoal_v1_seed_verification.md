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

3. Report the holder (name or role), the date, the commit checked and the printed line. Never report the seed.

Each report is added to `holder_checks` in the JSON record. Two-holder retention is confirmed when both entries are
present and both show the expected hash.
