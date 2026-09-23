# Phase 4 — development lifecycle passed; production certification and solving remain open

## Multimodal preflight v3 completed: image compatibility prerequisite passed

Frozen independent replay returns `image_input_verified`, with no review flags.
All three image probes reached vLLM and server/processor counts agreed. I2 and
I3 returned distinct correct answers; I1's valid but incorrect colour answer
is retained. Cleanup and finalization passed. See the
[v3 disposition](phase4_multimodal_preflight_v3_disposition.md).

All 24 downloads were verified and archived. Notebook elapsed was 789.925 s;
account usage increased 799.981 s, not exact billing. The attempt is consumed.
The compatibility prerequisite for reviewing the perception comparison is now
cleared; the comparison itself still needs completed implementation, budget
review and separate authorization. No perception or solving capability is
established by this preflight, and Phase 4 remains open.

## Historical preparation: multimodal preflight v3

The successor uses PyTorch processor tensors and distinguishes processor
execution failures from measured token-count disagreements. A real pinned
processor CPU regression reproduced the historical NumPy failure and verified
all image dimensions, patch geometry and full/manual counts (394 for I1,
1,378 each for I2/I3). The v2 source and classification remain frozen.

The new GPU-disabled review package and tests are documented in
[the v3 review](phase4_multimodal_preflight_v3_review.md). Separate source
approval and fresh compute authorization remain required. Actual vLLM image
dispatch is still unverified, and the representation comparison remains blocked.

Separately, [local perception groundwork](perception_v1_local_review.md) now
provides five boards, independent scoring dimensions, interface tests and a
transition-record contract. These are local infrastructure, not model results
or a frozen/authorized perception experiment. Phase 4 remains open.

## Multimodal preflight v2 completed: image path still unverified

The separately authorized v2 attempt completed; frozen independent replay and
cleanup passed. Startup took 624.321 seconds, including 482.438 seconds hashing
the model. The text control passed, but all three image probes failed locally:
the mounted fast processor accepts PyTorch tensors and the expectation helper
requested NumPy. No image request reached vLLM. The frozen verdict is
`token_accounting_mismatch`, and the perception comparison remains blocked.

All 24 downloads were hash-verified and archived. Account usage increased
777.475 seconds, not exact billing. The attempt is consumed; no retry is
authorized. See [disposition](phase4_multimodal_preflight_v2_disposition.md)
for the next local processor-contract repair and replay command.

## Historical preparation: multimodal preflight v2 startup repair

The proposed startup repair now has a separate v2 source namespace, preserving
v1 R2 and its consumed attempt. It adds timestamped startup stages and periodic
model-hash progress, raises the shared startup ceiling to 900 seconds, and
drains small log messages promptly. Probes and image-support blocking rules
remain unchanged. See the [new review](phase4_multimodal_preflight_v2_review.md)
and its local/package verification receipts for the frozen review state.

The new proposal remains one 1,800-second attempt, subject to separate source
approval and compute authorization. No new attempt has been reserved or
launched. The text-versus-image comparison and Phase 4 remain open.

## Multimodal preflight r2 run: startup timeout before any probe

Kaggle reported ERROR. The model host did not become ready within the frozen
750 s startup ceiling, so no probe was sent. The verdict is
`lifecycle_failure`, which carries no image-support finding, and the
perception comparison stays blocked.

Cleanup was verified, and all 20 downloads were archived. The frozen evaluator
reproduces the target's result. Monitor telemetry shows the pre-server stage
(model-tree hash through processor load) running more than 748 s, against
about 385 s in integrated v2. The cause is not isolated because that stage had
no timestamps. The attempt is consumed; account delta 918.581 s, not exact
billing.

Proposed r3, not built: startup stage markers and a 900 s startup ceiling
within the same budget. See the
[disposition](phase4_multimodal_preflight_v1_disposition.md).

## Multimodal image-input preflight v1: reviewable, not authorized

This is a zero-action Kaggle preflight. It inventories the model mount, loads
the mounted processor, sends one text canary, then four probes: a text control,
a 4×4 canary, and two different 64×64 boards at 1024×1024. Server prompt
tokens must match the mounted processor's count, and the image-minus-text
delta must equal the image expansion. Failures are classified as dependency,
server rejection, token accounting, image not consumed, or lifecycle. Any
unverified outcome blocks the perception comparison pending review.

24 tests and 10 supervised CPU modes passed with cleanup verified. Any review
flag, including `arithmetic_revision_required`, keeps the comparison blocked
(fixed in r2; r1 is superseded). The review notebook is
`notebooks/phase4-multimodal-preflight-v1-review-r2/`, lock
`8742c81b…57dbdc` (671 bindings). The actual-snapshot approval, package and
gate regression passed. The proposal is one 1,800-second attempt; source
approval and compute authorization are pending. See the
[review](phase4_multimodal_preflight_v1_review.md).

## Perception diagnostic v1: provisional protocol (not frozen)

This is a zero-action diagnostic of object identification, localization,
3×3-occupancy contour, same shape across colours, reflection versus rotation
and markings. It covers the ar25 frame plus four synthetic boards, and compares
the current grid text with a lossless 16 px/cell image. An action-interface
probe runs separately. A multimodal preflight on Kaggle, separately budgeted,
must pass before cases, scoring and budget are frozen and authorized. No model
call, reservation or upload has been made. See the
[protocol](phase4_perception_v1_protocol.md).

## Integrated ar25 v2 completed: inventory feasible, first decision invalid

Independent and clean-checkout replays passed. The compact inventory finished
with `finish_reason=stop` at 462 tokens (v1 hit its 2,048 cap), so output burden
is resolved. All four inventory regions missed every reference object
(IoU 0). The first decision gave a reversed target span `[16,25,16]` and was
rejected before dispatch, so the structured arm took zero actions. Control
repeated v1: eight clicks, zero levels. The remaining obstruction is grounding
and target specification, which is unisolated. All 45 downloads were archived
and the attempt is consumed; account usage delta was 658.957 s, not exact
billing. See the [disposition](phase4_integrated_v2_disposition.md). Earlier
entries are historical.

## Integrated ar25 v2: output contract repaired and frozen for review

