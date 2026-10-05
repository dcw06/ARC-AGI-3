# Declared-licence discrepancies: ninja, regex, prometheus_client

**Evidence for the designated reviewer: a proposal, not a decision, and not legal clearance.**

Each of these wheels declares in its metadata a licence that the inventory did not find in the wheel's bundled licence documents. For each one this pack checks the hash-verified local wheel, the hash-verified PyPI sdist of the exact version and, where useful, upstream files at a verified commit or tag. It then names the component that carries the extra licence, says whether that component ships in the wheel and where its licence text is, and proposes an obligation. Classification: `explained` (component identified, ships in the wheel, licence text located), `partially_explained`, or `unexplained`. Retained sources are under `reports/wheelhouse_evidence/sources/` with URL, date and SHA-256.

| Wheel | Declared | Detected in wheel documents | Component carrying the extra licence | Ships in wheel | Licence text | Classification |
|---|---|---|---|---|---|---|
| ninja 1.13.0 | OSI Approved :: Apache Software License; OSI Approved :: BSD License | Apache-2.0 | rapidhash (Copyright (C) 2024 Nicolas De Carli; based on wyhash by Wang Yi), vendored by ninja at ninja-upstream/src/third_party/rapidhash/ | True | `sources/metadata-ninja-rapidhash-licence-header.txt` | **explained** |
| regex 2026.4.4 | Apache-2.0 AND CNRI-Python | Apache-2.0 | SRE regular expression engine (Copyright (c) 1997-2001 Secret Labs AB), from CPython 2.6/3.1's re module, from which regex derives | True | `sources/metadata-regex-spdx-v3.27.0-CNRI-Python.txt` | **explained** |
| prometheus_client 0.25.0 | Apache-2.0 AND BSD-2-Clause | Apache-2.0 | decorator 4.0.10 (Copyright (c) 2005-2016, Michele Simionato), vendored as prometheus_client/decorator.py | True | `sources/metadata-prometheus_client-decorator-licence-header.txt` | **explained** |

## ninja 1.13.0

- Wheel: `ninja-1.13.0-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl` (sha256 `fb46acf6b93b8dd0322adc3a4945452a4e774b75b91293bafcc7b7f8e6517dfa`), opened after hash verification against the approved manifest.
- Declared: Classifier: License :: OSI Approved :: Apache Software License; Classifier: License :: OSI Approved :: BSD License
- Detected in the wheel's licence documents (inventory): Apache-2.0
- Extra declared licence: BSD (classifier "License :: OSI Approved :: BSD License", variant not named)
- **Classification: explained**

### Licence documents in the wheel

| Path | SHA-256 | Licence signals |
|---|---|---|
| `ninja-1.13.0.dist-info/licenses/AUTHORS.rst` | `6c6135b7f2e1…` | text: —; reference: —; spdx: — |
| `ninja-1.13.0.dist-info/licenses/LICENSE_Apache_20` | `73ba74dfaa52…` | text: Apache-2.0; reference: Apache-2.0; spdx: — |

### Files searched

- Wheel: 13 files; 12 text files scanned for licence headers (first 4000 characters), licence documents read in full; 1 compiled file(s) scanned for embedded licence strings.
  - `ninja/ninja_syntax.py` (`4425d9e91a1d…`, header lines 3-15): text: —; reference: Apache-2.0; spdx: —
  - compiled `ninja-1.13.0.data/scripts/ninja` (`696f9628a79d…`): "#     http://www.apache.org/licenses/LICENSE-2.0"; "# Copyright 2001 Google Inc. All Rights Reserved."; "# Licensed under the Apache License, Version 2.0 (the "License");"; "# See the License for the specific language governing permissions and"; "# You may obtain a copy of the License at"; "# distributed under the License is distributed on an "AS IS" BASIS,"; "# limitations under the License."; "# you may not use this file except in compliance with the License."
