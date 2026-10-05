"""Artifact-specific PROPOSED redistribution dispositions for every R2 wheel (review preparation only).

These are proposals prepared for the designated reviewer, not decisions: nothing here is written to the human-owned
decisions file, and no row is proposed as plainly `approved`. Each proposal names the artifact's own licence
documents and hashes (from the generated inventory), the clauses or facts relied on, the questions the reviewer must
resolve and, where an artifact may not be clearable, an explicit alternative (never a silent omission: every artifact
is a required dependency of the approved manifest).

Batch 1 covers the 43 flagged artifacts, using reports/wheelhouse_nvidia_licence_reconciliation.json for the NVIDIA
wheels. Batch 2 covers the 131 unflagged artifacts by a stated rule: the declared licence metadata is compared with
the licence families detected in the wheel's own documents.

  python scripts/propose_wheelhouse_dispositions.py
Outputs reports/wheelhouse_redistribution_proposed_dispositions.{csv,md}; exits 1 if a flagged artifact lacks a
proposal or a proposal names an artifact that is not in the inventory.
"""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_CSV = ROOT / 'reports/wheelhouse_redistribution_inventory.csv'
UPSTREAM_INDEX = ROOT / 'reports/wheelhouse_upstream_licenses/index.json'
RECONCILIATION = ROOT / 'reports/wheelhouse_nvidia_licence_reconciliation.json'
OUT_CSV = ROOT / 'reports/wheelhouse_redistribution_proposed_dispositions.csv'
OUT_MD = ROOT / 'reports/wheelhouse_redistribution_proposed_dispositions.md'
PREPARED_ON = '2026-10-04'
PREPARED_BY = 'Claude (assistant), for the designated reviewer; proposal only'
FIELDS = ['artifact', 'sha256', 'flags', 'batch', 'group', 'proposed_disposition', 'proposed_conditions', 'evidence',
          'rationale', 'questions_for_reviewer', 'alternative_if_not_cleared', 'prepared_by', 'prepared_on']
PROPOSED_VALUES = {'approved_with_conditions', 'needs_qualified_review', 'likely_not_distributable'}

EULA_CLAUSES = ('Bundled text: the older CUDA EULA License.txt (sha256 ad6f5853…) shared by eleven CUDA wheels. '
                'Version-specific primary source: the official CUDA 12.8.1 EULA (retained in '
                'reports/wheelhouse_primary_licence_sources/). Both: 1.1.1(3) distribution only of portions identified '
                'as distributable, incorporated into an application; 1.1.2(1)-(2) the application must add material '
                'functionality and be the only accessor; no distribution as a stand-alone product; 2.3 Linux portions '
                'redistributed unmodified; 2.5 licensing contact nvidia-compute-license-questions@nvidia.com')
NVIDIA_QUESTION = ('Which text governs: the licence bundled in the wheel or the official version-specific EULA? Is a '
                   'private Kaggle dataset, attached only to the team\'s own notebook (the ARC-AGI-3 agent, the '
                   'application), distribution "incorporated into a software application", or distribution "as a '
                   'stand-alone product"? Private access is not a substitute for redistribution clearance.')
NVIDIA_ALTERNATIVE = ('Do not redistribute until resolved. Options for the owner to choose explicitly: (a) written '
                      'clarification from NVIDIA via the licensing contact; (b) a new runtime revision using libraries '
                      'preinstalled in the Kaggle image, only after their exact versions are established and shown to '
                      'satisfy both the runtime and the package requirements (a new manifest, closure, download and '
                      'install check; never a silent substitution); (c) record the bundle as blocked. Never dropped '
                      'silently.')
REVISION_NOTE = ('removal is possible only through an explicitly revised dependency set with fresh validation (new '
                 'manifest, closure, download and offline install check), never because an inference path seems not '
                 'to use it')


