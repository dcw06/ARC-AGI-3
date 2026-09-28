# Evidence comprehension v2: post-approval dispositions (append-only)

Decisions, observations and corrections recorded after package r1 (lock `de9642c6…82a3`) was approved. Frozen
review documents are never edited after freezing; later dispositions are appended here instead, each dated.
Existing entries are not changed. A correction is made by appending an entry that names the entry it corrects.

---

## 1. 2026-09-28 — approval scope and unaccepted residual risk

- **Approval:** source approval and compute authorization for lock `de9642c6…82a3` record the user's response
  verbatim: "Now you can launch a new GPU run".
- **Residual risk:** the `late_abort` rehearsal test's dependence on the host not pausing, inherited from v1,
  was **not** accepted for v2. The approval did not address it.

## 2. 2026-09-28 — a hash-bound review document drifted after approval, and was restored

- **What happened.** `scripts/derive_evidence_comprehension_v2.py` is one of the review documents bound by the
  r1 lock (SHA-256 `359c87a5…5e58`). After the launch, commit `19fc928` extended it to also generate the post-run
  archive script. That broke its bound hash.
- **Scope.** All 265 runtime bindings and the other 22 review documents stayed unchanged. The edit was made
  after the launch, so it did not affect what ran. The live result is unaffected: the archive replays exactly.
- **Correction.**
  - The script is restored byte-for-byte to its approved content, from commit `1198f97`.
  - The archive derivation now lives in a separate script, `scripts/derive_evidence_comprehension_v2_postrun.py`,
    which imports the frozen renames without changing them.
  - The regenerated `scripts/archive_evidence_comprehension_v2_live.py` differs from the version that built the
    archive only in its first comment line, which now names the post-run derivation. The archive does not
    include that script, and its replay still verifies.
- **Regression.** `tests/test_evidence_comprehension_v2_postrun.py` checks every binding and review document
  against the approved lock, and checks that the post-run derivation reproduces its file.
- **Reported by** the review of `5bb1b02`.

## 3. 2026-09-28 — causal wording in the results report corrected

- The results report (`reports/evidence_comprehension_v2_results.md`, not a frozen document) said the remaining
  control errors showed "the history still wins", and attributed them to history salience overriding the rule.
- The experiment establishes only an association: all 14 remaining errors have ACTION6 in the history while it
  is not legal. The report now says this is consistent with history interference, and that testing it needs a
  matched comparison that removes or alters ACTION6 in the history.
- **Reported by** the review of `5bb1b02`.
