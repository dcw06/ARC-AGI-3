# Wheelhouse R2: proposed redistribution dispositions

Prepared 2026-10-04 by Claude (assistant), for the designated reviewer; proposal only.

**These are proposals, not decisions.** Nothing here is recorded in the decisions file; every row there stays `unresolved` until the designated reviewer records a decision with the artifact hash, rationale, reviewer and date. No row is proposed as plain `approved`, and no row may be approved in bulk.

Batch 1 (flagged, 43): 25 approved_with_conditions, 1 likely_not_distributable, 17 needs_qualified_review

Batch 2 (unflagged, 131): 126 approved_with_conditions, 5 needs_qualified_review

Values: `approved_with_conditions` (a candidate the reviewer may adopt, with the listed conditions), `needs_qualified_review` (terms unclear or applicability disputed; qualified review required), `likely_not_distributable` (no grant identified in the primary text; an explicit alternative is listed).

# Batch 1: flagged artifacts

## likely_not_distributable: NVIDIA CUTLASS DSL EULA (1)

### `nvidia_cutlass_dsl_libs_base-4.5.0.dev0-cp312-cp312-manylinux_2_28_x86_64.whl`

- sha256 `38136edf1a1cd0c49fed73dcce966c8ac8b4396bdbd996deada6f73c81f5896e`; flags: proprietary_terms_present
- Evidence: nvidia_cutlass_dsl/LICENSE (sha256 9ed3a0344d6b…); nvidia_cutlass_dsl_libs_base-4.5.0.dev0.dist-info/licenses/LICENSE (sha256 9ed3a0344d6b…); Reconciliation (cutlass-v4.5.0-eula): 3 library file(s); named in the bundled Attachment A: 0; in the official one: 0
- Rationale: The bundled LICENSE is byte-identical to EULA.txt at NVIDIA/cutlass tags v4.2.0 through v4.5.0 (sha256 9ed3a034…), so it is the primary text. Its 1.1(d) permits distributing only "python files ... in source format" incorporated into an application; the wheel also ships compiled files (libcute_dsl_runtime.so, _cutlass_ir.cpython-312-x86_64-linux-gnu.so, libcuda_dialect_runtime_static.a) that no identified grant covers; 2.2 forbids making it available to others except authorized users. It is a required dependency: flashinfer-python==0.6.6 requires nvidia-cutlass-dsl>=4.3.4 and quack-kernels==0.4.1 requires >=4.4.2.
- Proposed conditions: only with a grant identified by the reviewer or NVIDIA
- Questions for the reviewer: Is any grant available for the compiled files? Are Kaggle notebook viewers "authorized users" under section 3?
- If not cleared: Owner chooses explicitly: NVIDIA clarification; or an explicitly revised dependency set (removal is possible only through an explicitly revised dependency set with fresh validation (new manifest, closure, download and offline install check), never because an inference path seems not to use it); or record the bundle as blocked.

## needs_qualified_review: Bundled LGPL binaries (1)

### `opencv_python_headless-4.13.0.92-cp37-abi3-manylinux_2_28_x86_64.whl`

- sha256 `0bd48544f77c68b2941392fcdf9bcd2b9cdf00e98cb8c29b2455d194763cf99e`; flags: copyleft_terms_present
- Evidence: cv2/LICENSE-3RD-PARTY.txt (sha256 0e8fac55c2f5…); cv2/LICENSE.txt (sha256 09d719058e78…); cv2/data/haarcascade_license_plate_rus_16stages.xml (sha256 4d1c44bf7a1b…); opencv_python_headless-4.13.0.92.dist-info/LICENSE-3RD-PARTY.txt (sha256 0e8fac55c2f5…); opencv_python_headless-4.13.0.92.dist-info/LICENSE.txt (sha256 09d719058e78…)
- Rationale: Apache-2.0 for OpenCV, but the wheel bundles FFmpeg shared libraries (libavcodec.so.62, libavformat.so.62, libavutil.so.60, libswresample.so.6) under LGPL-2.1 per its licence document, plus OpenSSL 1.1.1k and libgfortran. Redistributing LGPL binaries needs the licence text and the corresponding source (or a written offer); shared linking satisfies relinking.
- Proposed conditions: ship all bundled licence documents; provide (or offer in writing) the corresponding source for the bundled LGPL libraries (FFmpeg libavcodec/libavformat/libavutil/libswresample and any others); README/NOTICES state this
- Questions for the reviewer: Exactly which bundled libraries are LGPL (or GPL)? Is a pointer to the opencv-python release sources sufficient, or must the FFmpeg source be shipped? OpenSSL 1.1.1k notice requirements?
- If not cleared: If the source obligation cannot be met: the owner chooses between shipping the corresponding sources in the bundle, or an explicitly revised dependency set (removal is possible only through an explicitly revised dependency set with fresh validation (new manifest, closure, download and offline install check), never because an inference path seems not to use it).

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
- Evidence: nvidia_cublas_cu12-12.8.4.1.dist-info/License.txt (sha256 ad6f5853fba0…); Bundled text: the older CUDA EULA License.txt (sha256 ad6f5853…) shared by eleven CUDA wheels. Version-specific primary source: the official CUDA 12.8.1 EULA (retained in reports/wheelhouse_primary_licence_sources/). Both: 1.1.1(3) distribution only of portions identified as distributable, incorporated into an application; 1.1.2(1)-(2) the application must add material functionality and be the only accessor; no distribution as a stand-alone product; 2.3 Linux portions redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com; Reconciliation (cuda-12.8.1-eula): 3 library file(s); named in the bundled Attachment A: 3; in the official one: 3
- Rationale: CUDA BLAS (libcublas, libcublasLt) is listed as distributable in Attachment A of both the bundled text and the official 12.8.1 EULA, but only as incorporated into an application; a wheelhouse dataset may be a stand-alone distribution.
- Proposed conditions: if cleared: ship License.txt unmodified; files unmodified (2.3); no NVIDIA endorsement claim
- Questions for the reviewer: Which text governs: the licence bundled in the wheel or the official version-specific EULA? Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, the application), distribution "incorporated into a software application", or distribution "as a stand-alone product"? Private access is not a substitute for redistribution clearance.
- If not cleared: Do not redistribute until resolved. Options for the owner to choose explicitly: (a) written clarification from NVIDIA via the licensing contact; (b) a new runtime revision using libraries preinstalled in the Kaggle image, only after their exact versions are established and shown to satisfy both the runtime and the package requirements (a new manifest, closure, download and install check; never a silent substitution); (c) record the bundle as blocked. Never dropped silently.

### `nvidia_cuda_cupti_cu12-12.8.90-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `ea0cb07ebda26bb9b29ba82cda34849e73c166c18162d3913575b0c9db9a6182`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: nvidia_cuda_cupti_cu12-12.8.90.dist-info/License.txt (sha256 ad6f5853fba0…); Bundled text: the older CUDA EULA License.txt (sha256 ad6f5853…) shared by eleven CUDA wheels. Version-specific primary source: the official CUDA 12.8.1 EULA (retained in reports/wheelhouse_primary_licence_sources/). Both: 1.1.1(3) distribution only of portions identified as distributable, incorporated into an application; 1.1.2(1)-(2) the application must add material functionality and be the only accessor; no distribution as a stand-alone product; 2.3 Linux portions redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com; Reconciliation (cuda-12.8.1-eula): 5 library file(s); named in the bundled Attachment A: 1; in the official one: 1; not named in the official Attachment A: libcheckpoint.so, libnvperf_host.so, libnvperf_target.so, libpcsamplingutil.so
- Rationale: CUPTI (libcupti) is listed as distributable in Attachment A of both the bundled text and the official 12.8.1 EULA, but only as incorporated into an application; a wheelhouse dataset may be a stand-alone distribution.
- Proposed conditions: if cleared: ship License.txt unmodified; files unmodified (2.3); no NVIDIA endorsement claim
- Questions for the reviewer: Which text governs: the licence bundled in the wheel or the official version-specific EULA? Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, the application), distribution "incorporated into a software application", or distribution "as a stand-alone product"? Private access is not a substitute for redistribution clearance. Are the files not named in Attachment A (libcheckpoint.so, libnvperf_host.so, libnvperf_target.so, libpcsamplingutil.so) distributable at all?
- If not cleared: Do not redistribute until resolved. Options for the owner to choose explicitly: (a) written clarification from NVIDIA via the licensing contact; (b) a new runtime revision using libraries preinstalled in the Kaggle image, only after their exact versions are established and shown to satisfy both the runtime and the package requirements (a new manifest, closure, download and install check; never a silent substitution); (c) record the bundle as blocked. Never dropped silently.

### `nvidia_cuda_nvrtc_cu12-12.8.93-py3-none-manylinux2010_x86_64.manylinux_2_12_x86_64.whl`

- sha256 `a7756528852ef889772a84c6cd89d41dfa74667e24cca16bb31f8f061e3e9994`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: nvidia_cuda_nvrtc_cu12-12.8.93.dist-info/License.txt (sha256 ad6f5853fba0…); Bundled text: the older CUDA EULA License.txt (sha256 ad6f5853…) shared by eleven CUDA wheels. Version-specific primary source: the official CUDA 12.8.1 EULA (retained in reports/wheelhouse_primary_licence_sources/). Both: 1.1.1(3) distribution only of portions identified as distributable, incorporated into an application; 1.1.2(1)-(2) the application must add material functionality and be the only accessor; no distribution as a stand-alone product; 2.3 Linux portions redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com; Reconciliation (cuda-12.8.1-eula): 4 library file(s); named in the bundled Attachment A: 2; in the official one: 2; not named in the official Attachment A: libnvrtc-builtins.alt.so.12.8, libnvrtc.alt.so.12
- Rationale: NVRTC (libnvrtc, libnvrtc-builtins) is listed as distributable in Attachment A of both the bundled text and the official 12.8.1 EULA, but only as incorporated into an application; a wheelhouse dataset may be a stand-alone distribution.
- Proposed conditions: if cleared: ship License.txt unmodified; files unmodified (2.3); no NVIDIA endorsement claim
- Questions for the reviewer: Which text governs: the licence bundled in the wheel or the official version-specific EULA? Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, the application), distribution "incorporated into a software application", or distribution "as a stand-alone product"? Private access is not a substitute for redistribution clearance. Are the files not named in Attachment A (libnvrtc-builtins.alt.so.12.8, libnvrtc.alt.so.12) distributable at all?
- If not cleared: Do not redistribute until resolved. Options for the owner to choose explicitly: (a) written clarification from NVIDIA via the licensing contact; (b) a new runtime revision using libraries preinstalled in the Kaggle image, only after their exact versions are established and shown to satisfy both the runtime and the package requirements (a new manifest, closure, download and install check; never a silent substitution); (c) record the bundle as blocked. Never dropped silently.

### `nvidia_cuda_runtime_cu12-12.8.90-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `adade8dcbd0edf427b7204d480d6066d33902cab2a4707dcfc48a2d0fd44ab90`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: nvidia_cuda_runtime_cu12-12.8.90.dist-info/License.txt (sha256 ad6f5853fba0…); Bundled text: the older CUDA EULA License.txt (sha256 ad6f5853…) shared by eleven CUDA wheels. Version-specific primary source: the official CUDA 12.8.1 EULA (retained in reports/wheelhouse_primary_licence_sources/). Both: 1.1.1(3) distribution only of portions identified as distributable, incorporated into an application; 1.1.2(1)-(2) the application must add material functionality and be the only accessor; no distribution as a stand-alone product; 2.3 Linux portions redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com; Reconciliation (cuda-12.8.1-eula): 1 library file(s); named in the bundled Attachment A: 1; in the official one: 1
- Rationale: CUDA Runtime (libcudart) is listed as distributable in Attachment A of both the bundled text and the official 12.8.1 EULA, but only as incorporated into an application; a wheelhouse dataset may be a stand-alone distribution.
- Proposed conditions: if cleared: ship License.txt unmodified; files unmodified (2.3); no NVIDIA endorsement claim
- Questions for the reviewer: Which text governs: the licence bundled in the wheel or the official version-specific EULA? Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, the application), distribution "incorporated into a software application", or distribution "as a stand-alone product"? Private access is not a substitute for redistribution clearance.
- If not cleared: Do not redistribute until resolved. Options for the owner to choose explicitly: (a) written clarification from NVIDIA via the licensing contact; (b) a new runtime revision using libraries preinstalled in the Kaggle image, only after their exact versions are established and shown to satisfy both the runtime and the package requirements (a new manifest, closure, download and install check; never a silent substitution); (c) record the bundle as blocked. Never dropped silently.