The inventory is now a bounded coarse list: at most four bboxes, with no cell or
row-span lists. Row-span masks appear only for a selected decision target, and
contour accuracy is scored separately there against the initial-frame reference.
With the pinned tokenizer, maximum-size outputs for all three stages fit their
caps (worst 1,767/2048). Offline counting of the actual v1 cap body reproduces
the server's 2,048 tokens. `finish_reason` is retained from transport through
replay. Partial JSON at every stage, including the real v1 body, is retained and
stops the episode as `invalid_output`, with no repair, retry or downstream
scoring. 27 tests and 11 supervised CPU modes passed.

A worst-case valid eight-step history fits: every prior answer at maximum size,
largest one-frame request 33,068 of 60,000 tokens. Late feedback admits at most
four returned frames; larger transitions stop technically, without truncation.

GPU-disabled review notebook: `notebooks/phase4-integrated-v2-review-r3/`, review
lock SHA-256 `eba5b1a59d977e1448caa7934be860339591f7d3d7a74a5b75521e95704ec93c`
(897 bindings). R1 and R2 are superseded. R2's authority code still referenced
R1, which blocked approval recording. R3 fixes the reference. A new regression
runs the actual frozen snapshot through approval, reservation, packaging and the
packaged gate, and it fails on the R2 state. Source approval and separate compute authorization are pending;
no model call, reservation or upload was made. See
[v2 review](phase4_integrated_v2_review.md). The entries below are historical.

## Integrated ar25 v1 completed: technical pass, inventory stop

Independent archived replay and cleanup passed. Baseline used eight actions with
zero level increase. The structured arm returned incomplete inventory JSON at its
2048-token cap and stopped before taking an action. Later diagnostic stages are
unobserved; this does not establish scaffold efficacy. All 43 downloads were
verified and archived; the reservation remains consumed. See
[final disposition](phase4_integrated_v1_disposition.md). Production certification
and exact billing remain open. Earlier entries below are historical.

## Coordinate v2 completed; no wording promotion

The repaired target run and independent archive replay passed. Baseline accuracy
was 15/28 and explicit indexing 16/28; the predeclared wording threshold was not
met. Both scored 4/4 on the synthetic 8x8 grid and 7/16 on retained 64x64 boards,
a grounding lead with size/content confounds. Cleanup verified; reservation
consumed. Exact billing and production Phase 4 gates remain open. See
[disposition and replay](phase4_coordinates_v2_disposition.md). Earlier entries
below are historical.

## Coordinate attempt ended in tokenizer-manifest failure

Kaggle reports ERROR. All 23 downloaded files were verified and archived. A
revision-copy substitution corrupted the expected vocab.json digest; tokenizer
verification stopped startup before diagnostic responses. Capability results are
inconclusive. Independent process/GPU cleanup and source/dependency removal were
retained. The reservation remains consumed; no retry was launched. See
[failure report](phase4_coordinates_v1_failure.md). Older entries below describe
historical preparation and queue status.


## Paired coordinate diagnostic R2 ready for review

A new offline package freezes 56 requests (28 paired targets) across four retained
64x64 development boards and three synthetic size controls. The prior system
prompt already states grid[y][x]; treatment repeats indexing in the task-local
instruction only. Historical grounding/transient snapshots remain unchanged.

Twenty-one local tests passed, including scoring and lifecycle/authority failure
paths. Exact pinned-tokenizer audit, unpacked R2 notebook review, clean-checkout
archive replay, and synthetic single-launch packaging passed. Failed packaging R1
is preserved and superseded. The proposal is one fresh 2100-second provider
attempt, with 56 diagnostic calls plus one canary, zero actions/scorecards/retries.
No source approval, compute authorization, reservation, or model call has been
made. See [coordinate review](phase4_coordinates_v1_review.md) and
[final checks](phase4_coordinates_v1_final_checks.json). Production Phase 4 gates
remain separate.


## Completed grounding diagnostic: independent technical pass

Grounding R1 completed; all 24 downloaded files verified and frozen replay passed.
Exact diagnostic answers: grid reading 2/4, localization 0/4, changes 0/4; no
malformed responses or transport failures. Correctness is separate from technical
acceptance. The 1800-second reservation remains consumed; no follow-up run is
authorized. See [final disposition](phase4_grounding_v1_disposition.md).
Earlier status entries below are historical.


## Grounding diagnostic implementation ready for source review

The new `phase4_grounding_v1` package freezes twelve cases across four development
games/source groups, an independent grader, and the supervised zero-action,
zero-scorecard runner. Nineteen local tests passed, including valid-but-incorrect
answers, malformed output, transport/token failures, cleanup and authority gates.
The pinned tokenizer audit covers all twelve requests and one canary. The new
budget proposes 1,800 provider seconds (1,680 internal), not a reused hour.

The private/offline review notebook remains GPU-disabled; source approval and
separate compute authorization are pending. No reservation or model call was made.
See [review and budget](phase4_grounding_v1_review.md). The original draft below
is historical; the transient experiment remains closed with no demonstrated
benefit. Production certification, admission limits, and accounting stay open.


## Experiment closure and grounding protocol draft

Transient v2 is closed as **no demonstrated benefit** and must not be repeated
unchanged. A 12-case observation-grounding protocol is prepared from retained
observations only: explicit color-feature localization, coordinate lookup, and
frame-change identification. Six local tests and deterministic answer checks
passed. Protocol review, exact tokenizer auditing, and separate execution approval
are still required; no model calls or compute are authorized. See
[grounding protocol](grounding_diagnostic_v1_protocol.md).

Production one-scorecard/110-distinct-game certification, workload-specific
admission limits, and accounting remain separate open gates.


## Transient v2 R1 independently replayed - September 21, 2026

All 156 downloaded files verified, and the unchanged frozen v2 replay passed
trajectory, selected-frame, retained token-parity, deadline, and final-cleanup
checks. The archived evidence also replays from a clean checkout without ignored
assets. Both arms completed 60 actions and zero levels. All 57 decisions following
non-null transient exposure matched the paired control action at the same step.
There is no demonstrated solving improvement in this bounded comparison, not
proof the capability can never help. No treatment promotion or new run is approved.

