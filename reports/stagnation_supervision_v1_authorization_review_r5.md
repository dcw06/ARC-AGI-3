# Track 3 R5 live authorization package review

This is preparation and local review, not approval, reservation or launch. R4
(`811e8e4`, lock `382dceb1d785b9701f026597d04572ff622199a75bbcca537b9504b7e72d0671`)
is preserved. The R5 candidate is private, GPU/TPU/internet disabled. It includes
no approval or reservation sidecars and must reject live execution before
installation, GPU probing or inference.

## Executable binding

R5 is constructed directly from the R4 notebook's verified embedded payload.
Exactly one of 1,111 files changes: authority.py. Three counted substitutions
enable authority checking, replace the obsolete R1 lock path with the R5 source
review path, and correct the gate docstring. All model, policy, reflection,
monitoring, deadlines, telemetry, evaluation and cleanup code is byte-identical
to R4. The derived workspace source and every historical notebook remain intact.
The overlay is explicit, reproducible packaging, not a mutation of frozen R4.

The candidate source-review.json is the authority's exact review lock. Its hash
is the source-approval identity. A separate review-source-lock.json binds that
source lock, notebook, metadata, builder, reviewer, tests and this document.
The term reviewed_launch_source describes the executable reviewed by the local
checks; it grants no authority. Source approval must bind the source-review
hash; each compute approval must separately bind that hash and the source
approval hash. Each execution and reservation binds the preceding records.

## Separate proposals

| Session | Provider reservation | Startup-inclusive internal ceiling | Episodes | Policy calls | Reflection calls | Canary |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 5,400 s | 5,100 s | 15 | 600 | 32 | 1 |
| 2 | 4,800 s | 4,500 s | 12 | 480 | 32 | 1 |

Each session requires its own compute decision, one fresh reservation and one
attempt. No aggregate authorization, automatic second-session launch or retry.
Maximum 40 actions per episode, zero scored submissions and zero holdout runs.
Cleanup reserve is 300 seconds inside each internal ceiling, with another 300
seconds between the internal and provider ceiling. New groups require the
unchanged 800-second admission allowance. Telemetry remains at R4's 0.5-second
cadence with the one-second maximum observed gap and unchanged evidence caps.
These are proposals only; this package reserves zero seconds.

## Checks and later packaging

Run `python -m scripts.review_stagnation_supervision_v1_authorization_r5` under
the existing Linux development environment. The reviewer verifies the exact
R4 overlay and all source/artifact/document hashes; exercises synthetic approval
records solely in temporary directories; executes the unapproved notebook and
checks refusal/source removal; then CPU-rehearses the same notebook with three
arms and independently evaluates trajectory and lifecycle evidence. R4's 161
passing tests and pinned-tokenizer audit remain applicable to the unchanged
runtime; its 1,122 ordered requests remain unchanged.

Negative checks cover missing, pending, mismatched, multi-session and consumed
records, wrong budgets, changed source and duplicate runtime claims. Local
assembly requires all exact approved sidecars, the authorized session, and a new
destination. It does not fabricate approvals/reservations, consume a reservation,
contact Kaggle or submit anything. GPU is enabled only in that later authorized
assembly, never in this review notebook. Before submission, a separately reviewed
submission operation must verify the assembled notebook and atomically record
the reservation's single submission claim; ambiguity must be reconciled without
a retry. A runtime marker alone is not a cross-provider-session submission lock.
No submission automation is authorized or performed by this review.

## Approval and remaining limitations

Request explicit source approval for the generated source-review hash and
separate compute authorization for each desired session only after the local
review receipt passes. Create real reservations only after those decisions;
verify the final per-session launch package before any separately instructed
submission. Historical consumed reservations cannot be reused.

Real GPU timing, including disk/startup and the 0.5-second telemetry cadence,
remains unmeasured. The false-interruption gate still lacks a second qualified
continuation control. ls20 remains descriptive/exploratory and cannot satisfy
that minimum. This study cannot establish that gate or complete Phase 4.
