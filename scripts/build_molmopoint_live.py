"""Build a bound private MolmoPoint template. Does not approve, reserve or launch."""
import argparse
import base64
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.molmopoint_identification_v1 import deployment as D
from research.molmopoint_identification_v1.supervisor import SCOPE
from research.object_identification_v1.mount_check import canonical


def build(previous, plan_path, receipts, validation_path, amendment_path, known_path, output,
          *, wheel_terms=None, prior_use=None):
    previous, output = Path(previous), Path(output)
    if output.exists():
        raise FileExistsError('preserve previous packages')
    prior = D.verify_review(previous)
    validation_path = Path(validation_path)
    validation = json.loads(validation_path.read_bytes())
    if validation['linux'] != dict(tests=validation['linux']['tests'], failures=0, errors=0, skipped=0, returncode=0):
        raise ValueError('Linux checks not passed without skips')
    for name, pin in validation['source_sha256'].items():
        if D.digest((ROOT/name).read_bytes()) != pin:
            raise ValueError('source verification stale: '+name)
    for name, pin in validation['evidence_sha256'].items():
        if D.digest((validation_path.parent/name).read_bytes()) != pin:
            raise ValueError('validation evidence differs')
    plan_raw = Path(plan_path).read_bytes()
    plan = json.loads(plan_raw)
    protocol = json.loads((previous/'runtime/protocol.json').read_bytes())
    licence = (ROOT/'research/molmopoint_identification_v1/LICENSE-APACHE-2.0.txt').read_bytes()
    records = {}
    for kind in ('model', 'inputs'):
        item = next(d for d in plan['datasets'] if d['kind'] == kind)
        old = next(d for d in protocol['datasets'] if d['kind'] == kind)
        frozen = {r['name']:r for r in old['files']}
        if kind == 'model':
            frozen['LICENSE-APACHE-2.0.txt'] = dict(name='LICENSE-APACHE-2.0.txt',
                bytes=len(licence),sha256=D.digest(licence))
        if (item['ref'] != old['ref'] or len(item['files']) != len(frozen)
                or {r['name']:r for r in item['files']} != frozen
                or item['expected_private'] is not True or item['expected_collaborators'] != 0):
            raise ValueError('upload plan differs from frozen inputs/model: '+kind)
        raw = Path(receipts[kind]).read_bytes()
        record = json.loads(raw)
        current, metadata = record['checks']['current'], record['checks']['metadata']
        inventory = record['checks']['inventory']
        expected = {r['name']: r['bytes'] for r in item['files']}
        if (record['ref'] != item['ref'] or record['provider_writes'] != 0
                or record['checks']['status'] != 'ready' or current['ref'] != item['ref']
                or current['version'] != 1 or current['private'] is not True
                or metadata['private'] is not True or metadata['collaborators'] != 0
                or metadata['error'] or inventory['error'] or inventory['has_next_page']
                or inventory['files'] != expected or inventory['matches'] is not True):
            raise ValueError('dataset verification incomplete: '+kind)
        old.update(ref=item['ref'], version=1, files=item['files'])
        records['review-evidence/'+kind+'-provider-verification.json'] = raw
    counts = {d['kind']:len(d['files']) for d in protocol['datasets']}
    if counts != {'wheelhouse':177, 'model':34, 'inputs':9}:
        raise ValueError('exact mounted inventories required')
    amendment_raw = Path(amendment_path).read_bytes()
    amendment = json.loads(amendment_raw)
    if (amendment.get('approved_time_policy_change') is not True
            or amendment.get('accepted_provider_overhead') is not True
            or amendment.get('session_timeout_seconds') != 3600
            or amendment.get('worker_seconds') != 3300
            or not amendment.get('owner_answer')):
        raise ValueError('accepted time amendment missing')
    protocol.update(live_runs_enabled=True, source_bindings_confirmed=True,
        source_binding_basis='owner-only provider version/inventory receipts; actual mounted bytes rechecked before install',
        scope=SCOPE, provider_full_job_cap_verified=False,
        time_policy=dict(owner_amendment_sha256=D.digest(amendment_raw), provider_overhead_may_exceed_one_hour=True))
    old_runtime = json.loads((previous/'runtime/runtime-lock.json').read_bytes())
    runtime = {n:(previous/'runtime'/n).read_bytes() for n in old_runtime['artifacts']}
    source_names = [n.removeprefix('reviewed-source/') for n in runtime
                    if n.startswith('reviewed-source/') and (ROOT/n.removeprefix('reviewed-source/')).is_file()]
    for name in source_names:
        runtime['reviewed-source/'+name] = (ROOT/name).read_bytes()
    runtime['protocol.json'] = canonical(protocol)
    runtime['runtime-lock.json'] = canonical({'schema':'molmopoint_runtime_lock_v1',
        'artifacts':{n:D.digest(raw) for n,raw in sorted(runtime.items())}})
    payload = canonical({n:base64.b64encode(raw).decode() for n,raw in sorted(runtime.items())})
    book = json.loads((previous/'profile.ipynb').read_bytes())
    if D.authority_from(book) is not None:
        raise ValueError('candidate authority must be empty')
    book['cells'][-1]['source'] = D.bootstrap(payload).splitlines(keepends=True)
    metadata = json.loads((previous/'kernel-metadata.json').read_bytes())
    metadata.update(enable_gpu=True, machine_shape='NvidiaRtxPro6000', session_timeout_seconds=3600,
        competition_sources=['arc-prize-2026-arc-agi-3'],
        dataset_sources=[d['ref']+'/1' for d in protocol['datasets']])
    save = dict(slug=metadata['id'], new_title=metadata['title'], is_private=True,
        enable_gpu=True, enable_tpu=False, enable_internet=False, machine_shape='NvidiaRtxPro6000',
        session_timeout_seconds=3600, docker_image=metadata['docker_image'],
        docker_image_pinning_type='original', dataset_data_sources=metadata['dataset_sources'],
        competition_data_sources=metadata['competition_sources'], kernel_data_sources=[], model_data_sources=[],
        language='python', kernel_type='notebook')
    files = {'runtime/'+n:raw for n,raw in runtime.items()}
    files.update(records)
    files.update({'profile.ipynb':canonical(book), 'kernel-metadata.json':canonical(metadata),
        'launch-spec.json':canonical({'save_fields':save,'maximum_save_calls':1,'automatic_retries':0}),
        'scope.json':canonical(SCOPE), 'time-policy-amendment.json':amendment_raw,
        'staging-plan.json':plan_raw, 'runtime-payload.json':payload,
        'review-evidence/known-owner-notebook.json':Path(known_path).read_bytes(),
        'validation/checks.json':validation_path.read_bytes()})
    # The earlier notebook identity establishes catalogue access only, never a
    # MolmoPoint installation or model inference result.
    for name in validation['evidence_sha256']:
        files['validation/'+name] = (validation_path.parent/name).read_bytes()
    previous_files = json.loads((previous/'review-lock.json').read_bytes())['artifacts']
    for name in previous_files:
        if name.startswith(('licences/', 'model-dataset-extra/')) or name in ('model-card.md','dependency-manifest.json','evaluation-binding.json','checkpoint-verification.json'):
            files[name] = (previous/name).read_bytes()
    # Bind the actual replay checkout, including operator and scientific scoring.
    evaluation = json.loads(files['evaluation-binding.json'])
    evaluation['source_sha256'] = {n:D.digest((ROOT/n).read_bytes()) for n in evaluation['source_sha256']}
    files['evaluation-binding.json'] = canonical(evaluation)
    files['model-dataset-extra/LICENSE-APACHE-2.0.txt'] = (ROOT/'research/molmopoint_identification_v1/LICENSE-APACHE-2.0.txt').read_bytes()
    if wheel_terms is not None or prior_use is not None:
        if wheel_terms is None or prior_use is None:
            raise ValueError('wheel terms require their retained provenance record')
        use_raw = Path(prior_use).read_bytes()
        use = json.loads(use_raw)
        terms = {n:h for n,h in use['licence_files_sha256'].items()
                 if n.startswith('licences/retained-wheel-term-')}
        if len(terms) != 23:
            raise ValueError('expected 23 retained wheel terms')
        for name, pin in terms.items():
            path = Path(wheel_terms)/Path(name).name
            raw = path.read_bytes()
            if D.digest(raw) != pin:
                raise ValueError('retained wheel terms differ')
            files[name] = raw
        files['review-evidence/prior-wheel-use-provenance-not-current-approval.json'] = use_raw
    files['review.md'] = b'''# Private MolmoPoint six-board live template

Prepared, awaiting exact source/use/compute approval. No reservation or launch.
Exactly one RTX PRO 6000; requested session timeout 3600 s, worker 3300 s,
work cutoff 3000 s and cleanup reserve 300 s. Provider overhead may extend
the whole job beyond one hour. Six greedy generations, <=1024 tokens each,
6144 total, no retries, game actions or scorecards. Internet and TPU off.

Model: allenai/MolmoPoint-8B, revision 188130f961c8e0888a34e11121a1423c461a01ba.
Plain 448px boards, fixed prompts, native point decoder, exact occupied-cell
scoring. References stay local; no answers/masks are uploaded or embedded.
All 220 mounted files are verified by hash before isolated 48-package install.
The private datasets were verified by owner access, version and inventory;
those listings do not replace the runtime byte checks. Competition attached
for accelerator eligibility; no game calls or submission is implemented.

CPU checks cover preprocessing and a tiny random-model API rehearsal only.
The complete isolated CUDA installation and full checkpoint GPU inference
are not yet tested. The historical CPU notebook record is solely a known
owner catalogue identity; it is not evidence of MolmoPoint installation.

Only the first AUTHORITY literal data assignment may change after approval.
All other notebook/configuration/source bytes are bound. Before submission,
fresh account/quota/target/privacy/version/inventory preflight is mandatory.
Consume one reservation and check the actual request body before forwarding.
Stop on failures or a hardware mismatch. Preserve every prior attempt.

Private account-only research and sanitized aggregate summaries only are
proposed. The pinned model card, Apache text and wheel licences are retained.
Use clearance and exact-package approval remain pending owner review.
Completion needs provider COMPLETE, post-write witness/cell marker, cleanup
and independent token/point replay. This is cued localization, not discovery
or gameplay competence.
'''
    operator_names = ['research/molmopoint_identification_v1/'+n+'.py' for n in ('deployment','operations','operator','kaggle_operator')]
    all_sources = set(source_names) | set(operator_names) | set(evaluation['source_sha256'])
    if not (all_sources | {'scripts/build_molmopoint_live.py'}) <= set(validation['source_sha256']):
        raise ValueError('source verification does not cover complete current package/operator/builder')
    lock = dict(schema='molmopoint_final_live_review_v1', artifacts={n:D.digest(raw) for n,raw in sorted(files.items())},
        source_sha256={n:D.digest((ROOT/n).read_bytes()) for n in sorted(all_sources)},
        builder_sha256=D.digest(Path(__file__).read_bytes()), prior_candidate_review_lock_sha256=prior,
        runtime_lock_sha256=D.digest(runtime['runtime-lock.json']), scope=SCOPE)
    output.mkdir(parents=True)
    for name, raw in files.items():
        path = output/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw)
    (output/'review-lock.json').write_bytes(canonical(lock))
    return {'review_lock_sha256':D.verify_review(output), 'provider_calls':0, 'GPU_launches':0,
            'approval_recorded':False, 'output':str(output)}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('previous','plan','model-receipt','inputs-receipt','validation','amendment','known-notebook','output'):
        p.add_argument('--'+name,required=True)
    p.add_argument('--wheel-terms',required=True)
    p.add_argument('--prior-use',required=True)
    a = p.parse_args()
    print(json.dumps(build(a.previous,a.plan,{'model':a.model_receipt,'inputs':a.inputs_receipt},
        a.validation,a.amendment,a.known_notebook,a.output,
        wheel_terms=a.wheel_terms,prior_use=a.prior_use),indent=2))