The one-hour reservation remains consumed. Observed account usage increased
764.482 seconds; exact billing remains unresolved. Production certification and
production C_admit also remain open. See
[final disposition](phase4_transient_v2_disposition.md) and
[independent replay](phase4_transient_v2_final_replay.json).
Earlier sections below retain historical states.


## Transient-frame implementation review — September 21, 2026

The isolated transient-frame field is implemented in `certification/phase4_transient_v1`
with the no-example prompt held constant. Ten CPU regressions passed, including
independent selection replay, matched requests, failure paths, and the 120-action
cap. Clean-checkout inspection recovery passed on Windows and Linux using only
committed archives; the historical generator and lock remain unchanged. Six local
development episodes completed 120 scripted actions with independent replay.
These are integration results, not model-performance evidence.

An actual frozen-tokenizer audit matched all 600 historical target counts and
checked 600 paired archived requests. Maximum treatment prompt was 43,668 tokens;
per-request byte/context guards remain enforced without truncation. The new
private/offline GPU-disabled review candidate is
`notebooks/phase4-transient-v1-review-r3/`; R1/R2 are superseded snapshots.
See `reports/phase4_transient_v1_review.md` and the package review receipt. Source
review and separate compute approval/reservation remain outstanding. No GPU run
was launched, no prompt was promoted, and production certification/admission and
exact billing remain open.

## Offline information trace — September 21, 2026

The missing inspection generator and findings report were recovered exactly from
local Git objects; all 13 historical bindings verify, and temporary regeneration
reproduced all 11 artifacts. A new `ft09` trace separates observed transient frame
changes from retrospective game-source interpretation. The next policy call
omitted a two-flash outline signal, but this does not establish that animation
handling caused failure or justify a memory treatment. A single intermediate-frame
input addition and a six-episode comparison are proposed, pending local checks,
review and separate compute approval; no run was launched or prompt promoted.
See `reports/phase4_ft09_information_v1/findings.md`. These are E1S-R-derived
`arc_action_v12` development variants, not unchanged E1S-R admission evidence.
Production certification, production `C_admit`, and exact billing remain open.

## Closed-loop GPU result — September 19, 2026

The authorized closed-loop v1 R1 run completed on Kaggle and passed independent
replay of the archived evidence. All 15 matched game pairs completed their 20-action
episodes: 600 policy calls/actions plus the startup canary. Startup-inclusive
runtime was 1659.281 seconds (27 minutes 39 seconds),
within the 3,300-second internal deadline and 3,600-second authorized attempt.
Independent GPU/process cleanup, dependency/source removal, finalization hashes,
request/action bindings, initial-state equality, progress counters, and evidence
completeness passed. All 664 frozen source bindings still match.

Original vs no-example adjacent repetition was 95.1% vs 62.5%; both arms
completed zero levels and all 15 pairs tied on level progress. The 20-action cap
limits this to early progress; it does not rule out later benefit. Evidence and
usage observations are archived/reconciled; exact billing remains open. See
`reports/phase4_closed_loop_v1_results.md`. The single attempt is consumed; no
additional compute is authorized. Production one-scorecard/110-distinct-game
certification and production `C_admit` remain open.

## Historical closed-loop runner review — September 19, 2026

The runner and independent trajectory/terminal evaluator are implemented in
`certification/phase4_closed_loop_v1`. Twenty regression cases passed across the
final suite and targeted cap-test rerun. Supervised CPU lifecycle replay passed;
actual local game integration completed all 30 episodes and 600 scripted actions,
with independent replay passing. These are CPU integration results, not model
performance evidence. The private GPU-disabled review notebook is frozen at
`notebooks/phase4-closed-loop-v1-review-r1/`; all 664 bindings, decompressed code
and the fail-closed authority gate were checked. Source approval and separate
one-hour compute authorization/reservation remain pending. See
`reports/phase4_closed_loop_v1_implementation_receipt.json` and
`reports/phase4_closed_loop_v1_implementation_review.md`. No GPU run was launched.
The 20-action cap measures early progress; zero progress would not establish that
the prompt change can never help. Exact billing and production certification remain open.

## Historical protocol preparation — September 19, 2026

A controlled original-prompt versus no-example development comparison is prepared
in `reports/phase4_closed_loop_v1_protocol.md`, with exact prompt texts, a fixed
30-episode schedule over 15 games, matched environment/request seed 0, and a
20-action cap per episode. The separate one-hour budget proposal permits at most
600 policy calls plus a canary if later authorized; currently zero compute is
authorized or reserved. Three preparation tests passed. The protocol and dependencies
are hash-locked; runner implementation, local fault testing, notebook freeze and
separate source/compute approvals remain prelaunch gates. No diagnostic rerun or
production run is requested. Exact billing and production certification remain open.

## Latest diagnostic result — September 19, 2026

Diagnostic v4 R1 and independent archived-evidence replay passed, with all 45
requests plus the canary complete and final cleanup verified in 612.344 seconds.
All 45 actions reproduced the preceding diagnostic. For two initial observations,
relocating the example coordinates moved the model's click to the new example;
this supports example copying in those cases, not improved solving. Evidence is
archived and usage observations reconciled; exact per-job billing remains open.
See `reports/phase4_diagnostic_v4_results.md`. No new compute is authorized.

## Earlier diagnostic update — September 19, 2026

Diagnostic v2 R2 completed its canary and all 45 requests with verified cleanup,
but Kaggle reported ERROR after a floating-point request-window comparison
failed. A separately frozen v3 offline evaluator passes replay of retained evidence;
the historical notebook remains failed. Three regression tests preserve real
deadline, cleanup, inventory and token-count rejection. See
`reports/phase4_diagnostic_v2_r2_failure.md`. Paired initial responses show
example-coordinate sensitivity, not improved solving. No GPU rerun was launched;
exact billing and the production gates remain open.

## Current summary — September 18, 2026

**V13 passed the target development pilot**, including final notebook cleanup and independent local evidence replay. V14 now directly enforces independent GPU cleanup and the worker/client action-contract and parent bindings; five regression tests (19 negative mutations) and replay of the existing v13 evidence passed without a GPU rerun. Historical frozen sources and verdicts remain unchanged.

