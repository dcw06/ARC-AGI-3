"""Prepare the exact private live notebook template; no approval, upload or launch."""
import argparse
import base64
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.object_identification_v1.deployment import bootstrap, digest, verify_review
from research.object_identification_v1.mount_check import canonical
from research.object_identification_v1.supervisor import SCOPE
from scripts.serve_manual_strategy_worksheet import private_directory


def build(base, previous, output, *, validation=None, kernel_id=None, title=None, prior_attempt=None):
    base, previous, output = map(Path, (base, previous, output))
    if output.exists():
        raise FileExistsError('preserve every earlier private package')
    old_pin = verify_review(previous)
    old_lock = json.loads((previous/'review-lock.json').read_bytes())
    amendment_raw = (base/'gpu-time-policy-amendment-r1.json').read_bytes()
    amendment = json.loads(amendment_raw)
    if (amendment['prior_candidate_review_lock_sha256'] != old_pin
            or amendment['approved_time_policy_change'] is not True
            or amendment['accepted_provider_overhead'] is not True
            or amendment['session_timeout_seconds'] != 3600 or amendment['worker_seconds'] != 3300
            or amendment['gpu_launch_authorized'] is not False):
        raise ValueError('owner time amendment not established, or mislabelled as launch authority')
    validation_path = Path(validation) if validation else base/'live-package-linux-checks-r1.json'
    validation_log = validation_path.with_suffix('.log')
    validation = json.loads(validation_path.read_bytes())
    if validation['returncode'] != 0 or validation['log_sha256'] != digest(validation_log.read_bytes()):
        raise ValueError('current Linux checks not passed')
    for name, pin in validation['source_sha256'].items():
        if digest((ROOT/name).read_bytes()) != pin:
            raise ValueError('validation is stale: '+name)
    source_names = sorted(set(old_lock['source_sha256']) | {'research/object_identification_v1/deployment.py'})
    runtime = {'reviewed-source/'+name: (ROOT/name).read_bytes() for name in source_names}
    for name in old_lock['artifacts']:
        if name.startswith('reviewed-source/') and name.endswith('/__init__.py'):
            runtime[name] = (previous/name).read_bytes()
    protocol = json.loads((previous/'protocol.json').read_bytes())
    owner = protocol['intended_private_account']
    target = kernel_id or protocol['intended_live_notebook']
    target_title = title or 'ARC3 InternVL Object Identification V1'
    if (not target.startswith(owner+'/') or target.count('/') != 1
            or re.sub('[^a-z0-9]+', '-', target_title.lower()).strip('-') != target.split('/')[1]):
        raise ValueError('notebook owner/title/slug binding differs')
    protocol['intended_live_notebook'] = target
    protocol.update(schema='internvl_object_identification_live_v2', live_runs_enabled=True, scope=SCOPE,
        time_policy={'mode': 'owner_accepted_session_and_worker_limits',
                     'owner_amendment_sha256': digest(amendment_raw),
                     'provider_full_job_cap_verified': False, 'provider_overhead_may_exceed_one_hour': True})
    runtime.update({'protocol.json': canonical(protocol), 'scope.json': canonical(SCOPE),
        'time-policy-amendment.json': amendment_raw,
        'protocol-r2.md': (ROOT/'reports/internvl_object_identification_v1_protocol_r2.md').read_bytes()})
    runtime_lock = {'schema': 'internvl_runtime_lock_v1',
                    'artifacts': {name: digest(raw) for name, raw in sorted(runtime.items())}}
    runtime['runtime-lock.json'] = canonical(runtime_lock)
    payload = canonical({name: base64.b64encode(raw).decode() for name, raw in sorted(runtime.items())})
    notebook = {'nbformat': 4, 'nbformat_minor': 5,
        'metadata': {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}},
        'cells': [{'cell_type': 'code', 'id': 'launch-authority', 'metadata': {},
                   'execution_count': None, 'outputs': [], 'source': ['AUTHORITY = None\n']},
                  {'cell_type': 'markdown', 'id': 'scope', 'metadata': {}, 'source': [
                      '# Private InternVL object identification — live package\n',
                      'One RTX PRO 6000, six generations, no game actions. No launch authority recorded.\n',
                      'Requested session timeout 3600 s; worker 3300 s; provider overhead can exceed one hour.\n']},
                  {'cell_type': 'code', 'id': 'bootstrap', 'metadata': {},
                   'execution_count': None, 'outputs': [], 'source': bootstrap(payload).splitlines(keepends=True)}]}
    metadata = json.loads((previous/'kernel-metadata.json').read_bytes())
    metadata.update(id=target,
        title=target_title, enable_gpu=True, enable_tpu=False,
        enable_internet=False, is_private=True, machine_shape='NvidiaRtxPro6000', session_timeout_seconds=3600)
    save = {'slug': metadata['id'], 'new_title': metadata['title'], 'is_private': True,
        'enable_gpu': True, 'enable_tpu': False, 'enable_internet': False,
        'machine_shape': 'NvidiaRtxPro6000', 'session_timeout_seconds': 3600,
        'docker_image': metadata['docker_image'], 'docker_image_pinning_type': metadata['docker_image_pinning_type'],
        'dataset_data_sources': metadata['dataset_sources'], 'competition_data_sources': metadata.get('competition_sources', []),
        'kernel_data_sources': [], 'model_data_sources': [], 'language': 'python', 'kernel_type': 'notebook'}
    files = {'runtime/'+name: raw for name, raw in runtime.items()}
    spent = []
    for slot in sorted((base/'gpu-reservation-registry-v2').glob('*')):
        if slot.is_symlink() or not slot.is_dir():
            raise ValueError('uncertain consumed-attempt registry entry')
        raw = (slot/'claim.json').read_bytes()
        claim = json.loads(raw)
        if claim.get('consumed') is not True or claim.get('attempt_id') != slot.name:
            raise ValueError('invalid consumed-attempt record')
        files['history/'+slot.name+'/claim.json'] = raw
        spent.append(claim)
    if spent:
        if prior_attempt is None:
            raise ValueError('consumed attempts require their retained terminal evidence')
        prior_raw = Path(prior_attempt).read_bytes()
        prior = json.loads(prior_raw)
        if (prior.get('attempt_consumed') is not True or prior.get('provider_status') != 'ERROR'
                or prior.get('runtime_result', {}).get('review_lock_sha256') not in {
                    row['review_lock_sha256'] for row in spent}):
            raise ValueError('prior failed-attempt evidence does not match consumed registry')
        files['history/prior-failed-attempt-collection.json'] = prior_raw
    for name in old_lock['artifacts']:
        if name.startswith(('evidence/', 'licences/')) or name == 'evaluation_binding.json':
            files['review-evidence/'+name] = (previous/name).read_bytes()
    files.update({'profile.ipynb': canonical(notebook), 'runtime-payload.json': payload,
        'kernel-metadata.json': canonical(metadata), 'launch-spec.json': canonical({'save_fields': save,
            'kernel_execution_type': 'SAVE_AND_RUN_ALL', 'maximum_save_calls': 1, 'automatic_retries': 0}),
        'scope.json': canonical(SCOPE), 'protocol-r2.md': runtime['protocol-r2.md'],
        'protocol-r1-preserved.md': (ROOT/'reports/internvl_object_identification_v1_protocol_r1.md').read_bytes(),
        'time-policy-amendment.json': amendment_raw,
        'scoped-use-approval-basis.json': (base/'gpu-owner-approval-r1/scoped_use_approval.json').read_bytes(),
        'validation/linux-checks.json': validation_path.read_bytes(),
        'validation/linux-checks.log': validation_log.read_bytes(),
        'late-binding-contract.json': canonical({'schema': 'internvl_authority_slot_v1',
            'cell_index': 0, 'cell_id': 'launch-authority', 'permitted_change': 'one literal AUTHORITY dictionary assignment',
            'all_other_notebook_and_metadata_changes_forbidden': True,
            'runtime_lock_sha256': digest(runtime['runtime-lock.json']), 'runtime_payload_sha256': digest(payload),
            'must_retain_sealed_execution_notebook_sha256_before_save': True}),
        'status.json': canonical({'status': 'final_live_template_prepared_awaiting_exact_hash_approval',
            'source_approval': None, 'compute_authorization': None, 'launch_claim': None,
            'provider_full_job_cap_verified': False, 'time_policy_amendment_recorded': True,
            'scoped_use_approval_basis_retained': True, 'CPU_attempts_consumed_and_preserved': 2,
            'GPU_attempts_consumed_for_this_probe': len(spent), 'provider_calls_during_this_build': 0})})
    files['review.md'] = ('''# Final private InternVL live package

Prepared only. This successor has not been uploaded, saved, allocated or launched.
The owner's time amendment is recorded; it explicitly does not authorize launch.
Two consumed CPU attempts and all earlier candidates/approvals/reservations remain intact.
Earlier consumed GPU attempts: %d. Their claims and terminal evidence are bound in history/.

One RTX PRO 6000 under the account in kernel-metadata.json, private notebook/raw outputs,
TPU and internet off. Requested Kaggle session timeout 3,600 seconds; worker 3,300 seconds
including cleanup/finalization, work cutoff 3,000 seconds, 300 seconds cleanup reserve.
Provider allocation/setup/mounting/release may add time beyond one hour; no enforced
whole-job cap is claimed. Six generations, <=4,096 tokens each / <=24,576 total;
zero game actions and scorecards, one attempt, no automatic retries. See protocol-r2.md.

The same immutable image and exact versioned model/input/publisher datasets from the
completed CPU checks are bound. All 216 mounted hashes are verified again before the
fresh 175-wheel isolated installation. Full real-checkpoint loading and GPU inference
remain untested. Partial responses, errors, token details and cleanup evidence are retained.

The notebook metadata requests GPU, but its AUTHORITY=None cell makes it refuse before
installation, GPU queries or model loading. After approval of this exact review lock,
only the declared literal authority-data cell may be filled with lock-bound source/use/
time/compute records, hashed evidence and the single-use consumed claim. All other
notebook cells, metadata and runtime bytes must match exactly. The sealed notebook's
execution hash is retained separately; it is not substituted for this review hash.
The offline deployment.validate_save guard checks actual outgoing source/configuration.

Approval of this review hash is still required. Scoped-use approval is retained as its
prior unchanged-scope basis, not relabelled as current source/compute authorization.
Before any save: recheck dataset inventories/target/account/quota/current availability,
bind fresh approval and reservation, consume a one-use claim, seal and validate the
exact request, then permit one SaveKernel with retries disabled. No trial GPU launch.

Collection requires provider COMPLETE, exact saved source/image/settings, manifest and
witness/marker verification, process/GPU cleanup and token/request replay before scoring.
Human reference labels are excluded from the notebook/runtime. Runtime source is retained
as declared evidence; temporary installation/cache files are removed.

The supervisor preserves only absolute LD_LIBRARY_PATH entries from the host for its
otherwise isolated child environment. It writes bounded driver-loader.json evidence
before the first GPU query. CPU loader regressions do not prove the real Kaggle driver
is available. Exact hardware and successful GPU cleanup remain mandatory at runtime.
''' % len(spent)).encode()
    lock = {'schema': 'internvl_final_live_review_v1',
        'artifacts': {name: digest(raw) for name, raw in sorted(files.items())},
        'source_sha256': {name: digest((ROOT/name).read_bytes()) for name in source_names},
        'builder_sha256': digest(Path(__file__).read_bytes()), 'scope': SCOPE,
        'prior_candidate_review_lock_sha256': old_pin,
        'runtime_lock_sha256': digest(runtime['runtime-lock.json']), 'runtime_payload_sha256': digest(payload)}
    files['review-lock.json'] = canonical(lock)
    private_directory(output)
    for name, raw in files.items():
        path = output/name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    return {'prepared': str(output), 'review_lock_sha256': digest(files['review-lock.json']),
        'runtime_lock_sha256': lock['runtime_lock_sha256'], 'provider_calls': 0, 'gpu_launches': 0,
        'launch_approval_recorded': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('base', 'previous', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--validation', type=Path)
    parser.add_argument('--kernel-id')
    parser.add_argument('--title')
    parser.add_argument('--prior-attempt', type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.base, args.previous, args.output, validation=args.validation,
                           kernel_id=args.kernel_id, title=args.title, prior_attempt=args.prior_attempt), indent=2))
