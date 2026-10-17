# Semantic transport CPU check: separate work and final alarms

**Subsequent CPU operation:** after the fix and owner approval, the first r2
CPU-only attempt was submitted once. Its [operation status](semantic_transport_cpu_attempt1_status_2026-10-17.md)
supersedes the pre-approval status below. Fix validation itself made no provider
call; GPU inference remains pending.

The cleanup deadline finding on `8d25d65` is reproduced and fixed. No Kaggle
call, upload, notebook job, GPU job, reservation or launch was made. All earlier
proposals, local evidence and provider attempts remain preserved.

## Reproduction and fix

The original one-shot lifecycle alarm could expire during restoration, be
caught as an ordinary work error, and leave cleanup without an active timer.
Its cleanup exception handler could also swallow an alarm before starting an
unbounded failure-receipt write.

Three isolated Linux reproductions were run before changing the runtime. With
a shortened 0.18-second worker limit:

| Path | Original runtime | Fixed runtime |
|---|---|---|
| Restoration stalls, then cleanup stalls | Cleanup timer absent; returned after 1.181 s including a stalled failure writer | Cleanup timer has 0.100 s remaining; final exception escapes at 0.181 s |
| Work fails early, then cleanup stalls | Alarm swallowed in cleanup; failure writer entered; returned after 0.681 s | Final exception escapes at 0.182 s; no writer entered |
| Work fails, then failure-evidence write stalls | Ordinary timeout at 0.181 s | Explicit final exception escapes at 0.181 s |

The real work alarm now ends restoration at 980 seconds and arms the remaining
absolute 1,100-second lifecycle deadline **before** raising a recoverable work
timeout. Early work errors and normal completion also switch to that same final
deadline; switching phases never grants additional time. The final alarm stays
active through temporary-file removal, evidence writes and the final marker.

`LifecycleDeadline` is explicitly re-raised by both work and cleanup handlers.
The cleanup sequence is outside a work `finally` block, so hitting the final
deadline during work cannot start another cleanup operation. Once that deadline
is reached, no new failure-receipt write is attempted. Incomplete originals may
remain in the failed notebook's disposable session; this is not a successful
cleanup claim. Passing still requires exact provider COMPLETE, saved-source and
attachment verification plus the matching result, witness and final cell marker.

## Validation and package status

- **101 Linux CPU tests passed**, zero failures, errors or skips. Four real-alarm
  regressions cover work timeout followed by stalled cleanup, an early failure
  followed by stalled cleanup, a stalled evidence write, and final expiry during
  work without starting cleanup. Child processes have their own outer test
  timeout, so a broken deadline cannot hang the test runner indefinitely.
- The existing cleanup-overrun regression now requires no receipt after final
  expiry. Existing provisional-result and marker checks remain in place.
- The final builder's five tests passed after updating the review wording.
- Private CPU review **r2** and its independent rebuild are byte-identical and
  refuse missing authority. Both bind the fixed source. The r1 proposal is
  preserved and superseded; its lock cannot authorize the changed runtime.
- The exact r2 packet also completed a full local Linux rehearsal in **123.799
  seconds** with the two-stage alarm active: all 21 actual transport files and
  12 reconstructed originals matched, temporary originals were removed, and
  the final receipt/witness/marker were checked. Authority was explicitly a
  synthetic local fixture, not a real owner approval or provider reservation.

The proposed CPU scope is unchanged: private, account-only; GPU, TPU and
internet off; requested session timeout 1,200 seconds; worker 1,100 seconds,
including 120 seconds reserved for cleanup; one attempt, zero automatic retries;
zero installs, model loads/forward passes, game actions or scorecards. The CPU
job has not been approved or submitted. Semantic-SAM CUDA inference remains
pending, as does review and authorization of its separate final GPU package.

Private receipts retain the baseline measurements, fixed measurements, test log,
exact package locks and local restoration evidence. No model files, input images,
private account bindings, credentials or authority records are published here.