The successful configuration is **E1S-R-derived `arc_action_v12`**, with a revised prompt and constrained decoding; it is not unchanged historical E1S-R. Offline split-environment installation was verified on the target in v6 install R5, followed by actual model/trajectory validation in v13: Linux/Python 3.12, torch 2.10.0 distribution / 2.10.0+cu128 runtime, CUDA 12.8, vLLM 0.19.0 and transformers 4.57.6 on RTX PRO 6000. Earlier statements below about installation being unverified describe historical checkpoints only.

V13 completed 110 clients and 7,582 real requests, including 5,262 accepted ACTION6 actions, with zero policy or inference transport failures. Runtime was 4,500.288 seconds; monitoring and all cleanup checks passed. **Zero levels were completed.** Infrastructure validation does not establish useful solving.

The reviewed development-capacity disposition accepts `C_nominal = 39,322`, conservative empirical rate 1.411523016 requests/second, separate 20% service-time headroom, and `C_admit_candidate = 22,358` only as development projections. Production admission remains unset; no new spending or advanced scheduling is authorized.

The accounting reconciliation inventories 16 attempts and preserves known terminal/rejected/ambiguous outcomes. Exact per-attempt billing remains unresolved; aggregate quota observations are not billed usage or reusable reservation credit. The remaining production gate is one scorecard covering 110 distinct games, rather than 110 clients repeating 15 development games on separate scorecards. A separately scoped action-selection investigation is the next strategic priority; advanced scheduling has no observed allocation problem to address.

Current references:

- [Diagnostic v2 response-retention repair](phase4_diagnostic_v2_review.md): bounded response/token evidence is captured before validation and retained across bridge failures. Eighteen tests passed; a new GPU-disabled snapshot is frozen pending separate source approval and compute authorization. No GPU run occurred.
- [Three-arm diagnostic runner: frozen budget, cleanup, evidence and local tests](phase4_diagnostic_v1_review.md). GPU-disabled review only; 45 cases plus one proposed startup canary, no launch authorization or new target execution.
- [Offline action-selection investigation and unexecuted prompt probe](phase4_action_selection_investigation.md): 97.28% of clicks matched the prompt's example coordinates; 96.99% of adjacent action pairs repeated. This is descriptive evidence, not a causal finding or authorization for model calls.
- [V13 target evidence](phase4_v13_pilot_status.md)
- [V14 evaluator, capacity and accounting review](phase4_v14_review.md)
- [V14 replay receipt](phase4_v14_replay.json)
- [Capacity disposition](phase4_development_capacity_disposition.json)
- [Attempt-accounting reconciliation](phase4_attempt_accounting_reconciliation.json)
- [Remaining certification gate and action-selection scope](phase4_remaining_certification_gate.md)

## Historical checkpoints — preserved verbatim below

The following sections record the state at their original checkpoints. Their uses of “current,” “pending,” and “unverified” are historical, superseded by the current summary above.

# Phase 4 — V2 fixture prescreen passed; accounting pending

## v6 integrated development pilot — local pass; target launch blocked

The unified runner now connects the shared clock/store, worker, monitor, bounded
logs, retained readiness, monitoring through worker/model-group cleanup, and
independent evaluation. A retained actual-environment CPU run passed: 110 clients,
7,722 requests, 23.35 seconds. Requests and actions matched the archived v3 scripted
run exactly. Seventeen process/integration tests passed; related regressions and
packaging checks passed separately. No model inference or real GPU telemetry.

Current notebook: `notebooks/phase4-lifecycle-v6-review-r2/profile.ipynb`, with a
hash-bound source/protocol review snapshot. Private, GPU-disabled, no upload or
authority. Initial v6 review artifacts are superseded and preserved after fixing
pre-install import order. The corrected portable archive was hash-verified and
its local evidence reevaluated successfully after fresh extraction. Details:
`reports/phase4_v6_integrated_result.json` and `certification/phase4_v6/README.md`.

**Not launch-ready:** clean Linux/CUDA offline installation could not be verified
on this Darwin ARM64 host without Docker or a local model wheelhouse. Independent
target review and an approved execution lock plus separate reservation also remain.
No new compute authorized; prescreen hours remain retained. Production one-scorecard,
110-distinct-game certification and measured capacity remain open.

## v6 live-adapter and shared evidence wiring — implemented locally

The live-probe adapter exists behind an explicitly closed v6 authority gate.
Monitor samples/receipts carry a shared first-cell clock, with validated conversion
into evaluator fields. Injected resource evidence cannot pass target evaluation.
The monitor can use a cross-process-locked evidence store with component budgets
summing to 64 MiB and reserved failure receipts. Twenty-two adapter, monitor,
measurement and capacity tests passed; hardware calls were mocked throughout.

This is not a complete target runner. Migrating every output producer, GPU-bound
readiness, sampling through GPU cleanup, bounded logs, clean offline installation
and the new notebook/approved execution lock remain pending. No live hardware
query, GPU/model run, upload or budget change occurred. See the v6 README for the
exact implemented-versus-pending boundary.

## v6 injected resource monitor — integrated with outer startup gate

`certification/phase4_v6/monitor.py` validates binding, UUID/resource samples and
sampling gaps, retaining the first checkpoint before readiness. Its fixture-only
entrypoint runs under the outer owner; monitor errors cause a failing exit and
cleanup. Bounded telemetry retains the last complete checkpoint and reserves a
small failure receipt. All records explicitly identify injected resource evidence.

Six monitor tests, fourteen outer/handshake tests and eleven measurement/capacity
tests passed (31 total). Historical snapshot verification passed. Live GPU probes,
shared-clock evaluator integration, whole-output budgeting, target notebook
packaging and clean offline installation remain unfinished. No GPU/model run,
upload, new reservation, or capacity/Phase 4 completion claim occurred.

## v6 monitor-ready handshake — September 16 local checks

Worker release now requires a bounded atomic monitor acknowledgement binding a
fresh nonce and both owned PIDs. Missing, malformed, mismatched, oversized,
symlinked or late readiness fails closed. The global admission cutoff bounds the
handshake deadline. Thirteen handshake/process tests and eleven measurement/
capacity tests passed. This is explicitly local-CPU readiness, not GPU binding.

