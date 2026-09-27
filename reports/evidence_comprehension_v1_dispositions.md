# Evidence comprehension v1: post-approval dispositions (append-only)

Decisions and observations recorded after package r3 (lock `fa425fd0…c051`) was frozen. Frozen
review documents are never edited after freezing; later dispositions are appended here instead, with
each entry dated. Existing entries are not changed. A correction is made by appending a new entry
that names the entry it corrects.

---

## 1. 2026-09-27T19:01:15Z — residual test-harness risk accepted

- **Decision:** the reviewer accepted the residual risk recorded as unresolved in the frozen
  investigation report: a host (VM) pause long enough to consume a call's bound before dispatch can
  make the `late_abort` rehearsal test fail, now with stop reason `deadline_expired`. This concerns
  the local test harness, not the live run.
- **Reviewer's response:** "Approve and authorize", given when approving package r3 for launch.
- **Record:** `reports/evidence_comprehension_v1_source_approval.json` (SHA-256 `002947cb…072c`),
  whose `user_response` records the acceptance.
- **Correction of process:** the acceptance was first written into the frozen investigation report
  in `5c72f2e`, which broke that document's r3 hash. That edit was reverted, restoring the document to
  the exact r3-locked content, and the disposition moved here. All 1,081 runtime bindings and the
  other 24 review documents had remained unchanged. The drift did not affect what ran.

## 2. 2026-09-27 — GPU accounting for attempt `ecv1-4458251e`

See the post-run provider record `reports/evidence_comprehension_v1_postrun_provider.json`.

- **Status:** exact provider-billed time is **unknown**. The provider does not report billed seconds
  per run.
- **Evidence:**
  - The prelaunch record showed `time_used` 0.0 s (after the weekly reset).
  - The post-run provider record retains the account counter observed after the run: 926.26 s at
    2026-09-27T20:11:58Z, with kernel status COMPLETE.
  - An earlier message reported "about 936 s", converted from the CLI's rounded 0.26 h. That figure
    was imprecise and is superseded by the retained 926.26 s.
  - The difference is an **account-counter observation**, not a billed amount. It would include any
    other GPU use on the account in that window, and the CLI displays it rounded (0.26 h).
- **Authorization:** the attempt is consumed. Authorization that went unused is **not** reusable:
  any further run needs a new, separate compute authorization.
