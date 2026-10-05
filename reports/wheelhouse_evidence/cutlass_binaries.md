# CUTLASS DSL binaries: evidence pack (first viability check)

**A proposal for the designated reviewer, not a decision.**

## Exact wheels

- `nvidia_cutlass_dsl_libs_base-4.5.0.dev0-cp312-cp312-manylinux_2_28_x86_64.whl` (sha256 `38136edf1a1cd0c49fed73dcce966c8ac8b4396bdbd996deada6f73c81f5896e`):
  - 168 Python source files
  - 3 compiled files
  - 1 non-Python headers
  - licence files: `nvidia_cutlass_dsl/LICENSE` (`9ed3a0344d6b…`), `nvidia_cutlass_dsl_libs_base-4.5.0.dev0.dist-info/licenses/LICENSE` (`9ed3a0344d6b…`)
- `nvidia_cutlass_dsl-4.5.0.dev0-py3-none-any.whl` (sha256 `ee81170c5f6e660147888ab84a86aa01e46b810e7c20c9e0fc5bcc8e35bbc719`):
  - 0 Python source files
  - 0 compiled files
  - 0 non-Python headers
  - licence files: `nvidia_cutlass_dsl-4.5.0.dev0.dist-info/licenses/LICENSE` (`9ed3a0344d6b…`)

## Compiled and non-Python files (libs-base wheel)

| File | Bytes | SHA-256 | Format | Embedded markers |
|---|---|---|---|---|
| `nvidia_cutlass_dsl/lib/libcuda_dialect_runtime_static.a` | 15,718 | `ad8f1b4d0c3c…` | ar static archive | — |
| `nvidia_cutlass_dsl/lib/libcute_dsl_runtime.so` | 37,292,792 | `5df6678437e0…` | ELF shared object | — |
| `nvidia_cutlass_dsl/python_packages/cutlass/_mlir/_mlir_libs/_cutlass_ir.cpython-312-x86_64-linux-gnu.so` | 143,954,120 | `40d93848a59d…` | ELF shared object | Copyright (c) 2005-%s NVIDIA Corporation; LLVM Exception; LLVM version 20.0.0; clang version 16.0.0; clang version 7.1.0 |
| `nvidia_cutlass_dsl/include/CuteDSLRuntime.h` | 6,524 | `ac8597baf0fb…` | C header (source, not Python) | — |

## Licence texts checked

| Source | SHA-256 | Identical to the wheels' LICENSE |
|---|---|---|
| `NVIDIA/cutlass@v4.2.0/EULA.txt` (retained `sources/cutlass-v4.2.0-EULA.txt`) | `9ed3a0344d6b…` | yes |
| `NVIDIA/cutlass@v4.2.1/EULA.txt` (retained `sources/cutlass-v4.2.1-EULA.txt`) | `9ed3a0344d6b…` | yes |
| `NVIDIA/cutlass@v4.3.0/EULA.txt` (retained `sources/cutlass-v4.3.0-EULA.txt`) | `9ed3a0344d6b…` | yes |
| `NVIDIA/cutlass@v4.3.5/EULA.txt` (retained `sources/cutlass-v4.3.5-EULA.txt`) | `9ed3a0344d6b…` | yes |
| `NVIDIA/cutlass@v4.4.0/EULA.txt` (retained `sources/cutlass-v4.4.0-EULA.txt`) | `9ed3a0344d6b…` | yes |
| `NVIDIA/cutlass@v4.4.2/EULA.txt` (retained `sources/cutlass-v4.4.2-EULA.txt`) | `9ed3a0344d6b…` | yes |
| `NVIDIA/cutlass@v4.5.0/EULA.txt` (retained `sources/cutlass-v4.5.0-EULA.txt`) | `9ed3a0344d6b…` | yes |
| `NVIDIA/cutlass@main/EULA.txt` (retained `sources/cutlass-main-EULA.txt`) | `9ed3a0344d6b…` | yes |

