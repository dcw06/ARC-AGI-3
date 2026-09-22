# Coordinate interpretation v1: review protocol and decision rules

Question: does task-local indexing clarification help, does performance differ
with grid size, or is the evidence inconclusive? This is not a general perception
remedy or a gameplay-policy comparison. Preserve completed grounding v1 unchanged.
No source approval, compute authorization, reservation, or model call exists for
this new revision. No environment actions, scorecards, images, memory, planning,
source-derived mechanics, answer examples, or holdout data are added.

## Exact baseline and isolated wording

The prior system prompt ALREADY says x is the column, y is the row, and
`grid[y][x]`. Preserve that system message byte-for-byte. Baseline user instruction:
`Return {"color": integer} for the cell at the supplied x,y.`
Treatment appends only: ` Here x selects the column, y selects the row, and the requested value is grid[y][x].`
Thus the treatment tests task-local repetition/prominence, not access to a missing
interface fact. Grid, target, answer, model, tokenizer, schema, temperature 0,
seed 0, non-thinking mode, and 128-token output cap remain identical within pairs.
Keep fresh independent requests and the previous strict color-only JSON schema.

## Inventory and selection, frozen before calls

56 requests = 28 target cells × two formulations. Seven source groups:
the retained initial 64×64 frames for ar25, ft09, ls20, sc25 (already-inspected
eligible development data), plus synthetic 8×8, 16×16, and 32×32 grids.
Synthetic sources are not games or generalization evidence. The original retained
archive digest and member/frame references are preserved by the builder.

Per source choose one unordered boundary coordinate pair and one interior pair.
Both coordinates are off-diagonal and their target/transposed colors must differ.
Ask both `(x,y)` and `(y,x)` separately, yielding four targets per source. Boundary
means either coordinate is 0 or size−1; interior means neither. Consider unordered
pairs with x>y. Choose by lowest sum of the running target-color counts, then
lowest maximum count, then lexicographic SHA-256 of selection seed/source/stratum/
x/y. Sources are ordered as listed, boundary before interior. Seed is 20260922.
Synthetic pixels use consecutive SHA-256 blocks of `seed:size:block`, bytes modulo
16, row-major; no hand-inserted target clues or edited retained pixels.

Every color 0–15 occurs as a target. Per condition counts are
`[1,1,2,3,2,3,2,1,1,2,2,1,2,1,2,2]`: not perfectly balanced; report this residual
imbalance. There are fourteen boundary and fourteen interior targets per condition.
Condition order alternates by source index plus direction; each source has equal
baseline-first and explicit-first targets. Target pairs and questions sharing a
source remain correlated. Do not use 56 requests as 56 independent games.

The source-bound `cases.json` records exact requests, pair/condition/source IDs,
coordinates, hashes, mechanical answers and provenance. Only the `request` field
is sent; expected answers and source labels are evaluator-only. Independent
scoring reads the actual request grid, flattens it and indexes `y*n+x`, rather
than trusting stored expected answers. Inventory regeneration rejects reordered,
duplicate, missing or changed cases and source provenance.

## Outcomes and decisions

Each received answer is classified as correct, transposed, another valid color,
or malformed. Missing requires an explicit execution-failure receipt, not silent
omission. Valid incorrect and malformed answers remain diagnostic outcomes.
Missing responses and transport/token/deadline/evidence/cleanup faults make the
attempt technically incomplete. Retain per-case outputs, prompt/output tokens,
latencies, both condition totals and condition-by-size/stratum/source breakdowns,
and paired improvement/regression/unchanged correctness.

These thresholds are decision aids for this small fixed sample, not statistical
significance or internal-cause proofs. Require complete technically valid evidence:

- **Clarification candidate:** explicit has at least four net additional correct
  targets of 28, at least four fewer transpose matches, and no more than two
  correct-to-incorrect regressions. At least two of the four retained source
  groups must have positive net accuracy, with no retained source losing more
  than one of its four targets. Passing permits proposing a separately approved
  matched gameplay test, not policy promotion.
