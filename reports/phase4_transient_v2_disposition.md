# Transient v2 R1: independent acceptance and decision inspection

**Experiment closed: no demonstrated benefit. Do not repeat unchanged.**
Further work is limited to a separately reviewed observation-grounding diagnostic;
this closure grants no new model-call or GPU authority.

The frozen v2 replay passes. This six-episode, 120-action ft09 development
comparison demonstrates **no solving improvement**: both arms completed zero
levels. It does not establish that transient-frame exposure can never help.
The no-example prompt remains unpromoted, and Phase 4 remains open.

## Integrity and independent replay

Every one of the 156 downloaded files matched its byte length and SHA-256 in
`phase4_transient_v2_download.json`; the local directory had no extra or missing
files. All 763 frozen source bindings and both review artifacts also matched.
The v2 evaluator was used unchanged, with `live=True` and a 3,300-second limit.

Replay checks reconstructed trajectories, paired initial states, isolated episode
identities, requests and actions, selected intermediate frames, retained
tokenizer/server prompt-count parity, token/context bounds, progress counters,
evidence completeness, deadline ordering, and final cleanup. It confirms 60
acknowledged actions in each arm, zero completed levels, and three paired ties.
Token parity here verifies retained tokenizer/server counts and request bindings;
it is not a new model inference or a fresh tokenizer re-execution.

Finalization verifies dependency/source removal and the independent GPU cleanup
receipt (no remaining owned groups/processes). Notebook elapsed time was
754.450747112 seconds. This is acceptance of retained evidence, not a current
query of the now-ended GPU session.

Full machine-readable results: `phase4_transient_v2_final_replay.json`.

## Did exposure change subsequent decisions?

Each treatment episode exposed a non-null selected frame on decisions 2 through
20: **57 exposed requests** overall. All 57 resulting actions matched the control
action at the same paired decision index. Each episode moved to `(32,32)` on
decision 2, then repeated that action through decision 20: 18 adjacent repeats
per episode, or 54/57 adjacent opportunities in each arm (94.74%).

Pairs 0 and 1 have identical action sequences across arms, with equal observation
payloads after removing the new field. Pair 2 differs only on decision 1:
control clicked `(32,16)`, treatment `(32,12)`. The treatment field was null at that
point, so this is not evidence of a response to an exposed transient frame.
Subsequent observation payloads in that pair differ; equal step indices alone
are not a controlled causal counterfactual after a divergent action. Both arms
nevertheless selected `(32,32)` on every subsequent step.

The observed exposure produced no subsequent action divergence in these matched
sequences and no completed-level improvement. This supports neither promotion
nor a claim that the model cannot ever use transient information. The trial is
limited to one game, three paired request seeds, and 20 actions per episode.
No game-source-derived interpretation or privileged inputs were needed for this
inspection. The configuration remains E1S-R-derived `arc_action_v12`.

## Archive and clean-checkout reproduction

Archive: `evidence/phase4-transient-v2-r1-completed.zip` (2,404,312 bytes).
SHA-256: `8d6c49a8edbcb75067fb5519282b5d62078260988c462ed0b8fd8c5af965145e`.
Its 165 members retain outputs, console log, provider observations, download
manifest, source/compute approvals, launch and quota receipts, execution lock,
and consumed reservation/claim. `phase4_transient_v2_archive.json` records each
member's size and checksum. The replay script validates the entire archive before
extracting into a temporary directory and invoking the frozen evaluator.

From a checkout containing these deliverables, using the project's Python 3.12
CPU/game environment:

```bash
python scripts/replay_phase4_transient_v2_archive.py --output /tmp/transient-v2-replay.json
```

On this machine:

```powershell
wsl -d Ubuntu --cd /mnt/c/Users/jjzzw/Desktop/AGI /home/jingjing/.local/share/agi/dev-env/bin/python scripts/replay_phase4_transient_v2_archive.py --output /tmp/transient-v2-replay.json
```

Tested with Python 3.12.3, arc-agi 0.9.9, arcengine 0.9.3, numpy 2.5.2,
requests 2.34.2, and pydantic 2.13.5. This command needs no credentials, model
weights, GPU, or ignored environment/game assets. A temporary `git archive HEAD`
checkout plus the three new replay/archive deliverables produced an exactly
matching result with no `reports/runs` directory. This tests clean repository
inputs with the existing CPU environment, not a fresh dependency installation.
See `phase4_transient_v2_clean_checkout.json`. Preserve Git blob line endings when
checking out frozen source, for example with `core.autocrlf=false`.

## Accounting and final disposition

The one 3,600-second authorization and reservation remain **consumed** and their
files are unchanged. The provider reports COMPLETE and zero currently reserved
seconds. Observed account usage changed from 3,119.043 to 3,883.525 seconds:
**764.482 seconds**. This account-level delta is not an attempt-specific bill.
Raw provider duration strings are malformed and the raw allowance disagrees
with SDK-converted allowance. Exact billed seconds remain unknown. Sparse queue
observations also do not establish an exact GPU start or finish time.

Final disposition: accept this bounded development run's retained evidence;
record no demonstrated solving improvement; do not promote the treatment or
authorize another attempt. Unused nominal reservation is not new spending
authority. Production one-scorecard/110-distinct-game certification, production
`C_admit`, and exact billing remain unresolved.
