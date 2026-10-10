# Derived from research/control_interface_action_selection_v2/binding.py at 5a21dd3 by research/feedback_action_v1/derive_runtime.py; edit the derivation.
"""Feedback-action v1 live-path gate (successor runtime v1): unresolved placeholders, reviewed sources, separate
source approval, compute authorization bound to the runtime binding, the unchanged experiment protocol and the
owner-gate record, account/permission/byte evidence for the publisher dataset, and an unconsumed single-attempt
reservation for one session (session 2 also needs session 1's independent evaluation). Import is inert."""
import hashlib
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # one directory deeper than the source
PACKAGE = 'research/feedback_action_v1/live'
PROTOCOL = PACKAGE + '/runtime.json'  # the runtime binding; the unchanged experiment protocol is EXPERIMENT
EXPERIMENT = PACKAGE + '/protocol.json'
GATES = PACKAGE + '/owner_gates.json'
# Review documents every review lock must bind; every repository-side gate verifies them (never in the payload).
REVIEW_REQUIRED = (
    'reports/feedback_action_v1_protocol_v2_frozen.md',
    'research/feedback_action_v1/live_evaluation.py',
    'research/feedback_action_v1/evaluate.py',
    'research/transition_evidence_v1/reference.py',
    'scripts/evaluate_feedback_action_v1.py',
    'research/feedback_action_v1/derive.py',
    'research/feedback_action_v1/derive_runtime.py',
    'scripts/feedback_action_v1_package.py',
    'scripts/check_feedback_action_v1_structured_outputs.py',
    'reports/feedback_action_v1/structured_outputs_check_r2.json',
)
SCOPE = 'feedback-action-v1'
REVIEW_GLOB = 'notebooks/feedback-action-v1-review-r*/review-source-lock.json'
SOURCE = 'reports/feedback_action_v1_source_approval.json'
COMPUTE = 'reports/feedback_action_v1_compute_authorization.json'
EXECUTION = PACKAGE + '/execution_lock.json'
RESERVATION = PACKAGE + '/reservation.json'
CLAIM = 'config/feedback_action_v1_launch_claim.json'
RECEIPT = 'reports/feedback_action_v1_launch.json'
ACCOUNT = 'reports/feedback_action_v1_account_attachment.json'
PERMISSION = 'reports/feedback_action_v1_use_permission.json'
BYTES = 'reports/feedback_action_v1_byte_verification.json'
COMPUTE_LIMITS = ('authorized_seconds', 'internal_seconds', 'cleanup_reserve_seconds', 'installation_seconds',
                  'startup_ceiling_seconds', 'pair_admission_seconds', 'maximum_attempts', 'maximum_policy_calls',
                  'maximum_canaries', 'automatic_retries')
ATTEMPT = re.compile(r'fa1-[a-zA-Z0-9-]{8,80}')


class LiveRefused(PermissionError):
    """The live path may not run; `reasons` lists every failed condition found."""

    def __init__(self, reasons):
        super().__init__('feedback-action v1 live path refused: ' + '; '.join(reasons))
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
    """The runtime binding (runtime.json, validated by runtime.load) and the unchanged experiment protocol's
    lifecycle, which must agree with it. `limits` is the gate's name for the runtime lifecycle."""
    from .runtime import load
    protocol = load(root)
    experiment = read_json(root, EXPERIMENT)
    if experiment.get('id') != 'feedback-action-v1' or experiment.get('arms') != ['baseline', 'candidate']:
        raise ValueError('not the feedback-action v1 experiment protocol')
    life, frozen = protocol['lifecycle'], experiment['limits']
    if (frozen['maximum_policy_calls'] != life['maximum_policy_calls'] or frozen['internal_seconds'] != life[
            'internal_seconds'] or frozen['cleanup_reserve_seconds'] != life['cleanup_reserve_seconds']
            or frozen['pair_admission_seconds'] != life['pair_admission_seconds']
            or frozen['provider_timeout_seconds'] != life['authorized_seconds']):
        raise ValueError('runtime lifecycle differs from the experiment protocol')
    from .owner_gates import load as load_gates
    load_gates(Path(root) / GATES)
    protocol['limits'] = life
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
    from .notebook import source_names
    required = set(source_names(root))  # every embedded file
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
        raise ValueError('compute authorization not bound to the runtime binding')
    if compute.get('experiment_protocol_sha256') != sha256(resolve(root, EXPERIMENT)):
        raise ValueError('compute authorization not bound to the experiment protocol')
    if compute.get('owner_gates_sha256') != sha256(resolve(root, GATES)):
        raise ValueError('compute authorization not bound to the owner-gate record')
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


SESSION_ONE_FIELDS = ('attempt_id', 'evaluation', 'evaluation_sha256')


def session_names(root):
    """The session-1 evaluation a session-2 attempt depends on (embedded in its launch package); else nothing."""
    execution = read_json(root, EXECUTION)
    return [execution['session_1']['evaluation']] if execution.get('session') == 2 else []


def check_session_one(root, execution):
    """Session 2 runs only after session 1 was independently evaluated and stopped under none of F2a and F3-F6
    (protocol v2 section 10). The evaluation is bound by hash; its verdict is the evaluator's, never a label."""
    link = execution.get('session_1')
    if not isinstance(link, dict) or set(link) != set(SESSION_ONE_FIELDS) or not ATTEMPT.fullmatch(
            str(link.get('attempt_id'))):
        raise ValueError('session 2 must bind its session-1 evaluation')
    if sha256(resolve(root, link['evaluation'])) != link['evaluation_sha256']:
        raise ValueError('session-1 evaluation drift')
    evaluation = read_json(root, link['evaluation'])
    study = evaluation.get('evaluation') or {}
    if (evaluation.get('mode') != 'live' or evaluation.get('attempt_id') != link['attempt_id']
            or study.get('session') != 1 or study.get('session_2_permitted') is not True):
        raise ValueError('session 1 is not a live, evaluated session that permits session 2')
    return evaluation


def check_reservation(root, lock_name):
    execution, reservation = read_json(root, EXECUTION), read_json(root, RESERVATION)
    bindings = {'review_lock': lock_name, 'review_sha256': sha256(resolve(root, lock_name)),
                'source_approval_sha256': sha256(resolve(root, SOURCE)),
                'compute_approval_sha256': sha256(resolve(root, COMPUTE)), 'scope': SCOPE}
    if any(execution.get(k) != v for k, v in bindings.items()):
        raise ValueError('execution lock not bound to the approvals')
    if not isinstance(execution.get('attempt_id'), str) or not ATTEMPT.fullmatch(execution['attempt_id']):
        raise ValueError('attempt id')
    if execution.get('session') not in (1, 2):
        raise ValueError('the execution lock must name session 1 or 2')
    if execution['session'] == 2:
        check_session_one(root, execution)
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
    reports/feedback_action_v1_successor_package.md for what neither can prevent."""
    protocol, execution = require_live(root, review_documents=False)  # inside the runtime payload
    marker = Path(working) / f".{execution['attempt_id']}.consumed.json"
    with marker.open('x', encoding='utf-8') as stream:
        json.dump({'attempt_id': execution['attempt_id'], 'status': 'consumed', 'scope': 'this provider session only',
                   'provider_run_type': os.environ.get('KAGGLE_KERNEL_RUN_TYPE')}, stream)
        stream.flush()
        os.fsync(stream.fileno())
    return protocol, execution, marker
