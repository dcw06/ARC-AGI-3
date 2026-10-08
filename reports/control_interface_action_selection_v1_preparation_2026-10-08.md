# Milestone E paired observation probe: preparation handoff

The first package is prepared as the user-selected paired observation probe.
It compares raw observations with the same observations plus computed control
metadata. It does not install a game engine or dispatch game actions.

- Frozen real observations: 30 distinct contexts from 15 exposed development games.
- Research completions: 120, two arms × two counterbalanced passes per context.
- Counted HTTP request proposal: at most 131, including runtime checks.
- Hardware/time proposal: exactly one RTX PRO 6000, at most 3,600 seconds,
  one attempt, no automatic retries; 300 seconds reserved for cleanup.
- Offline token audit: 2,128,220 scheduled prompt tokens; maximum prompt 36,120.
- Scientific verdict: development diagnostic only, no policy promotion or
  game-progress claim. Semantic-invalid answers count as invalid outcomes.
- Approval/reservation/attempt: none created. No provider upload or GPU launch.

Review [protocol r1](control_interface_action_selection_v1_protocol_r1.md),
[runtime scenarios](control_interface_action_selection_v1_budget.json),
[CPU results](control_interface_action_selection_v1/cpu_checks.json), and the
[GPU-disabled source lock](../notebooks/control-interface-action-selection-v1-review-r1/review-source-lock.json).
The [notebook execution check](control_interface_action_selection_review_check_r1.json)
refuses at the live gate, makes no GPU query and leaves no temporary source files.

The public snapshot intentionally leaves personal account/model locations
unresolved. A separate exact, resolved private review copy and its lock are
retained locally under `.cache/github-review`. Private account facts,
historical acceptance, launch authority, attempts and raw runtime results are
not published. Existing smoke sources and the r10 snapshot reproduce unchanged;
no consumed attempt is reused or replaced.

The new experiment changes purpose, code hashes and request count. It requires
review of its exact private source package and scoped use, confirmation of the
new notebook attachments, and fresh compute authorization/reservation. The
successful smoke's at-most-12-request authorization does not cover this
131-request proposal. These are pending review steps, not code labels to fill
automatically. Redistribution work remains a separate review.

Reproduce the frozen cases and scoped controller derivatives with
`python scripts/build_control_interface_action_selection_v1.py --check`.
Run complete Linux CPU checks with
`python scripts/run_control_interface_action_selection_checks.py`.
The controller preserves subprocess ownership, descendant cleanup, absolute
request deadlines, cancellation, GPU/environment cleanup, evidence finalization
and the final lifecycle deadline. The new research-phase ceiling also bounds
each HTTP watchdog; overruns fail while emergency cleanup remains possible.
