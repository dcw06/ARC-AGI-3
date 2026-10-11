# Track 3 runtime v2: independent prelaunch repairs, revision 3

The review of `b39f9e6` found six gaps. This revision changes runtime ownership and independent validation;
the frozen scientific protocol, thresholds, schedules, prompts, horizons and authorization ceilings are unchanged.
Historical snapshots, checks and the consumed R6 attempt remain unchanged.

| Finding | Repair |
| --- | --- |
| Child startup and supervisor death | Record intent before each spawn; defer handled interruptions through registration and logging startup. A bootstrap remains in the supervisor group until its per-child recovery record is durable, then detaches. Outer cleanup stops that group before reading recovery records. An absent, inconsistent or uncertain ownership journal cannot certify group absence. |
| Installation label trusted | Require the split-install receipt, exact bundle/runtime/game-wheel bindings, versions, imports, timing, retained installer logs and all command-group cleanup. Both model and game installation commands use the same owned-process implementation. |
| Outcomes after technical failure | Withhold endpoints unless lifecycle, trajectory and required checkout checks all pass. Preserve failure diagnostics and cost accounting separately. |
| Live overrides | Live evaluation cannot disable checkout verification or replace frozen detector thresholds. Testing overrides require explicit rehearsal mode. |
| Reflection evidence omitted from sample | Bind the self-review sample to both verified run inventories, complete reflection evidence and the reconstructed suggestion actions as well as transitions. |
| Annotation hash treated as prior commitment | Before live pooling, verify an existing private Git commit containing the exact completed annotations and evidence-bound sample. A matching caller hash alone refuses. |

## Private self-review commitment

After both technically complete sessions, draw and inspect the sample with the existing self-review script.
Complete the annotations yourself. Before running any pooled comparison, commit them to a new local private
repository outside all project checkouts:

```sh
python scripts/commit_stagnation_supervision_selfreview.py \
  --sample <private/sample.json> --annotations <private/annotations.json> \
  --repository <new-private-repository> --receipt <private/commitment.json>
```

The command requires your configured Git identity, refuses reused destinations and incomplete annotations,
and performs no upload or comparison. Keep the repository and receipt private. Live pooling additionally requires
`--annotations-commitment <private/commitment.json>`. It reads the immutable commit objects and verifies both blobs
against the current evidence before computing comparisons. This enforces the commitment-before-computation step;
it does not turn the sole researcher's unblinded review into an independent review or an externally timestamped record.

## Scope and remaining gates

CPU rehearsals use a scripted model and injected GPU telemetry; they establish no real GPU compatibility or setup
timing. A new review lock requires exact private-package review, Gate 4 evidence and separate session-1 source,
compute and launch decisions. This revision authorizes nothing, creates no reservation and launches nothing.

Session 1 remains at 633 completions (600 policy, 32 reflections and one canary), 5,400 seconds authorized,
5,100 internal and 4,800 study cutoff. Session 2 remains separately gated. Exposed games, unblinded review,
exploratory ls20 display effects, the noncertifiable false-interruption gate and potentially identical repeats
remain scientific limitations.
