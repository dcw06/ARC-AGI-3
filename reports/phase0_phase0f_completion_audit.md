# Plan 8 Phase 0 and Phase 0F/M0 completion audit

Date: 2026-09-09

Status: complete. This audit revalidates the local evidence and records the
existing mounted-runtime and Kaggle evidence. It does not spend another scored
submission or reinterpret the E0 score as model-performance evidence.

## Phase 0 deliverables

| Deliverable | Status | Evidence |
|---|---|---|
| Git initialization and ignore audit | Pass | Git history exists; `.env`, `.kaggle/access_token`, generated submission and M0 notebooks, run reports, scratch data, and journals are ignored. |
| Dated competition constraints | Pass | `config/competition_constraints.yaml` contains the required rule, runtime, licensing, account, deadline, allowance, output, external-input, score, and reset fields with source and revalidation metadata. |
| Public-inventory exposure and partition | Pass | `config/holdout_ledger.yaml` freezes a disjoint 15/5/5 partition, conservatively labels H1/H2 reduced-exposure, and exposes an append-only `consumption_events` sequence. |
| E0 schemas and later-treatment closure | Pass | The activation record names the versioned E0 registries; the activation commit retains M0/E1 as inactive/unclosed at Phase 0, while the current registry prospectively records later completed work. |
| Pinned transport adapter | Pass | `agent/framework_adapter.py` is the declared call boundary; it creates request-local bytes, disables redirects/retries, journals before transport, and quarantines ambiguous actions. |
| Mounted-client transport fixtures | Pass | Exact local source/runtime hashes and the local competition-mode REST fixture cover authentication, cookies, session identity, reasoning encoding, response conversion, and state binding. The accepted Kaggle rerun records mounted success. |
| Journaled open and close | Pass | Lifecycle journal tests cover acknowledged and ambiguous open/close with no retry; unknown close is classified as `finalization_unknown`. |
| Journaled bootstrap RESET | Pass | Bootstrap is prepared and dispatched once, has no fabricated pre-state, and the mounted scorer fixture distinguishes initial RESET from later scored RESET. |
| Bounded loop and orchestrator | Pass | Synthetic 110-client tests prove one scorecard, one bootstrap per game, bounded action state, streaming worker start, contained worker failure, and protected finalization reserve. |
| Immutable fallback, R path, and output isolation | Pass | Immutable `ActionDecision`, deterministic fallback, exact raw observation, `/kaggle/working` single-file allowlist, and `/tmp/arc3-agent` scratch policy are tested and packaged. |
| Minimum inference queue | Pass | FIFO/fair bounded queue tests cover 110 clients, maximum size, expiry, and independent deadline admission stop. |
| Competition-parity runner and notebook | Pass | Local/official adapter runner exists; the generated multi-file offline notebook and retained-output policy validate. |

## Phase 0 exit gate

| Condition | Status | Evidence |
|---|---|---|
| Three clean development runs | Pass | Activation record: three real `ls20` runs, 12 acknowledged actions each, without invalid action or uncaught exception. |
| Stable fixed-seed traces | Pass | Three-run trace SHA-256 `1dfe912b5f012fab00e2d289a196e563fc608f1e83f154d064e14858e8f00171`. |
| No adapter/journal bypass and conservative ambiguity handling | Pass | Transport tests distinguish pre-dispatch validation from post-entry ambiguity; ambiguity is terminal and never retried. |
| Mounted-client behavioral equivalence | Pass | `LOCAL_GATEWAY_EQUIVALENCE_PASSED`; scored submission `56076246` supplies the recorded mounted-runtime evidence. |
| Serialized make/startup invariants | Pass | Bootstrap occurs on the orchestrator thread before worker submission; local `Arcade.make` is serialized, and the fixture proves cookie/session/scorecard isolation. |
| ACTION6 and reasoning isolation | Pass | Two-client test verifies independent coordinates and independently serialized reasoning values. |
| Unknown runtime fails before play | Pass | Production-entry test injects a failed mounted audit and proves the adapter is never constructed. |
| No hidden-production unbounded retention or recording | Pass | Production state retains bounded evidence; notebook packages no upstream frame list, uses `save_recording=False`, and exposes bounded lifecycle output only. |
| Lifecycle, score, inventory, output, and finalization invariants | Pass | Unit, gateway, notebook, scorer, synthetic-load, activation, and accepted-rerun evidence all pass. |
| Bounded queue under 110-client load | Pass | Synthetic queue and hung-worker fixtures pass. |
| Plan 8 activation | Pass | `config/activation_record.json` is active, has no blocking checks, records accepted output/finalization, and grants authority to Plan 8. |

## Phase 0F/M0 deliverables and exit gate

| Requirement | Status | Evidence |
|---|---|---|
| Immediate uint8 packing, hashes, and T0-T3 retention | Pass | Frames become immutable contiguous `uint8`; grid and ordered-sequence hashes round-trip byte-for-byte; bounded records expose exact, summarized, omitted, evicted, unavailable, and corrupt states. |
| Storage failure preserves T0 and legal play | Pass | Failure fixture retains current state/legal actions and obtains a legal deterministic decision after persistence failure. |
| Minimal R and toggleable F | Pass | R exposes only final raw frames and bounded raw history; F independently adds registered animation/delta/region/translation features and bounded ACTION6 candidates. |
| Coordinate and representation fixtures | Pass | Row/column to x/y endpoints, reliability blocking, intermediate-only cues, and deterministic digests pass. |
| Frozen target-RTX profiles | Pass | Three public, hash-frozen artifacts were measured on NVIDIA RTX PRO 6000 with the same offline vLLM 0.19.0, Torch 2.10.0+cu128, Transformers 4.57.6, prompt, concurrency, and token contract. |
| Model viability envelope | Pass | All candidates satisfy artifact, cold-load, cancellation, RAM/VRAM, queue, 19,800-second model-service, and 27,540-second operational checks at the 8,800-call ceiling. |
| Provisional selection | Pass | Primary is Qwen3-VL 30B-A3B FP8; fallback is Qwen3-VL 8B FP8. Selection is explicitly viability-only pending E1 behavioral evidence. |

The exact measured launch files remain immutable because their SHA-256 values
are embedded in the target-hardware profile records. Post-run disposition is
therefore recorded in `config/model_manifest.yaml` and
`config/runtime_profiles.yaml`, not by rewriting those measured inputs.

## Revalidation commands

- `make validate-phase0` -> `LOCAL_PHASE0_PASSED`, `PLAN8_ACTIVATED`
- `make validate-m0-exit` -> `PHASE0F_FOUNDATION_PASSED`,
  `PHASE0F_M0_PASSED`, `M0_EXIT_GATE_PASSED`
- `make validate-phase1` -> `PHASE1_FOUNDATION_PASSED`, with Phase 1 activation
  correctly blocked on its prospective model-binding, cutoff, licensing,
  workspace-worker, and parameter-closure gates.

No new Kaggle run or scored submission was used for this revalidation.
