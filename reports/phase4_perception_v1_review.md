# Paired perception v1 — local implementation review

This is a zero-action, unscored diagnostic proposal. It is not an authorized
run, a policy promotion, or production certification. Historical preflight and
fixture revisions remain unchanged.

## Frozen workload and interpretation

The exact requests and processor expectations are in
`certification/phase4_perception_v1/cases.json`. Five boards each receive one
raw-grid request and one PNG request, with identical instructions, schema,
model, seed, temperature and non-thinking configuration. Only the observation
content differs. Text precedes image within each pair; requests have no shared
conversation. This fixed order is a limitation, not a randomized experiment.

P1 is the retained ar25 observation; P2–P5 are mechanically generated controls
for rotation, reflection, markings and different shapes sharing color. They are
not five independent development games. Results are descriptive and grouped by
board. Reference masks, geometry answers and source interpretations never enter
model requests. The two interface controls test supplied action schemas/roles,
not knowledge of a game's mechanics. No commands are executed.

Independent replay recomputes the reference fixtures and scores object detection,
bounding boxes, color, coarse occupancy, internal markings and geometric
relationships. Matching uses the frozen exact-rational IoU assignment and tie
rules in `research/perception_v1/scoring.py`. Ambiguous transform sets remain
sets. Invalid answers and omissions keep their denominators; an incorrect or
malformed answer is an outcome, not an infrastructure rejection. There is no
repair, retry, adaptive case selection or automatic promotion threshold.

The image canary is also scored without requiring correctness. The inherited
text startup canary remains a service-readiness check. Technical failures stop
admission and censor remaining calls. Successful descriptions would not establish
useful action selection, progress or solving.

## Token audit and proposed budget

The pinned processor/tokenizer was executed on CPU over every exact request.
`phase4_perception_v1_token_audit.json` records full/manual image-token agreement,
patch geometry, payload sizes and response feasibility examples. Images are
1024×1024, with 1,024 image tokens; text/image board requests share a schema.
The full workload contains 53,505 prompt tokens, including the startup canary.

There are 10 perception calls (2,048 completion tokens each), two interface
controls (512 each), one image canary (64), and one startup text canary (128):
14 calls and at most 21,696 generated tokens. Maximum-sized schema examples
use up to 1,802 tokens including EOS. This is feasibility evidence, not a bound
on arbitrary Unicode or whitespace. Truncated JSON remains retained and invalid.

Propose a fresh **2,400-second provider reservation**, with a startup-inclusive
2,280-second internal ceiling. Installation is capped at 450 seconds; model
startup at 900; the request window at 600; cleanup receives 300. Their sum is
2,250 seconds. Admission closes by 1,980 seconds, or 600 seconds after requests
begin, whichever comes first. Each transport timeout is 120 seconds. A slow
response can leave an incomplete study; it does not enlarge the reservation.
The 600-second window provides about 27 ms per maximum generated token before
prefill/overhead; completion is not guaranteed by this sizing.

Prior compatible startup measured 651 seconds, including a 509-second model
hash. This proposal retains startup markers and the 900-second ceiling rather
than treating average startup as a guarantee. No time has been authorized or
reserved for this study.

Limits: 16,000 prompt tokens per request, 65,536 context tokens, 262,144 request
bytes, 32,768 retained response bytes, 64 MiB shared evidence envelope, 128 GiB
RSS and 4 GiB scratch. Requests and bounded responses, hashes, observed token
counts, finish reasons and processor geometry survive validation failures and
the process bridge. Monitoring covers teardown; replay requires independent GPU
cleanup on live runs. Logs and finalization remain part of acceptance.

## Local validation and portable replay

Scripted correct, incorrect, incomplete JSON, token-mismatch, transport-failure
and evidence-exhaustion runs exercise the supervised path without a model.
Cancellation and monitor failure exercise cleanup. Mutation tests reject missing
pairs, changed request/response bindings, token drift and failed cleanup.
Launch tests reject missing, mismatched or consumed approvals/reservations and
preserve single-attempt semantics even after an unknown upload outcome.

From a clean checkout with the development Python environment:

```bash
python scripts/check_phase4_perception_v1.py --replay
python scripts/review_phase4_perception_v1_notebook.py --folder notebooks/phase4-perception-v1-review-r1
```

The first command verifies archive/member checksums and independently replays
retained CPU evidence without rewriting it. The second verifies and unpacks the
notebook, compiles its Python, tests refusal before installation, and exercises
approval/reservation/package gates in a temporary copy with a fake provider.
These fixtures confer no actual source or compute authority.

The notebook is private, GPU-disabled and internet-disabled. Actual launch
requires explicit source approval for its review lock and separate compute
authorization, then one fresh reservation. Phase 4 production certification,
workload admission limits and exact billing remain open.
