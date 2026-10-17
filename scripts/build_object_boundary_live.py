"""Build an uncued private template from verified existing sources. Never launch."""
import argparse
import base64
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.object_discovery_boundaries_v1 import deployment as D
from research.object_discovery_boundaries_v1.evaluation import verified_preparation,validate_review
from research.object_discovery_boundaries_v1.prepare import requests_for
from research.object_discovery_boundaries_v1.supervisor import SCOPE
from research.object_identification_v1.mount_check import canonical


def build(previous,preparation,reference_bundle,context_path,validation_path,output):
    previous,preparation,reference_bundle,output=map(Path,(previous,preparation,reference_bundle,output))
    if output.exists():raise FileExistsError('preserve every earlier package')
    previous_pin=D.verify_review(previous)
    source=verified_preparation(preparation);requests_for(preparation/'inputs')
    refs={p.name:p.read_bytes() for p in reference_bundle.iterdir() if p.is_file()}
    manifest=json.loads(refs['manifest.json'])
    for name,pin in manifest.items():
        if D.digest(refs[name])!=pin:raise ValueError('owner reference manifest differs')
    review=json.loads(refs['confirmed-review.json']);attestation=json.loads(refs['owner-attestation.json'])
    if (review['owner_confirmation_sha256']!=D.digest(refs['owner-attestation.json'])
            or attestation['export_sha256']!=D.digest(refs['original-owner-export.json'])):
        raise ValueError('owner reference attestation differs')
    validate_review(review,source)
    if not all(f['reference_exhaustive_confirmed'] for f in review['frames']):raise ValueError('incomplete reference inventory')
    context_raw=Path(context_path).read_bytes();context=json.loads(context_raw)
    if context.get('status')!='passed_read_only' or context.get('provider_writes')!=0:raise ValueError('provider context failed')
    validation_raw=Path(validation_path).read_bytes();validation=json.loads(validation_raw)
    if (not validation['linux']['tests'] or any(validation['linux'][k] for k in ('failures','errors','skipped','returncode'))):
        raise ValueError('Linux CPU verification incomplete')
    for name,pin in validation['source_sha256'].items():
        if D.digest((ROOT/name).read_bytes())!=pin:raise ValueError('CPU source verification stale: '+name)
    protocol=json.loads((previous/'runtime/protocol.json').read_bytes())
    for item in protocol['datasets']:
        current=next(r for r in context['datasets'] if r['kind']==item['kind'])
        facts=current['facts'];expected={r['name']:r['bytes'] for r in item['files']}
        if facts['ref']!=item['ref'] or facts['version']!=item['version'] or not current['inventory']['passed']:
            raise ValueError('attachment identity differs')
        if set(current['files'])!=set(expected) or any(n is not None and current['files'][k]!=n for k,n in expected.items()):
            raise ValueError('attachment inventory differs')
        if item['kind']!='wheelhouse' and not (facts['private'] and facts['ready'] and facts['collaborators']==0):
            raise ValueError('attachment privacy/readiness differs')
    agent={p.name:p.read_bytes() for p in (preparation/'inputs').iterdir()}
    protocol.update(schema='object_discovery_boundaries_uncued_v1',scope=SCOPE,live_runs_enabled=True,
        source_bindings_confirmed=True,intended_live_notebook=context['new_target'],
        agent_input_files=[dict(name=n,bytes=len(raw),sha256=D.digest(raw)) for n,raw in sorted(agent.items())],
        input_policy='Seven embedded uncued artifacts only. Existing input dataset reused for installation wheels; previous target prompts never enter worker staging or model context.',
        generation='Six greedy uncued whole-object inventories; native constraints; 4096 new tokens maximum each',
        condition='uncued_whole_inventory',boundary_method='seed_color_component_4',match_iou=.5,
        passing_verdict=None,pretrained_weights_dtype='bfloat16')
    names=['research/object_discovery_boundaries_v1/'+n+'.py' for n in (
        '__init__','supervisor','inference','prepare','decoding','masks','reference_audit')]+[
        'research/molmopoint_identification_v1/'+n for n in ('__init__.py','adapter.py','model_pin.json','runtime_requirements.lock')]+[
        'research/object_identification_v1/'+n+'.py' for n in ('__init__','mount_check','install_check')]+[
        'certification/direct_publisher_smoke_v1/'+n+'.py' for n in ('__init__','install','server')]+[
        'certification/phase4_multimodal_preflight_v3/'+n+'.py' for n in ('__init__','images')]
    runtime={'reviewed-source/'+n:(ROOT/n).read_bytes() for n in names}
    for name in ('research/__init__.py','certification/__init__.py'):
        runtime['reviewed-source/'+name]=(ROOT/name).read_bytes() if (ROOT/name).exists() else b''
    runtime.update({'agent-inputs/'+n:raw for n,raw in agent.items()})
    runtime['protocol.json']=canonical(protocol)
    runtime['runtime-lock.json']=canonical(dict(schema='uncued_object_boundary_runtime_lock_v1',
        artifacts={n:D.digest(raw) for n,raw in sorted(runtime.items())}))
    payload=canonical({n:base64.b64encode(raw).decode() for n,raw in sorted(runtime.items())})
    book=json.loads((previous/'profile.ipynb').read_bytes())
    if D.authority_from(book) is not None:raise ValueError('prior template authority must be empty')
    book['cells'][-1]['source']=D.bootstrap(payload).splitlines(keepends=True)
    metadata=json.loads((previous/'kernel-metadata.json').read_bytes())
    metadata.update(id=context['new_target'],title='ARC3 Uncued Object Discovery and Boundaries V1')
    save=json.loads((previous/'launch-spec.json').read_bytes())
    save['save_fields'].update(slug=metadata['id'],new_title=metadata['title'])
    files={'runtime/'+n:raw for n,raw in runtime.items()}
    files.update({'references/'+n:raw for n,raw in refs.items()})
    files.update({'profile.ipynb':canonical(book),'kernel-metadata.json':canonical(metadata),'launch-spec.json':canonical(save),
        'runtime-payload.json':payload,'scope.json':canonical(SCOPE),'validation/checks.json':validation_raw,
        'review-evidence/current-provider-context.json':context_raw,
        'review-evidence/known-owner-notebook.json':canonical(dict(target=context['known_target']))})
    prior_lock=json.loads((previous/'review-lock.json').read_bytes())
    for name in prior_lock['artifacts']:
        if name.startswith(('licences/','model-dataset-extra/')) or name in (
            'time-policy-amendment.json','model-card.md','dependency-manifest.json','checkpoint-verification.json',
            'review-evidence/prior-wheel-use-provenance-not-current-approval.json'):
            files[name]=(previous/name).read_bytes()
    operator_names=['research/object_discovery_boundaries_v1/'+n+'.py' for n in (
        'deployment','operations','operator','kaggle_operator','live_evaluation','evaluation','scoring','experiment')]
    source_names=sorted(set(names+operator_names+['scripts/build_object_boundary_live.py']))
    if not set(source_names)<=set(validation['source_sha256']):raise ValueError('verification does not cover complete source')
    files['evaluation-binding.json']=canonical(dict(match_iou=.5,primary_level='whole',passing_verdict=None,
        source_sha256={n:D.digest((ROOT/n).read_bytes()) for n in source_names},
        reference_files_sha256={'references/'+n:D.digest(raw) for n,raw in refs.items()}))
    files['review.md']=('''# Private uncued discovery/boundary pilot

Exactly one RTX PRO 6000. Requested session timeout 3600s; worker 3300s,
work cutoff 3000s, cleanup reserve 300s. Provider overhead can extend total
time beyond one hour under the retained owner amendment. Six generations,
4096 new tokens and 96 points maximum each, no automatic retries, actions
or scorecards. Private account-only notebook and raw outputs; sanitized
summaries only. No online gameplay or competition submission.

Same pinned MolmoPoint checkpoint, immutable Kaggle image and 48-package
hash-pinned runtime as the completed cued test. All 220 mounted files are
hashed before installation. The existing input dataset provides the two
installation wheels; its old target prompts are not read by the model worker.
Seven embedded files provide six plain 448px boards and the generic prompt.
Raw tokens precede native decoding; each predicted seed yields a same-color
four-connected region. Duplicates, background seeds and multicolor splits
remain. References are outside the executable notebook payload and mounted
model inputs. Whole objects primary; parts not a separate model condition.

Owner-confirmed references: 37 whole objects, 57 parts, six complete initial
boards. One owner review only. Exposed development examples, no held-out or
model-only segmentation claim. IoU 0.5 matching is diagnostic; no advancement
pass threshold. All six cases retained, including invalid outputs.

Completion requires provider COMPLETE, post-write witness and saved-cell
marker, process/GPU cleanup, exact request/token/native-point replay and
independently reconstructed masks. Original cued attempt remains consumed.
Only AUTHORITY literal may change after approval. Missing authority refuses
before extraction, install or GPU query. Fresh read-only preflight and a
single-use reservation/claim precede the single provider SaveKernel.
''').encode()
    lock=dict(schema='uncued_object_boundary_live_review_v1',artifacts={n:D.digest(raw) for n,raw in sorted(files.items())},
        source_sha256={n:D.digest((ROOT/n).read_bytes()) for n in source_names},
        builder_sha256=D.digest(Path(__file__).read_bytes()),scope=SCOPE,
        prior_completed_cued_review_lock_sha256=previous_pin,runtime_lock_sha256=D.digest(runtime['runtime-lock.json']))
    output.mkdir(parents=True)
    for name,raw in files.items():
        p=output/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    (output/'review-lock.json').write_bytes(canonical(lock))
    return dict(review_lock_sha256=D.verify_review(output),runtime_lock_sha256=lock['runtime_lock_sha256'],
                provider_writes=0,GPU_jobs=0,output=str(output))


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ('previous','preparation','reference-bundle','context','validation','output'):cli.add_argument('--'+name,required=True)
    a=cli.parse_args();print(json.dumps(build(a.previous,a.preparation,a.reference_bundle,a.context,a.validation,a.output)))
