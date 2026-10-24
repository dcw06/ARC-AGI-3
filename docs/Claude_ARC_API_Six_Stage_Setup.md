# Separate Claude + ARC API evaluation path

October 23, 2026. Implementation and CPU rehearsal only. No paid inference,
ARC scorecard, online game, competition run, upload or publication has been
performed or approved by this setup.

The historical Qwen/Kaggle agent and frozen study packages are unchanged. This
new path reuses `agent.e1_policy.CompletionClient` / `CompletionResult`, the
existing `Observation`, action serializer, and no-retry ARC adapter. It has its
own minimal controller, prompts, configuration and private evidence directory.
It is **not** the historical E1S-R prompt under a different model name.

## Stage 1 — connect the backend, without executing

The official model-specific page lists `claude-opus-5`. No silent substitution
with Opus 5.5, another model or another provider is made. Account-specific access
has not been tested. This path performs inference, not weight training.

- Model reference: https://platform.claude.com/docs/en/models/opus-5/overview
- API console: https://platform.claude.com/
- Messages: https://platform.claude.com/docs/en/api/messages/create
- Token counting: https://platform.claude.com/docs/en/build-with-claude/token-counting

Use the existing Python environment; no package installation is required for
the credential-free plan or tests. The live ARC adapter is pinned to installed
`arc-agi==0.9.9`, matching the existing repository contract. Do not upgrade the
environment silently. Direct HTTP is used for Anthropic; the Anthropic SDK is
not required. Live process-ownership protection requires POSIX (macOS or Linux;
use WSL on Windows). Planning and portable tests require no server or credentials.

```sh
.venv/bin/python -m research.claude_arc_v1.cli
.venv/bin/python -m unittest -v tests.test_claude_arc_v1
```

The first command prints `plan_only_no_network`, even if keys already exist in
the shell. Defaults are `live_enabled=false`, LS20, online-development mode,
96 policy calls, 96 actions/game, 2,048 output tokens, 32,768 input tokens,
120 seconds per HTTP operation, 1,800 seconds for the run with 30 seconds
reserved for closure, and **$0** spending authority. These are proposed limits,
not evidence they suffice for solving.

For a later authorized run, set personal environment variables
`ANTHROPIC_API_KEY` and `ARC_API_KEY`. Each key comes from its own account;
neither is a GitHub/Kaggle key. Do not send credentials in chat or commit them.
`.env` is already ignored. The new CLI intentionally does **not** auto-load
`.env`, so merely opening a checkout never acquires implicit live credentials.

In Bash or zsh, read each value without displaying it or placing the literal
key in shell command history:

```sh
read -rs ANTHROPIC_API_KEY
export ANTHROPIC_API_KEY
read -rs ARC_API_KEY
export ARC_API_KEY
```

Keep a personal config under `.cache/`, not in a shared notebook:

```sh
cp config/claude_arc_v1.example.json .cache/claude_arc_config.json
```

Before enabling execution, review the model ID, API version, thinking mode,
effort, current prices, output/input caps, timeouts and explicit dollar budget.
The example's $5/$25 per million input/output tokens are taken from the
model-specific page; check them again before a paid run. No prompt caching or
server-side tools are requested. Unexpected cache usage is rejected because its
pricing is outside this configuration.

The client reserves the configured maximum input/output cost **before** each
attempt. It also counts the input before generation. Transport failures retain
their full uncertain reservation and are not retried. Returned thinking tokens
remain part of provider output usage. The client-side accounting is not a
provider-enforced billing guarantee: set account-level spending controls too.
A client timeout does not prove the provider stopped billing/computing.

For the existing locally served model, change only the new configuration's
`backend` to `local_openai`, set the exact served `model`, and use a loopback
`local_model_url`. Set its API-token rates to zero only when it is genuinely a
local service; GPU/hosting cost is still separate. The existing server must
already be running and authorized. This setup never starts a GPU model server.
The local server must implement vLLM's chat-style `/tokenize` endpoint as well
as `/v1/chat/completions`; there is no silent tokenizer fallback. Both backends
use at most two model HTTP requests per admitted decision (count plus generation).