Target GPU readiness, continuous monitor/evidence integration, the new notebook
and clean offline installation remain pending. No GPU/model execution or compute
authority changed; the v4 notebook and historical evidence remain untouched.

## v6 outer ownership prototype — local process cleanup implemented

The new `certification/phase4_v6/outer.py` directly owns worker and monitor
session groups; its gated bootstrap prevents worker execution before ownership
registration. It enforces an external deadline, reserves cleanup time, and
verifies both groups are absent even when a leader exits before its descendants.
Local process tests cover monitor failures/hangs, worker failure, orphaned
TERM-ignoring descendants and pre-release launch failure. See the v6 README.

This does not yet replace the target supervisor. GPU-ready handshake, target
monitor/evidence/evaluator integration, bounded logs and clean offline installation
remain pending. No GPU execution, notebook upload or compute authority changed.

## Measurement integration v6 — local only, outer supervision still pending

`certification/phase4_v6/README.md` records the new timeline-instrumented worker,
bounded atomic checkpoint writer, telemetry coverage checks and additional
capacity evaluator. Seven new tests passed, including the 110-client mocked
request-invariance comparison; 11 passed with the v5 capacity tests and 65 in the
combined related local suite. Historical snapshot verification passed. No actual
environment/model performance measurement is claimed by that comparison.

The outer notebook watchdog/descendant ownership protocol, supervisor output
integration, clean offline install and approved pilot freeze remain unfinished.
The v4 notebook is unchanged and v6 direct execution is explicitly disabled.
Measured C_admit and new compute authorization remain absent.

## Development capacity design v5 — review draft, not a launch freeze

`certification/phase4_v5/README.md` scopes the approved development-only next
step and records the focused v4 source-review blockers: missing request timeline
events, no outer supervisor watchdog, incomplete retained-output size enforcement,
telemetry coverage validation, and unverified clean offline installation.
The existing v4 notebook is preserved, not approved for launch.

The new capacity arithmetic separates nominal wall-time throughput, a minimum-
window empirical rate margin, and 20% service-budget headroom. Four tests passed,
including concurrent timing, empty windows and malformed evidence. The calculator
is not an evidence validator and deliberately leaves actual C_admit unset; no
measurements or statistically guaranteed capacity are claimed. One eight-hour
pilot remains a proposal with zero authorization, not a new reservation. A new
runtime revision, reviewed pilot freeze and separate approval must precede GPU
execution; production one-scorecard/110-distinct-game certification stays open.

## Expanded local scheduler/fault matrix

`reports/phase4_scheduler_fault_matrix.md` records FIFO priority, exact aging
boundaries, 1/2/8-worker concurrency over 110 requests, model-error legal fallback,
forbidden workspace rejection, storage/finalization failure and cancellation
coverage. Nine new tests plus existing related suites passed: 54 tests together
and five real-process fake-service tests separately with approved process-table
access. The initial restricted process run failed resource monitoring; the
approved rerun passed. Frozen runtime/notebook sources remain unchanged.

This completes the added local regression matrix, not target GPU batching or
integrated full-game fault certification. Actual vLLM batching, realistic queue
tails, target filesystem faults and full-model lifecycle cancellation remain
measurement gates. No GPU execution or new authority was used.

## Model integration v4 — review notebook built, no execution authority

`certification/phase4_v4/README.md` documents the shared model-service path,
per-request tokenizer/server audit, single canary, external GPU supervision and
independent evaluator. The private review notebook at
`notebooks/phase4-lifecycle-v4-review/profile.ipynb` has GPU and internet disabled,
zero authorization and a standard-library-only pre-install gate. No upload or
model/GPU run occurred. Readiness remains false and capacity estimates remain null.

All 10 new tests and the combined 34-test sandbox-safe suite passed. A new full
43-test process-level rerun was blocked by the approval service's usage limit;
the prior local passes are not relabeled as that rerun. Focused target-path review,
clean offline installation, prospective capacity design, approved execution lock
and separate compute authorization remain launch gates.

## Terminal lifecycle v3 — local workload passed

The five v2 failure cases were reproduced twice under each old/new arm in fresh,
counterbalanced local runtimes. Cause: another non-reset action after acknowledged
GAME_OVER yields an engine response with no frames; strict parsing quarantines it.
v3 stops and finalizes at that terminal loss, without resetting, fabricating frames
or changing E1S-R policy. This is an explicit prospective lifecycle amendment,
not retrospective relabeling of v2. See `certification/phase4_v3/README.md`.

The snapshotted 110-client CPU run passed independent evaluation: 35 GAME_OVER
terminations, 75 action caps, zero quarantines, 7,722 acknowledged actions and
110 acknowledged local scorecard closes. Cleanup verified; 33 tests passed.
`reports/phase4_v3_terminal_result.json` binds the complete evidence/source archive.
Actual model integration, target GPU checks, real-trajectory capacity and the
production one-scorecard/110-distinct-game gate remain pending. No new GPU authority.

## Development integration v2 — local workload failed closed

See `certification/phase4_v2/README.md`. All 15 exact development environments
and 31 environment dependency wheels are packaged and checksummed; offline
Linux/Python-3.12 dependency resolution passed (not a clean runtime install).
The new external CPU supervisor ran 110 clients through the shared eight-worker
scripted-completion service. All 110 local scorecards closed, cleanup verified,
but 35 clients quarantined across five games: independent evaluation failed.
Evidence is in `reports/phase4_v2_integration_result.json`. Preparation v1 remains
unchanged. Model-backed target notebook integration, GPU resource checks and
real-model trajectory capacity are still pending; no target execution freeze or
new spending authority is claimed. The one-scorecard, 110-distinct-game production
gate remains separate from this repeated-development/separate-scorecard workload.

`reports/phase4_accounting_owner_recollection.json` records “no additional sessions
recalled” as tentative owner evidence, not verified history. The ledger retains
all eight prescreen hours, releases zero and transfers zero to the next run.

## Frozen development lifecycle preparation v1

