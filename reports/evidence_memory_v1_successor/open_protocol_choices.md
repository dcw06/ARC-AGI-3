# Track 2 Stage 1: protocol choices still open (for the owner)

**Decided October 9, 2026.** The owner decided these choices on October 9, 2026: choice 9 as option (a), choice 5
as the three-way reading (`freeze_decisions.md`, item 1), choice 8 as (a), choice 7 as enforced in session B's
launch tooling (not (a) as recommended below), and every other recommendation as written. Who holds the two
copies of the withheld nonce stays open (owner gate 1). The protocol of record is
`reports/evidence_memory_v1_protocol_v2_frozen.md`. This note is kept unchanged below as the options considered.

**Status.** Protocol v2 (`reports/evidence_memory_v1_protocol_v2.md`) is a draft. Nothing in it is frozen,
scheduled, reserved or approved. This note decides nothing. For each choice it lists the options and the
consequences, and gives a recommendation for the owner to accept or reject.

**What the successor packages implement.** They implement protocol v2 as written: two package builds, the 9-group
repeat split, per-call admission, separate duplicate requests, and the provisional margins. They do not change any of
these.

**Choices 1 to 5 are protocol v2 section 15.** Choices 6 to 12 arise from moving to the verified runtime, or from
gaps found while preparing it.

## 1. Two package builds or one (section 15.1)

**Current design.** Two builds, A and B. They share code and differ in scope, frozen set, token audit, review lock,
approvals, claim, receipt and reservation. The successor implements this as `research/evidence_memory_v1_session_{a,b}`.

**Options.**
- **(a) Keep two builds.** This is what is built. A session-A approval cannot run B. The two review notebooks and
  locks differ only in those session bindings. It costs two reviews and two approval sets.
- **(b) One package that selects its session from a locked frozen file.** One review and one source approval, but
  the session must be chosen at launch. The gate would then need its own once-per-session accounting, which the
  verified launch accounting does not provide.

**Recommendation: (a).** It reuses the verified one-attempt accounting unchanged and keeps the two sessions'
authority separate.

## 2. Repeat split (section 15.2)

**Current design.** 9 of 84 groups are repeated. Session A repeats 5 groups (304 calls) and B repeats 4 (240 calls).
Each family is covered only across both sessions.

**Options.**
- **(a) Keep it.**
- **(b) 7 groups per session**, so each session covers every family on its own. That adds about 120–150 calls per
  session.

**Recommendation: (a).** The repeat measures stability only and never enters an endpoint, and pooling across both
sessions already covers every family. Choose (b) only if a per-session stability statement is wanted; per-session
outcome reporting is excluded anyway.

## 3. Admission granularity (section 15.3)

**Current design.** The reviewed per-call rule: a call starts only if its whole 80 s bound ends before 3,000 s.

**Options.**
- **(a) Keep per-call admission.** At most one partial group results; the connected rehearsal shows a cutoff inside
  pass 1 stopping cleanly.
- **(b) Add group-level admission at measured rates.** This needs a change to the reviewed runner.

**Recommendation: (a).** An incomplete session yields no pooled analysis whichever rule truncates it, so (b) adds
risk without changing any result.

## 4. Duplicate requests at delay 0 (section 15.4)

**Facts.** Many pass-1 calls repeat an identical request already made for another arm: 613 of 2,592 in session A
(24%; 1,979 distinct requests) and 616 of 2,592 in B (1,976 distinct). The figures come from the token cross-check.

**Options.**
- **(a) Ask every scheduled call** (current).
- **(b) Ask once and share the answer.** This saves about 600 calls per session but couples the arms, and changes
  the schedule and the call count.

**Recommendation: (a).** The answers must agree under temperature 0 and seed 0, which doubles as a determinism
check. The runtime budget does not need the saving.

## 5. Unsupported-claim margins (section 15.5)

**Current design.** Point estimate ≤ +0.02 and upper bound ≤ +0.05 (memory minus recent).

**Options.**
- **(a) Accept them as provisional pilot margins.**
- **(b) Set them from a power or precision argument before the seed is drawn.**

