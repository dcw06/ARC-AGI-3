# Phase 4 full-game lifecycle certification — draft v1

Protocol ID: `P4-full-game-lifecycle-v1-draft`. Status: **not frozen, not
launchable, zero authorized compute**. This is a separate experiment from V2.
The associated budget is `reports/phase4_full_game_budget_draft.json`.
Documents remain outside the frozen prescreen source inventory so that the
completed V2 lock and Phase 2–3 decisions stay verifiable.

## Purpose and scope

Test real environment dispatch, model-backed action selection, bounded fair
service, legal degradation, cancellation, and acknowledged scorecard closure
under 110 concurrent client lifecycles. No E2–E6 changes, advanced scheduler,
game-solving improvement claim, H1/H2 exposure, or scored submission. Retain
E1S-R provisionally. Zero scores alone do not fail reliability certification,
but must be reported and must not be presented as solving progress.

The V2 fixture capacities (`C_nominal=419210`, `C_admit=252717`) are historical
fixture-only results, **not admission authority for real-game throughput**.
This protocol does not claim that its execution machinery exists yet.

## Required freeze before approval or packaging

1. Bind exact source, dependency wheelhouse and environment-engine artifacts,
   notebook, model tree, tokenizer/chat template, launch spec, E1S-R manifest,
   scheduler and policy prompt hashes in a new execution lock. Preserve V2's
   lock unchanged; include a standard-library-only offline bootstrap gate.
2. Bind a 110-row workload manifest with opaque client ID, exact game version,
   environment seed, request seed, action budget and isolation root. Validate
   every game against the development allowlist and holdout exclusions.
3. Bind local fault-test results, clean-checkout/offline installation evidence,
   evaluator source and required evidence inventory. A missing binding fails
   closed; no empty binding object or unverified success flag.
4. Bind a separate approved ledger and one fresh attempt ID. Account allowance
   must independently support the whole reservation; an ambiguous quota response
   is a launch blocker. Prescreen accounting may remain unresolved but cannot
   supply credit. No execution is authorized by this draft.

## Workload choice and claim boundary

Proposed development-only load: clients numbered 0–109; client `i` uses entry
`i % 15` from the ordered `development_game_seed_pairs` in
`config/e1_experiment_protocol.yaml`, preserving its exact game version and
environment seed. Request seed is 0; maximum 80 actions per client. Each client
has an independent environment, scorecard, evidence journal and runtime state;
only the bounded model service is shared. Register all rows explicitly before
execution, not just the generation rule. At most 8,800 E1S-R proposals; separately
account for bounded preflight canaries and fault probes. No parser repair or
model retry. Naturally terminal games stop; do not pad with synthetic requests.

This repeats development games and seeds and may benefit from prefix caching.
It can support **110-client bounded development lifecycle certification**, not
110 distinct official games or unrestricted full-game completion. Measure real
trajectory prompt/token distributions, repeat/cache rates, and terminal reasons.
Do not use game IDs or baseline scores as live scheduler features.

Before claiming the plan's full official-like exit, resolve whether this bounded
workload covers the intended official lifecycle and action limits. If not, freeze
a separately permitted representative manifest and seek a new budget; do not
silently introduce holdouts, change seeds, or relabel the development run. The
80-action cap is a resource envelope, not proof that every game was completed.

## Frozen candidate and proposed numeric envelope

- Exact model and parent from `config/operational_primary.yaml`: E1S-R,
  Qwen3-VL-30B-A3B-Instruct-FP8 revision
  `d9748a51ae66354c4dad665aab2c71f26cf2c8cd`, unchanged launch settings.
- `minimum_fair_v1`: 110 clients, queue capacity 110, eight inference workers,
  FIFO request sequence; maximum queue age and request timeout 300 seconds.
- One RTX PRO 6000. Record UUID before loading; require idle/exclusive initial
  GPU, unchanged UUID throughout, and no owned model processes at cleanup.
- Full lifecycle strictly below 27,540 seconds, measured from first cell and
  including installation, startup and evidence retention. Stop admitting work
  at 26,940 seconds; reserve 600 seconds for finalization. Provider wall-time
  cap 28,800 seconds is a separate billing bound, not an extended lifecycle.
