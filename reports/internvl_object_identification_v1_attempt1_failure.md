# InternVL object identification: consumed attempt 1 failed before installation

October 16, 2026. Saved version 1 is ERROR. One submission, no retry; the single-use
reservation/claim remains consumed and all evidence is retained privately. No new job
was started while collecting or diagnosing this failure.

| Item | Retained evidence |
|---|---|
| Source/configuration | Exact approved notebook, private/offline settings, immutable image, source identities and requested RTX PRO 6000 configuration re-verified after ERROR |
| Failing stage | First GPU identity subprocess: `/opt/bin/nvidia-smi --query-gpu=uuid,name --format=csv,noheader,nounits` |
| Error | Exit 12: NVIDIA-SMI could not find `libnvidia-ml.so` |
| Worker accounting | About 0.0045 seconds before its failure receipt; this is not provider allocation/setup/mounting time |
| Dataset verification / installation | Neither began in this GPU attempt; the prior successful CPU receipts are unchanged |
| Model loading / study generations / game actions | None began; zero study generations and zero game actions |
| Actual allocated GPU | Unverified because the first identity query failed; saved requested shape is not proof of allocation |
| Cleanup | Tracked subprocess group reaped/absent; GPU cleanup explicitly not verified because NVML/identity were unavailable |
| Verdict | Technical failure before study execution; no identification scores or object-recognition conclusion |

The supervisor constructs a fresh child environment and omits the parent's
`LD_LIBRARY_PATH`. That can hide provider-mounted NVIDIA libraries. A CPU-only
reproduction compiled a tiny synthetic shared library: the isolated child failed to
load it without the library search path (exit 1), and loaded it when that path was
retained (exit 0). No NVIDIA library, target model, GPU or provider job was involved.

This supports environment stripping as the likely code issue. The failed attempt did
not retain the parent's actual driver-library search paths, so this evidence does not
exclude an unavailable provider driver/library. Do not call it a confirmed physical
GPU failure or claim the CPU fixture validates the real NVIDIA environment.

Before another run: preserve only the necessary driver-library search paths in the
otherwise isolated environment, retain bounded driver-resolution diagnostics, add the
loader regression, and rebuild/review the changed package. Keep cleanup failure and
unknown hardware fail-closed. A new source hash and fresh one-attempt authorization
would be required; the consumed attempt must never be reset or automatically retried.
The present approved package and operational guards were not edited during diagnosis.

Collection rechecked manifest hashes and the process-log hash recorded in the runtime
receipt. Raw provider logs, failure result, process log, CPU reproduction and collection
manifest stay private. The earlier transient RUNNING observation remains historical.
