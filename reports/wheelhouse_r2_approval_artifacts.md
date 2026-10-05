# Wheelhouse R2: proposed approval records and remaining blockers

Prepared October 4, 2026 on `wheelhouse-replacement-audit`. Updated after:
- the review of `f1dd4c2`/`fae8157`/`f4392cf`, which closed the four tooling findings;
- the review of `b289f51`/`127633e`, which corrected the NVIDIA "no grant found" assessment (see the reconciliation below).

**Status.** Nothing in this document is approved.
- **Not done:** no bundle has been built, nothing has been uploaded, no compute has been reserved, and no GPU run has been launched.
- **Not decided:** no licence decision has been recorded. All 174 rows of `reports/wheelhouse_redistribution_decisions.csv` are `unresolved`. The proposed dispositions are proposals for the designated reviewer, not decisions.

Each record below is a template. The owner completes it at its gate, and it binds exact hashes.

## Where each gate stands

| Gate | State | Evidence |
|---|---|---|
| Metadata closure | complete | `reports/wheelhouse_metadata_closure.{json,md}` (174/174 verified; reproduces offline) |
| Download | complete (approved manifest `3691cb88…d546`) | `reports/wheelhouse_r2_download_receipt.json` (174/174 verified, 5,185,992,159 bytes) |
| CPU offline installation | passed (network-isolated) | `reports/wheelhouse_r2_offline_install_check.json` plus `reports/wheelhouse_r2_offline_install_evidence/install-check-hacm1z70/` (log and lock, hash-bound) |
| Tooling review | closed (reviews of `f1dd4c2`/`fae8157`/`f4392cf` and `b289f51`/`127633e`) | `reports/wheelhouse_tooling_checks_b289f51.json`; this update's checks are recorded alongside its commit |
| Upstream licence texts | gathered for all 9 wheels that ship none, plus 2 upstream NOTICE files | `reports/wheelhouse_upstream_licenses/` (index `c2745968…e9`: 16 texts, each with source URL, source hash, member and SHA-256). Each of the 5 repository sources is pinned to a commit whose version file carries the exact release version. |
| NVIDIA licence reconciliation | primary sources retained; applicability facts recorded; **qualified review open** | `reports/wheelhouse_nvidia_licence_reconciliation.{json,md}` (`497640af…c9`); sources in `reports/wheelhouse_primary_licence_sources/` (index `aef799e4…bc`) |
| Proposed dispositions | prepared for all 174 artifacts | `reports/wheelhouse_redistribution_proposed_dispositions.{csv,md}` (csv `00d9f0b4…64`). Batch 1 (43 flagged): 25 conditional candidates, 17 needing qualified review, 1 likely not distributable. Batch 2 (131 unflagged): 126 conditional candidates, 5 needing review. |
| Redistribution decisions | **open**: 174/174 unresolved | decisions file `b754d3ac…9e` |
| Local bundle build | not started; needs record A | plan `reports/wheelhouse_r2_bundle_plan.json` (`d8da7cbe…24`, 425 files; build eligibility: not eligible, 174 blockers) |

### Correction: NVIDIA licensing sources

The earlier proposals said cuFile, nvJitLink and NVSHMEM "appear nowhere" in the CUDA EULA, including Attachment A. That was true only of the older EULA text bundled in the eleven CUDA wheels (`ad6f5853…`). The official, version-specific CUDA 12.8.1 EULA was retained, and its Attachment A does list:
- `libcufile.so` and `libcufile_rdma.so`, with their static libraries;
- `libnvJitLink.so` and `libnvJitLink_static.a`.

These two packages are now recorded as an **applicability discrepancy requiring review**. That is neither a finding that no grant exists nor a grant: the reviewer must decide which text governs each wheel and whether the proposed distribution meets the conditions.

**NVSHMEM** has its own terms. The `License.txt` at `NVIDIA/nvshmem` tag `v3.4.5-0` is the NVIDIA SDK licence plus an NVSHMEM supplement that makes "any portion of the SDK" distributable. That remains subject to the SDK's application-incorporation requirements. The wheel itself ships the CUDA EULA instead.