### `nvidia_cufft_cu12-11.3.3.83-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `4d2dd21ec0b88cf61b62e6b43564355e5222e4a3fb394cac0db101f2dd0d4f74`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: nvidia_cufft_cu12-11.3.3.83.dist-info/License.txt (sha256 ad6f5853fba0…); Bundled text: the older CUDA EULA License.txt (sha256 ad6f5853…) shared by eleven CUDA wheels. Version-specific primary source: the official CUDA 12.8.1 EULA (retained in reports/wheelhouse_primary_licence_sources/). Both: 1.1.1(3) distribution only of portions identified as distributable, incorporated into an application; 1.1.2(1)-(2) the application must add material functionality and be the only accessor; no distribution as a stand-alone product; 2.3 Linux portions redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com; Reconciliation (cuda-12.8.1-eula): 2 library file(s); named in the bundled Attachment A: 2; in the official one: 2
- Rationale: cuFFT (libcufft, libcufftw) is listed as distributable in Attachment A of both the bundled text and the official 12.8.1 EULA, but only as incorporated into an application; a wheelhouse dataset may be a stand-alone distribution.
- Proposed conditions: if cleared: ship License.txt unmodified; files unmodified (2.3); no NVIDIA endorsement claim
- Questions for the reviewer: Which text governs: the licence bundled in the wheel or the official version-specific EULA? Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, the application), distribution "incorporated into a software application", or distribution "as a stand-alone product"? Private access is not a substitute for redistribution clearance.
- If not cleared: Do not redistribute until resolved. Options for the owner to choose explicitly: (a) written clarification from NVIDIA via the licensing contact; (b) a new runtime revision using libraries preinstalled in the Kaggle image, only after their exact versions are established and shown to satisfy both the runtime and the package requirements (a new manifest, closure, download and install check; never a silent substitution); (c) record the bundle as blocked. Never dropped silently.

### `nvidia_curand_cu12-10.3.9.90-py3-none-manylinux_2_27_x86_64.whl`

- sha256 `b32331d4f4df5d6eefa0554c565b626c7216f87a06a4f56fab27c3b68a830ec9`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: nvidia_curand_cu12-10.3.9.90.dist-info/License.txt (sha256 ad6f5853fba0…); Bundled text: the older CUDA EULA License.txt (sha256 ad6f5853…) shared by eleven CUDA wheels. Version-specific primary source: the official CUDA 12.8.1 EULA (retained in reports/wheelhouse_primary_licence_sources/). Both: 1.1.1(3) distribution only of portions identified as distributable, incorporated into an application; 1.1.2(1)-(2) the application must add material functionality and be the only accessor; no distribution as a stand-alone product; 2.3 Linux portions redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com; Reconciliation (cuda-12.8.1-eula): 1 library file(s); named in the bundled Attachment A: 1; in the official one: 1
- Rationale: cuRAND (libcurand) is listed as distributable in Attachment A of both the bundled text and the official 12.8.1 EULA, but only as incorporated into an application; a wheelhouse dataset may be a stand-alone distribution.
- Proposed conditions: if cleared: ship License.txt unmodified; files unmodified (2.3); no NVIDIA endorsement claim
- Questions for the reviewer: Which text governs: the licence bundled in the wheel or the official version-specific EULA? Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, the application), distribution "incorporated into a software application", or distribution "as a stand-alone product"? Private access is not a substitute for redistribution clearance.
- If not cleared: Do not redistribute until resolved. Options for the owner to choose explicitly: (a) written clarification from NVIDIA via the licensing contact; (b) a new runtime revision using libraries preinstalled in the Kaggle image, only after their exact versions are established and shown to satisfy both the runtime and the package requirements (a new manifest, closure, download and install check; never a silent substitution); (c) record the bundle as blocked. Never dropped silently.

### `nvidia_cusolver_cu12-11.7.3.90-py3-none-manylinux_2_27_x86_64.whl`

- sha256 `4376c11ad263152bd50ea295c05370360776f8c3427b30991df774f9fb26c450`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: nvidia_cusolver_cu12-11.7.3.90.dist-info/License.txt (sha256 ad6f5853fba0…); Bundled text: the older CUDA EULA License.txt (sha256 ad6f5853…) shared by eleven CUDA wheels. Version-specific primary source: the official CUDA 12.8.1 EULA (retained in reports/wheelhouse_primary_licence_sources/). Both: 1.1.1(3) distribution only of portions identified as distributable, incorporated into an application; 1.1.2(1)-(2) the application must add material functionality and be the only accessor; no distribution as a stand-alone product; 2.3 Linux portions redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com; Reconciliation (cuda-12.8.1-eula): 2 library file(s); named in the bundled Attachment A: 1; in the official one: 1; not named in the official Attachment A: libcusolverMg.so.11
- Rationale: cuSOLVER (libcusolver) is listed as distributable in Attachment A of both the bundled text and the official 12.8.1 EULA, but only as incorporated into an application; a wheelhouse dataset may be a stand-alone distribution.
- Proposed conditions: if cleared: ship License.txt unmodified; files unmodified (2.3); no NVIDIA endorsement claim
- Questions for the reviewer: Which text governs: the licence bundled in the wheel or the official version-specific EULA? Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, the application), distribution "incorporated into a software application", or distribution "as a stand-alone product"? Private access is not a substitute for redistribution clearance. Are the files not named in Attachment A (libcusolverMg.so.11) distributable at all?
- If not cleared: Do not redistribute until resolved. Options for the owner to choose explicitly: (a) written clarification from NVIDIA via the licensing contact; (b) a new runtime revision using libraries preinstalled in the Kaggle image, only after their exact versions are established and shown to satisfy both the runtime and the package requirements (a new manifest, closure, download and install check; never a silent substitution); (c) record the bundle as blocked. Never dropped silently.

### `nvidia_cusparse_cu12-12.5.8.93-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `1ec05d76bbbd8b61b06a80e1eaf8cf4959c3d4ce8e711b65ebd0443bb0ebb13b`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: nvidia_cusparse_cu12-12.5.8.93.dist-info/License.txt (sha256 ad6f5853fba0…); Bundled text: the older CUDA EULA License.txt (sha256 ad6f5853…) shared by eleven CUDA wheels. Version-specific primary source: the official CUDA 12.8.1 EULA (retained in reports/wheelhouse_primary_licence_sources/). Both: 1.1.1(3) distribution only of portions identified as distributable, incorporated into an application; 1.1.2(1)-(2) the application must add material functionality and be the only accessor; no distribution as a stand-alone product; 2.3 Linux portions redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com; Reconciliation (cuda-12.8.1-eula): 1 library file(s); named in the bundled Attachment A: 1; in the official one: 1
- Rationale: cuSPARSE (libcusparse) is listed as distributable in Attachment A of both the bundled text and the official 12.8.1 EULA, but only as incorporated into an application; a wheelhouse dataset may be a stand-alone distribution.
- Proposed conditions: if cleared: ship License.txt unmodified; files unmodified (2.3); no NVIDIA endorsement claim
- Questions for the reviewer: Which text governs: the licence bundled in the wheel or the official version-specific EULA? Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, the application), distribution "incorporated into a software application", or distribution "as a stand-alone product"? Private access is not a substitute for redistribution clearance.
- If not cleared: Do not redistribute until resolved. Options for the owner to choose explicitly: (a) written clarification from NVIDIA via the licensing contact; (b) a new runtime revision using libraries preinstalled in the Kaggle image, only after their exact versions are established and shown to satisfy both the runtime and the package requirements (a new manifest, closure, download and install check; never a silent substitution); (c) record the bundle as blocked. Never dropped silently.

## needs_qualified_review: NVIDIA CUDA Toolkit EULA: applicability discrepancy (2)

### `nvidia_cufile_cu12-1.13.1.3-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `1d069003be650e131b21c932ec3d8969c1715379251f8d23a1860554b1cb24fc`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: nvidia_cufile_cu12-1.13.1.3.dist-info/License.txt (sha256 ad6f5853fba0…); Bundled text: the older CUDA EULA License.txt (sha256 ad6f5853…) shared by eleven CUDA wheels. Version-specific primary source: the official CUDA 12.8.1 EULA (retained in reports/wheelhouse_primary_licence_sources/). Both: 1.1.1(3) distribution only of portions identified as distributable, incorporated into an application; 1.1.2(1)-(2) the application must add material functionality and be the only accessor; no distribution as a stand-alone product; 2.3 Linux portions redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com; Reconciliation (cuda-12.8.1-eula): 2 library file(s); named in the bundled Attachment A: 0; in the official one: 2
- Rationale: Applicability discrepancy requiring review: the bundled License.txt has no cuFile entry in Attachment A, but the official CUDA 12.8.1 EULA Attachment A lists libcufile.so, libcufile_rdma.so and their static libraries as distributable. This is neither a finding that no grant exists nor a grant; the distribution conditions still apply.
- Proposed conditions: if cleared: ship License.txt unmodified and record which EULA text governs; files unmodified
- Questions for the reviewer: Which text governs: the licence bundled in the wheel or the official version-specific EULA? Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, the application), distribution "incorporated into a software application", or distribution "as a stand-alone product"? Private access is not a substitute for redistribution clearance. Does the official 12.8.1 listing apply to this wheel although its bundled text omits the component?
- If not cleared: Do not redistribute until resolved. Options for the owner to choose explicitly: (a) written clarification from NVIDIA via the licensing contact; (b) a new runtime revision using libraries preinstalled in the Kaggle image, only after their exact versions are established and shown to satisfy both the runtime and the package requirements (a new manifest, closure, download and install check; never a silent substitution); (c) record the bundle as blocked. Never dropped silently.

### `nvidia_nvjitlink_cu12-12.8.93-py3-none-manylinux2010_x86_64.manylinux_2_12_x86_64.whl`

- sha256 `81ff63371a7ebd6e6451970684f916be2eab07321b73c9d244dc2b4da7f73b88`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: nvidia_nvjitlink_cu12-12.8.93.dist-info/License.txt (sha256 ad6f5853fba0…); Bundled text: the older CUDA EULA License.txt (sha256 ad6f5853…) shared by eleven CUDA wheels. Version-specific primary source: the official CUDA 12.8.1 EULA (retained in reports/wheelhouse_primary_licence_sources/). Both: 1.1.1(3) distribution only of portions identified as distributable, incorporated into an application; 1.1.2(1)-(2) the application must add material functionality and be the only accessor; no distribution as a stand-alone product; 2.3 Linux portions redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com; Reconciliation (cuda-12.8.1-eula): 1 library file(s); named in the bundled Attachment A: 0; in the official one: 1
- Rationale: Applicability discrepancy requiring review: the bundled License.txt has no nvJitLink entry in Attachment A, but the official CUDA 12.8.1 EULA Attachment A lists libnvJitLink.so and libnvJitLink_static.a as distributable. This is neither a finding that no grant exists nor a grant; the distribution conditions still apply.
- Proposed conditions: if cleared: ship License.txt unmodified and record which EULA text governs; files unmodified
- Questions for the reviewer: Which text governs: the licence bundled in the wheel or the official version-specific EULA? Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, the application), distribution "incorporated into a software application", or distribution "as a stand-alone product"? Private access is not a substitute for redistribution clearance. Does the official 12.8.1 listing apply to this wheel although its bundled text omits the component?
- If not cleared: Do not redistribute until resolved. Options for the owner to choose explicitly: (a) written clarification from NVIDIA via the licensing contact; (b) a new runtime revision using libraries preinstalled in the Kaggle image, only after their exact versions are established and shown to satisfy both the runtime and the package requirements (a new manifest, closure, download and install check; never a silent substitution); (c) record the bundle as blocked. Never dropped silently.

## needs_qualified_review: NVIDIA CUTLASS DSL EULA (1)

### `nvidia_cutlass_dsl-4.5.0.dev0-py3-none-any.whl`

- sha256 `ee81170c5f6e660147888ab84a86aa01e46b810e7c20c9e0fc5bcc8e35bbc719`; flags: proprietary_terms_present
- Evidence: nvidia_cutlass_dsl-4.5.0.dev0.dist-info/licenses/LICENSE (sha256 9ed3a0344d6b…); Reconciliation (cutlass-v4.5.0-eula): 0 library file(s); named in the bundled Attachment A: 0; in the official one: 0
- Rationale: Metadata-only wheel (dist-info plus one .txt) under the same CUTLASS DSL EULA (sha256 9ed3a034…, identical to the tagged EULA.txt); it ships no NVIDIA code itself but depends on nvidia-cutlass-dsl-libs-base, and is required by flashinfer-python==0.6.6 and quack-kernels==0.4.1.
- Proposed conditions: if cleared: ship LICENSE unmodified
- Questions for the reviewer: Follow the decision for nvidia_cutlass_dsl_libs_base; is redistributing the metadata wheel alone within 1.1(d)?
- If not cleared: As for nvidia_cutlass_dsl_libs_base (removal is possible only through an explicitly revised dependency set with fresh validation (new manifest, closure, download and offline install check), never because an inference path seems not to use it).

