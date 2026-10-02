# Track 3 evaluator r2: semantic evidence bindings

This is a local successor to the evaluator in `a2bc925`. Its output version is
`stagnation_supervision_v1_evaluation_r2`. The historical commit is preserved.
The protocol remains a draft; this record grants no source approval, reservation
or compute authorization.

## Review findings addressed

1. **Missing workload and failed closure.** Evaluation requires the exact
   ordered protocol group inventory. A completed report must contain every
   scheduled episode exactly once in the declared order, with matching game,
   block, arm and group identities. Each completed episode must have successful
   closure and a stop justified by its retained trajectory: terminal state,
   action horizon, invalid final policy response, or failed/unknown dispatch.
   Initial and final observations are checked, and policy, dispatch, reflection
   and token counters are recomputed. A re-signed empty report cannot pass.

2. **Policy response to action binding.** Replay constructs a fresh runtime from
   the verified initial observation and updates it from each acknowledged
   transition. It rebuilds each exact policy request, including the current
   observation, recent evidence, legal actions and independently replayed
   suggestion. Request hashes and pre-observation bindings are checked.
   Received response bodies, byte counts, hashes, positive integer token counts,
   tokenizer/server parity, token bounds, completion status and parsed actions
   are checked independently. A dispatched action must equal the parsed action.
   Missing, reused or out-of-range call bindings fail closed.

3. **Reflection evidence actually sent.** Before consuming a retained reflection
   response, replay constructs the full expected chat request from the fresh
   supervisor's evidence text and compares it with the retained request and
   hash. The evidence text must match exactly; a prefix-valid request containing
   `Evidence: {}` cannot pass with a recomputed hash. Stored admission counts,
   leftover responses, summaries and final suggestion state are also checked.
   Failed-call durations are retained measurements, not remeasured by replay.

Incorrect model answers remain outcomes when their evidence is internally valid.
An honestly retained invalid first policy response can justify `invalid_output`
with zero dispatched actions. Invalid reflections remain charged, retained and
undelivered. These cases are not relabeled as corrupted evidence.

## Local validation, 2026-10-02

Executed in the configured Ubuntu/WSL development interpreter:

```bash
/home/jingjing/.local/share/agi/dev-env/bin/python -m unittest \
  tests.test_stagnation_supervision_v1_live_evaluator -q

/home/jingjing/.local/share/agi/dev-env/bin/python -m unittest \
  tests.test_stagnation_supervision_v1_connected

python scripts/derive_stagnation_supervision_v1.py --check
```

- The focused evaluator suite passes **14 tests**, including clean evidence,
  legitimate invalid/failing responses and manifest-valid semantic mutations.
  Mutation cases write episode bodies and the run index through `RunEvidence`,
  regenerating valid manifests. They explicitly require `evidence_verified=true`
  and `technically_complete=false`.
- The connected CPU suite passes **3 tests**: normal completion, invalid
  reflections and transport failure. The shortened rehearsal uses one development
  game group, three arms and a 12-action horizon, through launcher, supervisor,
  worker, model host, bridge, runner, cleanup and independent replay. All model
  responses and GPU probes are scripted; this is no model/GPU result.
- **13 derived files** match the current derivation. Python compilation and
  `git diff --check` pass.

The connected process stack and derivation expansion were already uncommitted
when this task began. Their CPU success does not constitute a reviewed package.
The earlier report's two derivation-test failures concerned that dirty expansion;
the user's review did not reproduce them in the clean pushed snapshot. This task
does not claim a fresh pass of the user's broader 119-test suite.

## Target preparation and remaining gates

The strengthened evaluator works with the current connected rehearsal, and the
protocol checklist now records its implementation. Live mode remains disabled.
Before a reviewed target notebook can be frozen:

- decide the documented `ls20` inclusion question;
- finish live pinned-tokenizer admission wiring (the current worker raises
  `NotImplementedError` in live mode) and audit the exact requests/output bounds;
- resolve source provenance for the expanded derivation, including the rehearsal
  script absent from the historical source lock, without editing that lock;
- complete the connected deadline, cancellation, startup, monitoring and evidence
  exhaustion fault matrix, plus the audit sampling procedure;
- build and inspect a fresh GPU-disabled notebook and source lock in a clean
  checkout, then obtain separate approvals and reservations.

The replay checks retained token parity and bounds; it does not independently
retokenize without the pinned tokenizer. Closure receipts establish the declared
adapter's recorded closure, not independent provider billing. Observation equality
does not prove hidden-state equality. No policy is promoted and Phase 4 remains open.

Track 1 and Track 4 were not modified by this repair. No GPU work was launched.