**Recommendation.** Settle this before the withheld seed is drawn, because the seed is drawn only after every design
decision is fixed. With 84 groups, the upper bound will rarely fall below +0.05 unless the true difference is near 0.
(a) is defensible if it is stated as a pilot margin.

## 6. Runtime estimate and phase ceilings on the new runtime

**What changed.** Protocol v2 section 11 is based on the v3 runtime: 961 s measured before the first question, and a
1,540 s allowance. The verified runtime has its own ceilings: installation 900 s, model verification 600 s and server
startup 900 s. All are bounded by the unchanged 3,000 s admission cutoff.

**Measured on this runtime (updated October 9, 2026).** Track 4's attempt ran the same runtime, model snapshot and
lifecycle on one RTX PRO 6000 (`reports/progress_subgoal_v1_runtime2_attempt1_results.md` on
`track4-successor-runtime-v1`). It split the overhead before the first study call into:

| Phase | Seconds |
|---|---|
| Wheel integrity (all 174 mounted wheels hashed) | 31 |
| Hash-pinned installation | 85 |
| Model tree verification | 146 |
| Server start to ready | 113 |
| Startup and inference probes | about 26 |
| **First study call** | **at about 401 s** |

After the questionnaire, the cancellation probes and cleanup took about 5 s.

**Per-call time.** Fitted on 5,852 sequential calls:
- 0.0134 s per call, plus 2.11 × 10⁻⁵ s per prompt token, plus 0.0063 s per completion token;
- mean 0.114 s per call; p95 0.143 s.
- Track 4's prompts ran up to 5,675 tokens, but its completions were at most 10 tokens. The completion rate
  therefore extrapolates to Track 2's 64-token cap. It matches the v3 fit (0.0064 s).

**Re-derived estimates** (planning only; admission control enforces the deadline). Track 2's prompts average about
597 tokens, with a maximum of 1,249. A metrics read per call is allowed at 0.01 s.

| Session | Typical completions (about 20 tokens) | All completions at the 64-token cap | All at the cap, per-call time doubled |
|---|---|---|---|
| A (2,896 calls) | ≈ 875 s | ≈ 1,680 s | ≈ 2,950 s: just inside the 3,000 s cutoff |
| B (2,832 calls) | ≈ 865 s | ≈ 1,650 s | ≈ 2,890 s |

**Options.**
- **(a) Keep the section 11 figures** as conservative planning numbers.
- **(b) Replace section 11** with these measured figures.

**Recommendation: (b), as a documentation-only revision.** The budget itself (3,600 s reserved per session) needs no
change. Expected use falls from 1,500–2,100 s to about 900 s per session.

## 7. Should session B's gate require session A's technical report?

**Facts.** The stop rule says only technical rules may stop the experiment after A. Nothing in the code makes B's
launch depend on A's technical report.

**Options.**
- **(a) Leave it to the human compute authorization for B** (current).
- **(b) Add a gate condition for B:** a retained, technically valid session-A evaluation, bound by hash.

**Recommendation: (a) for the pilot, with the condition written into B's compute authorization text.** (b) would add
a cross-session dependency to a gate that is otherwise per scope.

## 8. Trajectory exclusions are specified but not implemented

**Facts.** Protocol v2 section 4 excludes, before the run, any trajectory that:
- fails `verify_history`;
- has gold answers that differ from its construction;
- has a faithful memory that is not faithful under the independent checker;
- has a prompt over 4,096 tokens.

Excluded trajectories are not replaced. `stage1.build` has no exclusion step. On development seeds there are 0
exclusions (336 of 336 trajectories pass), so the gap is invisible there.

The successor's frozen-set path (`successor/freeze.py`) checks every condition. If any trajectory fails, it refuses to
write a frozen set; it does not exclude anything silently.

**Options.**
- **(a) Keep "refuse and redraw".** A failing withheld draw would be recorded and a new nonce drawn.
- **(b) Implement exclusion in `stage1.build`.** Drop the trajectory and report counts. This is a scientific code
  change and needs review.

**Recommendation: decide before drawing the seed. (a) is simpler; (b) is what section 4 literally says.**