## needs_qualified_review: NVIDIA cuDNN SLA (1)

### `nvidia_cudnn_cu12-9.10.2.21-py3-none-manylinux_2_27_x86_64.whl`

- sha256 `949452be657fa16687d0930933f032835951ef0892b37d2d53824d1a84dc97a8`; flags: proprietary_terms_present
- Evidence: nvidia_cudnn_cu12-9.10.2.21.dist-info/licenses/License.txt (sha256 49cf79bdb357…)
- Rationale: cuDNN SLA (sha256 49cf79bd…) 1.1(iii)/1.2: distributable runtime .so and .h files only as incorporated into an application with material additional functionality; same stand-alone question as the CUDA EULA. The version-specific primary SLA for 9.10.2 has not yet been retained and compared.
- Proposed conditions: if cleared: ship License.txt unmodified; files unmodified
- Questions for the reviewer: Which text governs: the licence bundled in the wheel or the official version-specific EULA? Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, the application), distribution "incorporated into a software application", or distribution "as a stand-alone product"? Private access is not a substitute for redistribution clearance.
- If not cleared: Do not redistribute until resolved. Options for the owner to choose explicitly: (a) written clarification from NVIDIA via the licensing contact; (b) a new runtime revision using libraries preinstalled in the Kaggle image, only after their exact versions are established and shown to satisfy both the runtime and the package requirements (a new manifest, closure, download and install check; never a silent substitution); (c) record the bundle as blocked. Never dropped silently.

## needs_qualified_review: NVIDIA cuSPARSELt SLA (1)

### `nvidia_cusparselt_cu12-0.7.1-py3-none-manylinux2014_x86_64.whl`

- sha256 `f1bb701d6b930d5a7cea44c19ceb973311500847f81b634d802b7b539dc55623`; flags: proprietary_terms_present
- Evidence: nvidia/cusparselt/LICENSE.txt (sha256 e8d158885a68…)
- Rationale: cuSPARSELt SLA (sha256 e8d15888…) 1.1(iii)/1.2 and section 2: runtime .so and .h files distributable "as part of your application"; 2.2 forbids stand-alone distribution. The version-specific primary SLA for 0.7.1 has not yet been retained and compared.
- Proposed conditions: if cleared: ship LICENSE.txt unmodified; files unmodified
- Questions for the reviewer: Which text governs: the licence bundled in the wheel or the official version-specific EULA? Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, the application), distribution "incorporated into a software application", or distribution "as a stand-alone product"? Private access is not a substitute for redistribution clearance.
- If not cleared: Do not redistribute until resolved. Options for the owner to choose explicitly: (a) written clarification from NVIDIA via the licensing contact; (b) a new runtime revision using libraries preinstalled in the Kaggle image, only after their exact versions are established and shown to satisfy both the runtime and the package requirements (a new manifest, closure, download and install check; never a silent substitution); (c) record the bundle as blocked. Never dropped silently.

## needs_qualified_review: NVSHMEM: separate product terms (1)

### `nvidia_nvshmem_cu12-3.4.5-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `042f2500f24c021db8a06c5eec2539027d57460e1c1a762055a6554f72c369bd`; flags: copyleft_terms_present, proprietary_terms_present
- Evidence: nvidia_nvshmem_cu12-3.4.5.dist-info/licenses/License.txt (sha256 ad6f5853fba0…); Reconciliation (nvshmem-v3.4.5-0-license): 14 library file(s); named in the bundled Attachment A: 0; in the official one: 0
- Rationale: The wheel bundles the CUDA Toolkit EULA, which does not mention NVSHMEM. The version-specific source, License.txt at NVIDIA/nvshmem tag v3.4.5-0, is the NVIDIA SDK licence plus an NVSHMEM supplement whose section 2 makes "any portion of the SDK" distributable, still subject to the SDK distribution requirements (incorporated into an application with material additional functionality, accessed only by it; no stand-alone distribution). GitHub metadata reports Apache-2.0 for the default branch, unlike the tag text.
- Proposed conditions: if cleared: ship the governing licence text (record which) and the NVSHMEM third-party notices; files unmodified
- Questions for the reviewer: Which text governs: the licence bundled in the wheel or the official version-specific EULA? Is a private Kaggle dataset, attached only to the team's own notebook (the ARC-AGI-3 agent, the application), distribution "incorporated into a software application", or distribution "as a stand-alone product"? Private access is not a substitute for redistribution clearance. Does the NVSHMEM supplement or the bundled CUDA EULA govern this wheel? Do the bundled third-party notices in the tag's License.txt (DF-NVSHMEM-prototype and others) need to ship?
- If not cleared: Do not redistribute until resolved. Options for the owner to choose explicitly: (a) written clarification from NVIDIA via the licensing contact; (b) a new runtime revision using libraries preinstalled in the Kaggle image, only after their exact versions are established and shown to satisfy both the runtime and the package requirements (a new manifest, closure, download and install check; never a silent substitution); (c) record the bundle as blocked. Never dropped silently.

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
- If not cleared: Do not redistribute until resolved. Options for the owner to choose explicitly: (a) written clarification from NVIDIA via the licensing contact; (b) a new runtime revision using libraries preinstalled in the Kaggle image, only after their exact versions are established and shown to satisfy both the runtime and the package requirements (a new manifest, closure, download and install check; never a silent substitution); (c) record the bundle as blocked. Never dropped silently.

### `cuda_python-12.9.4-py3-none-any.whl`

- sha256 `d2cacea882a69863f1e7d27ee71d75f0684f4c76910aff839067e4f89c902279`; flags: proprietary_terms_present
- Evidence: cuda_python-12.9.4.dist-info/licenses/LICENSE (sha256 25a91d6edfb6…)
- Rationale: NVIDIA Software License (sha256 25a91d6e…) section 1(b) grants distribution subject to section 2: terms consistent with the licence, and notice to NVIDIA of known non-compliance. No application-incorporation requirement; no modification is made.
- Proposed conditions: ship LICENSE unmodified; dataset description states that the NVIDIA Software License governs these wheels and that no NVIDIA endorsement is implied
- Questions for the reviewer: Is a dataset description plus the shipped LICENSE sufficient to make the distribution terms "consistent"? Accept 3(a) (applications only for NVIDIA-GPU systems)? Is a version-specific primary text needed?
- If not cleared: Do not redistribute until resolved. Options for the owner to choose explicitly: (a) written clarification from NVIDIA via the licensing contact; (b) a new runtime revision using libraries preinstalled in the Kaggle image, only after their exact versions are established and shown to satisfy both the runtime and the package requirements (a new manifest, closure, download and install check; never a silent substitution); (c) record the bundle as blocked. Never dropped silently.

## approved_with_conditions: No licence file in wheel (9)

### `flashinfer_cubin-0.6.6-py3-none-any.whl`

- sha256 `36508dfc792eb5ecfb15d2c140a7702812e1fa1ab0fb03929b2ed55e3e8191f3`; flags: no_licence_file_in_wheel
- Evidence: flashinfer_cubin-0.6.6-py3-none-any.whl/LICENSE (sha256 cb67c224f503…); flashinfer_cubin-0.6.6-py3-none-any.whl/NOTICE (sha256 90bb9e1dec06…)
- Rationale: Upstream licence obtained from the repository flashinfer-ai/flashinfer at commit 70b142b75b46 (ref v0.6.6), whose version.txt contains '0.6.6'; no licence file exists in a PyPI sdist for this version.
- Proposed conditions: ship the upstream text(s) at LICENSES/flashinfer_cubin-0.6.6-py3-none-any.whl/UPSTREAM/ with their source recorded; ship the upstream NOTICE (Apache-2.0 4(d))
- Questions for the reviewer: Confirm that the repository-level licence covers this package and that the wheel was built from this release.

### `loguru-0.7.3-py3-none-any.whl`

- sha256 `31a33c10c8e1e10422bfd431aeb5d351c7cf7fa671e3c4df004162264b28220c`; flags: no_licence_file_in_wheel
- Evidence: loguru-0.7.3-py3-none-any.whl/LICENSE (sha256 b35d026cc7ac…)
- Rationale: Upstream licence obtained from the repository Delgan/loguru at commit ae3bfd1b85b6 (ref 0.7.3), whose loguru/__init__.py contains '__version__ = "0.7.3"'; no licence file exists in a PyPI sdist for this version.
- Proposed conditions: ship the upstream text(s) at LICENSES/loguru-0.7.3-py3-none-any.whl/UPSTREAM/ with their source recorded
- Questions for the reviewer: Confirm that the repository-level licence covers this package and that the wheel was built from this release.

### `mistral_common-1.11.1-py3-none-any.whl`

- sha256 `797fded812139069d359fc08a1a66bf994555e10bb51b613941281b91ee07135`; flags: no_licence_file_in_wheel
- Evidence: mistral_common-1.11.1-py3-none-any.whl/LICENCE (sha256 5ed6f79e7773…)
- Rationale: Upstream licence obtained from the repository mistralai/mistral-common at commit e5fe9b0beb7d (ref v1.11.1), whose pyproject.toml contains 'version = "1.11.1"'; no licence file exists in a PyPI sdist for this version.
- Proposed conditions: ship the upstream text(s) at LICENSES/mistral_common-1.11.1-py3-none-any.whl/UPSTREAM/ with their source recorded
- Questions for the reviewer: Confirm that the repository-level licence covers this package and that the wheel was built from this release.

### `model_hosting_container_standards-0.1.14-py3-none-any.whl`

- sha256 `d678be6745899b8ba1e8246c96b101e7802a6a4ea3fb5d90ae8d6eb4204e84c6`; flags: no_licence_file_in_wheel
- Evidence: model_hosting_container_standards-0.1.14-py3-none-any.whl/LICENSE (sha256 09e8a9bcec80…); model_hosting_container_standards-0.1.14-py3-none-any.whl/NOTICE (sha256 d4290ed64c2e…)
- Rationale: Upstream licence obtained from the repository aws/model-hosting-container-standards at commit 34ee9946fa5f (ref v0.1.14), whose python/pyproject.toml contains 'version = "0.1.14"'; no licence file exists in a PyPI sdist for this version.
- Proposed conditions: ship the upstream text(s) at LICENSES/model_hosting_container_standards-0.1.14-py3-none-any.whl/UPSTREAM/ with their source recorded; ship the upstream NOTICE (Apache-2.0 4(d))
- Questions for the reviewer: Confirm that the repository-level licence covers this package and that the wheel was built from this release.

### `nvidia_ml_py-13.595.45-py3-none-any.whl`

- sha256 `b65a7977f503d56154b14d683710125ef93594adb63fbf7e559336e3318f1376`; flags: no_licence_file_in_wheel
- Evidence: nvidia_ml_py-13.595.45-py3-none-any.whl/nvidia_ml_py-13.595.45__pynvml.py.licence-header.txt (sha256 4301ef224f42…)
- Rationale: Upstream licence obtained from the PyPI sdist nvidia_ml_py-13.595.45.tar.gz (sha256 c9f34897fe04…, verified against PyPI); licence notice embedded in the header of nvidia_ml_py-13.595.45/pynvml.py (the same file ships in the wheel).
- Proposed conditions: ship the upstream text(s) at LICENSES/nvidia_ml_py-13.595.45-py3-none-any.whl/UPSTREAM/ with their source recorded
- Questions for the reviewer: Confirm the text matches the declared licence and covers the wheel.

### `opentelemetry_semantic_conventions_ai-0.5.1-py3-none-any.whl`

- sha256 `25aeb22bd261543b4898a73824026d96770e5351209c7d07a0b1314762b1f6e4`; flags: no_licence_file_in_wheel
- Evidence: opentelemetry_semantic_conventions_ai-0.5.1-py3-none-any.whl/LICENSE (sha256 c71d239df917…)
- Rationale: Upstream licence obtained from the repository traceloop/openllmetry at commit ddcff1c205bf (ref ddcff1c205bf041f262a823a08ac8915cc8d156b), whose packages/opentelemetry-semantic-conventions-ai/pyproject.toml contains 'version = "0.5.1"'; no licence file exists in a PyPI sdist for this version.
- Proposed conditions: ship the upstream text(s) at LICENSES/opentelemetry_semantic_conventions_ai-0.5.1-py3-none-any.whl/UPSTREAM/ with their source recorded
- Questions for the reviewer: Confirm that the repository-level licence covers this package and that the wheel was built from this release. Monorepo: the semconv-ai package has no package-level licence and PyPI names no repository; confirm the attribution.

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

# Batch 2: unflagged artifacts

## needs_qualified_review: Batch 2: declared licence not found in documents (3)

