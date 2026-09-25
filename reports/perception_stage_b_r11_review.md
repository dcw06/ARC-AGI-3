# Stage B R11 frame-bound feedback review

**Status: reviewed GPU-disabled source; R8 reserved and packaged, not
launched.** The R7 reservation remains consumed. The R8 source approval,
compute authorization, execution lock, one-use reservation and exact local
launch package were subsequently recorded under attempt
`gab1-2b4f10a6f6b949aaa26aa457b9f56272`. No R8 upload or GPU run has
occurred. The historical R10 review notebook and R7 evidence archive remain
unchanged.

R7 reached one real control action, then the model returned
`{"assessment":"contradicted","changed_frames":[1,2,3,4,5,6,7,1]}` for a
single returned frame. Strict validation stopped the study. This is a
structural feedback failure, not a completed control/target comparison.

R11 uses `frame_flags_v2` for sealed feedback: a request with N returned
frames requires exactly `assessment` and Boolean fields
`frame_0_changed` through `frame_{N-1}_changed`, with N in 1..8. No array
or extra field is admitted. The runner derives the index list after strict
JSON validation and retains the raw bounded response before validation.
An inaccurate but structurally valid Boolean answer is scored as wrong by
independent replay; it does not fail the protocol. Prediction output,
policy prompts, model, case, arms, two-action horizon, and no-retry behavior
are unchanged. Sealed feedback still does not enter later policy requests.

New trajectories use `grounded_action_local_v4`. Replay selects the new
feedback contract only for v4; v1/v2/v3 keep their original index-list
contracts and request text. A complete synthetic v3 pair, both archived
R6/R7 failures, and the historical R10 notebook all verified under this
checkout. The R7-style response is retained and rejected in a scripted
regression. Cases cover valid and invalid responses for every frame count
from one through eight, as well as correct and incorrect change judgments.

The pinned tokenizer audit at
`reports/perception_stage_b_r11_token_audit.json` has SHA-256
`2673c46ceadbe75787a800bec256568d82480743e36e7d8188d2db0ce025927e`.
All 12 exact scripted requests fit; maximum exact prompt length is **25,799**
tokens. The maximum eight-frame stress request is **36,226** tokens under
the 60,000 prompt ceiling. The largest audited response example is **84**
tokens including end under the 128-token completion cap. Every live request
still requires tokenizer/server parity and context admission. No model or
GPU calls were made for this audit.

The full CPU Stage B suite passed **62 tests**. The R11 notebook is private,
Internet-disabled, and GPU-disabled. Independent unpacking checked **1,043**
source bindings and confirmed that execution without approval stops before
installation. Its review-lock SHA-256 is
`e7be0ab939c33aefb0a211a6159f9ed244d74c18ff6c5846028fa8f874e51bef`.
The R8 authority scope and one-use package gate reject missing, mismatched,
or consumed approvals/reservations in local tests.

This is a protocol repair, not evidence of improved gameplay. The user
approved the R11 source bound to this lock and separately authorized one
3,600-second provider attempt with a 3,300-second internal limit, at most
12 study calls plus one canary, and no automatic retry. The R8 reservation
is **reserved, not consumed**. The launch package passed local verification;
no provider quota check or upload was made. No R7 retry is permitted.