**CUTLASS DSL's** bundled EULA is byte-identical to `EULA.txt` at `NVIDIA/cutlass` tags v4.2.0 through v4.5.0. In that text, no grant has been identified for the compiled files in `nvidia_cutlass_dsl_libs_base`. It is a required dependency:
- `flashinfer-python==0.6.6` requires `nvidia-cutlass-dsl>=4.3.4`;
- `quack-kernels==0.4.1` requires `nvidia-cutlass-dsl>=4.4.2`;
- `nvidia-cutlass-dsl==4.5.0.dev0` requires `nvidia-cutlass-dsl-libs-base==4.5.0.dev0`.

The reconciliation also found library files in three "listed" CUDA wheels that neither Attachment A names. These are specific questions for the reviewer:
- CUPTI: `libcheckpoint`, `libnvperf_host`, `libnvperf_target`, `libpcsamplingutil`;
- NVRTC: the `.alt` libraries;
- cuSOLVER: `libcusolverMg`.

### Repository tag check

The openllmetry tag `v0.5.1` named earlier is an unrelated monorepo release; at that tag, `opentelemetry-semantic-conventions-ai` is version 0.0.12. The source is now commit `ddcff1c…`, which set the package to 0.5.1 on 2026-03-26, the PyPI upload date. Its LICENSE is byte-identical to the text gathered before, so only the source record changed. The tags for flashinfer `v0.6.6`, loguru `0.7.3`, mistral-common `v1.11.1` and model-hosting-container-standards `v0.1.14` each carry the exact version.
| Upload and Kaggle access | not started; needs record B | — |
| GPU-disabled smoke-test package | not started | — |
| GPU smoke test | not started; needs record C | — |

### Decisions-file schema change

The decisions file gained two columns, `conditions` and `conditions_satisfied`. These are parallel `|`-separated lists, one entry per condition. Before the change, the file (`43c7a769…88be`, committed only by the tool in `f1dd4c2`) was verified to be the untouched template: 174 rows, all `unresolved`, with no rationale, notices, questions or date. It was therefore recreated under the new columns (`b754d3ac…9e`), and no human input was lost. Tools still never overwrite an existing decisions file.

## Remaining blockers, in order

1. **Qualified review of the four priority artifacts, against the retained primary sources.** These are:
   - `nvidia_cufile_cu12` and `nvidia_nvjitlink_cu12`: the applicability discrepancy above.
   - `nvidia_nvshmem_cu12`: which terms govern, the NVSHMEM supplement or the bundled CUDA EULA.
   - `nvidia_cutlass_dsl_libs_base`: whether any grant covers its compiled files.

   Obtain NVIDIA clarification where the terms stay unclear. Each decision must record the exact applicability, the obligations and any remaining questions.
2. **The designated reviewer decides every other artifact individually.** No blanket approval. These include:
   - the other NVIDIA rows (8 listed CUDA components, cuDNN, cuSPARSELt, `nvidia_cutlass_dsl`), all on the stand-alone-distribution question;
   - the LGPL and MPL source obligations for `opencv_python_headless`, `pyzmq` and `pillow`;
   - 5 batch-2 rows: undeclared licences, or a declared licence not found in the documents;
   - the conditional candidates.

   If an artifact cannot be cleared, the owner chooses an explicit alternative. It is never silently dropped. Removing an artifact requires an explicitly revised dependency set and fresh validation: a new manifest, closure, download and install check. Using the libraries preinstalled in the Kaggle image would be a new runtime revision, made only after their exact versions are established and shown to satisfy both the runtime and the package requirements. It is never a silent substitution.
3. **The required notices are produced at build.** These are the per-wheel licence documents, the upstream texts and NOTICE files, `LICENSES/upstream-sources.json`, and a `NOTICES.md` generated from the recorded conditions (each condition with how it was satisfied).
4. **The owner confirms the dataset name and initial access.** The reviewer recommends `arc3-vllm-0.19.0-cu128-wheelhouse-r2`, private. Private access is not a substitute for redistribution clearance.

The sequence after that is fixed:
1. Record A: local build.
2. Inspect the exact bundle.
3. Separate upload approval (record B).
4. Separately authorized GPU smoke test (record C).
5. Research runs.

## Record A: local bundle build (draft)

