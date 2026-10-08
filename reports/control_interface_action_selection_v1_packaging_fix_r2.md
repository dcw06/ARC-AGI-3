# Paired observation probe: verifier-input packaging fix, review r2

The embedded notebook omitted `certification/direct_publisher_smoke_v1/proposal.json`.
The reused wheel verifier loads this file by default alongside its trusted
manifest and hash-pinned requirements. Without it, bundle integrity fails with
`FileNotFoundError` before installation or model requests.

The derivation now includes that unchanged shared proposal in the notebook
payload and requires its hash binding at the source gate. The experiment's
protocol, cases, token audit, request schedule, runtime inputs and controller
logic remain unchanged. No installation workaround or verification bypass is
introduced.

The prior CPU rehearsals supplied fixture verification inputs, bypassing the
default shared-package path. GPU-disabled review runs also stop at the live
gate before bundle verification. Two additional regressions close this gap:

- Extract the actual notebook payload into an isolated directory and exercise
  default trusted-file loading and the real bundle contract, with no checkout
  fallback. Only mounted-wheel hashing is replaced by a CPU sentinel.
- Require the source gate to reject a lock without the shared proposal binding.

Both fail against source `47329b9`; the retained [baseline test record](control_interface_action_selection_v1/packaging_47329b9_regressions.json)
contains two failures and no errors. The frozen r1 notebook also retains a
[direct extracted-payload reproduction](control_interface_action_selection_v1/packaging_47329b9_reproduction.json).

After the fix, [122 Linux CPU checks](control_interface_action_selection_v1/packaging_fix_r2_cpu_checks.json)
pass with no failures, errors or skips. The new public r2 package reproduces
byte for byte; the historical smoke r10 still reproduces. Its
[extracted verifier-input check](control_interface_action_selection_v1/packaging_fix_r2_extracted_inputs.json)
loads all 174 trusted artifact records and 174 pins. The
[GPU-disabled review check](control_interface_action_selection_review_check_r2.json)
refuses at the live gate before installation, GPU queries or model use, with
no temporary files left behind. The generated sources pass the derivation check.

Public r2 review-lock SHA256:
`1fe36d03ee517f17e8581b9a69515815c6731514c2367aac27c302c1b111c35f`.

Historical r1 notebooks and CPU records are preserved. These are CPU packaging
checks, not evidence of GPU compatibility or model performance. They neither
verify mounted wheel bytes nor authorize compute. No provider submission or GPU
launch was made for this fix. Consumed attempts stay consumed; a resolved private
r2 package requires its own final approval and fresh reservation before launch.
