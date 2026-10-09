# Derived from research/control_interface_action_selection_v2/binding.py (5a21dd3) by scripts/build_progress_subgoal_v1_runtime2.py; edit the derivation.
"""Protocol loading and the live-path gate: unresolved placeholders, reviewed sources, separate source approval,
Record C compute authorization and an unconsumed single-attempt reservation. Import is inert."""
import hashlib
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = 'research/progress_subgoal_v1_runtime2'
PROTOCOL = PACKAGE + '/protocol.json'
SCOPE = 'progress-subgoal-v1-runtime2'
REVIEW_GLOB = 'notebooks/progress-subgoal-v1-runtime2-review-r*/review-source-lock.json'
SOURCE = 'reports/progress_subgoal_v1_runtime2_source_approval.json'
COMPUTE = 'reports/progress_subgoal_v1_runtime2_compute_authorization.json'
EXECUTION = PACKAGE + '/execution_lock.json'
RESERVATION = PACKAGE + '/reservation.json'
CLAIM = 'reports/progress_subgoal_v1_runtime2_launch_claim.json'  # never in config/ (old r4 inventory)
RECEIPT = 'reports/progress_subgoal_v1_runtime2_launch.json'
ACCOUNT = 'reports/progress_subgoal_v1_runtime2_account_attachment.json'
PERMISSION = 'reports/progress_subgoal_v1_runtime2_use_permission.json'
BYTES = 'reports/progress_subgoal_v1_runtime2_byte_verification.json'
# Review documents every review lock must bind; every repository-side gate verifies them.
REVIEW_REQUIRED = ('reports/progress_subgoal_v1_protocol_v2_frozen.md', 'reports/progress_subgoal_v1_model_identity.json',
                   'research/progress_subgoal_v1/decision_rules.json', 'research/progress_subgoal_v1/score.py',
                   'research/progress_subgoal_v1/evaluate_run.py', 'scripts/evaluate_progress_subgoal_v1_runtime2.py')
COMPUTE_LIMITS = ('authorized_seconds', 'internal_seconds', 'cleanup_reserve_seconds', 'admission_cutoff_seconds',
                  'maximum_attempts', 'maximum_model_requests', 'automatic_retries')
ATTEMPT = re.compile(r'psv1r2-[a-zA-Z0-9-]{8,80}')


class LiveRefused(PermissionError):
    """The live path may not run; `reasons` lists every failed condition found."""

    def __init__(self, reasons):
        super().__init__('progress_subgoal_v1 runtime2 live path refused: ' + '; '.join(reasons))
        self.reasons = list(reasons)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve(root, name):
    if not isinstance(name, str) or not name or '\\' in name or name.startswith('/'):
        raise ValueError(f'unsafe reference {name!r}')
    path = (Path(root) / name).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError(f'reference escapes root: {name}')
    return path


def read_json(root, name):
    return json.loads(resolve(root, name).read_bytes())


def load_protocol(root=ROOT):
    protocol = read_json(root, PROTOCOL)
    if protocol.get('schema') != 'progress_subgoal_v1_runtime2_protocol' or protocol.get('scope') != SCOPE:
        raise ValueError('not the progress_subgoal_v1 runtime2 protocol')
    limits = protocol['limits']
    if type(protocol['dataset']['version']) is not int or protocol['dataset']['version'] < 1:
        raise ValueError('dataset version must be a positive integer')
    integer_limits = (*COMPUTE_LIMITS, 'installation_seconds', 'model_verification_seconds', 'startup_ceiling_seconds')
    if (any(type(limits.get(k)) is not int for k in integer_limits)
            or limits['maximum_attempts'] != 1 or limits['automatic_retries'] != 0
            or limits['maximum_model_requests'] != 6613
            or not 0 < limits['admission_cutoff_seconds'] < limits['internal_seconds'] <= limits['authorized_seconds']
            or any(limits[k] <= 0 for k in ('installation_seconds', 'model_verification_seconds',
                                          'startup_ceiling_seconds', 'cleanup_reserve_seconds'))
            or limits['internal_seconds'] - limits['admission_cutoff_seconds'] < limits['cleanup_reserve_seconds']):
        raise ValueError('invalid single-attempt lifecycle limits')
    from .runtime_controls import validate_protocol
    validate_protocol(root, protocol)
    return protocol


