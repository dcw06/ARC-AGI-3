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

**Withheld seed: first draw retired; draw 2 committed.**
- **Draw 1.** On October 10, 2026, one human holder, the owner, drew a first nonce and checked both copies
  (commitment `7f11432a…`; review snapshots r4 to r6).
- **Retired.** The recall decoding design changed after that draw, so the owner retired it before any execution
  (owner amendment, October 10, 2026; frozen protocol §5). It was not an automated-check failure. Its records are
  kept in `seed-commitment.json` (`retired`) and `nonce_custody.json` (`retired_draws`), and `freeze withheld`
  refuses its commitment. The frozen protocol keeps the chronology visible: the claim that every design decision
  preceded the draw was not true for draw 1.
- **Final design.** Review snapshots r7 freeze the complete final design (frozen protocol §5): decoder
  restrictions, scoring, thresholds, repeat selection, and the redraw and retirement conditions.
- **Draw 2.** The owner drew it on October 10, 2026 at 17:18:53 UTC, after r7 was committed and verified, and
  checked both copies (`nonce_custody.json`). Only its commitment is published: `d80505e2…`, in
  `seed-commitment.json` and each session's `protocol.json`, bound by review snapshots r8. The frozen protocol is
  byte-unchanged from r7.
- **Draw 2's withheld sets (gate 2, private).** Both passed with 0 exclusions: A 2,832 calls (repeat 4 groups),
  B 2,928 calls (repeat 5 groups). The request caps are 189,756 and 196,188. The derived values are in
  `withheld_draw_values.json`.

**Recall schema (owner decision, October 10, 2026).** After the first withheld draw, the recall decoding schema
allows exactly the eight valid answers (`structured_outputs_check_r3.json`). In that draw, session A's repeat had
48 answers per arm, where one invalid answer would fail the 2% rule. Review snapshots r6 and r7 bind it.

**Evaluator (r7).** The independent evaluator now requires every mandatory runtime probe (S1–S3, I1–I4, C1–C3)
and the pre-study metrics read (K0000). Each must appear in the ledger in the frozen order with its expected
outcome, and agree with its retained request record, stage value and passed phase. A run missing any probe is
never technically complete. Connected test 6 retains both of the review's reproductions (C3 removed; I4
removed); with the new check disabled, the C3 reproduction evaluates as technically complete.

**Withheld material.** No withheld frozen set exists in this repository: owner gate 2 builds them only in a
private checkout. No withheld answer has been inspected.

## Packages

| Session | Package | Review snapshot r8 (current) | r8 review lock SHA-256 |
|---|---|---|---|
| A (groups 0-5; withheld calls per draw, stand-in 2,896) | `research/evidence_memory_v1_session_a/` | `notebooks/evidence-memory-v1-session-a-review-r8/` | `051e34709fdb34536b919f5003ced65865a88f1ffbcf2c281cd05fcfa8c5b491` |
| B (groups 6-11; withheld calls per draw, stand-in 2,832) | `research/evidence_memory_v1_session_b/` | `notebooks/evidence-memory-v1-session-b-review-r8/` | `bc9718ab2e9b83410f3d7dbfda3443e4f6b917950b3850202ad02ffe6b301936` |

Kept as history (byte-identical): r1 locks `5539e126…` (A) and `fb94736b…` (B), built under the draft; r2 locks
`750ea373…` (A) and `37296378…` (B), the frozen protocol before the r3 fix; r3 locks `fbad29c7…` (A) and
`84407411…` (B), before the seed commitment; r4 locks `c6c89b3a…` (A) and `f9a480b8…` (B), before the eight-answer
recall schema; r5 locks `2176121e…` (A) and `52205ad7…` (B), whose stage1 imported itertools (outside the research
modules' import boundary; the schema is identical); r6 locks `80fbe454…` (A) and `26f321fc…` (B), bound to the
retired first draw and before the evaluator's probe reconciliation; r7 locks `364d06e0…` (A) and `9391afa5…` (B),
the complete final design frozen before draw 2. Both r8 locks bind draw 2's commitment, the frozen protocol
(SHA-256 `6f96dbe7…`, byte-unchanged from r7) and the other review documents (`review_documents`). Session B's lock also
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
