"""Build a private, gated MolmoPoint review notebook; never upload or submit."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.molmopoint_identification_v1.adapter import verify_snapshot,MODEL,REVISION
from research.molmopoint_identification_v1.inference import requests_for
from research.molmopoint_identification_v1.supervisor import SCOPE
from research.object_identification_v1.mount_check import canonical
from research.object_identification_v1.deployment import bootstrap

IMAGE='gcr.io/kaggle-private-byod/python@sha256:37c64f7dd9c54116ecd1bcc88817c5469b88387388fade02bfa8bf3fc647d461'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def build(model,preparation,dependencies,publisher_protocol,validation,output):
    model,preparation,dependencies,output=map(Path,(model,preparation,dependencies,output))
    if output.exists():
        raise FileExistsError('preserve previous review packages')
    validation=Path(validation)
    proof=json.loads(validation.read_bytes())
    if (proof['linux']['failures'] or proof['linux']['errors'] or proof['linux']['skipped']
            or proof['linux']['returncode']!=0 or proof['pretrained_generations']!=0):
        raise ValueError('CPU source verification did not pass')
    for name,digest in proof['source_sha256'].items():
        if sha((ROOT/name).read_bytes())!=digest:
            raise ValueError('CPU verification is stale: '+name)
    validation_files={}
    for name,digest in proof['evidence_sha256'].items():
        raw=(validation.parent/name).read_bytes()
        if sha(raw)!=digest:
            raise ValueError('CPU verification evidence differs')
        validation_files['validation/'+name]=raw
    verified=verify_snapshot(model)
    original=json.loads((preparation/'preparation-manifest.json').read_bytes())
    for name,digest in original.items():
        if sha((preparation/name).read_bytes()) != digest:
            raise ValueError('prepared inputs or references changed')
    requests_for(preparation/'inputs')
    dependency_manifest=(ROOT/'research/molmopoint_identification_v1/runtime_dependencies.json').read_bytes()
    runtime_lock=(ROOT/'research/molmopoint_identification_v1/runtime_requirements.lock').read_bytes()
    deps=json.loads(dependency_manifest)
    if sha(runtime_lock)!=deps['requirements_sha256']:
        raise ValueError('dependency lock differs')
    upload={p.name:p.read_bytes() for p in (preparation/'inputs').iterdir()}
    licences={}
    for row in deps['packages']:
        if row['acquisition'].startswith('https:'):
            raw=(dependencies/row['filename']).read_bytes()
            if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:
                raise ValueError('new dependency wheel differs')
            upload[row['filename']]=raw
            with zipfile.ZipFile(dependencies/row['filename']) as wheel:
                found=[]
                for member in wheel.namelist():
                    relative=Path(member)
                    if relative.is_absolute() or '..' in relative.parts:
                        raise ValueError('unsafe wheel member')
                    if not member.endswith('/') and relative.name.upper().startswith(('LICENSE','LICENCE','COPYING','NOTICE')):
                        found.append(member)
                        licences['licences/'+row['name']+'/'+member]=wheel.read(member)
                if not found:
                    raise ValueError('new dependency licence text missing')
    prior=json.loads(Path(publisher_protocol).read_bytes())
    publisher=next(row for row in prior['datasets'] if row['kind']=='publisher_wheels')
    if publisher['ref']!='driessmit1/arc3-vllm-h100-wheelhouse-v3' or publisher['version']!=1:
        raise ValueError('publisher dataset identity differs')
    publisher=dict(publisher,kind='wheelhouse')
    old={row['name']:row['sha256'] for row in publisher['files']}
    if any(old.get(r['filename'])!=r['sha256'] for r in deps['packages']
           if not r['acquisition'].startswith('https:')):
        raise ValueError('publisher does not cover exact dependency artifacts')
    inputs_ref='daichongwei06/arc3-molmopoint-targeted448-inputs-v1'
    model_ref='daichongwei06/arc3-molmopoint-8b-pinned-v1'
    datasets=[publisher,dict(kind='model',ref=model_ref,version=1,files=[
        dict(name=n,sha256=h,bytes=(model/n).stat().st_size) for n,h in sorted(verified['files_sha256'].items())]),
        dict(kind='inputs',ref=inputs_ref,version=1,files=[
            dict(name=n,sha256=sha(raw),bytes=len(raw)) for n,raw in sorted(upload.items())])]
    protocol=dict(schema='molmopoint_targeted448_v1',scope=SCOPE,model=MODEL,revision=REVISION,
        intended_private_account='daichongwei06',intended_live_notebook='daichongwei06/arc3-molmopoint-targeted448-v1',
        live_runs_enabled=False,source_bindings_confirmed=False,datasets=datasets,
        input_policy='plain448 nearest-neighbor; six frozen prompts; no overlays or references',
        pretrained_weights_dtype='bfloat16',generation='greedy; native logits constraints; 1024 new tokens maximum each',
        expected_image=IMAGE,provider_full_job_cap_verified=False,
        evidence_completion='provisional receipt + post-write witness + cell marker + provider COMPLETE + independent replay')
    sources=[
        'research/molmopoint_identification_v1/__init__.py',
        'research/molmopoint_identification_v1/adapter.py','research/molmopoint_identification_v1/inference.py',
        'research/molmopoint_identification_v1/supervisor.py','research/molmopoint_identification_v1/model_pin.json',
        'research/molmopoint_identification_v1/runtime_requirements.lock',
        'research/object_identification_v1/__init__.py','research/object_identification_v1/mount_check.py',
        'research/object_identification_v1/install_check.py',
        'certification/direct_publisher_smoke_v1/__init__.py',
        'certification/direct_publisher_smoke_v1/install.py','certification/direct_publisher_smoke_v1/server.py']
    runtime={'reviewed-source/'+n:(ROOT/n).read_bytes() for n in sources}
    # Isolate namespace roots from unrelated host packages; the repository itself
    # uses namespace packages, so these two reviewed initializers are empty.
    for name in ('research/__init__.py','certification/__init__.py'):
        runtime['reviewed-source/'+name]=b''
    runtime['protocol.json']=canonical(protocol)
    runtime['runtime-lock.json']=canonical(dict(schema='molmopoint_runtime_lock_v1',
        artifacts={n:sha(raw) for n,raw in sorted(runtime.items())}))
    payload=canonical({n:base64.b64encode(raw).decode() for n,raw in sorted(runtime.items())})
    code=bootstrap(payload).replace('internvl-object-identification-runtime','molmopoint-targeted448-runtime').replace(
        'research.object_identification_v1.supervisor','research.molmopoint_identification_v1.supervisor')
    book=dict(nbformat=4,nbformat_minor=5,metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3')),
        cells=[dict(cell_type='code',id='launch-authority',metadata={},execution_count=None,outputs=[],source=['AUTHORITY = None\n']),
               dict(cell_type='code',id='bootstrap',metadata={},execution_count=None,outputs=[],source=code.splitlines(keepends=True))])
    metadata=dict(id=protocol['intended_live_notebook'],title='ARC3 MolmoPoint Targeted448 V1',
        code_file='profile.ipynb',language='python',kernel_type='notebook',is_private=True,
        enable_gpu=False,enable_tpu=False,enable_internet=False,docker_image=IMAGE,
        docker_image_pinning_type='original',dataset_sources=[d['ref']+'/'+str(d['version']) for d in datasets],
        competition_sources=[],kernel_sources=[],model_sources=[])
    files={'runtime/'+n:raw for n,raw in runtime.items()}
    files.update({'profile.ipynb':canonical(book),'kernel-metadata.json':canonical(metadata),
        'scope.json':canonical(SCOPE),'checkpoint-verification.json':canonical(verified),
        'dependency-manifest.json':dependency_manifest,
        'evaluation-binding.json':canonical({'source_sha256':{n:sha((ROOT/n).read_bytes()) for n in [
            'research/molmopoint_identification_v1/evaluate.py','research/molmopoint_identification_v1/scoring.py']},
            'references_sha256':{n:h for n,h in original.items() if n.startswith('references/')},
            'references_shipped_to_inference':False}),
        'pending-gates.json':canonical(dict(approved=False,reserved=False,launched=False,
            dataset_uploads=0,pretrained_generations=0,blockers=[
            'MolmoPoint-specific scoped use and private staging approval',
            'model and input datasets not created/attached; proposed names only',
            'exact private live package/source approval after attachment binding',
            'fresh GPU compute authorization and single-use reservation/claim',
            'provider-side pinned image/allocation and offline installation not yet validated for MolmoPoint']))})
    files.update(licences)
    files.update(validation_files)
    files['validation/verification.json']=validation.read_bytes()
    files['model-card.md']=(model/'README.md').read_bytes()
    files['review.md']=('''# MolmoPoint six-board review candidate

Review only. No authority, reservation, upload or model inference is recorded.
The proposed new model/input datasets do not exist yet; attachment receipts are
required before deriving and approving a final live package. The notebook is
GPU/TPU/internet disabled and refuses at its empty authority slot.

One proposed RTX PRO 6000 attempt: requested session timeout 3,600 seconds,
worker limit 3,300 seconds, work cutoff 3,000 seconds and 300 seconds for cleanup.
Allocation, mounting and provider release can extend total time beyond one hour.
Six fixed cued targets, one greedy generation each, at most 1,024 new tokens,
zero game actions/scorecards and zero automatic retries. Plain448 RGB images,
nearest-neighbor 7x7 cells, no overlay, crop or added margins.

The immutable model revision is 188130f961c8e0888a34e11121a1423c461a01ba.
All 33 snapshot files and every mounted input/wheel must match SHA256 before
installing or importing model code. The separate runtime has 48 exact pins.
The two newly acquired wheels' retained licences and pinned model card are in
this review package; a MolmoPoint-specific scoped-use outcome is not supplied.

Raw continuation IDs, prompt IDs, native metadata, text, points and admissions
are retained. Incomplete points and multiple points cannot earn a target hit.
References stay local, outside model inputs. Independent CPU replay checks the
reviewing checkout, exact prompts, metadata and decoder results before scoring.
Technical completion additionally requires provider COMPLETE, the saved-cell
witness and verified process/GPU cleanup. A receipt alone cannot pass.

A passing cued hit does not establish discovery, masks, obstacle semantics,
click execution, gameplay or an advantage over InternVL. No gameplay is wired.
''').encode()
    output.mkdir(parents=True)
    for name,raw in files.items():
        path=output/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(raw)
    lock=canonical(dict(schema='molmopoint_review_lock_v1',artifacts={n:sha(raw) for n,raw in sorted(files.items())}))
    (output/'review-lock.json').write_bytes(lock)
    stage=output.parent/(output.name+'-input-staging')
    stage.mkdir()
    for name,raw in upload.items():
        (stage/name).write_bytes(raw)
    print(json.dumps(dict(review_lock_sha256=sha(lock),runtime_lock_sha256=sha(runtime['runtime-lock.json']),
        prepared_input_files=len(upload),checkpoint_files=len(verified['files_sha256']),GPU_launches=0)))


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    for name in ('model','preparation','dependencies','publisher-protocol','validation','output'):
        cli.add_argument('--'+name,required=True)
    a=cli.parse_args()
    build(a.model,a.preparation,a.dependencies,a.publisher_protocol,a.validation,a.output)