### `ninja-1.13.0-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `fb46acf6b93b8dd0322adc3a4945452a4e774b75b91293bafcc7b7f8e6517dfa`; flags: none
- Evidence: ninja-1.13.0.dist-info/licenses/AUTHORS.rst (sha256 6c6135b7f2e1…); ninja-1.13.0.dist-info/licenses/LICENSE_Apache_20 (sha256 73ba74dfaa52…)
- Rationale: Declared 'OSI Approved :: Apache Software License; OSI Approved :: BSD License' (AND); the wheel's documents show Apache-2.0; not found: BSD-any.
- Proposed conditions: ship the bundled licence document(s) unmodified: ninja-1.13.0.dist-info/licenses/AUTHORS.rst, ninja-1.13.0.dist-info/licenses/LICENSE_Apache_20
- Questions for the reviewer: Locate the text for BSD-any or confirm it is not needed. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `prometheus_client-0.25.0-py3-none-any.whl`

- sha256 `d5aec89e349a6ec230805d0df882f3807f74fd6c1a2fa86864e3c2279059fed1`; flags: none
- Evidence: prometheus_client-0.25.0.dist-info/licenses/LICENSE (sha256 c71d239df917…); prometheus_client-0.25.0.dist-info/licenses/NOTICE (sha256 4efa1874aeaa…)
- Rationale: Declared 'Apache-2.0 AND BSD-2-Clause' (AND); the wheel's documents show Apache-2.0; not found: BSD-2-Clause.
- Proposed conditions: ship the bundled licence document(s) unmodified: prometheus_client-0.25.0.dist-info/licenses/LICENSE, prometheus_client-0.25.0.dist-info/licenses/NOTICE; keep the NOTICE file (Apache-2.0 4(d))
- Questions for the reviewer: Locate the text for BSD-2-Clause or confirm it is not needed.

### `regex-2026.4.4-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl`

- sha256 `993f657a7c1c6ec51b5e0ba97c9817d06b84ea5fa8d82e43b9405de0defdc2b9`; flags: none
- Evidence: regex-2026.4.4.dist-info/licenses/LICENSE.txt (sha256 bff55ef4cdcc…)
- Rationale: Declared 'Apache-2.0 AND CNRI-Python' (AND); the wheel's documents show Apache-2.0; not found: CNRI-Python.
- Proposed conditions: ship the bundled licence document(s) unmodified: regex-2026.4.4.dist-info/licenses/LICENSE.txt
- Questions for the reviewer: Locate the text for CNRI-Python or confirm it is not needed. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

## needs_qualified_review: Batch 2: no declared licence (2)

### `openai_harmony-0.0.8-cp38-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`

- sha256 `c007d277218a50db8839e599ed78e0fffe5130f614c3f6d93ae257f282071a29`; flags: none
- Evidence: openai_harmony-0.0.8.dist-info/licenses/LICENSE (sha256 58d1e17ffe51…)
- Rationale: No licence in the metadata; the wheel's documents show Apache-2.0.
- Proposed conditions: ship the bundled licence document(s) unmodified: openai_harmony-0.0.8.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm the licence from the documents alone. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `quack_kernels-0.4.1-py3-none-any.whl`

- sha256 `c1c8df2935bf5156ec47d2c5384ac08b411fd0ee702d80ae916dbf6d6f5ae813`; flags: none
- Evidence: quack_kernels-0.4.1.dist-info/licenses/LICENSE (sha256 c71d239df917…)
- Rationale: No licence in the metadata; the wheel's documents show Apache-2.0.
- Proposed conditions: ship the bundled licence document(s) unmodified: quack_kernels-0.4.1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm the licence from the documents alone. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

## approved_with_conditions: Batch 2: declared and detected licences agree (126)

### `aiohttp-3.13.5-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl`

- sha256 `b18f31b80d5a33661e08c89e202edabf1986e9b49c42b4504371daeaa11b47c1`; flags: none
- Evidence: aiohttp-3.13.5.dist-info/licenses/LICENSE.txt (sha256 9f80d0db7d75…); aiohttp-3.13.5.dist-info/licenses/vendor/llhttp/LICENSE (sha256 ebca854e0134…)
- Rationale: Declared 'Apache-2.0 AND MIT'; the wheel's own documents show Apache-2.0, MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: aiohttp-3.13.5.dist-info/licenses/LICENSE.txt, aiohttp-3.13.5.dist-info/licenses/vendor/llhttp/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `aiosignal-1.4.0-py3-none-any.whl`

- sha256 `053243f8b92b990551949e63930a839ff0cf0b0ebbe0597b0f3fb19e1a0fe82e`; flags: none
- Evidence: aiosignal-1.4.0.dist-info/licenses/LICENSE (sha256 6fd5243e92dd…)
- Rationale: Declared 'Apache 2.0; OSI Approved :: Apache Software License'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: aiosignal-1.4.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `annotated_doc-0.0.4-py3-none-any.whl`

