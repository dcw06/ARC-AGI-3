# Semantic-SAM: bounded one-image GPU smoke package

**Attempt 1 outcome:** [failed at the accelerator guard](semantic_sam_gpu_smoke_attempt1_failure_2026-10-17.md).
Kaggle allocated two Tesla T4 devices; the runtime refused them before staging
or model loading. No CUDA inference result exists. The attempt is consumed and
preserved; no retry was launched.

**Launch update:** the owner-authorized final private r2 package was submitted
exactly once. The [submission record](semantic_sam_gpu_smoke_attempt1_status_2026-10-17.md)
reports RUNNING and verifies the saved source, immutable image, private/offline
settings and requested RTX PRO 6000. Actual CUDA/mask results remain pending.

The mounted CPU transport check passed. A separate one-image GPU wrapper now
packages the verified decoder, portable interpreter and existing reference-free
segmentation worker. This preparation report does not claim a CUDA result.

| Setting | Frozen scope |
|---|---|
| Accelerator | Exactly one RTX PRO 6000; no T4 or other fallback |
| Provider timeout | Requested session timeout 3,600 seconds |
| Worker lifecycle | 3,300 seconds, including staging, child cleanup, GPU census, environment removal and evidence finalization |
| Work admission | Ends at 3,000 seconds; 300 seconds reserved for cleanup/finalization |
| Attempts | One authorized submission, zero automatic retries |
| Image | sc25 / board-06, original plain 448 by 448 RGB; existing fixed 640 by 640 Semantic-SAM preprocessing |
| Conditions | Seeded and automatic, fixed granularity 1, separate fresh interpreters |
| Seeds | Original retained MolmoPoint points, unchanged |
| Automatic proposals | Fixed 16 by 16 grid, batches of 16, at most 96 selected by predicted quality |
| Model HTTP calls / new MolmoPoint generations | Zero / zero |
| Game actions / scorecards | Zero / zero |
| Access | Private, account-only; internet and TPU off |

Provider allocation, mounting, setup and GPU release can extend the whole job
beyond one hour under the previously accepted session/worker policy. The actual
GPU identity is checked before checkpoint loading; saved requested machine shape
alone is not allocation evidence.

## Lifecycle and payload

Both independently pinned manifests and every mounted part/original hash are
checked again. The runtime is extracted at its retained relocation prefix;
upstream source and inputs are staged separately. No package download/install is
performed. The worker verifies exact upstream source, checkpoint hash, environment
versions and seed-to-image binding before inference. Reference masks, owner answers
and scoring references never enter the model process.

Process ownership is registered before `Popen`, with startup signals deferred
through PID/group registration. Linux subreaper ownership allows scoped reaping
of grandchildren. Termination sends SIGKILL before inspecting the owned process
group; already verified-absent groups are retired and never signaled again.
Uncertain spawning cannot produce an absence receipt. The final alarm escapes
cleanup handling; an outer emergency path can signal known children without
starting a blocking census or wait. A cleanup or finalization overrun fails.

After both child conditions, owned groups and GPU compute-process absence are
verified. The extracted runtime, original checkpoint, source and staged inputs
are removed. Evidence hashing and result/witness/final marker remain inside the
worker deadline. Independent collection must also require provider COMPLETE,
exact saved source/settings and raw mask replay; a receipt alone is provisional.

## Local validation

- **120 connected Linux CPU tests passed**, with no failures, errors or skips.
  This includes 19 new wrapper/builder tests and the existing transport,
  granularity, scoring, input-binding and replay groups.
- Real child-process tests cover descendants, timeout, startup interruption,
  uncertainty before assignment, emergency kill before census and final expiry
  during a stalled census. Synthetic pipeline tests cover T4 refusal before
  staging and final receipt interruption without a completion witness.
- Two final private package builds are byte-identical. The notebook with an
  empty authority slot refuses before GPU queries, staging or subprocess use.
- The actual installed Kaggle SDK serialization passes 12 local request-guard
  checks. Empty attachment arrays are made explicit on the wire before exact
  validation; accelerator, privacy, sources, timeout and source cannot drift.
- An earlier local draft completed extraction and both non-inference planning
  paths, then its checkout-source check refused after a supervisor wiring update.
  The draft and its logs are preserved. Its result is not final-package
  certification; the corrected frozen snapshot gets its own local rehearsal.
- The corrected frozen r2 snapshot completed that fresh offline rehearsal in
  **166.296 seconds**: all transport/original hashes matched, safe runtime/source
  extraction and both planning paths passed, both child groups were reaped,
  temporary files were removed, and the final review/source lock still matched.
  No model load, inference, GPU or provider call occurred in that rehearsal.

Private locks, source/use/compute records, account bindings and provider evidence
remain git-ignored. The final submission record will name the exact consumed
package and one-use claim. No six-board comparison or automatic follow-up launch
is authorized by this one-image scope.
