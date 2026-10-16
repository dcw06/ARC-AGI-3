# InternVL object-identification probe — design r1, time amendment A1

October 16, 2026. This revision preserves the scientific choices in
[design r1](internvl_object_identification_v1_protocol_r1.md) and replaces only its
whole-job time requirement, as explicitly requested by the owner. R1 is retained.

The owner replaced the enforced one-hour limit for the entire GPU job with a
**requested 3,600-second Kaggle session timeout and a 3,300-second worker limit**,
accepting that allocation, setup, mounting and GPU release may add time beyond
one hour. There is no verified entire-job cap. The owner's verbatim amendment is
retained privately and bound into the live review package. It expressly does
**not authorize a GPU launch**; approval of the exact final review lock remains required.

All other choices remain: the same pinned original InternVL3.5-8B checkpoint;
the same six exposed first-level initial images and prompt; one 448×448 BF16 tile;
six independent greedy generations, each ≤4,096 new tokens (≤24,576 total);
180 seconds per generation; no generation canary, retries, game actions or
scorecards; owner-only notebook/raw outputs and sanitized summaries only.

The 3,300-second worker accounting includes byte verification, isolated installation,
checkpoint loading, generation, process/GPU cleanup, temporary-environment removal
and evidence finalization. Work ends at 3,000 seconds with 300 seconds reserved
for cleanup. Installation is bounded by worker start +900 seconds; model loading
by 900 seconds and the work cutoff. Admission requires more than 180 seconds of
work headroom. Emergency termination after an overrun remains possible, and fails
the attempt. Internal timers do not guarantee a bound on provider setup or release.

One actual RTX PRO 6000 is required. The live launch request must be private,
GPU enabled, TPU/internet disabled, with machine shape `NvidiaRtxPro6000`, the
immutable image and exact versioned sources in the private package. No alternative
accelerator is permitted. The single-use claim is consumed before the one save;
an uncertain save response must never trigger an automatic second submission.

The final package binds an executable notebook template and a separately hashed
runtime capsule. Its initial `AUTHORITY = None` cell refuses all work. After the
owner approves the review lock, the launcher may fill **only that declared literal
data cell** with the bound approvals, retained evidence and consumed claim. All
other notebook cells, metadata and runtime bytes must match the reviewed artifacts.
This avoids circular hashing of an approval that names the package containing it.
The sealed notebook's exact execution hash must also be retained before submission.

Missing, stale or changed authority refuses before model loading or GPU queries.
Scientific output scoring and independent replay are unchanged. A provider COMPLETE
status, post-write witness/marker, exact source/image/settings and verified cleanup
remain necessary for technical completion. This test still has no pretrained-image
results, and the real checkpoint/GPU loading path is not established by tiny CPU tests.
