"""Shared NVIDIA deployment assessment with product-specific findings (a proposal for the designated reviewer).

  python scripts/evidence_nvidia_deployment.py

Scope: the 13 NVIDIA wheels whose terms permit distribution only as part of an application (11 wheels bundling the
CUDA Toolkit EULA, NVSHMEM among them, plus cuDNN and cuSPARSELt). One deployment assessment records the facts the
licences make material (account ownership, recipients, access controls, application use) and maps each licence
requirement against them; every product keeps its own governing-text and file-coverage findings. Facts not recorded
in the repository are listed as owner inputs, never assumed. Writes reports/wheelhouse_evidence/
nvidia_deployment_assessment.{json,md}.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.evidence_common import (artifact_for, fetch_retained, html_text, open_wheel, sha256_bytes,  # noqa
                                     write_pack)

RECONCILIATION = ROOT / 'reports/wheelhouse_nvidia_licence_reconciliation.json'
CUDA_EULA_WHEELS = ('nvidia_cublas_cu12', 'nvidia_cuda_cupti_cu12', 'nvidia_cuda_nvrtc_cu12',
                    'nvidia_cuda_runtime_cu12', 'nvidia_cufft_cu12', 'nvidia_cufile_cu12', 'nvidia_curand_cu12',
                    'nvidia_cusolver_cu12', 'nvidia_cusparse_cu12', 'nvidia_nvjitlink_cu12', 'nvidia_nvshmem_cu12')
SEPARATE_SLA = {
    'nvidia_cudnn_cu12': ('https://docs.nvidia.com/deeplearning/cudnn/backend/v9.10.2/reference/eula.html',
                          'nvidia-cudnn-9.10.2-sla.html', 'release-specific (cuDNN backend v9.10.2 documentation)',
                          ('.so', '.h'), 'the runtime files .so and .h'),
    'nvidia_cusparselt_cu12': ('https://docs.nvidia.com/cuda/cusparselt/license.html',
                               'nvidia-cusparselt-latest-licence.html',
                               'NOT release-specific: the current cuSPARSELt licence page; no 0.7.1 page was found',
                               ('.so', '.h'), 'the runtimes files ending with .so and .h as part of your application'),
}
RECORDED_FACTS = [
    {'fact': 'Notebooks are created and pushed under the Kaggle account daichongwei06',
     'source': 'kernel ids in notebooks/*/kernel-metadata.json; docs/Team_Environment_and_Credentials_Guide_ZH.md'},
    {'fact': 'The proposed R2 dataset is private, named arc3-vllm-0.19.0-cu128-wheelhouse-r2 (not yet confirmed or '
             'created)', 'source': 'reports/wheelhouse_r2_approval_artifacts.md (Record B draft)'},
    {'fact': 'Runtime use: the wheels are installed offline into a fresh virtual environment inside the team\'s '
             'Kaggle notebook and loaded by vLLM/torch serving the pinned Qwen3-VL model for the ARC-AGI-3 agent; '
             'internet is disabled', 'source': 'certification/wheelhouse_r2_smoke_v1/protocol.json; '
                                                 'docs/ARC-AGI-3_Final_Project_Plan.md'},
    {'fact': 'Maximum team size 8; identity verification required',
     'source': 'docs/ARC-AGI-3_Final_Project_Plan.md (competition constraints table; to revalidate)'},
    {'fact': 'Milestone and prize eligibility require a public notebook and open-source materials with compatible '
             'licences; the stated winner licence is CC BY 4.0 plus open-system/model/weights obligations',
     'source': 'docs/ARC-AGI-3_Final_Project_Plan.md (sections on milestone release and constraints; to revalidate)'},
]
OWNER_INPUTS = [
    'Which Kaggle account will own the R2 dataset (personal account of a team member, or another team-controlled '
    'account)?',
    'Who will be granted access (named collaborators and their roles: team members, contractors, others)?',
    'Access controls: dataset visibility, collaborator permissions (view/edit), and whether any notebook that '
    'attaches it will ever be made public or shared',
    'Whether the dataset or any notebook attaching it is intended to be published for milestone or prize eligibility, '
    'and if so whether the NVIDIA wheels would be part of the published materials',
    'Whether the team or its members hold any separate agreement with NVIDIA covering these components',
]
REQUIREMENTS = [
    ('Distribution only of portions identified as distributable (Attachment A / the SLA\'s distribution clause)',
     'Product-specific: see file coverage below.'),
    ('Incorporated into a software application with material additional functionality',
     'Phase A (private development): the wheels are installed into an environment and loaded by vLLM/torch for the '
     'agent. Whether a wheelhouse dataset attached to the notebook is "incorporated into" that application, or a '
     'separate stand-alone copy of the SDK components, is the central open question. Phase B (publication): '
     'publishing the wheelhouse would be distribution to the public.'),
    ('The distributable portions are accessed only by the application',
     'Phase A: anyone with dataset access could download the wheels directly, outside the application. Recipients '
     'and access controls (owner inputs) are material.'),
    ('No distribution of the SDK as a stand-alone product',
     'A wheelhouse that also contains the unmodified NVIDIA wheels is not itself an application; whether attaching it '
     'to the team\'s notebook avoids stand-alone distribution needs the reviewer\'s assessment.'),
    ('Authorized users: employees and contractors (internal access, secure network)',
     'Depends on who the collaborators are (owner input) and whether Kaggle hosting counts as the team\'s secure '
     'network.'),
    ('Linux portions may be redistributed unmodified (CUDA EULA 2.3); unmodified object files',
     'The wheels are byte-identical to PyPI; nothing is modified.'),
    ('Terms of the application\'s distribution consistent with the agreement; notices retained',
     'Phase B: open-source publication terms (the competition\'s open-source requirements) may conflict with the '
     'proprietary terms; this is a Release Owner question as well as a licence question.'),
]


def file_coverage_separate(z, suffixes):
    covered, other = [], []
    for info in z.infolist():
        name = info.filename
        if name.endswith('/') or '.dist-info/' in name or name.endswith(('__init__.py', '.typed'))                 or re.search(r'(?i)licen[cs]e(\.txt)?$', name):
            continue
        base = Path(name).name
        is_so = base.endswith('.so') or '.so.' in base
        (covered if (is_so and '.so' in suffixes) or base.endswith(tuple(s for s in suffixes if s != '.so'))
         else other).append(name)
    return covered, other


def word_match(a, b):
    import difflib
    wa, wb = re.findall(r'[a-z0-9]+', a.lower()), re.findall(r'[a-z0-9]+', b.lower())
    wb = agreement_body(wa, wb)
    matcher = difflib.SequenceMatcher(None, wa, wb, autojunk=False)
    same = sum(block.size for block in matcher.get_matching_blocks())
    spans = [(' '.join(wa[i1:i2]), ' '.join(wb[j1:j2]))
             for tag, i1, i2, j1, j2 in matcher.get_opcodes() if tag != 'equal']
    numbering = [x for x in spans if label_only(x[0]) and label_only(x[1])]
    changes = [(a[:200], b[:200]) for a, b in spans if (a, b) not in numbering]
    return {'bundled_words': len(wa), 'primary_words': len(wb), 'matching_words': same,
            'numbering_only_differences': len(numbering), 'difference_count': len(changes),
            'differences': changes[:25],
            'note': 'the primary page is trimmed to the span between the first and last eight words of the bundled text '
                    '(page navigation excluded); differences are word-level, after lower-casing'}


def agreement_body(wa, wb, k=8):
    """The part of the page words between the first occurrence of the bundled text's opening k words and the last
    occurrence of its closing k words (the whole page if either is not found)."""
    def find(seq, needle, last=False):
        positions = [i for i in range(len(seq) - len(needle) + 1) if seq[i:i + len(needle)] == needle]
        return (positions[-1] if last else positions[0]) if positions else None
    start = next((find(wb, wa[i:i + k]) for i in range(min(200, len(wa) - k))
                  if find(wb, wa[i:i + k]) is not None), None)
    end = next((find(wb, wa[len(wa) - k - i:len(wa) - i], last=True) for i in range(min(200, len(wa) - k))
                if find(wb, wa[len(wa) - k - i:len(wa) - i], last=True) is not None), None)
    return wb[start:end + k] if start is not None and end is not None and end >= start else wb


LABEL = re.compile(r'^([0-9]+|[ivx]+|[a-z])$')


def label_only(span):
    return all(LABEL.match(w) for w in span.split())


def build():
    recon = {w['artifact'].split('-')[0]: w for w in json.loads(RECONCILIATION.read_text(encoding='utf-8'))['wheels']}
    sources = json.loads(RECONCILIATION.read_text(encoding='utf-8'))['sources']
    products = []
    for prefix in CUDA_EULA_WHEELS:
        r = recon[prefix]
        files = r['library_files']
        primary = r['primary_source']
        # NVSHMEM's version-specific terms (its supplement) make any portion distributable and have no Attachment A
        unnamed = [] if prefix == 'nvidia_nvshmem_cu12' else             [Path(f['member']).name for f in files if not f['in_official_attachment_a']]
        products.append({
            'distribution': prefix, 'artifact': r['artifact'], 'sha256': r['sha256'],
            'bundled_licence': r['bundled_licences'], 'primary_source': primary,
            'primary_source_basis': sources[primary]['basis'],
            'bundled_identical_to_primary': r['bundled_identical_to_primary'],
            'file_coverage': {'library_files': len(files),
                              'named_in_bundled_attachment_a': sum(f['in_bundled_attachment_a'] for f in files),
                              'named_in_primary_attachment_a': sum(f['in_official_attachment_a'] for f in files),
                              'not_named_in_primary': unnamed},
            'questions': product_questions(prefix, unnamed)})
    for prefix, (url, name, basis, suffixes, clause) in SEPARATE_SLA.items():
        artifact = artifact_for(prefix)
        z = open_wheel(artifact)
        bundled = {n: z.read(n) for n in z.namelist() if re.search(r'(?i)licen[cs]e(\.txt)?$', n)}
        page, record = fetch_retained(name, url)
        comparison = word_match('\n'.join(b.decode('utf-8', 'replace') for b in bundled.values()), html_text(page))
        covered, other = file_coverage_separate(z, suffixes)
        products.append({
            'distribution': prefix, 'artifact': artifact['filename'], 'sha256': artifact['sha256'],
            'bundled_licence': {n: sha256_bytes(b) for n, b in bundled.items()},
            'primary_source': record, 'primary_source_basis': basis,
            'bundled_vs_primary': comparison,
            'distribution_clause': clause,
            'file_coverage': {'files_matching_clause': len(covered), 'other_files': other,
                              'by_suffix': dict(Counter(Path(n).suffix or Path(n).name for n in covered + other))},
            'questions': product_questions(prefix, other) + [comparison_question(comparison, basis)]})
    return {'schema': 'wheelhouse_evidence_nvidia_deployment_v1',
            'scope': {'rows': len(products), 'note': 'an earlier note said 14 rows; the correct count is 13 '
                      '(11 CUDA-EULA wheels including NVSHMEM, plus cuDNN and cuSPARSELt)',
                      'excluded_with_reason': {
                          'cuda_python, cuda_bindings': 'own NVIDIA Software License without the application '
                                                        'requirements; reviewed separately',
                          'nvidia_cutlass_dsl, nvidia_cutlass_dsl_libs_base': 'own EULA; see cutlass_binaries pack',
                          'nvidia_nccl_cu12, nvidia_nvtx_cu12, nvidia_cudnn_frontend': 'permissive licence texts '
                          'under a proprietary classifier; reviewed separately'}},
            'deployment': {'recorded_facts': RECORDED_FACTS, 'owner_inputs_required': OWNER_INPUTS,
                           'phases': {'A': 'private development: a private dataset attached to the team\'s own '
                                           'notebooks', 'B': 'publication for milestone or prize eligibility, '
                                           'if pursued'},
                           'requirements_against_deployment': [{'requirement': a, 'assessment_inputs': b}
                                                               for a, b in REQUIREMENTS]},
            'products': products}


def product_questions(prefix, unnamed_or_other):
    q = []
    if prefix in ('nvidia_cufile_cu12', 'nvidia_nvjitlink_cu12'):
        q.append('Which text governs: the bundled CUDA EULA (omits this component) or the official CUDA 12.8.1 EULA '
                 '(lists its libraries)?')
    if prefix == 'nvidia_nvshmem_cu12':
        q.append('Which text governs: the bundled CUDA EULA or the NVSHMEM v3.4.5-0 SDK licence and supplement? Under '
                 'the bundled CUDA EULA none of the 14 shipped library files is named in Attachment A; under the '
                 'supplement "any portion of the SDK" is distributable, and the application requirements still apply.')
    if prefix == 'nvidia_cusparselt_cu12':
        q.append('Evidence gap: no release-specific (0.7.1) licence text was found; is the bundled text accepted as '
                 'governing?')
    if unnamed_or_other:
        q.append('Files not covered by the distributable listing: ' + ', '.join(Path(x).name for x in unnamed_or_other[:12])
                 + (' …' if len(unnamed_or_other) > 12 else '') + ' — are they distributable?')
    return q


def comparison_question(cmp_, basis):
    if cmp_['difference_count']:
        return (f"The primary text ({basis}) differs from the bundled text in {cmp_['difference_count']} spans beyond "
                'list numbering (listed above); which text governs this wheel?')
    return (f"The primary text ({basis}) matches the bundled text except list numbering"
            + ('; it is not release-specific, so the match does not establish the 0.7.1 terms.'
               if 'NOT release-specific' in basis else '.'))


def markdown(p):
    d = p['deployment']
    lines = ['# NVIDIA deployment assessment (shared) with product-specific findings', '',
             '**A proposal for the designated reviewer, not a decision.** Private visibility is not redistribution '
             'clearance.', '',
             f"Scope: {p['scope']['rows']} rows. {p['scope']['note']}.", '',
             'Excluded from this shared assessment:', '']
    lines += [f'- {k}: {v}' for k, v in p['scope']['excluded_with_reason'].items()]
    lines += ['', '## Deployment facts recorded in the repository (to revalidate)', '', '| Fact | Source |', '|---|---|']
    lines += [f"| {f['fact']} | {f['source']} |" for f in d['recorded_facts']]
    lines += ['', '## Owner inputs required (not recorded; not assumed)', '']
    lines += [f'{i}. {x}' for i, x in enumerate(d['owner_inputs_required'], 1)]
    lines += ['', '## Licence requirements against the deployment', '',
              f"Phase A: {d['phases']['A']}. Phase B: {d['phases']['B']}.", '',
              '| Requirement | What the assessment depends on |', '|---|---|']
    lines += [f"| {r['requirement']} | {r['assessment_inputs']} |" for r in d['requirements_against_deployment']]
    lines += ['', '## Product-specific findings', '']
    for x in p['products']:
        lines += [f"### `{x['artifact']}`", '', f"- sha256 `{x['sha256']}`",
                  '- Bundled licence: ' + ', '.join(f'`{n}` (`{h[:12]}…`)' for n, h in x['bundled_licence'].items())]
        if isinstance(x['primary_source'], str):
            lines.append(f"- Version-specific primary source: `{x['primary_source']}` ({x['primary_source_basis']}); "
                         f"bundled text identical: {'yes' if x['bundled_identical_to_primary'] else 'no'}")
            c = x['file_coverage']
            lines.append(f"- File coverage: {c['library_files']} library files; named in the bundled Attachment A: "
                         f"{c['named_in_bundled_attachment_a']}; in the primary one: {c['named_in_primary_attachment_a']}"
                         + (f"; not named in the primary: {', '.join(c['not_named_in_primary'])}"
                            if c['not_named_in_primary'] else ''))
        else:
            s, cmp_ = x['primary_source'], x['bundled_vs_primary']
            lines.append(f"- Primary source: {s['url']} (retained `{s['file']}`, `{s['sha256'][:12]}…`); "
                         f"{x['primary_source_basis']}")
            lines.append(f"- Bundled vs primary (word level): {cmp_['matching_words']} of {cmp_['bundled_words']} "
                         f"bundled words matched; {cmp_['numbering_only_differences']} list-numbering-only spans; "
                         f"{cmp_['difference_count']} other differing spans"
                         + ' (agreement body only; page navigation excluded)')
            for bundled_span, primary_span in cmp_['differences'][:12]:
                lines.append(f"  - bundled: \"{bundled_span or '—'}\" → primary: \"{primary_span or '—'}\"")
            c = x['file_coverage']
            lines.append(f"- Distribution clause: \"{x['distribution_clause']}\". Files matching it: "
                         f"{c['files_matching_clause']}; other files: {len(c['other_files'])} "
                         f"({', '.join(Path(o).name for o in c['other_files'][:8])}{' …' if len(c['other_files']) > 8 else ''})")
        lines += [f'- Question: {q}' for q in x['questions']] + ['']
    return '\n'.join(lines)


if __name__ == '__main__':
    payload = build()
    write_pack('nvidia_deployment_assessment', payload, markdown(payload))
    print(json.dumps({'rows': payload['scope']['rows'],
                      'products': {x['distribution']: x['questions'] for x in payload['products']}}, indent=1)[:3000])
