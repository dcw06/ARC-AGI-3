# ls20: DFS navigation with reassessment after stalls

DFS chooses navigation actions. The VLM supplies a path-color judgment and, when
needed, a new color assessment or exploratory move. This separates route finding
from the previous failure to recover from blocked moves.

| Component | Behavior |
| --- | --- |
| Terrain | Visible 64x64 screen; full 5x5 player footprint, five-cell directional moves |
| Floor color | Supplied VLM judgment, new model assessment through a callback, or initial k=4 vote when no model is connected |
| DFS | Iterative, cycle-checked search; neighbors ordered by distance to the cross, then action ID |
| Collision check | Full footprint at every intermediate position of a move |
| Execution | Dispatch one planned action; check the observed player center before continuing |
| First blocked move | Record the directed edge as blocked and replan |
| Repeated blocked moves | Two consecutive stationary moves trigger color reassessment even if the earlier answer was confident |
| Other reassessment triggers | No usable route or three visits to the same position |
| Unknown reassessment | VLM may use up to eight exploratory actions, then reassess; no forced color conclusion |
| Success | Observed player center reaches the initial cross center; level completion remains separate |

The planner reads no engine internals, demonstration routes or future frames.
It uses the existing board-specific visible detector for the player and cross.
Only the floor hidden beneath the original player and cross is filled using the
chosen path-color assumption. Newly visible pixels replace that assumption
when the player moves. The cross's underlying floor remains an explicit
assumption. Color alone is not proof of traversability.

DFS searches virtual positions without dispatching game actions. It does not
guarantee a shortest route. If its route exceeds the remaining action budget,
the controller stops instead of silently switching search algorithms. An
unexpected displacement also stops the controller rather than assuming a move
succeeded. Blocked edges remain excluded for the episode; reopening edges in a
changing world is outside this static-maze pilot.

Limits are 24 actual moves, eight exploratory moves within that total, two
reassessments, and at most 11 model callbacks (one initial assessment, two
reassessments, eight probes). Existing request builders allow at most 256 new
tokens per callback. A deployment adapter must also enforce native prompt/token
counts, HTTP limits, owned-process cleanup and its final lifecycle deadline.
The controller itself does not certify a GPU lifecycle.

When no model callback is connected, the controller stops with
`reassessment_required` or `path_color_unresolved` if it needs new model
evidence. It does not fabricate an assessment or relabel an uncertain answer as
the kNN vote. There are no automatic resets or episode retries.

## Integration

```python
from research.ls20_dfs_v1.controller import run_episode

result = run_episode(
    initial_observation,
    owned_offline_engine,
    durable_event_journal,
    assessment={"path_color_id": 3},  # Actual retained VLM answer, or omit.
    complete=bounded_model_completion,  # Receives a request body; returns text.
    deadline=admission_deadline,
)
```

Omitting `assessment` with a callback asks the VLM for an initial color judgment.
Omitting both uses the k=4 estimate and makes no model call. A supplied null
assessment remains unknown. `audit_episode` reconstructs plans and model
requests, reuses retained replies without inference, and replays actual actions
on a fresh engine; every event and outcome must match.

## CPU execution

`scripts/run_ls20_dfs_v1.py --help` documents a Linux/WSL runner that uses an
existing pinned game interpreter. Supply the initial JSON and its hash, local
game environment and receipt hash, game Python path and a new output directory.
An optional `--assessment` file reuses a color judgment without model inference.
The runner creates an owned CPU worker, executes DFS, independently replays the
actions, verifies process cleanup and preserves the result and event log. Its
default lifecycle budget is 300 seconds. It never installs packages, contacts
Kaggle, launches a GPU, or makes new model requests.

Run unit/regression checks with `python -m unittest tests.test_ls20_dfs_v1`.
Previous experiments and their consumed attempts remain unchanged. This is a
planner-assisted navigation test, not evidence that the VLM learned to plan or
that the agent can solve the whole level. A future GPU package must receive its
own review and authority.
