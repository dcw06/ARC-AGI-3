# Wheelhouse R2: proposed redistribution dispositions (batch 1: flagged artifacts)

Prepared 2026-10-04 by Claude (assistant), for the designated reviewer; proposal only.

**These are proposals, not decisions.** Nothing here is recorded in `reports/wheelhouse_redistribution_decisions.csv`; every row there stays `unresolved` until the designated reviewer records a decision with the artifact hash, rationale, reviewer and date. No row is proposed as plain `approved`.

Counts: 25 approved_with_conditions, 4 likely_not_distributable, 14 needs_qualified_review, 131 not_yet_proposed

Values: `approved_with_conditions` (a candidate the reviewer may adopt, with the listed conditions), `needs_qualified_review` (terms unclear; qualified review required), `likely_not_distributable` (no grant identified; an explicit alternative is listed), `not_yet_proposed` (unflagged; batch 2).

## likely_not_distributable: NVIDIA CUDA Toolkit EULA (3)

### `nvidia_cufile_cu12-1.13.1.3-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `1d069003be650e131b21c932ec3d8969c1715379251f8d23a1860554b1cb24fc`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: nvidia_cufile_cu12-1.13.1.3.dist-info/License.txt (sha256 ad6f5853fba0…); CUDA Toolkit EULA (License.txt sha256 ad6f5853…): 1.1.1(3) distribution only of portions identified as distributable, incorporated in object code into an application; 1.1.2(1)-(2) the application must add material functionality and be the only accessor; 1.1.4(2) no distribution as a stand-alone product; 2.3 Linux portions may be redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com
- Rationale: cuFile (GPUDirect Storage) does not appear anywhere in this EULA, including Attachment A, so no distribution grant has been identified for it (1.1.1(3) permits distribution only of portions identified as distributable).
- Proposed conditions: only with an explicit grant identified by the reviewer or NVIDIA
- Questions for the reviewer: Is there a supplement or other NVIDIA licence that makes this component distributable? Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, which is the application), distribution "incorporated into a software application", or distribution of the SDK "as a stand-alone product"? Does private, team-only access make this use by authorized users rather than distribution?
- If not cleared: Do not redistribute; options for the owner to choose explicitly: (a) written confirmation from NVIDIA via the licensing contact; (b) take the CUDA libraries from the Kaggle base image instead (changes the runtime: needs a new manifest, closure, download and install check); (c) stop and record the bundle as blocked. Never dropped silently.

### `nvidia_nvjitlink_cu12-12.8.93-py3-none-manylinux2010_x86_64.manylinux_2_12_x86_64.whl`

- sha256 `81ff63371a7ebd6e6451970684f916be2eab07321b73c9d244dc2b4da7f73b88`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: nvidia_nvjitlink_cu12-12.8.93.dist-info/License.txt (sha256 ad6f5853fba0…); CUDA Toolkit EULA (License.txt sha256 ad6f5853…): 1.1.1(3) distribution only of portions identified as distributable, incorporated in object code into an application; 1.1.2(1)-(2) the application must add material functionality and be the only accessor; 1.1.4(2) no distribution as a stand-alone product; 2.3 Linux portions may be redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com
- Rationale: nvJitLink does not appear anywhere in this EULA, including Attachment A, so no distribution grant has been identified for it (1.1.1(3) permits distribution only of portions identified as distributable).
- Proposed conditions: only with an explicit grant identified by the reviewer or NVIDIA
- Questions for the reviewer: Is there a supplement or other NVIDIA licence that makes this component distributable? Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, which is the application), distribution "incorporated into a software application", or distribution of the SDK "as a stand-alone product"? Does private, team-only access make this use by authorized users rather than distribution?
- If not cleared: Do not redistribute; options for the owner to choose explicitly: (a) written confirmation from NVIDIA via the licensing contact; (b) take the CUDA libraries from the Kaggle base image instead (changes the runtime: needs a new manifest, closure, download and install check); (c) stop and record the bundle as blocked. Never dropped silently.

### `nvidia_nvshmem_cu12-3.4.5-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `042f2500f24c021db8a06c5eec2539027d57460e1c1a762055a6554f72c369bd`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: nvidia_nvshmem_cu12-3.4.5.dist-info/licenses/License.txt (sha256 ad6f5853fba0…); CUDA Toolkit EULA (License.txt sha256 ad6f5853…): 1.1.1(3) distribution only of portions identified as distributable, incorporated in object code into an application; 1.1.2(1)-(2) the application must add material functionality and be the only accessor; 1.1.4(2) no distribution as a stand-alone product; 2.3 Linux portions may be redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com
- Rationale: NVSHMEM does not appear anywhere in this EULA, including Attachment A, so no distribution grant has been identified for it (1.1.1(3) permits distribution only of portions identified as distributable).
- Proposed conditions: only with an explicit grant identified by the reviewer or NVIDIA
- Questions for the reviewer: Is there a supplement or other NVIDIA licence that makes this component distributable? Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, which is the application), distribution "incorporated into a software application", or distribution of the SDK "as a stand-alone product"? Does private, team-only access make this use by authorized users rather than distribution?
- If not cleared: Do not redistribute; options for the owner to choose explicitly: (a) written confirmation from NVIDIA via the licensing contact; (b) take the CUDA libraries from the Kaggle base image instead (changes the runtime: needs a new manifest, closure, download and install check); (c) stop and record the bundle as blocked. Never dropped silently.

## likely_not_distributable: NVIDIA CUTLASS DSL EULA (1)

### `nvidia_cutlass_dsl_libs_base-4.5.0.dev0-cp312-cp312-manylinux_2_28_x86_64.whl`

- sha256 `38136edf1a1cd0c49fed73dcce966c8ac8b4396bdbd996deada6f73c81f5896e`; flags: proprietary_terms_present
- Evidence: nvidia_cutlass_dsl/LICENSE (sha256 9ed3a0344d6b…); nvidia_cutlass_dsl_libs_base-4.5.0.dev0.dist-info/licenses/LICENSE (sha256 9ed3a0344d6b…)
- Rationale: CUTLASS DSL EULA (sha256 9ed3a034… for the sibling wheel; this wheel ships it twice) 1.1(d) permits distributing only "python files ... in source format" incorporated into an application; this wheel also ships compiled binaries (libcute_dsl_runtime.so, _cutlass_ir.cpython-312-x86_64-linux-gnu.so, a static .a) that no identified grant covers; 2.2 forbids making it available to others except authorized users.
- Proposed conditions: only with an explicit grant
- Questions for the reviewer: Is any grant available for the binaries? Does vLLM 0.19.0 require nvidia-cutlass-dsl at import/startup for the pinned model, or only for optional kernels? Are Kaggle notebook viewers "authorized users"?
- If not cleared: Owner chooses explicitly: NVIDIA confirmation; or a reviewed change removing nvidia-cutlass-dsl from the runtime if vLLM does not require it (any change to the artifact set needs a new approved manifest, closure, download and offline install check); or record the bundle as blocked.