def p(group, disposition, conditions, rationale, questions, alternative='', evidence=''):
    return {'group': group, 'proposed_disposition': disposition, 'proposed_conditions': conditions,
            'rationale': rationale, 'questions_for_reviewer': questions, 'alternative_if_not_cleared': alternative,
            'extra_evidence': evidence}


def cuda_component(component):
    return p('NVIDIA CUDA Toolkit EULA', 'needs_qualified_review',
             'if cleared: ship License.txt unmodified; files unmodified (2.3); no NVIDIA endorsement claim',
             f'{component} is listed as distributable in Attachment A of both the bundled text and the official 12.8.1 '
             'EULA, but only as incorporated into an application; a wheelhouse dataset may be a stand-alone '
             'distribution.', NVIDIA_QUESTION, NVIDIA_ALTERNATIVE, EULA_CLAUSES)


def cuda_discrepancy(component, official_files):
    return p('NVIDIA CUDA Toolkit EULA: applicability discrepancy', 'needs_qualified_review',
             'if cleared: ship License.txt unmodified and record which EULA text governs; files unmodified',
             f'Applicability discrepancy requiring review: the bundled License.txt has no {component} entry in '
             f'Attachment A, but the official CUDA 12.8.1 EULA Attachment A lists {official_files} as distributable. '
             'This is neither a finding that no grant exists nor a grant; the distribution conditions still apply.',
             NVIDIA_QUESTION + ' Does the official 12.8.1 listing apply to this wheel although its bundled text '
             'omits the component?', NVIDIA_ALTERNATIVE, EULA_CLAUSES)


