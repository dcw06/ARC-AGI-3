"""Artifact-specific PROPOSED redistribution dispositions for the flagged R2 wheels (review preparation only).

These are proposals prepared for the designated reviewer, not decisions: nothing here is written to the human-owned
reports/wheelhouse_redistribution_decisions.csv, and no row is proposed as plainly `approved`. Each proposal names the
artifact's own licence documents and hashes (from the generated inventory), the clauses or facts relied on, the
questions the reviewer must resolve and, where an artifact may not be clearable, an explicit alternative (never a
silent omission: every artifact is a required dependency of the approved manifest).

Batch 1 covers every flagged artifact (43). The 131 unflagged artifacts are listed as `not_yet_proposed`.

  python scripts/propose_wheelhouse_dispositions.py
Outputs reports/wheelhouse_redistribution_proposed_dispositions.{csv,md}; exits 1 if a flagged artifact lacks a
proposal or a proposal names an artifact that is not in the inventory.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_CSV = ROOT / 'reports/wheelhouse_redistribution_inventory.csv'
UPSTREAM_INDEX = ROOT / 'reports/wheelhouse_upstream_licenses/index.json'
OUT_CSV = ROOT / 'reports/wheelhouse_redistribution_proposed_dispositions.csv'
OUT_MD = ROOT / 'reports/wheelhouse_redistribution_proposed_dispositions.md'
PREPARED_ON = '2026-10-04'
PREPARED_BY = 'Claude (assistant), for the designated reviewer; proposal only'
FIELDS = ['artifact', 'sha256', 'flags', 'group', 'proposed_disposition', 'proposed_conditions', 'evidence',
          'rationale', 'questions_for_reviewer', 'alternative_if_not_cleared', 'prepared_by', 'prepared_on']
PROPOSED_VALUES = {'approved_with_conditions', 'needs_qualified_review', 'likely_not_distributable',
                   'not_yet_proposed'}

CUDA_EULA = 'ad6f5853fba0'  # identical License.txt in eleven CUDA Toolkit wheels
EULA_CLAUSES = ('CUDA Toolkit EULA (License.txt sha256 ad6f5853…): 1.1.1(3) distribution only of portions identified '
                'as distributable, incorporated in object code into an application; 1.1.2(1)-(2) the application '
                'must add material functionality and be the only accessor; 1.1.4(2) no distribution as a '
                'stand-alone product; 2.3 Linux portions may be redistributed unmodified; 2.5 licensing contact '
                'nvidia-compute-license-questions@nvidia.com')
NVIDIA_QUESTION = ('Is a private Kaggle dataset, attached only to the team\'s own notebook (the ARC-AGI-3 agent, '
                   'which is the application), distribution "incorporated into a software application", or '
                   'distribution of the SDK "as a stand-alone product"? Does private, team-only access make this '
                   'use by authorized users rather than distribution?')
NVIDIA_ALTERNATIVE = ('Do not redistribute; options for the owner to choose explicitly: (a) written confirmation '
                      'from NVIDIA via the licensing contact; (b) take the CUDA libraries from the Kaggle base image '
                      'instead (changes the runtime: needs a new manifest, closure, download and install check); '
                      '(c) stop and record the bundle as blocked. Never dropped silently.')
REBUILD_NOTE = ('any change to the artifact set needs a new approved manifest, closure, download and offline install '
                'check')


def p(group, disposition, conditions, rationale, questions, alternative='', evidence=''):
    return {'group': group, 'proposed_disposition': disposition, 'proposed_conditions': conditions,
            'rationale': rationale, 'questions_for_reviewer': questions, 'alternative_if_not_cleared': alternative,
            'extra_evidence': evidence}


def cuda_component(component, listed):
    if listed:
        return p('NVIDIA CUDA Toolkit EULA', 'needs_qualified_review',
                 'if cleared: ship License.txt unmodified; files unmodified (2.3); no NVIDIA endorsement claim',
                 f'{component} is listed in Attachment A as distributable, but only as incorporated into an '
                 'application; a wheelhouse dataset may be a stand-alone distribution.',
                 NVIDIA_QUESTION + ' Do the wheel\'s headers/other files beyond the Attachment A libraries need to '
                 'be excluded or separately cleared?', NVIDIA_ALTERNATIVE, EULA_CLAUSES)
    return p('NVIDIA CUDA Toolkit EULA', 'likely_not_distributable',
             'only with an explicit grant identified by the reviewer or NVIDIA',
             f'{component} does not appear anywhere in this EULA, including Attachment A, so no distribution grant '
             'has been identified for it (1.1.1(3) permits distribution only of portions identified as '
             'distributable).',
             'Is there a supplement or other NVIDIA licence that makes this component distributable? ' + NVIDIA_QUESTION,
             NVIDIA_ALTERNATIVE, EULA_CLAUSES)


PROPOSALS = {
    # NVIDIA CUDA Toolkit EULA family
    'nvidia_cublas_cu12': cuda_component('CUDA BLAS (libcublas, libcublasLt)', True),
    'nvidia_cuda_cupti_cu12': cuda_component('CUPTI (libcupti)', True),
    'nvidia_cuda_nvrtc_cu12': cuda_component('NVRTC (libnvrtc, libnvrtc-builtins)', True),
    'nvidia_cuda_runtime_cu12': cuda_component('CUDA Runtime (libcudart)', True),
    'nvidia_cufft_cu12': cuda_component('cuFFT (libcufft)', True),
    'nvidia_curand_cu12': cuda_component('cuRAND (libcurand)', True),
    'nvidia_cusolver_cu12': cuda_component('cuSOLVER (libcusolver)', True),
    'nvidia_cusparse_cu12': cuda_component('cuSPARSE (libcusparse)', True),
    'nvidia_cufile_cu12': cuda_component('cuFile (GPUDirect Storage)', False),
    'nvidia_nvjitlink_cu12': cuda_component('nvJitLink', False),
    'nvidia_nvshmem_cu12': cuda_component('NVSHMEM', False),
    # Other NVIDIA SLAs
    'nvidia_cudnn_cu12': p(
        'NVIDIA cuDNN SLA', 'needs_qualified_review', 'if cleared: ship License.txt unmodified; files unmodified',
        'cuDNN SLA (sha256 49cf79bd…) 1.1(iii)/1.2: distributable runtime .so and .h files only as incorporated into '
        'an application with material additional functionality; same stand-alone question as the CUDA EULA.',
        NVIDIA_QUESTION, NVIDIA_ALTERNATIVE),
    'nvidia_cusparselt_cu12': p(
        'NVIDIA cuSPARSELt SLA', 'needs_qualified_review', 'if cleared: ship LICENSE.txt unmodified; files unmodified',
        'cuSPARSELt SLA (sha256 e8d15888…) 1.1(iii)/1.2 and section 2: runtime .so and .h files distributable "as '
        'part of your application"; 2.2 forbids stand-alone distribution.', NVIDIA_QUESTION, NVIDIA_ALTERNATIVE),
    'nvidia_cutlass_dsl_libs_base': p(
        'NVIDIA CUTLASS DSL EULA', 'likely_not_distributable', 'only with an explicit grant',
        'CUTLASS DSL EULA (sha256 9ed3a034… for the sibling wheel; this wheel ships it twice) 1.1(d) permits '
        'distributing only "python files ... in source format" incorporated into an application; this wheel also '
        'ships compiled binaries (libcute_dsl_runtime.so, _cutlass_ir.cpython-312-x86_64-linux-gnu.so, a static .a) '
        'that no identified grant covers; 2.2 forbids making it available to others except authorized users.',
        'Is any grant available for the binaries? Does vLLM 0.19.0 require nvidia-cutlass-dsl at import/startup '
        'for the pinned model, or only for optional kernels? Are Kaggle notebook viewers "authorized users"?',
        'Owner chooses explicitly: NVIDIA confirmation; or a reviewed change removing nvidia-cutlass-dsl from the '
        f'runtime if vLLM does not require it ({REBUILD_NOTE}); or record the bundle as blocked.'),
    'nvidia_cutlass_dsl': p(
        'NVIDIA CUTLASS DSL EULA', 'needs_qualified_review', 'if cleared: ship LICENSE unmodified',
        'Metadata-only wheel (dist-info plus one .txt) under the CUTLASS DSL EULA (sha256 9ed3a034…); it ships no '
        'NVIDIA code itself but depends on nvidia-cutlass-dsl-libs-base. Its disposition should follow that wheel.',
        'Follow the decision for nvidia_cutlass_dsl_libs_base; is redistributing the metadata wheel alone within '
        '1.1(d)?', 'As for nvidia_cutlass_dsl_libs_base.'),
    'cuda_python': p(
        'NVIDIA Software License (cuda-python)', 'approved_with_conditions',
        'ship LICENSE unmodified; dataset description states that the NVIDIA Software License governs these wheels '
        'and that no NVIDIA endorsement is implied',
        'NVIDIA Software License (sha256 25a91d6e…) section 1(b) grants distribution subject to section 2: terms '
        'consistent with the licence, and notice to NVIDIA of known non-compliance. No application-incorporation '
        'requirement; no modification is made.',
        'Is a dataset description plus the shipped LICENSE sufficient to make the distribution terms "consistent"? '
        'Accept 3(a) (applications only for NVIDIA-GPU systems)?', NVIDIA_ALTERNATIVE),
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
        f'the bundle, or a reviewed change of the runtime ({REBUILD_NOTE}).'),
}


def upstream_proposal(artifact, entry):
    files = '; '.join(f"{f['path']} (sha256 {f['sha256'][:12]}…)" for f in entry['files'])
    source = entry['source']
    if source['kind'] == 'repository_file_at_release_tag':
        how = (f"repository licence file at the release tag ({source['url']}); no licence file exists in a PyPI "
               'sdist for this version')
        question = ('Confirm the tag matches the released version and that the repository-level licence covers '
                    'this package; does the repository have a NOTICE file that Apache-2.0 4(d) requires?')
    else:
        how = f"PyPI sdist {source['filename']} (sha256 {source['sha256'][:12]}…, verified against PyPI)"
        question = 'Confirm the text matches the declared licence and covers the wheel.'
        if source.get('note'):
            how += f"; {source['note']}"
    return p('No licence file in wheel', 'approved_with_conditions',
             f'ship the upstream text(s) at LICENSES/{artifact}/UPSTREAM/ with their source recorded',
             f'Upstream licence obtained from the {how}.', question, evidence=files)


def build(rows, upstream):
    by_dist = {}
    upstream_by_artifact = {e['artifact']: e for e in upstream}
    out, problems = [], []
    for r in rows:
        flags = [f for f in r['flags'].split(', ') if f]
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
        else:
            prop = p('Unflagged', 'not_yet_proposed', '', 'Batch 2: not yet reviewed artifact by artifact.', '')
        by_dist[r['distribution']] = True
        evidence = '; '.join(f'{d} (sha256 {h[:12]}…)' for d, h in zip(
            r['licence_documents'].split('; '), r['licence_document_sha256'].split('; ')) if h)
        evidence = '; '.join(x for x in (evidence, prop['extra_evidence']) if x)
        out.append({'artifact': r['artifact'], 'sha256': r['sha256'], 'flags': r['flags'], 'group': prop['group'],
                    'proposed_disposition': prop['proposed_disposition'],
                    'proposed_conditions': prop['proposed_conditions'], 'evidence': evidence,
                    'rationale': prop['rationale'], 'questions_for_reviewer': prop['questions_for_reviewer'],
                    'alternative_if_not_cleared': prop['alternative_if_not_cleared'],
                    'prepared_by': PREPARED_BY, 'prepared_on': PREPARED_ON})
    problems += [f'proposal for {d}, which is not in the inventory' for d in sorted(set(PROPOSALS) - set(by_dist))]
    return out, problems


def render(out):
    from collections import Counter
    counts = Counter(o['proposed_disposition'] for o in out)
    lines = ['# Wheelhouse R2: proposed redistribution dispositions (batch 1: flagged artifacts)', '',
             f'Prepared {PREPARED_ON} by {PREPARED_BY}.', '',
             '**These are proposals, not decisions.** Nothing here is recorded in '
             '`reports/wheelhouse_redistribution_decisions.csv`; every row there stays `unresolved` until the '
             'designated reviewer records a decision with the artifact hash, rationale, reviewer and date. No row is '
             'proposed as plain `approved`.', '',
             'Counts: ' + ', '.join(f'{v} {k}' for k, v in sorted(counts.items())), '',
             'Values: `approved_with_conditions` (a candidate the reviewer may adopt, with the listed conditions), '
             '`needs_qualified_review` (terms unclear; qualified review required), `likely_not_distributable` (no '
             'grant identified; an explicit alternative is listed), `not_yet_proposed` (unflagged; batch 2).', '']
    groups = {}
    for o in out:
        if o['proposed_disposition'] != 'not_yet_proposed':
            groups.setdefault((o['proposed_disposition'], o['group']), []).append(o)
    order = ['likely_not_distributable', 'needs_qualified_review', 'approved_with_conditions']
    for disposition in order:
        for (d, group), items in sorted(groups.items()):
            if d != disposition:
                continue
            lines += [f'## {d}: {group} ({len(items)})', '']
            for o in items:
                lines += [f"### `{o['artifact']}`", '', f"- sha256 `{o['sha256']}`; flags: {o['flags']}",
                          f"- Evidence: {o['evidence'] or '—'}", f"- Rationale: {o['rationale']}",
                          f"- Proposed conditions: {o['proposed_conditions'] or '—'}",
                          f"- Questions for the reviewer: {o['questions_for_reviewer'] or '—'}"]
                if o['alternative_if_not_cleared']:
                    lines.append(f"- If not cleared: {o['alternative_if_not_cleared']}")
                lines.append('')
    lines += ['## Not yet proposed (batch 2)', '',
              f"{counts.get('not_yet_proposed', 0)} unflagged artifacts; each needs its own decision before Record A.",
              '']
    return '\n'.join(lines)


def main():
    with INVENTORY_CSV.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    upstream = json.loads(UPSTREAM_INDEX.read_text(encoding='utf-8'))
    out, problems = build(rows, upstream)
    if problems:
        print('\n'.join(problems))
        return 1
    with OUT_CSV.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(out)
    OUT_MD.write_text(render(out), encoding='utf-8')
    from collections import Counter
    print(json.dumps(dict(Counter(o['proposed_disposition'] for o in out))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