- Sdist `ninja-1.13.0.tar.gz` (sha256 `4a40ce995ded54d9dc24f8ea37ff3bf62ad192b547f6c7126e7e25045e76f978`, verified against PyPI): 159 files, 159 text files scanned. Licence documents: `AUTHORS.rst` (text: —; reference: —; spdx: —), `LICENSE_Apache_20` (text: Apache-2.0; reference: Apache-2.0; spdx: —), `ninja-upstream/COPYING` (text: Apache-2.0; reference: Apache-2.0; spdx: —).
  Members whose header carries a licence signal other than Apache-2.0:
  - `PKG-INFO`: text: —; reference: BSD (variant not named); spdx: —
  - `ninja-upstream/src/getopt.c`: text: —; reference: public-domain; spdx: —
  - `ninja-upstream/src/third_party/emhash/README.ninja`: text: —; reference: —; spdx: MIT
  - `ninja-upstream/src/third_party/emhash/hash_table8.hpp`: text: MIT; reference: MIT; spdx: MIT
  - `ninja-upstream/src/third_party/rapidhash/README.ninja`: text: —; reference: BSD-2-Clause; spdx: BSD-2-Clause
  - `ninja-upstream/src/third_party/rapidhash/rapidhash.h`: text: BSD-2-Clause-style; reference: BSD-2-Clause; spdx: —
  - `pyproject.toml`: text: —; reference: BSD (variant not named); spdx: —