## 9. Strict JSON-schema decoding on the verified runtime (updated: a blocking defect, fix required)

**What Track 4 showed.** Strict `json_schema` decoding works on this runtime for flat objects with string enums. All
5,852 of 5,852 live calls were schema-valid; vLLM selected the xgrammar backend.

**What Track 2's schemas need beyond that.**
- Recall answers use an array of enum strings with `minItems` and `uniqueItems`.
- Decision answers use an integer, a nested object and an integer-valued map.

**CPU check on the exact runtime install.** `scripts/check_evidence_memory_v1_structured_outputs.py` was run with
vLLM 0.19.0, xgrammar 0.1.34, llguidance 1.3.0 and the pinned tokenizer, under the server's default configuration
(backend `auto`). The receipt is `structured_outputs_check_r1.json`.

| Schema | Result |
|---|---|
| Decision | Accepted (xgrammar). The grammar accepts valid answers and rejects strings in `action_data`, a non-integer id and a missing field |
| Control (flat string enum) | Accepted (xgrammar), as in Track 4 |
| **Recall** | **Rejected.** xgrammar flags `uniqueItems` as unsupported, so vLLM falls back to llguidance, which fails with `Unimplemented keys: ["uniqueItems"]`. The server would refuse every recall request, so session A would stop at its first recall call as a transport failure and spend the attempt with no result |

**Options.**
- **(a) Drop `uniqueItems` from the decoding schema only.** The scorer (`readers.validate_response`) already
  enforces distinct values, and that "no_evidence" stands alone. A duplicate stays an invalid output, counted against
  the 2% cap; scoring does not change. Checked on CPU: the recall schema without `uniqueItems` is accepted by
  xgrammar and enforces everything except uniqueness.
- **(b) Encode the allowed answers exactly**, as an enum of the eight canonical arrays. The decoder would then also
  enforce uniqueness, "no_evidence" alone and canonical order. This is a larger change to what the decoder permits.
- **(c) Pin another decoding backend in the server argv.** This changes the verified runtime; not recommended.

**Recommendation: (a).** Either fix changes the request bodies but not the prompts, so the token counts are unchanged.
The request digests, frozen request plans and review snapshots must then be rebuilt, and the check rerun until both
schemas are accepted, all before the freeze.

## 10. Counted metrics reads and the request cap

**Facts.** Protocol v2 section 10 requires per-call prefix-cache counters and idle verification after a timeout. On
the verified runtime every HTTP request is counted. The successor's ledger cap is therefore the worst case: 194,044
requests for A and 189,756 for B, with up to 65 idle-verification reads per timed-out call. A complete session issues
2 × N + 12 requests (5,804 for A in rehearsal). The "calls ceiling per session" in section 12 (2,896 / 2,832
completions) is still enforced separately by the study service.

**Options.**
- **(a) Accept the worst-case cap.**
- **(b) Pool the idle-verification reads** under a smaller cap. This would add a stop condition, triggered only after
  several timeouts, by which point the session is already incomplete.

**Recommendation: (a), stated in the compute authorization alongside the 2,896 / 2,832 completion ceiling.**

## 11. In-run tokenizer admission replaced by the offline audit

**Facts.** The verified controller has no pinned transformers. The successor admits each call by the audited
pinned-tokenizer count, and stops at the first server/tokenizer parity mismatch, as the reviewed bridge did.
On all 5,728 stand-in requests the audit agrees exactly with the pure-Python tokenizer; for a withheld set the owner
reruns the audit before the run. The successor's runtime-only diff report states this change.

**Recommendation: accept.** The numbers are the same tokenizer's, computed before the run instead of during it.

## 12. A teammate's stress set (development material only)

Yue Yu's `evidence_memory_stress_v1` (on `origin/teammate/mac-track2`) is development material and was not merged or
used here. If the owner wants it in Stage 1, it would need a reviewed amendment that defines its role (development
only, or a third, separately powered set) before the withheld seed is drawn.

**Recommendation:** keep it out of Stage 1. Consider it for a later stage or for development diagnostics.