## Stage 2 — minimal baseline

Set `stage=baseline`. Inputs contain the current raw integer-grid frame sequence,
state, level counter and legal actions. There is no teacher solution, annotated
mask, rulebook, previous game memory or external filesystem/tool access.

Each iteration requests one action, validates strict JSON, checks current
legality and coordinate types, dispatches once, and observes the result. Invalid
output stops the attempt; it is not repaired or replaced with a hidden fallback.
GAME_OVER stops the game; no resets are generated by this baseline. Every game
uses a fresh policy instance. The existing historical agent is not modified.

Model input uses text grids in both backends. Images are not silently added.
Claude uses an explicit adaptive-thinking/effort configuration. Seed and sampling
parameters are not fabricated for unsupported Anthropic options. Consequently a
comparison is between declared model/serving configurations, not an isolated
weight-only causal test. Thinking can consume the entire output cap: truncated
responses are recorded and refused, never dispatched.

## Stage 3 — add discovery components one at a time

Use separate config copies, attempt directories and reports for these cumulative
conditions. Never mutate a running attempt or mix its outputs with another arm.

| `stage` | Addition |
| --- | --- |
| `baseline` | Current observation to one legal action |
| `history` | Last six complete before/action/after transitions, with omitted count |
| `hypotheses` | At most eight reported claims, uncertainty/status and evidence IDs |
| `experiments` | A short distinguishing purpose for the action selected now |
| `world_model` | Prospective predictions and observed checks of any-frame change, final-frame change and level increase |
| `planning` | At most four short proposed steps; execute only the current action and re-observe |

The hypothesis memory holds **reported claims**, not certified facts. Provenance
checks ensure cited IDs were supplied, not that the claim is true. Empty or
unknown answers are allowed. Per-game memory starts empty; claims are cleared
on a level increase to avoid automatically carrying layout-specific coordinates.
Automatic selective cross-level rule transfer remains future work.

**History-size risk (CPU measurement, no Claude token count).** With six
transitions of synthetic 64x64 one-digit grids and one frame per observation,
the rendered request contains 113,859 characters. With three frames per
observation it contains 330,231. Two-digit grids are larger. These are character
and UTF-8 byte measurements, not token counts and not proof that the 32,768-token
input cap is sufficient or exceeded. The existing preflight refuses an over-cap
request; it does not shorten history. Before a live history-enabled condition,
measure exact backend counts on representative frames under separate authorized
access, or explicitly review a smaller history limit / revised budget. Do not
silently change selection or token caps during an attempt. Reproduce locally:

```sh
.venv/bin/python -m research.claude_arc_v1.history_probe
```

World-model checking here is a small declarative prediction checker, **not** an
executable learned simulator. Planning is model-proposed bounded text, not a
verified search planner. Generated Python is never executed. These additions
make the proposed experiment possible; they do not demonstrate learning or
better solving. Score predictions made before an action, report coverage of
non-abstained predictions, and keep change distinct from progress/usefulness.

## Stage 4 — development and evaluation boundaries

LS20 is the default development game. Keep the human worksheet, earlier manual
rules, masks and solutions out of these inputs. Fresh request memory prevents
carryover from earlier runs; it cannot remove prior human/model/game exposure.

All 15 games previously tested by this project are **exposed development games**.
Do not call the other 14 fresh holdouts merely because this new code has not
played them. A new evaluation list needs an exposure ledger and an owner-reviewed
freeze of code, prompts, settings, game versions/order and budget before access.
`exposure=reserved_evaluation` is a label, not proof a freeze/ledger exists.

For the model comparison, use the same stage, text observations, tools,
starting-state checks, game order and action/model-call limits. Freeze the
selected settings for each model. Closed-loop arms naturally visit different
states after different actions; do not claim all subsequent observations match.
Use separately authorized fixed-observation probes if identical-input inference
comparison is required. Deterministic repeats are reproductions, not independent
trials. Neither stage enables retrieval of game source or teacher annotations.

## Stage 5 — online ARC scorecards

Toolkit and competition restrictions:
https://github.com/arcprize/ARC-AGI#competition-mode