def unresolved(protocol):
    """Dotted paths of every value still carrying the placeholder prefix."""
    prefix, found = protocol['placeholder_prefix'], []

    def walk(value, path):
        if isinstance(value, dict):
            for key, item in value.items():
                if key != 'placeholder_prefix':
                    walk(item, f'{path}.{key}' if path else key)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f'{path}[{index}]')
        elif isinstance(value, str) and value.startswith(prefix):
            found.append(path)
    walk(protocol, '')
    return found


def review_lock(root):
    locks = sorted(Path(root).glob(REVIEW_GLOB), key=lambda p: int(p.parent.name.rsplit('-r', 1)[1]))
    if not locks:
        raise ValueError('no review source lock')
    return locks[-1].relative_to(root).as_posix()


def check_sources(root, lock_name, review_documents=True):
    """The reviewed runtime sources and, unless inside the runtime payload, the review documents, by hash."""
    lock = read_json(root, lock_name)
    if lock.get('scope') != SCOPE or lock.get('gpu_enabled') is not False:
        raise ValueError('review lock is outside this GPU-disabled source-review scope')
    required = {p.relative_to(root).as_posix() for p in (Path(root) / PACKAGE).glob('*.py')} | {PROTOCOL, PACKAGE + '/proposal.json', PACKAGE + '/trusted_manifest.json', PACKAGE + '/trusted_requirements.lock'}
    required |= {p.relative_to(root).as_posix() for p in (Path(root) / 'certification/direct_publisher_smoke_v1').glob('*.py')}
    from .runtime_controls import EXPERIMENT_SOURCES
    required |= set(EXPERIMENT_SOURCES) | {PACKAGE + '/derivation.json', PACKAGE + '/token-audit.json'}
    required |= {'certification/direct_publisher_smoke_v1/' + n for n in ('proposal.json', 'trusted_manifest.json', 'trusted_requirements.lock')}
    missing = sorted(required - set(lock.get('bindings', {})))
    if missing:
        raise ValueError('reviewed sources incomplete: ' + ', '.join(missing))
    for name, digest in lock['bindings'].items():
        if sha256(resolve(root, name)) != digest:
            raise ValueError('source drift: ' + name)
    if review_documents:
        listed = lock.get('review_documents') or {}
        missing = sorted(set(REVIEW_REQUIRED) - set(listed))
        if missing:
            raise ValueError('review documents incomplete: ' + ', '.join(missing))
        for name, digest in sorted(listed.items()):
            if sha256(resolve(root, name)) != digest:
                raise ValueError('review document drift: ' + name)
    return lock


def check_approvals(root, lock_name, protocol):
    lock_sha = sha256(resolve(root, lock_name))
    source, compute = read_json(root, SOURCE), read_json(root, COMPUTE)
    for record, kind in ((source, 'source'), (compute, 'compute')):
        if (record.get('status') != 'approved' or record.get('approval_kind') != kind or record.get('scope') != SCOPE
                or record.get('review_lock_sha256') != lock_sha or not str(record.get('user_response', '')).strip()
                or not record.get('approved_at')):
            raise ValueError(f'{kind} approval missing or not bound to the reviewed lock')
    if compute.get('source_approval_sha256') != sha256(resolve(root, SOURCE)):
        raise ValueError('compute authorization not bound to the source approval')
    if compute.get('protocol_sha256') != sha256(resolve(root, PROTOCOL)):
        raise ValueError('compute authorization not bound to the protocol')
    for name in COMPUTE_LIMITS:
        if type(compute.get(name)) is not int or compute[name] != protocol['limits'][name]:
            raise ValueError('compute limit differs from the protocol: ' + name)
    for name in protocol['dataset']:
        if compute.get('dataset', {}).get(name) != protocol['dataset'][name]:
            raise ValueError('compute authorization not bound to the dataset ' + name)
    return source, compute


