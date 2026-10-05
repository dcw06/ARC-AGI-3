# NVIDIA licence reconciliation (review preparation; not a grant)

Applicability facts and open questions for the designated reviewer. Nothing here grants or refuses redistribution permission.

## Primary sources retained

| Source | URL | Retrieved | SHA-256 | Basis |
|---|---|---|---|---|
| `cuda-12.8.1-eula` | https://docs.nvidia.com/cuda/archive/12.8.1/eula/index.html | 2026-10-04 | `6722d4c310a2…` | official CUDA Toolkit 12.8.1 EULA (archive page for the release whose components these wheels are: cuBLAS 12.8.4.1, CUDA runtime 12.8.90, nvJitLink 12.8.93, cuFile 1.13.1.3, ...) |
| `nvshmem-v3.4.5-0-license` | https://raw.githubusercontent.com/NVIDIA/nvshmem/v3.4.5-0/License.txt | 2026-10-04 | `1f5b7ada7029…` | License.txt at the NVIDIA/nvshmem tag v3.4.5-0 (the release of the 3.4.5 wheel): NVIDIA SDK licence plus the NVSHMEM supplement |
| `nvshmem-sla-latest` | https://docs.nvidia.com/nvshmem/api/latest/sla.html | 2026-10-04 | `cc9736532198…` | current NVSHMEM SLA page; NOT version-specific (no 3.4.x SLA page exists in the NVSHMEM archive, which ends at 2.8.0) |
| `cutlass-v4.5.0-eula` | https://raw.githubusercontent.com/NVIDIA/cutlass/v4.5.0/EULA.txt | 2026-10-04 | `9ed3a0344d6b…` | EULA.txt at the NVIDIA/cutlass tag v4.5.0; the wheels are 4.5.0.dev0, a pre-release with no tag of its own |

## Priority artifacts

### `nvidia_cufile_cu12-1.13.1.3-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

Applicability discrepancy requiring review. The wheel's bundled License.txt (the same older CUDA EULA text in all eleven CUDA wheels) has no cuFile entry in Attachment A, but the official CUDA 12.8.1 EULA Attachment A lists libcufile.so, libcufile_rdma.so and their static libraries as distributable. Which text governs this wheel, and whether the proposed private-dataset distribution meets the official conditions (incorporation in an application with material additional functionality; no stand-alone distribution), is for qualified review. This is not a finding that no grant exists, and not a grant.

- Primary source: `cuda-12.8.1-eula`; bundled licence identical to it: no
- Bundled licence files: `nvidia_cufile_cu12-1.13.1.3.dist-info/License.txt` (`ad6f5853fba0…`)

| Library file | In bundled Attachment A | In official Attachment A |
|---|---|---|
| `nvidia/cufile/lib/libcufile.so.0` | no | yes |
| `nvidia/cufile/lib/libcufile_rdma.so.1` | no | yes |

### `nvidia_nvjitlink_cu12-12.8.93-py3-none-manylinux2010_x86_64.manylinux_2_12_x86_64.whl`

Applicability discrepancy requiring review. As for cuFile: the bundled text omits nvJitLink, while the official CUDA 12.8.1 EULA Attachment A lists libnvJitLink.so and libnvJitLink_static.a as distributable. The same applicability and distribution-condition questions apply.

- Primary source: `cuda-12.8.1-eula`; bundled licence identical to it: no
- Bundled licence files: `nvidia_nvjitlink_cu12-12.8.93.dist-info/License.txt` (`ad6f5853fba0…`)
- Required by: nvidia-cufft-cu12==11.3.3.83 (Requires-Dist: nvidia-nvjitlink-cu12); nvidia-cusolver-cu12==11.7.3.90 (Requires-Dist: nvidia-cusparse-cu12); nvidia-cusolver-cu12==11.7.3.90 (Requires-Dist: nvidia-nvjitlink-cu12); nvidia-cusparse-cu12==12.5.8.93 (Requires-Dist: nvidia-nvjitlink-cu12)

| Library file | In bundled Attachment A | In official Attachment A |
|---|---|---|
| `nvidia/nvjitlink/lib/libnvJitLink.so.12` | no | yes |

### `nvidia_nvshmem_cu12-3.4.5-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl`

Separate product terms. The wheel bundles the CUDA Toolkit EULA, which does not mention NVSHMEM. The License.txt at NVIDIA/nvshmem tag v3.4.5-0 is the NVIDIA SDK licence plus an NVSHMEM supplement whose section 2 makes "any portion of the SDK" distributable, still subject to the SDK licence's distribution requirements (incorporation into an application with material additional functionality, accessed only by it; no stand-alone distribution). The current NVSHMEM SLA page carries the same supplement (v. July 11, 2019) but is not version-specific. GitHub's repository metadata reports Apache-2.0 for the default branch, which differs from the tag's License.txt; the tag text is treated as the version-specific source. Which text governs the wheel, and whether the proposed distribution meets the conditions, is for qualified review.

- Primary source: `nvshmem-v3.4.5-0-license`; bundled licence identical to it: no
- Bundled licence files: `nvidia_nvshmem_cu12-3.4.5.dist-info/licenses/License.txt` (`ad6f5853fba0…`)

