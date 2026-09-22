# Integrated ar25 executable revision 1

Implementation of the frozen integrated case, not a new indexing test. The original
specification lock is preserved. Baseline uses the unchanged transient-v2 control
request builder on reconstructed runtime state, seed zero. Structured requests use
inventory, decision and feedback schemas with 2048/1024/1024 output-token caps.
Both episodes start from the locked ar25 state. Each stops dispatch at eight actions,
first level increase, WIN or GAME_OVER. Structured final feedback still runs after
the final acknowledged action. No fallback, reset, repair, retry or extra inference.

The runner durably records call intent, response evidence before validation, action
intent, exact dispatch journals, all observation frames and local card finalization.
Invalid model output ends that episode as `invalid_output`; its downstream stages
are censored, not scored as wrong. It is not a transport failure. Incorrect valid
claims remain outcomes. Technical errors terminate the comparison and invoke cleanup.
OFFLINE local scorecards are recorded; there is no production submission.

## Executable resolutions of specification ambiguities

Target spans always refer to the current pre-frame. Mechanical scoring checks a
click against the model's declared mask; actual object identity/grounding and causal
interpretation stay separate rubric adjudications. No stale reference-mask tracking
or answer-key correction is supplied. Each next structured request retains all its
own prior declarations and feedback; baseline sees its historical compact observation.
This remains a scaffold bundle, not a same-information prompt-only comparison.

Prediction `any_returned` means existential over returned frames; `final` means last.
An empty changed-region predicate is invalid. Dimension changes yield unresolved
pixel predicates; a true observed frame still supports an existential predicate.
Translation means the complete set of cells of the declared color equals the
translated declared mask. Clipping yields unresolved; extra cells/occlusion contradict
that exact visible predicate. This does not assert persistent game-object identity.
Level-counter predicates use the final observation. Both competing predicates can
be supported; neither is automatically declared the unique true mechanic.

Replay reconstructs every request and stage, validates initial-state equality to the
frozen case, action serialization and acknowledgement journals, monotonic timelines,
progress stops, finalization and evidence inventory. It recomputes frame differences,
predicate verdicts and declared target hits independently of the worker's summaries.
It does not claim to automate human judgments of geometry prose, experimental value,
behavioral updating or first consequential break. Those need the frozen rubric.

## New compute proposal, no authority yet

Propose one **3600-second provider attempt**, 3300-second first-cell lifecycle,
300-second cleanup reserve, 300-second provider margin, admission no later than
3000 seconds, and at most 1200 seconds for the study after model readiness.
Installation cap 450 seconds; model readiness cap 900; each inference timeout 120.
These are intersecting caps, not additive guaranteed entitlements. Prior measured
coordinate startup was 492.258 seconds and total runtime 632.562 seconds. This
study has much longer generated responses and adaptive inputs, motivating a new
conservative ceiling rather than reuse of that observed duration. No previous
reservation or unused time is carried forward.

At most 25 study calls + one 128-token canary; 16 action attempts; 19,584 generated
tokens including canary. Study prompt ceiling 1,500,000 tokens (25 x 60,000), plus
the fixed 46-token canary. Context stays 65,536. Every exact request is tokenized
without truncation before inference. Prompt >60,000 tokens, serialized payload
>196,608 bytes, response >32,768 bytes, or >8 returned frames causes retained
technical failure; no silent pruning. Some admissible schema outputs can accumulate
into an inadmissible future request: that produces an explicit incomplete case,
not an assertion that all adaptive trajectories fit. The pinned audit reports exact
fixture requests and stress inputs, not unknowable future model responses.

Evidence ceiling 128 MiB: control 4, monitor 16, worker 88, evaluation 12, logs 8.
RSS 128 GiB, VRAM 86 GiB, scratch 4 GiB; monitoring runs through process termination
and an independent post-termination GPU check. Both dependency trees and extracted
source must be removed before a final passing receipt. Actual billing remains a
separate reconciliation obligation.

## Review boundary

The notebook is private, offline and GPU-disabled. Its embedded source lock covers
the baseline implementation and all reused lifecycle dependencies. Missing source
approval, compute approval or matching unconsumed reservation rejects execution
before installation. Synthetic local tests cover missing/mismatched/consumed
authority and one upload only. The prior launch request is recorded as intent in
`phase4_integrated_v1_launch_intent.json`; it is not converted into a fabricated
approval of a source hash that did not yet exist. No reservation or upload is made.

Local results: `phase4_integrated_v1_local_checks.json`; tokenizer audit:
`phase4_integrated_v1_token_audit.json`; unpacked package inspection is recorded
separately after freezing the notebook. These checks do not establish target vLLM
support for the new stage schemas or solving improvement. Future authorized target
validation must retain schema rejection as a failure without retry or fallback.
Production certification, admission limits, and exact billing remain open.