## needs_qualified_review: Bundled LGPL binaries (1)

### `opencv_python_headless-4.13.0.92-cp37-abi3-manylinux_2_28_x86_64.whl`

- sha256 `0bd48544f77c68b2941392fcdf9bcd2b9cdf00e98cb8c29b2455d194763cf99e`; flags: copyleft_terms_present
- Evidence: cv2/LICENSE-3RD-PARTY.txt (sha256 0e8fac55c2f5…); cv2/LICENSE.txt (sha256 09d719058e78…); cv2/data/haarcascade_license_plate_rus_16stages.xml (sha256 4d1c44bf7a1b…); opencv_python_headless-4.13.0.92.dist-info/LICENSE-3RD-PARTY.txt (sha256 0e8fac55c2f5…); opencv_python_headless-4.13.0.92.dist-info/LICENSE.txt (sha256 09d719058e78…)
- Rationale: Apache-2.0 for OpenCV, but the wheel bundles FFmpeg shared libraries (libavcodec.so.62, libavformat.so.62, libavutil.so.60, libswresample.so.6) under LGPL-2.1 per its licence document, plus OpenSSL 1.1.1k and libgfortran. Redistributing LGPL binaries needs the licence text and the corresponding source (or a written offer); shared linking satisfies relinking.
- Proposed conditions: ship all bundled licence documents; provide (or offer in writing) the corresponding source for the bundled LGPL libraries (FFmpeg libavcodec/libavformat/libavutil/libswresample and any others); README/NOTICES state this
- Questions for the reviewer: Exactly which bundled libraries are LGPL (or GPL)? Is a pointer to the opencv-python release sources sufficient, or must the FFmpeg source be shipped? OpenSSL 1.1.1k notice requirements?
- If not cleared: If the source obligation cannot be met: the owner chooses between shipping the corresponding sources in the bundle, or a reviewed change of the runtime (any change to the artifact set needs a new approved manifest, closure, download and offline install check).

## needs_qualified_review: Bundled MPL-2.0 binary (1)

### `pyzmq-27.1.0-cp312-abi3-manylinux_2_26_x86_64.manylinux_2_28_x86_64.whl`

- sha256 `43ad9a73e3da1fab5b0e7e13402f0b2fb934ae1c876c51d0afff0e7c052eca31`; flags: copyleft_terms_present
- Evidence: pyzmq-27.1.0.dist-info/licenses/LICENSE.md (sha256 c0cf5f5c03f8…); pyzmq-27.1.0.dist-info/licenses/licenses/LICENSE.libsodium.txt (sha256 43964d976a6d…); pyzmq-27.1.0.dist-info/licenses/licenses/LICENSE.tornado.txt (sha256 cfc7749b96f6…); pyzmq-27.1.0.dist-info/licenses/licenses/LICENSE.zeromq.txt (sha256 1f256ecad192…)
- Rationale: BSD-3-Clause; the wheel bundles a compiled libzmq under MPL-2.0 (Executable Form) and libsodium (ISC). MPL-2.0 3.2(a) requires informing recipients how to obtain the Source Code Form.
- Proposed conditions: ship all bundled licence documents; README/NOTICES state where the Source Code Form of the bundled libzmq (libzmq.so.5.2.5, i.e. libzmq 4.3.x) is available
- Questions for the reviewer: Which libzmq release and source location must be cited? Is a pointer sufficient, or must the source be shipped? Any LGPL-licensed component?

## needs_qualified_review: Bundled binaries with dual-licensed components (1)

### `pillow-12.2.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`

- sha256 `62f5409336adb0663b7caa0da5c7d9e7bdbaae9ce761d34669420c2a801b2780`; flags: copyleft_terms_present
- Evidence: pillow-12.2.0.dist-info/licenses/LICENSE (sha256 13e1d5014de0…)
- Rationale: MIT-CMU; bundles compiled libraries (e.g. libfreetype, libharfbuzz, libavif, libbrotli). FreeType is FTL or GPLv2; relying on FTL requires a credit in the documentation.
- Proposed conditions: ship all bundled licence documents; record which option of each dual-licensed bundled library is relied on
- Questions for the reviewer: Confirm FTL is elected and the credit wording; identify any LGPL-only bundled library and its obligations.

## needs_qualified_review: NVIDIA CUDA Toolkit EULA (8)

### `nvidia_cublas_cu12-12.8.4.1-py3-none-manylinux_2_27_x86_64.whl`

- sha256 `8ac4e771d5a348c551b2a426eda6193c19aa630236b418086020df5ba9667142`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: nvidia_cublas_cu12-12.8.4.1.dist-info/License.txt (sha256 ad6f5853fba0…); CUDA Toolkit EULA (License.txt sha256 ad6f5853…): 1.1.1(3) distribution only of portions identified as distributable, incorporated in object code into an application; 1.1.2(1)-(2) the application must add material functionality and be the only accessor; 1.1.4(2) no distribution as a stand-alone product; 2.3 Linux portions may be redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com
- Rationale: CUDA BLAS (libcublas, libcublasLt) is listed in Attachment A as distributable, but only as incorporated into an application; a wheelhouse dataset may be a stand-alone distribution.
- Proposed conditions: if cleared: ship License.txt unmodified; files unmodified (2.3); no NVIDIA endorsement claim
- Questions for the reviewer: Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, which is the application), distribution "incorporated into a software application", or distribution of the SDK "as a stand-alone product"? Does private, team-only access make this use by authorized users rather than distribution? Do the wheel's headers/other files beyond the Attachment A libraries need to be excluded or separately cleared?
- If not cleared: Do not redistribute; options for the owner to choose explicitly: (a) written confirmation from NVIDIA via the licensing contact; (b) take the CUDA libraries from the Kaggle base image instead (changes the runtime: needs a new manifest, closure, download and install check); (c) stop and record the bundle as blocked. Never dropped silently.

