# Wheelhouse R2: proposed approval records and remaining blockers

Prepared October 4, 2026 on `wheelhouse-replacement-audit` at `fae8157`.

**Status.** Nothing in this document is approved.
- **Not done:** no bundle has been built, nothing has been uploaded, no compute has been reserved, and no GPU run has been launched.
- **Not decided:** no licence decision has been recorded. All 174 rows of `reports/wheelhouse_redistribution_decisions.csv` are `unresolved`.

Each record below is a template. The owner completes it at its gate, and it binds exact hashes.

## Where each gate stands

| Gate | State | Evidence |
|---|---|---|
| Metadata closure | complete | `reports/wheelhouse_metadata_closure.{json,md}` (174/174 verified; reproduces offline) |
| Download | complete (approved manifest `3691cb88…d546`) | `reports/wheelhouse_r2_download_receipt.json` (174/174 verified, 5,185,992,159 bytes) |
| CPU offline installation | passed (network-isolated) | `reports/wheelhouse_r2_offline_install_check.json` plus `reports/wheelhouse_r2_offline_install_evidence/install-check-hacm1z70/` (log and lock, hash-bound) |
| Tooling review | **open**: the fixes for the review of 6bb20bf/5f74b03 are in `f1dd4c2`, awaiting independent review | `reports/wheelhouse_tooling_checks_f1dd4c2.json` (documented command, fresh clone, no PYTHONPATH: 90/90 passed; reports reproduce) |
| Redistribution decisions | **open**: 174/174 unresolved | decisions file `43c7a769…88be`; prompts in `reports/wheelhouse_redistribution_inventory.csv`; evidence in `reports/wheelhouse_license_evidence.md` |
| Local bundle build | not started; needs record A | plan `reports/wheelhouse_r2_bundle_plan.json` (`607020a4…037c`, 407 files) |
| Upload and Kaggle access | not started; needs record B | — |
| GPU-disabled smoke-test package | not started | — |
| GPU smoke test | not started; needs record C | — |

## Remaining blockers, in order

1. **Independent review of `f1dd4c2`/`fae8157`.** This covers the four findings: unconfirmed termination as a hard failure; human decisions preserved and keyed by artifact hash; the runner importing its suites from a fresh checkout; and non-circular checksums with the installation log included in the bundle.
2. **A recorded redistribution decision, with rationale, reviewer and date, for every artifact.** Do these first:
   - the 22 rows with proprietary terms (18 NVIDIA wheels, `cuda-python`, `cuda-bindings`, `torch`, `numba`);
   - the 3 packages that declare a copyleft licence (`certifi`, `tqdm`, `pycountry`);
   - the 9 wheels without a bundled licence text, whose upstream texts must be obtained.

   Where terms are unclear, qualified review is needed. If an artifact cannot be cleared, an explicit alternative is proposed; it is never silently dropped or replaced.
3. **The required notices are prepared.** This includes the 9 upstream licence texts that the wheels do not ship.
4. **The owner confirms the dataset name and initial access.** Proposed: `arc3-vllm-0.19.0-cu128-wheelhouse-r2`, private.

## Record A: local bundle build (draft)

| Field | Value |
|---|---|
| Action approved | build the R2 bundle locally only (no upload) |
| Download manifest | `reports/wheelhouse_download_manifest.json`, manifest_sha256 `3691cb8854df4d8ff10e42ca9957fddb9a8ae0362064e7b31b3205891af0d546` (file sha256 `91ad9ede…462b`) |
| Bundle plan | `reports/wheelhouse_r2_bundle_plan.json`, sha256 `607020a4…037c` (to be regenerated, and its hash re-recorded, once decisions are complete) |
| Decisions file | `reports/wheelhouse_redistribution_decisions.csv`, sha256 at approval: _to fill_; must show no `unresolved` row for any included artifact |
| Source revision | _to fill_: the reviewed commit |
| Output location | outside the repository, e.g. `~/.local/share/agi/wheelhouse-r2-bundle/` |
| Checksum construction | `bundle-manifest.json` covers the payload only (never itself, never `SHA256SUMS`); `SHA256SUMS` covers the payload plus the finished manifest (never itself) |
| Required checks | file inventory equals the plan; sizes and hashes; no duplicate paths; no credentials or unrelated files; a rebuild from identical inputs reproduces every file hash |
| Deliverables for review | exact inventory, total size, `bundle-manifest.json` hash, **`SHA256SUMS` hash** |
| Approver / date | _to fill_ |

## Record B: upload and access (draft)

| Field | Value |
|---|---|
| Action approved | upload exactly the reviewed bundle to the team-controlled Kaggle account |
| Bundle identity | `SHA256SUMS` sha256: _from record A_ |
| Dataset name / access | `arc3-vllm-0.19.0-cu128-wheelhouse-r2` / private (_to confirm_) |
| Description | a new replacement bundle, not a byte-identical reconstruction of any earlier dataset |
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