`certification/phase4_v1/README.md` documents the frozen E1S-R source bindings,
explicit 110-client development-only workload, seeds, 80-action limits, resource
ceilings, acceptance rules and separate eight-hour budget proposal. Authorization
is zero. This supersedes the earlier draft for the implemented preparation scope.

Actual offline ls20 dispatch, inference-error legal fallback, cancellation before
dispatch and local scorecard finalization all passed with scripted completions.
The 19 targeted tests passed; final-lock evidence and environment hashes are in
`reports/phase4_lifecycle_v1_preparation.json`. This is not real-model inference,
target GPU evidence, remote finalization or a complete 110-client certification.
Full target orchestration/supervision, environment packaging, real-workload capacity
and new approval remain explicit launch blockers. Both V2 and new lifecycle locks
validate; historical Phase 2–3 verification remains valid.

## Owner-supplied provider duration evidence

The subsequent screenshot, recorded in
`reports/phase4_accounting_v2_version_count.json`, additionally confirms the
canonical notebook URL, PRIVATE visibility and **Version 1 of 1**. Its rounded
runtime of **18m 4s** is consistent with the Logs display. One saved version is
not a complete inventory of interactive sessions or failed starts; billing and
session-history limitations below remain unchanged.

The screenshot and pasted log are retained with hashes in
`reports/phase4_accounting_v2_screenshot.json`. Kaggle displays successful run
duration **1,083.8 seconds**, on **GPU RTX Pro 6000**. This is distinct from the
1,074.16-second internal timer and is not labeled charged GPU time. Provider
session ID, start/end timestamps and complete session history remain unknown.
All eight hours remain retained; no credit or new compute authorization results.
The earlier API-only collection notes below are historical evidence limitations.

## Accounting collection and separate certification draft

Read-only provider queries and their exports are documented in
`reports/phase4_accounting_v2_disposition.md`. Latest metadata still confirms
version 1, private visibility and RTX PRO 6000; status is COMPLETE. Explicit
version requests returned 404. Session ID, charged duration, start/end and complete
interactive/failed-session inventory were not available. No values were inferred
from the internal timer or the inconsistent account quota response. An append-only
ledger disposition retains all 28,800 seconds and releases/transfers zero; owner
confirmation remains requested, not received. Original result/evidence are unchanged.

`reports/phase4_full_game_certification_protocol_draft.md` and
`reports/phase4_full_game_budget_draft.json` propose a separate one-attempt,
eight-hour lifecycle experiment, with **zero authorized seconds**. They require
real dispatch/finalization, local fault tests, a frozen workload and real-trajectory
capacity bound, independent allowance verification and a reviewed execution lock.
Repeated development-game load is explicitly not 110 distinct official games.
No GPU run, retry or additional session was started during this preparation.

## Authorized V2 execution

The user authorized one private, unscored eight-hour V2 attempt. Reviewed source
and bound Phase 2–3 evidence were checkpointed in `7f85a80`; authorization,
reservation and the reserved notebook were checkpointed in `3a10d81`.
Attempt `p4-v2-20260915T104415Z` reserves 28,800 seconds. Exactly one upload was
accepted as version 1 of `daichongwei06/arc3-phase4-fixture-prescreen-v2`.
Kaggle confirmed private visibility, internet disabled and `NvidiaRtxPro6000`.
The provider completed the run, and the strict evaluator passed all eight windows
(8,800 requests). `C_nominal=419210` and `C_admit=252717` are frozen-rule fixture
projections, not realistic game throughput. First-cell elapsed time was 1,074.16
seconds, maximum queue age 8.73 seconds, and verified process/GPU cleanup 0.28
seconds. Peak VRAM was 72.22 GiB; peak process-group RSS was 14.06 GiB.

See `reports/phase4_prescreen_v2_result.json` for results and limitations, and
`reports/phase4_launch_v2.json` for launch bindings. The account-wide GPU counter
decreased between observations and cannot establish per-attempt billing. Exact
provider runtime and complete session inventory remain unresolved; all 28,800
seconds remain charged or reserved, with zero released. The terminal ledger event
consumes this attempt and prevents the current launch gate from reusing it. No
automatic retry, V1 run, scored submission or holdout access is authorized.

The checksummed output archive and inventory are recorded in
`reports/phase4_prescreen_v2_evidence.json`. All archived file hashes and sizes
were verified, and evaluation passed again after extraction to a fresh temporary
directory. To reevaluate from a clean checkout, extract the referenced ZIP into
a new directory and run:

```sh
.venv/bin/python scripts/evaluate_phase4_prescreen.py /path/to/extracted/phase4-prescreen
```

Next: obtain provider billing/session evidence to finalize accounting, then scope
full-game lifecycle certification covering environment dispatch, legal fallback,
cancellation and scorecard finalization. This service-only pass does not complete
Phase 4 or justify advanced scheduling. H1 remains preserved.

The preparation and review notes below describe the pre-authorization milestone;
their statements about zero authorized compute are historical, not current.

## Historical prelaunch handoff: reviewable target prescreen

The latest target protocol is `config/phase4_execution_protocol_v2.json`, with
`config/phase4_execution_lock_v2.json` binding the full packaged source/config
inventory. It supersedes the earlier target-profile draft for prospective
execution, without rewriting the Phase 2–3 archive or local preparation contract.
The executable notebook is `notebooks/phase4-prescreen-v2/profile.ipynb`; metadata
is private, offline and unscored. `make phase4-target-notebook` builds a review-only
copy. Nothing has been uploaded or run on a GPU.

V2 addresses the four pre-launch review findings. The bootstrap authorization
gate now uses only the standard library and runs with site packages disabled.
Worker errors override cancellation-ready state both during polling and after
termination. The final atomic checkpoint is retained before scratch deletion,
including errors appearing after the last poll or after worker exit.

The evaluator now requires retained protocol/lock copies, the reservation ledger,
GPU UUID/telemetry, resource peaks, successful worker evidence, the artifact and
tokenizer audit, and per-fixture server token usage for each fixed window. It
recomputes assignment counts, checks prompt-token parity and completion bounds,
and rejects missing evidence, nonfinite measurements, errors and breached limits.
The notebook retains the reservation ledger alongside its original claim.

