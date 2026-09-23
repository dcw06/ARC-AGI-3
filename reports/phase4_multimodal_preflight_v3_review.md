# Multimodal preflight v3: supported processor tensors and precise failures

Review successor to the consumed v2 attempt, preserving every v2 source,
notebook, classification and receipt. No new attempt is authorized or reserved.

## Repair and evidence contract

The processor expectation path requests `return_tensors='pt'`. It retains input
dimensions, patch/merge sizes, returned `image_grid_thw`, processed dimensions,
full processor count and independent manual count. Cases, image bytes, prompts,
model, tokenizer, server launch specification and decoding are unchanged.

Failure provenance crosses the existing process bridge as bounded audit data:

| Event | Failure kind | Stage | Transport attempted |
|---|---|---|---|
| Processor call raises | `processor_execution_failure` | `processor_execution` | false |
| Invalid processor output | `processor_execution_failure` | `processor_output` | false |
| Input/template preparation raises | `processor_execution_failure` | `expectation_preparation` | false |
| Two actual offline counts differ | `token_accounting_mismatch` | `offline_count_comparison` | false |
| Actual server/expected counts differ | `token_accounting_mismatch` | `server_count_validation` | true |
| Missing/invalid server usage | `usage_validation_failure` (technical stop) | `server_usage_validation` | true |
| Transport raises | `transport_failure` (technical stop) | `transport` | true |

Every failure retains its exception type and request identity. The expectation
failures retain any partial computed expectation, without inventing counts or
a server response. `transport_attempted` means the transport method was invoked,
not that a server necessarily received a request. HTTP rejection also retains
status and bounded body. The independent evaluator requires this provenance,
checks failure-body hashes, and rejects a claimed count disagreement without
two differing counts. Successful probe rows require transport provenance too.

Processor execution failure is a new classified outcome that blocks the
representation comparison. Missing usage and transport errors stop technically.
All existing behavioural and arithmetic review flags continue to block. No
historical result is relabeled.

## Actual pinned processor CPU regression

`phase4_multimodal_preflight_v3_processor_audit.json` records a real
`Qwen3VLProcessor` with `Qwen2VLImageProcessorFast`, transformers 4.57.6,
torch 2.10.0+cpu, torchvision 0.25.0+cpu and Pillow 12.2.0. Tokenizer and both
processor config files are hash-verified against the frozen model revision.
The historical NumPy call reproduces the exact target exception for every
image; the PyTorch call succeeds for every image and produces CPU tensors.

| Probe | Input pixels | Processed pixels | Grid t,h,w | Image tokens | Full/manual prompt tokens |
|---|---|---|---|---:|---:|
| T0 | none | none | none | none | 352 |
| I1 | 64 x 64 | 256 x 256 | 1,16,16 | 64 | 394 / 394 |
| I2 | 1024 x 1024 | 1024 x 1024 | 1,64,64 | 1024 | 1378 / 1378 |
| I3 | 1024 x 1024 | 1024 x 1024 | 1,64,64 | 1024 | 1378 / 1378 |

Patch size is 16, merge size 2. No model weights, inference or server were
needed. The test ran on Windows/Python 3.11.9 with CPU builds: this establishes
the pinned processor API/accounting path, not target Python 3.12/CUDA or vLLM
image compatibility. The fake processor now rejects any tensor format other
than `pt`, but the real test is the compatibility evidence.

Portable input archive (only tokenizer/config files, no weights):
`evidence/phase4-multimodal-preflight-v3-processor-inputs.zip`. With the pinned
CPU packages installed, the repeatable offline regression is:

```sh
python scripts/audit_phase4_multimodal_preflight_v3_processor.py
```

It validates all eight file hashes before loading and disables hub access.

## Local tests and package review

The supervised check passed 32 tests and eleven fixture outcomes, including
processor failure; the final five processor-classification regressions also
passed after adding the missing-usage guard (33 distinct preflight tests).
The fixture archive has checksum-bound read-only replay:

```sh
python scripts/check_phase4_multimodal_preflight_v3.py --replay
```

The new notebook is `notebooks/phase4-multimodal-preflight-v3-review-r1/`.
The package review receipt verifies unpacked source, private/offline/GPU-disabled
metadata, refusal without authority, and the actual snapshot through synthetic
approval, reservation, one fake upload and consumed-reservation rejection.
No real approvals or reservations are created by those tests.

## Separate budget proposal and remaining gate

The unchanged proposal is one 1,800-second provider attempt, 1,680 internal,
900-second startup ceiling, 300-second cleanup reserve, four probes plus one
canary and at most 384 generated tokens. Zero actions, scorecards or retries.
Stage maxima do not add extra time: the global admission cutoff wins.

The image probes still need actual vLLM dispatch and matching server counts.
Source approval and separate compute authorization must bind this successor's
review lock before reservation/packaging/submission. The text-versus-image
study remains blocked and gets no spending authority from this work.

Local control tests, five perception fixtures/scoring and a transition-record
contract are documented separately in `perception_v1_local_review.md`. They
are development infrastructure, not model-performance evidence. Production
certification, admission limits, exact accounting and Phase 4 remain open.