PROPOSALS = {
    # NVIDIA CUDA Toolkit EULA family
    'nvidia_cublas_cu12': cuda_component('CUDA BLAS (libcublas, libcublasLt)'),
    'nvidia_cuda_cupti_cu12': cuda_component('CUPTI (libcupti)'),
    'nvidia_cuda_nvrtc_cu12': cuda_component('NVRTC (libnvrtc, libnvrtc-builtins)'),
    'nvidia_cuda_runtime_cu12': cuda_component('CUDA Runtime (libcudart)'),
    'nvidia_cufft_cu12': cuda_component('cuFFT (libcufft, libcufftw)'),
    'nvidia_curand_cu12': cuda_component('cuRAND (libcurand)'),
    'nvidia_cusolver_cu12': cuda_component('cuSOLVER (libcusolver)'),
    'nvidia_cusparse_cu12': cuda_component('cuSPARSE (libcusparse)'),
    'nvidia_cufile_cu12': cuda_discrepancy('cuFile', 'libcufile.so, libcufile_rdma.so and their static libraries'),
    'nvidia_nvjitlink_cu12': cuda_discrepancy('nvJitLink', 'libnvJitLink.so and libnvJitLink_static.a'),
    'nvidia_nvshmem_cu12': p(
        'NVSHMEM: separate product terms', 'needs_qualified_review',
        'if cleared: ship the governing licence text (record which) and the NVSHMEM third-party notices; files '
        'unmodified',
        'The wheel bundles the CUDA Toolkit EULA, which does not mention NVSHMEM. The version-specific source, '
        'License.txt at NVIDIA/nvshmem tag v3.4.5-0, is the NVIDIA SDK licence plus an NVSHMEM supplement whose '
        'section 2 makes "any portion of the SDK" distributable, still subject to the SDK distribution requirements '
        '(incorporated into an application with material additional functionality, accessed only by it; no '
        'stand-alone distribution). GitHub metadata reports Apache-2.0 for the default branch, unlike the tag text.',
        NVIDIA_QUESTION + ' Does the NVSHMEM supplement or the bundled CUDA EULA govern this wheel? Do the bundled '
        'third-party notices in the tag\'s License.txt (DF-NVSHMEM-prototype and others) need to ship?',
        NVIDIA_ALTERNATIVE),
    # Other NVIDIA SLAs
    'nvidia_cudnn_cu12': p(
        'NVIDIA cuDNN SLA', 'needs_qualified_review', 'if cleared: ship License.txt unmodified; files unmodified',
        'cuDNN SLA (sha256 49cf79bd…) 1.1(iii)/1.2: distributable runtime .so and .h files only as incorporated into '
        'an application with material additional functionality; same stand-alone question as the CUDA EULA. The '
        'version-specific primary SLA for 9.10.2 has not yet been retained and compared.', NVIDIA_QUESTION,
        NVIDIA_ALTERNATIVE),
    'nvidia_cusparselt_cu12': p(
        'NVIDIA cuSPARSELt SLA', 'needs_qualified_review', 'if cleared: ship LICENSE.txt unmodified; files unmodified',
        'cuSPARSELt SLA (sha256 e8d15888…) 1.1(iii)/1.2 and section 2: runtime .so and .h files distributable "as '
        'part of your application"; 2.2 forbids stand-alone distribution. The version-specific primary SLA for 0.7.1 '
        'has not yet been retained and compared.', NVIDIA_QUESTION, NVIDIA_ALTERNATIVE),
    'nvidia_cutlass_dsl_libs_base': p(
        'NVIDIA CUTLASS DSL EULA', 'likely_not_distributable', 'only with a grant identified by the reviewer or NVIDIA',
        'The bundled LICENSE is byte-identical to EULA.txt at NVIDIA/cutlass tags v4.2.0 through v4.5.0 (sha256 '
        '9ed3a034…), so it is the primary text. Its 1.1(d) permits distributing only "python files ... in source '
        'format" incorporated into an application; the wheel also ships compiled files (libcute_dsl_runtime.so, '
        '_cutlass_ir.cpython-312-x86_64-linux-gnu.so, libcuda_dialect_runtime_static.a) that no identified grant '
        'covers; 2.2 forbids making it available to others except authorized users. It is a required dependency: '
        'flashinfer-python==0.6.6 requires nvidia-cutlass-dsl>=4.3.4 and quack-kernels==0.4.1 requires >=4.4.2.',
        'Is any grant available for the compiled files? Are Kaggle notebook viewers "authorized users" under '
        'section 3?',
        'Owner chooses explicitly: NVIDIA clarification; or an explicitly revised dependency set ('
        f'{REVISION_NOTE}); or record the bundle as blocked.'),
    'nvidia_cutlass_dsl': p(
        'NVIDIA CUTLASS DSL EULA', 'needs_qualified_review', 'if cleared: ship LICENSE unmodified',
        'Metadata-only wheel (dist-info plus one .txt) under the same CUTLASS DSL EULA (sha256 9ed3a034…, identical '
        'to the tagged EULA.txt); it ships no NVIDIA code itself but depends on nvidia-cutlass-dsl-libs-base, and is '
        'required by flashinfer-python==0.6.6 and quack-kernels==0.4.1.',
        'Follow the decision for nvidia_cutlass_dsl_libs_base; is redistributing the metadata wheel alone within '
        '1.1(d)?', f'As for nvidia_cutlass_dsl_libs_base ({REVISION_NOTE}).'),
    'cuda_python': p(
        'NVIDIA Software License (cuda-python)', 'approved_with_conditions',
        'ship LICENSE unmodified; dataset description states that the NVIDIA Software License governs these wheels '
        'and that no NVIDIA endorsement is implied',
        'NVIDIA Software License (sha256 25a91d6e…) section 1(b) grants distribution subject to section 2: terms '
        'consistent with the licence, and notice to NVIDIA of known non-compliance. No application-incorporation '
        'requirement; no modification is made.',
        'Is a dataset description plus the shipped LICENSE sufficient to make the distribution terms "consistent"? '
        'Accept 3(a) (applications only for NVIDIA-GPU systems)? Is a version-specific primary text needed?',
        NVIDIA_ALTERNATIVE),
    'cuda_bindings': p(
        'NVIDIA Software License (cuda-python)', 'approved_with_conditions',
        'ship LICENSE unmodified; dataset description as for cuda_python',
        'LICENSE is byte-identical to cuda_python\'s (sha256 25a91d6e…); same grant in section 1(b) and '
        'requirements in section 2.', 'As for cuda_python.', NVIDIA_ALTERNATIVE),
    'nvidia_cudnn_frontend': p(
        'Permissive under a proprietary classifier', 'approved_with_conditions',
        'ship LICENSE.txt and thirdparty/nlohmann/LICENSE.MIT',
        'The licence document (sha256 3fc4b473…) is the MIT licence; the "NVIDIA Proprietary Software" classifier is '
        'the only proprietary signal. The wheel includes a compiled module (_compiled_module.cpython-312 .so).',
        'Confirm that the MIT text governs the whole wheel, including the compiled module, despite the classifier.'),
    'nvidia_nccl_cu12': p(
        'Permissive under a proprietary classifier', 'approved_with_conditions', 'ship License.txt',
        'The licence document (sha256 0f0174a6…) is BSD-3-Clause; only the "Other/Proprietary" classifier is '
        'proprietary.', 'Confirm that BSD-3-Clause governs the binary libnccl in this wheel despite the classifier.'),
    'nvidia_nvtx_cu12': p(
        'Permissive under a proprietary classifier', 'approved_with_conditions', 'ship License.txt',
        'The licence document (sha256 9e45e856…) is Apache-2.0; only the "Other/Proprietary" classifier is '
        'proprietary.', 'Confirm Apache-2.0 governs; is there an upstream NOTICE file that 4(d) requires?'),
    'torch': p(
        'BSD with third-party listings', 'approved_with_conditions', 'ship LICENSE and NOTICE unmodified',
        'Declared BSD-3-Clause. The NVIDIA-proprietary signals are third-party listings: the CUTLASS repository '
        'note that python/CuTeDSL is under the NVIDIA EULA, and a LicenseRef-NvidiaProprietary header listed under '
        'third_party/fbgemm/.../hstu. A name check of the wheel\'s 11,780 members found no CuTeDSL or hstu files. '
        'The GPL/LGPL texts are likewise third-party listings.',
        'Confirm that no shipped file is under NVIDIA proprietary terms (the name check is not a content audit) '
        'and that no listed LGPL/GPL component is shipped in a way that needs more than these notices.'),
    'numba': p(
        'BSD with vendored CUDA headers', 'approved_with_conditions', 'ship LICENSE and LICENSES.third-party',
        'Declared BSD. The proprietary signal is numba/cuda/cuda_fp16.h and .hpp, vendored from CUDA 11.2.2 and '
        'stated in LICENSES.third-party to be Attachment A distributable; they ship as part of numba, which adds '
        'material functionality.', 'Confirm that the vendored headers satisfy the CUDA 11.2.2 EULA when shipped '
        'inside unmodified numba, and that the GPL text in LICENSES.third-party concerns no shipped component.'),
    # Declared copyleft
    'certifi': p(
        'Declared MPL-2.0', 'approved_with_conditions',
        'ship LICENSE; README/NOTICES point to the Source Code Form (the PyPI sdist of this exact version)',
        'MPL-2.0; the wheel is unmodified and already in Source Code Form (Python plus cacert.pem), so 3.1/3.2 are '
        'met by shipping the licence and identifying where the source is available.',
        'Confirm that shipping the licence and a source pointer meets MPL-2.0 for unmodified redistribution.'),
    'tqdm': p(
        'Declared MPL-2.0 AND MIT', 'approved_with_conditions',
        'ship LICENCE (both texts); README/NOTICES point to the PyPI sdist', 'MPL-2.0 and MIT; pure Python, '
        'unmodified, in Source Code Form.', 'As for certifi.'),
    'pycountry': p(
        'Declared LGPL-2.1-only', 'approved_with_conditions',
        'ship LICENSE.txt and COPYRIGHT.txt; README/NOTICES point to the PyPI sdist for complete source',
        'LGPL-2.1-only; pure Python plus ISO data files, unmodified, so the shipped files are the source; no '
        'linking or modification by us.', 'Confirm LGPL-2.1 section 1 (verbatim copies of source with the licence) '
        'covers this, and that the bundled iso-codes data files carry no extra terms.'),
    'shellingham': p(
        'Unrecognised text (ISC)', 'approved_with_conditions', 'ship LICENSE',
        'Read manually: the text is the ISC licence ("Permission to use, copy, modify, and distribute this '
        'software for any purpose with or without fee is hereby granted, provided that the above copyright notice '
        'and this permission notice appear in all copies"), matching the ISC metadata; the automatic matcher missed '
        'this wording.', 'Confirm the classification.'),
    # Copyleft text present only
    'aiohappyeyeballs': p(
        'False copyleft signal', 'approved_with_conditions', 'ship LICENSE',
        'PSF-2.0; the GPL mention is the PSF history table ("most ... Python releases have also been '
        'GPL-compatible"), not a copyleft licence.', 'Confirm.'),
    'typing_extensions': p(
        'False copyleft signal', 'approved_with_conditions', 'ship LICENSE',
        'PSF-2.0; the GPL mention is the PSF history table, as for aiohappyeyeballs.', 'Confirm.'),
    'setuptools': p(
        'Vendored MPL-2.0 source', 'approved_with_conditions',
        'ship all bundled licence documents; README/NOTICES point to the PyPI sdist',
        'MIT; vendored validate-pyproject files are MPL-2.0 and ship unmodified in Source Code Form.',
        'Confirm; identify the source of the LGPL signal and whether it concerns a shipped file.'),
    'grpcio': p(
        'Bundled MPL-2.0 data', 'approved_with_conditions',
        'ship all bundled licence documents; README/NOTICES point to the source of etc/roots.pem',
        'Apache-2.0; etc/roots.pem is under MPL-2.0 and ships unmodified as a text file (its own source form).',
        'Confirm; identify what the LGPL signal refers to and whether it concerns a shipped binary.'),
    'numpy': p(
        'Bundled runtime libraries', 'approved_with_conditions', 'ship all bundled licence documents',
        'BSD-3-Clause; bundled libgfortran is GPL-3.0 with the GCC Runtime Library Exception, which permits '
        'redistribution with the notices.', 'Confirm the GCC exception applies to the bundled libgfortran and '
        'libquadmath; identify the LGPL signal\'s component.'),
    'pyzmq': p(
        'Bundled MPL-2.0 binary', 'needs_qualified_review',
        'ship all bundled licence documents; README/NOTICES state where the Source Code Form of the bundled libzmq '
        '(libzmq.so.5.2.5, i.e. libzmq 4.3.x) is available',
        'BSD-3-Clause; the wheel bundles a compiled libzmq under MPL-2.0 (Executable Form) and libsodium (ISC). '
        'MPL-2.0 3.2(a) requires informing recipients how to obtain the Source Code Form.',
        'Which libzmq release and source location must be cited? Is a pointer sufficient, or must the source be '
        'shipped? Any LGPL-licensed component?'),
    'pillow': p(
        'Bundled binaries with dual-licensed components', 'needs_qualified_review',
        'ship all bundled licence documents; record which option of each dual-licensed bundled library is relied on',
        'MIT-CMU; bundles compiled libraries (e.g. libfreetype, libharfbuzz, libavif, libbrotli). FreeType is '
        'FTL or GPLv2; relying on FTL requires a credit in the documentation.',
        'Confirm FTL is elected and the credit wording; identify any LGPL-only bundled library and its '
        'obligations.'),
    'opencv_python_headless': p(
        'Bundled LGPL binaries', 'needs_qualified_review',
        'ship all bundled licence documents; provide (or offer in writing) the corresponding source for the bundled '
        'LGPL libraries (FFmpeg libavcodec/libavformat/libavutil/libswresample and any others); README/NOTICES '
        'state this',
        'Apache-2.0 for OpenCV, but the wheel bundles FFmpeg shared libraries (libavcodec.so.62, libavformat.so.62, '
        'libavutil.so.60, libswresample.so.6) under LGPL-2.1 per its licence document, plus OpenSSL 1.1.1k and '
        'libgfortran. Redistributing LGPL binaries needs the licence text and the corresponding source (or a '
        'written offer); shared linking satisfies relinking.',
        'Exactly which bundled libraries are LGPL (or GPL)? Is a pointer to the opencv-python release sources '
        'sufficient, or must the FFmpeg source be shipped? OpenSSL 1.1.1k notice requirements?',
        'If the source obligation cannot be met: the owner chooses between shipping the corresponding sources in '
        f'the bundle, or an explicitly revised dependency set ({REVISION_NOTE}).'),
}