### `nvidia_cuda_cupti_cu12-12.8.90-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `ea0cb07ebda26bb9b29ba82cda34849e73c166c18162d3913575b0c9db9a6182`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: nvidia_cuda_cupti_cu12-12.8.90.dist-info/License.txt (sha256 ad6f5853fba0…); CUDA Toolkit EULA (License.txt sha256 ad6f5853…): 1.1.1(3) distribution only of portions identified as distributable, incorporated in object code into an application; 1.1.2(1)-(2) the application must add material functionality and be the only accessor; 1.1.4(2) no distribution as a stand-alone product; 2.3 Linux portions may be redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com
- Rationale: CUPTI (libcupti) is listed in Attachment A as distributable, but only as incorporated into an application; a wheelhouse dataset may be a stand-alone distribution.
- Proposed conditions: if cleared: ship License.txt unmodified; files unmodified (2.3); no NVIDIA endorsement claim
- Questions for the reviewer: Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, which is the application), distribution "incorporated into a software application", or distribution of the SDK "as a stand-alone product"? Does private, team-only access make this use by authorized users rather than distribution? Do the wheel's headers/other files beyond the Attachment A libraries need to be excluded or separately cleared?
- If not cleared: Do not redistribute; options for the owner to choose explicitly: (a) written confirmation from NVIDIA via the licensing contact; (b) take the CUDA libraries from the Kaggle base image instead (changes the runtime: needs a new manifest, closure, download and install check); (c) stop and record the bundle as blocked. Never dropped silently.

### `nvidia_cuda_nvrtc_cu12-12.8.93-py3-none-manylinux2010_x86_64.manylinux_2_12_x86_64.whl`

- sha256 `a7756528852ef889772a84c6cd89d41dfa74667e24cca16bb31f8f061e3e9994`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: nvidia_cuda_nvrtc_cu12-12.8.93.dist-info/License.txt (sha256 ad6f5853fba0…); CUDA Toolkit EULA (License.txt sha256 ad6f5853…): 1.1.1(3) distribution only of portions identified as distributable, incorporated in object code into an application; 1.1.2(1)-(2) the application must add material functionality and be the only accessor; 1.1.4(2) no distribution as a stand-alone product; 2.3 Linux portions may be redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com
- Rationale: NVRTC (libnvrtc, libnvrtc-builtins) is listed in Attachment A as distributable, but only as incorporated into an application; a wheelhouse dataset may be a stand-alone distribution.
- Proposed conditions: if cleared: ship License.txt unmodified; files unmodified (2.3); no NVIDIA endorsement claim
- Questions for the reviewer: Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, which is the application), distribution "incorporated into a software application", or distribution of the SDK "as a stand-alone product"? Does private, team-only access make this use by authorized users rather than distribution? Do the wheel's headers/other files beyond the Attachment A libraries need to be excluded or separately cleared?
- If not cleared: Do not redistribute; options for the owner to choose explicitly: (a) written confirmation from NVIDIA via the licensing contact; (b) take the CUDA libraries from the Kaggle base image instead (changes the runtime: needs a new manifest, closure, download and install check); (c) stop and record the bundle as blocked. Never dropped silently.

### `nvidia_cuda_runtime_cu12-12.8.90-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `adade8dcbd0edf427b7204d480d6066d33902cab2a4707dcfc48a2d0fd44ab90`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: nvidia_cuda_runtime_cu12-12.8.90.dist-info/License.txt (sha256 ad6f5853fba0…); CUDA Toolkit EULA (License.txt sha256 ad6f5853…): 1.1.1(3) distribution only of portions identified as distributable, incorporated in object code into an application; 1.1.2(1)-(2) the application must add material functionality and be the only accessor; 1.1.4(2) no distribution as a stand-alone product; 2.3 Linux portions may be redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com
- Rationale: CUDA Runtime (libcudart) is listed in Attachment A as distributable, but only as incorporated into an application; a wheelhouse dataset may be a stand-alone distribution.
- Proposed conditions: if cleared: ship License.txt unmodified; files unmodified (2.3); no NVIDIA endorsement claim
- Questions for the reviewer: Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, which is the application), distribution "incorporated into a software application", or distribution of the SDK "as a stand-alone product"? Does private, team-only access make this use by authorized users rather than distribution? Do the wheel's headers/other files beyond the Attachment A libraries need to be excluded or separately cleared?
- If not cleared: Do not redistribute; options for the owner to choose explicitly: (a) written confirmation from NVIDIA via the licensing contact; (b) take the CUDA libraries from the Kaggle base image instead (changes the runtime: needs a new manifest, closure, download and install check); (c) stop and record the bundle as blocked. Never dropped silently.

### `nvidia_cufft_cu12-11.3.3.83-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `4d2dd21ec0b88cf61b62e6b43564355e5222e4a3fb394cac0db101f2dd0d4f74`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: nvidia_cufft_cu12-11.3.3.83.dist-info/License.txt (sha256 ad6f5853fba0…); CUDA Toolkit EULA (License.txt sha256 ad6f5853…): 1.1.1(3) distribution only of portions identified as distributable, incorporated in object code into an application; 1.1.2(1)-(2) the application must add material functionality and be the only accessor; 1.1.4(2) no distribution as a stand-alone product; 2.3 Linux portions may be redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com
- Rationale: cuFFT (libcufft) is listed in Attachment A as distributable, but only as incorporated into an application; a wheelhouse dataset may be a stand-alone distribution.
- Proposed conditions: if cleared: ship License.txt unmodified; files unmodified (2.3); no NVIDIA endorsement claim
- Questions for the reviewer: Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, which is the application), distribution "incorporated into a software application", or distribution of the SDK "as a stand-alone product"? Does private, team-only access make this use by authorized users rather than distribution? Do the wheel's headers/other files beyond the Attachment A libraries need to be excluded or separately cleared?
- If not cleared: Do not redistribute; options for the owner to choose explicitly: (a) written confirmation from NVIDIA via the licensing contact; (b) take the CUDA libraries from the Kaggle base image instead (changes the runtime: needs a new manifest, closure, download and install check); (c) stop and record the bundle as blocked. Never dropped silently.

### `nvidia_curand_cu12-10.3.9.90-py3-none-manylinux_2_27_x86_64.whl`

