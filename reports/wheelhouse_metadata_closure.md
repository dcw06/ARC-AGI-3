# Wheelhouse metadata closure (metadata only)

Generated offline by `scripts/check_wheelhouse_metadata.py analyze` from the retained acquisition record `reports/wheelhouse_metadata_acquisition.json.gz`. No wheel was requested, downloaded, installed or executed.

## Answers

| Question | Answer |
|---|---|
| Exact wheels located upstream (filename and SHA-256) | 174 of 174 |
| Wheels with hash-verified core metadata | 174 of 174 |
| Dependency closure of the install pins complete? | **yes** (`metadata_closure_complete`) |
| Wheels required by the closure / unrequired | 174 / 0 |
| glibc required by the closure | 2.34 (target lower bound 2.34) |
| Package or build changes needed? | none indicated by metadata |
| Non-wheel bundle files missing (new bundle identity required) | 5: `README.md`, `dataset-metadata.json`, `pip-resolve-report.json`, `requirements.in`, `requirements.lock` |
| Requests made / wheel URLs requested | 348 / 0 |

## Evidence validation (before analysis)

Retained acquisition bound to the verified inventory: **yes**. Entries checked: 174; recomputed as verified: 174; validation problems: 0. Stored located/verified flags are not trusted: exact upstream hashes, artifact URLs, metadata hashes, metadata URLs and metadata identity are recomputed. Offline validation checks the retained evidence for internal consistency and against the verified inventory. It cannot independently prove what network activity took place; request counters are checked only for consistency with the retained entries.

## Established versus not established

| Level | Status |
|---|---|
| Metadata verified | established for all wheels |
| Wheel bytes verified after download | not established (no download) |
| Offline installation passed | not established |
| GPU runtime passed | not established |

## Target (declared, not the host)

Python 3.12 (ABI `cp312`, set explicitly), Linux x86-64, glibc ≥ 2.34, 933 compatible tags. Install pins: `vllm==0.19.0`, `torch==2.10.0`, `transformers==4.57.6`, `numpy==2.2.6`. Marker values: `implementation_name=cpython`, `implementation_version=3.12.13`, `os_name=posix`, `platform_machine=x86_64`, `platform_python_implementation=CPython`, `platform_release=6.12.90+`, `platform_system=Linux`, `platform_version=#1 SMP Sat May 30 15:40:53 UTC 2026`, `python_full_version=3.12.13`, `python_version=3.12`, `sys_platform=linux`.

## Unresolved and diagnostics

- **Missing dependencies:** 0
- **Conflicting constraints:** 0
- **Required wheels without verified metadata:** 0
- **Problems:** 0
- **Pre-release versions accepted:** 2
  - `{"available": "4.5.0.dev0", "required_by": "flashinfer-python==0.6.6", "requirement": "nvidia-cutlass-dsl>=4.3.4"}`
  - `{"available": "4.5.0.dev0", "required_by": "quack-kernels==0.4.1", "requirement": "nvidia-cutlass-dsl>=4.4.2"}`
  - These are the only candidates in the inventory. An installer accepts a pre-release when no final release satisfies the specifier (PEP 440; `packaging` `SpecifierSet.filter` semantics), which is how an offline `--no-index` install from this set resolves them. They are reported, not counted as conflicts.
- **Requested extras not provided:** 0

**Unrequired wheels (0)** — reported, not removed; each needs a decision on whether it serves a runtime feature or is a historical extra:


## Redistribution questions

Distributions whose metadata declares a proprietary licence (18): `nvidia-cublas-cu12`, `nvidia-cuda-cupti-cu12`, `nvidia-cuda-nvrtc-cu12`, `nvidia-cuda-runtime-cu12`, `nvidia-cudnn-cu12`, `nvidia-cudnn-frontend`, `nvidia-cufft-cu12`, `nvidia-cufile-cu12`, `nvidia-curand-cu12`, `nvidia-cusolver-cu12`, `nvidia-cusparse-cu12`, `nvidia-cusparselt-cu12`, `nvidia-cutlass-dsl`, `nvidia-cutlass-dsl-libs-base`, `nvidia-nccl-cu12`, `nvidia-nvjitlink-cu12`, `nvidia-nvshmem-cu12`, `nvidia-nvtx-cu12`. Every wheel still needs licence and redistribution review before any team-owned upload; metadata licence fields are not a legal review.

## Not established by this check

- wheel bytes verified after download
- offline installation
- GPU runtime
- exact target glibc and driver (only a lower bound is known)
- torch runtime build 2.10.0+cu128 (metadata reports 2.10.0; the runtime build is in the wheel, not its metadata)

The exact artifacts a later, separately approved download would acquire are listed in `reports/wheelhouse_metadata_closure.json` under `next_download` (filename, upstream URL, size, SHA-256).
