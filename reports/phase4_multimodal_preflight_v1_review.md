# Multimodal image-input preflight v1: implementation review

This is the preflight required by `phase4_perception_v1_protocol.md` before the
perception experiment's image arm can be frozen. It asks one question: does
the frozen Kaggle stack accept and consume image input for the pinned model,
with exact token accounting, at the intended 1024×1024 size? It is not a
perception result and not a game-solving run. There are zero actions and zero
scorecards. The model, engine and launch spec are unchanged.

## What runs

The package is `certification/phase4_multimodal_preflight_v1`. It reuses the
supervisor, monitor, bridge, evidence, cleanup and approval stack from grounding
v1 and integrated v2, which ran on this target before. The transport and bridge
carry `finish_reason`.

1. **Mount inventory.** It lists all 81 mounted files with their sizes, and
   hashes every file of 2 MiB or less. It records whether the preprocessor
   configs are present and match the pinned Hugging Face revision
   (`6a970fd0…`, `e203bc06…`).
2. **Processor load.** `AutoProcessor` is loaded from the *mounted* files,
   offline, with no remote code. Pillow, torch and torchvision versions are
   recorded. A failure is recorded as a dependency outcome and is not raised.
3. **Text canary.** The existing canary, byte-identical and with a known
   request hash, which must finish with `stop`.
4. **Probes, in order, each attempted.** A classified failure is recorded and
   the run continues. The images are lossless PNGs (16 px per cell, fixed
   palette), sent as inline data URLs.

| Probe | Image | Correct answer | Frozen local expectation (prompt tokens) |
|---|---|---|---|
| T0 | none (text control) | `none` / `null` | 352 |
| I1 | 4×4 cells, 64×64 px (below the processor minimum) | colour 12 | 394 (resized to 256×256, 64 image tokens) |
| I2 | 64×64 board, 1024×1024 px, colour 8 square at top left | `top_left` / 8 | 1,378 (1,024 image tokens) |
| I3 | same size, colour 9 square at bottom right | `bottom_right` / 9 | 1,378 |

T0, I2 and I3 are byte-identical apart from the image part; `load_cases`
enforces this. Each PNG is verified against its frozen grid by the package's own
decoder at load time. Pillow independently decoded all three images at the
correct sizes, with every cell matching at its centre and corners.

## Evidence that the server processed the image

For each image request, the model interpreter computes the expected prompt
count from the mounted processor by two independent methods. One is the
processor's own expansion, `len(input_ids)`. The other is manual: template
tokens − 1 + t·h·w/merge², using `image_grid_thw`. The two must agree. The
following are retained for every request:

- `image_grid_thw`;
- the processed pixel dimensions;
- the image-token count;
- both counts;
- the frozen local expectation.

The evaluator then checks three things:

- **Accounting.** The server's prompt tokens equal the processor count, for
  every image probe.
- **Consumption.** The server's I2 − T0 delta equals the processor's image
  tokens + 2 (the two vision-marker tokens). A delta of 3 or less means the
  image was dropped.
- **Consistency.** I2 and I3 have the same server count.

Correct answers are recorded but are never evidence of processing.

**Behavioural sanity check.** Identical answers to I2 and I3 set
`review_required_behavioural`, and so do invalid or missing answers.

## Outcome classes

The evaluator derives the class independently from retained evidence. It
checks each classified failure against its own evidence. For example, a
`dependency_missing` claim is rejected while the processor loaded, and a
mismatch claim is rejected when the counts are equal.

| Class | Condition |
|---|---|
| `image_input_verified` | Accounting, consumption and consistency pass |
| `dependency_missing` | Preprocessor absent, or processor or image libraries fail. No image request is sent |
| `image_rejected_by_server` | HTTP ≥ 400 on an image request; status and body retained |
| `token_accounting_mismatch` | Server ≠ processor count, the processor's two methods disagree, or I2 ≠ I3 |
| `image_not_consumed` | Server delta ≤ 3 instead of the expansion |
| `text_control_failed` | T0 did not complete |
| `lifecycle_failure` | Supervisor, monitor, cleanup or evidence-binding failure |

The flag `arithmetic_revision_required` is raised when verified processor
counts differ from the provisional arithmetic or the frozen local expectation.
Image support is not denied, but the measured dimensions and token counts must
be reviewed and incorporated into the frozen perception protocol first.

`representation_comparison_unblocked` is true only for `image_input_verified`
with **no review flag of either kind**. Every other outcome, and any flagged
verified outcome, blocks the comparison pending review.

R1 (`8bd5b2c`) left the comparison unblocked under
`arithmetic_revision_required`, which contradicted this rule. R2 fixes the
evaluator and its regression expectation. R1 is preserved and superseded. No outcome establishes that images are "unsupported", and
nothing launches a text-only substitute.

## Local results

These are in `phase4_multimodal_preflight_v1_local_checks.json`.

- **Unit tests: 24 passed.** They cover:
  - case drift, image drift and question drift;
  - strict parsing and finish-reason handling;
  - each classified failure in the real `audited_probe` path, using a fake
    tokenizer and processor with real Pillow images;
  - that structured expectation evidence survives failure (a structured dict,
    not a `repr` string);
  - HTTP rejection retention in the transport;
  - classified-evidence relay across the bridge;
  - evaluator rejection of inconsistent claims;
  - monitor, evidence and deadline faults.
- **Supervised CPU fixture runs: 10, each with verified cleanup.** Each mode
  produced its intended class and flags, and replay from the checksum-bound
  archive reproduced them. Nine modes are technical passes: verified,
  incorrect, identical, invalid, arithmetic, dependency, rejected, mismatch and
  not consumed. The transport mode is a lifecycle failure, as intended.
- **No model calls, GPU runs, environment actions or scorecards.**

## Limits of this review

- Local tests use a *fake* processor. The real mounted processor, vLLM's image
  path, the server's multimodal accounting and the 81-file mount contents are
  only observable on the target; that is the point of the run.
- The vision encoder is part of the model already started in every earlier run
  (same launch spec), so no change in startup is expected. Startup is still
  capped at 750 s.
- An image rejection might come from the request format (data URL, content
  parts) rather than the model's capability. The retained HTTP body is needed
  to tell them apart during review.

## Budget (proposal, zero authority)

- One attempt, 1,800 provider seconds, 1,680 internal, with a 300 s cleanup
  reserve.
- One text canary plus 4 probes, 5 completions in total, and at most 384
  generated tokens.
- Payloads of 262,144 bytes or less; context 65,536 tokens.
- Integrated v2 measured 525 s startup and 669 s total.
- No retry, and no reuse of an earlier reservation.
- It requires its own source approval and compute authorization, bound to the
  review lock.

After the run, the perception experiment is frozen against the verified
configuration: processed dimensions, token counts and outcome class. Phase 4
remains open.