- **Size/indexing lead:** in both conditions, the synthetic 8×8 group has at least
  3/4 correct and exceeds pooled retained 64×64 accuracy by at least 25 percentage
  points. Report 16×16 and 32×32 results even if nonmonotonic. This is a lead only:
  size, input length, content and synthetic-vs-retained distribution differ, with
  just one synthetic grid per size. It does not isolate size as a causal factor.
- **Small-grid failure:** both conditions have at most 1/4 correct on 8×8. Recheck
  construction/serving evidence before any separate model or representation probe.
- **Otherwise:** inconclusive; no remedy chosen from aggregate accuracy. Multiple
  supported leads may coexist; none automatically authorizes a run. If technical
  acceptance fails, no advancement decision from missing or corrupted evidence.

No result automatically changes a live policy. Prospective, separately approved
gameplay and transfer evidence would still be necessary for promotion.

## Tokens and fresh compute proposal

Pinned tokenizer audit: transformers 4.57.6, tokenizers 0.22.2, Jinja2 3.1.6,
hash-verified original tokenizer. All 56 exact requests plus the separate startup
canary pass with truncation disabled: 299,814 total prompt tokens; largest 8,629.
Completion cap stays 128, yielding at most 7,296 generated tokens over 57 calls.
Per-request bytes, token counts and context headroom are retained in the audit.

Propose ONE **2,100-second** provider attempt, not previous reservation credit:
1,980 seconds startup-inclusive internal lifecycle, absolute admission cutoff
1,680, cleanup reserve 300, provider margin 120; installation cap 450, model
startup cap 900, workload window 480, individual transport timeout 120 seconds.
The prior grounding run measured 162.577 seconds install, 655.805 startup,
820.301 to readiness, and 8.610 seconds for twelve calls. This inventory has about
2.22 times the prompt volume; stage limits are conservative ceilings, not duration
guarantees. Absolute admission closes even if stage maxima cannot all fit.

Retain context 65,536 tokens; compact/default serialized request at most 65,536
bytes; full response retained up to 8 KiB, overflow technical failure; total
evidence 64 MiB (control 1, monitor 16, worker 32, evaluation 8, logs 7).
Resource ceilings: RSS 128 GiB, VRAM 86 GiB, scratch 4 GiB. Zero retries,
environment actions, scorecards, or scored submissions. Authority must bind
exactly 56 diagnostic calls, one canary, one attempt, and the new source lock.

## Lifecycle, local checks, and review

Reuse the verified model-service supervision in a new namespace. Durable request
intent precedes inference; bounded response/hash/observed counts precede validation
and survive bridge failures. Preserve token parity, allowlisted ordered requests,
monitoring through termination, independent process/GPU cleanup, final dependency
and source removal, and final receipt hashes. A color-only request schema cannot
encode a particular answer. Startup canary is separately counted, not gameplay.

Local scripted runs cover correct, transposed, other valid, malformed, missing
transport, token mismatch, evidence exhaustion, deadlines, and monitor/cleanup
failures. Tests also check bounds, transpose discrimination, paired wording-only
changes, no provenance/answer-key fields in requests, and altered inventories.
Portable archive replay regenerates source-bound cases and reconstructs scores:

```bash
python scripts/build_phase4_coordinates_v1.py --check
python scripts/check_phase4_coordinates_v1.py --replay
```

Use the project's CPU Python environment; no ignored downloads, credentials,
model weights or GPU are needed. Live evidence will use the same frozen evaluator
with finalization checks, not the scripted fixtures. A target run has not occurred.

Inspect the unpacked private/offline GPU-disabled notebook and source/artifact
lock before explicit source approval and SEPARATE compute approval. Missing,
mismatched or consumed authority must fail before upload/installation. Reserve
fresh only after approval; deterministic package verification and an exclusive
pre-upload claim allow one managed launch, with no retry on uncertain outcome.
Manual copy/upload into a new provider session is outside this local gate's
protection and is not authorized. Preserve every historical revision.

Production one-scorecard/110-distinct-game certification, workload-specific
admission limits and exact accounting remain separate open Phase 4 obligations.

## Packaging revision disposition

R1 is preserved as a failed packaging snapshot: its notebook cell accidentally
contained a builder-only statement and raised NameError before the authority gate.
R2 removes that statement and is the review candidate. No GPU run occurred.
