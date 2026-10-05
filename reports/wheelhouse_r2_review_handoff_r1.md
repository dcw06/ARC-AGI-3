# R2 redistribution review handoff r1

Prepared 2026-10-05 against `wheelhouse-replacement-audit` revision
`a82e7e66c26fba15de1f9d6cf6de2c01eadf5f1b`. The validated smoke fixes remain separately
on `wheelhouse-r2-smoke-v1` at `b07e2b2`.

The next input is the designated reviewer's artifact-by-artifact decisions. The
worksheet is ready for that review: its 174 rows match the inventory and regenerated
proposal context, and all reviewer columns are blank. The current import preview has
zero errors, zero warnings and zero changes. It would leave all 174 build blockers.
There is no reason to import this empty preview.

## Files for the reviewer

- [Worksheet CSV](wheelhouse_redistribution_decision_worksheet.csv): fill the `reviewer_*` columns for each decided row; retain the artifact identity and context columns.
- [Worksheet instructions](wheelhouse_redistribution_decision_worksheet.md): decision values, required fields and condition-satisfaction format.
- [Proposed dispositions](wheelhouse_redistribution_proposed_dispositions.md): evidence and proposals for all 174 artifacts.
- [NVIDIA reconciliation](wheelhouse_nvidia_licence_reconciliation.md): retained source comparisons and unresolved applicability questions.

Every non-unresolved decision needs a rationale, reviewer name and ISO date.
`approved_with_conditions` needs the recorded conditions; each condition must have
documented satisfaction before the bundle is eligible. `restricted` and `excluded`
also block this dependency set and require an explicit alternative.

## Start with the four priority artifacts

These questions are summarized from the existing worksheet and reconciliation, and
remain for qualified review. The JSON receipt binds each row to its full wheel SHA-256.

| Artifact | Question that must be resolved |
|---|---|
| `nvidia_cufile_cu12` 1.13.1.3 | The bundled Attachment A omits cuFile while the retained CUDA 12.8.1 text lists its libraries. Which text governs this wheel, and does the proposed distribution satisfy the applicable conditions? |
| `nvidia_nvjitlink_cu12` 12.8.93 | The bundled Attachment A omits nvJitLink while the retained CUDA 12.8.1 text lists its library. Resolve the governing text and the proposed distribution conditions. |
| `nvidia_nvshmem_cu12` 3.4.5 | Resolve the wheel's bundled CUDA terms against the version-specific NVSHMEM SDK licence and supplement, and whether the proposed distribution satisfies the governing terms. |
| `nvidia_cutlass_dsl_libs_base` 4.5.0.dev0 | Resolve the governing terms for the pre-release binary wheel against the retained v4.5.0 source, and the proposed distribution conditions. |

The worksheet contains the complete questions and alternatives. A clarification
request can be drafted from them for the reviewer; no message has been sent to NVIDIA
or anyone else.

## Remaining review order

| Tier | Rows | Work remaining |
|---|---|---|
| 2 | 19 | Other artifacts requiring qualified review |
| 3 | 48 | Conditional candidates with additional obligations |
| 4 | 103 | Other conditional candidates |

Tier 2 contains `ninja`, `nvidia_cublas_cu12`, `nvidia_cuda_cupti_cu12`,
`nvidia_cuda_nvrtc_cu12`, `nvidia_cuda_runtime_cu12`, `nvidia_cudnn_cu12`,
`nvidia_cufft_cu12`, `nvidia_curand_cu12`, `nvidia_cusolver_cu12`,
`nvidia_cusparse_cu12`, `nvidia_cusparselt_cu12`, `nvidia_cutlass_dsl`,
`openai_harmony`, `opencv_python_headless`, `pillow`, `prometheus_client`, `pyzmq`,
`quack_kernels` and `regex`. Their artifact identities and proposed dispositions are
retained in the JSON receipt; their full questions remain in the worksheet.

## Validation retained

Validation ran in an initially clean native Linux clone with `core.autocrlf=false`.
It checked the worksheet lock's input hashes, every context row against both the lock
and regenerated proposals, all six retained primary-source files (including extracted
texts), and all sixteen retained upstream licence/NOTICE files. The existing validator
then produced the empty preview, and the decisions file's hash stayed unchanged.

- [Validation and handoff receipt](wheelhouse_r2_review_handoff_r1.json): exact source revision, input hashes, source checks, priority rows and validator result.
- [Import preview JSON](wheelhouse_decision_import_preview.json) and [rendered preview](wheelhouse_decision_import_preview.md).
- Preview SHA-256: `ed5128d14a6faa779f698855022c7066d39a8bb9137f688703030fc836e754fd`.

## After the reviewer returns decisions

1. Validate the returned CSV using `python scripts/wheelhouse_decision_worksheet.py validate RETURNED.csv`. Inspect the complete before/after fields and any unsatisfied conditions.
2. Obtain the owner's confirmation of that exact populated preview, then import it using the preview hash. The existing importer requires this confirmation and refuses to replace recorded decisions.
3. Regenerate the bundle plan and check eligibility. The current repository provides the planner and eligibility rules; the bundle builder still needs to be prepared and reviewed against the final conditions. Obtain Record A for the exact local build inputs, then build, inspect and independently verify the bundle.
4. Obtain Record B for upload of the exact bundle. Record the resulting dataset reference/version, verify launch-account attachment access, and bind both bundle checksum hashes.
5. Rebuild a successor smoke review snapshot (r5 or later) after binding the dataset, validate it from a fresh checkout, and present Record C with the exact source lock, dataset and compute limits. Only after that authorization, reservation and claim can a single GPU attempt be submitted.

No decision has been imported, no bundle built or uploaded, no attempt reserved, and
no GPU launched during this preparation. Existing decisions, licence evidence and
smoke sources are unchanged.
