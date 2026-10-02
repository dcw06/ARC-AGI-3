# Research-track findings: focused verification, 2026-10-02

The three findings against historical Track 1 `e887e78` and Track 3 `463cea3`
are fixed in the current track worktrees. This report records independently
executed local checks of the existing fixes; it is not source approval, compute
authorization, a notebook review, or a launch-readiness declaration.

## Sources checked

| Track | Worktree | HEAD | Fix commit |
|---|---|---|---|
| 1 | `.claude/worktrees/agent-a5ca48cc34a0a87fa` | `687acc8` | `687acc8` |
| 3 | `.claude/worktrees/agent-ad85269782539a5c8` | `a2bc925` | `b3ce08b` |

Track 1 was clean. Track 3 contained pre-existing modified and untracked target
stack files, including its derivation script and closed-loop tests. No track
implementation was edited during this verification. These branches have not
been integrated into the root checkout by this task.

## Findings and verified behavior

1. **Track 1 session aborts.** `live/runner.py` checks F2a after each policy
   response and F5 after each dispatch. Per the clarified draft protocol, F2a
   fires on the seventh invalid response among an arm's first 24 calls: the
   final window rate is then certain to exceed 25%. Exactly six invalid
   responses do not abort, calls after the window do not count, and the window
   belongs to each arm across its episodes. F5 counts failed and unknown
   dispatches over the whole session and aborts strictly above 10%. Checkpoints
   precede the checks. An abort closes the current adapter, records partial
   evidence and `status=aborted`, and starts no later call or episode.
   The existing `always_invalid` regression now verifies seven calls, zero
   dispatches, one aborted episode, closed cleanup, and no next arm.
   Dispatch regressions cover 1/10 versus 1/9 and 2/20 versus 2/19, including
   unknown outcomes and durable evidence reload.

2. **Track 3 terminal reflection admission.** `supervision.py` preserves the
   transition and detector output, clears an old suggestion, sets remaining
   actions to zero at terminal states, and suppresses a due reflection. The
   regression exercises GAME_OVER at periodic and triggered call points,
   including the tenth periodic action, plus reset and level boundaries.
   No new reflection or suggestion is delivered after termination.

3. **Track 3 reflection completion.** The closed-loop runner retains the
   response, hash, tokens and finish reason before validation, then passes the
   reported finish reason to the supervisor. Non-`stop` completions (including
   a missing reason, passed as null) are invalid, retained and charged; no new
   suggestion is delivered. A structurally completed run can contain invalid
   reflections, which remain invalid in metrics and replay. Regressions cover
   `length`, null and `tool_calls`; independent evaluator tests replay these
   failures and GAME_OVER.

## Independently executed validation

The runtime was Ubuntu/WSL with
`/home/jingjing/.local/share/agi/dev-env/bin/python`. Run the following in the
respective track worktree, using that interpreter:

```bash
# Track 1: 38 tests, all passed (325.572 s)
python -m unittest \
  tests.test_feedback_action_v1_live \
  tests.test_feedback_action_v1_dispatch \
  tests.test_feedback_action_v1_denominators

# Track 3: exact reported boundaries, 2 tests, both passed (146.013 s)
python -m unittest \
  tests.test_stagnation_supervision_v1_closed_loop.ScriptedRehearsals.test_no_reflection_when_termination_or_a_boundary_coincides_with_a_due_reflection \
  tests.test_stagnation_supervision_v1_closed_loop.ScriptedRehearsals.test_reflections_that_did_not_finish_with_stop_are_invalid_charged_and_retained

# Track 3: broader check, 57 tests, 55 passed (353.776 s)
python -m unittest \
  tests.test_stagnation_supervision_v1_closed_loop \
  tests.test_stagnation_supervision_v1_live_evaluator \
  tests.test_stagnation_supervision_v1_intervention
```

The two exact tests also occur in the broader run; they are not additional
independent cases. Models were scripted; the real development engine checks
were local CPU checks. No GPU work was launched.

The initial native Windows test attempt could not import `arcengine`, `numpy`
or `fcntl`. It was not treated as validation of the Linux runner; the commands
above were subsequently executed in the configured Linux environment.

## Remaining target-package failures

The broader Track 3 suite is **not passing**. Its two failures arise in the
pre-existing, uncommitted derivation expansion:

- `Derivation.test_sources_are_the_reviewed_action_effect_history_files` raises
  `KeyError: scripts/rehearse_action_effect_history_v1.py`: the newly derived
  rehearsal source is absent from the historical review lock's bindings.
- `Derivation.test_counted_substitutions` expects 11 substitutions for the
  launch script, while the current derivation reports 12.

These remain target-package blockers. The historical lock must be preserved;
new source provenance and the current derivation must be reviewed and bound
in a successor package. Tokenizer audits, the ls20 selection decision, complete
target-stack review, source approval and fresh reservations remain separate
gates. Track 4's preparation sequence is outside this focused verification.
