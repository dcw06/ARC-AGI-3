# V7 split-environment pilot: implementation review

Approval update: the user approved this exact source/protocol snapshot. See
`reports/phase4_v7_source_approval.json` and the separate
[GPU pilot proposal](phase4_v7_pilot_proposal.md). The review findings below
remain the original record; GPU compute is still unauthorized.

The integrated pilot now has separate game and model interpreter paths. The
source, protocol and notebook are frozen for user source approval. They are
not marked approved on the user's behalf, and no GPU time is authorized.

Review artifact: `notebooks/phase4-lifecycle-v7-review-r1/profile.ipynb`.
Source/protocol lock: `notebooks/phase4-lifecycle-v7-review-r1/review-source-lock.json`.
Lock SHA-256: `2ccab9336f3d27d174741f03b437138dd94c682ab449372ed9a0a38f9957e87b`.
The lock binds 248 source/configuration/test/evidence files plus notebook and
metadata hashes. Earlier r1–r5 installation source/artifact bindings still match.

## Implementation

The game interpreter runs game lifecycles, the policy, supervisor and monitor.
It starts one model-side Python process in the supervised worker process group.
That process owns Transformers tokenization, vLLM startup and the existing
tokenizer/server token audit. A Unix socket carries complete requests and
results between the two interpreters. The game-side proxy verifies the request
hash and token counts before retaining each audit record.

The copied model transport/configuration/artifact helpers remove incidental
`arcengine` imports from the model path without changing policy prompts or
inference parameters. The model process still uses the frozen model launch
specification and one audited startup canary. No inference retries are added.

Each transport frame is limited to 1 MiB; there are at most eight active handlers
and 32 queued connections. Oversized, incomplete, expired or mismatched messages
fail rather than being truncated. Admission observes the same cancellation
file and first-cell deadline as the worker. Model children do not detach into
new process groups, so existing group cleanup includes the bridge and vLLM.

## Integrated control review

- Preparation reuses r5's split installer and headless backend. Both environments
  resolve before either install, and each gets its own dependency check.
- Preparation checks model package metadata without GPU work. The independent
  monitor must publish verified readiness before the worker can start the model
  process. That process reruns the passed r5 CUDA/import/isolation contract before
  model loading. Monitoring continues through worker/model-group teardown.
- Compiler, model and plotting caches remain under monitored workload scratch.
  Prepared dependency trees have write bits removed while the pilot runs and
  directory permissions restored only for removal. These interpreter trees are
  explicitly accounted as prepared dependencies outside the 4 GiB mutable
  workload scratch limit; this distinction is part of the new protocol review.
- Existing aggregate/component evidence budgets and lossless telemetry are
  retained. Installation logs/reports are compressed into the same budgeted
  evidence store. An evidence overflow fails the attempt.
- Installation, startup, inference, final evaluation and dependency/source
  removal share the first-cell clock. The supervisor retains cancellation and
  external cleanup deadlines; its process also has an absolute alarm guard.
  The intermediate evaluator result is marked provisional until notebook cleanup.
- Final acceptance requires `evaluation/notebook-result.json`, which binds the
  evaluator result and dependency-cleanup receipt. Missing cleanup, an exception
  or late publication cannot produce a final pass.
- GPU metadata remains disabled. The authority gate requires separate source
  approval, an execution lock, a new 28800-second reservation and its single
  launch claim. None were created by this implementation task.

## Validation

Ten focused tests passed in WSL Python 3.12: concurrent per-request audits,
forged-audit rejection, cancellation/deadlines, oversized frames, model imports
with game packages blocked, read-only dependency permissions, the closed live
gate, executing the frozen review notebook up to that gate, failure/cancellation
cleanup, and final notebook acceptance after cleanup.

The real 110-client local development lifecycle passed from an isolated native
Linux snapshot: 7722 scripted requests, 70.877 seconds, identical request and
action signatures to the archived v3 scripted baseline, and verified cleanup.
This uses scripted completions and injected GPU telemetry; it is not live-model
or capacity evidence. Bridge behavior was tested separately with local sockets.
The earlier run on the Windows-mounted filesystem failed the sampling-gap gate;
that gate was not relaxed. The historical v3 60-second timing verdict remains
failed, while the established 300-second local functional gate passed.

Machine-readable review: `reports/phase4_v7_review.json`.
Portable local lifecycle evidence: `evidence/phase4-v7-local-review.zip`.
The successful target installation basis remains r5, with Python 3.12.13,
Torch runtime 2.10.0+cu128, vLLM 0.19.0, Transformers 4.57.6 and CUDA 12.8.

## Approval and remaining evidence

The concrete approval item is this v7 source/protocol snapshot, including the
process boundary, bridge limits and prepared-dependency accounting above. Source
approval does not authorize spending the separate eight-hour pilot reservation.
The original request explicitly separated freezing approved sources from
authorizing/reserving the GPU pilot; this review preserves that distinction.

No live v7 model startup, end-to-end token audit, performance, server cancellation
or target monitoring run has occurred. A separately authorized single pilot must
establish those facts and reconcile provider usage. Phase 4 and production
certification remain incomplete.