- sha256 `b32331d4f4df5d6eefa0554c565b626c7216f87a06a4f56fab27c3b68a830ec9`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: nvidia_curand_cu12-10.3.9.90.dist-info/License.txt (sha256 ad6f5853fba0…); CUDA Toolkit EULA (License.txt sha256 ad6f5853…): 1.1.1(3) distribution only of portions identified as distributable, incorporated in object code into an application; 1.1.2(1)-(2) the application must add material functionality and be the only accessor; 1.1.4(2) no distribution as a stand-alone product; 2.3 Linux portions may be redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com
- Rationale: cuRAND (libcurand) is listed in Attachment A as distributable, but only as incorporated into an application; a wheelhouse dataset may be a stand-alone distribution.
- Proposed conditions: if cleared: ship License.txt unmodified; files unmodified (2.3); no NVIDIA endorsement claim
- Questions for the reviewer: Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, which is the application), distribution "incorporated into a software application", or distribution of the SDK "as a stand-alone product"? Does private, team-only access make this use by authorized users rather than distribution? Do the wheel's headers/other files beyond the Attachment A libraries need to be excluded or separately cleared?
- If not cleared: Do not redistribute; options for the owner to choose explicitly: (a) written confirmation from NVIDIA via the licensing contact; (b) take the CUDA libraries from the Kaggle base image instead (changes the runtime: needs a new manifest, closure, download and install check); (c) stop and record the bundle as blocked. Never dropped silently.

### `nvidia_cusolver_cu12-11.7.3.90-py3-none-manylinux_2_27_x86_64.whl`

- sha256 `4376c11ad263152bd50ea295c05370360776f8c3427b30991df774f9fb26c450`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: nvidia_cusolver_cu12-11.7.3.90.dist-info/License.txt (sha256 ad6f5853fba0…); CUDA Toolkit EULA (License.txt sha256 ad6f5853…): 1.1.1(3) distribution only of portions identified as distributable, incorporated in object code into an application; 1.1.2(1)-(2) the application must add material functionality and be the only accessor; 1.1.4(2) no distribution as a stand-alone product; 2.3 Linux portions may be redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com
- Rationale: cuSOLVER (libcusolver) is listed in Attachment A as distributable, but only as incorporated into an application; a wheelhouse dataset may be a stand-alone distribution.
- Proposed conditions: if cleared: ship License.txt unmodified; files unmodified (2.3); no NVIDIA endorsement claim
- Questions for the reviewer: Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, which is the application), distribution "incorporated into a software application", or distribution of the SDK "as a stand-alone product"? Does private, team-only access make this use by authorized users rather than distribution? Do the wheel's headers/other files beyond the Attachment A libraries need to be excluded or separately cleared?
- If not cleared: Do not redistribute; options for the owner to choose explicitly: (a) written confirmation from NVIDIA via the licensing contact; (b) take the CUDA libraries from the Kaggle base image instead (changes the runtime: needs a new manifest, closure, download and install check); (c) stop and record the bundle as blocked. Never dropped silently.

### `nvidia_cusparse_cu12-12.5.8.93-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `1ec05d76bbbd8b61b06a80e1eaf8cf4959c3d4ce8e711b65ebd0443bb0ebb13b`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: nvidia_cusparse_cu12-12.5.8.93.dist-info/License.txt (sha256 ad6f5853fba0…); CUDA Toolkit EULA (License.txt sha256 ad6f5853…): 1.1.1(3) distribution only of portions identified as distributable, incorporated in object code into an application; 1.1.2(1)-(2) the application must add material functionality and be the only accessor; 1.1.4(2) no distribution as a stand-alone product; 2.3 Linux portions may be redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com
- Rationale: cuSPARSE (libcusparse) is listed in Attachment A as distributable, but only as incorporated into an application; a wheelhouse dataset may be a stand-alone distribution.
- Proposed conditions: if cleared: ship License.txt unmodified; files unmodified (2.3); no NVIDIA endorsement claim
- Questions for the reviewer: Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, which is the application), distribution "incorporated into a software application", or distribution of the SDK "as a stand-alone product"? Does private, team-only access make this use by authorized users rather than distribution? Do the wheel's headers/other files beyond the Attachment A libraries need to be excluded or separately cleared?
- If not cleared: Do not redistribute; options for the owner to choose explicitly: (a) written confirmation from NVIDIA via the licensing contact; (b) take the CUDA libraries from the Kaggle base image instead (changes the runtime: needs a new manifest, closure, download and install check); (c) stop and record the bundle as blocked. Never dropped silently.

## needs_qualified_review: NVIDIA CUTLASS DSL EULA (1)

### `nvidia_cutlass_dsl-4.5.0.dev0-py3-none-any.whl`

- sha256 `ee81170c5f6e660147888ab84a86aa01e46b810e7c20c9e0fc5bcc8e35bbc719`; flags: proprietary_terms_present
- Evidence: nvidia_cutlass_dsl-4.5.0.dev0.dist-info/licenses/LICENSE (sha256 9ed3a0344d6b…)
- Rationale: Metadata-only wheel (dist-info plus one .txt) under the CUTLASS DSL EULA (sha256 9ed3a034…); it ships no NVIDIA code itself but depends on nvidia-cutlass-dsl-libs-base. Its disposition should follow that wheel.
- Proposed conditions: if cleared: ship LICENSE unmodified
- Questions for the reviewer: Follow the decision for nvidia_cutlass_dsl_libs_base; is redistributing the metadata wheel alone within 1.1(d)?
- If not cleared: As for nvidia_cutlass_dsl_libs_base.

## needs_qualified_review: NVIDIA cuDNN SLA (1)

### `nvidia_cudnn_cu12-9.10.2.21-py3-none-manylinux_2_27_x86_64.whl`

- sha256 `949452be657fa16687d0930933f032835951ef0892b37d2d53824d1a84dc97a8`; flags: proprietary_terms_present
- Evidence: nvidia_cudnn_cu12-9.10.2.21.dist-info/licenses/License.txt (sha256 49cf79bdb357…)
- Rationale: cuDNN SLA (sha256 49cf79bd…) 1.1(iii)/1.2: distributable runtime .so and .h files only as incorporated into an application with material additional functionality; same stand-alone question as the CUDA EULA.
- Proposed conditions: if cleared: ship License.txt unmodified; files unmodified
- Questions for the reviewer: Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, which is the application), distribution "incorporated into a software application", or distribution of the SDK "as a stand-alone product"? Does private, team-only access make this use by authorized users rather than distribution?
- If not cleared: Do not redistribute; options for the owner to choose explicitly: (a) written confirmation from NVIDIA via the licensing contact; (b) take the CUDA libraries from the Kaggle base image instead (changes the runtime: needs a new manifest, closure, download and install check); (c) stop and record the bundle as blocked. Never dropped silently.

