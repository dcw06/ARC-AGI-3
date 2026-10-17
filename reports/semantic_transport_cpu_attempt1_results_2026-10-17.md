# Semantic transport CPU attempt 1: verified completion

The first authorized r2 CPU attempt finished with provider status **COMPLETE**.
Read-only terminal collection and a separate offline audit both pass. This
verifies the actual mounted transport and reconstruction in the pinned Kaggle
image; it does not establish Semantic-SAM CUDA loading or inference.

| Check | Verified result |
|---|---|
| Provider submission | One saved version; one consumed attempt; zero automatic retries |
| Runtime configuration | Private; GPU, TPU and internet off; immutable image matches review |
| Submitted and saved source | Matches the exact authorized request and r2 source bindings |
| Worker duration | **144.189 seconds**, below the 1,100-second worker limit |
| Mounted transport | **21 files, 10,576,724,059 bytes** checked |
| Original payload | **12 reconstructed originals**, every pinned SHA256 matches |
| Manifest authority | Both separately pinned transport and original-payload manifests match |
| Cleanup | Temporary originals removed; no restoration directory remains in saved outputs |
| Evidence finalization | Result/witness hashes and final cell marker match; provider COMPLETE |
| Installations / model loads / model forward passes | **0 / 0 / 0** |
| Game actions / scorecards | **0 / 0** |
| Independent offline audit | Pass; collection hashes, source bindings, approval/claim, original manifest, cleanup and marker checked |

The duration is the measured worker lifecycle, not total provider mounting,
allocation, setup or release time. The requested session timeout was 1,200
seconds. The worker used the corrected work/final alarms with a 120-second
cleanup reserve.

The provider API returns an unversioned saved attachment reference. Preflight
verified current version 1, the submitted request named version 1, and the mounted
content equals its independently pinned bytes. An independently displayed saved
attachment version label is not claimed. This qualification does not change the
verified byte identity.

One read-only collector initially refused Kaggle's output-download hostname
before downloading the result files. The hostname was then inspected without
exposing signed URLs, and the two small results were retrieved credential-free
from the exact provider-registered output URLs. The stopped collector receipt is
preserved. Collection made no provider write, compute retry or new submission.

All private source, approval, reservation, claim, provider logs, output bytes,
collection manifests and audit records remain git-ignored. The consumed CPU
attempt and every earlier attempt remain preserved.

## Next gate

Prepare and review the separate final GPU smoke package using the verified
transport decoder, mounted dataset and isolated runtime. It must bind the
one-image seeded/automatic experiment, exact model/source/runtime bytes,
immutable image, scoped use evidence and limits. Actual Semantic-SAM CUDA loading,
mask generation, visual inspection and saved-output replay remain pending.
This CPU approval grants no GPU authorization or automatic follow-up launch.
