# Track 3 connected target: GPU-disabled R2 review candidate

This revision prepares source for independent review. It grants no source approval, compute authorization,
reservation, model inference, Kaggle upload or GPU launch. The connected stack's first independently reviewable
checkpoint is `82f1d0c`. The final candidate binds the successor executable and this report by SHA-256;
the historical derivation sources and earlier review locks remain unchanged.

The user explicitly retained ls20 as an exposed development continuation case. Its display-driven novelty
and playfield oscillation must accompany results. The selection criterion, game seed, initial state and
scheduled workload were not replaced. This decision supplies no launch authority.

The target stack connects installation, distinct model/game interpreters, a retained canary, a ready bridge,
the worker, resource monitoring, bounded evidence and external cleanup. Exact reflection-token admission now
uses a hash-bound count operation in the model process, with the serving tokenizer. It makes no inference
request and does not consume an inference-call slot. The game interpreter remains free of model dependencies.
The count operation has a separate 2,160-call CPU ceiling and uses the shared cancellation/deadline rules.

Readiness validates the canary's request, retained response/hash, action, positive integer token counts,
completion cap, finish reason, artifact and 900-second startup ceiling. The real model host is import-tested
with `arcengine` and `arc_agi` blocked. These are CPU contract checks, not new target-installation evidence.

The online protocol rules are also part of this review: running dispatch failures above 10% stop the session;
zero firings in the completed full-horizon b1-ar25 continuation stop subsequent work; and an invalid-output
reflection fraction above 50% after at least ten attempts ends/skips the reflection arms. Continuation may
proceed after that last rule, but the result remains incomplete for comparison. Exact semantics are in
protocol v2 and negative regressions; they require review before any source approval.

The independent evaluator binds the ordered scheduled inventory, justified episode completion, successful
client/scorecard closure, reconstructed observations and requests, policy response/action bindings,
token/finish checks, exact reflection evidence, supervision replay and online-stop rules. Incorrect but valid
reflection content remains an outcome. A non-`stop` reflection is charged and retained but delivers no new
suggestion. Incomplete evidence cannot produce a technically complete comparison.

## Local verification and its limits

The machine-readable test receipt is `reports/stagnation_supervision_v1_local_checks_r2.json`.
The connected tests use the offline development engine, real process groups, real RSS/scratch measurements,
scripted model responses and explicitly injected GPU probes. They establish CPU execution/replay and fault
handling; they establish no GPU capacity, target startup timing, model correctness or solving improvement.

| Path | Required result |
|---|---|
| Normal three-arm rehearsal | Completed trajectories independently replay; process, injected GPU and scratch cleanup verify |
| Invalid or length-finished reflection | Charged, retained, delivers no new suggestion; replay distinguishes validity from lifecycle failure |
| Startup failure / transport failure | Partial evidence survives; no complete comparison; cleanup verifies |
| Monitor exit | Outer failure survives the monitor; independent cleanup verifies |
| Evidence exhaustion | Technical failure retained; no complete comparison; cleanup verifies |
| Cancellation | Admitted work stops; partial trajectories survive; cleanup verifies |
| Frozen group admission cutoff | No group admitted, no policy calls; explicitly not a mid-call deadline test |
| Slow calls after rehearsal-only admission override | Actual calls occur before the retained external cutoff; either `deadline_exceeded/run deadline enforced` or `technical_failure/model transport` survives, depending on whether the cutoff lands between calls or inside the bridge; cleanup verifies |
| SIGTERM-resistant descendant | Escalation removes the owned group and independently verifies termination |
| Failed cleanup | Remaining group, wrong UUID, remaining GPU PID and expired cleanup deadline all fail verification |

The live 800-second group-admission rule remains unchanged. The shortened admission override is available
only in CPU rehearsal. No-retry is enforced by source control flow and authority consumption; counting one
model-process filename is not claimed as independent proof that a process never restarted.

The pinned tokenizer audit counts all 1,122 exact scripted requests: 1,080 policy requests and 42 actual
reflections. Policy maximum is 26,010 tokens; actual reflection maximum is 1,483; the constructed reflection
stress case is 1,533. All declared audit checks pass. Tokenizer provenance is separately recorded.
The input-replay report verifies the final ordered request hashes against that immutable audit and binds
the final request-generating source. The audit covers scripted trajectories, not every future live state or
model-generated suggestion; every actual request still undergoes exact runtime prompt/context admission.

## Notebook and remaining authority

`notebooks/stagnation-supervision-v1-review-r2` is a new embedded-source target candidate with GPU, TPU and
Internet disabled. It selects session 1 and cannot start session 2 automatically. The package review verifies
unpacked source, compiles all packaged Python, rejects the as-frozen live cell before installation, checks
source removal and runs/replays a shortened three-arm CPU bootstrap. Its live gate deliberately remains
closed, even with synthetic approval records. Missing, mismatched or consumed authority is tested separately
against the underlying validator; synthetic records are test fixtures and are never real approvals.

The frozen proposals are 5,400 provider / 5,100 internal seconds for session 1 and 4,800 / 4,500 for session 2.
Study work stops 300 seconds before each internal limit; the provider proposal retains another 300 seconds
of buffer. Each session permits one canary, at most 32 reflections, no automatic retries, and respectively
600 or 480 policy calls. These are proposals, not spending authority or proof all work will fit.

Before submission, an independent reviewer must disposition this candidate and the documented stop-rule
semantics, target-timing uncertainty, two-session split and blinded reference-label audit. A separately
reviewed authority revision must bind an executable source lock, explicit source approval, separate compute
authorization and one fresh reservation per admitted session. The current R1 gate must not be bypassed by
toggling notebook flags. Nothing has been reserved, uploaded or launched here.

Clean-checkout CPU commands, using a Linux interpreter with the project's offline game dependencies:

```sh
python -m scripts.derive_stagnation_supervision_v1 --check
python -m scripts.check_stagnation_supervision_v1_review_r2 --check
python -m unittest discover -s tests -p 'test_stagnation_supervision_v1*.py' -v
python -m scripts.verify_stagnation_supervision_v1_audit_inputs --check
python -m scripts.verify_stagnation_supervision_v1_audit_inputs --replay
python -m scripts.review_stagnation_supervision_v1_notebook_r2 --folder notebooks/stagnation-supervision-v1-review-r2
```

The replay restores manifest-checked development games from the committed archive, rather than ignored
`reports/runs` files. Retokenizing requires the pinned tokenizer files and versions documented by the audit.
The review command is read-only apart from temporary rehearsal outputs; `--record` separately retains a new
write-once receipt. Existing receipts are preserved and compared.

Phase 4 remains open: production one-scorecard/110-distinct-game certification, workload-specific admission
limits and exact accounting are unresolved. This exploratory study cannot close those gates automatically.

## R2 packaging correction

R1 is retained unchanged. A committed-source export identified that R1 embeds the evaluator but omits
`scripts/replay_transition_evidence_v1.py`, which that evaluator loads. R2 embeds and hashes this helper
explicitly, and binds the reused package-builder/verifier scripts as review documents. No prompt, request,
case, serving setting, budget, online rule or model-service source changes. The existing pinned tokenizer
audit and exact request replay remain applicable. The new receipt covers the complete R2 source inventory.
The authority module remains deliberately closed and still references the historical R1 path; a future
reviewed launch-authority revision must replace that path and gate. No R1 approval is reused.