# Batch 2: declared-licence tokens -> detected family names (from the licence extractor)
DECLARED = [(r'\bmit\b', 'MIT'), (r'apache', 'Apache-2.0'), (r'bsd-3|3-clause|new bsd', 'BSD-3-Clause'),
            (r'bsd-2|2-clause|simplified bsd', 'BSD-2-Clause'), (r'\bisc\b', 'ISC'), (r'unlicense', 'Unlicense'),
            (r'cc0', 'CC0'), (r'cnri-python', 'CNRI-Python'), (r'\bpsf|python software foundation', 'PSF-2.0'),
            (r'\bzlib\b', 'Zlib')]
GENERIC_BSD = re.compile(r'\bbsd\b', re.I)


def declared_families(text):
    """(families, operator) from licence metadata: 'OR' when the SPDX expression offers a choice, else 'AND'."""
    found = []
    for pattern, family in DECLARED:
        if re.search(pattern, text, re.I) and family not in found:
            found.append(family)
    if GENERIC_BSD.search(text) and not any(f.startswith('BSD-') for f in found):
        found.append('BSD-any')
    return found, ('OR' if re.search(r'\bOR\b', text) else 'AND')


def unflagged_proposal(r):
    detected = [f for f in r['detected_families'].split(', ') if f]
    declared, operator = declared_families(r['metadata_declared'])
    present = lambda f: (any(d.startswith('BSD-') for d in detected) if f == 'BSD-any' else f in detected)  # noqa
    docs = [d for d in r['licence_documents'].split('; ') if d and d != 'none in wheel']
    has_notice = any(re.search(r'(?i)notice', Path(d).name) for d in docs)
    conditions = 'ship the bundled licence document(s) unmodified: ' + ', '.join(docs)
    questions = []
    if 'Apache-2.0' in detected and not has_notice:
        questions.append('Apache-2.0 with no NOTICE file in the wheel: confirm no upstream NOTICE must accompany it '
                         '(4(d) concerns NOTICE files that are part of the Work as distributed).')
    if 'Apache-2.0' in detected and has_notice:
        conditions += '; keep the NOTICE file (Apache-2.0 4(d))'
    extra = sorted(set(detected) - set(declared))
    if not declared:
        return p('Batch 2: no declared licence', 'needs_qualified_review', conditions,
                 f"No licence in the metadata; the wheel's documents show {', '.join(detected)}.",
                 ' '.join(['Confirm the licence from the documents alone.'] + questions))
    missing = [f for f in declared if not present(f)]
    consistent = (not missing) if operator == 'AND' else any(present(f) for f in declared)
    if not consistent:
        return p('Batch 2: declared licence not found in documents', 'needs_qualified_review', conditions,
                 f"Declared {r['metadata_declared']!r} ({operator}); the wheel's documents show "
                 f"{', '.join(detected)}; not found: {', '.join(missing)}.",
                 ' '.join([f"Locate the text for {', '.join(missing)} or confirm it is not needed."] + questions))
    rationale = (f"Declared {r['metadata_declared']!r}; the wheel's own documents show {', '.join(detected)}, "
                 'consistent with the declaration' + (f" ({operator}: a choice of licence)" if operator == 'OR'
                                                      else '') + '. Permissive; no copyleft or proprietary signal.')
    if extra:
        rationale += f" Additional families in the documents ({', '.join(extra)}) are bundled notices to ship too."
    return p('Batch 2: declared and detected licences agree', 'approved_with_conditions', conditions, rationale,
             ' '.join(['Confirm, artifact by artifact.'] + questions))


