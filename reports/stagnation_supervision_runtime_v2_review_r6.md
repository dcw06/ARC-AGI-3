# Track 3 runtime v2: package r6 for independent review (sanitized)

**Status.** This is a GPU-disabled review record. It authorises nothing. Both session-1 attempts are consumed and no
further attempt is authorized. The repairs answer the independent review of `b80b75c`; the detail is in
`reports/stagnation_supervision_runtime_v2_attempt2_repairs_r6.md`.

| Item | Value |
|---|---|
| Repairs | `2e4d54c` |
| Public review snapshot r6 | `notebooks/stagnation-supervision-v1-runtime-v2-review-r6/`, lock `aebf220f513cb3708d729147595b2dfc2736fa264b722cf66fdba6e2ecc15f2e`: 154 embedded bindings, 178 review documents, four private placeholders unresolved, GPU disabled |
| Private review snapshot r9 | lock `11983a949a38b69c8cd887562e2ad6a0c1bf06aa694ec82b2064dd04d2241687`; differs from public r6 only in the runtime protocol's four private bindings (unchanged from both attempts) |

## Fresh Linux verification of this revision (CPU; scripted model; injected GPU; not target evidence)

| Check | Result |
|---|---|
| CPU suite r10 (`..._local_checks_r10.json`, CPython 3.12.3) | 293 tests (160 historical, 133 runtime v2, including the r6 regressions and the connected fault matrix), 0 failures, errors or skips; all seven receipt checks pass, including the runtime diff r6; `--check` binds the committed tree |
| Derivation | 16 derived files match; 14 invert to their sources |
| Public review check r6 | passed: bindings verified, embedded files compiled, live refusal at the gate before any GPU use, embedded-cell rehearsal technically complete, no leaked source |
| Private review check r9 | passed: no unresolved bindings; live refusal at the gate before any GPU use; embedded-cell rehearsal technically complete |
| Staged interpreters (from the extracted r6 payload) | both trusted-lock installs passed (183 s) |
| Staged session 1 (15 episodes at 40 actions) | technically complete with the lifecycle verified; first cell 319 s (installation 159 s); finalization certified, source removed; the `/proc` RSS probe ran on real processes throughout |
| Staged session 2 (12 episodes at 40 actions) | technically complete with the lifecycle verified; first cell 299 s (installation 156 s) |
| Final launch notebook of r9 (built in a temporary copy with synthetic authority) | session-1 kernel, private, GPU on `NvidiaRtxPro6000`, TPU and internet off, exactly the wheel and model datasets and the competition, no model sources, the pinned image, session 1, live mode, 568,433 bytes, bound to lock r9 |

## Provider reconciliation (read-only, October 12, 03:23 UTC)

| Notebook version | Content | Final status |
|---|---|---|
| 1 | GPU-off Quick Save (account-attachment evidence) | rendering only |
| 2 | attempt 1, `ssv1rt2-s1-c5ebca7f…` | ERROR |
| 3 | attempt 2, `ssv1rt2-s1r-99405387…` (current) | ERROR |

- No job is active, and 0 GPU-seconds are reserved.
- The quota charged about 150 s to attempt 1 and 145 s to attempt 2.
- The reconciliation made no provider write.

## Still required before any further attempt

1. An independent review of this exact package (private lock r9), since no earlier approval covers changed code.
2. Reconfirmed private, account-only use and sanitized-output scope for lock r9, with explicit acceptance of any
   reused attachment, wheel-byte or model-verification evidence.
3. Separate source, compute and launch decisions; a fresh reservation and claim; one submission and zero automatic
   retries.

The frozen session-1 limits are 5,400 authorized seconds, 5,100 internal seconds, 600 policy calls, 32 reflections,
one canary and at most 600 offline actions. These are ceilings, not permission.

Session 2 still requires a technically complete, accepted session-1 evaluation.

## Open uncertainties

- The reason the target's `ps` scan was slow is unknown. If the `/proc` reads are also slow there, the run fails closed
  before readiness, and the receipt names the probe and the scan's cost.
- Target throughput remains unverified; admission and deadline enforcement stay the protection.

The scientific limitations recorded in the frozen protocol are unchanged.