| Field | Value |
|---|---|
| Action approved | build the R2 bundle locally only (no upload) |
| Download manifest | `reports/wheelhouse_download_manifest.json`, manifest_sha256 `3691cb8854df4d8ff10e42ca9957fddb9a8ae0362064e7b31b3205891af0d546` (file sha256 `91ad9ede…462b`) |
| Bundle plan | `reports/wheelhouse_r2_bundle_plan.json`, sha256 `d8da7cbea5db811237cde675c5c7a7c11835e5598f9ac4b7db65148a97797624` (425 files, including the 16 upstream licence and NOTICE texts, `LICENSES/upstream-sources.json` and `NOTICES.md`). It is regenerated, and its hash re-recorded here, once decisions are complete. |
| Upstream licence index | `reports/wheelhouse_upstream_licenses/index.json`, sha256 `c274596833422d7b9d85e58c6ffb9e32019ab5f8e5b1f06b4730925f037860e9` |
| NVIDIA reconciliation | `reports/wheelhouse_nvidia_licence_reconciliation.json`, sha256 `497640affe72bda71f962b459e247d34886206ed99dd82a25cad0f16add063c9` |
| Decisions file | `reports/wheelhouse_redistribution_decisions.csv`, sha256 at approval: _to fill_ |
| **Eligibility rule (enforced by the builder)** | Every included artifact must be `approved`, or `approved_with_conditions` with every condition documented as satisfied. Each decision must identify the exact artifact hash, rationale, reviewer and date. `unresolved`, `restricted` and `excluded` artifacts block this bundle. Required dependencies must not be silently omitted. The builder calls `bundle_eligibility()` (`scripts/plan_wheelhouse_r2_bundle.py`) and writes nothing unless it returns no blockers. The planning script reports an unresolved draft but does not treat it as an error. |
| Source revision | _to fill_: the reviewed commit |
| Output location | outside the repository, e.g. `~/.local/share/agi/wheelhouse-r2-bundle/` |
| Checksum construction | `bundle-manifest.json` covers the payload only (never itself, never `SHA256SUMS`); `SHA256SUMS` covers the payload plus the finished manifest (never itself) |
| Required checks | eligibility has no blockers; the file inventory equals the plan; sizes and hashes match; no duplicate paths; no credentials or unrelated files; a rebuild from identical inputs reproduces every file hash |
| Deliverables for review | exact inventory, total size, `bundle-manifest.json` hash, **`SHA256SUMS` hash**, `NOTICES.md` |
| Approver / date | _to fill_ |

## Record B: upload and access (draft)

| Field | Value |
|---|---|
| Action approved | upload exactly the reviewed bundle to the team-controlled Kaggle account |
| Bundle identity | `SHA256SUMS` sha256: _from record A_ |
| Dataset name / access | `arc3-vllm-0.19.0-cu128-wheelhouse-r2` / private (_to confirm_) |
| Description | a new replacement bundle, not a byte-identical reconstruction of any earlier dataset; states the licence terms that govern the NVIDIA wheels, as recorded in the decisions |
| After upload | record the dataset reference and version; confirm the launch account can list the files and attach that version; treat any provider `invalid*Sources` result as failure even with HTTP 200; re-verify `SHA256SUMS` against the attached files |
| Historical record | the earlier inaccessible dataset and the consumed attempt stay documented unchanged |
| Approver / date | _to fill_ |

## Record C: runtime smoke-test compute authorization (draft)

| Field | Value |
|---|---|
| Purpose | runtime compatibility only: no solving claim, no Phase 4 completion |
| Package / source lock | _to fill_: the reviewed GPU-disabled smoke-test package and its lock hash |
| Dataset | `arc3-vllm-0.19.0-cu128-wheelhouse-r2`, version _from record B_ |
| Model | Qwen/Qwen3-VL-30B-A3B-Instruct-FP8, revision `d9748a51ae66354c4dad665aab2c71f26cf2c8cd`; tokenizer, chat template and inference settings pinned |
| Attempts | 1; no automatic retry |
| Time | at most 3,600 s authorized; one clock from installation start through cleanup; admission cutoff and cleanup reserve _to freeze_ |
| Model requests | at most 12 in total, **including** startup and cancellation probes |
| Checks | Python, Linux/glibc, GPU and driver facts; bundle integrity; clean offline install; package versions, `pip check`, imports, torch CUDA build; GPU binding and telemetry; model startup; bounded inference; cancellation with return to an idle server; worker and model termination; GPU cleanup; retained evidence |
| Failure behaviour | a runtime mismatch fails explicitly (no upgrade, no model change); a failure consumes the attempt and is diagnosed before any new authorization |
| Approver / date | _to fill_ |
