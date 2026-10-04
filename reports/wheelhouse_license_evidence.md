# Wheelhouse R2 licence evidence (reading aid, not a legal review)

Extracted from the 174 downloaded, hash-verified wheels of manifest `3691cb88…d546` by `scripts/extract_wheelhouse_licenses.py`. Full texts are kept outside the repository (`~/.local/share/agi/wheelhouse-r2-licenses/`). Family detection is heuristic. Every row remains `unresolved` in `reports/wheelhouse_license_review.csv` until the owner (dcw06) decides it.

**How to read the families and flags.** A family is listed when its licence text appears anywhere in the wheel’s licence files. That includes bundled third-party notices (for example the NVIDIA `License.txt` files and torch’s `NOTICE` reproduce the licences of components they include) and mere mentions (the PSF licence text mentions GPL compatibility, so PSF-licensed packages show `GPL`). `declared_copyleft` is the stronger signal: the package’s own metadata declares an MPL, LGPL or GPL licence. `copyleft_terms_present` only says such text appears somewhere and needs reading.

## Summary

- Wheels: 174
- Wheels shipping licence material: 165
- Licence files found: 225

| Detected family | Wheels |
|---|---|
| MIT | 79 |
| Apache-2.0 | 62 |
| BSD-3-Clause | 47 |
| LGPL | 19 |
| NVIDIA-proprietary | 17 |
| BSD-2-Clause | 9 |
| ISC | 8 |
| MPL-2.0 | 6 |
| Zlib | 4 |
| GPL | 3 |
| PSF-2.0 | 3 |
| CC0 | 1 |
| Unlicense | 1 |

| Review flag | Wheels |
|---|---|
| `copyleft_terms_present` | 24 |
| `declared_copyleft` | 3 |
| `no_licence_file_in_wheel` | 9 |
| `proprietary_terms_present` | 22 |
| `unrecognised_licence_text` | 1 |

## Proprietary terms (decide redistribution first) (22)

- **cuda_bindings 12.9.4** — declared: LicenseRef-NVIDIA-SOFTWARE-LICENSE; detected: none; files: `LICENSE`
  - _LICENSE_: “Subject to the terms of this license, NVIDIA grants you a non-exclusive limited license to: (a) install and use the SOFTWARE, and (b) distribute the SOFTWARE subject to the distribution requirements described in this license.”
  - _LICENSE_: “The terms under which you distribute the SOFTWARE must be consistent with the terms of this license, including (without limitation) terms relating to the license grant and license restrictions and protection of NVIDIA's intellectual property rights.”
- **cuda_python 12.9.4** — declared: LicenseRef-NVIDIA-SOFTWARE-LICENSE; detected: none; files: `LICENSE`
  - _LICENSE_: “Subject to the terms of this license, NVIDIA grants you a non-exclusive limited license to: (a) install and use the SOFTWARE, and (b) distribute the SOFTWARE subject to the distribution requirements described in this license.”
  - _LICENSE_: “The terms under which you distribute the SOFTWARE must be consistent with the terms of this license, including (without limitation) terms relating to the license grant and license restrictions and protection of NVIDIA's intellectual property rights.”
- **numba 0.61.2** — declared: BSD; OSI Approved :: BSD License; detected: BSD-2-Clause, MIT, BSD-3-Clause, PSF-2.0, GPL, ISC, NVIDIA-proprietary; files: `LICENSE`, `LICENSES.third-party`
  - _LICENSES.third-party_: “Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met: * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.”
  - _LICENSES.third-party_: “* Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.”
- **nvidia_cublas_cu12 12.8.4.1** — declared: NVIDIA Proprietary Software; Other/Proprietary License; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **nvidia_cuda_cupti_cu12 12.8.90** — declared: NVIDIA Proprietary Software; Other/Proprietary License; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **nvidia_cuda_nvrtc_cu12 12.8.93** — declared: NVIDIA Proprietary Software; Other/Proprietary License; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **nvidia_cuda_runtime_cu12 12.8.90** — declared: NVIDIA Proprietary Software; Other/Proprietary License; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **nvidia_cudnn_cu12 9.10.2.21** — declared: LicenseRef-NVIDIA-Proprietary; Other/Proprietary License; detected: NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “1.1 Grant Subject to the terms of this Agreement, NVIDIA hereby grants you a non-exclusive, non-transferable license, without the right to sublicense (except as expressly provided in this Agreement) to: (i) Install and use the SDK, (ii) Modify and create derivative works of sample source code delive”
  - _License.txt_: “1.2 Distribution Requirements These are the distribution requirements for you to exercise the distribution grant: (i) Your application must have material additional functionality, beyond the included portions of the SDK.”
