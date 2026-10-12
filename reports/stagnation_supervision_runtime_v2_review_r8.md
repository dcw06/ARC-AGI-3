# Track 3 runtime v2: package r8 for independent review (sanitized)

**Status.** This is a GPU-disabled review record. It authorises nothing. Both session-1 attempts are consumed and no
further attempt is authorized. The repairs answer two independent reviews.

| Review | Repairs | Detail |
|---|---|---|
| Review of `b80b75c` | r6 (`2e4d54c`): cleanup control flow, `/proc` probes, warm-up diagnostics | `reports/stagnation_supervision_runtime_v2_attempt2_repairs_r6.md` |
| Review of r6 | r7 (`ee6aafd`): the budget bounds the caller's wait; consistent interrupted census | `reports/stagnation_supervision_runtime_v2_procfs_bound_r7.md` |
| CPU suite r11 failure | r8 (`bbddbe0`): the scan's worker started with `_thread` | the r8 section of the same file |

The r7 snapshot and suite r11 are retained as superseded and failed records.

| Item | Value |
|---|---|
| Public review snapshot r8 | `notebooks/stagnation-supervision-v1-runtime-v2-review-r8/`, lock `735478845af79c5b5f202dcbc51ae62c45a66d539d968e7939fee35e44c65d1c`: 154 embedded bindings, 179 review documents, four private placeholders unresolved, GPU disabled |
| Private review snapshot r11 | lock `00cb69dbe6b8b505bd7448e5f2a92cd5f03211365bfb73f1adbdf20ad3cb9a68`; differs from public r8 only in the runtime protocol's four private bindings (unchanged from both attempts) |

## Fresh Linux verification of this revision (CPU; scripted model; injected GPU; not target evidence)

| Check | Result |
|---|---|
| CPU suite r12 (`..._local_checks_r12.json`, CPython 3.12.3) | 298 tests (160 historical, 138 runtime v2, including the r6-r8 regressions, the prelaunch regressions and the connected fault matrix), 0 failures, errors or skips; all seven receipt checks pass, including the runtime diff r8; `--check` binds the committed tree |
| Derivation | 16 derived files match; 14 invert to their sources |
| Public review check r8 | passed: bindings verified, embedded files compiled, live refusal at the gate before any GPU use, embedded-cell rehearsal technically complete, no leaked source |
| Private review check r11 | passed: no unresolved bindings; live refusal at the gate before any GPU use; embedded-cell rehearsal technically complete |
| Staged interpreters (from the extracted r8 payload) | both trusted-lock installs passed (157 s) |
| Staged session 1 (15 episodes at 40 actions) | technically complete with the lifecycle verified; first cell 309 s (installation 151 s); finalization certified, source removed; the bounded `/proc` RSS probe ran on real processes throughout |
| Staged session 2 (12 episodes at 40 actions) | technically complete with the lifecycle verified; first cell 362 s (installation 195 s) |
| Final launch notebook of r11 (built in a temporary copy with synthetic authority) | session-1 kernel, private, GPU on `NvidiaRtxPro6000`, TPU and internet off, exactly the wheel and model datasets and the competition, no model sources, the pinned image, session 1, live mode, 569,685 bytes, bound to lock r11 |

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

1. An independent review of this exact package (private lock r11), since no earlier approval covers changed code.
2. Reconfirmed private, account-only use and sanitized-output scope for lock r11, with explicit acceptance of any
   reused attachment, wheel-byte or model-verification evidence.
3. Separate source, compute and launch decisions; a fresh reservation and claim; one submission and zero automatic
   retries.

The frozen session-1 limits are 5,400 authorized seconds, 5,100 internal seconds, 600 policy calls, 32 reflections,
one canary and at most 600 offline actions. These are ceilings, not permission.

Session 2 still requires a technically complete, accepted session-1 evaluation.

## Open uncertainties

- The reason the target's `ps` scan was slow is unknown. If the `/proc` reads are also slow or stall there, the probe
  fails within its budget, before readiness, and the receipt names the probe, the phase and the scan's cost.
- Target throughput remains unverified; admission and deadline enforcement stay the protection.

The scientific limitations recorded in the frozen protocol are unchanged.
