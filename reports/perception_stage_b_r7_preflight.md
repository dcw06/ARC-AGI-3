# Stage B R7 preflight before any further GPU attempt

**Disposition:** the R7 source is locally reviewed and the known R3
game-bootstrap blocker has a tested repair. No R4-source approval,
compute authorization, reservation, GPU-enabled package, or upload exists.
R3's attempt remains consumed. This review does not itself authorize a run.

## R3 evidence and narrow repair

The independently replayed R3 archive shows a successful target split
install (129.362 seconds; isolated game/model interpreters; torch
2.10.0+cu128), pinned model readiness in 629.707 seconds, and a passed
startup canary. The first game bootstrap then selected
`module://matplotlib_inline.backend_inline` and failed before a study call
or action. R3 independently verified process-group and GPU cleanup.

R7 forces `MPLBACKEND=Agg` only in the game-supervisor subprocess
environment. The supervisor's worker and monitor environments inherit that
value; their monitored scratch still receives `MPLCONFIGDIR`. A CPU
regression deliberately sets the parent notebook backend to the failing
value, checks the child environment, and bootstraps and closes the actual
offline `ar25` game. Another connected-supervisor regression checks the
headless setting reaches its worker and monitor launches. The model,
requests, case, two-arm horizon, and scoring rules are unchanged. Comparing
R6 and R7 source locks found exactly two changed bindings: the first-cell
launcher and the new authority namespace.

## Lifecycle, evidence, and limits

- The R3 provider output contained 27 files; all hashes and byte counts
  passed. Its incomplete trajectory was rejected by independent replay.
  The startup canary passed token parity, finish reason, action validation,
  and response-hash checks. Monitoring retained 2,383 samples; independent
  cleanup recorded zero remaining GPU PIDs. R7 does not weaken these gates.
- The existing authorization gate rejects absent, mismatched, or consumed
  approvals before installation or GPU access. R7 uses new `live-r4`
  source/compute, execution, reservation, and launch paths. The historical
  R3 records cannot authorize it.
- The proposed unchanged ceiling is one 3,600-second provider attempt,
  3,300-second internal limit, 3,000-second admission cutoff, two episodes,
  at most two actions per episode, 12 study completions plus one canary,
  and no retry or scored submission. R3 reached the failed bootstrap at
  about 765 seconds, leaving roughly 2,235 seconds before admission cutoff.
  That is timing headroom, not a completion guarantee.
- The pinned-tokenizer audit's largest normal exact request is 25,798
  prompt tokens. Its six-frame feedback stress request is 59,569 tokens,
  only 431 below the 60,000-token per-call cap. Denser real frames could
  exceed that cap; live admission retokenizes and stops before transport.
  This remains a possible censored outcome, not grounds to broaden the
  protocol during this environment-only repair.

## Local verification and remaining gates

All **56** Stage B CPU tests passed, including authority/package rejection,
first-cell import isolation, real offline-game bootstrap, scripted lifecycle
failure paths, and independent replay. Two focused propagation/bootstrap
tests passed again after strengthening their environment assertions. The
GPU-disabled R7 notebook was unpacked and independently reviewed: **1,043**
source bindings verified, unapproved execution rejected. Review lock
SHA-256:
`5e2e74c64fe828092c4402ea7ccf52a30380cadfc76819907ecf257850be1da9`.
`git diff --check` passed.

The actual Kaggle game bootstrap after this repair is still unverified;
the CPU test uses the pinned local development game assets. A future live
run may produce a valid incorrect model response, token-budget rejection,
or another target-only failure; those outcomes must be retained and
evaluated, not retried automatically. Exact provider billing remains open;
the R3 quota increase of 774.953 seconds was account-wide, not exact
per-attempt billing. A successful exploratory comparison would not satisfy
Phase 4 production certification.

Before any new submission, obtain explicit R7 source approval and a
separate one-attempt compute authorization, reserve fresh capacity, verify
the exact GPU-enabled package and current provider quota, and upload once.
