# Phase 1 hierarchical decision

Date: 2026-09-12

Status: Phase 1 complete with operational label `Provisional primary`. This is
an operational selection, not an acceptance, superiority, or generalization
claim. The counterbalanced whole-run experiment passed its frozen execution and
validation gates, but zero nonzero blocks leave every factorial effect
provisional.

## Hierarchical decision

1. E0 correctness and transaction safety pass. The deterministic E0 controller
   remains the legal fallback for model-startup and proposal failures.
2. The frozen Duck and Reki published references are inventory controls only.
   Duck cannot run faithfully under the required Python boundary, and Reki's
   captured wheelhouse has unknown licensing. Their public scores are not
   substituted for project reproductions.
3. All four same-model E1 cells completed under the frozen model, engine,
   reasoning mode, feature manifest, and `minimum_fair_v1` queue. Version 5 is
   retained as descriptive shared-resource evidence because it has only one
   non-counterbalanced workload block.
4. Every version-5 cell scored 0.0. The registered tie-break selects E1S-R, the
   least complex one-request R cell, with operational label
   `Provisional primary`. No factorial effect is accepted.
5. The counterbalanced whole-run completed both reverse-order blocks with fresh
   treatment runtimes in 23,344.80 seconds. Every cell mean and factorial
   contrast was 0.0; with zero nonzero blocks, the frozen rule keeps all effects
   and E1S-R provisional.
6. The production notebook now mounts the exact model and vLLM wheelhouse,
   starts the local model server, requires a real completion canary before any
   competition call, routes every proposal through the bounded queue, enforces
   the 27,540-second full-lifecycle runtime envelope with a 600-second
   finalization reserve, and degrades to E0 without retry when model service or
   a proposal is unavailable.

## Controls and comparison classes

| Entry | Class | Reproduction status | Production status |
|---|---|---|---|
| Duck Qwen3.8 Flash Next NVFP4 | Frozen published workspace control | Unavailable: Python isolation and distribution licensing not closed | Disabled |
| Reki Gemma 4 31B | Frozen published structured reference | Unavailable: captured wheelhouse license unknown | Disabled |
| E1C-F | Adapted Duck-style safe-operation substitute | Version 5 complete; not a faithful or normalized Duck reproduction | Eligible, not selected |
| E1S-R | Project structured fallback | Version 5 complete; not a Reki reproduction | **Provisional primary** |
| E0 | Deterministic legal controller | Phase 0 parity and load fixtures pass | Fallback |

The four-cell comparison mode is `shared_resource_whole_run`: game clients in
one treatment share the inference service and scheduler. Version-5 per-game
contrasts and cross-validation are diagnostic. The completed corrective design
uses paired complete-workload blocks as both randomization and uncertainty unit.

## Completed model/runtime table

All model rows were measured on NVIDIA RTX PRO 6000 with offline vLLM 0.19.0.

| Candidate | Role | Cold load | First-token p95 | Throughput | Cancel | Peak VRAM | Peak RAM | Offline artifact | Conservative projection | Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Qwen3.8 27B FP8 / low | Dense control candidate | 332.25 s | 22.12 s | 300.58 tok/s | 0.309 s | 86.82 GiB | 10.03 GiB | 28.77 GiB | 5,014.06 s / 8,800 calls | Not selected |
| Qwen3-VL 30B-A3B FP8 / instruct | M0 and E1 model | 223.17 s | 23.40 s | 933.73 tok/s | 0.027 s | 72.21 GiB | 13.55 GiB | 60.09 GiB | 762.49 s / 8,800 calls | Selected model |
| Qwen3-VL 8B FP8 / instruct | Resource fallback | 191.14 s | 23.19 s | 861.69 tok/s | 0.027 s | 38.52 GiB | 8.75 GiB | 19.74 GiB | 942.10 s / 8,800 calls | Model fallback |
| E1S-R mixed prompt | Operational policy | 236.18 s shared profile load | 0.455 s request p95 | `C_admit=278323` | 0.187 s service recovery | 72.21 GiB | 13.61 GiB | 60.09 GiB | 7,702.21 s / 8,800 calls | **Provisional primary** |
| E1C-F mixed prompt | Highest measured E1 workload | 236.18 s shared profile load | 1.610 s request p95 | `C_admit=78697` | 0.187 s service recovery | 72.21 GiB | 13.61 GiB | 60.09 GiB | 24,788.63 s / 70,400 calls | Fits, not selected |

`C_admit`, rather than nominal capacity or a best-run mean, is used for the E1
projection. Both 8,800 E1S-R requests and the 70,400-request E1C ceiling are
below their measured headroom-adjusted admission capacities and their projected
totals are below 27,540 seconds.

## Offline dependency bundle

The production bundle is frozen in `config/dependency_manifest.lock` and
packaged by `scripts/build_notebook.py`:

- public Kaggle model
  `qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1`, exact revision and
  tree SHA-256 `052ab27f...ab8627`;
- public Kaggle wheelhouse `driessmit1/arc3-vllm-h100-wheelhouse-v3/1`, with
  frozen SHA256SUMS and index-manifest hashes and all 178 mounted payload files
  verified before no-index installation;
- competition-mounted ARC packages with exact versions and wheel hashes;
- internet disabled, RTX PRO 6000 selected, and only `submission.parquet`
  retained on handled exit.

This closure applies to public Kaggle runtime use. The repository does not
redistribute the wheelhouse; redistribution remains blocked pending transitive
license closure.

## Operational record

- Primary: `E1S-R` / Qwen3-VL-30B-A3B-Instruct-FP8 / vLLM 0.19.0 /
  non-thinking mode.
- Operational status: `Provisional primary`.
- Fallback: E0 deterministic legal action policy.
- Binding: `config/operational_primary.yaml`.
- Generated submission: `notebooks/submission.ipynb`.
- Selection evidence SHA-256:
  `f186192705e061734bf7bb93dd64f2afbe2f5538eaf828a04a123fca9515eb9d`.
- Mixed-prompt resource evidence SHA-256:
  `e83f750635fc862bba8138229c97bcd8c5dd7ae56e4a99dc31a48ce9acf157a7`.
- Counterbalanced whole-run evidence SHA-256:
  `7ca485b51f38955ca73b148e3396426f09ea6ade911c170a2dc203f6ef5bb245`.

The completed two-block result confirms the existing primary without changing
its label: E1S-R remains `Provisional primary`. It does not retroactively convert
version 5 or the final selection into an accepted causal result.