The V1 lock and notebook are preserved as historical review artifacts and must
not be launched. Their supersession is not retroactive GPU evidence. The new
package remains review-only with zero authorization; no reservation, commit,
upload or GPU execution was made during this repair pass. A fresh review of V2
precedes any commit/approval/launch decision.

The frozen limits are 86 GiB device-wide VRAM, 128 GiB process-group RSS,
4 GiB worker scratch, 64 MiB retained measurement bound, 900 seconds each for
dependency setup and model/preflight startup, a 300-second request/queue bound,
10 seconds graceful process termination plus 5 seconds kill verification,
and the existing 27,540-second lifecycle including 600 seconds finalization.
These are conservative prospective limits, not observed measurements. GPU UUID
is discovered exactly once on an exclusive idle single RTX PRO 6000, retained
before model startup, and checked thereafter; it is not guessed before allocation.

The scope is explicitly **repeated fixture service performance** with the frozen
prefix cache still enabled. It cannot estimate uncached real-game throughput,
show improved game solving, or close Phase 4. Eight fixed 1,100-request windows
retain measured wall times and server token totals. Offline tokenizer counts
must match the server for every measured request. Capacity is recomputed as:

```text
C_nominal = floor(19800 * 8800 / sum(window_seconds))
guard_rate = 0.8 * min(1100 / window_seconds)
C_admit = min(C_nominal, floor(15840 * guard_rate))
```

All eight windows must complete without errors, `C_admit >= 8800`, and lifecycle
and cleanup checks must pass. These margins are empirical, not a statistical
confidence bound or hard capacity guarantee. Failures invalidate the attempt;
there is no selective window rerun, model restart or scheduler alternative.
After the windows, an extra completion is attempted while the supervisor
terminates the model process group. Success requires the group and all GPU
compute processes to disappear within 15 seconds. This tests process-level
model-service cancellation, not proof of a per-request server abort or that
decoding was active at the exact signal instant.

`config/phase4_compute_ledger.json` still authorizes **zero seconds**. To enable
execution, a reviewed approval reference and exactly 28,800 authorized seconds
must first be recorded. Only then can `scripts/phase4_budget.py ATTEMPT_ID`
create the single source-lock-bound reservation; a second reservation is rejected.
`scripts/build_phase4_target_notebook.py --reserved` refuses unreserved builds.
The launch gate now validates those prerequisites rather than always raising.
An approval boolean in the old draft cannot bypass it. The local output claim
prevents reuse of a run directory, but is not a distributed Kaggle replay lock:
the operator must launch the reserved notebook exactly once and reconcile provider
attempt inventory before considering any future execution.

The notebook charges setup/startup/failure time from the first cell and retains
the full eight-hour reservation even if output is missing. Provider startup
before the first cell and accounting reconciliation remain provider evidence,
not inferred from the local timer. Measured runtime never automatically releases
reserved compute. Output retains the execution lock, protocol, GPU binding,
claim, partial/final measurements and cost receipt; raw model text is not retained.
Worker scratch and temporary packaged source are cleaned. An incomplete cleanup
or unknown finalization cannot count as a pass.

After an authorized run, evaluate downloaded output with:

```bash
.venv/bin/python scripts/evaluate_phase4_prescreen.py /path/to/phase4-prescreen
```

No actual tokenizer/GPU/model-process validation has yet occurred. The notebook
and protocol are ready for review, not declared hardware-certified. After a
successful prescreen and accounting review, register a separate full-game
lifecycle certification covering environment dispatch, legal fallback, cancellation
and scorecard finalization. H1 stays untouched; advanced scheduling stays deferred.

## Earlier implementation milestones (historical scope)

`config/phase4_contract.json` freezes E1S-R, its model and prompt manifests,
the minimum FIFO scheduler (110 queue slots, eight workers, 300-second age
limit), the existing development game/seed inventory, local workload, metrics,
failure rules and local acceptance thresholds. Its lock detects contract drift.
Required SHA-256 bindings reject missing evidence and changed parent sources.
The Phase 2–3 archive, decisions and holdout ledger are unchanged.

The operating target is 27,540 seconds from lifecycle start, including model
startup and the 600-second finalization reserve. Admission stops at 26,940
seconds. This is not a 27,540-second inference allowance plus cleanup.

## Local evidence

`make phase4-load` uses the production `QueuedInferenceExecutor`, with 110
concurrent client threads making 80 sequential requests each. A seeded client
submission order and fixed rotating 1/8/32 KiB byte payloads exercise request
isolation and mixed service inputs. Callbacks hash bytes and simulate short
service delays; they do not tokenize prompts, encode images, load the model,
play games, or exercise continuous batching on vLLM. Thread interleaving and
measured timings are intentionally not claimed deterministic.

The first local run completed 8,800 requests with zero request failures and all
110 clients completing 80 requests. Its maximum observed queue size was 109.
These figures establish only this synthetic queue smoke/load result; throughput
is not a model capacity estimate. Reports explicitly keep `C_nominal` and
`C_admit` null and `target_gpu_certified` and `phase4_complete` false.
An additional full local run is retained in `reports/phase4_local_load.json`:
8,800 completed, zero failures, maximum queue size 106. Its contract, parent
and harness hashes identify the measured setup; differing timings and queue
peaks reflect local thread scheduling, not a scheduler comparison.

`make validate-phase4` combines the new queue/cutoff tests with existing
production-path fixtures for 110-client orchestration, hung-worker finalization,
ambiguous dispatch, degraded evidence storage and model startup failures.
The new tests cover FIFO order/overflow, stale and canceled requests, timeout
result rejection, callback failures without retries, T0 journal exhaustion and
the exact operating cutoff. These are component/integration fixtures, not a
single combined 110-client model-backed fault soak. Disk-backed evidence loss
may degrade while preserving T0/T1 and legal play; failure to journal a
transaction must deny dispatch.

## Remaining gates before target execution

### Supervised runner implementation

`make phase4-service-probe` now executes the exact generated requests in eight
1,100-request windows against a fake backend. `FAULT=startup`, `inference`,
`timeout`, `storage`, `finalization`, `hang`, or `finalization_hang` exercises
failure paths. Fault runs deliberately exit nonzero; tests assert that outcome.
The production model lifecycle/transport adapter is implemented separately in
`TargetServiceBackend`, but target launch is unconditionally disabled pending
a new approved execution lock and compute reservation. Editing a boolean in
the draft does not enable spending. No target-GPU runner certification is claimed.

