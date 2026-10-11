# Track 1 pre-GPU review: edc9566

Review scope: track1-successor-runtime-v1 edc9566 and status ledger 1653b36.
Review is CPU-only, on macOS, using an isolated Git clone with historical objects.
No project-source edits, real approvals, reservations, provider requests or GPU launches.
The private final package itself is not available in this checkout.

## Confirmed findings

1. P1: scripts/feedback_action_v1_launch.py:80-97 spawns the supervisor and starts its drain thread before entering
   the cleanup guard. A KeyboardInterrupt at thread.start leaves the real spawned child alive and no cleanup receipt.
   The reproduction explicitly terminates and reaps the child afterwards.
2. P2: scripts/feedback_action_v1_launch.py:209-220 samples the final elapsed time before writing notebook-cost.json.
   A controlled clock advances from 59.9 to 60.1 during that write against a 60-second limit; the returned receipt
   still has error=null and a complete study status. live/notebook.py also removes extracted source afterwards,
   outside that sampled duration. Finalization must be bounded and included in the verdict.
3. P2: live_evaluation.py:116-145 does not independently verify the full request contract or rebuild observations.
   Changed system prompts, model IDs, schemas, message roles, current grids and available actions pass replay after
   recomputing request hashes. In live-mode evaluation they remain technically_complete and permit session 2.
   The live host rejects the first four request-contract mutations, but replay does not.
4. P2: live_evaluation.py:replay_episode/evaluate_session does not justify terminal labels or reconcile run totals.
   Setting a non-winning episode's stop_reason to win, or setting calls/dispatches to zero, still passes live replay.
   Rebuild counters, terminal/cap reasons, final observations and pair accounting from retained steps and calls.
5. P2: live/service.py:123-148 validate_ready accepts canary completion counts of 129 (cap 128), zero and true,
   and matching negative prompt counts. The independent output evaluator calls this same validator.
   Independently enforce the host's integer, positivity, prompt/context and completion-cap checks.
6. P2: live_evaluation.py:378 onward evaluate_sessions trusts prior evaluations without binding them to the supplied
   runs. An altered response paired with its earlier successful evaluation still yields technically_valid_both_sessions=true;
   independent re-evaluation rejects the altered run. Bind each evaluation to the exact run inputs and re-evaluate.

## Validation

- Two unittest commands: 160 executions, 153 distinct tests; 150 distinct tests pass, 3 skipped, no failures/errors.
- Skips: Linux-only first-cell imports, Linux-only server-group test, pinned model-interpreter HTTP test.
- Full connected Linux/WSL rehearsals and a GPU install/load were not rerun here.
- derive --check: 11 derived files match.
- derive_runtime --check: 4 derived files, 8 verbatim files and 1 copied function match.
- Review notebook r6 refuses at the live gate, no nvidia-smi call and no temporary files left.
- launch-build refuses with unresolved private bindings and missing source approval.
- Earlier deleted-source/source-lock findings and guide-revision finding are fixed.

## Reproduce

Use an isolated checkout of edc9566 with the project's CPU test dependencies installed:

    /path/to/python reports/reviews/track1_prelaunch_edc9566/review_repros.py /path/to/edc9566-checkout

The script writes only temporary CPU test evidence. JSON output is diagnostic, not approval or compute authority.
All sleeping test processes are explicitly killed and reaped. SyntheticSpec overrides only synthetic-test protocol
and development membership; it is not used by the actual live launcher.

## Before launch

Fix these findings in their derivations, add negative-control regressions, rebuild the public and private snapshots,
and repeat Linux connected fault checks. Review the final private notebook and its exact attachments/image. Obtain
new scoped evidence bindings, source approval, compute authorization and a new single-use reservation/claim for the
one replacement session-1 attempt under amendment A1. The original failed attempt remains consumed. Session 2 is
not authorized by this review. Old package locks/approvals cannot cover the changed source.
