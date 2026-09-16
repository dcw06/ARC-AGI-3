# v5 development-only measurement design — review draft

This additive revision preserves v1–v4, including the v4 review notebook. It is
not a runnable target revision, approved measurement freeze, or compute approval.
It defines the next development pilot and provides tested capacity arithmetic.

## Scope and budget proposal

Use exactly the frozen v1 110-row workload: 15 repeated development games,
separate scorecards, E1S-R, request seed zero, existing environment seeds,
80 actions maximum, eight FIFO workers and one shared frozen model. Preserve
single-episode terminal-loss handling and the existing context/token settings.
No holdouts, advanced scheduler, scored submissions or production claim.

Propose one cold-start pilot attempt capped at 28,800 provider seconds, with
installation/startup/failures charged. This elaborates the existing separate
lifecycle budget proposal; it does not add another reservation. Authorized
seconds remain zero. All prescreen hours remain retained without credit.
Later confirmation/certification requires a separately reviewed budget.

The pilot must not depend on a capacity estimate from itself to authorize its
own launch. A reviewed pilot protocol must prospectively replace that circular
precondition with the hard 8,800-request cap, first-cell deadline, resource
limits and external cancellation. Do not alter the historical v1 condition.

## Prospective measurement rule

After model startup, record global monotonic workload start BEFORE any scorecard
opens and workload end AFTER all 110 finalizations. Separately retain first-cell,
install, cold-start/canary, cleanup, and provider billing clocks. No subtraction
of idle/bootstrap/drain/finalization periods from the workload interval.

Every request needs a unique opaque event ID (a prompt digest is not unique),
client ID, submission/service-start/completion times on the same clock, outcome,
token counts and tokenizer parity. Retain all events, including failures and
cancellations. Live scheduler inputs stay unchanged. Record latency quantiles
for queue, service and end-to-end separately; do not sum overlapping latencies
to estimate throughput. Report prompt digest repetition and token distributions;
repeated seeds and prefix-cache benefits remain explicit scope limitations.

Before calculating capacity, independently validate the complete 110-client
inventory, journals, finalization receipts, exact source/model/workload bindings,
all request events and GPU/resource evidence. Any nominal infrastructure failure
or incomplete evidence makes the pilot inconclusive; no selective rerun/window
deletion, fallback counting as model completion, or zero-padding terminal games.

Candidate rule implemented in `capacity.py`:

1. Divide the entire workload interval into eight equal wall-time windows.
   Assign successful model completions by completion time; retain empty windows.
2. Nominal rate = total completions / entire workload wall time.
3. Empirical conservative rate = 0.8 × minimum window completion rate.
   This 20% rate margin is separate from service-budget headroom. It is not a
   confidence interval, independence claim, or deterministic lower bound.
4. Service budget = 19,800 seconds. Headroom = 20% = 3,960 seconds.
   Effective service budget = 15,840 seconds.
5. C_nominal = floor(19,800 × nominal rate).
   C_admit_candidate = min(C_nominal, floor(15,840 × conservative rate)).
   An empty window yields zero candidate admission; do not change the rule after
   seeing data. All numeric measured values remain unavailable before the run.

The calculator is arithmetic, not an independent evidence validator: it cannot
authenticate a list of timestamps. Its output deliberately leaves C_admit null.
After pilot review, any admission freeze must bind retained measured evidence,
the predeclared rule, source and complete configuration; label the empirical
guard honestly and require separate prospective confirmation. A single pilot
does not establish reliability uncertainty across whole runs or future games.
The 8,800-request hard cap continues even if projections are much larger.

## Focused v4 source review: concrete blockers

- `worker.py` retains per-request service duration but no global submission/start/
  completion timestamps. It cannot feed this rule or independently reconstruct
  queue latency. Add event instrumentation in a new runtime revision and test
  diagnostic invariance before packaging.
- `build_notebook.py` invokes run_target with unbounded subprocess.run. Its child
  supervisor provides a deadline only while healthy. An outer notebook watchdog
  must own and terminate the supervisor AND its independently grouped worker/model
  descendants, with verified cleanup. Killing the supervisor group alone is
  insufficient because worker launch uses start_new_session=True.
- `supervisor.py` limits one checkpoint to one third of evidence_bytes, but writes
  worker data twice and accumulates GPU telemetry without enforcing the total
  retained-output ceiling. Required journals must never be silently truncated.
- The evaluator samples UUID/VRAM but does not enforce timestamp coverage/gaps of
  telemetry. Sparse telemetry cannot prove continuous resource compliance.
- Clean target-compatible offline installation remains unverified, including
  the separate vLLM wheelhouse. A dependency-resolution dry run is not sufficient.

Next implementation: a new runtime revision addressing those blockers, then
negative tests, independent review and source/evidence lock. Only afterward seek
explicit one-attempt GPU approval and allowance verification. Neither the v4
notebook nor this design may be uploaded as an approved run.