The supervisor launches a dedicated process session and owns its entire process
group. It stops work at its scaled local admission cutoff, sends termination,
escalates to kill after bounded grace, and cleans only its own temporary directory.
This includes noncooperative inference and stalled finalization. Unknown cleanup
or missing results cannot masquerade as acknowledged finalization. An acknowledged
fake-service shutdown is not an official scorecard finalization acknowledgment.

Local controls are a 15-second lifecycle, two-second reserve, 2 GiB aggregate
process-group RSS and 16 MiB scratch ceiling, checked approximately every 20 ms
plus monitor latency. These are polling limits, not OS-enforced allocation caps;
short spikes can exceed them. `ps` must be permitted for the host-RSS monitor;
unavailable resource telemetry fails closed. This can require running local tests
outside a restrictive process-inspection sandbox. The target's GPU VRAM, host
RAM, disk and fault-soak thresholds are **not** inferred from these local limits.
The tests inject memory/disk telemetry breaches as well as real subprocess hangs.

The fake fault schedule injects startup failure before queue creation, inference
or timeout at callbacks, evidence-storage failure before measured windows, and
finalization failure/stall after the workload. Storage injection is a controlled
exception, not an actual disk-full event. Existing evidence-store degradation and
transaction tests remain separate. Target backend cancellation and full-game
integration remain prerequisites to enabling a live run. Artifact/context
preflight and VRAM monitoring are now implemented, as described below, but
have not been measured on the actual target.

### Target preflight and telemetry

`evaluation/phase4_preflight.py` verifies the full model tree using M0's hashing
algorithm; changed bytes, symlinks and unexpected layout fail closed. The launch
specification is SHA-bound and its 65,536-token context limit must match the audit.
Tokenization uses only the mounted artifact, the pinned Transformers version,
no remote code and no downloads. It includes the actual chat template, generation
prompt and thinking-disabled setting. No truncation is allowed, and prompt tokens
plus the 128-token completion allowance must fit. See the
[Transformers template contract](https://huggingface.co/docs/transformers/v4.57.0/chat_templating).

Where the exact model and tokenizer dependencies are installed, run the read-only
audit (full weight hashing may take time):

```bash
.venv/bin/python scripts/phase4_preflight.py --model-path /path/to/exact/model
```

The NVIDIA monitor requires exactly one RTX PRO 6000, a bound UUID and an explicit
VRAM ceiling. It checks device-wide memory before/after completions and polls
during service lifetime. Missing or ambiguous telemetry, changed identity and
over-limit samples fail closed; errors remain sticky. Polling is not an allocator
cap and may miss transient spikes. UUID and ceiling remain null in
`config/phase4_preflight_lock.json`, pending target configuration.

The adapter requires preflight before startup, cleans up on startup failure,
accepts only audited requests, and rejects missing server token counts or any
disagreement with offline prompt counts. Tests use fixture artifacts and mocked
tokenizers, GPU telemetry and service responses. No actual weights, GPU or model
inference were exercised. Server parity, sustained monitoring, in-flight
cancellation and full lifecycle behavior still require target evidence.
Preflight success grants no launch authority: the target gate stays closed until
a separately reviewed execution lock and compute reservation exist.

Offline request-shape preparation is now implemented in
`evaluation/phase4_workload.py`; inspect it with `make phase4-workload`.
It captures requests through the actual `E1Policy.propose` path with a recording
completion client, exercising 16/32/64-square grids and 0/1/79-transition history.
The nine deterministic requests span 1,707–30,700 serialized request bytes;
token counts remain unknown until measured with the frozen tokenizer/service.
E1S-R sends JSON grids as text to a multimodal-capable model, not image attachments.
No alternate image/prompt format is introduced. The 110-client/8,800-request
assignment is deterministic and hash-bound. These are generated shape fixtures,
not an empirical sample of real game trajectories.

`config/phase4_target_profile.json` proposes one eight-GPU-hour, private unscored
service prescreen, with eight fixed 1,100-request windows and a conservative
empirical throughput projection. It is explicitly a **draft**, with zero
authorized compute and no bound executable runner. The minimum-window haircut
and service headroom are prospective margins, not confidence bounds or a hard
capacity guarantee. A service prescreen cannot replace full-game certification.
All startup/failure time must be charged; no automatic reruns are proposed.

1. Capture and bind empirical E1S-R grid-text prompt-length/context mixtures.
   Freeze a full 110-client development-only workload manifest and seeds.
   The existing 15-game inventory is a provenance input, not 110 independent games.
2. Register a target protocol, runner hashes, repetitions, conservative sustained
   throughput bound and numeric fault/recovery thresholds before measurements.
   Freeze nominal capacity and headroom-adjusted admission capacity separately;
   the local contract reserves 20% service headroom, not a measured capacity.
3. Allocate explicit accelerator hours, notebook runs, game passes and restart
   contingency in a new prospective record. This preparation contract authorizes
   zero GPU hours, target runs, scored submissions and holdout runs; it transfers
   no Phase 2 budget. No expensive execution has been launched.
4. Measure startup, real mixed-load queues/service, memory/storage pressure,
   inference timeout and cancellation, legal degradation and finalization on the
   actual target. In-flight callback timeout does not prove model computation
   was canceled: backend/process cancellation remains a target gate. Require
   a complete lifecycle below 27,540 seconds and verified finalization.
5. Consider at most one advanced scheduler only after a measurable allocation
   failure. Register numeric improvement thresholds and a separate counterbalanced
   whole-workload comparison with paired-run uncertainty before execution.
   No alternative is admitted now; the minimum scheduler remains rollback.

The Phase 4 contract is deliberately scoped to local preparation, not a claim
that the target experiment contract or certification is finished. Further
protocols must be versioned rather than editing historical decisions. H1 remains
preserved. Scheduling reliability does not explain or remedy cd82's ineffective
clicks; action-selection improvement needs its own scoped development study.