- Dependency setup at most 900 seconds; model/preflight startup at most 900.
  Device VRAM at most 86 GiB, process-group RSS 128 GiB, scratch 4 GiB and retained
  evidence 64 MiB. Sample at most every 0.25 seconds. Demonstrate that the real
  journal fits before freeze; if not, amend limits prospectively, never drop T0.
- Process cleanup: 10-second graceful termination plus five-second kill and
  GPU verification. Stale/canceled request results never reach dispatch.
- Proposed service allocation 19,800 seconds with 20% headroom retained. A
  prospective real-trajectory capacity rule and numeric admission bound remain
  **unresolved prelaunch requirements**; V2 rates must not fill those fields.

## Lifecycle and faults

One fresh model/runtime per whole-workload attempt. Require an actual `E1Policy`
and successful model canary; E0-only execution cannot pass as E1S-R. Open and
retain scorecard/client identities, bootstrap each environment, run bounded
single-action closed-loop decisions, journal dispatch intent before transport,
record acknowledgements, and close every opened scorecard. Finalize in `finally`
paths even after errors. An unknown finalization result is never acknowledged.

Local deterministic fault matrix must pass before GPU approval:

| Fault | Required observed behavior |
| --- | --- |
| Queue full / age limit | Bounded admission; no unaccepted or expired dispatch. |
| Inference timeout / malformed proposal | Existing legal E0 fallback, counted and labeled; no model retry. |
| Cancellation while queued or decoding | No late action; retain cancellation acknowledgement or explicitly unsupported server abort; verify terminal process cleanup separately. |
| T2 storage failure | Degrade optional storage while preserving T0/T1. |
| T0 journal failure | Deny unjournaled dispatch and finalize safely. |
| Ambiguous post-entry environment result | Quarantine once; no retry or duplicate action. |
| Startup / model-process failure | Fail E1 certification; legal shutdown/fallback evidence cannot become an E1 pass. |
| Client or scorecard close failure | Record unknown/failed, fail certification, retain evidence. |

GPU whole-workload evidence must exercise actual environment dispatch and
scorecard closure, not fake acknowledgements. Any on-GPU injected faults need
predeclared timing, client selection and counts in a separately labeled segment
inside the same reservation, after the nominal segment. Freeze that schedule and
its resource allocation before launch; no ad hoc fault exploration. Do not infer
server per-request abort from successful process-group termination.

## Evidence and independent acceptance

Retain per-client start/terminal/finalization records, dispatch IDs and outcomes,
legal-action checks, real prompt/token counts and server parity, model/fallback
counts, queue/service quantiles and maximum age, per-client progress, resource
telemetry, GPU binding, cold-load and first-action timing, cancellation records,
scorecard receipts and complete attempted-client inventory. Retain bounded
critical checkpoints after child termination, including final errors. Capture
provider version/session metadata and all session history available; keep billed
duration, provider timestamps and internal timers distinct.

Acceptance requires all 110 clients accounted for; every opened scorecard closed
with an acknowledgement; zero duplicate, illegal, stale, canceled or unjournaled
dispatches; no retry after ambiguous dispatch; zero unclassified failures; all
numeric limits respected; verified cleanup; and complete hash-bound evidence
that independently recomputes counters and timings. Report quarantines and early
terminations, not as completed games. Unexpected quarantine, unknown closure,
missing evidence or a nominal-segment infrastructure failure blocks the nominal
certification pass even if legal containment succeeds. Injected-fault containment
is evaluated separately and cannot mask nominal failures.

Require real model inference for every nonterminal client before describing
coverage as model-backed; report fallback rates without hiding degraded clients.
Descriptive score/level progress is not an acceptance improvement test. Advanced
scheduling remains deferred unless measured allocation problems justify a
separate registered comparison with its own budget.

The evaluator must report scope and any unresolved official-like workload or
capacity gates. A bounded development pass does not automatically set
`phase4_complete=true`. Final closure requires the plan's full-load applicability
review, a frozen defensible real-workload capacity bound, and accounting disposition.

## Implementation handoff

Next implement the real lifecycle wrapper and strict evidence evaluator, including
the fault matrix; resolve workload/capacity/fault-segment choices and review the
offline notebook. Only then freeze the new lock, request explicit compute
approval, reserve one attempt and launch once. No prescreen retry is needed.
