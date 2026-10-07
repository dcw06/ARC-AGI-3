# Runner validation for da31405

Commit `da31405c7d60b24a4301a595f5ebc985939be744` was checked from a fresh, initially clean Linux checkout with `core.autocrlf=false`. The focused suite passed **49/49 tests**, with no errors, failures or skips. `fresh_checkout_checks.json` records every test and its outcome/duration; its adjacent log records the unittest output.

The frozen `profile.ipynb`, `kernel-metadata.json` and `review-source-lock.json` reproduced byte for byte. The embedded review notebook stopped at the live gate, made no GPU query and left no temporary source files. Its GPU/TPU/internet settings remain disabled.

All **12/12 integration rehearsals** behaved as expected in that checkout. The nominal case issued 11 counted requests. Integrity mismatches, version/model mismatches, early server exit, startup/request timeouts, wrong served model and non-idle cancellation failed at their expected stages. SIGTERM-resistant parent/child scenarios required SIGKILL and verified process-group absence. The retained nominal evidence manifest matches its result/log files.

The focused suite includes both original reproductions (interrupt before process assignment and cleanup overrun), interruption before group registration, unknown ownership, emergency termination after a deadline, GPU/evidence/environment cleanup overruns, failed or late final publication, actual temporary-source removal, scoped account/use/byte evidence, exact compute limits, once-only launch accounting and flat-mount hash-pinned installation. All evidence is from scripted CPU fixtures; it does not establish real wheel-byte integrity, account attachment, use permission or GPU/model compatibility.

The updated rehearsal report and review-refusal receipt name or bind this tested source revision/snapshot. The authoritative redistribution decisions remain unchanged, SHA-256 `4a07339315f220b099c1489a0d15e7fe9f2d2eace1fd15123c593d5ae8ccd3ce`. No real evidence/approval/reservation sidecars were created, no provider was contacted, and no GPU job was launched.
