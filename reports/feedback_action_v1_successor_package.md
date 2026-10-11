# Feedback-action v1 successor package (runtime v1): review guide

**Protocol of record:** `reports/feedback_action_v1_protocol_v2_frozen.md` (frozen October 10, 2026: gate A
`ascii_only`, gate B `denominator_floor_10`). Review snapshots r2 bind it, the owner-gate record and the review
documents (frozen protocol §15). r3 added the review's P2 evaluator fix; r4 the installation fix after session 1's
first attempt (`MPLBACKEND=Agg`); r5 owner amendment A1 (one replacement session-1 attempt); r6 anchors the source
inventory to the reviewed notebook and rejects missing repository modules (the review's second P2). Use the newest
revision: a superseded revision's review check fails on source drift by design.
r1 to r5 stay unchanged as history.

**Status:**
- GPU-disabled review package for one feedback-action v1 session on the verified runtime;
- no approval, compute authorization, reservation, launch claim, upload or submission exists;
- the live path refuses in this checkout.

## What the notebook does when (and only when) every gate holds

1. The first cell extracts the embedded sources and verifies them by hash. It needs:
   - 112 files: the static import closure of the first cell, the game interpreter and the model interpreter;
   - the data files they read.
2. **Gate.** `binding.require_live` runs before installation, any subprocess, model or GPU use. It requires:
   - no `REPLACE_WITH_` placeholder;
   - the newest review lock binding every embedded file;
   - separate source and compute approvals bound to that lock, to `runtime.json`, to `protocol.json` and to
     `owner_gates.json`;
   - account-attachment, direct-use permission and mounted-byte receipts for `driessmit1/arc3-vllm-h100-wheelhouse-v3`
     version 1;
   - an unconsumed one-session reservation, with session 2 binding session 1's independent evaluation;
   - the launch claim.

   The attempt is then marked consumed in the provider working directory (exclusive create).
3. **Host facts:** CPython 3.12, x86_64, glibc ≥ 2.34.
4. **Mounts:**
   - the publisher wheel mount (verified flat inventory, 174 wheels and 3 metadata files);
   - the competition mount (one of two layouts).

   The three development games are staged by manifest hash.
5. **Interpreter pair**, within 900 s of the first cell, every command in an owned process group:
   - **model:** hash-pinned offline install of the trusted lock;
   - **game:** the 31 competition wheels by manifest hash, then a hash-pinned offline install of the game lock;
   - **both:** `pip check`, exact versions, the import closure of each interpreter.

   The trees are then made read-only.
6. **Supervisor** (game interpreter). It owns the worker and monitor groups. The monitor binds exactly one GPU named
   `RTX PRO 6000` and samples it. Once the monitor is ready, the worker is released.
7. **Worker:**
   - starts the model host (model interpreter);
   - the host verifies the snapshot tree `b480ad92…`;
   - the host starts vLLM in its own process group with the verified argv (prefix caching off, confirmed in the
     server log) and records the group;
   - the host runs the one canary and serves the bounded bridge;
   - the worker then runs one session (6 episodes) on the offline engine.
8. **Cleanup:**
   - the host stops the server group;
   - the supervisor stops the worker and monitor groups, and the server group if it is still recorded;
   - an independent GPU check confirms nothing remains;
   - the first cell stops every recorded group;
   - evidence is finalized.

## Review commands (CPU; WSL Ubuntu, CPython 3.12)

```bash
python -m research.feedback_action_v1.derive --check            # harness derived from AEH v1
python -m research.feedback_action_v1.derive_runtime --check    # gate/notebook/launch from the verified runtime; verbatim controller
python scripts/feedback_action_v1_package.py review-check --revision 6     # must refuse at the live gate
python scripts/feedback_action_v1_package.py review-rehearse --revision 6  # the same cell, MODE switched: one connected session
python scripts/feedback_action_v1_package.py launch-build                  # must refuse
python scripts/check_feedback_action_v1_runtime.py --bundle <replica flat mount> --competition <replica competition mount> --work <new dir>
python -m unittest tests.test_feedback_action_v1_successor tests.test_feedback_action_v1_live_evaluation tests.test_feedback_action_v1_connected
```

## Review documents (r2)

Every review lock binds the frozen protocol text, the independent evaluator's files outside the payload, the
derivations, this package script and the structured-output check with its receipt (frozen protocol §15). The
review check, the launch tooling, `launch-build` and the live independent evaluation verify them; only the gate
inside the runtime payload skips them, because the payload never carries them.

## What the guards cannot prevent

These limits are the same as the verified runtime's.
- The consumed marker lives in the provider session's working directory. It cannot see other provider sessions.
- Durable once-only accounting is the launch-side claim, created exclusively before packaging, and the receipt,
  created as `submitting` before the push.
- An uncertain submission is reconciled by hand against the provider's version history. It is never relaunched.
- A new attempt needs a new authorization and reservation.

## What remains outside this package

- the private bindings (consuming account, model dataset reference and mount path), resolved in a private checkout
  with a successor review snapshot;
- the owner gates: decided October 10, 2026 (`reports/feedback_action_v1_owner_gates.md`);
- the use and attachment evidence for this scope;
- review, source approval, compute authorization and one reservation per session;
- everything GPU-side:
  - model load;
  - guided decoding of the candidate schema during generation (request validation and grammar enforcement are
    verified on CPU, `reports/feedback_action_v1/structured_outputs_check_r2.json`);
  - the competition mount layout on the pinned image;
  - cleanup on the target.
