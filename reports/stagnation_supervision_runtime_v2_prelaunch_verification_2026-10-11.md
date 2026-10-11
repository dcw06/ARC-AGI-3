# Track 3 runtime v2: prelaunch repair verification

The six findings against `b39f9e6` are repaired in `591d490` and `3908546` on
`track3-successor-runtime-v1`. Generated files were changed through their derivation.
The frozen scientific protocol, schedules, trigger thresholds, prompts, horizons and
compute ceilings are unchanged. Historical snapshots and the consumed R6 attempt are preserved.

| Finding | Result |
| --- | --- |
| Inner child ownership | A durable intent journal precedes each spawn. Each bootstrap records its future process group before detaching. Cleanup recovers both child groups after supervisor death and refuses to certify absence when ownership is uncertain. |
| Installation evidence | Independent acceptance requires both successful installation records, frozen identities, timing, command ownership/cleanup, retained logs and wheel-install plans. Recorded metadata must also match the exact probe and its retained stdout. |
| Endpoints after technical failure | Outcome endpoints are withheld unless the complete lifecycle and checkout verdict pass. Failure diagnostics and charged costs remain available. |
| Live escape hatches | Live reporting requires checkout verification; live pooling refuses detector overrides. Overrides are confined to explicit rehearsals. |
| Reflection/sample binding | The sample binds both verified evidence inventories, reflection requests/responses/interventions and reconstructed suggestion actions. Changed reflections invalidate prior annotations even when transitions are unchanged. |
| Private annotation commitment | Live pooling requires a prior immutable local Git commit containing the exact completed annotations and evidence-bound sample. A supplied hash alone refuses. This provides neither independent review nor an external timestamp. |

## Regression and connected checks

The retained baseline reproduction ran nine test methods on an unmodified `b39f9e6`
checkout: all nine failed, with ten failed assertions/subtests and zero errors.
The extra failure is the missing/failed installation receipt test's two cases.
See [the retained reproduction](stagnation_supervision_runtime_v2_b39f9e6_reproductions.py)
and [its output](stagnation_supervision_runtime_v2_b39f9e6_regressions.txt).
Real CPU children used in ownership tests were terminated and reaped.

The current regression suite adds supervisor-death, logging-start, installation
inconsistency, rehashed-stdout tampering and private-commit tampering cases.

| Check | Result |
| --- | --- |
| Complete fresh Linux suite | Pass on fresh `26b993e`: 277 tests (160 historical + 117 successor), zero failures/errors/skips; all seven required checks pass; 842.851 s. Earlier failed CPU attempts retained separately. |
| Generated files | 16 match the derivation; 14 invert to their recorded sources. |
| Public r4 review notebook | Pass: 161 source bindings, CPU rehearsal complete, live refusal before GPU use, no extracted-source leak. |
| Private r7 review notebook | Pass: no unresolved bindings; CPU rehearsal complete and live refusal before GPU use. Approval and reservation records absent. |
| Public r4 extracted payload, session 1 | Pass: full 15-episode scripted schedule, 40-action horizon, zero evaluation problems; first-cell lifecycle 741.763 s, installation 370.019 s. |
| Public r4 extracted payload, session 2 | Pass: full 12-episode scripted schedule, 40-action horizon, zero evaluation problems; first-cell lifecycle 639.517 s, installation 355.873 s. |
| Public r4 and private r7 rebuild | Both byte-identical to their retained snapshots. |

The final [CPU receipt](stagnation_supervision_runtime_v2_local_checks_r7.json) binds
the current sources, tests and runner, and explicitly identifies the one historical
test replaced by its successor. Its read-only verification passes:

```sh
python -m scripts.check_stagnation_supervision_runtime_v2 --check
```

The [verification inventory](stagnation_supervision_runtime_v2_prelaunch_verification_2026-10-11.json)
records every earlier CPU attempt and the connected-rehearsal hashes. The full suite
used Linux CPython 3.12.3 with arc-agi 0.9.9, arcengine 0.9.3 and numpy 2.5.2; the
connected installer rehearsals separately installed the frozen model/game pins.

Both connected sessions installed the real model and game interpreters from staged
local wheels, then used a scripted model and injected GPU telemetry. Their installer
logs and process cleanup were independently checked; dependency trees and extracted
source were removed. The installation allowance was explicitly overridden to 1,800 s
for these CPU rehearsals. These are not real-model results, pinned-image timing evidence
or proof of GPU compatibility.

Two test assumptions exposed by the full suite were corrected separately. `281ef16`
keeps the installer environment stand-in a class so the model backend regression reaches
the intended checks. The first cutoff-test correction (`f1b07ee`) changed a file bound
by older packages, and assumed verified partial evidence always has a final status.
The full suite correctly refused those historical bindings; all failed CPU receipts
are retained. `26b993e` restores that file byte for byte and adds a successor-only
replacement which checks both interrupted/unverified evidence and verified incomplete
snapshots, including a still-running snapshot killed at the external cutoff. Both must
remain technically incomplete with verified cleanup. The runner explicitly records
the one replaced test; its successor is counted, not skipped. Neither runtime nor
scientific acceptance criteria are relaxed. `e36fc6f` also replays the original R4
receipt against its exact `b39f9e6` tree. An old receipt cannot certify changed tests.

## Review snapshots and remaining authority

Public review r4 is at
`notebooks/stagnation-supervision-v1-runtime-v2-review-r4/`, with lock SHA256
`b9f166006541166adaa98f0d699089ae716c7cd5da9c8c82020557cedfd5193c`.
It binds 161 payload files and 182 review documents. GPU, TPU and internet are disabled;
authorized compute is zero.

The final private r7 candidate and its review packet remain git-ignored.
The superseded private r5 draft is preserved: its folder number differed from its
embedded r4 label, so it is not the final candidate. Private r7 retains the intended
four private bindings, with 23 licence texts checked by size and SHA256. Use assessment,
wheel-byte reuse, model-verification reuse and a proposed GPU-off Quick Save remain
drafts; all approval outcomes remain blank.

Next: independent review of the exact private package and its immutable image/input
bindings, completion of scoped Gate 4 evidence, then separate session-1 source approval,
compute authorization, reservation and exact-attempt launch confirmation. No provider
operation, GPU run, approval or reservation was performed for these repairs. Session 2
remains separately gated after session 1's technical validation. The consumed R6 attempt
cannot be reused.

The exposed development games, solo unblinded review, noncertifiable false-interruption
gate, exploratory ls20 display effects and possibly identical repeats remain limitations.
Track 3 is prepared for review; its GPU study is not complete.