def evidence_names(root):
    """Every receipt and referenced private evidence file embedded in a launch."""
    account, permission = read_json(root, ACCOUNT), read_json(root, PERMISSION)
    return sorted({ACCOUNT, PERMISSION, BYTES, account['provider_evidence'], permission['use_assessment']})


def check_evidence(root, lock_name, protocol):
    """Require evidence and a scoped reviewer outcome, not reused R2 labels.

    A reviewer validates the authenticity of the private evidence; code enforces
    bindings and scope. Wheel integrity is checked again before installation.
    """
    if not re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_-]+', protocol['kernel_id']):
        raise ValueError('consuming kernel/account binding unresolved or invalid')
    account, permission, byte_receipt = (read_json(root, name) for name in (ACCOUNT, PERMISSION, BYTES))
    expected_account = protocol['kernel_id'].split('/')[0]
    dataset = {name: protocol['dataset'][name] for name in ('ref', 'version')}
    if (account.get('status') != 'verified' or account.get('scope') != SCOPE
            or account.get('consuming_account') != expected_account
            or account.get('dataset') != dataset or not account.get('verified_at')):
        raise ValueError('account attachment receipt missing or mismatched')
    provider = read_json(root, account['provider_evidence'])
    if sha256(resolve(root, account['provider_evidence'])) != account.get('provider_evidence_sha256'):
        raise ValueError('account provider evidence drift')
    if (provider.get('authenticated_account') != expected_account
            or not any(row.get('ref') == dataset['ref'] and type(row.get('version')) is int
                       and row['version'] == dataset['version'] and row.get('attachment_confirmed') is True
                       for row in provider.get('dataset_attachments', []) if isinstance(row, dict))):
        raise ValueError('provider evidence does not confirm the authenticated account and exact attachment version')
    facts = read_json(root, permission['use_assessment'])
    if sha256(resolve(root, permission['use_assessment'])) != permission.get('use_assessment_sha256'):
        raise ValueError('private use assessment drift')
    required_facts = ('licence_holder', 'recipients_and_roles', 'access_controls', 'publication_intent',
                      'applicable_agreements', 'output_and_payload_handling', 'licence_evidence')
    if (facts.get('consuming_account') != expected_account
            or facts.get('dataset') != dataset or any(not facts.get(k) for k in required_facts)):
        raise ValueError('private use assessment lacks deployment facts or licence evidence')
    if (permission.get('status') != 'approved' or permission.get('approval_kind') != 'direct_consumption_permission'
            or permission.get('scope') != SCOPE or permission.get('dataset') != protocol['dataset']
            or permission.get('review_lock_sha256') != sha256(resolve(root, lock_name))
            or permission.get('protocol_sha256') != sha256(resolve(root, PROTOCOL))
            or permission.get('trusted_artifacts_sha256') != protocol['bundle']['approved_manifest_sha256']
            or permission.get('requirements_lock_sha256') != protocol['bundle']['requirements_lock_sha256']
            or permission.get('permission_outcome') != 'permitted_for_reviewed_use'
            or permission.get('outstanding_conditions') != []
            or not str(permission.get('reviewer_response', '')).strip() or not permission.get('reviewed_at')):
        raise ValueError('direct-consumption permission missing, conditional or outside the reviewed use')
    expected_bytes = {'integrity_passed': True, 'wheel_bytes_verified': protocol['bundle']['wheel_count'],
                      'dataset_ref': dataset['ref'], 'requested_version': dataset['version'],
                      'trusted_artifacts_sha256': protocol['bundle']['approved_manifest_sha256'],
                      'installation_requirements_sha256': protocol['bundle']['requirements_lock_sha256']}
    if (any(byte_receipt.get(k) != v for k, v in expected_bytes.items())
            or byte_receipt.get('integrity_passed') is not True
            or type(byte_receipt.get('wheel_bytes_verified')) is not int
            or type(byte_receipt.get('requested_version')) is not int):
        raise ValueError('mounted wheel byte verification missing or mismatched')
    bindings = {name: sha256(resolve(root, name)) for name in evidence_names(root)}
    for name in (SOURCE, COMPUTE):
        if read_json(root, name).get('evidence_bindings') != bindings:
            raise ValueError('approval not bound to the account, permission and byte evidence: ' + name)
    return bindings


