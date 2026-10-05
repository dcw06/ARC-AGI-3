# NVIDIA deployment assessment (shared) with product-specific findings

**A proposal for the designated reviewer, not a decision.** Private visibility is not redistribution clearance.

Scope: 13 rows. an earlier note said 14 rows; the correct count is 13 (11 CUDA-EULA wheels including NVSHMEM, plus cuDNN and cuSPARSELt).

Excluded from this shared assessment:

- cuda_python, cuda_bindings: own NVIDIA Software License without the application requirements; reviewed separately
- nvidia_cutlass_dsl, nvidia_cutlass_dsl_libs_base: own EULA; see cutlass_binaries pack
- nvidia_nccl_cu12, nvidia_nvtx_cu12, nvidia_cudnn_frontend: permissive licence texts under a proprietary classifier; reviewed separately

## Deployment facts recorded in the repository (to revalidate)

| Fact | Source |
|---|---|
| Notebooks are created and pushed under the Kaggle account daichongwei06 | kernel ids in notebooks/*/kernel-metadata.json; docs/Team_Environment_and_Credentials_Guide_ZH.md |
| The proposed R2 dataset is private, named arc3-vllm-0.19.0-cu128-wheelhouse-r2 (not yet confirmed or created) | reports/wheelhouse_r2_approval_artifacts.md (Record B draft) |
| Runtime use: the wheels are installed offline into a fresh virtual environment inside the team's Kaggle notebook and loaded by vLLM/torch serving the pinned Qwen3-VL model for the ARC-AGI-3 agent; internet is disabled | certification/wheelhouse_r2_smoke_v1/protocol.json; docs/ARC-AGI-3_Final_Project_Plan.md |
| Maximum team size 8; identity verification required | docs/ARC-AGI-3_Final_Project_Plan.md (competition constraints table; to revalidate) |
| Milestone and prize eligibility require a public notebook and open-source materials with compatible licences; the stated winner licence is CC BY 4.0 plus open-system/model/weights obligations | docs/ARC-AGI-3_Final_Project_Plan.md (sections on milestone release and constraints; to revalidate) |

## Owner inputs required (not recorded; not assumed)

1. Which Kaggle account will own the R2 dataset (personal account of a team member, or another team-controlled account)?
2. Who will be granted access (named collaborators and their roles: team members, contractors, others)?
3. Access controls: dataset visibility, collaborator permissions (view/edit), and whether any notebook that attaches it will ever be made public or shared
4. Whether the dataset or any notebook attaching it is intended to be published for milestone or prize eligibility, and if so whether the NVIDIA wheels would be part of the published materials
5. Whether the team or its members hold any separate agreement with NVIDIA covering these components

## Licence requirements against the deployment

Phase A: private development: a private dataset attached to the team's own notebooks. Phase B: publication for milestone or prize eligibility, if pursued.

| Requirement | What the assessment depends on |
|---|---|
| Distribution only of portions identified as distributable (Attachment A / the SLA's distribution clause) | Product-specific: see file coverage below. |
| Incorporated into a software application with material additional functionality | Phase A (private development): the wheels are installed into an environment and loaded by vLLM/torch for the agent. Whether a wheelhouse dataset attached to the notebook is "incorporated into" that application, or a separate stand-alone copy of the SDK components, is the central open question. Phase B (publication): publishing the wheelhouse would be distribution to the public. |
| The distributable portions are accessed only by the application | Phase A: anyone with dataset access could download the wheels directly, outside the application. Recipients and access controls (owner inputs) are material. |
| No distribution of the SDK as a stand-alone product | A wheelhouse that also contains the unmodified NVIDIA wheels is not itself an application; whether attaching it to the team's notebook avoids stand-alone distribution needs the reviewer's assessment. |
| Authorized users: employees and contractors (internal access, secure network) | Depends on who the collaborators are (owner input) and whether Kaggle hosting counts as the team's secure network. |
| Linux portions may be redistributed unmodified (CUDA EULA 2.3); unmodified object files | The wheels are byte-identical to PyPI; nothing is modified. |
| Terms of the application's distribution consistent with the agreement; notices retained | Phase B: open-source publication terms (the competition's open-source requirements) may conflict with the proprietary terms; this is a Release Owner question as well as a licence question. |

## Product-specific findings

### `nvidia_cublas_cu12-12.8.4.1-py3-none-manylinux_2_27_x86_64.whl`

- sha256 `8ac4e771d5a348c551b2a426eda6193c19aa630236b418086020df5ba9667142`
- Bundled licence: `nvidia_cublas_cu12-12.8.4.1.dist-info/License.txt` (`ad6f5853fba0…`)
- Version-specific primary source: `cuda-12.8.1-eula` (official CUDA Toolkit 12.8.1 EULA (archive page for the release whose components these wheels are: cuBLAS 12.8.4.1, CUDA runtime 12.8.90, nvJitLink 12.8.93, cuFile 1.13.1.3, ...)); bundled text identical: no
- File coverage: 3 library files; named in the bundled Attachment A: 3; in the primary one: 3

### `nvidia_cuda_cupti_cu12-12.8.90-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `ea0cb07ebda26bb9b29ba82cda34849e73c166c18162d3913575b0c9db9a6182`
- Bundled licence: `nvidia_cuda_cupti_cu12-12.8.90.dist-info/License.txt` (`ad6f5853fba0…`)
- Version-specific primary source: `cuda-12.8.1-eula` (official CUDA Toolkit 12.8.1 EULA (archive page for the release whose components these wheels are: cuBLAS 12.8.4.1, CUDA runtime 12.8.90, nvJitLink 12.8.93, cuFile 1.13.1.3, ...)); bundled text identical: no
- File coverage: 5 library files; named in the bundled Attachment A: 1; in the primary one: 1; not named in the primary: libcheckpoint.so, libnvperf_host.so, libnvperf_target.so, libpcsamplingutil.so
- Question: Files not covered by the distributable listing: libcheckpoint.so, libnvperf_host.so, libnvperf_target.so, libpcsamplingutil.so — are they distributable?

### `nvidia_cuda_nvrtc_cu12-12.8.93-py3-none-manylinux2010_x86_64.manylinux_2_12_x86_64.whl`

- sha256 `a7756528852ef889772a84c6cd89d41dfa74667e24cca16bb31f8f061e3e9994`
- Bundled licence: `nvidia_cuda_nvrtc_cu12-12.8.93.dist-info/License.txt` (`ad6f5853fba0…`)
- Version-specific primary source: `cuda-12.8.1-eula` (official CUDA Toolkit 12.8.1 EULA (archive page for the release whose components these wheels are: cuBLAS 12.8.4.1, CUDA runtime 12.8.90, nvJitLink 12.8.93, cuFile 1.13.1.3, ...)); bundled text identical: no
- File coverage: 4 library files; named in the bundled Attachment A: 2; in the primary one: 2; not named in the primary: libnvrtc-builtins.alt.so.12.8, libnvrtc.alt.so.12
- Question: Files not covered by the distributable listing: libnvrtc-builtins.alt.so.12.8, libnvrtc.alt.so.12 — are they distributable?

### `nvidia_cuda_runtime_cu12-12.8.90-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `adade8dcbd0edf427b7204d480d6066d33902cab2a4707dcfc48a2d0fd44ab90`
- Bundled licence: `nvidia_cuda_runtime_cu12-12.8.90.dist-info/License.txt` (`ad6f5853fba0…`)
- Version-specific primary source: `cuda-12.8.1-eula` (official CUDA Toolkit 12.8.1 EULA (archive page for the release whose components these wheels are: cuBLAS 12.8.4.1, CUDA runtime 12.8.90, nvJitLink 12.8.93, cuFile 1.13.1.3, ...)); bundled text identical: no
- File coverage: 1 library files; named in the bundled Attachment A: 1; in the primary one: 1

### `nvidia_cufft_cu12-11.3.3.83-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `4d2dd21ec0b88cf61b62e6b43564355e5222e4a3fb394cac0db101f2dd0d4f74`
- Bundled licence: `nvidia_cufft_cu12-11.3.3.83.dist-info/License.txt` (`ad6f5853fba0…`)
- Version-specific primary source: `cuda-12.8.1-eula` (official CUDA Toolkit 12.8.1 EULA (archive page for the release whose components these wheels are: cuBLAS 12.8.4.1, CUDA runtime 12.8.90, nvJitLink 12.8.93, cuFile 1.13.1.3, ...)); bundled text identical: no
- File coverage: 2 library files; named in the bundled Attachment A: 2; in the primary one: 2

### `nvidia_cufile_cu12-1.13.1.3-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `1d069003be650e131b21c932ec3d8969c1715379251f8d23a1860554b1cb24fc`
- Bundled licence: `nvidia_cufile_cu12-1.13.1.3.dist-info/License.txt` (`ad6f5853fba0…`)
- Version-specific primary source: `cuda-12.8.1-eula` (official CUDA Toolkit 12.8.1 EULA (archive page for the release whose components these wheels are: cuBLAS 12.8.4.1, CUDA runtime 12.8.90, nvJitLink 12.8.93, cuFile 1.13.1.3, ...)); bundled text identical: no
- File coverage: 2 library files; named in the bundled Attachment A: 0; in the primary one: 2
- Question: Which text governs: the bundled CUDA EULA (omits this component) or the official CUDA 12.8.1 EULA (lists its libraries)?

### `nvidia_curand_cu12-10.3.9.90-py3-none-manylinux_2_27_x86_64.whl`

- sha256 `b32331d4f4df5d6eefa0554c565b626c7216f87a06a4f56fab27c3b68a830ec9`
- Bundled licence: `nvidia_curand_cu12-10.3.9.90.dist-info/License.txt` (`ad6f5853fba0…`)
- Version-specific primary source: `cuda-12.8.1-eula` (official CUDA Toolkit 12.8.1 EULA (archive page for the release whose components these wheels are: cuBLAS 12.8.4.1, CUDA runtime 12.8.90, nvJitLink 12.8.93, cuFile 1.13.1.3, ...)); bundled text identical: no
- File coverage: 1 library files; named in the bundled Attachment A: 1; in the primary one: 1

### `nvidia_cusolver_cu12-11.7.3.90-py3-none-manylinux_2_27_x86_64.whl`

- sha256 `4376c11ad263152bd50ea295c05370360776f8c3427b30991df774f9fb26c450`
- Bundled licence: `nvidia_cusolver_cu12-11.7.3.90.dist-info/License.txt` (`ad6f5853fba0…`)
- Version-specific primary source: `cuda-12.8.1-eula` (official CUDA Toolkit 12.8.1 EULA (archive page for the release whose components these wheels are: cuBLAS 12.8.4.1, CUDA runtime 12.8.90, nvJitLink 12.8.93, cuFile 1.13.1.3, ...)); bundled text identical: no
- File coverage: 2 library files; named in the bundled Attachment A: 1; in the primary one: 1; not named in the primary: libcusolverMg.so.11
- Question: Files not covered by the distributable listing: libcusolverMg.so.11 — are they distributable?

### `nvidia_cusparse_cu12-12.5.8.93-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `1ec05d76bbbd8b61b06a80e1eaf8cf4959c3d4ce8e711b65ebd0443bb0ebb13b`
- Bundled licence: `nvidia_cusparse_cu12-12.5.8.93.dist-info/License.txt` (`ad6f5853fba0…`)
- Version-specific primary source: `cuda-12.8.1-eula` (official CUDA Toolkit 12.8.1 EULA (archive page for the release whose components these wheels are: cuBLAS 12.8.4.1, CUDA runtime 12.8.90, nvJitLink 12.8.93, cuFile 1.13.1.3, ...)); bundled text identical: no
- File coverage: 1 library files; named in the bundled Attachment A: 1; in the primary one: 1

### `nvidia_nvjitlink_cu12-12.8.93-py3-none-manylinux2010_x86_64.manylinux_2_12_x86_64.whl`

- sha256 `81ff63371a7ebd6e6451970684f916be2eab07321b73c9d244dc2b4da7f73b88`
- Bundled licence: `nvidia_nvjitlink_cu12-12.8.93.dist-info/License.txt` (`ad6f5853fba0…`)
- Version-specific primary source: `cuda-12.8.1-eula` (official CUDA Toolkit 12.8.1 EULA (archive page for the release whose components these wheels are: cuBLAS 12.8.4.1, CUDA runtime 12.8.90, nvJitLink 12.8.93, cuFile 1.13.1.3, ...)); bundled text identical: no
- File coverage: 1 library files; named in the bundled Attachment A: 0; in the primary one: 1
- Question: Which text governs: the bundled CUDA EULA (omits this component) or the official CUDA 12.8.1 EULA (lists its libraries)?

### `nvidia_nvshmem_cu12-3.4.5-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

- sha256 `042f2500f24c021db8a06c5eec2539027d57460e1c1a762055a6554f72c369bd`
- Bundled licence: `nvidia_nvshmem_cu12-3.4.5.dist-info/licenses/License.txt` (`ad6f5853fba0…`)
- Version-specific primary source: `nvshmem-v3.4.5-0-license` (License.txt at the NVIDIA/nvshmem tag v3.4.5-0 (the release of the 3.4.5 wheel): NVIDIA SDK licence plus the NVSHMEM supplement); bundled text identical: no
- File coverage: 14 library files; named in the bundled Attachment A: 0; in the primary one: 0
- Question: Which text governs: the bundled CUDA EULA or the NVSHMEM v3.4.5-0 SDK licence and supplement? Under the bundled CUDA EULA none of the 14 shipped library files is named in Attachment A; under the supplement "any portion of the SDK" is distributable, and the application requirements still apply.

### `nvidia_cudnn_cu12-9.10.2.21-py3-none-manylinux_2_27_x86_64.whl`

- sha256 `949452be657fa16687d0930933f032835951ef0892b37d2d53824d1a84dc97a8`
- Bundled licence: `nvidia_cudnn_cu12-9.10.2.21.dist-info/licenses/License.txt` (`49cf79bdb357…`)
- Primary source: https://docs.nvidia.com/deeplearning/cudnn/backend/v9.10.2/reference/eula.html (retained `sources/nvidia-cudnn-9.10.2-sla.html`, `f3763a5ae20a…`); release-specific (cuDNN backend v9.10.2 documentation)
- Bundled vs primary (word level): 2781 of 2921 bundled words matched; 21 list-numbering-only spans; 34 other differing spans (agreement body only; page navigation excluded)
  - bundled: "non transferable" → primary: "nontransferable"
  - bundled: "pre release" → primary: "prerelease"
  - bundled: "1 6 third party" → primary: "components under other"
  - bundled: "—" → primary: "nvidia or"
  - bundled: "by a nvidia supplier" → primary: "with separate legal notices or terms as may be described in proprietary notices accompanying the sdk if"
  - bundled: "or open source software provided under an open source license use of third party software is subject" → primary: "—"
  - bundled: "third party" → primary: "extent there is a conflict between the terms in this agreement and the"
  - bundled: "or in" → primary: "associated with"
  - bundled: "absence of third party" → primary: "component the license"
  - bundled: "—" → primary: "associated with"
  - bundled: "terms of this agreement copyright" → primary: "components control only"
  - bundled: "third party software is held by" → primary: "—"
- Distribution clause: "the runtime files .so and .h". Files matching it: 22; other files: 0 ()
- Question: The primary text (release-specific (cuDNN backend v9.10.2 documentation)) differs from the bundled text in 34 spans beyond list numbering (listed above); which text governs this wheel?

### `nvidia_cusparselt_cu12-0.7.1-py3-none-manylinux2014_x86_64.whl`

- sha256 `f1bb701d6b930d5a7cea44c19ceb973311500847f81b634d802b7b539dc55623`
- Bundled licence: `nvidia/cusparselt/LICENSE.txt` (`e8d158885a68…`)
- Primary source: https://docs.nvidia.com/cuda/cusparselt/license.html (retained `sources/nvidia-cusparselt-latest-licence.html`, `596ac591bebd…`); NOT release-specific: the current cuSPARSELt licence page; no 0.7.1 page was found
- Bundled vs primary (word level): 2842 of 2861 bundled words matched; 19 list-numbering-only spans; 0 other differing spans (agreement body only; page navigation excluded)
- Distribution clause: "the runtimes files ending with .so and .h as part of your application". Files matching it: 2; other files: 0 ()
- Question: Evidence gap: no release-specific (0.7.1) licence text was found; is the bundled text accepted as governing?
- Question: The primary text (NOT release-specific: the current cuSPARSELt licence page; no 0.7.1 page was found) matches the bundled text except list numbering; it is not release-specific, so the match does not establish the 0.7.1 terms.
