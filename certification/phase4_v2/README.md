# Development lifecycle integration v2 — local implementation

Preparation v1 is unchanged. This revision implements the next concrete milestone:
an externally supervised 110-client worker, an offline environment package, and
independent local evidence checks. It is **not yet a runnable model-backed GPU
notebook or frozen target execution protocol**. No new compute is authorized.

## Offline artifacts

`evidence/phase4-v2-development-offline.zip` contains all **30 files for the 15
exact development environments** plus **31 environment dependency wheels**.
`reports/phase4_v2_offline_package.json` binds the ZIP and each file by SHA-256.
Only allowlisted development directories were downloaded, not holdout game files.
The packager rejects missing environments, symlinks, unsafe ZIP paths, duplicate
members, extra inventory and checksum changes. The local entrypoint also checks
the mounted environment files against this manifest before starting a child.

The environment dependency closure passed an offline, ignore-installed,
binary-only resolver dry run for Linux x86-64 / Python 3.12. The portable wheel
hash receipt is in `reports/phase4_v2_integration_result.json`; the full resolver
report is `reports/phase4_v2_offline_dependency_resolution.json`. The package's
original `dependency_resolution_verified=false` is the historical build-time
state; the later resolver receipt supplements it rather than rewriting the ZIP.
This is not a clean Linux installation/import test. vLLM/torch/model-service
dependencies are **not** in this environment package and remain a separate gate.

## Supervisor and workload

`run_local.py` launches `worker.py` in a dedicated process group. The worker
uses the unchanged 110-row v1 manifest: repeated development games, exact seeds,
80-action limits, separate adapters/scorecards and opaque inference isolation
keys. It runs up to 110 client threads through one shared eight-worker bounded
queue. The current backend is scripted completion through E1S-R; there is no
model service startup or GPU launch path here.

The external local envelope is 60 seconds including cleanup, admission cutoff
at 50 seconds, 4 GiB group RSS, 64 MiB scratch/retained checkpoint bound, 50 ms
monitoring, one second graceful process termination plus five seconds verification.
The supervisor signals cancellation independently of worker progress, kills the
owned group if needed, checks group disappearance, and reads the final atomic
checkpoint after termination. Errors override completion flags; missing or
oversized evidence fails closed. The supervisor cannot convert a completed
worker into a certification pass; `evaluate.py` separately checks the results.

The evaluator requires exactly 110 client IDs, matching seeds/game/action caps,
action audit/journal agreement, legal action IDs/click coordinates, no duplicate
transactions, complete nominal request counts, bounded queues/resources and
matching finalization receipts. Unknown outcomes fail nominal acceptance even
when quarantine is legally contained. Resource checks here are CPU-only; GPU
UUID/VRAM/server-abort certification is not claimed.

Actual trajectory requests are hashed/counted. At most the first 64 completed
requests within 16 MiB retain full prompts. This bounded convenience sample is
not a representative capacity corpus. All scripted timings are explicitly
non-model timings; `C_nominal` and `C_admit` remain null.

## First 110-client local result: failed closed

The local run took **39.45 seconds**, retained all **110 client results** and
**110 acknowledged local scorecard closes**, and verified process cleanup.
75 clients reached their action caps; **35 quarantined**, seven each on `sp80`,
`vc33`, `s5i5`, `sc25` and `lf52`. The retained journals identify `ValueError`
after dispatch entry, but do not establish its underlying cause. No ambiguous
action was retried. The independent evaluator rejected the workload.

7,757 scripted requests and 64 trajectory prompt samples were retained. Peak
group RSS was 255,574,016 bytes; scratch peak was 18,492,152 bytes. This is useful
local integration/failure evidence, not target capacity or game-solving evidence.
The original checkpoints/evaluation and later independent reevaluation are in
`evidence/phase4-v2-local-110-evidence.zip`, checksummed in
`reports/phase4_v2_integration_result.json`. That report distinguishes the executed
run from subsequent local precheck hardening; there is no retroactive source freeze.

## Reproduce locally

Verify the archive hash against the package manifest and verify its members with
`package.verify` before extracting into a fresh directory. Then:

```sh
.venv/bin/python certification/phase4_v2/run_local.py \
  --environments /path/to/extracted/environment_files \
  --output /path/to/new-output-directory
.venv/bin/python -m unittest tests.test_phase4_integration tests.test_phase4_lifecycle tests.test_phase4 -q
```

The output directory must be new. Process-table access is required for external
RAM and cleanup checks; denied monitoring fails closed. No network or GPU is
needed for this local worker. The tests include deliberate hung processes and
resource faults under short local deadlines; they do not authorize provider runs.

## Remaining gates

1. Reproduce and explain the five environment/dispatch failure cases without
   changing the frozen parent or retrying ambiguous actions.
2. Add the model-backed service under external GPU UUID/VRAM/process monitoring,
   per-request tokenizer/server parity and bounded shutdown. Verify dependency
   installation on a clean target-compatible offline runtime.
3. Register a representative real-trajectory capacity measurement design, then
   obtain actual model measurements; never reuse fixture/scripted rates.
4. Build and review the offline target notebook, then freeze a new execution lock
   and separately approve/reserve the proposed one-attempt eight-hour budget.

`budget_proposal.json` authorizes zero seconds, with no credit from the retained
prescreen reservation. No notebook was uploaded or GPU session started.

Even a future pass certifies only **110 clients repeating 15 development games
with separate scorecards**. The production **one-scorecard, 110-distinct-game**
lifecycle remains an explicit separate gate. H1/H2 and advanced scheduling remain
untouched. Owner accounting recollection is recorded as “no additional sessions
recalled,” not verified session history; all eight prescreen hours stay retained.
