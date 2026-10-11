# Track 1: interrupted finalization repair

The remaining `afc34ca` finalization finding is repaired in the derivation and generated launcher/evaluator.
This is a CPU-verified successor review package, with no GPU launch, Kaggle upload, approval or reservation.

| Change | Result |
| --- | --- |
| Durable pending barrier | A success receipt remains provisional while `control/finalization-pending.json` exists. The barrier is created before certification and removed only after the write and deadline check succeed. |
| Interruption protection | Handled shutdown signals are deferred through certification; their replay and direct exceptions are caught. Interrupted certification invalidates the saved receipt before emergency failure recording. |
| Storage failure | A failed emergency write leaves a pending barrier or no cost receipt, preventing completion. |
| Deadline accounting | Evidence writes, source removal and barrier removal are charged. An overrun fails, while emergency failure recording remains possible. |
| Independent evaluator | Requires the guarded receipt version and refuses a pending barrier, uncertified lifecycle or failed receipt. Such evidence cannot permit session 2. |

## Regression proof and verification

A separate `git archive afc34ca` received only the final new regression file. All six methods fail there,
with zero errors or skips. Its connected fixture first verifies technically complete scripted CPU evidence,
then reproduces the interrupted write at 420.1 seconds against a 420-second ceiling: the old evaluator accepts it.
The baseline archive/test hashes and failure records are retained in `finalization_baseline_afc34ca.json` and
`cpu_checks_finalization-afc34ca-final-regressions.{json,log}`.

| Current verification | Result |
| --- | --- |
| Six finalization regressions, four real-child startup faults, two existing deadline checks | 12 passed |
| Successor checks, review locks, retained snapshot history and unchanged science | 34 passed |
| Pinned model-interpreter HTTP path, tokenizer and grammar (24 forms) | 1 passed |
| Exact extracted r8 notebook, connected scripted CPU rehearsal | Technically complete; no lifecycle errors; extracted source removed |
| Public r8 and private r9 review checks | Refused before GPU activity; no temporary files left |
| Private launch packaging | Refused missing source approval |
| Both derivation checks | Match; eight verbatim controller files unchanged |

There are **47 distinct passing checks, zero failures/errors/skips**. External networking was disabled and GPUs
hidden for the Linux runs. These are scripted CPU checks, not target-model performance or GPU allocation evidence.
The previous full 200-test suite was not rerun; this follow-up covers the changed finalization path, independent
evaluation, Linux startup faults, rebuilt snapshot and pinned interpreter path. Exact receipts and source hashes
are in `finalization_verification_r8.json`.

## Successor snapshots and authority

| Snapshot | Review-lock SHA-256 |
| --- | --- |
| Public r8 | `8e4cd19b68faa852db4570541e3a55944484d4f8203b49b0aa81dc4bbb8a7c2d` |
| Private r9 | `3bac65029913b6bcd22661642536906274ef1846e563969b4b9df20db4847811` |

Public r1-r7 and the earlier private copies remain unchanged. The scientific design and frozen protocol/A1
remain unchanged (protocol SHA-256 `c489bdc68e5e557def4183c5f0a963d827090f0f54e2e8c5ca41d59b7c14935c`).

The private successor and handoff are under the git-ignored `.cache/github-review/track1-finalization-interruption/`.
Only the existing runtime bindings differ from public r8; review documents are identical, and the private snapshot
rebuilds byte for byte. Its immutable image and version-pinned attachments match the bound runtime locally.
The 23 retained licence texts are hash-verified; permission and reuse records remain unapproved drafts.

No source approval, compute authorization, execution lock, reservation, launch claim or submission receipt was
carried forward. The original failed attempt stays consumed and preserved; A1's single replacement permission
is unchanged, and session 2 remains unauthorized. Before launch, review the exact private package and scope
evidence, obtain fresh lock-bound approvals and a single-use reservation/claim, then perform current provider
attachment and accelerator checks. This repair authorizes no compute or additional attempts.
