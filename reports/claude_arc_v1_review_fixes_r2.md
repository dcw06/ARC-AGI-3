# Claude/ARC API path: review fixes r2

CPU-only changes based on `9ceed20921f915f533ec01bd6e25152458cc4825`.
No paid model call, online game, scorecard, GPU job, upload or launch was made.

## Confirmed and fixed

1. **Interrupted dispatch omitted its game.** Reproduced the original outcome:
   one dispatch, `games=[]`, active game in `games_not_started`, old audit passes.
   A game row is now registered before its first operation and retained for
   `KeyboardInterrupt`, `SystemExit` and ordinary exceptions. An unresolved
   dispatch counts once as uncertain; a proven pre-dispatch rejection counts as
   not sent. Earlier acknowledged actions are preserved. State/level credit comes
   only from acknowledged observations, never an adapter's interrupted mutation.
   The scorecard is still closed once and the interrupted run remains incomplete.
2. **Final permitted action won but was labelled action_cap.** Reproduced it
   with a one-action cap. Terminal-state checking now follows each acknowledged
   dispatch. Summaries explicitly retain `final_state` and `last_dispatch_status`.
   WIN and GAME_OVER on the last input are terminal; a nonterminal result remains
   `action_cap`. A POSIX interrupt during the acknowledgement commit cannot split
   its event from the corresponding counters; an actual SIGINT regression covers it.

The independent auditor derives attempted-game coverage and pending dispatches
from the events, checks uncertain counts and final states, and rejects omitted
rows or terminal mislabelling even when both summaries and all chain hashes have
been refreshed coherently. Reports carry `report_revision=2`. Revision-1 evidence
and `claude_arc_v1_cpu_checks.json` remain historical and unmodified; the updated
auditor refuses old report revisions rather than silently accepting weaker checks.

## History measurement, not a tokenizer result

`python -m research.claude_arc_v1.history_probe` deterministically measures 24
synthetic request shapes: 64x64 grids, one/two-digit and mixed colors, one/three
frames per observation, and zero/one/three/six transitions. No provider endpoint,
model tokenizer, live game or engine action is called.

Six transitions, rendered complete request:

| Pattern | Frames per observation | Characters / UTF-8 bytes |
| --- | ---: | ---: |
| One-digit | 1 | 113,859 |
| One-digit | 3 | 330,231 |
| Two-digit | 1 | 167,107 |
| Two-digit | 3 | 489,975 |
| Mixed palette | 1 | 133,827 |
| Mixed palette | 3 | 390,135 |

Actual Claude token counts are **not measured**. The default 32,768-token cap's
adequacy is unresolved. The prompt, history limit, truncation policy, output cap
and budget were not silently changed. The existing preflight still refuses an
over-cap request. Exact representative token counts (separately authorized), or
an explicitly reviewed selection/configuration change, are needed before relying
on a live history-enabled workload fitting this cap.

## Verification

- Seventeen new regressions cover the two fixes, real acknowledgement interruption,
  pre-dispatch rejection, bootstrap/model interruptions, multi-action accounting,
  coherent rehash attacks, and history-size probe behavior.
- The two exact review regressions fail on original `9ceed209` code (two failures,
  zero errors), and pass on the repaired code.
- Original test modules remain unmodified; their results must be read together
  with the new tests, not substituted for them.

```sh
python -m unittest \
  tests.test_claude_arc_v1_report_r2 \
  tests.test_claude_arc_v1 \
  tests.test_phase1 \
  tests.test_phase4_v12_action_contract \
  tests.test_phase4_v13_action_contract
```

This is existing-environment macOS CPU verification, not a fresh Linux clone or
live API compatibility check. The detailed r2 receipt binds the tested files.
No new model/game evidence or provider invoice is established. Live defaults
remain disabled with a zero-dollar spending cap. No commit or push is performed
by this repair; the unrelated worksheet is preserved.