def upstream_proposal(artifact, entry):
    files = '; '.join(f"{f['path']} (sha256 {f['sha256'][:12]}…)" for f in entry['files'])
    source = entry['source']
    names = [Path(f['member']).name for f in entry['files']]
    conditions = f'ship the upstream text(s) at LICENSES/{artifact}/UPSTREAM/ with their source recorded'
    if any('NOTICE' in n for n in names):
        conditions += '; ship the upstream NOTICE (Apache-2.0 4(d))'
    if source['kind'] == 'repository_files_at_release_commit':
        how = (f"repository {source['repository']} at commit {source['commit'][:12]} (ref {source['ref']}), whose "
               f"{source['version_check']['file']} contains {source['version_check']['expected_line']!r}; no licence "
               'file exists in a PyPI sdist for this version')
        question = ('Confirm that the repository-level licence covers this package and that the wheel was built from '
                    'this release.')
        if source.get('note') and 'monorepo' in source['note']:
            question += (' Monorepo: the semconv-ai package has no package-level licence and PyPI names no '
                         'repository; confirm the attribution.')
    else:
        how = f"PyPI sdist {source['filename']} (sha256 {source['sha256'][:12]}…, verified against PyPI)"
        question = 'Confirm the text matches the declared licence and covers the wheel.'
        if source.get('note'):
            how += f"; {source['note']}"
    return p('No licence file in wheel', 'approved_with_conditions', conditions,
             f'Upstream licence obtained from the {how}.', question, evidence=files)


