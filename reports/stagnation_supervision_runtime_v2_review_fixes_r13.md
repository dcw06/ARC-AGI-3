# Track 3 amendment S2: code-review fixes and reproduction of the old and corrected analyses (sanitized)

**Status.** This is an offline, CPU-only record. No GPU run, upload, reservation or launch was made or authorized.
- **Preserved.** The GPU evidence, every retained session record, the original pooled analysis and every published
  report are untouched, including `reports/stagnation_supervision_v1_results.md`.
- **Outcome.** No numerical conclusion changes.

## What was fixed

A code review of the S2 commits (`c145f8c..8ad7aff`) reported 15 findings. The fixes are in `18455f9`; review
snapshot r13 is `9d25d1f`.

| Finding | Fix |
|---|---|
| Two different, weak definitions of an identical trajectory; duplicates could hide differing reflection outcomes or cost | One identity, `selfreview.trajectory_signature` (`trajectory_signature_v2`), is used by the self-review draw, `pooled.reproducibility` and `pooled_distinct`. It covers policy calls and reflections (details below). |
| Limitation sentence hard-coded ("one distinct trajectory per game and arm") | Derived from the observed distinct-trajectory counts per game and arm (`pooled.distinct_limitation`) |
| The distinct section's "realised" cost left out the spend of the excluded runs | The top-level `spend` gives actual spend over every executed episode, including repeats and exact duplicates (canaries excluded). `pooled_distinct.analysis_cost` replaces its `realised_cost` and is labelled "not actual spend". `cost_denominators` labels all three cost figures. |
| Launch-time record hashed and parsed from separate reads; a missing or malformed file crashed the evaluation; ignored in rehearsal mode | The launch-time record, the execution lock and each retained record are read once, and the hash and the comparison use those bytes. A missing, malformed or non-object file is reported as a validation failure. The chain is checked whenever a launch-time record is supplied, in either mode. Its equality uses `content_sha256` (the record without the evaluating lock). |
| §14a said the distinct section reports "the same quantities" | §14a gains a dated correction that lists exactly what `pooled_distinct` reports and what it omits. `not_reported_here` in the output says why for each omission. The October 12 text is kept. |
| Duplicated code; the distinct set computed twice | `compute` and `compute_distinct` share `_quantities`. `distinct()` is computed once per evaluation and shared by the sample and the distinct section. |
| Weak or missing regressions | Strengthened (see Verification) |

**What the identity covers:**
- the game and arm, and every step's observed facts;
- every policy call's request and response hashes, status, finish reason, response size and token counts;
- every reflection call's request and response hashes, status, finish reason, response size and token counts;
- the evaluator's reflection rows (status, validity, tokens);
- every supervision event's index, outcome, due flag, delivered text, call request hash, call error and validity;
- the suggestion tests in force, levels and stop reason.

**What it excludes, as documented in `SIGNATURE_EXCLUDES`:**
- **Timing:** call start and return times and latencies; step dispatch times; episode start and end times.
- **Identifiers:** session, episode and pair ids, block, `repeat_of`, supervision record ids, journal ids and
  sequence numbers, and the evidence-inventory digest.

**The committed self-review.** The committed sample (`1d46ed57…`) embeds the first S2 rule text, and the annotations
are bound to its digest. `selfreview.committed_sample` accepts such a sample only if the corrected identity draws
exactly the same selection and exclusions, carrying the old description. It does here. The review is not redrawn and
not re-annotated.

**Two findings deliberately left as they are:**
- **The sample's top-level `amendment: "S1"`.** Changing it would alter the committed sample's digest. Its meaning
  (the self-review exists under S1; `amendment_s2` marks the distinct draw) is now documented.
- **A lock-independent digest bound at launch time in the gate.** It would change the GPU payload, and no launch is
  authorized. The historical execution lock binds the whole launch-time file, and the pooled evaluation ties a
  re-evaluation to it through `content_sha256`.

## Verification (CPU)

| Check | Result |
|---|---|
| CPU suite r17 (`..._local_checks_r17.json`, CPython 3.12.3, commit `9d25d1f`) | 327 tests (160 historical, 167 runtime v2), 0 failures, errors or skips; all seven receipt checks pass |
| Public review snapshot r13 | lock `ce13355c256051733761743991c0e5064ac1bed981c97a45fe39ceafa0f0478f`; payload bindings identical to r12 (154); review documents differ only in `pooled.py`, `selfreview.py` and the protocol text |
| Public review check r13 | passed |
| Private review snapshot r16 | lock `d7fbf1eda80fd69f98ba94d1a59f1bcbeb3cdde1f39ca0559ff86e3fa9bbb9b4`; differs from public r13 only in the four private bindings; payload equals private r14, the package both sessions ran |

