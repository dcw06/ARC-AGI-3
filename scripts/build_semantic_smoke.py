"""Build the exact private one-image Semantic-SAM package locally; never submits."""
import argparse
import base64
import json
from pathlib import Path
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import build_semantic_transport_check as CPU
from research.object_discovery_boundaries_v1.archive_transport import canonical,digest,manifest
from research.object_discovery_boundaries_v1.semantic_smoke import SCOPE,authority_check


def verify_review(package): return CPU.verify_review(package)


def seal(package,authority):
    package = Path(package); pin = verify_review(package)
    protocol = json.loads((package/'runtime/protocol.json').read_bytes())
    authority_check(protocol,authority)
    if authority['review_lock_sha256']!=pin or authority['runtime_lock_sha256']!=digest((package/'runtime/runtime-lock.json').read_bytes()):
        raise ValueError('authority does not bind exact GPU review/runtime')
    book = json.loads((package/'profile.ipynb').read_bytes())
    if CPU.authority_from(book) is not None: raise ValueError('review slot must be empty')
    book['cells'][0]['source'] = ['AUTHORITY = '+repr(authority)+'\n']
    return book


def validate_save(body,package,authority):
    def field(name):
        parts = name.split('_'); camel = parts[0]+''.join(part.title() for part in parts[1:])
        if name!=camel and name in body and camel in body: raise ValueError('ambiguous field')
        return body.get(camel,body.get(name))
    spec = json.loads((Path(package)/'launch-spec.json').read_bytes())
    for name,expected in spec['save_fields'].items():
        if canonical(field(name))!=canonical(expected): raise ValueError('GPU request differs: '+name)
    execution = field('kernel_execution_type')
    if not ((type(execution) is int and execution==1) or type(execution) is str and execution in
            ('SAVE_AND_RUN_ALL','saveAndRunAll','SaveAndRunAll')): raise ValueError('one save-and-run required')
    if field('id') is not None or field('priority') is not None or field('category_ids') not in (None,[]):
        raise ValueError('numeric target override/priority/extra tags refused')
    if canonical(json.loads(field('text')))!=canonical(seal(package,authority)):
        raise ValueError('sealed notebook changed')
    return True