| Library file | In bundled Attachment A | In official Attachment A |
|---|---|---|
| `nvidia/nvshmem/lib/libnvshmem_device.a` | no | no |
| `nvidia/nvshmem/lib/libnvshmem_device.bc` | no | no |
| `nvidia/nvshmem/lib/libnvshmem_host.so.3` | no | no |
| `nvidia/nvshmem/lib/nvshmem_bootstrap_mpi.so.3` | no | no |
| `nvidia/nvshmem/lib/nvshmem_bootstrap_pmi.so.3` | no | no |
| `nvidia/nvshmem/lib/nvshmem_bootstrap_pmi2.so.3` | no | no |
| `nvidia/nvshmem/lib/nvshmem_bootstrap_pmix.so.3` | no | no |
| `nvidia/nvshmem/lib/nvshmem_bootstrap_shmem.so.3` | no | no |
| `nvidia/nvshmem/lib/nvshmem_bootstrap_uid.so.3` | no | no |
| `nvidia/nvshmem/lib/nvshmem_transport_ibdevx.so.3` | no | no |
| `nvidia/nvshmem/lib/nvshmem_transport_ibgda.so.3` | no | no |
| `nvidia/nvshmem/lib/nvshmem_transport_ibrc.so.3` | no | no |
| `nvidia/nvshmem/lib/nvshmem_transport_libfabric.so.3` | no | no |
| `nvidia/nvshmem/lib/nvshmem_transport_ucx.so.3` | no | no |

### `nvidia_cutlass_dsl_libs_base-4.5.0.dev0-cp312-cp312-manylinux_2_28_x86_64.whl`

Bundled text confirmed as the primary text. The wheel's LICENSE is byte-identical to EULA.txt at NVIDIA/cutlass tags v4.2.0 through v4.5.0 and main (sha256 9ed3a034...). Section 1.1(d) grants distribution of "python files in the Software package in source format as incorporated into a software application"; the wheel also ships compiled files (listed below) for which no distribution grant has been identified in that text. Whether another grant covers them is for qualified review or NVIDIA clarification. The package is a required dependency (see required_by) and must not be dropped without an explicitly revised dependency set and fresh validation.

- Primary source: `cutlass-v4.5.0-eula`; bundled licence identical to it: yes
- Bundled licence files: `nvidia_cutlass_dsl/LICENSE` (`9ed3a0344d6b…`), `nvidia_cutlass_dsl_libs_base-4.5.0.dev0.dist-info/licenses/LICENSE` (`9ed3a0344d6b…`)
- Required by: flashinfer-python==0.6.6 (nvidia-cutlass-dsl>=4.3.4); nvidia-cutlass-dsl==4.5.0.dev0 (Requires-Dist: nvidia-cutlass-dsl-libs-base==4.5.0.dev0); quack-kernels==0.4.1 (nvidia-cutlass-dsl>=4.4.2)

| Library file | In bundled Attachment A | In official Attachment A |
|---|---|---|
| `nvidia_cutlass_dsl/lib/libcuda_dialect_runtime_static.a` | no | no |
| `nvidia_cutlass_dsl/lib/libcute_dsl_runtime.so` | no | no |
| `nvidia_cutlass_dsl/python_packages/cutlass/_mlir/_mlir_libs/_cutlass_ir.cpython-312-x86_64-linux-gnu.so` | no | no |

## All reconciled wheels

| Wheel | Library files | Listed (bundled) | Listed (official) |
|---|---|---|---|
| `nvidia_cublas_cu12-12.8.4.1-py3-none-manylinux_2_27_x86_64.whl` | 3 | 3 | 3 |
| `nvidia_cuda_cupti_cu12-12.8.90-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl` | 5 | 1 | 1 |
| `nvidia_cuda_nvrtc_cu12-12.8.93-py3-none-manylinux2010_x86_64.manylinux_2_12_x86_64.whl` | 4 | 2 | 2 |
| `nvidia_cuda_runtime_cu12-12.8.90-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl` | 1 | 1 | 1 |
| `nvidia_cufft_cu12-11.3.3.83-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl` | 2 | 2 | 2 |
| `nvidia_cufile_cu12-1.13.1.3-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl` | 2 | 0 | 2 |
| `nvidia_curand_cu12-10.3.9.90-py3-none-manylinux_2_27_x86_64.whl` | 1 | 1 | 1 |
| `nvidia_cusolver_cu12-11.7.3.90-py3-none-manylinux_2_27_x86_64.whl` | 2 | 1 | 1 |
| `nvidia_cusparse_cu12-12.5.8.93-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl` | 1 | 1 | 1 |
| `nvidia_nvjitlink_cu12-12.8.93-py3-none-manylinux2010_x86_64.manylinux_2_12_x86_64.whl` | 1 | 0 | 1 |
| `nvidia_nvshmem_cu12-3.4.5-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl` | 14 | 0 | 0 |
| `nvidia_cutlass_dsl-4.5.0.dev0-py3-none-any.whl` | 0 | 0 | 0 |
| `nvidia_cutlass_dsl_libs_base-4.5.0.dev0-cp312-cp312-manylinux_2_28_x86_64.whl` | 3 | 0 | 0 |

Name matching is a string check of library basenames (version suffixes removed) against the Attachment A text; it does not decide which text governs, whether headers or other files are covered, or whether a distribution meets the conditions.
