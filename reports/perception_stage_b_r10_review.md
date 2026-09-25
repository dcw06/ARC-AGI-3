# Stage B R10 prediction-output contract review

**Historical review snapshot.** R10 was subsequently approved and packaged
for the consumed R7 attempt. Its prelaunch statements below describe the
state at review time; the final R7 disposition is in
`reports/perception_stage_b_r7_failure.md`. The R11 successor preserves this
review lock unchanged.

**Status:** R10 is a GPU-disabled review revision. The consumed R6 GPU
reservation remains consumed. There is no R7-scope source approval,
compute authorization, reservation, GPU-enabled package, or upload.

The R6 attempt reached model readiness and a passed canary, then stopped
before its first game action because the model returned both prediction
fields as `no_change`. The response was retained correctly; strict
validation correctly rejected the duplicate alternatives. The [R6
disposition](perception_stage_b_r6_failure.md) and checksummed archive
preserve that failure.

R10 removes only the redundant field from the **sealed prediction model
output**. The model now returns one enum value, `change` or `no_change`.
The runner validates that exact one-field JSON object, then derives the
opposite value mechanically for the committed prediction and later
feedback audit. Missing, extra, malformed, duplicate-key, non-stop, and
token-mismatched responses still fail closed before any action dispatch.
A valid but incorrect prediction remains a scored outcome. The policy
request, case, arms, action horizon, feedback-grid representation, model,
decoding settings, and no-retry rule are unchanged. This is an output
contract repair, not a demonstrated improvement in gameplay.

New trajectories identify themselves as `grounded_action_local_v3`.
Independent replay reconstructs the one-field schema for v3 and keeps
the original two-field schema for historical v1/v2 evidence. The consumed
R6 archive still replays as `verified_prediction_contract_failure`; the
older CPU archive remains on its original protocol. Comparing R9 and R10
notebook source locks found four changed bindings: `authority.py`,
`contract.py`, `local.py`, and `replay.py`.

The pinned Python 3.12 tokenizer audit is
`reports/perception_stage_b_r10_token_audit.json` (SHA-256
`cad9044b0244898362eee6c7d75bacb4d2d23dda3ac8ece20dd95f6c0486e104`).
All 12 exact scripted requests fit; the maximum prompt is **25,799**
tokens. Repeated eight-frame feedback stress reaches **36,207** tokens
against the 60,000 ceiling. The one-field prediction response uses 7
tokens plus end in compact JSON and 11 in pretty JSON, under the 128-token
completion cap. Live admission still re-tokenizes every request and
rejects any context/byte limit violation before transport. No GPU or
model call was used for this audit.

The private, Internet-disabled R10 review notebook is GPU-disabled. An
independent unpacking verified **1,043** source bindings and rejected
unapproved execution. Review-lock SHA-256:
`0b255babdcfd25d293342dc405cdbe154c5e7f8b6dc83988c630fe09792d82cd`.
The new `live-r7` authority scope points to fresh approval and one-use
reservation files; old authority cannot launch this source.

The full CPU Stage B suite passed **59 tests** on rerun. A first full-suite
invocation had one failure in the local supervisor rehearsal: its monitor
exited during concurrent test execution. The same persistent-output
rehearsal and its three supervisor tests passed separately, followed by
the clean 59-test rerun. The cause of that first local failure was not
isolated; it did not occur in the R6 target monitor evidence. This remains
a local reliability observation, not proof of target readiness. The
consumed R6 archive replays unchanged, and `git diff --check` passes.

The actual target model's response to the new one-field constrained schema
is not yet observed. R10 still needs explicit source approval and separate
one-attempt compute authorization before reserving or uploading anything.
A future successful exploratory pair would not complete Phase 4 production
certification or resolve exact provider billing.
