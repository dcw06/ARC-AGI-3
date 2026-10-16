"""Build a private review-only GPU-probe candidate, without any provider calls."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.object_identification_v1.mount_check import canonical
from research.object_identification_v1.probe import verify
from research.object_identification_v1.supervisor import SCOPE, readiness
from research.object_identification_v1.install_check import validate_completion
from scripts.serve_manual_strategy_worksheet import private_directory


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def build(base, bundle, model_licenses, previous_use, output):
    base, bundle, model_licenses, previous_use, output = map(Path,
        (base, bundle, model_licenses, previous_use, output))
    if output.exists():
        raise FileExistsError('preserve all earlier packets')
    verify(bundle)
    cpu_packet, cpu_result = base/'cpu-install-review-r2', base/'cpu-install-completed-version1-r1'
    cpu_verification = json.loads((base/'cpu-install-completed-version1-verification-r1.json').read_bytes())
    assert cpu_verification['verified'] and cpu_verification['provider_status'] == 'COMPLETE'
    assert sha((cpu_packet/'review-lock.json').read_bytes()) == cpu_verification['review_lock_sha256']
    collection = json.loads((cpu_result/'collection-manifest.json').read_bytes())
    for name, digest in collection.items():
        assert sha((cpu_result/name).read_bytes()) == digest, name
    stdout = ''.join(row['data'] for row in json.loads((cpu_result/'provider.log').read_bytes())
                     if row.get('stream_name') == 'stdout')
    validate_completion((cpu_result/'result.json').read_bytes(), (cpu_result/'completion-witness.json').read_bytes(),
                        'COMPLETE', stdout, sha((cpu_packet/'manifest.json').read_bytes()))
    datasets = json.loads((cpu_packet/'manifest.json').read_bytes())['datasets']
    metadata = json.loads((cpu_packet/'kernel-metadata.json').read_bytes())
    metadata.update(id='daichongwei06/arc3-internvl-object-identification-review-v1',
        title='ARC3 InternVL Object Identification Review V1', is_private=True,
        enable_gpu=False, enable_tpu=False, enable_internet=False)
    protocol = {'schema': 'internvl_object_identification_prelaunch_v1',
                'live_runs_enabled': False, 'scope': SCOPE, 'datasets': datasets,
                'model': 'OpenGVLab/InternVL3_5-8B', 'revision': '9bb6a56ad9cc69db95e2d4eeb15a52bbcac4ef79',
                'intended_private_account': 'daichongwei06',
                'intended_live_notebook': 'daichongwei06/arc3-internvl-object-identification-v1',
                'kaggle_image': {k: metadata[k] for k in ('docker_image', 'docker_image_pinning_type')},
                'prior_cpu_authority_reused_for_gpu': False}
    names = [
        'research/object_identification_v1/'+name for name in (
            'inference.py', 'supervisor.py', 'replay.py', 'runtime.py', 'runtime_source_pin.json',
            'runtime_requirements_extra.lock', 'install_check.py', 'mount_check.py', 'probe.py')]
    names += ['certification/direct_publisher_smoke_v1/'+name for name in
              ('install.py', 'server.py', 'trusted_requirements.lock')]
    names += ['certification/phase4_multimodal_preflight_v3/images.py',
              'scripts/serve_manual_strategy_worksheet.py', 'scripts/object_identification_v1.py']
    files = {'reviewed-source/'+name: (ROOT/name).read_bytes() for name in names}
    for package in ('research', 'research/object_identification_v1', 'certification',
                    'certification/direct_publisher_smoke_v1', 'certification/phase4_multimodal_preflight_v3', 'scripts'):
        files['reviewed-source/'+package+'/__init__.py'] = b''
    files['protocol.json'] = canonical(protocol)
    files['protocol.md'] = (ROOT/'reports/internvl_object_identification_v1_protocol_r1.md').read_bytes()
    files['support-request-draft.md'] = (ROOT/'reports/internvl_object_identification_v1_platform_cap_support_request.md').read_bytes()
    files['kernel-metadata.json'] = canonical(metadata)
    files['evaluation_binding.json'] = canonical({
        'probe_bundle_review_lock_sha256': sha((bundle/'review-lock.json').read_bytes()),
        'reference_answers_sha256': sha((bundle/'references/answers.json').read_bytes()),
        'reference_location': 'outside model sandbox; use the retained private probe bundle',
        'references_included_in_runtime': False})
    for name in ('result.json', 'completion-witness.json', 'provider.log', 'collection-manifest.json'):
        files['evidence/cpu-install/'+name] = (cpu_result/name).read_bytes()
    for name in ('cpu-install-completed-version1-verification-r1.json',
                 'cpu-install-completed-version1-independent-audit-r1.json',
                 'model-byte-verification-r1.json', 'private-dataset-provider-verification-model-r1.json',
                 'private-dataset-provider-verification-inputs-v2-r1.json'):
        files['evidence/'+name] = (base/name).read_bytes()
    for name in ('generation-interface-cpu-r2.json', 'real-prompt-token-check-r1.json',
                 'gpu-prelaunch-final2-linux-tests.json', 'gpu-prelaunch-final2-linux-tests.log'):
        files['evidence/local-validation/'+name] = (base/name).read_bytes()
    for name in ('generation-interface-cpu-r2.json', 'real-prompt-token-check-r1.json'):
        proof = json.loads((base/name).read_bytes())
        assert proof['source_sha256'] == sha((ROOT/'research/object_identification_v1/inference.py').read_bytes())
        assert proof['study_requests'] == 0 and proof['cuda_initialized'] is False
    checked = json.loads((base/'gpu-prelaunch-final2-linux-tests.json').read_bytes())
    assert checked['returncode'] == 0
    assert checked['log_sha256'] == sha((base/'gpu-prelaunch-final2-linux-tests.log').read_bytes())
    for name, digest in checked['source_sha256'].items():
        assert sha((ROOT/name).read_bytes()) == digest
    historical = json.loads(previous_use.read_bytes())
    terms = historical['licence_evidence']
    assert len(terms) == 23
    for index, term in enumerate(terms, 1):
        raw = (previous_use.parents[3]/term['path']).read_bytes()
        assert sha(raw) == term['sha256'] and len(raw) == term['bytes']
        files[f'licences/retained-wheel-term-{index:02d}.txt'] = raw
    model_inventory = {row['name']: row for row in next(d for d in datasets if d['kind'] == 'model')['files']}
    for name in ('LICENSE-APACHE-2.0.txt', 'LICENSE-MIT-INTERNVL.txt', 'PROVENANCE.json'):
        raw = (model_licenses/name).read_bytes()
        assert sha(raw) == model_inventory[name]['sha256']
        files['licences/model/'+name] = raw
    files['licences/timm-LICENSE.txt'] = (bundle/'runtime-extra/LICENSE').read_bytes()
    use = {'status': 'draft_no_new_scope_approval', 'account': 'daichongwei06',
           'access': 'account_holder_only', 'outputs': 'raw private; sanitized summaries only',
           'teammate_notebook_access': False, 'separate_nvidia_agreement': False,
           'wheel_source': next(d['ref']+'/'+str(d['version']) for d in datasets if d['kind'] == 'publisher_wheels'),
           'model': protocol['model'], 'model_revision': protocol['revision'],
           'historical_use_assessment_sha256': sha(previous_use.read_bytes()),
           'historical_acceptance_is_not_new_gpu_authority': True,
           'permission_outcome': None, 'owner_reconfirmation': None,
           'licence_files_sha256': {name: sha(raw) for name, raw in files.items() if name.startswith('licences/')}}
    files['use_assessment_draft.json'] = canonical(use)
    files['scope.json'] = canonical(SCOPE)
    files['readiness.json'] = canonical({'status': 'review_only_not_uploaded',
        'blockers': readiness(protocol, {}), 'GPU_attempts_consumed': 0,
        'CPU_attempts_consumed_and_preserved': 2, 'provider_cap_verified': False,
        'source_approval': None, 'compute_authorization': None, 'reservation': None})
    cell = 'raise SystemExit("REVIEW ONLY: provider full-job cap and fresh GPU authority missing; no imports, installation or inference started.")\n'
    files['profile.ipynb'] = canonical({'nbformat': 4, 'nbformat_minor': 5,
        'metadata': {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}},
        'cells': [{'cell_type': 'markdown', 'id': 'scope', 'metadata': {}, 'source': [
            '# Private InternVL object-identification candidate\n',
            'Review only; six proposed greedy generations, zero actions. GPU/TPU/internet off.\n']},
            {'cell_type': 'code', 'id': 'refusal', 'metadata': {}, 'execution_count': None,
             'outputs': [], 'source': [cell]}]})
    files['review.md'] = b'''# Private InternVL prelaunch candidate

Prepared locally only: no upload, save, reservation, launch claim or GPU authority.
The notebook is GPU/TPU/internet off and always refuses before imports or work.
The complete candidate supervisor/worker and independent replay source are retained
for review; this is not a final live submission artifact. A separately reviewed
operational revision is required after the provider mechanism is known.

Read protocol.md, scope.json, the retained CPU evidence, use_assessment_draft.json
and all licence texts. CPU evidence is historical only; both CPU attempts are consumed.
The new model-use outcome is blank, and no approval labels have been supplied.
No references/answers or reference overlays are included in the model runtime.

Current blockers: provider-enforced entire-GPU-job cap; scoped-use confirmation
for this exact probe; exact live source-package review/approval; compute authorization
and one-use reservation/claim. Do not reuse CPU or previous-study compute authority.
The attached support request is an unsent draft. Do not send it without instruction.

Proposed compute scope: one RTX PRO 6000, 3600 s provider full-job cap, 3300 s worker,
3000 s work cutoff plus 300 s cleanup reserve; six generations, at most 4096 tokens
each; one attempt, no retries, no game actions or scorecards; account-only outputs.
The full pretrained checkpoint and GPU inference have not yet been tested.
'''
    lock = {'schema': 'internvl_prelaunch_review_lock_v1',
            'artifacts': {name: sha(raw) for name, raw in sorted(files.items())},
            'source_sha256': {name: sha((ROOT/name).read_bytes()) for name in names},
            'builder_sha256': sha(Path(__file__).read_bytes()), 'scope': SCOPE}
    files['review-lock.json'] = canonical(lock)
    private_directory(output)
    for name, raw in files.items():
        path = output/name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    return {'packet': str(output), 'review_lock_sha256': sha(files['review-lock.json']),
            'live_runs_enabled': False, 'provider_calls': 0, 'gpu_attempts': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('base', 'bundle', 'model-licenses', 'previous-use', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.base, args.bundle, args.model_licenses, args.previous_use, args.output), indent=2))
