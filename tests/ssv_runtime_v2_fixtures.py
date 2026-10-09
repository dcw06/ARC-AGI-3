"""Synthetic, test-only authority trees for the runtime v2 gate. Never written inside the repository; every record
says it is synthetic. They prove the gate's positive path and its refusals without creating real approvals."""
import copy
import hashlib
import json
from pathlib import Path
import shutil

from research.stagnation_supervision_runtime_v2 import authority as A
from research.stagnation_supervision_runtime_v2.closure import closure

OWNER = 'synthetic-owner'
MODEL = 'synthetic-owner/qwen-snapshot/1'
MOUNT = '/kaggle/input/datasets/synthetic-owner/qwen-snapshot'
ATTEMPT = 'ssv1rt2-synthetic-0001'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(root, name, value):
    path = Path(root) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=1), encoding='utf-8')
    return sha(path)


def provenance(answer):
    return {'type': 'user_confirmation', 'message_reference': 'synthetic-test-message', 'answer_reference': answer,
            'verbatim_text': 'synthetic test only', 'interpretation_only': False}


def resolved_protocol(root):
    path = Path(root) / A.PROTOCOL
    protocol = json.loads(path.read_bytes())
    protocol['kernel_ids'] = {s: f'{OWNER}/arc3-ssv1-runtime-v2-session-{s}' for s in ('1', '2')}
    protocol['model'] = {**protocol['model'], 'kaggle_source': MODEL, 'mounted_path': MOUNT}
    path.write_text(json.dumps(protocol, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    return protocol


def source_tree(root):
    """Copy the payload closure and the bound science files into `root`."""
    root = Path(root)
    protocol = json.loads((A.ROOT / A.PROTOCOL).read_bytes())
    names = set(closure(A.ROOT)['files']) | set(protocol['science']['files'])
    for name in names:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(A.ROOT / name, target)
    return sorted(names)


def authority_tree(root, *, session='1', claim=True, review=True):
    """A complete synthetic authority set over a placeholder-free copy of the successor sources."""
    from research.stagnation_supervision_runtime_v2.notebook import build_review
    root = Path(root)
    source_tree(root)
    protocol = resolved_protocol(root)
    if review:
        build_review(root / 'notebooks/stagnation-supervision-v1-runtime-v2-review-r1', root=root, revision=1)
    lock = A.review_lock(root) if review else 'notebooks/missing/review-source-lock.json'
    lock_sha = sha(root / lock) if review else '0' * 64
    dataset = {k: protocol['dataset'][k] for k in ('ref', 'version')}
    provider = {'authenticated_account': OWNER, 'synthetic': True,
                'dataset_attachments': [{**dataset, 'attachment_confirmed': True},
                                        {'ref': 'synthetic-owner/qwen-snapshot', 'version': 1, 'attachment_confirmed': True}],
                'competition_attachments': [protocol['competition']['ref']]}
    provider_sha = write(root, 'private/provider-evidence.json', provider)
    write(root, A.ACCOUNT, {'status': 'verified', 'scope': A.SCOPE, 'consuming_account': OWNER, 'dataset': dataset,
                            'model_source': MODEL, 'competition': protocol['competition']['ref'],
                            'verified_at': 'synthetic', 'provider_evidence': 'private/provider-evidence.json',
                            'provider_evidence_sha256': provider_sha})
    facts = {k: 'synthetic' for k in ('licence_holder', 'recipients_and_roles', 'access_controls', 'publication_intent',
                                      'applicable_agreements', 'output_and_payload_handling', 'licence_evidence')}
    facts_sha = write(root, 'private/use-assessment.json', {**facts, 'consuming_account': OWNER, 'dataset': dataset})
    write(root, A.PERMISSION, {'status': 'approved', 'approval_kind': 'direct_consumption_permission', 'scope': A.SCOPE,
                               'dataset': protocol['dataset'], 'review_lock_sha256': lock_sha,
                               'protocol_sha256': sha(root / A.PROTOCOL),
                               'trusted_artifacts_sha256': protocol['bundle']['approved_manifest_sha256'],
                               'requirements_lock_sha256': protocol['bundle']['requirements_lock_sha256'],
                               'permission_outcome': 'permitted_for_reviewed_use', 'outstanding_conditions': [],
                               'reviewer_response': 'synthetic', 'use_assessment': 'private/use-assessment.json',
                               'use_assessment_sha256': facts_sha})
    write(root, A.BYTES, {'integrity_passed': True, 'wheel_bytes_verified': protocol['bundle']['wheel_count'],
                          'dataset_ref': dataset['ref'], 'requested_version': dataset['version'],
                          'trusted_artifacts_sha256': protocol['bundle']['approved_manifest_sha256'],
                          'installation_requirements_sha256': protocol['bundle']['requirements_lock_sha256']})
    model_provider_sha = write(root, 'private/model-evidence.json', {'synthetic': True})
    write(root, A.MODEL, {'status': 'verified', 'model_source': MODEL, 'tree_sha256': protocol['model']['tree_sha256'],
                          'file_count': protocol['model']['file_count'], 'bytes': protocol['model']['bytes'],
                          'mounted_path': MOUNT, 'provider_evidence': 'private/model-evidence.json',
                          'provider_evidence_sha256': model_provider_sha})
    evidence = {n: sha(root / n) for n in A.evidence_names(root)}
    common = {'status': 'approved', 'scope': A.SCOPE, 'review_lock_sha256': lock_sha, 'explicit_confirmation': True,
              'user_response': 'synthetic test only', 'approved_at': 'synthetic', 'evidence_bindings': evidence}
    source_sha = write(root, A.SOURCE, {**common, 'approval_kind': 'source', 'provenance': provenance('source')})
    limits = copy.deepcopy(A.SESSION_LIMITS[session])
    compute_sha = write(root, A.COMPUTE, {**common, 'approval_kind': 'compute', 'provenance': provenance('compute'),
                                          'source_approval_sha256': source_sha, 'protocol_sha256': sha(root / A.PROTOCOL),
                                          'sessions': {session: limits}, 'dataset': protocol['dataset'],
                                          'model_source': MODEL, 'consumed_attempts_acknowledged': protocol['consumed_attempts']})
    execution_sha = write(root, A.EXECUTION, {'review_lock': lock, 'review_sha256': lock_sha, 'scope': A.SCOPE,
                                              'source_approval_sha256': source_sha, 'compute_authorization_sha256': compute_sha,
                                              'session': session, 'attempt_id': ATTEMPT})
    reservation_sha = write(root, A.RESERVATION, {'status': 'reserved', 'attempt_id': ATTEMPT, 'events': ['reserve'],
                                                  'execution_sha256': execution_sha,
                                                  'seconds': A.SESSION_LIMITS[session]['authorized_seconds']})
    write(root, A.LAUNCH, {**common, 'approval_kind': 'launch', 'provenance': provenance('launch'),
                           'authorization_scope': 'submit_and_execute_one_attempt', 'submission_authorized': True,
                           'compute_authorization_sha256': compute_sha, 'source_approval_sha256': source_sha,
                           'execution_sha256': execution_sha, 'reservation_sha256': reservation_sha, 'session': session,
                           'maximum_submissions': 1, 'automatic_retries': 0})
    if claim:
        write(root, A.CLAIM, {'status': 'claimed', 'attempt_id': ATTEMPT, 'execution_sha256': execution_sha,
                              'reservation_sha256': reservation_sha, 'claimed_at': 'synthetic'})
    return root