- **nvidia_cudnn_frontend 1.18.0** — declared: NVIDIA Proprietary Software; detected: MIT; files: `LICENSE.MIT`, `LICENSE.txt`
- **nvidia_cufft_cu12 11.3.3.83** — declared: NVIDIA Proprietary Software; Other/Proprietary License; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **nvidia_cufile_cu12 1.13.1.3** — declared: NVIDIA Proprietary Software; Other/Proprietary License; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **nvidia_curand_cu12 10.3.9.90** — declared: NVIDIA Proprietary Software; Other/Proprietary License; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **nvidia_cusolver_cu12 11.7.3.90** — declared: NVIDIA Proprietary Software; Other/Proprietary License; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **nvidia_cusparse_cu12 12.5.8.93** — declared: NVIDIA Proprietary Software; Other/Proprietary License; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **nvidia_cusparselt_cu12 0.7.1** — declared: NVIDIA Proprietary Software; detected: NVIDIA-proprietary; files: `LICENSE.txt`
  - _LICENSE.txt_: “1.1 Grant Subject to the terms of this Agreement, NVIDIA hereby grants you a non-exclusive, non-transferable license, without the right to sublicense (except as expressly provided in this Agreement) to: (i) Install and use the SDK, (ii) Modify and create derivative works of sample source code delive”
  - _LICENSE.txt_: “1.2 Distribution Requirements These are the distribution requirements for you to exercise the distribution grant: (i) Your application must have material additional functionality, beyond the included portions of the SDK.”
- **nvidia_cutlass_dsl 4.5.0.dev0** — declared: Other/Proprietary License; detected: NVIDIA-proprietary; files: `LICENSE`
  - _LICENSE_: “distribute python files in the Software package in source format as incorporated into a software application subject to the following distribution requirements: i.”
  - _LICENSE_: “Sell, rent, sublicense, transfer, distribute or otherwise make available to others (except authorized users as stated in Section 3 (“Authorized Users”)) any portion of the Software or Derivatives, except as expressly granted in Section 1.1 (“License Grant to You”);”
- **nvidia_cutlass_dsl_libs_base 4.5.0.dev0** — declared: Other/Proprietary License; detected: NVIDIA-proprietary; files: `LICENSE`, `LICENSE`
  - _LICENSE_: “distribute python files in the Software package in source format as incorporated into a software application subject to the following distribution requirements: i.”
  - _LICENSE_: “Sell, rent, sublicense, transfer, distribute or otherwise make available to others (except authorized users as stated in Section 3 (“Authorized Users”)) any portion of the Software or Derivatives, except as expressly granted in Section 1.1 (“License Grant to You”);”
- **nvidia_nccl_cu12 2.27.5** — declared: BSD-3-Clause; Other/Proprietary License; detected: BSD-3-Clause; files: `License.txt`
- **nvidia_nvjitlink_cu12 12.8.93** — declared: NVIDIA Proprietary Software; Other/Proprietary License; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **nvidia_nvshmem_cu12 3.4.5** — declared: LicenseRef-NVIDIA-Proprietary; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **nvidia_nvtx_cu12 12.8.90** — declared: Apache 2.0; Other/Proprietary License; detected: Apache-2.0; files: `License.txt`
- **torch 2.10.0** — declared: BSD-3-Clause; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, Zlib, NVIDIA-proprietary; files: `LICENSE`, `NOTICE`
  - _LICENSE_: “Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met: 1.”
  - _LICENSE_: “Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.”

## Package declares a copyleft licence itself (3)

- **certifi 2026.4.22** — declared: MPL-2.0; OSI Approved :: Mozilla Public License 2.0 (MPL 2.0); detected: MPL-2.0; files: `LICENSE`
- **pycountry 26.2.16** — declared: LGPL-2.1-only; OSI Approved :: GNU Lesser General Public License v2 (LGPLv2); detected: LGPL; files: `COPYRIGHT.txt`, `LICENSE.txt`
- **tqdm 4.67.3** — declared: MPL-2.0 AND MIT; detected: MIT, MPL-2.0; files: `LICENCE`

## Copyleft terms present (notice and source obligations to check) (24)

- **aiohappyeyeballs 2.6.1** — declared: PSF-2.0; OSI Approved :: Python Software Foundation License; detected: PSF-2.0, GPL, ISC; files: `LICENSE`
- **certifi 2026.4.22** — declared: MPL-2.0; OSI Approved :: Mozilla Public License 2.0 (MPL 2.0); detected: MPL-2.0; files: `LICENSE`
- **grpcio 1.80.0** — declared: Apache-2.0; detected: Apache-2.0, BSD-3-Clause, MPL-2.0, LGPL; files: `LICENSE`
- **numba 0.61.2** — declared: BSD; OSI Approved :: BSD License; detected: BSD-2-Clause, MIT, BSD-3-Clause, PSF-2.0, GPL, ISC, NVIDIA-proprietary; files: `LICENSE`, `LICENSES.third-party`
  - _LICENSES.third-party_: “Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met: * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.”
  - _LICENSES.third-party_: “* Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.”
