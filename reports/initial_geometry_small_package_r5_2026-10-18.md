# Initial-geometry smaller successor r5 — October 18, 2026

**Completed and independently validated:** [results](initial_geometry_r5_attempt3_results_2026-10-18.md).
Neither arm completed a first level (0/6 each); all 12 episodes reached the
24-action cap. The notebook lifecycle was 537.543 s on an RTX PRO 6000,
with verified cleanup. This attempt and both earlier uncertain attempts remain
consumed. The preparation/submission record below is retained.

The submission-size repair is implemented. The r5 review notebook is
**343,350 bytes**, down from r4 attempt 2's **57,967,905 bytes** (about 99.4%
smaller). The actual SDK JSON body for the authority-free review is
**344,232 bytes**. The owner subsequently approved r5; one fresh authorized
submission succeeded with HTTP 200 and created version 1. Kaggle reported
RUNNING immediately afterward and later COMPLETE. Both uncertain r4 attempts
remain consumed and preserved. The completed run's accelerator, evidence and
independent replay are now verified in the results report.

| Package item | r5 |
|---|---|
| Private review-lock SHA256 | `fe5d0ddaa3ffceeeb0e548c0c186eb24ccab5bd2ac649b2f84b0a818ca3299fb` |
| Payload ZIP | 254,992 bytes; 87 pinned members plus the payload manifest |
| Game dependencies | Same 31 exact wheels, now resolved from the already attached competition's `arc_agi_3_wheels` directory |
| Embedded game content | Unchanged game receipt, hash-pinned requirements and six development-game sources; no wheel binaries |
| Dataset attachments | Unchanged publisher wheel dataset v1 and private model dataset v1; no additional upload |
| Source/use/compute approval for r5 | Recorded from the owner's “Approve gpu run” reply to this exact package, under the unchanged reviewed scope; old authority and attempts preserved |

## What changed

The runtime resolves exactly one of Kaggle's two known competition mount
layouts. It refuses missing or ambiguous mounts, redirected symlink paths,
unexpected wheel files and altered wheel sizes or hashes. Hashing is streamed
with lifecycle deadline checks. All 31 wheels verify against the original
externally pinned game receipt before any dependency installation. The existing
isolated installer still uses `--no-index --require-hashes` against the unchanged
requirements lock.

The review lock also retains the wheel inventory. Read-only preflight now
compares all 31 competition filenames and sizes with it, and the independent
evaluator requires the mounted-wheel verification receipt. Filename/size
preflight does not replace the runtime byte check.

Package construction refuses review notebooks over a conservative local
900,000-byte source budget. SDK preparation and the final send boundary refuse
JSON bodies over 1,000,000 bytes, including late-bound authority data. These are
local prevention limits, not assertions about Kaggle's undocumented exact limit.
The real old attempt-2 request is now refused locally without sending it.

## Scientific and operational scope

The protocol, inputs, original game receipt and provider request fields are
unchanged from r4. An offline comparison also confirmed identical policy,
episode, prompt/token, worker, process/deadline, engine-bridge, geometry and
episode-audit sources. The only runtime JSON addition is the competition wheel
source binding. Source changes concern dependency resolution, packaging,
verification and the CPU rehearsal path.

| Proposed next attempt | Ceiling, unchanged |
|---|---|
| Accelerator and attempts | Exactly one RTX PRO 6000; one fresh attempt; no automatic retries |
| Time | Requested Kaggle timeout 3,600 s; worker 3,300 s; work cutoff 3,000 s; cleanup reserve 300 s |
| Generations / HTTP requests | At most 289 / 300 |
| Offline actions including resets | At most 300 |
| Local scorecards | At most 12 |
| Online game calls / leaderboard submissions | Zero |
| Privacy | Account-only notebook and raw outputs; sanitized summaries only; internet and TPU off |

The accepted time policy still allows provider allocation, mounting, setup and
GPU release to extend total elapsed time beyond one hour. Preparation alone
authorized no attempt; the subsequent owner approval authorized exactly one.
Current quota and requested shape do not prove actual allocation; the runtime
retains its exact accelerator refusal.

## Validation