The licence page named in the metadata (https://docs.nvidia.com/cutlass/latest/media/docs/pythonDSL/license.html, retained `sources/cutlass-dsl-licence-page.html`) has the same wording as `v4.5.0/EULA.txt`. The only differences are list labels: a, b, c, d, i, ii, iii, iv, v, vi.

Metadata licence fields (libs-base): Project-URL: Documentation, https://github.com/NVIDIA/cutlass; Project-URL: Repository, https://github.com/NVIDIA/cutlass; Project-URL: Issues, https://github.com/NVIDIA/cutlass/issues; Project-URL: License, https://docs.nvidia.com/cutlass/latest/media/docs/pythonDSL/license.html; Classifier: License :: Other/Proprietary License; License-File: LICENSE; Requires-Dist: numpy; Requires-Dist: typing-extensions; Requires-Dist: cuda-python>=12.8

## Operative clauses (v4.5.0 text)

**1.1(d) distribution grant.** d. distribute python files in the Software package in source format as incorporated into a software application subject to the following distribution requirements: i. Your application must have material additional functionality, beyond the included portions of the Software. ii. The distributable portions of the Software shall only be accessed by your application. iii. The following notice shall be included in modifications and derivative works of sample source code distributed: “This software contains source code provided by NVIDIA Corporation.” iv. Unless a developer tool is identified in this Agreement as distributable, it is delivered for your internal use only. v. The terms under which you distribute your application must be consistent with the terms of this Agreement, including (without limitation) terms relating to the license grant and license restrictions and protection of NVIDIA’s intellectual property rights. vi. Additionally, you agree that you will protect the privacy, security and legal rights of your application users.

**2.2 no making available to others.** 2.2. Sell, rent, sublicense, transfer, distribute or otherwise make available to others (except authorized users as stated in Section 3 (“Authorized Users”)) any portion of the Software or Derivatives, except as expressly granted in Section 1.1 (“License Grant to You”);

**2.3 no reverse engineering of binaries.** 2.3. Reverse engineer, decompile, or disassemble the Software components provided in binary form, nor attempt in any other manner to obtain source code of such Software;

**3 authorized users.** You may allow employees and contractors of your entity or of your subsidiary(ies), and for educational institutions also enrolled students, to internally access and use the Software as authorized by this Agreement from your secure network to perform the work authorized by this Agreement on your behalf. You are responsible for the compliance with the terms of this Agreement by your authorized users. Any act or omission that if committed by you would constitute a breach of this Agreement will be deemed to constitute a breach of this Agreement if committed by your authorized users.

**6 components under other licenses.** The Software may include or be distributed with components provided with separate legal notices or terms that accompany the components, such as open source software licenses and other license terms (“Other Licenses”). The components are subject to the applicable Other Licenses, including any proprietary notices, disclaimers, requirements and extended use rights; except that this Agreement will prevail regarding the use of third-party open source software, unless a third-party open source software license requires its license terms to prevail. Open source software license means any software, data or documentation subject to any license identified as an open source license by the Open Source Initiative (http://opensource.org), Free Software Foundation (http://www.fsf.org) or other similar open source organization or listed by the Software Package Data Exchange (SPDX) Workgroup under the Linux Foundation (http://www.spdx.org).

## Finding

**No applicable binary redistribution grant identified.** Applies to the compiled files and the C header of the exact wheel listed, under the licence texts listed. Section 1.1(d) grants distribution of "python files in the Software package in source format as incorporated into a software application"; no clause found grants distribution of the compiled files or the non-Python header. This is not a finding that no permission exists anywhere.

Not checked:

- any separate agreement between the team and NVIDIA (none known)
- NVIDIA clarification (not requested)
- whether section 6 covers the embedded LLVM/MLIR code, which the wheel ships with no accompanying licence or notice; even if it does, that permission would cover only those components, not NVIDIA's code in the same binaries
- repository refs other than those listed

Questions for the reviewer:

- Is any permission available for the compiled files (libcute_dsl_runtime.so, _cutlass_ir.cpython-312 .so, libcuda_dialect_runtime_static.a) and the header CuteDSLRuntime.h?
- Do the embedded LLVM/MLIR components (markers: Copyright (c) 2005-%s NVIDIA Corporation, LLVM Exception, LLVM version 20.0.0, clang version 16.0.0, clang version 7.1.0) impose their own notice obligations when the binaries are redistributed?
- Section 3 permits access by employees and contractors "from your secure network": does the planned deployment fit that, or is it making the Software available to others (2.2)?

Owner options if not cleared (no automatic choice):

- written clarification from NVIDIA (licensing contact in the EULA)
- an explicitly revised dependency set with fresh validation (flashinfer-python 0.6.6 requires nvidia-cutlass-dsl>=4.3.4 and quack-kernels 0.4.1 requires >=4.4.2)
- record the bundle as blocked