## needs_qualified_review: NVIDIA cuSPARSELt SLA (1)

### `nvidia_cusparselt_cu12-0.7.1-py3-none-manylinux2014_x86_64.whl`

- sha256 `f1bb701d6b930d5a7cea44c19ceb973311500847f81b634d802b7b539dc55623`; flags: proprietary_terms_present
- Evidence: nvidia/cusparselt/LICENSE.txt (sha256 e8d158885a68…)
- Rationale: cuSPARSELt SLA (sha256 e8d15888…) 1.1(iii)/1.2 and section 2: runtime .so and .h files distributable "as part of your application"; 2.2 forbids stand-alone distribution.
- Proposed conditions: if cleared: ship LICENSE.txt unmodified; files unmodified
- Questions for the reviewer: Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, which is the application), distribution "incorporated into a software application", or distribution of the SDK "as a stand-alone product"? Does private, team-only access make this use by authorized users rather than distribution?
- If not cleared: Do not redistribute; options for the owner to choose explicitly: (a) written confirmation from NVIDIA via the licensing contact; (b) take the CUDA libraries from the Kaggle base image instead (changes the runtime: needs a new manifest, closure, download and install check); (c) stop and record the bundle as blocked. Never dropped silently.

## approved_with_conditions: BSD with third-party listings (1)

### `torch-2.10.0-3-cp312-cp312-manylinux_2_28_x86_64.whl`

- sha256 `98c01b8bb5e3240426dcde1446eed6f40c778091c8544767ef1168fc663a05a6`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: torch-2.10.0.dist-info/licenses/LICENSE (sha256 2e311cbf8c76…); torch-2.10.0.dist-info/licenses/NOTICE (sha256 c2cc7bf0caec…)
- Rationale: Declared BSD-3-Clause. The NVIDIA-proprietary signals are third-party listings: the CUTLASS repository note that python/CuTeDSL is under the NVIDIA EULA, and a LicenseRef-NvidiaProprietary header listed under third_party/fbgemm/.../hstu. A name check of the wheel's 11,780 members found no CuTeDSL or hstu files. The GPL/LGPL texts are likewise third-party listings.
- Proposed conditions: ship LICENSE and NOTICE unmodified
- Questions for the reviewer: Confirm that no shipped file is under NVIDIA proprietary terms (the name check is not a content audit) and that no listed LGPL/GPL component is shipped in a way that needs more than these notices.

## approved_with_conditions: BSD with vendored CUDA headers (1)

### `numba-0.61.2-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `5b1bb509d01f23d70325d3a5a0e237cbc9544dd50e50588bc581ba860c213546`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: numba-0.61.2.dist-info/licenses/LICENSE (sha256 3a70e0a21cad…); numba-0.61.2.dist-info/licenses/LICENSES.third-party (sha256 a9d83f4ad0e4…)
- Rationale: Declared BSD. The proprietary signal is numba/cuda/cuda_fp16.h and .hpp, vendored from CUDA 11.2.2 and stated in LICENSES.third-party to be Attachment A distributable; they ship as part of numba, which adds material functionality.
- Proposed conditions: ship LICENSE and LICENSES.third-party
- Questions for the reviewer: Confirm that the vendored headers satisfy the CUDA 11.2.2 EULA when shipped inside unmodified numba, and that the GPL text in LICENSES.third-party concerns no shipped component.

## approved_with_conditions: Bundled MPL-2.0 data (1)

### `grpcio-1.80.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `4e78c4ac0d97dc2e569b2f4bcbbb447491167cb358d1a389fc4af71ab6f70411`; flags: copyleft_terms_present
- Evidence: grpcio-1.80.0.dist-info/licenses/LICENSE (sha256 58c86a3f2b5c…)
- Rationale: Apache-2.0; etc/roots.pem is under MPL-2.0 and ships unmodified as a text file (its own source form).
- Proposed conditions: ship all bundled licence documents; README/NOTICES point to the source of etc/roots.pem
- Questions for the reviewer: Confirm; identify what the LGPL signal refers to and whether it concerns a shipped binary.

## approved_with_conditions: Bundled runtime libraries (1)

### `numpy-2.2.6-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`

- sha256 `fd83c01228a688733f1ded5201c678f0c53ecc1006ffbc404db9f7a899ac6249`; flags: copyleft_terms_present
- Evidence: numpy/ma/LICENSE (sha256 05f3b8835198…); numpy/random/LICENSE.md (sha256 103166b62b80…); numpy/_core/include/numpy/random/LICENSE.txt (sha256 fbc539f47d0c…); numpy-2.2.6.dist-info/LICENSE.txt (sha256 c002bd26de7d…)
- Rationale: BSD-3-Clause; bundled libgfortran is GPL-3.0 with the GCC Runtime Library Exception, which permits redistribution with the notices.
- Proposed conditions: ship all bundled licence documents
- Questions for the reviewer: Confirm the GCC exception applies to the bundled libgfortran and libquadmath; identify the LGPL signal's component.

## approved_with_conditions: Declared LGPL-2.1-only (1)

### `pycountry-26.2.16-py3-none-any.whl`

- sha256 `115c4baf7cceaa30f59a4694d79483c9167dbce7a9de4d3d571c5f3ea77c305a`; flags: declared_copyleft, copyleft_terms_present
- Evidence: pycountry/COPYRIGHT.txt (sha256 f4b01617064b…); pycountry-26.2.16.dist-info/licenses/LICENSE.txt (sha256 3fa39c6e18a3…)
- Rationale: LGPL-2.1-only; pure Python plus ISO data files, unmodified, so the shipped files are the source; no linking or modification by us.
- Proposed conditions: ship LICENSE.txt and COPYRIGHT.txt; README/NOTICES point to the PyPI sdist for complete source
- Questions for the reviewer: Confirm LGPL-2.1 section 1 (verbatim copies of source with the licence) covers this, and that the bundled iso-codes data files carry no extra terms.

## approved_with_conditions: Declared MPL-2.0 (1)

### `certifi-2026.4.22-py3-none-any.whl`

