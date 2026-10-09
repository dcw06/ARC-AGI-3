# Track 2 Stage 1 on the verified runtime: successor packages (GPU-disabled)

**Status.** These are two session packages bound to the verified direct-publisher runtime at `5a21dd3`. They are
prepared CPU-only. No GPU was used and no provider was called. No approval, compute authorization, reservation,
claim, upload or notebook submission exists. Every live path refuses in this checkout.

**Withheld material.** The withheld seed was not drawn. No withheld frozen set exists. No withheld answer was
inspected.

## Packages

| Session | Package | Review snapshot (r1) | Review lock SHA-256 |
|---|---|---|---|
| A (groups 0-5, 2,896 calls) | `research/evidence_memory_v1_session_a/` | `notebooks/evidence-memory-v1-session-a-review-r1/` | see `verification.md` |
| B (groups 6-11, 2,832 calls) | `research/evidence_memory_v1_session_b/` | `notebooks/evidence-memory-v1-session-b-review-r1/` | see `verification.md` |

**Shared code.**
- `research/evidence_memory_v1/successor/`:
  - the study phase: `plan.py`, `service.py`, `study.py`, and the derived `runner.py`;
  - the evaluator (`evaluate.py`) and the pooled-analysis wrapper (`final.py`);
  - the owner-gated frozen-set path (`freeze.py`, `seed-commitment.json`);
  - the rehearsal stub (`stub.py`);
  - the vendored verification sources (`verified_sources/`).
- The verified runtime itself: `certification/direct_publisher_smoke_v1/`, byte-identical.

**Builder.** `scripts/build_evidence_memory_v1_sessions.py`. Pass `--check` to verify the committed files.

## Reports

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
- `verification.md`, `cpu_checks_*.json` and `.log`: the Linux CPU test and rehearsal record.
