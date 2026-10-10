# Track 2 Stage 1 on the verified runtime: successor packages (GPU-disabled)

**Status.** These are two session packages bound to the verified direct-publisher runtime at `5a21dd3`. They are
prepared CPU-only. No GPU was used and no provider was called. No approval, compute authorization, reservation,
claim, upload or notebook submission exists. Every live path refuses in this checkout.

**Protocol of record.** `reports/evidence_memory_v1_protocol_v2_frozen.md`, frozen on the owner's decisions of
October 9, 2026 (`freeze_decisions.md`). Review snapshots r2 and r3 bind it; r1 (built under the draft) and r2 are
kept byte-identical as history. r3 adds one fix (Track 4 parity): the review documents are verified by the launch
tooling and the live evaluation too, not only by the review check (`runtime_diff.md`, addendum r3). The decisions changed the recall decoding schema (no `uniqueItems`), the reading of the
unsupported-claim margins (three ways), the exclusion procedure (refuse and redraw) and session B's launch tooling
(only after session A is technically complete). Every changed file is listed in `freeze_change_list_r2.md`. Still
open: who holds the two copies of the withheld nonce (owner gate 1).

**Withheld seed (owner gate 1, done October 10, 2026).** One human holder, the owner, drew the nonce and checked
both copies (`nonce_custody.json`). The commitment `7f11432a…` is in `seed-commitment.json`, in each
session's `protocol.json` and in the frozen protocol §5; review snapshots r4 bind it.

**Withheld material.** The withheld seed is drawn and committed (above). No withheld frozen set exists in this
repository: owner gate 2 builds them only in a private checkout. No withheld answer has been inspected.

## Packages

| Session | Package | Review snapshot r4 (current) | r4 review lock SHA-256 |
|---|---|---|---|
| A (groups 0-5, 2,896 calls) | `research/evidence_memory_v1_session_a/` | `notebooks/evidence-memory-v1-session-a-review-r4/` | `c6c89b3af1d6203e6b14cbd358f78c1b0706766f14314955dfe17f1050dba7d4` |
| B (groups 6-11, 2,832 calls) | `research/evidence_memory_v1_session_b/` | `notebooks/evidence-memory-v1-session-b-review-r4/` | `f9a480b81d97689070dcdb09aa45864c5636e4a52020962fdd36113d0c247832` |

Kept as history (byte-identical): r1 locks `5539e126…` (A) and `fb94736b…` (B), built under the draft; r2 locks
`750ea373…` (A) and `37296378…` (B), the frozen protocol before the r3 fix; r3 locks `fbad29c7…` (A) and
`84407411…` (B), before the seed commitment. Both r4 locks bind
the frozen protocol (SHA-256 `bba44981…`) and the other review documents (`review_documents`). Session B's lock also
binds `research/evidence_memory_v1/successor/session_order.py`, its launch tooling's session-A condition.

**Shared code.**
- `research/evidence_memory_v1/successor/`:
  - the study phase: `plan.py`, `service.py`, `study.py`, and the derived `runner.py`;
  - the evaluator (`evaluate.py`) and the pooled-analysis wrapper (`final.py`);
  - the owner-gated frozen-set path (`freeze.py`, `seed-commitment.json`);
  - session B's launch condition (`session_order.py`): session A's retained technical evaluation, bound by hash;
  - the rehearsal stub (`stub.py`);
  - the vendored verification sources (`verified_sources/`).
- The verified runtime itself: `certification/direct_publisher_smoke_v1/`, byte-identical.

**Builder.** `scripts/build_evidence_memory_v1_sessions.py`. Pass `--check` to verify the committed files. It also
records the protocol-freeze amendments to the reused Track 2 modules exactly (`FREEZE_AMENDMENTS`).

## Reports

The protocol freeze (October 9, 2026; r2):
- `../evidence_memory_v1_protocol_v2_frozen.md`: the protocol of record.
- `freeze_decisions.md`: the owner's decisions, each marked decided, with the decision packet as prepared.
- `freeze_change_list_r2.md`: every file changed or added, grouped by decision.
- `structured_outputs_check_r2.json`: on the exact runtime install, both Track 2 response schemas are accepted
  (xgrammar). The decoder admits exactly two answers the protocol counts invalid, and the scorer rejects both.
  r1's receipt (`structured_outputs_check_r1.json`) recorded the defect.
- `token_cross_check_r2.json`, `token_counts_r1_vs_r2.json`: the real-tokenizer cross-check on the new request
  bodies, and the proof that no prompt token count changed.
- `extracted_inputs_session_{a,b}_r2.json`, `../evidence_memory_v1_session_{a,b}_review_check_r2.json`: the r2
  payload and review-notebook checks.
- `verification.md`: the r2 fresh-clone verification (`fresh_clone_run_r2.sh` and `.log`, `cpu_checks_*_r2.json`
  and `.log`), above the r1 record.

From the successor build (r1):
- `runtime_binding_inventory.md`: every outdated runtime binding of the Track 2 package at `107d8b4`.
- `runtime_diff.md`: the runtime-only diff, and what still enforces the unchanged science.
- `open_protocol_choices.md`: protocol choices still open, with options and recommendations.
- `owner_gates.md`: the withheld seed, frozen-set generation, private bindings, evidence, enabling and approvals, with
  exact procedures.
- `token_cross_check.json`: the real-tokenizer cross-check (transformers 4.57.6 / tokenizers 0.22.2, pinned files)
  on every study request of both sessions.
- `extracted_inputs_session_{a,b}_r1.json`: each review payload, extracted alone, loads the 174 trusted wheel records
  and imports the live path.
- `../evidence_memory_v1_session_{a,b}_review_check_r1.json`: each GPU-disabled review notebook, executed with a
  decoy `nvidia-smi`, stops at the live gate.
- `cpu_checks_*.json` and `.log`, `fresh_clone_run.sh` and `.log`: the r1 Linux CPU test and rehearsal record,
  from a fresh clone at `9655dbf` (`verification.md`, second part).
