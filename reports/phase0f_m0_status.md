# Plan 8 Phase 0F/M0 status

Date: 2026-09-09

Phase 0F/M0 passes its exit gate. The model choice is explicitly provisional;
E1 must test behavior and can replace it prospectively without rewriting this
viability result.

## Evidence and representation foundation

- `FrameData.frame` is handled as an ordered temporal sequence; production has
  no upstream `layers` accumulation.
- Frames are packed immediately as contiguous `uint8`. Versioned grid and
  sequence SHA-256 values, exact decoding, and corruption checks make every
  round trip byte-verifiable.
- T0-T3 retention is bounded. T0 is committed before optional storage; storage
  failure leaves the current frame, legal actions, counters, and legal play
  available.
- Evidence availability distinguishes `exact`, `summarized`,
  `omitted_capacity`, `evicted_pressure`, `unavailable_storage`, and `corrupt`;
  loss never silently becomes an empty observation.
- R and toggleable E0F F are independently constructible. R excludes
  intermediate frames and engineered F features. Coordinate fixtures cover
  row/column scene space, x/y display space, and unreliable-transform blocking.

## Target-RTX profiles

All runs used the same offline vLLM 0.19.0, Torch 2.10.0+cu128, Transformers
4.57.6 stack on an observed NVIDIA RTX PRO 6000 Blackwell Server Edition with
97,887 MiB. Artifact hashes were computed after timing so hashing did not warm
the cold-load page cache.

| Candidate | Cold load | First-token p95 | Concurrent throughput | Cancellation | Peak VRAM | Peak RAM | Mounted artifact | 8,800-call projection |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.8 27B FP8 / low | 332.25 s | 22.12 s | 300.58 tok/s | 0.309 s | 86.82 GiB | 10.03 GiB | 28.77 GiB | 5,014.06 s |
| Qwen3-VL 30B-A3B FP8 / instruct | 223.17 s | 23.40 s | 933.73 tok/s | 0.027 s | 72.21 GiB | 13.55 GiB | 60.09 GiB | 762.49 s |
| Qwen3-VL 8B FP8 / instruct | 191.14 s | 23.19 s | 861.69 tok/s | 0.027 s | 38.52 GiB | 8.75 GiB | 19.74 GiB | 942.10 s |

The projection is not the earlier one-request-per-game estimate. It uses the
production ceiling of 110 games x 80 actions x one model call/action = 8,800
requests, concurrency eight, the observed eight-request p95 (therefore the
sample maximum), and a 1.25 safety factor. Each candidate remains below both
the 19,800-second model-service allowance and 27,540-second operational target.

Raw records:

- `reports/m0_profiles/m0-q38-low.json` — private kernel version 7
- `reports/m0_profiles/m0-q3vl30-instruct.json` — private kernel version 1
- `reports/m0_profiles/m0-q3vl8-instruct.json` — private kernel version 1

## Provisional selection

- Primary: `M0-Q3VL-30B-A3B-FP8`. It has the best measured throughput and
  bounded projection while retaining about 24.5% VRAM headroom.
- Fallback: `M0-Q3VL-8B-FP8`. It has the smallest mounted artifact and about
  59.7% VRAM headroom while remaining fast enough for the full call ceiling.
- Not selected: `M0-Q38-27B-FP8`. It fits, but uses about 90.8% of VRAM, has the
  slowest projection, and emitted a nonfatal FLA layout warning that E1 would
  have to clear with behavioral evidence.

This is a viability decision, not a claim that the 30B model solves more games.
E1 compares policy behavior under the frozen primary and fallback contracts.

## Gate evidence

- Phase 0F/M0 focused tests: 20 passing, including explicit persisted-corruption
  reporting and continued legal action selection after storage degradation.
- Full repository regression suite: 63 passing, run by
  `make validate-m0-exit`.
- Machine gate: `scripts/validate_m0_exit.py` checks all three immutable hashes,
  target GPU identity, package pins, public offline mounts, 5% VRAM reserve,
  cold-load allowance, cancellation bound, full call projection, and distinct
  primary/fallback selection.

The public wheelhouse is used as a mounted Kaggle input and is not redistributed
by this repository. Runtime-use review passes for M0; an exact dependency-
closure review remains required before redistributing that bundle in a release.