- sha256 `571ac1dc6991c450b25a9c2d84a3705e2ae7a53467b5d111c24fa8baabbed320`; flags: none
- Evidence: annotated_doc-0.0.4.dist-info/licenses/LICENSE (sha256 fff170779a6a…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: annotated_doc-0.0.4.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `annotated_types-0.7.0-py3-none-any.whl`

- sha256 `1f02e8b43a8fbbc3f3e0d4f0f4bfc8131bcb4eebe8849b8e5c773f3a1c582a53`; flags: none
- Evidence: annotated_types-0.7.0.dist-info/licenses/LICENSE (sha256 fe1049884b1a…)
- Rationale: Declared 'OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: annotated_types-0.7.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `anthropic-0.97.0-py3-none-any.whl`

- sha256 `8a1a472dfabcfc0c52ff6a3eecf724ac7e07107a2f6e2367be55ceb42f5d5613`; flags: none
- Evidence: anthropic-0.97.0.dist-info/licenses/LICENSE (sha256 8bf96984ff8b…)
- Rationale: Declared 'MIT; OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: anthropic-0.97.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `anyio-4.13.0-py3-none-any.whl`

- sha256 `08b310f9e24a9594186fd75b4f73f4a4152069e3853f1ed8bfbf58369f4ad708`; flags: none
- Evidence: anyio-4.13.0.dist-info/licenses/LICENSE (sha256 5361ac9dc58f…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: anyio-4.13.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `apache_tvm_ffi-0.1.10-cp312-abi3-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl`

- sha256 `96b69030c722572e13e30182733adfa2d604258e988b3f6630a16f397c7f9288`; flags: none
- Evidence: tvm_ffi/3rdparty/libbacktrace/LICENSE (sha256 ef8a9b324748…); apache_tvm_ffi-0.1.10.dist-info/licenses/LICENSE (sha256 bb354d8b9458…); apache_tvm_ffi-0.1.10.dist-info/licenses/NOTICE (sha256 5181189219b7…)
- Rationale: Declared 'Apache 2.0; OSI Approved :: Apache Software License'; the wheel's own documents show BSD-2-Clause, Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal. Additional families in the documents (BSD-2-Clause) are bundled notices to ship too.
- Proposed conditions: ship the bundled licence document(s) unmodified: tvm_ffi/3rdparty/libbacktrace/LICENSE, apache_tvm_ffi-0.1.10.dist-info/licenses/LICENSE, apache_tvm_ffi-0.1.10.dist-info/licenses/NOTICE; keep the NOTICE file (Apache-2.0 4(d))
- Questions for the reviewer: Confirm, artifact by artifact.

### `astor-0.8.1-py2.py3-none-any.whl`

- sha256 `070a54e890cefb5b3739d19f30f5a5ec840ffc9c50ffa7d23cc9fc1a38ebbfc5`; flags: none
- Evidence: astor-0.8.1.dist-info/LICENSE (sha256 ce41eafc2efc…)
- Rationale: Declared 'BSD-3-Clause; OSI Approved :: BSD License'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: astor-0.8.1.dist-info/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `attrs-26.1.0-py3-none-any.whl`

- sha256 `c647aa4a12dfbad9333ca4e71fe62ddc36f4e63b2d260a37a8b83d2f043ac309`; flags: none
- Evidence: attrs-26.1.0.dist-info/licenses/LICENSE (sha256 882115c95dfc…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: attrs-26.1.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `blake3-1.0.8-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`

- sha256 `504d1399b7fb91dfe5c25722d2807990493185faa1917456455480c36867adb5`; flags: none
- Evidence: blake3-1.0.8.dist-info/licenses/LICENSE (sha256 f1d7009e0628…)
- Rationale: Declared 'CC0-1.0 OR Apache-2.0'; the wheel's own documents show Apache-2.0, CC0, consistent with the declaration (OR: a choice of licence). Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: blake3-1.0.8.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `cachetools-7.0.6-py3-none-any.whl`

- sha256 `4e94956cfdd3086f12042cdd29318f5ced3893014f7d0d059bf3ead3f85b7f8b`; flags: none
- Evidence: cachetools-7.0.6.dist-info/licenses/LICENSE (sha256 28c000b52b0e…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: cachetools-7.0.6.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `cbor2-6.0.1-cp312-cp312-manylinux_2_28_x86_64.whl`

- sha256 `65f0dc88cbd2cc252c31212b0bac3d10ae8e94db5e476a662022593cdd3cc56a`; flags: none
- Evidence: cbor2-6.0.1.dist-info/licenses/LICENSE.txt (sha256 a6afd126d8f5…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: cbor2-6.0.1.dist-info/licenses/LICENSE.txt
- Questions for the reviewer: Confirm, artifact by artifact.

### `cffi-2.0.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `3e17ed538242334bf70832644a32a7aae3d83b57567f9fd60a26257e992b79ba`; flags: none
- Evidence: cffi-2.0.0.dist-info/licenses/AUTHORS (sha256 2a67a60bbfb3…); cffi-2.0.0.dist-info/licenses/LICENSE (sha256 5ba24ddc5706…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: cffi-2.0.0.dist-info/licenses/AUTHORS, cffi-2.0.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `charset_normalizer-3.4.7-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl`

- sha256 `5649fd1c7bade02f320a462fdefd0b4bd3ce036065836d4f42e0de958038e116`; flags: none
- Evidence: charset_normalizer-3.4.7.dist-info/licenses/LICENSE (sha256 6d0d41bfe170…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: charset_normalizer-3.4.7.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `click-8.3.3-py3-none-any.whl`

- sha256 `a2bf429bb3033c89fa4936ffb35d5cb471e3719e1f3c8a7c3fff0b8314305613`; flags: none
- Evidence: click-8.3.3.dist-info/licenses/LICENSE.txt (sha256 9a8ad106a394…)
- Rationale: Declared 'BSD-3-Clause'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: click-8.3.3.dist-info/licenses/LICENSE.txt
- Questions for the reviewer: Confirm, artifact by artifact.

### `cloudpickle-3.1.2-py3-none-any.whl`

- sha256 `9acb47f6afd73f60dc1df93bb801b472f05ff42fa6c84167d25cb206be1fbf4a`; flags: none
- Evidence: cloudpickle-3.1.2.dist-info/licenses/LICENSE (sha256 3029ea34173e…)
- Rationale: Declared 'BSD-3-Clause; OSI Approved :: BSD License'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: cloudpickle-3.1.2.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `compressed_tensors-0.14.0.1-py3-none-any.whl`

- sha256 `46c4940a3a779d3d97108c294bfcd9acf4bd0491f7c6737c320f0e815ec732e4`; flags: none
- Evidence: compressed_tensors-0.14.0.1.dist-info/licenses/LICENSE (sha256 c71d239df917…)
- Rationale: Declared 'Apache 2.0'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: compressed_tensors-0.14.0.1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `cryptography-47.0.0-cp311-abi3-manylinux_2_34_x86_64.whl`

- sha256 `4e1de79e047e25d6e9f8cea71c86b4a53aced64134f0f003bbcbf3655fd172c8`; flags: none
- Evidence: cryptography-47.0.0.dist-info/licenses/LICENSE (sha256 3e0c7c091a94…); cryptography-47.0.0.dist-info/licenses/LICENSE.APACHE (sha256 aac73b3148f6…); cryptography-47.0.0.dist-info/licenses/LICENSE.BSD (sha256 602c4c7482de…)
- Rationale: Declared 'Apache-2.0 OR BSD-3-Clause'; the wheel's own documents show Apache-2.0, BSD-3-Clause, consistent with the declaration (OR: a choice of licence). Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: cryptography-47.0.0.dist-info/licenses/LICENSE, cryptography-47.0.0.dist-info/licenses/LICENSE.APACHE, cryptography-47.0.0.dist-info/licenses/LICENSE.BSD
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `cuda_pathfinder-1.5.4-py3-none-any.whl`

- sha256 `9563d3175ce1828531acf4b94e1c1c7d67208c347ca002493e2654878b26f4b7`; flags: none
- Evidence: cuda_pathfinder-1.5.4.dist-info/licenses/LICENSE (sha256 0d542e0c8804…)
- Rationale: Declared 'Apache-2.0'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: cuda_pathfinder-1.5.4.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `depyf-0.20.0-py3-none-any.whl`

- sha256 `d31effad4261cebecb58955d832e448ace88f432328f95f82fd99c30fd9308d4`; flags: none
- Evidence: depyf-0.20.0.dist-info/licenses/LICENSE (sha256 973b9ad2aeca…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: depyf-0.20.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `dill-0.4.1-py3-none-any.whl`

- sha256 `1e1ce33e978ae97fcfcff5638477032b801c46c7c65cf717f95fbc2248f79a9d`; flags: none
- Evidence: dill-0.4.1.dist-info/LICENSE (sha256 f669d63bebf7…)
- Rationale: Declared 'BSD-3-Clause; OSI Approved :: BSD License'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: dill-0.4.1.dist-info/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `diskcache-5.6.3-py3-none-any.whl`

- sha256 `5e31b2d5fbad117cc363ebaf6b689474db18a1f6438bc82358b024abd4c2ca19`; flags: none
- Evidence: diskcache-5.6.3.dist-info/LICENSE (sha256 583546baa3fd…)
- Rationale: Declared 'Apache 2.0; OSI Approved :: Apache Software License'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: diskcache-5.6.3.dist-info/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `distro-1.9.0-py3-none-any.whl`

- sha256 `7bffd925d65168f85027d8da9af6bddab658135b840670a223589bc0c8ef02b2`; flags: none
- Evidence: distro-1.9.0.dist-info/LICENSE (sha256 cb5e8e7e5f4a…)
- Rationale: Declared 'Apache License, Version 2.0; OSI Approved :: Apache Software License'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: distro-1.9.0.dist-info/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `dnspython-2.8.0-py3-none-any.whl`

- sha256 `01d9bbc4a2d76bf0db7c1f729812ded6d912bd318d3b1cf81d30c0f845dbf3af`; flags: none
- Evidence: dnspython-2.8.0.dist-info/licenses/LICENSE (sha256 c3ea3ff5654b…)
- Rationale: Declared 'ISC; OSI Approved :: ISC License (ISCL)'; the wheel's own documents show ISC, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: dnspython-2.8.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `docstring_parser-0.18.0-py3-none-any.whl`

- sha256 `b3fcbed555c47d8479be0796ef7e19c2670d428d72e96da63f3a40122860374b`; flags: none
- Evidence: docstring_parser-0.18.0.dist-info/licenses/LICENSE.md (sha256 dfe514a337ae…)
- Rationale: Declared 'MIT; OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: docstring_parser-0.18.0.dist-info/licenses/LICENSE.md
- Questions for the reviewer: Confirm, artifact by artifact.

### `einops-0.8.2-py3-none-any.whl`

- sha256 `54058201ac7087911181bfec4af6091bb59380360f069276601256a76af08193`; flags: none
- Evidence: einops-0.8.2.dist-info/licenses/LICENSE (sha256 30d984364296…)
- Rationale: Declared 'MIT; OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: einops-0.8.2.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `email_validator-2.3.0-py3-none-any.whl`

- sha256 `80f13f623413e6b197ae73bb10bf4eb0908faf509ad8362c5edeb0be7fd450b4`; flags: none
- Evidence: email_validator-2.3.0.dist-info/licenses/LICENSE (sha256 672179752e10…)
- Rationale: Declared 'Unlicense; OSI Approved :: The Unlicense (Unlicense)'; the wheel's own documents show Unlicense, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: email_validator-2.3.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `fastapi-0.136.1-py3-none-any.whl`

- sha256 `a6e9d7eeada96c93a4d69cb03836b44fa34e2854accb7244a1ece36cd4781c3f`; flags: none
- Evidence: fastapi-0.136.1.dist-info/licenses/LICENSE (sha256 4ec89ffc8148…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: fastapi-0.136.1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `fastapi_cli-0.0.24-py3-none-any.whl`

- sha256 `4a1f78ed798f106b4fee85ca93b85d8fe33c0a3570f775964d37edb80b8f0edc`; flags: none
- Evidence: fastapi_cli-0.0.24.dist-info/licenses/LICENSE (sha256 16a0f907855b…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: fastapi_cli-0.0.24.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `fastapi_cloud_cli-0.17.1-py3-none-any.whl`

- sha256 `325e0199bdac7cb86f5df4f4a1d2070054095588088ef7b923a60cec458dcd63`; flags: none
- Evidence: fastapi_cloud_cli-0.17.1.dist-info/licenses/LICENSE (sha256 16a0f907855b…)
- Rationale: Declared 'MIT; OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: fastapi_cloud_cli-0.17.1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `fastar-0.11.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`

- sha256 `ef5a6071121e05d8287fc75bccb054bcbac8bb0501200a0c0a8feeace5303ea4`; flags: none
- Evidence: fastar-0.11.0.dist-info/licenses/LICENSE (sha256 ad8190a4c8a2…)
- Rationale: Declared 'MIT; OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: fastar-0.11.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `filelock-3.29.0-py3-none-any.whl`

- sha256 `96f5f6344709aa1572bbf631c640e4ebeeb519e08da902c39a001882f30ac258`; flags: none
- Evidence: filelock-3.29.0.dist-info/licenses/LICENSE (sha256 608c89d5060a…)
- Rationale: Declared 'MIT; OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: filelock-3.29.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `flashinfer_python-0.6.6-py3-none-any.whl`

- sha256 `078f158636969eec1a0d3dea19c3ca90b426b66df89bbf7b7b8276ce2ec08148`; flags: none
- Evidence: flashinfer/data/spdlog/include/spdlog/fmt/bundled/fmt.license.rst (sha256 825c9324e70f…); flashinfer_python-0.6.6.dist-info/licenses/LICENSE (sha256 cb67c224f503…)
- Rationale: Declared 'Apache-2.0'; the wheel's own documents show MIT, Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal. Additional families in the documents (MIT) are bundled notices to ship too.
- Proposed conditions: ship the bundled licence document(s) unmodified: flashinfer/data/spdlog/include/spdlog/fmt/bundled/fmt.license.rst, flashinfer_python-0.6.6.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `frozenlist-1.8.0-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl`

- sha256 `494a5952b1c597ba44e0e78113a7266e656b9794eec897b19ead706bd7074383`; flags: none
- Evidence: frozenlist-1.8.0.dist-info/licenses/LICENSE (sha256 6fd5243e92dd…)
- Rationale: Declared 'Apache-2.0'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: frozenlist-1.8.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `fsspec-2026.4.0-py3-none-any.whl`

- sha256 `11ef7bb35dab8a394fde6e608221d5cf3e8499401c249bebaeaad760a1a8dec2`; flags: none
- Evidence: fsspec-2026.4.0.dist-info/licenses/LICENSE (sha256 2dc35496ce53…)
- Rationale: Declared 'BSD-3-Clause'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: fsspec-2026.4.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `gguf-0.18.0-py3-none-any.whl`

- sha256 `af93f7ef198a265cbde5fa6a6b3101528bca285903949ab0a3e591cd993a1864`; flags: none
- Evidence: gguf-0.18.0.dist-info/licenses/LICENSE (sha256 ef78c7e6659e…)
- Rationale: Declared 'OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: gguf-0.18.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `googleapis_common_protos-1.74.0-py3-none-any.whl`

- sha256 `702216f78610bb510e3f12ac3cafd281b7ac45cc5d86e90ad87e4d301a3426b5`; flags: none
- Evidence: googleapis_common_protos-1.74.0.dist-info/licenses/LICENSE (sha256 cfc7749b96f6…)
- Rationale: Declared 'Apache 2.0; OSI Approved :: Apache Software License'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: googleapis_common_protos-1.74.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `h11-0.16.0-py3-none-any.whl`

- sha256 `63cf8bbe7522de3bf65932fda1d9c2772064ffb3dae62d55932da54b31cb6c86`; flags: none
- Evidence: h11-0.16.0.dist-info/licenses/LICENSE.txt (sha256 37db5bb85926…)
- Rationale: Declared 'MIT; OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: h11-0.16.0.dist-info/licenses/LICENSE.txt
- Questions for the reviewer: Confirm, artifact by artifact.

### `hf_xet-1.4.3-cp37-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `fc360b70c815bf340ed56c7b8c63aacf11762a4b099b2fe2c9bd6d6068668c08`; flags: none
- Evidence: hf_xet-1.4.3.dist-info/licenses/LICENSE (sha256 c71d239df917…)
- Rationale: Declared 'Apache-2.0; OSI Approved :: Apache Software License'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: hf_xet-1.4.3.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `httpcore-1.0.9-py3-none-any.whl`

- sha256 `2d400746a40668fc9dec9810239072b40b4484b640a8c38fd654a024c7a1bf55`; flags: none
- Evidence: httpcore-1.0.9.dist-info/licenses/LICENSE.md (sha256 fdcb59154c74…)
- Rationale: Declared 'BSD-3-Clause; OSI Approved :: BSD License'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: httpcore-1.0.9.dist-info/licenses/LICENSE.md
- Questions for the reviewer: Confirm, artifact by artifact.

### `httptools-0.7.1-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl`

- sha256 `2c15f37ef679ab9ecc06bfc4e6e8628c32a8e4b305459de7cf6785acd57e4d03`; flags: none
- Evidence: httptools-0.7.1.dist-info/licenses/LICENSE (sha256 f4573e7cb767…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: httptools-0.7.1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `httpx-0.28.1-py3-none-any.whl`

- sha256 `d909fcccc110f8c7faf814ca82a9a4d816bc5a6dbfea25d6591d6985b8ba59ad`; flags: none
- Evidence: httpx-0.28.1.dist-info/licenses/LICENSE.md (sha256 4ec59d544f12…)
- Rationale: Declared 'BSD-3-Clause; OSI Approved :: BSD License'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: httpx-0.28.1.dist-info/licenses/LICENSE.md
- Questions for the reviewer: Confirm, artifact by artifact.

### `httpx_sse-0.4.3-py3-none-any.whl`

- sha256 `0ac1c9fe3c0afad2e0ebb25a934a59f4c7823b60792691f779fad2c5568830fc`; flags: none
- Evidence: httpx_sse-0.4.3.dist-info/licenses/LICENSE (sha256 beec67e4ee83…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: httpx_sse-0.4.3.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `huggingface_hub-0.36.2-py3-none-any.whl`

- sha256 `48f0c8eac16145dfce371e9d2d7772854a4f591bcb56c9cf548accf531d54270`; flags: none
- Evidence: huggingface_hub-0.36.2.dist-info/licenses/LICENSE (sha256 c71d239df917…)
- Rationale: Declared 'Apache; OSI Approved :: Apache Software License'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: huggingface_hub-0.36.2.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `idna-3.13-py3-none-any.whl`

- sha256 `892ea0cde124a99ce773decba204c5552b69c3c67ffd5f232eb7696135bc8bb3`; flags: none
- Evidence: idna-3.13.dist-info/licenses/LICENSE.md (sha256 1a9a4f0e3d47…)
- Rationale: Declared 'BSD-3-Clause'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: idna-3.13.dist-info/licenses/LICENSE.md
- Questions for the reviewer: Confirm, artifact by artifact.

### `ijson-3.5.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl`

- sha256 `7389a56b8562a19948bdf1d7bae3a2edc8c7f86fb59834dcb1c4c722818e645a`; flags: none
- Evidence: ijson-3.5.0.dist-info/licenses/LICENSE.txt (sha256 e5c6f4cfe2d7…)
- Rationale: Declared 'BSD-3-Clause AND ISC'; the wheel's own documents show BSD-3-Clause, ISC, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: ijson-3.5.0.dist-info/licenses/LICENSE.txt
- Questions for the reviewer: Confirm, artifact by artifact.

### `importlib_metadata-8.7.1-py3-none-any.whl`

- sha256 `5a1f80bf1daa489495071efbb095d75a634cf28a8bc299581244063b53176151`; flags: none
- Evidence: importlib_metadata-8.7.1.dist-info/licenses/LICENSE (sha256 458502e12d97…)
- Rationale: Declared 'Apache-2.0'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: importlib_metadata-8.7.1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `interegular-0.3.3-py37-none-any.whl`

- sha256 `b0c07007d48c89d6d19f7204972d369b2a77222722e126b6aa63aa721dc3b19c`; flags: none
- Evidence: interegular-0.3.3.dist-info/LICENSE.txt (sha256 8a23189a1074…)
- Rationale: Declared 'MIT; OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: interegular-0.3.3.dist-info/LICENSE.txt
- Questions for the reviewer: Confirm, artifact by artifact.

### `jinja2-3.1.6-py3-none-any.whl`

- sha256 `85ece4451f492d0c13c5dd7c13a64681a86afae63a5f347908daf103ce6d2f67`; flags: none
- Evidence: jinja2-3.1.6.dist-info/licenses/LICENSE.txt (sha256 3b49dcee4105…)
- Rationale: Declared 'OSI Approved :: BSD License'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal. Additional families in the documents (BSD-3-Clause) are bundled notices to ship too.
- Proposed conditions: ship the bundled licence document(s) unmodified: jinja2-3.1.6.dist-info/licenses/LICENSE.txt
- Questions for the reviewer: Confirm, artifact by artifact.

### `jiter-0.14.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`

- sha256 `c1dcfbeb93d9ecd9ca128bbf8910120367777973fa193fb9a39c31237d8df165`; flags: none
- Evidence: jiter-0.14.0.dist-info/licenses/LICENSE (sha256 7c7134b9f7b9…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: jiter-0.14.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `jmespath-1.1.0-py3-none-any.whl`

- sha256 `a5663118de4908c91729bea0acadca56526eb2698e83de10cd116ae0f4e97c64`; flags: none
- Evidence: jmespath-1.1.0.dist-info/LICENSE (sha256 6eefacfa4d71…)
- Rationale: Declared 'MIT; OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: jmespath-1.1.0.dist-info/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `jsonschema-4.26.0-py3-none-any.whl`

- sha256 `d489f15263b8d200f8387e64b4c3a75f06629559fb73deb8fdfb525f2dab50ce`; flags: none
- Evidence: jsonschema-4.26.0.dist-info/licenses/COPYING (sha256 4f92a015a13c…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: jsonschema-4.26.0.dist-info/licenses/COPYING
- Questions for the reviewer: Confirm, artifact by artifact.

### `jsonschema_specifications-2025.9.1-py3-none-any.whl`

- sha256 `98802fee3a11ee76ecaca44429fda8a41bff98b00a0f2838151b113f210cc6fe`; flags: none
- Evidence: jsonschema_specifications-2025.9.1.dist-info/licenses/COPYING (sha256 42dcd63495f8…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: jsonschema_specifications-2025.9.1.dist-info/licenses/COPYING
- Questions for the reviewer: Confirm, artifact by artifact.

### `lark-1.2.2-py3-none-any.whl`

- sha256 `c2276486b02f0f1b90be155f2c8ba4a8e194d42775786db622faccd652d8e80c`; flags: none
- Evidence: lark-1.2.2.dist-info/LICENSE (sha256 2eee60f52d4e…)
- Rationale: Declared 'MIT; OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: lark-1.2.2.dist-info/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `llguidance-1.3.0-cp39-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`

- sha256 `bc17e9dd602c3879bf91664a64bf72f54c74dbfbeb24ccfab6a5fe435b12f7aa`; flags: none
- Evidence: llguidance-1.3.0.dist-info/licenses/LICENSE (sha256 c2cfccb812fe…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: llguidance-1.3.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `llvmlite-0.44.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`

- sha256 `c0143a5ef336da14deaa8ec26c5449ad5b6a2b564df82fcef4be040b9cacfea9`; flags: none
- Evidence: llvmlite-0.44.0.dist-info/LICENSE (sha256 4b9a7264b011…); llvmlite-0.44.0.dist-info/LICENSE.thirdparty (sha256 dc527293cfc2…)
- Rationale: Declared 'BSD'; the wheel's own documents show BSD-2-Clause, Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal. Additional families in the documents (Apache-2.0, BSD-2-Clause) are bundled notices to ship too.
- Proposed conditions: ship the bundled licence document(s) unmodified: llvmlite-0.44.0.dist-info/LICENSE, llvmlite-0.44.0.dist-info/LICENSE.thirdparty
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `lm_format_enforcer-0.11.3-py3-none-any.whl`

- sha256 `cf586350875def1ae7a8fba84fcbbfc8371424b6c9d05c1fcba70aa233fbf06f`; flags: none
- Evidence: lm_format_enforcer-0.11.3.dist-info/LICENSE (sha256 d1c02373f9da…)
- Rationale: Declared 'MIT; OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: lm_format_enforcer-0.11.3.dist-info/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `markdown_it_py-4.0.0-py3-none-any.whl`

- sha256 `87327c59b172c5011896038353a81343b6754500a08cd7a4973bb48c6d578147`; flags: none
- Evidence: markdown_it_py-4.0.0.dist-info/licenses/LICENSE (sha256 4a2260d6e2cd…); markdown_it_py-4.0.0.dist-info/licenses/LICENSE.markdown-it (sha256 792c48c5a849…)
- Rationale: Declared 'OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: markdown_it_py-4.0.0.dist-info/licenses/LICENSE, markdown_it_py-4.0.0.dist-info/licenses/LICENSE.markdown-it
- Questions for the reviewer: Confirm, artifact by artifact.

### `markupsafe-3.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl`

- sha256 `d6dd0be5b5b189d31db7cda48b91d7e0a9795f31430b7f271219ab30f1d3ac9d`; flags: none
- Evidence: markupsafe-3.0.3.dist-info/licenses/LICENSE.txt (sha256 489a8e110850…)
- Rationale: Declared 'BSD-3-Clause'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: markupsafe-3.0.3.dist-info/licenses/LICENSE.txt
- Questions for the reviewer: Confirm, artifact by artifact.

### `mcp-1.27.0-py3-none-any.whl`

- sha256 `5ce1fa81614958e267b21fb2aa34e0aea8e2c6ede60d52aba45fd47246b4d741`; flags: none
- Evidence: mcp-1.27.0.dist-info/licenses/LICENSE (sha256 5e13dbbc1d12…)
- Rationale: Declared 'MIT; OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: mcp-1.27.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `mdurl-0.1.2-py3-none-any.whl`

- sha256 `84008a41e51615a49fc9966191ff91509e3c40b939176e643fd50a5c2196b8f8`; flags: none
- Evidence: mdurl-0.1.2.dist-info/LICENSE (sha256 7c605df6e286…)
- Rationale: Declared 'OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: mdurl-0.1.2.dist-info/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `mpmath-1.3.0-py3-none-any.whl`

- sha256 `a0b2b9fe80bbcd81a6647ff13108738cfb482d481d826cc0e02f5b35e5c88d2c`; flags: none
- Evidence: mpmath-1.3.0.dist-info/LICENSE (sha256 c26cae81da45…)
- Rationale: Declared 'BSD; OSI Approved :: BSD License'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal. Additional families in the documents (BSD-3-Clause) are bundled notices to ship too.
- Proposed conditions: ship the bundled licence document(s) unmodified: mpmath-1.3.0.dist-info/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `msgspec-0.21.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl`

- sha256 `21995e74b5c598c2e004110ad66ec7f1b8c20bf2bcf3b2de8fd9a3094422d3ff`; flags: none
- Evidence: msgspec-0.21.1.dist-info/licenses/LICENSE (sha256 6fde8b672388…)
- Rationale: Declared 'BSD-3-Clause'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: msgspec-0.21.1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `multidict-6.7.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl`

- sha256 `bfde23ef6ed9db7eaee6c37dcec08524cb43903c60b285b172b6c094711b3961`; flags: none
- Evidence: multidict-6.7.1.dist-info/licenses/LICENSE (sha256 93d11a968e2f…)
- Rationale: Declared 'Apache License 2.0'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: multidict-6.7.1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `networkx-3.6.1-py3-none-any.whl`

- sha256 `d47fbf302e7d9cbbb9e2555a0d267983d2aa476bac30e90dfbe5669bd57f3762`; flags: none
- Evidence: networkx-3.6.1.dist-info/licenses/LICENSE.txt (sha256 3cf7c3a179d8…)
- Rationale: Declared 'BSD-3-Clause'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: networkx-3.6.1.dist-info/licenses/LICENSE.txt
- Questions for the reviewer: Confirm, artifact by artifact.

### `openai-2.33.0-py3-none-any.whl`

- sha256 `03ac37d70e8c9e3a8124214e3afa785e2cbc12e627fbd98177a086ef2fd87ad5`; flags: none
- Evidence: openai-2.33.0.dist-info/licenses/LICENSE (sha256 636eb7d79da9…)
- Rationale: Declared 'Apache-2.0; OSI Approved :: Apache Software License'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: openai-2.33.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `opentelemetry_api-1.41.1-py3-none-any.whl`

- sha256 `a22df900e75c76dc08440710e51f52f1aa6b451b429298896023e60db5b3139f`; flags: none
- Evidence: opentelemetry_api-1.41.1.dist-info/licenses/LICENSE (sha256 c71d239df917…)
- Rationale: Declared 'Apache-2.0'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: opentelemetry_api-1.41.1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `opentelemetry_exporter_otlp-1.41.1-py3-none-any.whl`

- sha256 `db276c5a80c02b063994e80950d00ca1bfddcf6520f608335b7dc2db0c0eb9c6`; flags: none
- Evidence: opentelemetry_exporter_otlp-1.41.1.dist-info/licenses/LICENSE (sha256 c71d239df917…)
- Rationale: Declared 'Apache-2.0'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: opentelemetry_exporter_otlp-1.41.1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `opentelemetry_exporter_otlp_proto_common-1.41.1-py3-none-any.whl`

- sha256 `10da74dad6a49344b9b7b21b6182e3060373a235fde1528616d5f01f92e66aa9`; flags: none
- Evidence: opentelemetry_exporter_otlp_proto_common-1.41.1.dist-info/licenses/LICENSE (sha256 c71d239df917…)
- Rationale: Declared 'Apache-2.0'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: opentelemetry_exporter_otlp_proto_common-1.41.1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `opentelemetry_exporter_otlp_proto_grpc-1.41.1-py3-none-any.whl`

- sha256 `537926dcef951136992479af1d9cd88f25e33d56c530e9f020ed57774dca2f94`; flags: none
- Evidence: opentelemetry_exporter_otlp_proto_grpc-1.41.1.dist-info/licenses/LICENSE (sha256 c71d239df917…)
- Rationale: Declared 'Apache-2.0'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: opentelemetry_exporter_otlp_proto_grpc-1.41.1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `opentelemetry_exporter_otlp_proto_http-1.41.1-py3-none-any.whl`

- sha256 `1a21e8f49c7a946d935551e90947d6c3eb39236723c6624401da0f33d68edcb4`; flags: none
- Evidence: opentelemetry_exporter_otlp_proto_http-1.41.1.dist-info/licenses/LICENSE (sha256 c71d239df917…)
- Rationale: Declared 'Apache-2.0'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: opentelemetry_exporter_otlp_proto_http-1.41.1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `opentelemetry_proto-1.41.1-py3-none-any.whl`

- sha256 `0496713b804d127a4147e32849fbaf5683fac8ee98550e8e7679cd706c289720`; flags: none
- Evidence: opentelemetry_proto-1.41.1.dist-info/licenses/LICENSE (sha256 c71d239df917…)
- Rationale: Declared 'Apache-2.0'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: opentelemetry_proto-1.41.1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `opentelemetry_sdk-1.41.1-py3-none-any.whl`

- sha256 `edee379c126c1bce952b0c812b48fe8ff35b30df0eecf17e98afa4d598b7d85d`; flags: none
- Evidence: opentelemetry_sdk-1.41.1.dist-info/licenses/LICENSE (sha256 c71d239df917…)
- Rationale: Declared 'Apache-2.0'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: opentelemetry_sdk-1.41.1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `opentelemetry_semantic_conventions-0.62b1-py3-none-any.whl`

- sha256 `cf506938103d331fbb78eded0d9788095f7fd59016f2bda813c3324e5a74a93c`; flags: none
- Evidence: opentelemetry_semantic_conventions-0.62b1.dist-info/licenses/LICENSE (sha256 c71d239df917…)
- Rationale: Declared 'Apache-2.0'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: opentelemetry_semantic_conventions-0.62b1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `outlines_core-0.2.11-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`

- sha256 `86df9740368866295077346440d911df4972da2b3f1f54b8125e6f329e8a8891`; flags: none
- Evidence: outlines_core-0.2.11.dist-info/licenses/LICENSE (sha256 f71078ee8aaa…)
- Rationale: Declared 'Apache-2.0'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: outlines_core-0.2.11.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `packaging-26.2-py3-none-any.whl`

- sha256 `5fc45236b9446107ff2415ce77c807cee2862cb6fac22b8a73826d0693b0980e`; flags: none
- Evidence: packaging-26.2.dist-info/licenses/LICENSE (sha256 cad1ef5bd340…); packaging-26.2.dist-info/licenses/LICENSE.APACHE (sha256 0d542e0c8804…); packaging-26.2.dist-info/licenses/LICENSE.BSD (sha256 b70e7e9b742f…)
- Rationale: Declared 'Apache-2.0 OR BSD-2-Clause'; the wheel's own documents show Apache-2.0, BSD-2-Clause, consistent with the declaration (OR: a choice of licence). Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: packaging-26.2.dist-info/licenses/LICENSE, packaging-26.2.dist-info/licenses/LICENSE.APACHE, packaging-26.2.dist-info/licenses/LICENSE.BSD
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `partial_json_parser-0.2.1.1.post7-py3-none-any.whl`

- sha256 `145119e5eabcf80cbb13844a6b50a85c68bf99d376f8ed771e2a3c3b03e653ae`; flags: none
- Evidence: partial_json_parser-0.2.1.1.post7.dist-info/licenses/LICENSE (sha256 f2ca3ffaa3b6…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: partial_json_parser-0.2.1.1.post7.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `prometheus_fastapi_instrumentator-7.1.0-py3-none-any.whl`

- sha256 `978130f3c0bb7b8ebcc90d35516a6fe13e02d2eb358c8f83887cdef7020c31e9`; flags: none
- Evidence: prometheus_fastapi_instrumentator-7.1.0.dist-info/LICENSE (sha256 d416f8eb35fa…)
- Rationale: Declared 'ISC; OSI Approved'; the wheel's own documents show ISC, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: prometheus_fastapi_instrumentator-7.1.0.dist-info/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `propcache-0.4.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl`

- sha256 `15932ab57837c3368b024473a525e25d316d8353016e7cc0e5ba9eb343fbb1cf`; flags: none
- Evidence: propcache-0.4.1.dist-info/licenses/LICENSE (sha256 cfc7749b96f6…); propcache-0.4.1.dist-info/licenses/NOTICE (sha256 56d6ac6c8105…)
- Rationale: Declared 'Apache-2.0; OSI Approved :: Apache Software License'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: propcache-0.4.1.dist-info/licenses/LICENSE, propcache-0.4.1.dist-info/licenses/NOTICE; keep the NOTICE file (Apache-2.0 4(d))
- Questions for the reviewer: Confirm, artifact by artifact.

### `protobuf-6.33.6-cp39-abi3-manylinux2014_x86_64.whl`

- sha256 `e9db7e292e0ab79dd108d7f1a94fe31601ce1ee3f7b79e0692043423020b0593`; flags: none
- Evidence: protobuf-6.33.6.dist-info/LICENSE (sha256 6e5e117324af…)
- Rationale: Declared '3-Clause BSD License'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: protobuf-6.33.6.dist-info/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `psutil-7.2.2-cp36-abi3-manylinux2010_x86_64.manylinux_2_12_x86_64.manylinux_2_28_x86_64.whl`

- sha256 `076a2d2f923fd4821644f5ba89f059523da90dc9014e85f8e45a5774ca5bc6f9`; flags: none
- Evidence: psutil-7.2.2.dist-info/LICENSE (sha256 b89c063b3786…)
- Rationale: Declared 'BSD-3-Clause'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: psutil-7.2.2.dist-info/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `py_cpuinfo-9.0.0-py3-none-any.whl`

- sha256 `859625bc251f64e21f077d099d4162689c762b5d6a4c3c97553d56241c9674d5`; flags: none
- Evidence: py_cpuinfo-9.0.0.dist-info/LICENSE (sha256 ddbaf76396bf…)
- Rationale: Declared 'MIT; OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: py_cpuinfo-9.0.0.dist-info/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `pybase64-1.4.3-cp312-cp312-manylinux1_x86_64.manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_5_x86_64.whl`

- sha256 `bb632edfd132b3eaf90c39c89aa314beec4e946e210099b57d40311f704e11d4`; flags: none
- Evidence: pybase64/_license.py (sha256 2eedefd4eddb…); pybase64/_license.pyi (sha256 693a7066a509…); pybase64-1.4.3.dist-info/licenses/LICENSE (sha256 5e523b54c158…)
- Rationale: Declared 'BSD-2-Clause; OSI Approved :: BSD License'; the wheel's own documents show BSD-2-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: pybase64/_license.py, pybase64/_license.pyi, pybase64-1.4.3.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `pycparser-3.0-py3-none-any.whl`

- sha256 `b727414169a36b7d524c1c3e31839a521725078d7b2ff038656844266160a992`; flags: none
- Evidence: pycparser-3.0.dist-info/licenses/LICENSE (sha256 0c846399369e…)
- Rationale: Declared 'BSD-3-Clause'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: pycparser-3.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `pydantic-2.13.3-py3-none-any.whl`

- sha256 `6db14ac8dfc9a1e57f87ea2c0de670c251240f43cb0c30a5130e9720dc612927`; flags: none
- Evidence: pydantic-2.13.3.dist-info/licenses/LICENSE (sha256 a9e186f3ca16…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: pydantic-2.13.3.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `pydantic_core-2.46.3-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`

- sha256 `fb528e295ed31570ac3dcc9bfdd6e0150bc11ce6168ac87a8082055cf1a67395`; flags: none
- Evidence: pydantic_core-2.46.3.dist-info/licenses/LICENSE (sha256 2afdd30d54b4…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: pydantic_core-2.46.3.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `pydantic_extra_types-2.11.1-py3-none-any.whl`

- sha256 `1722ea2bddae5628ace25f2aa685b69978ef533123e5638cfbddb999e0100ec1`; flags: none
- Evidence: pydantic_extra_types-2.11.1.dist-info/licenses/LICENSE (sha256 a09bbbbb46be…)
- Rationale: Declared 'MIT; OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: pydantic_extra_types-2.11.1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `pydantic_settings-2.14.0-py3-none-any.whl`

- sha256 `fc8d5d692eb7092e43c8647c1c35a3ecd00e040fcf02ed86f4cb5458ca62182e`; flags: none
- Evidence: pydantic_settings-2.14.0.dist-info/licenses/LICENSE (sha256 eb355a753e02…)
- Rationale: Declared 'MIT; OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: pydantic_settings-2.14.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `pygments-2.20.0-py3-none-any.whl`

- sha256 `81a9e26dd42fd28a23a2d169d86d7ac03b46e2f8b59ed4698fb4785f946d0176`; flags: none
- Evidence: pygments-2.20.0.dist-info/licenses/AUTHORS (sha256 0db603a5f449…); pygments-2.20.0.dist-info/licenses/LICENSE (sha256 a9d66f1d526d…)
- Rationale: Declared 'BSD-2-Clause'; the wheel's own documents show BSD-2-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: pygments-2.20.0.dist-info/licenses/AUTHORS, pygments-2.20.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `pyjwt-2.12.1-py3-none-any.whl`

- sha256 `28ca37c070cad8ba8cd9790cd940535d40274d22f80ab87f3ac6a713e6e8454c`; flags: none
- Evidence: pyjwt-2.12.1.dist-info/licenses/AUTHORS.rst (sha256 925ce4346102…); pyjwt-2.12.1.dist-info/licenses/LICENSE (sha256 797a7a20231d…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: pyjwt-2.12.1.dist-info/licenses/AUTHORS.rst, pyjwt-2.12.1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `python_dotenv-1.2.2-py3-none-any.whl`

- sha256 `1d8214789a24de455a8b8bd8ae6fe3c6b69a5e3d64aa8a8e5d68e694bbcb285a`; flags: none
- Evidence: python_dotenv-1.2.2.dist-info/licenses/LICENSE (sha256 80619b7049f0…)
- Rationale: Declared 'BSD-3-Clause'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: python_dotenv-1.2.2.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `python_json_logger-4.1.0-py3-none-any.whl`

- sha256 `132994765cf75bf44554be9aa49b06ef2345d23661a96720262716438141b6b2`; flags: none
- Evidence: python_json_logger-4.1.0.dist-info/licenses/LICENSE (sha256 18ea95179e3a…)
- Rationale: Declared 'BSD-2-Clause'; the wheel's own documents show BSD-2-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: python_json_logger-4.1.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `python_multipart-0.0.27-py3-none-any.whl`

- sha256 `6fccfad17a27334bd0193681b369f476eda3409f17381a2d65aa7df3f7275645`; flags: none
- Evidence: python_multipart-0.0.27.dist-info/licenses/LICENSE.txt (sha256 cfc7749b96f6…)
- Rationale: Declared 'Apache-2.0; OSI Approved :: Apache Software License'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: python_multipart-0.0.27.dist-info/licenses/LICENSE.txt
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl`

- sha256 `ba1cc08a7ccde2d2ec775841541641e4548226580ab850948cbfda66a1befcdc`; flags: none
- Evidence: pyyaml-6.0.3.dist-info/licenses/LICENSE (sha256 8d3928f9dc44…)
- Rationale: Declared 'MIT; OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: pyyaml-6.0.3.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `referencing-0.37.0-py3-none-any.whl`

- sha256 `381329a9f99628c9069361716891d34ad94af76e461dcb0335825aecc7692231`; flags: none
- Evidence: referencing-0.37.0.dist-info/licenses/COPYING (sha256 42dcd63495f8…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: referencing-0.37.0.dist-info/licenses/COPYING
- Questions for the reviewer: Confirm, artifact by artifact.

### `requests-2.33.1-py3-none-any.whl`

- sha256 `4e6d1ef462f3626a1f0a0a9c42dd93c63bad33f9f1c1937509b8c5c8718ab56a`; flags: none
- Evidence: requests-2.33.1.dist-info/licenses/LICENSE (sha256 09e8a9bcec80…); requests-2.33.1.dist-info/licenses/NOTICE (sha256 f5110972deda…)
- Rationale: Declared 'Apache-2.0; OSI Approved :: Apache Software License'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: requests-2.33.1.dist-info/licenses/LICENSE, requests-2.33.1.dist-info/licenses/NOTICE; keep the NOTICE file (Apache-2.0 4(d))
- Questions for the reviewer: Confirm, artifact by artifact.

### `rich-15.0.0-py3-none-any.whl`

- sha256 `33bd4ef74232fb73fe9279a257718407f169c09b78a87ad3d296f548e27de0bb`; flags: none
- Evidence: rich-15.0.0.dist-info/licenses/LICENSE (sha256 deed7c17a431…)
- Rationale: Declared 'MIT; OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: rich-15.0.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `rich_toolkit-0.19.7-py3-none-any.whl`

- sha256 `0288e9203728c47c5a4eb60fd2f0692d9df7455a65901ab6f898437a2ba5989d`; flags: none
- Evidence: rich_toolkit-0.19.7.dist-info/licenses/LICENSE (sha256 71579251fc27…); rich_toolkit-0.19.7.dist-info/licenses/LICENSE-THIRD-PARTY (sha256 512631a0a7f2…)
- Rationale: Declared 'MIT; OSI Approved :: MIT License'; the wheel's own documents show MIT, BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal. Additional families in the documents (BSD-3-Clause) are bundled notices to ship too.
- Proposed conditions: ship the bundled licence document(s) unmodified: rich_toolkit-0.19.7.dist-info/licenses/LICENSE, rich_toolkit-0.19.7.dist-info/licenses/LICENSE-THIRD-PARTY
- Questions for the reviewer: Confirm, artifact by artifact.

### `rignore-0.7.6-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`

- sha256 `d24321efac92140b7ec910ac7c53ab0f0c86a41133d2bb4b0e6a7c94967f44dd`; flags: none
- Evidence: rignore-0.7.6.dist-info/licenses/LICENSE (sha256 71579251fc27…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: rignore-0.7.6.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `rpds_py-0.30.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`

- sha256 `47f236970bccb2233267d89173d3ad2703cd36a0e2a6e92d0560d333871a3d23`; flags: none
- Evidence: rpds_py-0.30.0.dist-info/licenses/LICENSE (sha256 314e4e91be3b…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: rpds_py-0.30.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `safetensors-0.7.0-cp38-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`

- sha256 `dac7252938f0696ddea46f5e855dd3138444e82236e3be475f54929f0c510d48`; flags: none
- Evidence: safetensors-0.7.0.dist-info/licenses/LICENSE (sha256 c71d239df917…)
- Rationale: Declared 'OSI Approved :: Apache Software License'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: safetensors-0.7.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `sentry_sdk-2.58.0-py2.py3-none-any.whl`

- sha256 `688d1c704ddecf382ea3326f21a67453d4caa95592d722b7c780a36a9d23109e`; flags: none
- Evidence: sentry_sdk-2.58.0.dist-info/licenses/LICENSE (sha256 2a140d660f46…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: sentry_sdk-2.58.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `setproctitle-1.3.7-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl`

- sha256 `2906b6c7959cdb75f46159bf0acd8cc9906cf1361c9e1ded0d065fe8f9039629`; flags: none
- Evidence: setproctitle-1.3.7.dist-info/licenses/LICENSE (sha256 4bb8a954b088…)
- Rationale: Declared 'BSD-3-Clause; OSI Approved :: BSD License'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: setproctitle-1.3.7.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `six-1.17.0-py2.py3-none-any.whl`

- sha256 `4721f391ed90541fddacab5acf947aa0d3dc7d27b2e1e8eda2be8970586c3274`; flags: none
- Evidence: six-1.17.0.dist-info/LICENSE (sha256 4375ba20e2b9…)
- Rationale: Declared 'MIT; OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: six-1.17.0.dist-info/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `sniffio-1.3.1-py3-none-any.whl`

- sha256 `2f6da418d1f1e0fddd844478f41680e794e6051915791a034ff65e5f100525a2`; flags: none
- Evidence: sniffio-1.3.1.dist-info/LICENSE (sha256 652c878488d1…); sniffio-1.3.1.dist-info/LICENSE.APACHE2 (sha256 cfc7749b96f6…); sniffio-1.3.1.dist-info/LICENSE.MIT (sha256 3e6dae555eb9…)
- Rationale: Declared 'MIT OR Apache-2.0; OSI Approved :: MIT License; OSI Approved :: Apache Software License'; the wheel's own documents show Apache-2.0, MIT, consistent with the declaration (OR: a choice of licence). Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: sniffio-1.3.1.dist-info/LICENSE, sniffio-1.3.1.dist-info/LICENSE.APACHE2, sniffio-1.3.1.dist-info/LICENSE.MIT
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `sse_starlette-3.4.1-py3-none-any.whl`

- sha256 `6b43cf21f1d574d582a6e1b0cfbde1c94dc86a32a701a7168c99c4475c6bd1d0`; flags: none
- Evidence: sse_starlette-3.4.1.dist-info/licenses/AUTHORS (sha256 c2ff63d2ecf1…); sse_starlette-3.4.1.dist-info/licenses/LICENSE (sha256 80af6bfccbeb…)
- Rationale: Declared 'BSD-3-Clause'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: sse_starlette-3.4.1.dist-info/licenses/AUTHORS, sse_starlette-3.4.1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `starlette-0.52.1-py3-none-any.whl`

- sha256 `0029d43eb3d273bc4f83a08720b4912ea4b071087a3b48db01b7c839f7954d74`; flags: none
- Evidence: starlette-0.52.1.dist-info/licenses/LICENSE.md (sha256 dcb95677a022…)
- Rationale: Declared 'BSD-3-Clause'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: starlette-0.52.1.dist-info/licenses/LICENSE.md
- Questions for the reviewer: Confirm, artifact by artifact.

### `sympy-1.14.0-py3-none-any.whl`

- sha256 `e091cc3e99d2141a0ba2847328f5479b05d94a6635cb96148ccb3f34671bd8f5`; flags: none
- Evidence: sympy/parsing/latex/LICENSE.txt (sha256 007bc30a58fa…); sympy-1.14.0.dist-info/licenses/AUTHORS (sha256 82b1038521b0…); sympy-1.14.0.dist-info/licenses/LICENSE (sha256 07a5e9819f72…)
- Rationale: Declared 'BSD; New BSD License (see the [LICENSE](LICENSE) file for details) covers all; OSI Approved :: BSD License'; the wheel's own documents show MIT, BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal. Additional families in the documents (MIT) are bundled notices to ship too.
- Proposed conditions: ship the bundled licence document(s) unmodified: sympy/parsing/latex/LICENSE.txt, sympy-1.14.0.dist-info/licenses/AUTHORS, sympy-1.14.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `tabulate-0.10.0-py3-none-any.whl`

- sha256 `f0b0622e567335c8fabaaa659f1b33bcb6ddfe2e496071b743aa113f8774f2d3`; flags: none
- Evidence: tabulate-0.10.0.dist-info/licenses/LICENSE (sha256 cdfab50d37d8…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: tabulate-0.10.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `tiktoken-0.12.0-cp312-cp312-manylinux_2_28_x86_64.whl`

- sha256 `edde1ec917dfd21c1f2f8046b86348b0f54a2c0547f68149d8600859598769ad`; flags: none
- Evidence: tiktoken-0.12.0.dist-info/licenses/LICENSE (sha256 418cb499b436…)
- Rationale: Declared 'MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: tiktoken-0.12.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `torch_c_dlpack_ext-0.1.5-cp312-cp312-manylinux_2_24_x86_64.manylinux_2_28_x86_64.whl`

- sha256 `e6f9da4bb9af70e27facc777458be62e10dbbbddda7672d16138db0553c5a524`; flags: none
- Evidence: torch_c_dlpack_ext-0.1.5.dist-info/licenses/LICENSE (sha256 b40930bbcf80…); torch_c_dlpack_ext-0.1.5.dist-info/licenses/NOTICE (sha256 f3b4f47f4a9c…)
- Rationale: Declared 'Apache License; OSI Approved :: Apache Software License'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: torch_c_dlpack_ext-0.1.5.dist-info/licenses/LICENSE, torch_c_dlpack_ext-0.1.5.dist-info/licenses/NOTICE; keep the NOTICE file (Apache-2.0 4(d))
- Questions for the reviewer: Confirm, artifact by artifact.

### `torchaudio-2.10.0-cp312-cp312-manylinux_2_28_x86_64.whl`

- sha256 `0e77b2956448d63790a99beed0b74ac8b8cd3a94dcdd9ad01974411078f46278`; flags: none
- Evidence: torchaudio-2.10.0.dist-info/licenses/LICENSE (sha256 93a58861a858…)
- Rationale: Declared 'OSI Approved :: BSD License'; the wheel's own documents show BSD-2-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal. Additional families in the documents (BSD-2-Clause) are bundled notices to ship too.
- Proposed conditions: ship the bundled licence document(s) unmodified: torchaudio-2.10.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `torchvision-0.25.0-cp312-cp312-manylinux_2_28_x86_64.whl`

- sha256 `f25aa9e380865b11ea6e9d99d84df86b9cc959f1a007cd966fc6f1ab2ed0e248`; flags: none
- Evidence: torchvision-0.25.0.dist-info/LICENSE (sha256 6502f676851c…)
- Rationale: Declared 'BSD'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal. Additional families in the documents (BSD-3-Clause) are bundled notices to ship too.
- Proposed conditions: ship the bundled licence document(s) unmodified: torchvision-0.25.0.dist-info/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `transformers-4.57.6-py3-none-any.whl`

- sha256 `4c9e9de11333ddfe5114bc872c9f370509198acf0b87a832a0ab9458e2bd0550`; flags: none
- Evidence: transformers-4.57.6.dist-info/licenses/LICENSE (sha256 77fd4710def9…)
- Rationale: Declared 'Apache 2.0 License; OSI Approved :: Apache Software License'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: transformers-4.57.6.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `triton-3.6.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`

- sha256 `74caf5e34b66d9f3a429af689c1c7128daba1d8208df60e81106b115c00d6fca`; flags: none
- Evidence: triton-3.6.0.dist-info/licenses/LICENSE (sha256 92640fb97222…)
- Rationale: Declared 'OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: triton-3.6.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `typer-0.25.1-py3-none-any.whl`

- sha256 `75caa44ed46a03fb2dab8808753ffacdbfea88495e74c85a28c5eefcf5f39c89`; flags: none
- Evidence: typer-0.25.1.dist-info/licenses/LICENSE (sha256 58992cebcf8d…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: typer-0.25.1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `typing_inspection-0.4.2-py3-none-any.whl`

- sha256 `4ed1cacbdc298c220f1bd249ed5287caa16f34d44ef4e9c3d0cbad5b521545e7`; flags: none
- Evidence: typing_inspection-0.4.2.dist-info/licenses/LICENSE (sha256 804b59b25f2c…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: typing_inspection-0.4.2.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `urllib3-2.6.3-py3-none-any.whl`

- sha256 `bf272323e553dfb2e87d9bfd225ca7b0f467b919d7bbd355436d3fd37cb0acd4`; flags: none
- Evidence: urllib3-2.6.3.dist-info/licenses/LICENSE.txt (sha256 130e3a64d5fd…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: urllib3-2.6.3.dist-info/licenses/LICENSE.txt
- Questions for the reviewer: Confirm, artifact by artifact.

### `uvicorn-0.46.0-py3-none-any.whl`

- sha256 `bbebbcbed972d162afca128605223022bedd345b7bc7855ce66deb31487a9048`; flags: none
- Evidence: uvicorn-0.46.0.dist-info/licenses/LICENSE.md (sha256 efe1acf3e62f…)
- Rationale: Declared 'BSD-3-Clause'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: uvicorn-0.46.0.dist-info/licenses/LICENSE.md
- Questions for the reviewer: Confirm, artifact by artifact.

### `uvloop-0.22.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl`

- sha256 `7b5b1ac819a3f946d3b2ee07f09149578ae76066d70b44df3fa990add49a82e4`; flags: none
- Evidence: uvloop-0.22.1.dist-info/licenses/LICENSE-APACHE (sha256 377025287798…); uvloop-0.22.1.dist-info/licenses/LICENSE-MIT (sha256 6dd4c399f26d…)
- Rationale: Declared 'MIT License; OSI Approved :: Apache Software License; OSI Approved :: MIT License'; the wheel's own documents show Apache-2.0, MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: uvloop-0.22.1.dist-info/licenses/LICENSE-APACHE, uvloop-0.22.1.dist-info/licenses/LICENSE-MIT
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `vllm-0.19.0-cp38-abi3-manylinux_2_31_x86_64.whl`

- sha256 `2d0e5fae45367bdbf111fcad68f4c0f8fdddd2f2fb643e52f0f2daebef7b41cf`; flags: none
- Evidence: vllm-0.19.0.dist-info/licenses/LICENSE (sha256 c71d239df917…)
- Rationale: Declared 'Apache-2.0'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: vllm-0.19.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact. Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it (4(d) concerns NOTICE files that are part of the Work as distributed).

### `watchfiles-1.1.1-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`

- sha256 `1db5d7ae38ff20153d542460752ff397fcf5c96090c1230803713cf3147a6803`; flags: none
- Evidence: watchfiles-1.1.1.dist-info/licenses/LICENSE (sha256 4fd78355b67c…)
- Rationale: Declared 'MIT; OSI Approved :: MIT License'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: watchfiles-1.1.1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `websockets-16.0-cp312-cp312-manylinux1_x86_64.manylinux_2_28_x86_64.manylinux_2_5_x86_64.whl`

- sha256 `9b5aca38b67492ef518a8ab76851862488a478602229112c4b0d58d63a7a4d5c`; flags: none
- Evidence: websockets-16.0.dist-info/licenses/LICENSE (sha256 3d6a0c050d8b…)
- Rationale: Declared 'BSD-3-Clause'; the wheel's own documents show BSD-3-Clause, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: websockets-16.0.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.

### `xgrammar-0.1.34-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`

- sha256 `cc7abf6b323b7f5ac566bdfdb8889dfa45288ba000820e6c0cf048598d8899d9`; flags: none
- Evidence: xgrammar-0.1.34.dist-info/licenses/LICENSE (sha256 c71d239df917…); xgrammar-0.1.34.dist-info/licenses/NOTICE (sha256 769c6907073c…)
- Rationale: Declared 'Apache 2.0; OSI Approved :: Apache Software License'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: xgrammar-0.1.34.dist-info/licenses/LICENSE, xgrammar-0.1.34.dist-info/licenses/NOTICE; keep the NOTICE file (Apache-2.0 4(d))
- Questions for the reviewer: Confirm, artifact by artifact.

### `yarl-1.23.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl`

- sha256 `a3d2bff8f37f8d0f96c7ec554d16945050d54462d6e95414babaa18bfafc7f51`; flags: none
- Evidence: yarl-1.23.0.dist-info/licenses/LICENSE (sha256 cfc7749b96f6…); yarl-1.23.0.dist-info/licenses/NOTICE (sha256 56d6ac6c8105…)
- Rationale: Declared 'Apache-2.0'; the wheel's own documents show Apache-2.0, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: yarl-1.23.0.dist-info/licenses/LICENSE, yarl-1.23.0.dist-info/licenses/NOTICE; keep the NOTICE file (Apache-2.0 4(d))
- Questions for the reviewer: Confirm, artifact by artifact.

### `zipp-3.23.1-py3-none-any.whl`

- sha256 `0b3596c50a5c700c9cb40ba8d86d9f2cc4807e9bedb06bcdf7fac85633e444dc`; flags: none
- Evidence: zipp-3.23.1.dist-info/licenses/LICENSE (sha256 9755a1851966…)
- Rationale: Declared 'MIT'; the wheel's own documents show MIT, consistent with the declaration. Permissive; no copyleft or proprietary signal.
- Proposed conditions: ship the bundled licence document(s) unmodified: zipp-3.23.1.dist-info/licenses/LICENSE
- Questions for the reviewer: Confirm, artifact by artifact.
