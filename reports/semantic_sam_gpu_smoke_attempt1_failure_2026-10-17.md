# Semantic-SAM GPU smoke attempt 1: accelerator mismatch

**Subsequent configuration finding:** the [RTX competition-binding repair](semantic_sam_rtx_competition_binding_fix_2026-10-17.md)
addresses an omitted ARC-AGI-3 attachment. Earlier RTX notebooks had this binding;
this failed notebook did not. The repair still requires visible-menu confirmation
and does not prove future hardware allocation. Attempt 1 remains consumed.

The first authorized attempt ended with provider status **ERROR**. Read-only
collection and a separate offline audit establish that the initial GPU identity
guard refused **two Tesla T4 devices**, before transport restoration or model
loading. The consumed attempt and all earlier records remain preserved. No new
GPU job, retry, notebook edit or cancellation was made during diagnosis.

| Evidence | Result |
|---|---|
| Actual saved source | Matches the authorized private r2 notebook |
| Saved requested machine shape | `NvidiaRtxPro6000` |
| Actual runtime `nvidia-smi` census | **Tesla T4, Tesla T4** |
| Failure stage | Initial GPU identity guard: `exactly one RTX PRO 6000 required; no fallback` |
| Measured worker duration before failure receipt | **0.065863 seconds**; this excludes provider setup/release |
| Transport restoration / runtime extraction | Not started |
| Checkpoint/model loading / segmentation inference | Not started |
| Model HTTP calls / MolmoPoint generations / game actions / scorecards | All zero |
| Owned child-process group | Registered, terminated/reaped, absence verified |
| GPU cleanup certification | Not established: no approved GPU identity was bound; the failed receipt explicitly says so |
| Completion witness / worker mask outputs | Absent |
| Submission count | One; authorization consumed; zero automatic retries |

The read-only collector retrieved the provider log, exact saved source, initial
GPU census and failed result receipt. Their retained hashes, source/attempt
bindings, census digest, failure stage and cleanup record pass an independent
offline audit. The absence of restoration and inference artifacts agrees with
the guard's position before those operations in the reviewed code.

The saved machine-shape label and available quota did not prove actual RTX PRO
6000 allocation. The precise cause of Kaggle's allocation mismatch is not yet
established. The runtime guard worked as intended; weakening it or permitting
T4 fallback would change the approved hardware scope and is not a remedy.

## Before any future attempt

Investigate the account/notebook's actual accelerator-selection route and the
outgoing provider configuration using read-only evidence, without a trial GPU
job. Establish why the requested shape did not match the allocated devices.
Any new submission requires a fresh authorization and single-use claim; this
failed attempt cannot be reused. The verified mounted CPU transport result and
local runtime preparation remain valid within their stated CPU-only scope.

Private identities, raw logs, approvals, reservation/claim and collected failure
receipts remain in the git-ignored operation directory. No segmentation accuracy
or CUDA model compatibility result follows from this failed attempt.