- **numpy 2.2.6** — declared: Copyright (c) 2005-2024, NumPy Developers.; OSI Approved :: BSD License; detected: BSD-3-Clause, MIT, Zlib, LGPL; files: `LICENSE`, `LICENSE.md`, `LICENSE.txt`, `LICENSE.txt`
- **nvidia_cublas_cu12 12.8.4.1** — declared: NVIDIA Proprietary Software; Other/Proprietary License; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **nvidia_cuda_cupti_cu12 12.8.90** — declared: NVIDIA Proprietary Software; Other/Proprietary License; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **nvidia_cuda_nvrtc_cu12 12.8.93** — declared: NVIDIA Proprietary Software; Other/Proprietary License; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **nvidia_cuda_runtime_cu12 12.8.90** — declared: NVIDIA Proprietary Software; Other/Proprietary License; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **nvidia_cufft_cu12 11.3.3.83** — declared: NVIDIA Proprietary Software; Other/Proprietary License; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **nvidia_cufile_cu12 1.13.1.3** — declared: NVIDIA Proprietary Software; Other/Proprietary License; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **nvidia_curand_cu12 10.3.9.90** — declared: NVIDIA Proprietary Software; Other/Proprietary License; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **nvidia_cusolver_cu12 11.7.3.90** — declared: NVIDIA Proprietary Software; Other/Proprietary License; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **nvidia_cusparse_cu12 12.5.8.93** — declared: NVIDIA Proprietary Software; Other/Proprietary License; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **nvidia_nvjitlink_cu12 12.8.93** — declared: NVIDIA Proprietary Software; Other/Proprietary License; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **nvidia_nvshmem_cu12 3.4.5** — declared: LicenseRef-NVIDIA-Proprietary; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, NVIDIA-proprietary; files: `License.txt`
  - _License.txt_: “Distribute those portions of the SDK that are identified in this Agreement as distributable, as incorporated in object code format into a software application that meets the distribution requirements indicated in this Agreement.”
  - _License.txt_: “You agree to notify NVIDIA in writing of any known or suspected distribution or use of the SDK not in compliance with the requirements of this Agreement, and to enforce the terms of your agreements with respect to distributed SDK.”
- **opencv_python_headless 4.13.0.92** — declared: Apache 2.0; OSI Approved :: Apache Software License; detected: Apache-2.0, MIT, BSD-3-Clause, MPL-2.0, LGPL, ISC, Zlib; files: `LICENSE-3RD-PARTY.txt`, `LICENSE.txt`, `haarcascade_license_plate_rus_16stages.xml`, `LICENSE-3RD-PARTY.txt`
- **pillow 12.2.0** — declared: MIT-CMU; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, Zlib; files: `LICENSE`
- **pycountry 26.2.16** — declared: LGPL-2.1-only; OSI Approved :: GNU Lesser General Public License v2 (LGPLv2); detected: LGPL; files: `COPYRIGHT.txt`, `LICENSE.txt`
- **pyzmq 27.1.0** — declared: BSD 3-Clause License; OSI Approved :: BSD License; detected: BSD-3-Clause, ISC, Apache-2.0, MPL-2.0, LGPL; files: `LICENSE.md`, `LICENSE.libsodium.txt`, `LICENSE.tornado.txt`, `LICENSE.zeromq.txt`
- **setuptools 80.10.2** — declared: MIT; detected: Apache-2.0, MIT, BSD-2-Clause, MPL-2.0, BSD-3-Clause, LGPL; files: `LICENSE`, `LICENSE`, `LICENSE`, `LICENSE`
- **torch 2.10.0** — declared: BSD-3-Clause; detected: Apache-2.0, MIT, BSD-3-Clause, LGPL, Zlib, NVIDIA-proprietary; files: `LICENSE`, `NOTICE`
  - _LICENSE_: “Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met: 1.”
  - _LICENSE_: “Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.”
- **tqdm 4.67.3** — declared: MPL-2.0 AND MIT; detected: MIT, MPL-2.0; files: `LICENCE`
- **typing_extensions 4.15.0** — declared: PSF-2.0; detected: PSF-2.0, GPL, ISC; files: `LICENSE`

## Licence text not recognised by the heuristics (1)

- **shellingham 1.5.4** — declared: ISC License; OSI Approved :: ISC License (ISCL); detected: none; files: `LICENSE`
  - _LICENSE_: “Copyright (c) 2018, Tzu-ping Chung <uranusjr@gmail.com> Permission to use, copy, modify, and distribute this software for any purpose with or without fee is hereby granted, provided that the above copyright notice and this permission notice appear in all copies.”

## No licence file in the wheel (rely on metadata/upstream) (9)

- **flashinfer_cubin 0.6.6** — declared: Apache-2.0; OSI Approved :: Apache Software License; detected: none; files: none
- **loguru 0.7.3** — declared: OSI Approved :: MIT License; detected: none; files: none
- **mistral_common 1.11.1** — declared: Apache-2.0; detected: none; files: none
- **model_hosting_container_standards 0.1.14** — declared: Apache-2.0; OSI Approved :: Apache Software License; detected: none; files: none
- **nvidia_ml_py 13.595.45** — declared: BSD; OSI Approved :: BSD License; detected: none; files: none
- **opentelemetry_semantic_conventions_ai 0.5.1** — declared: Apache-2.0; detected: none; files: none
- **sentencepiece 0.2.1** — declared: none; detected: none; files: none
- **supervisor 4.3.0** — declared: BSD-derived (http://www.repoze.org/LICENSE.txt); detected: none; files: none
- **tokenizers 0.22.2** — declared: OSI Approved :: Apache Software License; detected: none; files: none
