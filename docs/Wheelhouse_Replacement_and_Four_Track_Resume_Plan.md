# Offline wheelhouse replacement and four-track research resumption

Prepared: October 3, 2026 (America/Los_Angeles)

Status: planning handoff only. This document does not approve a source package,
authorize compute, reserve an attempt, authorize an upload, or authorize a launch.

## 1. Objective and immediate decision

Replace an inaccessible dependency source with a reproducible, team-controlled
offline package bundle. Validate that bundle before resuming the four research
workstreams. Keep the selected model and experimental designs unchanged wherever
possible; record and review every unavoidable runtime change.

Do not launch the existing notebooks merely to see whether the dependency works.
Do not reuse a consumed reservation or assume unused time from an earlier attempt
is available for a new one.

Proposed sources:

- Candidate packaging reference: [vllm-latest-wheels by damndeepesh](https://www.kaggle.com/code/damndeepesh/vllm-latest-wheels).
- Authoritative vLLM distribution source: [official vLLM 0.19.0 release](https://pypi.org/project/vllm/0.19.0/).
- Final runtime input: a new, explicitly versioned Kaggle package owned by the team/account owner, subject to license review and upload approval.

The candidate is a notebook, not a verified replacement dataset. Its output files,
versions, completeness, and current account access have not been verified here.
The official release provides Linux wheels, but a version label alone does not
establish equivalence to the old wheel or compatibility with its dependencies.

## 2. Handoff context and repository identity

Repository: [dcw06/ARC-AGI-3](https://github.com/dcw06/ARC-AGI-3).

The Mac checkout used to write this document is on `main` at `4275286`. It is older
than the reviewed research work described in the conversation. Do not use this
checkout as proof of the latest runner's implementation or launch readiness.

Synchronization update before publication: local `main` was fast-forwarded to
GitHub's `main` at `f4ee307`. Remote research branches were fetched but not merged
into `main`. The initial drafting revision above is retained for provenance;
branch-specific research locks still require inspection on the receiving machine.

Relevant historical review references from the conversation:

- [bc19919](https://github.com/dcw06/ARC-AGI-3/commit/bc19919): provider-preflight preparation; wheelhouse access remained blocked.
- [9de3a83](https://github.com/dcw06/ARC-AGI-3/commit/9de3a83): earlier authorization/one-attempt launch machinery.
- [84f143c](https://github.com/dcw06/ARC-AGI-3/commit/84f143c): earlier submission/cancellation evidence.

These are historical pointers, not instructions to launch those revisions. Verify
their contents and any newer commits on the receiving computer.

Before implementation, run read-only local checks:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git log -5 --oneline
```

Fetch remote updates as needed, identify the intended research branch explicitly,
and record its full SHA. Preserve uncommitted work. Do not reset, force-push,
blindly merge research branches, or assume `main` contains the latest experiment.
Create a dedicated replacement branch from the agreed base.

Read applicable `AGENTS.md` instructions and the selected branch's current
protocols, locks, accounting records, and review reports before editing.

## 3. Established blocker and what remains unknown

Original input:

`driessmit1/arc3-vllm-h100-wheelhouse-v3/1`

- [Original dataset page](https://www.kaggle.com/datasets/driessmit1/arc3-vllm-h100-wheelhouse-v3).
- [Owner profile](https://www.kaggle.com/driessmit1).
- [Public notebook logs showing historical use of that path](https://www.kaggle.com/code/jeroencottaar/tufa-labs-duck-harness-june-30-milestone-winner/log).

Prior retained checks reported HTTP 403 for dataset metadata/file listing; the
user's browser showed a missing-page message. The owner has been contacted and has
not replied as of this handoff. These observations do not establish whether the
dataset is private, moved, deleted, or otherwise inaccessible.

The earlier attempt remains consumed. Its cancellation, accounting uncertainty,
and historical approval issues must remain recorded, not rewritten by this work.
Confirm the exact disposition from the receiving checkout's retained records.

## 4. Scope: preserve the experiment, investigate the runtime

Initial compatibility targets from the local manifests:

| Component | Existing recorded target |
| --- | --- |
| Python | 3.12 |
| Platform | Target Linux x86-64; verify exact image and ABI |
| vLLM | 0.19.0 |
| PyTorch installed build | 2.10.0+cu128 |
| Transformers | 4.57.6 |
| CUDA family | 12.8 |
| Model | Qwen/Qwen3-VL-30B-A3B-Instruct-FP8 |
| Model revision | d9748a51ae66354c4dad665aab2c71f26cf2c8cd |
| Kaggle model reference | qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1 |
| Target GPU | NVIDIA RTX PRO 6000 |

Local references: [model manifest](../config/model_manifest.yaml) and
[dependency manifest](../config/dependency_manifest.lock). The selected runner's
frozen lock is authoritative for its experiment; investigate discrepancies rather
than copying these summary values blindly.

Keep fixed: model bytes, tokenizer and chat template, policy prompts, action
schema, decoding settings, context limits, scheduler, cache configuration,
environment versions, seeds, episode/action caps, comparison arms, and evaluator.
Cache configuration is experiment-specific; do not impose one setting on all tracks.

The local dependency manifest contains different development and target-runtime
profiles. Do not resolve from whichever profile is easiest to install. Freeze an
explicit inventory for each process: environment worker, supervisor, and model host.

If required package versions conflict, stop the equivalence claim. Propose a new
runtime revision instead of silently upgrading, downgrading, patching, or using
`--no-deps` to conceal a dependency conflict.

## 5. Milestone A: audit and choose exact artifacts

### A1. Inspect the candidate notebook without executing it

Retain its exact notebook version, source hash, output inventory, and acquisition
date. Review all download/install commands, indexes, executable code, patches,
and license information. Never bind to an unspecified "latest" version.

For each candidate wheel, inspect filename, package metadata, dependency
requirements, version/build, Python ABI, operating-system/architecture tags,
size, SHA-256, and upstream provenance.

### A2. Compare with retained original evidence

Search the repository and authorized evidence archives for the full original
requirements lock, wheel index, per-file checksums, installed distributions,
installation logs, and system-library requirements. Do not infer a complete
dependency closure from the three principal package versions.

The local model manifest records this original vLLM wheel SHA-256:

`2d0e5fae45367bdbf111fcad68f4c0f8fdddd2f2fb643e52f0f2daebef7b41cf`

Verify it against retained evidence and compare it with the chosen upstream
artifact. Do not assume that the original was an unmodified official wheel.

Classify every component as byte-identical, changed, missing, or unknown. Record
package/build differences separately from hosting-location differences.

### A3. Freeze a source decision

Prefer verified upstream artifacts. Reuse candidate notebook outputs only if
their provenance, compatibility, and permissions are established. Do not install
the whole candidate bundle and then overwrite vLLM afterward.

If matching wheels are unavailable, document that result. Building from source
or changing the CUDA/PyTorch stack requires a separate reviewed decision and a
new build identity; do not expand into a compiler project automatically.

Deliverables: source audit, exact inventory, original-versus-replacement diff,
and a list of unresolved compatibility/license questions.

Exit gate: enough verified information exists to assemble one coherent package
set, or a specific runtime-change decision is presented to the owner.

## 6. Milestone B: reproducible offline package

Build in a disposable target-compatible Linux environment. macOS can review,
hash, and orchestrate preparation; it cannot certify Linux CUDA execution.
WSL without an NVIDIA runtime can perform CPU/package checks but cannot certify
model startup or GPU cleanup. Check storage and RAM before large downloads.

Create a complete pinned dependency closure with:

- Exact artifact URLs, filenames, versions/builds, sizes, and SHA-256 values.
- Hash-checked requirements and an allowed-file inventory.
- Acquisition recipe, tool versions, and build logs.
- Target Python, architecture, glibc, system-library, CUDA and driver assumptions.
- License notices and redistribution review for all included components.
- Explicit separation of downloaded packages from dependencies supplied by the target image.

Acquisition may use an approved network-enabled CPU environment. Installation
verification and the later target experiment must be offline. Network-enabled
package acquisition is not permission for a GPU session.

The old manifest says redistribution review is pending. Runtime-use permission
does not automatically authorize copying the whole old bundle into a new dataset.

Exit gate: every required artifact has an identified source and checksum, no
unbounded resolver or network fallback remains, and distribution is permissible.

## 7. Milestone C: clean offline installation and local rehearsals

Install in a fresh environment with networking disabled, not into the developer's
working environment. Use the reviewed complete requirements with `--no-index`,
`--find-links`, and `--require-hashes`. Inspect actual installed distribution
versions and import paths; run `pip check`.

Test:

1. Successful installation without using a warm pip cache or undeclared packages.
2. Missing, corrupt, duplicate/conflicting, and wrong-platform artifact rejection.
3. Interrupted installation and bounded cleanup.
4. Correct tokenizer/chat-template loading and exact request/token fixtures.
5. Available server flags, API schema, metrics expectations, and dependency imports
   where CPU inspection is meaningful.
6. Runner/supervisor operation with a scripted model: normal completion, invalid
   outputs, failed/unknown dispatch, timeout, cancellation, monitor failure,
   storage exhaustion, and incomplete-result reporting.
7. Independent evaluation of retained evidence and rejection of forged success
   flags or inconsistent accounting.
8. Instrumentation invariance: scripted requests/actions match direct execution.

Record unsupported GPU-dependent checks as unverified, not passed. Account for
runtime assets downloaded lazily by tokenizers or kernel libraries; include them
or establish that the frozen configuration does not need them.

Exit gate: clean offline installation and local fault tests pass with retained
evidence. No claim of target GPU compatibility yet.

## 8. Milestone D: reviewed package and controlled upload

Prepare a team-owned, explicitly versioned Kaggle dataset after license and owner
approval. Do not upload credentials, model weights, unrelated game artifacts, or
other people's private files. Model weights remain a separate frozen input.

Produce new versioned dependency/configuration records and a GPU-disabled review
notebook. Preserve historical manifests and locks; avoid broad search-and-replace
of old dataset references. Update active consumers deliberately and inventory them.

The notebook must:

- Gate execution before GPU/model startup and before installing non-standard dependencies.
- Verify exact attached file inventory/hashes before installation.
- Bind model files, source, protocol, dependency bundle, and budget records.
- Count installation and startup from the first-cell clock.
- Use existing bounded evidence/logging and process-ownership mechanisms.
- Refuse launch without explicit authority for the exact package and attempt.

After upload approval, verify metadata access, actual file access, hashes, and
notebook attachment. Handle every provider `invalid*Sources` result as failure,
even when the HTTP submission response is 200. Never treat publication as execution
approval or automatically retry an ambiguous submission.

Exit gate: reviewed source and package are reproducible from a fresh checkout,
provider inputs are accessible, and the review notebook still cannot launch without authority.

## 9. Milestone E: separately authorized GPU compatibility smoke test

Purpose: verify the new runtime, not solve games or evaluate treatments.

Proposed budget for review, not authorization:

| Item | Proposed bound |
| --- | --- |
| Attempts | One; no automatic retry |
| Provider reservation | At most 3,600 seconds |
| Internal lifecycle deadline | 3,300 seconds from first-cell start |
| Latest inference admission cutoff | 3,000 seconds, earlier if worst-case call/cancellation would overrun |
| Cleanup reserve | At least 300 seconds inside the internal deadline |
| Model requests | At most 12 total, including canaries and fault probes |

Reassess feasibility from installation evidence before freezing these values.
Freeze per-call deadlines, startup limits, cancellation allowances, and numeric
RAM/VRAM/scratch/evidence/log limits in the actual protocol. These are unresolved
launch prerequisites until chosen and reviewed; the table alone is not a full lock.

Use the same selected model, quantization, target GPU, context configuration,
and experiment-required APIs. Predeclare the exact requests and expected checks.
Include short schema-constrained responses, a representative long prompt,
tokenizer/server count parity, and the required metrics/cache behavior. Include
image support only for experiments that actually require it.

Validate cancellation with a bounded probe; retain evidence that work stopped on
the server rather than assuming a closed client connection proves cancellation.
Continue monitoring through model/worker termination and verify owned groups and
GPU processes are gone. Do not terminate unrelated processes.

Require:

- Correct offline installation, model/tokenizer hashes, and GPU UUID binding.
- Required response interfaces and token accounting work.
- No undeclared downloads or silent package substitution.
- Timings and resource limits are met, including startup and finalization.
- Timeout/cancellation/cleanup receipts are consistent with observed process state.
- An independent evaluator passes on the retained result, not just a success flag.

Keep internal elapsed time, provider-reported runtime, account quota changes, and
exact charged GPU usage distinct. Unknown billing remains unknown. Retain failed
and interrupted attempts and do not release reservations by inference.

A passing smoke test is not a solving result, numerical-equivalence proof,
capacity certification, or Phase 4 closure.

## 10. Milestone F: resume the four research tracks

Use the latest reviewed protocol for each track. The summaries below describe
research intent, not a replacement for frozen arms, thresholds, or sample sizes.
All previously exposed development cases remain labelled as such.

| Track | Research question | Work possible before GPU readiness | Later model experiment |
| --- | --- | --- | --- |
| 1: Hypothesis testing | Does a structured hypothesis/probe/update procedure improve evidence-grounded decisions and level progress? | Validate evidence citations, action legality, statement handling, denominators, budget caps and CPU trajectories. | Run the registered baseline/treatment comparisons under one runtime; separate behavior change from solving. |
| 2: Memory | Can useful prior evidence survive delay/context limits and be retrieved accurately without invented claims? | Verify faithful-writer fixtures, token budgets, answer keys, delay groups, withheld separation and scorer. | Run the registered reader/retention/retrieval arms; report comprehension, forgetting and unsupported claims separately. |
| 3: Stagnation | Can a detector and intervention break ineffective loops without disrupting useful continuation? | Check observer replay, display-driven novelty/oscillation, false interruptions, terminal handling and reflection placement. | Run registered continuation/intervention episodes; report loop escape, reliability and level completion separately. |
| 4: Change versus progress | Can the model distinguish visible effects, confirmed progress and justified causal claims? | Audit transition fixtures, independent labels, unknown/failed outcomes, no-op versus reversion and balanced question sets. | Run frozen questionnaire arms; score accuracy, validity, over-claims and over-hedging separately. |

Do not infer readiness from old passing test counts. Rerun each track's relevant
tests against its actual successor package. Preserve the frozen unmasked condition
unless a new protocol explicitly approves masks; adding game-specific masks is
not part of dependency repair.

For any track using baseline/treatment comparisons, both arms must use the same
replacement runtime. Do not compare a new treatment with an old-runtime baseline
and attribute differences solely to the treatment.

Choose the first research run by readiness and information value: smallest
reviewed workload, fewest remaining runtime assumptions, and a result that can
inform other tracks. A questionnaire may qualify, but no track is automatically
approved by this document. Do not start all four as an environment test.

Local development can proceed in parallel on separate branches. GPU concurrency
requires explicit per-run authorization and account/quota coordination; this
handoff grants neither. Each run gets its own frozen package, reservation, attempt
claim, result archive, independent evaluation and accounting disposition.

## 11. Suggested implementation deliverables

These are proposed new artifacts, not files claimed to exist already. Fit them to
the receiving branch's conventions and reuse reviewed machinery where practical.

| Deliverable | Required content |
| --- | --- |
| Source audit | Candidate notebook version, upstream identities, permissions, unresolved items |
| Dependency diff | Old/new artifact hashes, versions, build metadata and comparability classification |
| Bundle recipe and lock | Complete offline inventory, pinned acquisition recipe and integrity checks |
| Local validation report | Clean-install results, fault tests, import paths, tokenizer fixtures, limitations |
| Runtime smoke protocol | Exact requests, criteria, resource limits, deadlines and separate proposed budget |
| GPU-disabled review package | Notebook, source lock, model/dependency bindings and authority refusal tests |
| Provider preflight | Fresh input-access and attachment verification tied to exact package/version |
| Result and accounting archive | All outcomes, logs, independent verdict, provider receipts and uncertainties |
| Per-track successor notes | Changed runtime bindings, unchanged scientific design, separate launch gates |

## 12. Reference links

- [Repository](https://github.com/dcw06/ARC-AGI-3)
- [Candidate packaging notebook](https://www.kaggle.com/code/damndeepesh/vllm-latest-wheels)
- [Official vLLM 0.19.0 files and checksums](https://pypi.org/project/vllm/0.19.0/)
- [Versioned vLLM GPU installation documentation](https://docs.vllm.ai/en/v0.19.0/getting_started/installation/gpu/)
- [vLLM v0.19.0 source](https://github.com/vllm-project/vllm/tree/v0.19.0)
- [Selected model upstream page](https://huggingface.co/Qwen/Qwen3-VL-30B-A3B-Instruct-FP8)
- [PyTorch CUDA 12.8 wheel index](https://download.pytorch.org/whl/cu128)
- [pip secure installation guidance](https://pip.pypa.io/en/stable/topics/secure-installs/)
- [pip download documentation](https://pip.pypa.io/en/stable/cli/pip_download/)
- [Kaggle dataset documentation](https://www.kaggle.com/docs/datasets)
- [Kaggle API documentation](https://www.kaggle.com/docs/api)
- [Local WSL setup notes](WSL_ENVIRONMENT.md) — historical machine-specific paths, not proof of current setup.
- [Windows transfer notes](WINDOWS_TRANSFER.md)

## 13. Copy/paste task for the receiving coding assistant

> Read this handoff and the applicable repository instructions. First report the
> exact branch/commit, working-tree state, latest dependency and experiment locks,
> and available Linux/CPU/GPU capabilities without displaying credentials. Start
> with a read-only audit of the original retained wheel inventory, the pinned
> candidate notebook, and official vLLM 0.19.0 artifact metadata. Produce a precise
> dependency diff and implementation proposal. Do not assume version equality
> means build equivalence. Identify missing evidence and incompatibilities rather
> than silently changing dependencies. Preserve historical experiments and
> accounting. Do not install into my working environment, make large downloads,
> upload a dataset/notebook, reserve compute, invoke a model, submit a scored run,
> or launch GPU work without the corresponding explicit approval. After review,
> implement reproducible offline packaging and local checks in an isolated branch.

Immediate next milestone: finish the source audit and dependency diff. The next
GPU milestone, if separately approved, is runtime compatibility only; research
resumption follows its evaluated result.