def reconciliation_facts(recon, artifact):
    row = next((w for w in recon.get('wheels', []) if w['artifact'] == artifact), None)
    if not row:
        return '', ''
    files = row['library_files']
    unnamed = [Path(f['member']).name for f in files if not f['in_official_attachment_a']]
    evidence = (f"Reconciliation ({row['primary_source']}): {len(files)} library file(s); named in the bundled "
                f"Attachment A: {sum(f['in_bundled_attachment_a'] for f in files)}; in the official one: "
                f"{sum(f['in_official_attachment_a'] for f in files)}")
    question = ''
    if unnamed and row['primary_source'] == 'cuda-12.8.1-eula':
        evidence += f"; not named in the official Attachment A: {', '.join(unnamed)}"
        question = f" Are the files not named in Attachment A ({', '.join(unnamed)}) distributable at all?"
    return evidence, question


def build(rows, upstream, recon=None):
    recon = recon or {}
    upstream_by_artifact = {e['artifact']: e for e in upstream}
    out, problems, used = [], [], set()
    for r in rows:
        flags = [f for f in r['flags'].split(', ') if f]
        batch = 1 if flags else 2
        if 'no_licence_file_in_wheel' in flags:
            entry = upstream_by_artifact.get(r['artifact'])
            if not entry or not entry['found']:
                problems.append(f"{r['artifact']}: no upstream licence text gathered")
                continue
            prop = upstream_proposal(r['artifact'], entry)
        elif flags:
            prop = PROPOSALS.get(r['distribution'])
            if prop is None:
                problems.append(f"{r['artifact']}: flagged ({r['flags']}) but has no proposal")
                continue
            used.add(r['distribution'])
            prop = dict(prop)
            facts, question = reconciliation_facts(recon, r['artifact'])
            prop['extra_evidence'] = '; '.join(x for x in (prop['extra_evidence'], facts) if x)
            prop['questions_for_reviewer'] += question
        else:
            prop = unflagged_proposal(r)
        evidence = '; '.join(f'{d} (sha256 {h[:12]}…)' for d, h in zip(
            r['licence_documents'].split('; '), r['licence_document_sha256'].split('; ')) if h)
        evidence = '; '.join(x for x in (evidence, prop['extra_evidence']) if x)
        out.append({'artifact': r['artifact'], 'sha256': r['sha256'], 'flags': r['flags'], 'batch': batch,
                    'group': prop['group'], 'proposed_disposition': prop['proposed_disposition'],
                    'proposed_conditions': prop['proposed_conditions'], 'evidence': evidence,
                    'rationale': prop['rationale'], 'questions_for_reviewer': prop['questions_for_reviewer'],
                    'alternative_if_not_cleared': prop['alternative_if_not_cleared'],
                    'prepared_by': PREPARED_BY, 'prepared_on': PREPARED_ON})
    problems += [f'proposal for {d}, which is not in the inventory or not flagged'
                 for d in sorted(set(PROPOSALS) - used)]
    return out, problems