- sha256 `3cb2210c8f88ba2318d29b0388d1023c8492ff72ecdde4ebdaddbb13a31b1c4a`; flags: declared_copyleft, copyleft_terms_present
- Evidence: certifi-2026.4.22.dist-info/licenses/LICENSE (sha256 e93716da6b9c…)
- Rationale: MPL-2.0; the wheel is unmodified and already in Source Code Form (Python plus cacert.pem), so 3.1/3.2 are met by shipping the licence and identifying where the source is available.
- Proposed conditions: ship LICENSE; README/NOTICES point to the Source Code Form (the PyPI sdist of this exact version)
- Questions for the reviewer: Confirm that shipping the licence and a source pointer meets MPL-2.0 for unmodified redistribution.

## approved_with_conditions: Declared MPL-2.0 AND MIT (1)

### `tqdm-4.67.3-py3-none-any.whl`

- sha256 `ee1e4c0e59148062281c49d80b25b67771a127c85fc9676d3be5f243206826bf`; flags: declared_copyleft, copyleft_terms_present
- Evidence: tqdm-4.67.3.dist-info/licenses/LICENCE (sha256 fcff87c3a47c…)
- Rationale: MPL-2.0 and MIT; pure Python, unmodified, in Source Code Form.
- Proposed conditions: ship LICENCE (both texts); README/NOTICES point to the PyPI sdist
- Questions for the reviewer: As for certifi.

## approved_with_conditions: False copyleft signal (2)

### `aiohappyeyeballs-2.6.1-py3-none-any.whl`

- sha256 `f349ba8f4b75cb25c99c5c2d84e997e485204d2902a9597802b0371f09331fb8`; flags: copyleft_terms_present
- Evidence: aiohappyeyeballs-2.6.1.dist-info/LICENSE (sha256 3b2f81fe21d1…)
- Rationale: PSF-2.0; the GPL mention is the PSF history table ("most ... Python releases have also been GPL-compatible"), not a copyleft licence.
- Proposed conditions: ship LICENSE
- Questions for the reviewer: Confirm.

### `typing_extensions-4.15.0-py3-none-any.whl`

- sha256 `f0fa19c6845758ab08074a0cfa8b7aecb71c999ca73d62883bc25cc018c4e548`; flags: copyleft_terms_present
- Evidence: typing_extensions-4.15.0.dist-info/licenses/LICENSE (sha256 3b2f81fe21d1…)
- Rationale: PSF-2.0; the GPL mention is the PSF history table, as for aiohappyeyeballs.
- Proposed conditions: ship LICENSE
- Questions for the reviewer: Confirm.

## approved_with_conditions: NVIDIA Software License (cuda-python) (2)

### `cuda_bindings-12.9.4-cp312-cp312-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl`

- sha256 `fda147a344e8eaeca0c6ff113d2851ffca8f7dfc0a6c932374ee5c47caa649c8`; flags: proprietary_terms_present
- Evidence: cuda_bindings-12.9.4.dist-info/licenses/LICENSE (sha256 25a91d6edfb6…)
- Rationale: LICENSE is byte-identical to cuda_python's (sha256 25a91d6e…); same grant in section 1(b) and requirements in section 2.
- Proposed conditions: ship LICENSE unmodified; dataset description as for cuda_python
- Questions for the reviewer: As for cuda_python.
- If not cleared: Do not redistribute; options for the owner to choose explicitly: (a) written confirmation from NVIDIA via the licensing contact; (b) take the CUDA libraries from the Kaggle base image instead (changes the runtime: needs a new manifest, closure, download and install check); (c) stop and record the bundle as blocked. Never dropped silently.

### `cuda_python-12.9.4-py3-none-any.whl`

- sha256 `d2cacea882a69863f1e7d27ee71d75f0684f4c76910aff839067e4f89c902279`; flags: proprietary_terms_present
- Evidence: cuda_python-12.9.4.dist-info/licenses/LICENSE (sha256 25a91d6edfb6…)
- Rationale: NVIDIA Software License (sha256 25a91d6e…) section 1(b) grants distribution subject to section 2: terms consistent with the licence, and notice to NVIDIA of known non-compliance. No application-incorporation requirement; no modification is made.
- Proposed conditions: ship LICENSE unmodified; dataset description states that the NVIDIA Software License governs these wheels and that no NVIDIA endorsement is implied
- Questions for the reviewer: Is a dataset description plus the shipped LICENSE sufficient to make the distribution terms "consistent"? Accept 3(a) (applications only for NVIDIA-GPU systems)?
- If not cleared: Do not redistribute; options for the owner to choose explicitly: (a) written confirmation from NVIDIA via the licensing contact; (b) take the CUDA libraries from the Kaggle base image instead (changes the runtime: needs a new manifest, closure, download and install check); (c) stop and record the bundle as blocked. Never dropped silently.

## approved_with_conditions: No licence file in wheel (9)

### `flashinfer_cubin-0.6.6-py3-none-any.whl`

