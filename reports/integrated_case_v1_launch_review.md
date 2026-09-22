# Integrated case v1: launch-readiness review

Disposition: specification checks pass; **not executable or ready to launch**.
The user's request to check issues and launch is retained as intent to run the
integrated study. The blockers below are implementation/evidence problems, not a
request to repeat authorization. No reservation was created and no GPU was launched.
The historical coordinate/transient notebooks would execute different experiments.

## Blocking findings

1. **No integrated worker, evaluator, or notebook exists.** The frozen package is
   intentionally a case specification and rubric. The existing transient worker
   has a six-episode, 120-call schedule and 20-action loops. Its authority has the
   same historical scope; reusing it does not implement two eight-action episodes.
   Build a new namespace with explicit baseline/inventory/decision/feedback states,
   at most 25 study calls plus one canary, final feedback after the last action,
   and stop at the first environment-confirmed level increment in either episode.
   Each episode stops on its own progress; a technical fault stops the comparison.

2. **The service and request contracts reject this study's outputs.** A local
   execution of the historical request validator rejects max_tokens=2048 with
   `request settings`, and rejects the structured prompt even at 128 with `prompt`.
   Historical `service.audited_completion` also caps output at 128. The proposed
   inventory/decision/feedback need distinct exact schemas and bounded output
   contracts (2048/1024/1024); merely raising one limit would leave inconsistent
   guards, evidence limits and replay. Keep the baseline request byte-equivalent
   to the frozen control. Extend response retention, bridge validation, canary,
   worker and independent evaluation consistently in a new revision.

3. **Adaptive prompt and runtime budgets are not frozen.** The specification's
   19,584 generated-token arithmetic is correct, but it is not a tokenizer audit
   or provider-time budget. Questions are prose specifications, not exact request
   bodies. “All returned frames” plus accumulated declared hypotheses needs a
   precise frame/byte/history admission rule. The inherited service's 65,536-byte
   payload ceiling may reject multi-frame requests before context is exhausted.
   Do not silently truncate feedback or increase ceilings without review. Audit
   actual pinned-tokenizer requests and worst-case admitted adaptive payloads,
   then freeze wall time, admission cutoff, cleanup reserve, evidence ceilings
   and one fresh provider reservation. No elapsed-time allowance is inferred from
   the prior 632-second coordinate run: this workload emits much longer outputs.

4. **Scoring rules need an executable temporal binding.** The frozen A/B/C masks
   are initial-frame annotation units, not guaranteed persistent game entities.
   Never score later clicks against stale initial masks after an object changes.
   Intended target cells must bind the exact current pre-frame; separately assess
   correspondence to visible structure. If tracking admits multiple matches,
   preserve ambiguity rather than choosing the most favorable identity. Independent
   replay must bind prediction -> dispatch -> all returned frames -> feedback ->
   next choice. A valid but false prediction is a diagnostic outcome, not a
   technical acceptance failure. Mechanical checks must not claim to automate
   the rubric's human adjudications of intent, discrimination or behavioral use.

## Specification findings that do not block on their own

- Archive provenance, exact initial observation and specification hashes verify.
  Three 45-cell masks and five internal marking cells reproduce from pixels.
- Reflection and rotation are genuinely nonunique geometric descriptions here;
  the existing rubric correctly accepts either. This supplies no objective rule.
- The structured arm changes prompts, inference cost, retained declarations and
  feedback exposure together. It is a scaffold bundle; any improvement cannot be
  attributed solely to questions or inferred baseline reasoning.
- Baseline intent/prediction/update scores remain unobserved rather than failed.
  Only environment counters/WIN establish progress/completion.
- This is a previously source-inspected development case, not transfer evidence.
  Keep reference masks, game-source interpretation and historical future outcomes
  out of all model requests.

## Required verification before the requested launch

Implement and independently replay complete scripted paired trajectories, including
valid incorrect geometry/predictions, contradictory feedback, repeated justified
tests, missing/extra/late calls, invalid targeting, partial pairs, frame dimension
changes, payload exhaustion, token mismatches across the process bridge, progress
stops, dispatch/acknowledgement mismatch, and cleanup failure. Retain raw received
responses before validation. Verify exact baseline request equivalence and fresh
initial-state equality. Verify missing/mismatched/consumed authority fails before
installation/upload and that a second upload cannot occur.

Package a new GPU-disabled notebook, review its unpacked source and freeze the
actual compute ceiling. Record approval/reservation for that concrete revision;
never modify or reuse historical consumed reservations. Then submit once, privately
and unscored, download, replay independently and reconcile usage. Production
certification, workload-specific admission limits and exact billing remain open.

Reproduce this readiness check locally (no model, GPU or environment actions):

```powershell
.cache/kaggle-windows-client/Scripts/python.exe scripts/check_integrated_launch_readiness_v1.py
```

The script verifies the frozen case and tests actual historical guard rejections.
It is a readiness report, not an integrated runner or a passing launch certificate.
