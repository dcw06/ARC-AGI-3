# Phase 2 treatment contract

Date: 2026-09-12

Status: **contract frozen; zero treatments admitted or activated**.

Chunk 2.0 closes the failure-driven admission surface before treatment code is
written. Its authority is `config/phase2_contract.yaml`, SHA-256
`ac93fec5404824cc58744f3d1da72a1bc2c4706d96ad3eb1ecd634a37b43b430`.

## Frozen scope

- At most **two** treatments may be activated in Phase 2.
- Treatments are evaluated strictly sequentially. A prior treatment and all of
  its runtime state must be finalized before another admission is considered.
- The only registered treatments are E2a, E2b, E2c, E2d, E3, and E4. All six
  remain `inactive_pending_reproduced_failure_admission`.
- The exact parent is E1S-R, the Phase 1 `Provisional primary`, with frozen
  operational-config, feature-manifest, model-binding, and Phase 1 decision
  hashes.
- Evaluation uses the same fifteen development games and one frozen seed per
  game. H1 and H2 are not available to Phase 2 diagnosis or admission.
- The comparison is `shared_resource_whole_run`. It uses two counterbalanced
  parent/treatment blocks; the paired complete-workload block is both the
  randomization and uncertainty unit. Per-game values are diagnostic only.
- The family receives at most 8 RTX PRO 6000 hours, 4 hours per treatment,
  eight total complete-workload runs, 120 game plays, 9,600 model requests,
  one infrastructure-only failed-run allowance, and zero scored submissions.
  Failed runs still consume the eight-hour family allowance from kernel start
  through exit.

## Admission rule

A treatment remains inactive unless one taxonomy entry maps to it and one
failure record proves all of the following under the exact parent:

1. At least two distinct parent-only runs reproduce the same failure signature
   on the same frozen game and seed.
2. Every reproduction uses policy-visible development evidence only; evaluator
   and holdout evidence are absent.
3. The diagnosis attributes the failure to exactly one registered missing
   capability and excludes protocol, resource/queue, and environment/transport
   causes.
4. Evidence remains exact or summarized and has action-relevant references.
   E4 specifically requires available exact historical evidence.
5. Admission uses the frozen contract hash and thresholds. A later threshold
   change requires a new contract revision and fresh experiment.

The diagnostic taxonomy includes six admissible failure classes, one for each
registered treatment, and four explicitly non-admissible classes. Protocol,
resource, transport, and unsupported failures cannot be relabeled as evidence
or memory failures.

## Feature and stopping boundary

Each admitted manifest may enable exactly the one feature delta registered for
its treatment. Model, scheduler, context mode, one-action surface, games/seeds,
action/reset/retry limits, runtime, and finalization limits remain identical to
the parent. E5 hypotheses, E6 queues, Python, transition models, search,
specialists, advanced scheduling, and cross-game mutable memory remain disabled.

The sample rule is two fixed paired blocks with no early positive stop. The
family stops after two activated treatments, 8 accelerator-hours, or the dated
deadline. Safety, parent-hash, feature-leakage, evaluator-access, runtime,
ambiguity, queue, or finalization violations stop immediately. Candidate-caused
failures remain scored; only one infrastructure invalid run may be repeated,
and only when it emitted no usable policy or semantic result.

## Machine gate

The failure-record and treatment-manifest schemas are closed with
`additionalProperties: false`. `scripts/validate_phase2_contract.py` verifies
the registry cap, inactive state, parent hashes, games/seeds, taxonomy,
comparison units, compute allowance, prospective decision rules, stop rules,
and schema hashes. Its proposal-validation path rejects unregistered treatments,
feature leakage, retrospective thresholds, unreproduced failures, and missing
or drifted parents.

Run:

```bash
make validate-phase2-contract
```
