# Track 3 runtime v2: package r11 verified before session 2 (sanitized)

**Status.** This is a GPU-disabled verification record, and it authorises nothing by itself.
- Session 1 (attempt 3, provider version 4) is technically complete and accepted.
- All four attempts are consumed: R6 and session-1 attempts 1, 2 and 3.
- The account holder approved session 2's four decisions on October 12. The source decision says the launch happens
  only after this verification passes; it has passed.

| Review | Repairs | Detail |
|---|---|---|
| Review of r9 | r10 (`5ff385e`): session-1 attempts 1 and 2 join the consumed history | `reports/stagnation_supervision_runtime_v2_consumed_attempts_r10.md` |
| Review of r10 | r11 (`4bf2d35`): the completed session-1 attempt is consumed too; session-2 refusal regression | the r11 section of the same file |

| Item | Value |
|---|---|
| Public review snapshot r11 | `notebooks/stagnation-supervision-v1-runtime-v2-review-r11/`, lock `ce6c7e101c28317dd17b7dc30990ef816eda1a78d5fd886c94509c6ddf1eac2d`: 154 embedded bindings, 180 review documents, four private placeholders unresolved, GPU disabled |
| Private review snapshot r14 | lock `371dbd5bf5d2276f482e903d84d6d8b84de3638163c472b35275b7f4fb7dc0b7`; differs from public r11 only in the runtime protocol's four private bindings (unchanged since session 1) |
| Session-1 evaluation under private r14 | read-only re-evaluation of the retained evidence (`29001aa96df74d9ba1d79cd09cf540b92104b852cad87e298a13626f9d040795`): technically complete and accepted, 0 problems; identical to the r13 evaluation apart from the evaluating lock, which is retained |

## Fresh Linux verification of this revision (CPU; scripted model; injected GPU; not target evidence)

| Check | Result |
|---|---|
| CPU suite r15 (`..._local_checks_r15.json`, CPython 3.12.3) | 304 tests (160 historical, 144 runtime v2, including the consumed-attempt regressions), 0 failures, errors or skips; all seven receipt checks pass |
| Derivation (Windows checkout) | 16 derived files match; 14 invert to their sources |
| Public review check r11 | passed: 154 bindings verified, embedded files compiled, live refusal at the gate before any GPU use, embedded-cell rehearsal technically complete |
| Private review check r14 | passed |
| Staged interpreters (from the extracted r11 payload) | both trusted-lock installs passed (215 s) |
| Staged session 1 (15 episodes at 40 actions) | technically complete with the lifecycle verified, 0 problems; first cell 356 s (installation 176 s); finalization certified, source removed |
| Staged session 2 (12 episodes at 40 actions) | technically complete with the lifecycle verified, 0 problems; first cell 283 s (installation 164 s); finalization certified, source removed |
| Final session-2 launch notebook of r14 (built in a temporary copy with synthetic authority) | session-2 kernel, private, GPU on `NvidiaRtxPro6000`, TPU and internet off, exactly the wheel and model datasets and the competition, no model sources, the pinned image, session 2, live mode, the session-1 evaluation embedded, 591,629 bytes, bound to lock r14 |
| Same build with session-1 attempt 3's id | refused |

The game interpreter's informational probe of an optional local-engine module reports it absent, as in r10. That module
is not part of this payload, and installation passed.

## Session 2's bounds

- 4,800 authorized seconds, 4,500 internal seconds;
- 480 policy calls, 32 reflections, one canary;
- 12 episodes of 40 actions (at most 480 offline actions);
- zero online game calls, scorecards, holdout runs and retries.

These are ceilings, not permission. The launch is bound to the accepted session-1 evaluation above.

## Open uncertainties

- Target throughput remains unverified; admission and deadline enforcement stay the protection.
- Session 1's study outcomes stay withheld until session 2 and the S1 self-review.

The scientific limitations recorded in the frozen protocol are unchanged.
