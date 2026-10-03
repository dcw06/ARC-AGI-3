# R7: provider-specific access receipts and successor preparation

Read-only provider checks were performed for the exact frozen sources. Both
GetDataset and ListDatasetFiles return 403 datasets.get denied for the wheelhouse.
The competition identity and first file page are accessible (HTTP 200), as are
the model instance identity and explicitly requested model version 1 file page.
The first parser rejected the provider's capitalized Transformers URL segment;
that exact casing is now used and the retained model response replays correctly.
The initial result.json is preserved; final interpretation comes from the tested
receipt parser, not that initial draft verdict.

Wheelhouse access is NOT resolved. No alternate source, credential, sharing or
provider configuration was changed. An owner/account-side confirmation is needed
that the exact dataset exists and is shared with daichongwei06. No new launch
approval, replacement budget or reservation is requested while this is blocked.

## Provider receipt construction

stagnation_provider_preflight_v1.py admits only six hard-coded read-only RPCs.
Each retains the exact request identity, response bytes/hash, status and timestamp.
Replay verifies all fields, five-minute freshness, non-truncation, exact dataset/
model/competition identity, and nonempty named file entries. The explicit model
version-1 list request binds the version independently of the current version.
Caller-supplied normalized accessible/resolved flags are recomputed, not trusted.
The preparation boundary runs this provider-specific validation before consuming
explicit approval records; it cannot generate approvals or submit a notebook.

These are first-page read-access receipts, not complete file inventory, model or
wheel checksums, install evidence or guaranteed SaveKernel attachment acceptance.
The successor rejected-attachment response validator remains required. Historical
R6 code, records, consumed claim and previous archive manifests remain unchanged.

## Review scope

Three new offline tests pass, including actual retained 403/200 responses,
request/identity/hash/status/freshness mutations and an integrated denied-access
path that never reaches approval handling. The four preparatory attachment tests
remain applicable; no request, policy, model, decoding, token budget or telemetry
change was made.

The R7 notebook is a GPU-disabled preparation snapshot based on R4's exact
runtime payload, adding the provider-preflight and approval/attachment helpers.
Its entrypoint deliberately refuses instead of calling a live launcher. The
package verifier checks every source/document/artifact and embedded Python file,
executes the unpacked refusal, and verifies extracted-source removal. It does not
claim to exercise a replacement live authorization or provider submission path.

Commands in the existing Linux development environment:

```sh
python -m unittest discover -s tests -p test_ssv_provider_preflight.py -v
python -m unittest discover -s tests -p test_ssv_attachment_repair.py -v
python -m scripts.build_review_stagnation_preparation_r7
```

Replaying retained responses uses their observation timestamp and is historical
evidence only. A future launch requires new fresh provider reads. The raw provider
metadata includes public descriptive fields and potentially expiring thumbnail
URLs; none are used as credentials or model input.

## Remaining gate

Obtain owner-side wheelhouse access clarification, repeat read-only checks after
access is restored, and only then review a launch-capable successor with explicit
source, fresh replacement-budget and launch decisions. Do not reuse the consumed
R6 reservation. Exact old billing and independent cleanup remain unknown. Real
GPU timing, the second qualified continuation control and Phase 4 remain open.