- Upstream: the ninja-python-distributions tag 1.13.0 pins the ninja-upstream submodule at Kitware/ninja `d74efef9fa331d3ae60b62479d49254827c081fe` (API lookup this run: True; matches the recorded commit: True; the wheel README's `1.13.0.gd74ef.kitware.jobserver-pipe-1` abbreviates it: True). Its src/version.cc contains the binary's version string: True. Files fetched at that commit, and whether they match the sdist:
  - `src/version.cc`: identical to sdist True; retained `sources/metadata-ninja-kitware-d74efef9-src_version.cc`
  - `src/hash_map.h`: identical to sdist True; retained `sources/metadata-ninja-kitware-d74efef9-src_hash_map.h`
  - `src/third_party/rapidhash/README.ninja`: identical to sdist True; retained `sources/metadata-ninja-kitware-d74efef9-src_third_party_rapidhash_README.ninja`
  - `src/third_party/rapidhash/rapidhash.h`: identical to sdist True; retained `sources/metadata-ninja-kitware-d74efef9-src_third_party_rapidhash_rapidhash.h`
  - `src/third_party/emhash/README.ninja`: identical to sdist True; retained `sources/metadata-ninja-kitware-d74efef9-src_third_party_emhash_README.ninja`
- Classifier history: ninja 1.7.2 declared ['License :: OSI Approved :: Apache Software License', 'License :: OSI Approved :: BSD License'] (retained `sources/metadata-ninja-pypi-1.7.2.json`).

### Component carrying the extra licence

**rapidhash (Copyright (C) 2024 Nicolas De Carli; based on wyhash by Wang Yi), vendored by ninja at ninja-upstream/src/third_party/rapidhash/**, licence BSD-2-Clause (SPDX identifier in README.ninja; BSD 2-Clause wording in the rapidhash.h header).

- Linux sources of the binary that include rapidhash.h (via hash_map.h): src/build.cc, src/build_log.cc, src/clean.cc, src/deps_log.cc, src/dyndep.cc, src/dyndep_parser.cc, src/graph.cc, src/manifest_parser.cc, src/missing_deps.cc, src/ninja.cc, src/state.cc.
- Sources calling rapidhash(): src/build_log.cc, src/hash_map.h.
- Ships in the wheel: True: compiled into `ninja-1.13.0.data/scripts/ninja` (sha256 `696f9628a79d9ce50314cf9556d7cd1a1d1ec52b8fd52828f6f9db1719565b67`). The binary embeds the sdist's kNinjaVersion `1.13.0.git.kitware.jobserver-pipe-1`: True. rapidhash's secret constants occur 0x2d358dccaa6c78a5 ×22, 0x8bb84b93962eacc9 ×45, 0x4b33a62ed433d4a3 ×27. The constants are also in the emhash header: True, but only under EMH_WYHASH_HASH, which no other file mentions (none).
- The bundled LICENSE_Apache_20 is byte-identical to ninja's COPYING: False.

### Licence text location

- In the wheel: no (the wheel carries only LICENSE_Apache_20 and AUTHORS.rst)
- In the sdist: yes: ninja-upstream/src/third_party/rapidhash/rapidhash.h lines 1-34 (licence header); README.ninja beside it names SPDX BSD-2-Clause
- Upstream: Kitware/ninja@d74efef9fa33/src/third_party/rapidhash/rapidhash.h

| Retained file | SHA-256 | Source |
|---|---|---|
| `sources/metadata-ninja-rapidhash-licence-header.txt` | `c22c67335c2b…` | https://files.pythonhosted.org/packages/43/73/79a0b22fc731989c708068427579e840a6cf4e937fe7ae5c5d0b7356ac22/ninja-1.13.0.tar.gz#ninja-upstream/src/third_party/rapidhash/rapidhash.h (lines 1-34) |
| `sources/metadata-ninja-github-submodule-at-1.13.0.json` | `42a5921a46c5…` | https://api.github.com/repos/scikit-build/ninja-python-distributions/contents/ninja-upstream?ref=1.13.0 |
| `sources/metadata-ninja-kitware-d74efef9-src_version.cc` | `4f82c00b2f3a…` | https://raw.githubusercontent.com/Kitware/ninja/d74efef9fa331d3ae60b62479d49254827c081fe/src/version.cc |
| `sources/metadata-ninja-kitware-d74efef9-src_hash_map.h` | `c0ee50e8a9b1…` | https://raw.githubusercontent.com/Kitware/ninja/d74efef9fa331d3ae60b62479d49254827c081fe/src/hash_map.h |
| `sources/metadata-ninja-kitware-d74efef9-src_third_party_rapidhash_README.ninja` | `551724350651…` | https://raw.githubusercontent.com/Kitware/ninja/d74efef9fa331d3ae60b62479d49254827c081fe/src/third_party/rapidhash/README.ninja |
| `sources/metadata-ninja-kitware-d74efef9-src_third_party_rapidhash_rapidhash.h` | `263b42cbe8d4…` | https://raw.githubusercontent.com/Kitware/ninja/d74efef9fa331d3ae60b62479d49254827c081fe/src/third_party/rapidhash/rapidhash.h |
| `sources/metadata-ninja-kitware-d74efef9-src_third_party_emhash_README.ninja` | `871523bf3637…` | https://raw.githubusercontent.com/Kitware/ninja/d74efef9fa331d3ae60b62479d49254827c081fe/src/third_party/emhash/README.ninja |
| `sources/metadata-ninja-pypi-1.7.2.json` | `194e68604269…` | https://pypi.org/pypi/ninja/1.7.2/json |
| `sources/metadata-ninja-emhash-licence-header.txt` | `a0232916dc02…` | https://files.pythonhosted.org/packages/43/73/79a0b22fc731989c708068427579e840a6cf4e937fe7ae5c5d0b7356ac22/ninja-1.13.0.tar.gz#ninja-upstream/src/third_party/emhash/hash_table8.hpp (lines 1-25) |

### Proposed obligation

Ship, alongside the wheel and its bundled LICENSE_Apache_20 and AUTHORS.rst, the rapidhash BSD-2-Clause notice (copyright line, both conditions and the disclaimer) from sources/metadata-ninja-rapidhash-licence-header.txt: rapidhash code is compiled into ninja-1.13.0.data/scripts/ninja, and the licence asks binary redistributions to reproduce the notice in the documentation or other materials; the wheel carries no copy. Because emhash (MIT) is compiled into the same binary and is not declared, also ship its MIT notice from sources/metadata-ninja-emhash-licence-header.txt.

### Uncertainty

- The BSD classifier is already in the ninja 1.7.2 metadata (2016; retained PyPI JSON), long before ninja vendored rapidhash. The classifier names no variant and its original basis was not established: rapidhash accounts for a BSD-licensed component in this wheel, which may not be the reason the maintainers added the classifier.
- The binary is stripped. That rapidhash ships rests on the Linux source set (files including hash_map.h, and build_log.cc, call rapidhash()) and on its three 64-bit secret constants occurring in the binary. The same constants also appear in the emhash header, but only under EMH_WYHASH_HASH, which no other ninja-upstream file mentions.
- The wheel was not rebuilt from these sources. The link between the shipped binary and the sdist and submodule sources rests on the kNinjaVersion string (sdist, submodule commit and binary agree) and on the commit hash abbreviated in the wheel README.
- emhash presence rests on source evidence only (header-only template code; no distinctive marker in the stripped binary).
- Not examined: toolchain runtime code statically linked by the manylinux2014 toolchain (GCC 10.2.1 and 4.8.5 ident strings in the binary) and its terms.

### Other observations

- emhash8::HashMap 1.6.5 (Copyright (c) 2021-2024 Huang Yuanbing & bailuzhou), vendored at ninja-upstream/src/third_party/emhash/ — MIT (SPDX identifier in README.ninja and the header; full MIT wording in the header) — compiled into the binary per the Linux source set; licence not declared in the metadata; text retained at sources/metadata-ninja-emhash-licence-header.txt
- ninja-upstream/src/getopt.c (public domain) — not compiled on Linux: CMakeLists adds it only under WIN32 and OS400/AIX
- embedded browse.py text — the licence strings in the binary all come from src/browse.py (Apache-2.0, Google)

## regex 2026.4.4

- Wheel: `regex-2026.4.4-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl` (sha256 `993f657a7c1c6ec51b5e0ba97c9817d06b84ea5fa8d82e43b9405de0defdc2b9`), opened after hash verification against the approved manifest.
- Declared: License-Expression: Apache-2.0 AND CNRI-Python; License-File: LICENSE.txt
- Detected in the wheel's licence documents (inventory): Apache-2.0
- Extra declared licence: CNRI-Python (License-Expression "Apache-2.0 AND CNRI-Python")
- **Classification: explained**

### Licence documents in the wheel

| Path | SHA-256 | Licence signals |
|---|---|---|
| `regex-2026.4.4.dist-info/licenses/LICENSE.txt` | `bff55ef4cdcc…` | text: Apache-2.0; reference: Apache-2.0, CNRI-Python; spdx: — |

### Files searched

- Wheel: 10 files; 9 text files scanned for licence headers (first 4000 characters), licence documents read in full; 1 compiled file(s) scanned for embedded licence strings.
  - `regex/_main.py` (`240a36c133d8…`, header lines 1-14): text: —; reference: CNRI-Python; spdx: —
  - `regex/_regex_core.py` (`a8378b9e67b7…`, header lines 1-14): text: —; reference: CNRI-Python; spdx: —
  - compiled `regex/_regex.cpython-312-x86_64-linux-gnu.so` (`34cacc9e637c…`): "RE 2.3.0 Copyright (c) 1997-2002 by Secret Labs AB"; "copyright"
- Sdist `regex-2026.4.4.tar.gz` (sha256 `e08270659717f6973523ce3afbafa53515c4dc5dcad637dc215b6fd50f689423`, verified against PyPI): 22 files, 22 text files scanned. Licence documents: `LICENSE.txt` (text: Apache-2.0; reference: Apache-2.0, CNRI-Python; spdx: —).
  Members whose header carries a licence signal other than Apache-2.0:
  - `LICENSE.txt`: text: Apache-2.0; reference: Apache-2.0, CNRI-Python; spdx: —
  - `PKG-INFO`: text: —; reference: Apache-2.0, CNRI-Python; spdx: —
  - `docs/Features.html`: text: —; reference: public-domain; spdx: —
  - `pyproject.toml`: text: —; reference: Apache-2.0, CNRI-Python; spdx: —
  - `regex.egg-info/PKG-INFO`: text: —; reference: Apache-2.0, CNRI-Python; spdx: —
  - `regex/_main.py`: text: —; reference: CNRI-Python; spdx: —
  - `regex/_regex_core.py`: text: —; reference: CNRI-Python; spdx: —
  - `src/_regex.c`: text: —; reference: CNRI-Python; spdx: —

### Component carrying the extra licence

**SRE regular expression engine (Copyright (c) 1997-2001 Secret Labs AB), from CPython 2.6/3.1's re module, from which regex derives**, licence CNRI's Python 1.6 license (source headers); declared as SPDX CNRI-Python.

- Ships in the wheel: `regex/_main.py` (sha256 `240a36c133d858f336ccff3b2c6dd4060e9da673f2f469e611a4807d0ce69e9b`)
- Ships in the wheel: `regex/_regex_core.py` (sha256 `a8378b9e67b747e5490c898656a4ba23672afa3772d3ec3ce976a5f2348d0c7a`)
- Ships in the wheel: `regex/_regex.cpython-312-x86_64-linux-gnu.so` (sha256 `34cacc9e637c15a55befb51f938312762b0955010b292e10413a9be068870a24`); embeds "RE 2.3.0 Copyright (c) 1997-2002 by Secret Labs AB" from src/_regex.c: True
- The compiled module is built from src/_regex.c, src/_regex_unicode.c (setup.py).
- Wheel files identical to the sdist: `regex/_main.py` yes, `regex/_regex_core.py` yes, `regex-2026.4.4.dist-info/licenses/LICENSE.txt` yes.
- CPython 3.1 Modules/_sre.c carries the same statement: True.

### Licence text location

- In the wheel: no: LICENSE.txt names "CNRI's Python 1.6 license" in its first paragraph but carries only the Apache-2.0 text
- In the sdist: no (same LICENSE.txt)
- Upstream: SPDX license-list-data v3.27.0 `text/CNRI-Python.txt`. CPython v2.6 (tag carries the version: True; contains the CNRI 1.6.1 agreement: True); v3.1 (tag carries the version: True; contains the CNRI 1.6.1 agreement: True).
- SPDX CNRI-Python clause 2 (excerpt): "2. Subject to the terms and conditions of this License Agreement, CNRI hereby grants Licensee a non-exclusive, royalty-free, world-wide license to reproduce, analyze, test, perform and/or display publicly, prepare derivative works, distribute, and otherwise use Python 1.6b1 alone or in any derivative version, provided, however, that CNRIs License Agreement is retained in Python 1.6b1, alone or in any derivative version prepared by Licensee. Alternately, in lieu of CNRIs License Agreement, Licensee may substitute the following text (omitting the quotes): "Python 1.6, beta 1, is made available subject to the terms and conditions in CNRIs License Agreement. This Agreement may be located on the Internet using the following unique, persistent identifier (known as a handle): 1895.22/1011. This Agreement may also be obtained from a proxy server on the Internet using the URL:http://hdl.handle.net/1895.22/1011"."

| Retained file | SHA-256 | Source |
|---|---|---|
| `sources/metadata-regex-spdx-v3.27.0-CNRI-Python.txt` | `69b5d7d41a6e…` | https://raw.githubusercontent.com/spdx/license-list-data/v3.27.0/text/CNRI-Python.txt |
| `sources/metadata-regex-cpython-v3.1-LICENSE.txt` | `1524dab343bf…` | https://raw.githubusercontent.com/python/cpython/v3.1/LICENSE |
| `sources/metadata-regex-cpython-v2.6-LICENSE.txt` | `f7a0d9a43d04…` | https://raw.githubusercontent.com/python/cpython/v2.6/LICENSE |
| `sources/metadata-regex-_main.py-licence-header.txt` | `98770cca405b…` | https://files.pythonhosted.org/packages/11/0e/a9f6f81013e0deaf559b25711623864970fe6a098314e374ccb1540a4152/regex-2026.4.4-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl#regex/_main.py (lines 1-14) |
| `sources/metadata-regex-_regex.c-licence-header.txt` | `d84fdfa5c7f3…` | https://files.pythonhosted.org/packages/cb/0e/3a246dbf05666918bd3664d9d787f84a9108f6f43cc953a077e4a7dfdb7e/regex-2026.4.4.tar.gz#src/_regex.c (lines 1-36) |
| `sources/metadata-regex-cpython-v2.6-patchlevel.h` | `1d4580050ece…` | https://raw.githubusercontent.com/python/cpython/v2.6/Include/patchlevel.h |
| `sources/metadata-regex-cpython-v3.1-patchlevel.h` | `d9bc4cd0be8b…` | https://raw.githubusercontent.com/python/cpython/v3.1/Include/patchlevel.h |
| `sources/metadata-regex-cpython-v3.1-_sre.c-licence-header.txt` | `392f2606f135…` | https://raw.githubusercontent.com/python/cpython/v3.1/Modules/_sre.c (lines 1-35) |
| `sources/metadata-regex-cpython-tags-v1.6.json` | `bf97bc46f86c…` | https://api.github.com/repos/python/cpython/git/matching-refs/tags/v1.6 |

### Proposed obligation

Ship, alongside the wheel and its bundled LICENSE.txt, a copy of the CNRI licence text. Proposed: sources/metadata-regex-spdx-v3.27.0-CNRI-Python.txt (the text of the declared SPDX identifier, which in clause 2 asks that the CNRI agreement be retained in any derivative version). The reviewer may instead or also choose the CPython licence file (sources/metadata-regex-cpython-v3.1-LICENSE.txt), which carries the CNRI agreement for Python 1.6.1 within the PSF licence history. The Secret Labs AB copyright notices already ship in the headers of regex/_main.py and regex/_regex_core.py; keep those files unmodified.

### Uncertainty

- "CNRI's Python 1.6 license" in the headers does not pin a text: SPDX CNRI-Python is worded for Python 1.6b1, CPython 2.6/3.1 carry the agreement for Python 1.6.1, and the Python 1.6 final text was not retrieved (the CPython repository has tags v1.6a1, v1.6a2 only, no v1.6 final). Which text satisfies the headers is for the reviewer.
- regex derives from the re module of CPython 2.6 and 3.1. Changes made inside CPython between 2001 and 2009 may fall under the PSF licence history, which the declared expression does not name. Not resolved.
- src/_regex_unicode.c, compiled into the module, holds tables generated from the Unicode Character Database 17.0.0 (tools/build_regex_unicode.py). Whether Unicode data licence terms apply was not examined.

### Other observations

- src/_regex.h (sdist only, compiled in) carries the Secret Labs AB copyright line without the CNRI statement

## prometheus_client 0.25.0

- Wheel: `prometheus_client-0.25.0-py3-none-any.whl` (sha256 `d5aec89e349a6ec230805d0df882f3807f74fd6c1a2fa86864e3c2279059fed1`), opened after hash verification against the approved manifest.
- Declared: License-Expression: Apache-2.0 AND BSD-2-Clause; License-File: LICENSE; License-File: NOTICE
- Detected in the wheel's licence documents (inventory): Apache-2.0
- Extra declared licence: BSD-2-Clause (License-Expression "Apache-2.0 AND BSD-2-Clause")
- **Classification: explained**

### Licence documents in the wheel

| Path | SHA-256 | Licence signals |
|---|---|---|
| `prometheus_client-0.25.0.dist-info/licenses/LICENSE` | `c71d239df917…` | text: Apache-2.0; reference: Apache-2.0; spdx: — |
| `prometheus_client-0.25.0.dist-info/licenses/NOTICE` | `4efa1874aeaa…` | text: —; reference: BSD-2-Clause; spdx: — |

### Files searched

- Wheel: 37 files; 37 text files scanned for licence headers (first 4000 characters), licence documents read in full; 0 compiled file(s) scanned for embedded licence strings.
  - `prometheus_client/decorator.py` (`ecc754a245a6…`, header lines 1-28): text: BSD-2-Clause-style; reference: —; spdx: —
- Sdist `prometheus_client-0.25.0.tar.gz` (sha256 `5e373b75c31afb3c86f1a52fa1ad470c9aace18082d39ec0d2f918d11cc9ba28`, verified against PyPI): 68 files, 68 text files scanned. Licence documents: `LICENSE` (text: Apache-2.0; reference: Apache-2.0; spdx: —), `NOTICE` (text: —; reference: BSD-2-Clause; spdx: —).
  Members whose header carries a licence signal other than Apache-2.0:
  - `NOTICE`: text: —; reference: BSD-2-Clause; spdx: —
  - `PKG-INFO`: text: —; reference: Apache-2.0, BSD-2-Clause; spdx: —
  - `prometheus_client.egg-info/PKG-INFO`: text: —; reference: Apache-2.0, BSD-2-Clause; spdx: —
  - `prometheus_client/decorator.py`: text: BSD-2-Clause-style; reference: —; spdx: —
  - `pyproject.toml`: text: —; reference: Apache-2.0, BSD-2-Clause; spdx: —

### Component carrying the extra licence

**decorator 4.0.10 (Copyright (c) 2005-2016, Michele Simionato), vendored as prometheus_client/decorator.py**, licence BSD-style 2-clause licence (header of the vendored file; "bytecode form" wording).

- Ships in the wheel: `prometheus_client/decorator.py` (sha256 `ecc754a245a6cd0d7b7e87add91e5070cb9b759d560cf198a34fc7a8bc40c369`)
- Imported by: prometheus_client/context_managers.py. NOTICE points to it: True. Wheel files identical to the sdist: `prometheus_client/decorator.py` yes, `prometheus_client-0.25.0.dist-info/licenses/NOTICE` yes, `prometheus_client-0.25.0.dist-info/licenses/LICENSE` yes.
- Upstream decorator release `decorator-4.0.10.tar.gz` (sha256 `9c6e98edcb33499881b86ede07d9968c81ab7c769e28e9af24075f0a5379f070`, verified against PyPI): vendored file identical to upstream src/decorator.py: False.

### Licence text location

- In the wheel: yes: prometheus_client/decorator.py lines 1-28 (the licence text itself), pointed to by the bundled NOTICE; the inventory read only dist-info/licenses/ and so did not see it
- In the sdist: yes (same file and NOTICE)
- Upstream: decorator 4.0.10 LICENSE.txt

| Retained file | SHA-256 | Source |
|---|---|---|
| `sources/metadata-prometheus_client-decorator-licence-header.txt` | `d2687c072a1d…` | https://files.pythonhosted.org/packages/8d/9b/d4b1e644385499c8346fa9b622a3f030dce14cd6ef8a1871c221a17a67e7/prometheus_client-0.25.0-py3-none-any.whl#prometheus_client/decorator.py (lines 1-28) |
| `sources/metadata-prometheus_client-NOTICE.txt` | `4efa1874aeaa…` | https://files.pythonhosted.org/packages/8d/9b/d4b1e644385499c8346fa9b622a3f030dce14cd6ef8a1871c221a17a67e7/prometheus_client-0.25.0-py3-none-any.whl#prometheus_client-0.25.0.dist-info/licenses/NOTICE |
| `sources/metadata-prometheus_client-decorator-4.0.10-LICENSE.txt` | `fd065f714547…` | https://files.pythonhosted.org/packages/13/8a/4eed41e338e8dcc13ca41c94b142d4d20c0de684ee5065523fee406ce76f/decorator-4.0.10.tar.gz#LICENSE.txt |

### Proposed obligation

Ship the wheel unmodified: prometheus_client/decorator.py carries the licence text in its header and the bundled NOTICE points to it. Where licence documents are collected separately from the wheel, add the decorator notice from sources/metadata-prometheus_client-decorator-licence-header.txt beside LICENSE and NOTICE. If the module is ever redistributed only as bytecode, the licence asks for the notice in the accompanying documentation.

### Uncertainty

- The licence says "Redistributions in bytecode form" where SPDX BSD-2-Clause says "binary form". The declared identifier is close to the text but not verbatim. Whether SPDX matching treats it as BSD-2-Clause was not checked.
- The vendored file differs from decorator 4.0.10 src/decorator.py (formatting and Python 3 changes). The file does not state the licence of the Prometheus authors' changes; presumably it is the project licence (Apache-2.0).
- Licence header differences from upstream src/decorator.py: none. Upstream LICENSE.txt gives the years as 2005-2015.
