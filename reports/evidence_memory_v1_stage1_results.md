# Track 2 Stage 1 (evidence_memory_v1): results of the registered two-session analysis

**What this is.** The sanitized results of the frozen protocol's one scientific analysis
(`research/evidence_memory_v1/successor/final.py`, owner gate 7). It pools sessions A and B, each run once on one RTX
PRO 6000 on October 10, 2026, on withheld draw 2. Aggregates only: the notebooks, raw outputs and withheld questions
stay private and account-only.

**Verdict: `memory_preserves_access_not_shown_over_retrieval`** (frozen protocol §9). Under a restricted context, the
memory package preserves access to old evidence that recent history loses. It does not improve over simple
state-keyed retrieval, which holds the same old facts. Its unsupported-claim margin is `met`, so the verdict meets
the protocol's advancement rule for access; it supports no claim of advantage over retrieval.

## Inputs

| | Session A | Session B |
|---|---|---|
| Attempt | `em1a-159d1a1c…`, 873.6 s | `em1b-fc6257fe…`, 790.7 s |
| Withheld frozen set | `69b450c1…` (groups 0–5) | `fa1500fe…` (groups 6–11) |
| Calls answered | 2,832 of 2,832 | 2,928 of 2,928 |
| Invalid answers (all arms) | 1 | 3 |
| Technical status | `session_technically_valid` | `session_technically_valid` |
| Technical evaluation (SHA-256) | `45826b5f…` | `1ee0599d…` |

The analysis recomputed both sessions' technical validity from their retained inputs and found both live, withheld,
registered and complete. Pooled-analysis output (private): SHA-256 `ce7d16a85a59bd44cf09a614c6c4ee7f2e48020b46430986345bc468209e9a5d`.
Common to both: frozen protocol `6f96dbe7…`, draw 2 commitment `d80505e2…`, evaluator sources `d37ba0ea…`.

## Comprehension floor (§9, rule 2): passed

| | `recent_raw` | `state_keyed_raw` | `memory` | Floor |
|---|---|---|---|---|
| Reading accuracy (package holds the evidence) | 0.990 | 0.997 | 0.979 | 0.80 |
| `recent_raw` recent-evidence accuracy | 1.000 | | | 0.80 |

The experiment is interpretable: it can separate retention from comprehension.

## Primary endpoint: old-evidence accuracy (delays 8 and 16; 168 questions, 60 groups per arm)

| Arm | Estimate | 95% CI | Exact-reader ceiling (§8) |
|---|---|---|---|
| `recent_raw` | 0.000 | [0.000, 0.000] | 0.00 |
| `state_keyed_raw` | 0.900 | [0.900, 0.900] | 0.90 |
| `memory` | 0.892 | [0.875, 0.900] | 0.90 |
| `full_history` (reference) | 1.000 | [1.000, 1.000] | 1.00 |

The model read every arm at or within 0.01 of its exact-reader ceiling. Old-evidence accuracy here is therefore set
by what each package makes available, not by how well the model reads it.

## Contrasts (paired, 168 pairs, 60 groups)

| Contrast | Estimate | 95% CI | Reading |
|---|---|---|---|
| 1. memory − recent history | +0.892 | [+0.875, +0.900] | **memory preserves access** |
| 2. memory − state-keyed retrieval | −0.008 | [−0.025, 0.000] | no difference detected |
| 2, evidence in both packages (144 eligible, 24 excluded) | −0.008 | [−0.025, 0.000] | no difference detected (representation) |

## Unsupported claims (memory − recent, paired over 960 recall questions, 84 groups)

| Estimate | 95% CI | Margins (point ≤ +0.02, upper ≤ +0.05) |
|---|---|---|
| −0.012 | [−0.016, −0.010] | **met** |

Unsupported-claim rates: `recent_raw` 0.012, `state_keyed_raw` 0.050, `memory` 0.000, `full_history` 0.054.

## Diagnostics (never gates, §9 rule 6)

| | `recent_raw` | `state_keyed_raw` | `memory` | `full_history` |
|---|---|---|---|---|
| Forgetting difference (60 groups) | 1.000 | 0.100 | −0.008 | 0.000 |
| Recent controls at old delays (168, 84 groups) | 0.970 | 0.988 | 0.292 | 1.000 |
| Decision accuracy, old (secondary; 120, 60 groups) | 0.408 | 0.767 | 0.800 | 0.667 |
| Correct abstention when the package lacks evidence | 0.979 | 0.826 | 1.000 | 0.747 |
| Abstention when the package holds evidence | 0.006 | 0.003 | 0.021 | 0.000 |
| Invalid rate (1,296 per arm) | 0.000 | 0.001 | 0.001 | 0.000 |

- **`recent_raw` loses old evidence** (forgetting difference 1.00, above the 0.15 diagnostic threshold): the restricted
  context does remove access, so contrast 1 measures something real.
- **Memory's recent controls at old delays are low (0.292) by construction.** The exact-reader ceiling is 0.321
  (§8): at long delays the memory package often does not carry those recent-control facts. This is a limit of the
  memory writer's selection, not a reading failure, and it is the main cost of the memory representation in this
  design.
- **Decision accuracy** on old questions is highest for memory (0.800) and lowest for recent history (0.408). It is a
  secondary measure and supports no claim on its own.
- **Abstention.** Memory abstains whenever its package lacks the evidence (1.000) and asserts no unsupported value.
  The other arms abstain less often when their packages lack the evidence and assert more unsupported values.

## Stability (repeat pass)

576 repeated questions (144 per arm, across both sessions): 576 identical answers (100%) under temperature 0 and
seed 0.

## Limits

- One model (`Qwen3-VL-30B-A3B-Instruct-FP8`), synthetic trajectories, single-turn reading, one draw (168 old
  questions per arm). The results describe access under a restricted context, not forgetting inside the model.
- The design's availability ceilings determine the primary endpoint almost completely, and the model matched them.
  This stage therefore tests whether the model reads each representation faithfully. It does not test whether one
  representation is better at equal availability; that was contrast 2's restricted reading, which detected no
  difference.
- The first withheld draw was retired before execution (frozen protocol §5). Draw 2 was drawn after the complete
  final design was frozen.

## Reproduction

Frozen protocol §5, step 5: after the run, the withheld nonce is published so anyone can rebuild the exact cases and
check the commitment `d80505e2…`. Only the owner holds it; publication is the owner's step and has not been taken.
