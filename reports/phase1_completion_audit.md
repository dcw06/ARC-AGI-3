# Phase 1 completion audit

Date: 2026-09-12

Audit result: every Phase 1 deliverable and exit-gate prerequisite that does
not require the frozen counterbalanced whole-run result is complete. Phase 1
itself remains open until that result is downloaded and validated. No causal
factorial claim is made from kernel version 5.

## Deliverables

| # | Requirement | Status | Closure evidence |
|---|---|---|---|
| 1 | Freeze the current Duck-style control and strongest eligible structured-action control, with Section 5.2 classifications | **Complete** | `config/control_registry.yaml` and `reports/phase1_control_freeze.md` freeze Duck and Reki as unavailable published references, E1S-R as the eligible project structured fallback, and E1C-F as an adapted substitute rather than a reproduction. |
| 2 | Published reproduction and justified same-model normalization | **Complete by fail-closed disposition** | No eligible faithful published runner exists at the cutoff. The registry records `unavailable_not_run_fail_closed`; same-model normalization is explicitly `not_justified_without_an_eligible_faithful_published_harness`. Published scores are not substituted. |
| 3 | Strict E1S and safe-operation E1C on the frozen minimum queue and Section 5.4 manifest | **Complete** | `agent/e1_policy.py`, `agent/safe_operations.py`, `agent/feature_manifest.py`, and `config/e1_feature_manifests.yaml`; strict one-action schema, no repair, bounded safe operations, one shared queue contract, and disabled later treatments are tested. Published-control capabilities remain separately classified in the control registry. |
| 4 | Causal four-cell E1 when one model supports all cells; otherwise non-causal tournament plus same-model comparison | **Pending only the excluded run** | One exact model supports all four cells. Version 5 is retained only as a descriptive single shared-resource block. `config/e1_whole_run_protocol.yaml` freezes the corrective two-block, reverse-order, fresh-runtime comparison with the paired complete-workload block as randomization and uncertainty unit. Execution and evidence validation are the sole remaining work. |
| 5 | Stateless reconstruction versus visible compaction only after demonstrated need; cached/programmatic optional | **Complete** | `config/context_policy.yaml` and the version-3 failure record document the observed context-continuity failure that activated visible one-transition compaction. Cached and programmatic modes remain inactive. |
| 6 | Hierarchical report, model/runtime table, offline bundle, operational primary | **Complete** | `reports/phase1_hierarchical_decision.md`, `config/dependency_manifest.lock`, and `config/operational_primary.yaml`. E1S-R is a runnable `Provisional primary`; E0 is the legal fallback. The submission performs an actual completion canary before any competition call and applies the 27,540-second full-lifecycle deadline. |

## Exit gates

| Requirement | Status without the excluded run | Evidence |
|---|---|---|
| No invalid factorial comparison across models, queues, or uncharged work | **Pass** | All four E1 manifests share one exact model/engine/reasoning binding and `minimum_fair_v1`; version 5 is explicitly non-causal and all model/tool work is charged. |
| Later-treatment features disabled; R/F claims include intermediate-frame evidence access | **Pass** | Durable memory, retrieval, hypotheses, prediction queue, Python, transition model, search, and specialist features are false. R excludes raw and derived intermediate evidence; F contains only registered features derived from bounded intermediate-frame sequences. |
| Comparison execution mode and statistical unit agree | **Pass for design and existing evidence** | Version 5 is a descriptive `shared_resource_whole_run`; the pending closure uses paired complete-workload blocks for both randomization and uncertainty. Final empirical validation depends only on the excluded run. |
| Accepted cells fit safety and resource ceilings | **Pass** | No cell is accepted. Every eligible/provisional cell passes the frozen RTX profile, cancellation, RAM, VRAM, queue, and time ceilings. |
| Selection-procedure and fixed-candidate estimands reported separately | **Pass** | Both are independently named in `config/e1_experiment_protocol.yaml`, `config/statistics_protocol.yaml`, and version-5 evidence. |
| Sparse/tied evidence receives Provisional status | **Pass** | All version-5 contrasts have zero nonzero pairs; E1S-R is labeled `Provisional primary`, with `acceptance_claim: false`. |
| Full-run projection uses headroom-adjusted capacity | **Pass** | The mixed target-RTX profile uses `C_admit`; the largest 70,400-request workload is below `C_admit=78,697` and projects to 24,788.63 seconds, below 27,540. |

The historical top-level status strings inside
`config/e1_feature_manifests.yaml` and `config/m0_launch_spec_q3vl30.json` are
part of hash-frozen run inputs and are intentionally not rewritten while the
run is active. Current authoritative status is recorded in
`config/e1_experiment_protocol.yaml`, `config/experiment_registry.yaml`,
`config/operational_primary.yaml`, and this audit.

## Remaining closure action

Download the already-running counterbalanced whole-run artifact, validate it
with `scripts/validate_e1_whole_run.py`, freeze its hashes, and update the
prospective decision record. This is the only incomplete Phase 1 item.