Scorecard documentation:
https://github.com/arcprize/docs/blob/main/docs/scorecards.mdx

This path uses remote-only requests with the official API origin from its own
config (`https://three.arcprize.org`), rather than `OperationMode.NORMAL`, which
can also load local environments. It implements the existing toolkit's online
wire contract through `RemoteFrameworkAdapter`; it does not patch ARC's SDK.
There are no anonymous-key calls, redirects or automatic HTTP retries.

Development config: `mode=online`, an explicit `games` list (default `ls20`).
Prefixes resolve only when the live inventory has exactly one matching game.

Competition config: `mode=competition`, **`games=[]`**. The controller takes the
entire live inventory, opens one competition scorecard and initializes each game
at most once. It does not fetch an inflight competition score. A resource cutoff
may leave games unplayed; `games_not_started` records this and official scoring
still covers the full available inventory. This API competition path is not a
Kaggle notebook submission or a claim of prize eligibility/verified ranking.

Nothing runs unless the personal config enables it and the caller explicitly
confirms the relevant scopes. The following is a **later, paid/live command**,
not part of setup verification:

```sh
.venv/bin/python -m research.claude_arc_v1.cli \
  --config .cache/claude_arc_config.json \
  --execute --confirm-paid-api --confirm-online-arc
```

Competition additionally requires `--confirm-competition` and a separately
reviewed frozen configuration. Do not use competition for debugging. Opening or
initializing may consume an attempt even if a later call fails. Unknown outcomes
stop the attempt; reconcile the retained card ID on ARC's site, never launch an
automatic replacement.

Every HTTP operation runs in an owned subprocess with an absolute parent deadline,
bounded response size, atomic result publication and kill/reap cleanup. Closing
the scorecard is attempted once in the controller's `finally`, even if the close
intent log fails. Closure may itself be uncertain and is reported as such.
An OS/host kill or power loss cannot guarantee remote scorecard closure.

## Stage 6 — audit and report before publishing

Evidence goes to a new owner-private, Git-ignored directory under
`.cache/claude_arc_runs/`. No credentials are recorded. Requests, API responses
(including any API-provided thinking blocks), observations and scorecards are
private research data; do not upload them automatically. Review provider data
terms and your own sharing scope before publishing even sanitized material.

```sh
.venv/bin/python -m research.claude_arc_v1.audit .cache/claude_arc_runs/ATTEMPT
```

The audit checks the event hash chain, observations, dispatch legality, continuity,
derived changes/predictions, action/level counts, caps and summary consistency.
Report revision 2 additionally checks every initialization attempt has a game
row, unresolved dispatches count as uncertain, and final state / terminal stop
reasons agree with the last acknowledged observation. An interrupted game is not
listed as unstarted. `final_state` means the last acknowledged state, not an
inferred remote state after uncertain execution. A win or GAME_OVER on the last
allowed action is still terminal, rather than `action_cap`. The new auditor
requires revision 2; preserve revision-1 artifacts and use their original
evaluator if reviewing them, rather than silently rewriting historical evidence.
It is a **record audit**, not an independent replay of a remote engine or a
provider invoice. Hashes are tamper evidence only relative to a retained trusted
copy/digest; they do not authenticate arbitrary rewritten histories.

Report:

- Per-game level gains and games fully completed (WIN), including failures and unstarted games.
- Official closed scorecard result and URL, separately from local counts.
- Acknowledged and uncertain actions, plus conservative attempt accounting.
- Repeated identical actions with unchanged final frames, described observationally:
  the metric does not establish the actions were useless, and HUD changes can hide repetition.
- Prospective prediction accuracy and its scored/abstained/unobservable denominators.
- Usage-based estimated cost, uncertain reservations, elapsed time and model/HTTP request counts.
- Stage, exact model, thinking/effort, exposure classification and frozen source/config bindings.

No completed levels, API compatibility, account permissions, scoring result or
cost advantage is claimed by the credential-free tests. Before any real attempt,
review the actual config and limits, verify account/key access without sharing
keys, and explicitly authorize the workload. Existing GPU approvals cover none
of these paid API operations.
