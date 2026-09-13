# Phase 3 preparation — inactive

All work here is offline preparation, not E5/E6 activation or Phase 3 completion.
The running Phase 2 lock and its bundled files are unchanged by this preparation.
The separate draft contract is `config/phase3_preparation.json`; it is not a
replacement for the frozen experiment registry. Its proposed two-treatment cap
and two-hour family ceiling are planning limits, not compute authorization.
The actual allocation is zero. Games, seeds, exact parent, matched ceilings,
pair count, numerical futility/regression thresholds and inference rule remain
unresolved deliberately. Freeze them before observing Phase 3 outcomes. The
execution gate always rejects this draft, including when a caller fills fields.

## Prepared components

1. Draft contract: E5 / E6-DISC / E6-REPEAT candidates, sequential allocation,
   reproduced-failure requirement, complete-workload comparison units, accounting,
   safety stops and explicit unresolved prospective choices.
2. Versioned fixture-only schema: at most four hypotheses and 64 predictions,
   bounded claims/references, typed scope, evidence, precommit sequence, expiry,
   contradiction and recommendation fields. Schema status labels do not confer
   verified support. No live hypothesis store or status advancement exists.
3. Pure evaluator: dependency-bound exact integer facts, three-valued outcomes.
   A trusted extractor must eventually establish scope, correspondence and
   dependency relevance; fixtures supply these explicitly. No image extractor,
   tracker, semantic inference or generic changed-cell proxy is implemented.
4. Controller oracle and tests: no environment access; missing/unknown required
   conditions cancel, ambiguity quarantines, and inactive E6 remains single-action.
   Existing production E1 schema rejection is exercised independently.
5. Synthetic support fixtures: distinct-transition counting, discriminating
   alternatives, repeated local support, contradiction, expiry, evidence loss,
   correspondence loss and timer-insensitive local fingerprints. These are not
   evidence of a real failure, a useful treatment, or statistical independence.
6. Offline paired-results harness and the report template below. It checks exact
   shared bindings, fresh IDs, complete workload pairs and charged metric fields.
   It reports counterbalance and paired differences, never a promotion or an
   unfrozen confidence interval. Cost completeness is declared by input records;
   eventual runtime evidence must verify it. It does not launch experiments.

## Local commands

```bash
.venv/bin/python -m unittest tests.test_phase3 -v
.venv/bin/python scripts/phase3_prepare.py
.venv/bin/python scripts/phase3_prepare.py --records path/to/paired-records.json
```

## Prospective report template

- Admission: reproduced failure hash, category, excluded transport/resource causes.
- Parent: Phase 2 decision, exact manifest/model/prompt/runner/scheduler hashes.
- Treatment: exactly one feature delta and observation bundle; inherited features.
- Protocol: freeze timestamp/hash, games/seeds, AB/BA allocation, complete-workload
  randomization and paired-workload uncertainty unit, numerical ceilings and stops.
- Accounting: setup, probes, support-building, failed work and extra inference;
  total family ledger and headroom-adjusted full-run projection.
- Outcomes: official RHAE percent, actions, calls, tokens, probes, blocked/false
  continuations, scope failures, elapsed time, peak RAM/VRAM; all run outcomes.
- Inference: frozen paired rule, multiplicity if both E6 gates are tested,
  selection-procedure estimand separate from final fixed candidate. Sparse or
  tied evidence remains provisional. Do not pool differing parents or workloads.
- Decision: reject/retain parent/provisional treatment; safety findings and rollback.
- H1: deferred until stable architecture/resources and truthful exposure label.

Each input row requires pair_id, run_id, arm (parent/treatment), order (AB/BA),
mode=shared_resource_whole_run, complete_workload=true,
cost_scope=all_work_including_setup_probes_support_and_failures, metrics containing
all contract metric keys, and seven 64-hex bindings: parent_sha256, model_sha256,
scheduler_sha256, workload_sha256, ceilings_sha256, protocol_sha256 and
treatment_manifest_sha256. The treatment binding identifies the comparison in
both arms; it does not imply the parent executes that treatment.

Before activation: review the real Phase 2 evidence; justify E5/E6 independently;
bind the resulting parent and remaining budget; freeze prospective thresholds;
register only the selected treatment; implement and validate its real extractors,
runtime cost capture and enabled controller. Keep single-action rollback. Do not
run H1, activate memory/retrieval, or change the shared inference scheduler here.
