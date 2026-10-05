# Wheelhouse R2: proposed approval records and remaining blockers

Prepared October 4, 2026 on `wheelhouse-replacement-audit`. Updated after the review of `f1dd4c2`/`fae8157`/`f4392cf`, which closed the four tooling findings.

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
| Tooling review | closed (review of `f1dd4c2`/`fae8157`/`f4392cf`) | `reports/wheelhouse_tooling_checks_f1dd4c2.json`; this update's checks are recorded alongside its commit |
| Upstream licence texts | gathered for all 9 wheels that ship none | `reports/wheelhouse_upstream_licenses/` (index `054c16ab…d5`: source URL, source hash, member and SHA-256 of each of the 14 texts) |
| Proposed dispositions | batch 1 prepared (43 flagged artifacts); batch 2 (131 unflagged) not yet proposed | `reports/wheelhouse_redistribution_proposed_dispositions.{csv,md}` (csv `71606ec5…de`) |
| Redistribution decisions | **open**: 174/174 unresolved | decisions file `b754d3ac…9e` |
| Local bundle build | not started; needs record A | plan `reports/wheelhouse_r2_bundle_plan.json` (`6140fe79…de`, 423 files; build eligibility: not eligible, 174 blockers) |
| Upload and Kaggle access | not started; needs record B | — |
| GPU-disabled smoke-test package | not started | — |
| GPU smoke test | not started; needs record C | — |

### Decisions-file schema change

The decisions file gained two columns, `conditions` and `conditions_satisfied`. These are parallel `|`-separated lists, one entry per condition. Before the change, the file (`43c7a769…88be`, committed only by the tool in `f1dd4c2`) was verified to be the untouched template: 174 rows, all `unresolved`, with no rationale, notices, questions or date. It was therefore recreated under the new columns (`b754d3ac…9e`), and no human input was lost. Tools still never overwrite an existing decisions file.

## Remaining blockers, in order

1. **The designated reviewer resolves the proposals.** Do not blanket-approve. Start with:
   - **4 artifacts with no distribution grant identified:**
     - `nvidia_cufile_cu12`, `nvidia_nvjitlink_cu12` and `nvidia_nvshmem_cu12`: absent from the CUDA EULA, including Attachment A.
     - `nvidia_cutlass_dsl_libs_base`: it ships binaries, but its EULA grants distribution of Python source files only.
   - **14 artifacts that need qualified review:**
     - 8 CUDA Toolkit components that Attachment A lists, plus cuDNN and cuSPARSELt. The question is whether a private, team-only dataset is application-incorporated or stand-alone distribution.
     - `nvidia_cutlass_dsl`.
     - LGPL/MPL binary source obligations for `opencv_python_headless`, `pyzmq` and `pillow`.
   - **25 conditional candidates.**

   Each artifact then needs its own recorded decision, including the 131 unflagged artifacts. If an artifact cannot be cleared, the owner chooses an explicit alternative from those listed. Such an artifact is never silently dropped. Any change to the artifact set needs a new manifest, closure, download and install check.
2. **The required notices are produced at build.** These are the per-wheel licence documents, the upstream texts, `LICENSES/upstream-sources.json`, and a `NOTICES.md` generated from the recorded conditions (each condition with how it was satisfied).
3. **The owner confirms the dataset name and initial access.** Proposed: `arc3-vllm-0.19.0-cu128-wheelhouse-r2`, private.

## Record A: local bundle build (draft)

| Field | Value |
|---|---|
| Action approved | build the R2 bundle locally only (no upload) |
| Download manifest | `reports/wheelhouse_download_manifest.json`, manifest_sha256 `3691cb8854df4d8ff10e42ca9957fddb9a8ae0362064e7b31b3205891af0d546` (file sha256 `91ad9ede…462b`) |
| Bundle plan | `reports/wheelhouse_r2_bundle_plan.json`, sha256 `6140fe7905606e023ba091fa1dde43b823e02262efd9cccdd63eae26d55cb2de` (423 files, including the 14 upstream licence texts, `LICENSES/upstream-sources.json` and `NOTICES.md`). It is regenerated, and its hash re-recorded here, once decisions are complete. |
| Upstream licence index | `reports/wheelhouse_upstream_licenses/index.json`, sha256 `054c16abdca4844585ad2adf4f54fe080aa0df86381a869519f3bdd62291b7d5` |
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
