# Semantic-SAM one-image GPU smoke: attempt 1 submitted

After the owner's instruction to launch, the final private r2 package passed
fresh read-only preflight and was submitted **once**. Provider status is RUNNING;
no completed model load, inference or mask result is claimed yet.

| Gate | Retained evidence |
|---|---|
| Implementation | `f501e92`; bounded GPU wrapper and source builder; 120 Linux CPU tests passed without failures or skips |
| Final private snapshot | Two byte-identical builds and an independent stdlib artifact/source/embedded-payload audit |
| Local staging | Frozen r2 rehearsal passed in 166.296 seconds; no inference; owned environment removed |
| Owner instruction | Recorded verbatim with the one-image scope and exact generated review lock; no claim of personal review of an unseen hash |
| Account and quota | Account identity matched; at least one hour of unreserved GPU quota available |
| Target/source preflight | New notebook target absent; dataset private version 1, no collaborators, all 21 filenames/sizes unchanged |
| Image | Immutable pin matches the retained completed provider CPU run |
| Submission | One SaveKernel call; version 1; no provider error or rejected sources; no automatic retry |
| Saved notebook | Exact authorized source, private, internet/TPU off, intended attachment and pinned image |
| Saved accelerator configuration | `NvidiaRtxPro6000`; actual identity must additionally pass the worker's runtime census before model loading |
| Current status | RUNNING |

The frozen scope is one RTX PRO 6000, requested session timeout 3,600 seconds,
worker lifecycle 3,300 seconds, work cutoff 3,000 seconds, and a 300-second
cleanup/finalization reserve. It covers sc25 / board-06 in seeded and automatic
mode at granularity 1. No new MolmoPoint generations, model HTTP requests, game
actions or scorecards are authorized. Provider overhead can extend beyond one
hour under the retained session/worker policy.

The single-use claim was consumed immediately before the actual send. Every
previous provider attempt, completed CPU check, unlaunched draft and local
refusal remains preserved. No failure triggers another submission.

Private notebooks, approvals, exact locks, reservation/claim, preflight evidence,
raw source and provider receipts remain git-ignored. After termination, collect
read-only, verify provider COMPLETE, exact saved source/settings, both independently
pinned mounted manifests, owned-group/GPU cleanup, environment removal, under-limit
finalization and output/witness/marker hashes. Then independently replay and
inspect masks on the bound board before using externally frozen references.
This is a one-image runtime smoke, not the six-board comparison.
