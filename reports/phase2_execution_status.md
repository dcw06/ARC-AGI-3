# Phase 2 parent diagnostic execution

The earlier no-treatment selection is an evidence-availability decision, not
proof that richer evidence or memory cannot help. Phase 2 is now closed with
no justified treatment after two E1S-R parent reproductions on cd82-fb555c5d,
environment and model request seed 104759 (the Phase 1 experimental seed).

The broken experiment policy factory has been repaired and is exercised by a
test that invokes the factory through the real cell runner and requires model
inference. The dedicated notebook starts two fresh worker and model processes,
uses unique run IDs, retains both bundles, and pins source, parent, prompt,
schema and model artifact hashes in its execution lock before launch.

Diagnostic compute reserves at most two RTX PRO 6000 hours from the existing
eight-hour Phase 2 family allowance, including notebook setup and failed work.
This leaves at most six hours before measured diagnostic runtime is reconciled.
Treatment budgets must fit the remaining family allowance; four hours per
treatment is a ceiling, not permission to exceed the family total. This capture
is parent-only and activates no treatment. No scored submission is authorized.

The cross-run validator revalidates exact proposals, sources and dispatched
actions, replays retained frames, requires contiguous complete trajectories,
and reports grid changes separately from levels and official scores. Its
signature excludes run IDs and model wording but includes ordered observations,
actions, rejection categories and dispatch outcomes. Exact signature agreement
is a conservative reproduction test; disagreement is reported explicitly.

A stable zero-level trajectory remains unsupported_other until evidence
identifies exactly one missing registered capability. No automatic E2/E3/E4
admission follows from zero scores or a matching trajectory alone.

Commands: make phase2-cd82-push, make phase2-cd82-status,
make phase2-cd82-output, make validate-phase2-reproduction.
Both V1 runs have been downloaded and validated. They reproduce the same
80-action unproductive trajectory; the retained-evidence review is recorded in
phase2_cd82_evidence_review.md. No single Phase 2 capability is justified.
The owner confirmed a provider runtime of 19m 25s and no other attempts.
The ledger is reconciled at 1165 seconds; config/phase2_closure.json records
the final no-treatment decision, validated by make validate-phase2-exit. V1
retains final frames and must not be relabeled as full-sequence capture. See
phase2_hardening.md for the separate V2 recorder and admission/accounting rules.