- sha256 `36508dfc792eb5ecfb15d2c140a7702812e1fa1ab0fb03929b2ed55e3e8191f3`; flags: no_licence_file_in_wheel
- Evidence: flashinfer_cubin-0.6.6-py3-none-any.whl/LICENSE (sha256 cb67c224f503…)
- Rationale: Upstream licence obtained from the repository licence file at the release tag (https://raw.githubusercontent.com/flashinfer-ai/flashinfer/v0.6.6/LICENSE); no licence file exists in a PyPI sdist for this version.
- Proposed conditions: ship the upstream text(s) at LICENSES/flashinfer_cubin-0.6.6-py3-none-any.whl/UPSTREAM/ with their source recorded
- Questions for the reviewer: Confirm the tag matches the released version and that the repository-level licence covers this package; does the repository have a NOTICE file that Apache-2.0 4(d) requires?

### `loguru-0.7.3-py3-none-any.whl`

- sha256 `31a33c10c8e1e10422bfd431aeb5d351c7cf7fa671e3c4df004162264b28220c`; flags: no_licence_file_in_wheel
- Evidence: loguru-0.7.3-py3-none-any.whl/LICENSE (sha256 b35d026cc7ac…)
- Rationale: Upstream licence obtained from the repository licence file at the release tag (https://raw.githubusercontent.com/Delgan/loguru/0.7.3/LICENSE); no licence file exists in a PyPI sdist for this version.
- Proposed conditions: ship the upstream text(s) at LICENSES/loguru-0.7.3-py3-none-any.whl/UPSTREAM/ with their source recorded
- Questions for the reviewer: Confirm the tag matches the released version and that the repository-level licence covers this package; does the repository have a NOTICE file that Apache-2.0 4(d) requires?

### `mistral_common-1.11.1-py3-none-any.whl`

- sha256 `797fded812139069d359fc08a1a66bf994555e10bb51b613941281b91ee07135`; flags: no_licence_file_in_wheel
- Evidence: mistral_common-1.11.1-py3-none-any.whl/LICENCE (sha256 5ed6f79e7773…)
- Rationale: Upstream licence obtained from the repository licence file at the release tag (https://raw.githubusercontent.com/mistralai/mistral-common/v1.11.1/LICENCE); no licence file exists in a PyPI sdist for this version.
- Proposed conditions: ship the upstream text(s) at LICENSES/mistral_common-1.11.1-py3-none-any.whl/UPSTREAM/ with their source recorded
- Questions for the reviewer: Confirm the tag matches the released version and that the repository-level licence covers this package; does the repository have a NOTICE file that Apache-2.0 4(d) requires?

### `model_hosting_container_standards-0.1.14-py3-none-any.whl`

- sha256 `d678be6745899b8ba1e8246c96b101e7802a6a4ea3fb5d90ae8d6eb4204e84c6`; flags: no_licence_file_in_wheel
- Evidence: model_hosting_container_standards-0.1.14-py3-none-any.whl/LICENSE (sha256 09e8a9bcec80…)
- Rationale: Upstream licence obtained from the repository licence file at the release tag (https://raw.githubusercontent.com/aws/model-hosting-container-standards/v0.1.14/LICENSE); no licence file exists in a PyPI sdist for this version.
- Proposed conditions: ship the upstream text(s) at LICENSES/model_hosting_container_standards-0.1.14-py3-none-any.whl/UPSTREAM/ with their source recorded
- Questions for the reviewer: Confirm the tag matches the released version and that the repository-level licence covers this package; does the repository have a NOTICE file that Apache-2.0 4(d) requires?

### `nvidia_ml_py-13.595.45-py3-none-any.whl`

- sha256 `b65a7977f503d56154b14d683710125ef93594adb63fbf7e559336e3318f1376`; flags: no_licence_file_in_wheel
- Evidence: nvidia_ml_py-13.595.45-py3-none-any.whl/nvidia_ml_py-13.595.45__pynvml.py.licence-header.txt (sha256 4301ef224f42…)
- Rationale: Upstream licence obtained from the PyPI sdist nvidia_ml_py-13.595.45.tar.gz (sha256 c9f34897fe04…, verified against PyPI); licence notice embedded in the header of nvidia_ml_py-13.595.45/pynvml.py (the same file ships in the wheel).
- Proposed conditions: ship the upstream text(s) at LICENSES/nvidia_ml_py-13.595.45-py3-none-any.whl/UPSTREAM/ with their source recorded
- Questions for the reviewer: Confirm the text matches the declared licence and covers the wheel.

### `opentelemetry_semantic_conventions_ai-0.5.1-py3-none-any.whl`

- sha256 `25aeb22bd261543b4898a73824026d96770e5351209c7d07a0b1314762b1f6e4`; flags: no_licence_file_in_wheel
- Evidence: opentelemetry_semantic_conventions_ai-0.5.1-py3-none-any.whl/LICENSE (sha256 c71d239df917…)
- Rationale: Upstream licence obtained from the repository licence file at the release tag (https://raw.githubusercontent.com/traceloop/openllmetry/v0.5.1/LICENSE); no licence file exists in a PyPI sdist for this version.
- Proposed conditions: ship the upstream text(s) at LICENSES/opentelemetry_semantic_conventions_ai-0.5.1-py3-none-any.whl/UPSTREAM/ with their source recorded
- Questions for the reviewer: Confirm the tag matches the released version and that the repository-level licence covers this package; does the repository have a NOTICE file that Apache-2.0 4(d) requires?

### `sentencepiece-0.2.1-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`

- sha256 `0cdfecef430d985f1c2bcbfff3defd1d95dae876fbd0173376012d2d7d24044b`; flags: no_licence_file_in_wheel
- Evidence: sentencepiece-0.2.1-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl/sentencepiece-0.2.1__sentencepiece__LICENSE (sha256 cfc7749b96f6…); sentencepiece-0.2.1-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl/sentencepiece-0.2.1__sentencepiece__third_party__absl__LICENSE (sha256 d3e2f59e1d71…); sentencepiece-0.2.1-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl/sentencepiece-0.2.1__sentencepiece__third_party__darts_clone__LICENSE (sha256 155f59997298…); sentencepiece-0.2.1-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl/sentencepiece-0.2.1__sentencepiece__third_party__esaxx__LICENSE (sha256 7c28553d1d33…); sentencepiece-0.2.1-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl/sentencepiece-0.2.1__sentencepiece__third_party__protobuf-lite__LICENSE (sha256 6e5e117324af…)
- Rationale: Upstream licence obtained from the PyPI sdist sentencepiece-0.2.1.tar.gz (sha256 8138cec27c2f…, verified against PyPI).
- Proposed conditions: ship the upstream text(s) at LICENSES/sentencepiece-0.2.1-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl/UPSTREAM/ with their source recorded
- Questions for the reviewer: Confirm the text matches the declared licence and covers the wheel.

### `supervisor-4.3.0-py2.py3-none-any.whl`

- sha256 `0bcb763fddafba410f35cbde226aa7f8514b9fb82eb05a0c85f6588d1c13f8db`; flags: no_licence_file_in_wheel
- Evidence: supervisor-4.3.0-py2.py3-none-any.whl/supervisor-4.3.0__COPYRIGHT.txt (sha256 3f49f4637a22…); supervisor-4.3.0-py2.py3-none-any.whl/supervisor-4.3.0__LICENSES.txt (sha256 4c35fda9f70b…)
- Rationale: Upstream licence obtained from the PyPI sdist supervisor-4.3.0.tar.gz (sha256 4a2bf149adf4…, verified against PyPI).
- Proposed conditions: ship the upstream text(s) at LICENSES/supervisor-4.3.0-py2.py3-none-any.whl/UPSTREAM/ with their source recorded
- Questions for the reviewer: Confirm the text matches the declared licence and covers the wheel.

### `tokenizers-0.22.2-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`

- sha256 `369cc9fc8cc10cb24143873a0d95438bb8ee257bb80c71989e3ee290e8d72c67`; flags: no_licence_file_in_wheel
- Evidence: tokenizers-0.22.2-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl/tokenizers-0.22.2__tokenizers__LICENSE (sha256 c71d239df917…)
- Rationale: Upstream licence obtained from the PyPI sdist tokenizers-0.22.2.tar.gz (sha256 473b83b915e5…, verified against PyPI).
- Proposed conditions: ship the upstream text(s) at LICENSES/tokenizers-0.22.2-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl/UPSTREAM/ with their source recorded
- Questions for the reviewer: Confirm the text matches the declared licence and covers the wheel.

## approved_with_conditions: Permissive under a proprietary classifier (3)

### `nvidia_cudnn_frontend-1.18.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`

- sha256 `6c023539ca6de99234cf5102c3ec0d6af817f5396fc93028a22ba5b834a35b8a`; flags: proprietary_terms_present
- Evidence: include/cudnn_frontend/thirdparty/nlohmann/LICENSE.MIT (sha256 86b998c79289…); nvidia_cudnn_frontend-1.18.0.dist-info/licenses/LICENSE.txt (sha256 3fc4b473a2c0…)
- Rationale: The licence document (sha256 3fc4b473…) is the MIT licence; the "NVIDIA Proprietary Software" classifier is the only proprietary signal. The wheel includes a compiled module (_compiled_module.cpython-312 .so).
- Proposed conditions: ship LICENSE.txt and thirdparty/nlohmann/LICENSE.MIT
- Questions for the reviewer: Confirm that the MIT text governs the whole wheel, including the compiled module, despite the classifier.

### `nvidia_nccl_cu12-2.27.5-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `ad730cf15cb5d25fe849c6e6ca9eb5b76db16a80f13f425ac68d8e2e55624457`; flags: proprietary_terms_present
- Evidence: nvidia_nccl_cu12-2.27.5.dist-info/licenses/License.txt (sha256 0f0174a6b4e0…)
- Rationale: The licence document (sha256 0f0174a6…) is BSD-3-Clause; only the "Other/Proprietary" classifier is proprietary.
- Proposed conditions: ship License.txt
- Questions for the reviewer: Confirm that BSD-3-Clause governs the binary libnccl in this wheel despite the classifier.

### `nvidia_nvtx_cu12-12.8.90-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `5b17e2001cc0d751a5bc2c6ec6d26ad95913324a4adb86788c944f8ce9ba441f`; flags: proprietary_terms_present
- Evidence: nvidia_nvtx_cu12-12.8.90.dist-info/License.txt (sha256 9e45e856bedc…)
- Rationale: The licence document (sha256 9e45e856…) is Apache-2.0; only the "Other/Proprietary" classifier is proprietary.
- Proposed conditions: ship License.txt
- Questions for the reviewer: Confirm Apache-2.0 governs; is there an upstream NOTICE file that 4(d) requires?

## approved_with_conditions: Unrecognised text (ISC) (1)

### `shellingham-1.5.4-py2.py3-none-any.whl`

- sha256 `7ecfff8f2fd72616f7481040475a65b2bf8af90a56c89140852d1120324e8686`; flags: unrecognised_licence_text
- Evidence: shellingham-1.5.4.dist-info/LICENSE (sha256 f388fd38cad1…)
- Rationale: Read manually: the text is the ISC licence ("Permission to use, copy, modify, and distribute this software for any purpose with or without fee is hereby granted, provided that the above copyright notice and this permission notice appear in all copies"), matching the ISC metadata; the automatic matcher missed this wording.
- Proposed conditions: ship LICENSE
- Questions for the reviewer: Confirm the classification.

## approved_with_conditions: Vendored MPL-2.0 source (1)

### `setuptools-80.10.2-py3-none-any.whl`

- sha256 `95b30ddfb717250edb492926c92b5221f7ef3fbcc2b07579bcd4a27da21d0173`; flags: copyleft_terms_present
- Evidence: setuptools/_vendor/importlib_metadata-8.7.1.dist-info/licenses/LICENSE (sha256 458502e12d97…); setuptools/_vendor/jaraco_context-6.1.0.dist-info/licenses/LICENSE (sha256 9755a1851966…); setuptools/_vendor/jaraco_functools-4.4.0.dist-info/licenses/LICENSE (sha256 5a57cb4db85e…); setuptools/_vendor/more_itertools-10.8.0.dist-info/licenses/LICENSE (sha256 09f1c8c9e941…); setuptools/_vendor/packaging-26.0.dist-info/licenses/LICENSE (sha256 cad1ef5bd340…); setuptools/_vendor/packaging-26.0.dist-info/licenses/LICENSE.APACHE (sha256 0d542e0c8804…); setuptools/_vendor/packaging-26.0.dist-info/licenses/LICENSE.BSD (sha256 b70e7e9b742f…); setuptools/_vendor/platformdirs-4.4.0.dist-info/licenses/LICENSE (sha256 29e0fd62e929…); setuptools/_vendor/tomli-2.4.0.dist-info/licenses/LICENSE (sha256 b80816b0d530…); setuptools/_vendor/wheel-0.46.3.dist-info/licenses/LICENSE.txt (sha256 30c236186791…); setuptools/_vendor/zipp-3.23.0.dist-info/licenses/LICENSE (sha256 5a57cb4db85e…); setuptools/config/NOTICE (sha256 2dddf0881829…); setuptools/config/_validate_pyproject/NOTICE (sha256 5d300dbfa643…); setuptools-80.10.2.dist-info/licenses/LICENSE (sha256 86da0f01aeae…); setuptools/_vendor/autocommand-2.2.2.dist-info/LICENSE (sha256 ade78d04982d…); setuptools/_vendor/backports.tarfile-1.2.0.dist-info/LICENSE (sha256 86da0f01aeae…); setuptools/_vendor/jaraco.text-4.0.0.dist-info/LICENSE (sha256 86da0f01aeae…)
- Rationale: MIT; vendored validate-pyproject files are MPL-2.0 and ship unmodified in Source Code Form.
- Proposed conditions: ship all bundled licence documents; README/NOTICES point to the PyPI sdist
- Questions for the reviewer: Confirm; identify the source of the LGPL signal and whether it concerns a shipped file.

## Not yet proposed (batch 2)

131 unflagged artifacts; each needs its own decision before Record A.
