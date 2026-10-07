# Direct-publisher smoke preparation, October 6, 2026

This retains the original CPU-only intake draft for consuming `driessmit1/arc3-vllm-h100-wheelhouse-v3`, requested version 1. A separate runtime runner and review candidate are now implemented; see [runner.md](runner.md) for the current source/evidence gates. A private derivative of the CPU verifier has completed actual mounted-wheel verification: see [cpu_verification.md](cpu_verification.md). No packages were installed and no GPU job, final GPU package approval or compute authorization occurred.

The original anonymous checks in `availability.json` returned HTTP 200 for dataset view/list and the three small files. View reports version 1; all three downloaded files match the retained evidence. The publisher README says the dataset was recreated October 5. Earlier 403 responses do not establish current unavailability. In the later CPU follow-up, WSL authentication established account identity/reference attachment. The operator then confirmed version 1 in the saved-run Input panel; this observation is retained privately and hash-bound to the authenticated metadata and byte evidence. Pulled API metadata still omits the version suffix. See [cpu_verification.md](cpu_verification.md) for the verification method and future-launch revalidation requirement.

Both requirements locks contain the same 174 package/version pins. The publisher's has no embedded hashes; the retained trusted lock has 174. The proposed installation must use the trusted lock, without dropping `--require-hashes` or changing versions.

## Reviewable intake package

`certification/direct_publisher_smoke_v1/` retains the trusted manifest and exact hash-pinned lock, a proposed use/compute record with unresolved gates, and a CPU-only byte verifier. The verifier requires the exact flat dataset file inventory: 174 wheels and the three bound metadata files. It checks every wheel's size and streamed SHA-256 against the trusted manifest, metadata hashes, identical package/version pins, and a final integrity deadline. It refuses changed/missing/extra files and symlinks. It does not execute installed package code or invoke pip, a model server, or a GPU query.

`notebooks/direct-publisher-smoke-v1-preflight-review-r1/` is an embedded-source snapshot of this intake only. GPU, TPU and internet are disabled; no model is attached. It has not been submitted. Its metadata requests the dataset reference, but that field does not prove or pin the provider attachment version: retain separate provider evidence for version 1. A byte match does not establish provenance or permission.

Local commands:

```powershell
python -m unittest discover -s tests -p test_direct_publisher_smoke_preflight.py -v
python scripts/direct_publisher_smoke_preflight.py review-check
python scripts/direct_publisher_smoke_preflight.py verify --dataset-root <mounted-dataset-root>
```

`review-build` reproduces the snapshot in a clean checkout where its output directory does not yet exist. Its source lock binds the embedded input files and generated artifacts. A local run without a Kaggle mount must refuse before any package installation or GPU activity. Local fixture results are integrity-control evidence, not actual remote wheel verification or GPU compatibility evidence.

## Separate use assessment to complete

The 67 existing findings block the proposed redistribution bundle. Their application to direct consumption has not been assessed; do not automatically carry either clearance or every blocker into this new use. Matching bytes and public availability do not decide permission.

The deployment facts supplied in conversation are retained locally and excluded from this public draft. See [use_assessment.md](use_assessment.md) for the separate installation/use and redistribution questions. A reviewer must assess the actual account, collaborator roles, access model, publication intent, applicable agreements and payload/output handling. The reviewer outcome must bind those facts to this exact dataset/version, inventory and review snapshot. This document supplies questions, not a legal conclusion.

## Remaining work before a GPU smoke review

1. Account identity, dataset-reference attachment and saved-run version 1 are established privately using the authenticated API and operator UI observation. Bind those records to final approvals and revalidate the future launch attachment without starting a GPU job.
2. Resolve and review the specific direct-consumption permissions assessment.
3. Actual mounted-byte verification is complete for all 174 wheels; preserve and bind the [receipt](cpu_integrity_receipt_2026-10-06.json). The live runner must reverify the mounted bytes before installation.
4. Review the implemented smoke runner's source binding and installation adapter in [runner.md](runner.md). It installs from the verified flat mount with the retained trusted lock and does not assert an R2 bundle manifest. Resolve the private consuming-account binding and freeze the successor review package before final approval.
5. Preserve the existing smoke harness's startup ownership protection, uncertainty-aware cleanup, request accounting, single-attempt reservation/launch receipts and final lifecycle deadline accounting through GPU cleanup, evidence finalization and environment removal.
6. Freeze the final model/runtime, request plan, compute limits, review lock and authorization for that revised smoke package before any live run. The proposed values in `proposal.json` are not an authorization and changing a status label cannot complete any gate.

The historical intake deliberately provides no live launch path. The separate runtime candidate's live path remains refused by unresolved bindings and missing evidence/authorization. Existing R2 protocols, reviewer decisions and approvals are unchanged.