def render(out):
    lines = ['# Wheelhouse R2: proposed redistribution dispositions', '',
             f'Prepared {PREPARED_ON} by {PREPARED_BY}.', '',
             '**These are proposals, not decisions.** Nothing here is recorded in the decisions file; every row there '
             'stays `unresolved` until the designated reviewer records a decision with the artifact hash, rationale, '
             'reviewer and date. No row is proposed as plain `approved`, and no row may be approved in bulk.', '']
    for batch in (1, 2):
        rows = [o for o in out if o['batch'] == batch]
        counts = Counter(o['proposed_disposition'] for o in rows)
        lines += [f"Batch {batch} ({'flagged' if batch == 1 else 'unflagged'}, {len(rows)}): " +
                  ', '.join(f'{v} {k}' for k, v in sorted(counts.items())), '']
    lines += ['Values: `approved_with_conditions` (a candidate the reviewer may adopt, with the listed conditions), '
              '`needs_qualified_review` (terms unclear or applicability disputed; qualified review required), '
              '`likely_not_distributable` (no grant identified in the primary text; an explicit alternative is '
              'listed).', '']
    order = ['likely_not_distributable', 'needs_qualified_review', 'approved_with_conditions']
    for batch in (1, 2):
        lines += [f"# Batch {batch}: {'flagged' if batch == 1 else 'unflagged'} artifacts", '']
        groups = {}
        for o in out:
            if o['batch'] == batch:
                groups.setdefault((o['proposed_disposition'], o['group']), []).append(o)
        for disposition in order:
            for (d, group), items in sorted(groups.items()):
                if d != disposition:
                    continue
                lines += [f'## {d}: {group} ({len(items)})', '']
                for o in items:
                    lines += [f"### `{o['artifact']}`", '', f"- sha256 `{o['sha256']}`; flags: {o['flags'] or 'none'}",
                              f"- Evidence: {o['evidence'] or '—'}", f"- Rationale: {o['rationale']}",
                              f"- Proposed conditions: {o['proposed_conditions'] or '—'}",
                              f"- Questions for the reviewer: {o['questions_for_reviewer'] or '—'}"]
                    if o['alternative_if_not_cleared']:
                        lines.append(f"- If not cleared: {o['alternative_if_not_cleared']}")
                    lines.append('')
    return '\n'.join(lines)


def main():
    with INVENTORY_CSV.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    upstream = json.loads(UPSTREAM_INDEX.read_text(encoding='utf-8'))
    recon = json.loads(RECONCILIATION.read_text(encoding='utf-8'))
    out, problems = build(rows, upstream, recon)
    if problems:
        print('\n'.join(problems))
        return 1
    with OUT_CSV.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(out)
    OUT_MD.write_text(render(out), encoding='utf-8')
    print(json.dumps({f'batch{b}': dict(Counter(o['proposed_disposition'] for o in out if o['batch'] == b))
                      for b in (1, 2)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