| Check | Result |
|---|---|
| Local Linux CPU regressions, network isolated except loopback | 81 passed; zero failures, errors or skips |
| Mounted dependency regressions | Both provider layouts; absent/ambiguous mount; changed source; missing, extra, same-size altered and symlinked wheels; streaming deadline; changed game; sealed ZIP inventory; request-size refusal; preflight inventory refusal |
| Current provider catalogue | All 31 competition wheel filenames and sizes match; no download or provider write |
| Read-only r5 preflight | Seven checks pass at 16:25:19 UTC: account, quota, target absence, dataset versions, model privacy, existing inventories and competition wheel inventory |
| Review notebook refusal | Stops before extraction, installation or GPU queries with authority unset |
| SDK preparation | Exact settings and unchanged attachments validated offline; 344,232-byte body |
| Prior attempts | Their retained files and r4 lock hash checked unchanged |
| Exact sealed payload CPU rehearsal | Fresh offline installation from the simulated mount; 25 scripted HTTP completions, 12 episodes, 24 dispatches plus 12 resets; all 12 independent real-engine replays pass |
| Extracted-package tests | 27 passed; no failures or skips; module paths explicitly checked |
| Corrected CPU lifecycle | 114.67 s; all owned process groups absent; temporary interpreter/mount removed; extracted pinned files unchanged |
| Deterministic rebuild | New private snapshot reproduces r5 byte for byte |

The exact-payload CPU check uses a **simulated provider mount** populated with
the original verified wheel bytes. It is not a byte verification of a current
Kaggle mount and does not establish CUDA/vLLM compatibility or model performance.
The CPU processor is Transformers 4.57.1; the earlier separate pinned 4.57.6
prompt audit remains retained and is not represented as rerun here.

The first CPU harness completed its fresh installation, 12 scripted episodes
and 12 independent engine replays, then failed its final test invocation because
Python resolved the main checkout's test package. Its logs are preserved. The
corrected harness explicitly selects and checks the extracted package's test
paths and passes, including fresh installation and all episodes/replays. It
does not change the sealed notebook or review lock. The deliberate hard-kill
fault test emits Python's semaphore-recovery warning, as in the retained r4
suite; the child-absence assertion passes.

| Retained private receipt | SHA256 |
|---|---|
| `linux-checks-r1.json` | `8e8b1a6a17d3185797b297f9d0accd6dbc1fe79a821ada76965a4447a9cfee53` |
| `build-r5.json` | `7f693b29b0d384627f2ff28ba7175a725635b4b621bb9dfb3accda121d62d283` |
| `CPU-lifecycle-r5-r2.json` | `627830efd82414857cef8709c6adef324b034fc08b52dd3d4d5f3e862ff10e48` |
| `connected-CPU-rehearsal-r5-r2/connected-receipt.json` | `00907482de322d252fa2593a685e747313708811435e5bbc5ab40957e162ce03` |

## Private handoff

The exact private package is in the main workspace at:

```text
.cache/github-review/initial-geometry-small-package-2026-10-18/private-live-review-r5/
```

It contains the review notebook, lock, runtime/settings and scoped-use draft.
The surrounding directory retains the build, inventory, source comparison,
read-only preflight and CPU receipts. Private raw inputs and evidence are not
published with this report.

## Owner-authorized submission

| Stage | Result |
|---|---|
| Owner statement | “Approve gpu run”, replying to the exact r5 lock and request for fresh approval; original scope/ceilings retained verbatim as context |
| Fresh preflight | All seven checks pass at 17:05:01 UTC, including target absence and all 31 competition wheel filenames/sizes |
| Authority | New source/use/compute records bound to r5, the protocol and scoped-use evidence |
| Reservation / claim | Fresh, exclusive and consumed; neither r4 attempt reused |
| Submission | Exactly one SaveKernel; HTTP 200; version 1; no provider error or invalid source |
| Saved package | Pulled source/authority, private setting, pinned image, RTX PRO 6000 request and attachments match the approved package |
| Provider echoes | Dataset version labels and session timeout were not echoed; exact versioned sources and requested timeout remain bound at send time |
| Initial status | RUNNING; actual GPU allocation and study results still pending |

The smaller package crossed the submission boundary successfully. This resolves
the observed SSL upload failure for this send, not the untested live study.
The runtime still must verify mounted wheel bytes and the exact accelerator.
Raw approval, preflight, claim, provider response, HTTP event and saved-source
records remain private under `gpu-execution-r5-attempt3/`. No automatic retry
or subsequent submission is authorized. Read-only collection and independent
evaluation are complete; their records remain private.