**New and strengthened regressions** (`tests/test_ssv_runtime_v2_review_fixes.py`, plus edits to two existing files):
- **Identity:**
  - episodes with identical actions and frames but different delivered reflections are distinct;
  - so are episodes whose undelivered reflections differ in status (an invalid versus a failed call);
  - so are episodes with a different policy response or reflection request;
  - timing-only and identifier-only differences are not;
  - the draw, the reproducibility flags and the distinct section agree pair by pair.
- **Rehearsal (end to end on real offline evidence):** the block-2 episodes excluded are exactly those whose raw
  policy and reflection request/response hashes replay block 1, checked independently of the signature. The scripted
  model replays all three.
- **Self-review fixture:** it now draws the S2 sample, so the only failure it models is the missing commitment.
- **The branch without a launch-time record:** a binding mismatch and a match are both asserted.
- **Inputs:**
  - missing, truncated and non-object records and execution locks are reported, not raised;
  - each record is read exactly once;
  - a supplied launch-time record is checked in rehearsal mode.
- **Derived limitation:** the counts-derived statement is checked, along with spend and its denominators.
- **The committed sample:** a sample under the old rule text with the same selection is accepted and labelled; one
  with a different selection is refused.

## Reproduction of the old and corrected analyses (private inputs; read-only)

1. **The original analysis, rerun with the original code** (private r15 checkout, commit `99c13b3`): byte-identical
   to the retained original, `47fd9d07bf4eab31aee0e007e821687959aed1ed6e36e8d8a4cbf8eb922ba1c2`.
2. **Both sessions re-evaluated under private r16:** technically complete and accepted, 0 problems. Each is identical
   to its r14 and r15 records apart from the evaluating lock.
3. **The corrected analysis** (private r16, launch-time session-1 record supplied, committed annotations): the binding
   checks and the committed-sample equivalence pass. The retained private result has SHA-256 prefix
   `3da22f6b9d083de3`.
4. **An independent reproduction** reads the run evidence directly, without `pooled.py` or `selfreview.py`. It
   deduplicates from raw call hashes and recomputes the endpoints with the frozen evaluator and outcome functions.

**The original against the corrected analysis.** Apart from the limitations, all 33 items compared are identical (32
numeric items and the headline's precision statement):
- the primary recovery per arm (counts, rates, Wilson and bootstrap intervals, censoring, actions to exit) in both
  sections;
- every game, and every block-by-game cell;
- completed levels, false interruptions (detector and calls), suggestion following, reliability and the s5i5 blind
  spot;
- the §8.6 conditions and verdict (inconclusive);
- the reproducibility flags, distinct counts and repeat spread, which are unchanged under the stronger identity: every
  repeat and every block-2 episode still replays exactly, policy requests and responses included;
- the 12 exclusions;
- the distinct-trajectory reflection cost, now labelled `analysis_cost`;
- the self-review summary.

**The one change** is the S2 limitation sentence. It now comes from the counts and gains "(12 in all)"; its meaning is
unchanged.

**The independent reproduction against the corrected analysis.** All 19 checks agree:
- primary recovery per arm for the 24 main episodes and the 12 distinct trajectories;
- distinct recovery by game;
- levels and false interruptions;
- the excluded episodes and the distinct counts per game and arm;
- actual spend from the call rows, which equals the run totals exactly.

**Actual spend (new; every executed episode, both sessions, canaries excluded):**
- **Policy:** 1,080 calls, 26,978,054 prompt and 27,827 completion tokens charged.
- **Reflections:** 40 calls (periodic 24, triggered 16), 53,576 prompt and 8,962 completion tokens charged.

**The three cost denominators:**

| Figure | Denominator |
|---|---|
| `spend` | every executed episode: 27 episodes, including 3 repeats and 12 exact duplicates |
| `pooled.realised_cost` | the frozen definition: main episodes, repeats excluded, duplicates counted (24) |
| `pooled_distinct.analysis_cost` | distinct trajectories only (12); not actual spend |

**Conclusion.** The published results stand unchanged: inconclusive, with one genuine recovery (periodic, ls20). The
triggered arm's only recovery is a display-counter artefact, and no level was completed. The fixes make the code match
what the amendment and the reports claim. They do not alter any reported number.