def build(protocol_path,transport_path,cpu_receipt_path,worker_archive,output):
    output = Path(output)
    if output.exists(): raise FileExistsError('preserve previous GPU packets')
    protocol = json.loads(Path(protocol_path).read_bytes())
    if protocol.get('schema')!='semantic_sam_gpu_smoke_protocol_v1' or canonical(protocol.get('scope'))!=canonical(SCOPE):
        raise ValueError('exact one-image GPU scope required')
    if protocol.get('dataset_version')!=1 or type(protocol['dataset_version']) is not int:
        raise ValueError('version-1 dataset required')
    if not __import__('re').fullmatch('daichongwei06/[A-Za-z0-9_-]+',protocol['notebook_ref']):
        raise ValueError('personal private notebook binding required')
    if not __import__('re').fullmatch(r'gcr\.io/kaggle-private-byod/python@sha256:[0-9a-f]{64}',protocol['docker_image']):
        raise ValueError('immutable image pin required')
    raw_transport = Path(transport_path).read_bytes()
    transport = manifest(raw_transport,protocol['transport_manifest_sha256'],protocol['original_manifest_sha256'])
    worker_pin = next(row for row in transport['originals'] if row['name']=='reviewed-worker-source.tar')
    if Path(worker_archive).stat().st_size!=worker_pin['bytes'] or digest(Path(worker_archive).read_bytes())!=worker_pin['sha256']:
        raise ValueError('worker archive differs from verified original payload')
    receipt_raw = Path(cpu_receipt_path).read_bytes(); receipt = json.loads(receipt_raw)
    if (receipt.get('verified') is not True or receipt.get('provider_status')!='COMPLETE' or
            receipt.get('all_pinned_hashes_match') is not True or receipt.get('temporary_originals_removed') is not True or
            receipt.get('mounted_transport_files_checked')!=21 or receipt.get('restored_originals_checked')!=12 or
            digest(receipt_raw)!=protocol['cpu_verification_sha256']):
        raise ValueError('verified mounted CPU receipt required')
    names = []
    with tarfile.open(worker_archive) as archive:
        for member in archive:
            if not member.isfile() or Path(member.name).is_absolute() or '..' in Path(member.name).parts:
                raise ValueError('flat reviewed source archive required')
            current = ROOT/member.name; raw = archive.extractfile(member).read()
            if not current.exists() and member.name in ('research/__init__.py','certification/__init__.py') and raw==b'':
                continue
            if not current.is_file() or current.read_bytes()!=raw:
                raise ValueError('staged worker source differs: '+member.name)
            names.append(member.name)
    additions = ['research/object_discovery_boundaries_v1/semantic_smoke.py',
        'research/object_discovery_boundaries_v1/archive_transport.py',
        'research/object_discovery_boundaries_v1/transport_check.py']
    names = sorted(set(names+additions))
    runtime = {'protocol.json':canonical(protocol),'transport-manifest.json':raw_transport}
    for name in names: runtime['reviewed-source/'+name] = (ROOT/name).read_bytes()
    for name in ('research/__init__.py','certification/__init__.py'):
        runtime.setdefault('reviewed-source/'+name,b'')
    runtime['runtime-lock.json'] = canonical(dict(artifacts={name:digest(raw) for name,raw in sorted(runtime.items())}))
    runtime_pin = digest(runtime['runtime-lock.json'])
    payload = canonical({name:base64.b64encode(raw).decode() for name,raw in sorted(runtime.items())})
    bootstrap = CPU.bootstrap(payload,digest(payload),runtime_pin).replace(
        'semantic-transport-check-runtime','semantic-sam-smoke-runtime-r1').replace(
        'transport_check import run','semantic_smoke import run').replace(
        'CPU transport check not authorized; no mount read or extraction started.',
        'GPU smoke not authorized; no staging or GPU query started.')
    book = dict(nbformat=4,nbformat_minor=5,metadata=dict(kernelspec=dict(display_name='Python 3',language='python',name='python3')),
        cells=[dict(id='launch-authority',cell_type='code',metadata={},execution_count=None,outputs=[],source=['AUTHORITY = None\n']),
               dict(id='scope',cell_type='markdown',metadata={},source=['# Private Semantic-SAM one-image smoke\n',
                   'sc25 / board-06, seeded and automatic, fixed granularity 1. No reference masks or game actions.\n']),
               dict(id='run',cell_type='code',metadata={},execution_count=None,outputs=[],source=bootstrap.splitlines(keepends=True))])
    metadata = dict(id=protocol['notebook_ref'],title='ARC3 Semantic SAM One Image Smoke V1',code_file='profile.ipynb',
        language='python',kernel_type='notebook',is_private=True,enable_gpu=True,enable_tpu=False,enable_internet=False,
        dataset_sources=[protocol['dataset_ref']+'/1'],kernel_sources=[],model_sources=[],competition_sources=[],
        docker_image=protocol['docker_image'],docker_image_pinning_type='original')
    save = dict(slug=metadata['id'],new_title=metadata['title'],language='python',kernel_type='notebook',
        is_private=True,enable_gpu=True,enable_tpu=False,enable_internet=False,machine_shape='NvidiaRtxPro6000',
        session_timeout_seconds=3600,docker_image=metadata['docker_image'],docker_image_pinning_type='original',
        dataset_data_sources=metadata['dataset_sources'],kernel_data_sources=[],model_data_sources=[],competition_data_sources=[])
    guide = '''# Private one-image Semantic-SAM GPU smoke review

One requested RTX PRO 6000, one attempt, no automatic retries. Private/account-only;
internet and TPU off. Requested session timeout 3,600 seconds; worker 3,300 seconds;
work cutoff 3,000 seconds; cleanup reserve 300 seconds. Provider allocation, mounting,
setup and GPU release can extend the whole job beyond one hour, as previously accepted.

Restore/hash the verified version-1 transport. Extract the isolated portable runtime
at its fixed prefix, source and retained input boards. No package download/install.
Run exactly the sc25 board-06 seeded and automatic conditions at granularity 1 in
separate fresh interpreters. Use the retained MolmoPoint seeds unchanged, plain
448-square input, the fixed 640-square Semantic-SAM preprocessing, automatic grid
16 by 16/batch 16 and at most 96 selected proposals. Retain all raw masks and quality
scores. No new MolmoPoint generation, model HTTP request, game action or scorecard.
Reference masks and owner answers never enter inference. No six-board comparison.

Verify one RTX PRO 6000 and no existing GPU compute process before any model load;
refuse any accelerator mismatch. Register every child before Popen, use isolated
process groups and a subreaper, kill before census, reap children, verify absence,
and remove the extracted interpreter, source, weights and inputs. The separate final
alarm remains active through cleanup and evidence writes. Any late/uncertain cleanup
fails; emergency SIGKILL remains possible without a blocking census or wait.

A provisional receipt passes only with provider COMPLETE, exact saved source/image/
private settings, the matching result/witness/final marker and independently verified
output manifests and raw mask replay. Output masks still require inspection and the
externally frozen local reference evaluator. This notebook is initially disabled:
AUTHORITY=None. Only that literal slot may be filled after actual owner approval
and a fresh single-use claim. All previous attempts remain preserved.
'''
    artifacts = {'runtime/'+name:raw for name,raw in runtime.items()}
    artifacts.update({'profile.ipynb':canonical(book),'kernel-metadata.json':canonical(metadata),
        'launch-spec.json':canonical(dict(save_fields=save,kernel_execution_type='SAVE_AND_RUN_ALL')),
        'scope.json':canonical(SCOPE),'review.md':guide.encode(),'evidence/cpu-verification.json':receipt_raw})
    source_names = sorted(set(names+['scripts/build_semantic_smoke.py','scripts/build_semantic_transport_check.py']))
    lock = dict(schema='semantic_sam_gpu_smoke_review_v1',artifacts={name:digest(raw) for name,raw in sorted(artifacts.items())},
        source_sha256={name:digest((ROOT/name).read_bytes()) for name in source_names},runtime_lock_sha256=runtime_pin,scope=SCOPE)
    output.mkdir(parents=True)
    for name,raw in artifacts.items():
        path = output/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(raw)
    (output/'review-lock.json').write_bytes(canonical(lock))
    return dict(review_lock_sha256=verify_review(output),runtime_lock_sha256=runtime_pin,output=str(output),provider_calls=0)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('protocol','transport-manifest','cpu-receipt','worker-archive','output'): parser.add_argument('--'+name,required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.protocol,args.transport_manifest,args.cpu_receipt,args.worker_archive,args.output),indent=2))