def check_reservation(root, lock_name):
    execution, reservation = read_json(root, EXECUTION), read_json(root, RESERVATION)
    bindings = {'review_lock': lock_name, 'review_sha256': sha256(resolve(root, lock_name)),
                'source_approval_sha256': sha256(resolve(root, SOURCE)),
                'compute_approval_sha256': sha256(resolve(root, COMPUTE)), 'scope': SCOPE}
    if any(execution.get(k) != v for k, v in bindings.items()):
        raise ValueError('execution lock not bound to the approvals')
    if not isinstance(execution.get('attempt_id'), str) or not ATTEMPT.fullmatch(execution['attempt_id']):
        raise ValueError('attempt id')
    digest = hashlib.sha256(json.dumps(execution, sort_keys=True, indent=2).encode() + b'\n').hexdigest()
    if (reservation.get('status') != 'reserved' or reservation.get('attempt_id') != execution['attempt_id']
            or reservation.get('execution_sha256') != digest or reservation.get('events') != ['reserve']):
        raise ValueError('reservation missing, consumed or not bound to the execution lock')
    return execution


def reservation_digest(root):
    return sha256(resolve(root, RESERVATION))


def check_claim(root, execution):
    """The launch-side claim: created exclusively by the launch tooling before the package is built, immutable,
    and embedded in the launch package. It binds the attempt to one recorded launch."""
    claim = read_json(root, CLAIM)
    if (claim.get('status') != 'claimed' or claim.get('attempt_id') != execution['attempt_id']
            or claim.get('execution_sha256') != sha256(resolve(root, EXECUTION))
            or claim.get('reservation_sha256') != reservation_digest(root) or not claim.get('claimed_at')):
        raise ValueError('launch claim missing or not bound to this attempt')
    return claim


def require_live(root=None, need_claim=True, review_documents=True):
    """Every live-path condition, checked before any installation, model or GPU activity. Raises LiveRefused with
    all reasons found; returns (protocol, execution) when the attempt may run. `need_claim=False` is used only by
    the launch tooling to create the claim itself. `review_documents=False` is used only inside the runtime
    payload, which never carries the review documents; they were verified when the launch package was built."""
    root = ROOT if root is None else Path(root)
    reasons = []
    try:
        protocol = load_protocol(root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise LiveRefused([f'protocol unreadable: {exc}']) from exc
    pending = unresolved(protocol)
    if pending:
        reasons.append('unresolved placeholders: ' + ', '.join(pending))
    execution = None
    try:
        lock_name = review_lock(root)
        check_sources(root, lock_name, review_documents)
        check_approvals(root, lock_name, protocol)
        check_evidence(root, lock_name, protocol)
        execution = check_reservation(root, lock_name)
        if need_claim:
            check_claim(root, execution)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        reasons.append(f'authorization: {type(exc).__name__}: {exc}')
    if reasons:
        raise LiveRefused(reasons)
    return protocol, execution


def consume(root, working):
    """Session-local guard: mark the attempt consumed in this provider session's working directory (exclusive
    create), so it cannot run twice within one session. It cannot see other sessions: an offline notebook has no
    durable shared state. Durable once-only accounting is the launch-side claim and receipt (launch.py); see
    reports/progress_subgoal_v1_runtime2_package.md for what neither can prevent."""
    protocol, execution = require_live(root, review_documents=False)  # inside the runtime payload
    marker = Path(working) / f".{execution['attempt_id']}.consumed.json"
    with marker.open('x', encoding='utf-8') as stream:
        json.dump({'attempt_id': execution['attempt_id'], 'status': 'consumed', 'scope': 'this provider session only',
                   'provider_run_type': os.environ.get('KAGGLE_KERNEL_RUN_TYPE')}, stream)
        stream.flush()
        os.fsync(stream.fileno())
    return protocol, execution, marker
