# Track 2 Stage 1: decisions needed to freeze protocol v2

Prepared October 9, 2026, for the owner. This page decides nothing; nothing is frozen, drawn, approved or reserved.
The full options are in `open_protocol_choices.md`. This page orders them for the freeze:
- **First:** one defect found today, which must be fixed.
- **Then:** the three priorities named in the review of the Track 4 results.
- **Then:** the rest.

The withheld seed is drawn only after every decision here is recorded in a frozen revision.

## 0. Must fix: the recall response schema is rejected by the verified runtime (choice 9)

**The defect.** vLLM 0.19's default structured-output path refuses the recall schema. `uniqueItems` is unsupported by
xgrammar and unimplemented in the llguidance fallback (`structured_outputs_check_r1.json`). Every recall request
would be refused, so session A would stop at its first recall call and spend its attempt.

**Recommendation: drop `uniqueItems` from the decoding schema only.**
- The scorer already enforces distinct values and "no_evidence" standing alone, so a duplicate stays an invalid
  output (counted, never correct).
- Checked on CPU: the amended schema is accepted by xgrammar and enforces everything else.
- After the change, rebuild the frozen request plans and both review snapshots. Then rerun
  `check_evidence_memory_v1_structured_outputs.py` until both schemas are accepted.
- Prompt token counts do not change.

## 1. Unsupported-claim margins (choice 5)

**The current rule.** Memory minus recent, paired over all recall questions: point estimate ≤ +0.02 and 95% upper
bound ≤ +0.05. Otherwise the verdict is `..._unsupported_claims_outside_margin`.

**Precision.** These figures are approximate.
- The development count is 960 pairs in 84 groups, about 11 per group, pooled over both sessions.
- With *d* the share of pairs where the two arms disagree on "unsupported", and a design effect (DEFF) for
  clustering within groups, the interval half-width is about 1.96 √(d·DEFF/960).
- Track 4 gives a reference for *d* on this model. When two arms differed in one prompt element, 4% to 17% of
  paired questions changed correctness between arms. Track 2's arms differ in the evidence itself, so *d* of
  10–20% is plausible.

| Discordance *d* | Half-width, DEFF 2 | Half-width, DEFF 4 | Largest point estimate that still passes "upper ≤ +0.05" |
|---|---|---|---|
| 5% | 0.020 | 0.028 | +0.030 / +0.022 |
| 10% | 0.028 | 0.040 | +0.022 / +0.010 |
| 17% | 0.037 | 0.052 | +0.013 / below 0 |

Macro-averaging over families adds variance, so these half-widths are lower bounds.

**Consequence.** At plausible discordance the upper-bound condition, not the point margin, decides the verdict. A
true difference near zero can then fail the margin from imprecision alone. The current verdict cannot tell
"exceeds the margin" from "not measured precisely enough".

**Options.**
- **(a) Keep both thresholds as provisional pilot margins**, and state this precision limit in the frozen text.
- **(b) Keep the thresholds and split the reading into three outcomes:**
  - *met*: point ≤ +0.02 and upper ≤ +0.05;
  - *exceeded*: point > +0.02;
  - *not shown*: point ≤ +0.02 but upper > +0.05.

  Only *met* permits advancement, so the rule stays as strict as now. This is a small reviewed change to
  `protocol.conclusions` and its tests.
- **(c) Widen the upper margin** (for example to +0.08), chosen from this precision argument before the seed is
  drawn.

**Recommendation: (b).** It keeps the decision rule as conservative as now, but reports imprecision honestly instead of
as a failed margin. (a) is acceptable if the owner prefers no code change.

## 2. Trajectory exclusions (choice 8)

**The gap.** Protocol §4 excludes failing trajectories without replacement, but `stage1.build` has no exclusion step.
The successor's `freeze withheld` refuses to write a frozen set if any trajectory fails, and drops nothing silently.
On development seeds 336 of 336 trajectories pass.

**Options.**
- **(a) Amend §4 to "refuse and redraw".** This matches the implemented, tested freeze path and needs no change to
  the science code. On a failure:
  - publish the failed commitment and its counts;
  - discard that nonce;
  - draw a new one;
  - never inspect the failed set beyond the automated checks.
- **(b) Implement exclusion in `stage1.build`,** as §4 literally says. Report the counts; the denominators shrink.
  This is a reviewed change to science code, with tests.

**Recommendation: (a).** With 0 exclusions in development, a redraw should be rare. A recorded redraw is more
transparent than a silently smaller withheld set. Choose (b) if keeping every first draw matters more than avoiding a
code change.

## 3. Session B depends on session A's technical completion (choice 7)

**Facts.**
- No outcome exists after A; the session-level evaluation is technical only.
- The pooled analysis needs both sessions technically complete and valid in every pass.
- Nothing in the code makes B wait for A.

**What Track 4 showed.** A condition that lives only in authorization text is weak. Track 4's seed condition had to
be enforced by a launch-tooling gate that refuses until the committed record shows it satisfied.

**Recommendation: enforce it.**
- B's compute authorization names the SHA-256 of A's retained technical evaluation.
- B's launch tooling refuses unless that evaluation exists, matches the hash, and shows A technically complete and
  valid in every pass.
- This needs no change to the reviewed per-scope runtime gate, and follows the Track 4 seed-gate pattern.
- If A is not technically complete, the experiment stops: no pooled analysis is possible, and B is not launched.

## 4. Remaining choices

| Choice | Recommendation |
|---|---|
| 1. Two package builds or one | Keep two builds, A and B |
| 2. Repeat split | Keep 5 + 4 groups |
| 3. Admission granularity | Keep per-call admission |
| 4. Duplicate requests at delay 0 | Ask every scheduled call; doubles as a determinism check |
| 6. Runtime estimate | Replace §11 with the measured Track 4 figures (documentation only) |
| 10. Request cap | Accept the worst case (194,044 for A and 189,756 for B), with the 2,896 / 2,832 completion ceilings, stated in each compute authorization |
| 11. Tokenizer admission | Accept the offline audit |
| 12. Teammate stress set | Keep it out of Stage 1 |

**Also decide before Gate 1.** Who holds the two copies of the withheld nonce? Track 4 used an owner-approved
single-holder amendment, with two copies on one computer and the limitation recorded. Deciding the rule in advance
avoids an amendment at launch time.

## 5. After the decisions

1. Make the agreed changes: the recall schema; and, if chosen, `protocol.conclusions`, §4 text and B's launch gate.
2. Write the frozen protocol revision with the measured §11. Rebuild both packages and review snapshots. Run the
   structured-output check and the fresh-clone CPU checks.
3. Owner gates 1 to 7 follow unchanged (`owner_gates.md`), starting with the seed draw.
