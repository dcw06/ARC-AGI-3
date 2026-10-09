"""Runtime v2 live gate (hand-written). Import is inert; every live entry point calls `require` first.

Structure follows the verified runtime's gate (control-interface v2 `binding.require_live`) with Track 3's session
limits and the R6/R7 lessons: separate, provenance-bearing source, compute and launch decisions; no reuse of the
consumed R6 attempt; hash-bound account/attachment, direct-use permission, mounted-wheel and model-snapshot
evidence. In this checkout the gate refuses: the private bindings are REPLACE_WITH_ placeholders and no review lock
with authority, approval, evidence, execution lock, reservation or claim exists. Nothing here creates such records.

Records (all under reports/stagnation_supervision_runtime_v2_authority/, none present):
  source_approval.json, compute_authorization.json, launch_approval.json   separate human decisions
  account_attachment.json, use_permission.json, byte_verification.json, model_verification.json   evidence
  execution_lock.json, reservation.json, launch_claim.json, launch_receipt.json   one attempt per session
"""
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SCOPE = 'stagnation-supervision-v1-runtime-v2'
PACKAGE = 'research/stagnation_supervision_runtime_v2'
PROTOCOL = PACKAGE + '/protocol.json'
REVIEW_GLOB = 'notebooks/stagnation-supervision-v1-runtime-v2-review-r*/review-source-lock.json'
RECORDS = 'reports/stagnation_supervision_runtime_v2_authority'
SOURCE = RECORDS + '/source_approval.json'
COMPUTE = RECORDS + '/compute_authorization.json'
LAUNCH = RECORDS + '/launch_approval.json'
ACCOUNT = RECORDS + '/account_attachment.json'
PERMISSION = RECORDS + '/use_permission.json'
BYTES = RECORDS + '/byte_verification.json'
MODEL = RECORDS + '/model_verification.json'
EXECUTION = RECORDS + '/execution_lock.json'
RESERVATION = RECORDS + '/reservation.json'
CLAIM = RECORDS + '/launch_claim.json'
RECEIPT = RECORDS + '/launch_receipt.json'
ATTEMPT = re.compile(r'ssv1rt2-[A-Za-z0-9-]{8,80}')
# Track 3 protocol v2 section 11, unchanged (the frozen R4 values; nothing here authorizes them).
from research.stagnation_supervision_v1.closed_loop.authority import SESSION_LIMITS  # noqa: E402
REQUIRED_SOURCE = {PACKAGE + '/' + n for n in (
    '__init__.py', 'authority.py', 'protocol.json', 'derivation.json', 'model_binding.py', 'mounts.py', 'prepare.py',
    'launch.py', 'supervisor.py', 'worker.py', 'host.py', 'monitor.py', 'resources.py', 'publisher_install.py',
    'publisher_preflight.py', 'publisher_process.py', 'publisher_host.py', 'proposal.json', 'trusted_manifest.json',
    'trusted_requirements.lock')}


class LiveRefused(PermissionError):
    """The live path may not run; `reasons` lists every failed condition found."""

    def __init__(self, reasons):
        super().__init__('stagnation-supervision runtime v2 live path refused: ' + '; '.join(reasons))
        self.reasons = list(reasons)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve(root, name):
    if not isinstance(name, str) or not name or '\\' in name or name.startswith('/'):
        raise ValueError(f'unsafe reference {name!r}')
    unresolved = Path(root) / name
    path = unresolved.resolve()
    if not path.is_relative_to(Path(root).resolve()) or unresolved.is_symlink():
        raise ValueError(f'reference escapes root: {name}')
    return path


def read_json(root, name):
    path = resolve(root, name)
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('oversized authority record: ' + name)
    return json.loads(path.read_bytes())


def load_protocol(root=ROOT):
    protocol = read_json(root, PROTOCOL)
    if protocol.get('schema') != 'stagnation_supervision_runtime_v2_protocol' or protocol.get('scope') != SCOPE:
        raise ValueError('not the runtime v2 protocol')
    if protocol['science'].get('unchanged') is not True:
        raise ValueError('runtime v2 binds the unchanged science only')
    drift = [n for n, d in protocol['science']['files'].items() if sha256(resolve(root, n)) != d]
    if drift:
        raise ValueError('frozen science drift: ' + ', '.join(sorted(drift)))
    if set(protocol['kernel_ids']) != set(SESSION_LIMITS) or 'ssv1-r5-session1-reservation-001' not in protocol['consumed_attempts']:
        raise ValueError('session/attempt bindings')
    if type(protocol['dataset']['version']) is not int or protocol['dataset']['version'] < 1:
        raise ValueError('dataset version must be a positive integer')
    if protocol['limits']['installation_seconds'] != 450 or protocol['limits']['model_startup_ceiling_seconds'] != 900:
        raise ValueError('frozen R4 installation/startup ceilings')
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


def check_sources(root, lock_name):
    lock = read_json(root, lock_name)
    if lock.get('scope') != SCOPE or lock.get('gpu_enabled') is not False:
        raise ValueError('review lock is outside this GPU-disabled source-review scope')
    bindings = lock.get('bindings', {})
    missing = sorted(REQUIRED_SOURCE - set(bindings))
    if missing:
        raise ValueError('reviewed sources incomplete: ' + ', '.join(missing))
    for name, digest in bindings.items():
        if sha256(resolve(root, name)) != digest:
            raise ValueError('source drift: ' + name)
    return lock


def _decision(record, kind, lock_sha):
    provenance = record.get('provenance') or {}
    if (record.get('status') != 'approved' or record.get('approval_kind') != kind or record.get('scope') != SCOPE
            or record.get('review_lock_sha256') != lock_sha or record.get('explicit_confirmation') is not True
            or not str(record.get('user_response', '')).strip() or not record.get('approved_at')
            or provenance.get('type') != 'user_confirmation' or not provenance.get('message_reference')
            or not provenance.get('answer_reference') or not provenance.get('verbatim_text')
            or provenance.get('interpretation_only') is not False):
        raise ValueError(f'{kind} decision missing, unexplained or not bound to the reviewed lock')


def check_decisions(root, lock_name, protocol):
    lock_sha = sha256(resolve(root, lock_name))
    source, compute, launch = (read_json(root, n) for n in (SOURCE, COMPUTE, LAUNCH))
    for record, kind in ((source, 'source'), (compute, 'compute'), (launch, 'launch')):
        _decision(record, kind, lock_sha)
    answers = [r['provenance']['answer_reference'] for r in (source, compute, launch)]
    if len(set(answers)) != 3:
        raise ValueError('source, compute and launch need three separate decisions')
    if compute.get('source_approval_sha256') != sha256(resolve(root, SOURCE)):
        raise ValueError('compute authorization not bound to the source approval')
    if compute.get('protocol_sha256') != sha256(resolve(root, PROTOCOL)):
        raise ValueError('compute authorization not bound to the protocol')
    sessions = compute.get('sessions')
    if type(sessions) is not dict or len(sessions) != 1 or next(iter(sessions)) not in SESSION_LIMITS:
        raise ValueError('compute must authorize exactly one session')
    session = next(iter(sessions))
    for name, expected in SESSION_LIMITS[session].items():
        if type(sessions[session].get(name)) is not int or sessions[session][name] != expected:
            raise ValueError(f'compute limit differs from protocol v2: session {session} {name}')
    if compute.get('dataset') != protocol['dataset'] or compute.get('model_source') != protocol['model']['kaggle_source']:
        raise ValueError('compute authorization not bound to the dataset and model inputs')
    if compute.get('consumed_attempts_acknowledged') != protocol['consumed_attempts']:
        raise ValueError('compute authorization must acknowledge the consumed R6 attempt')
    if (launch.get('authorization_scope') != 'submit_and_execute_one_attempt' or launch.get('submission_authorized') is not True
            or launch.get('compute_authorization_sha256') != sha256(resolve(root, COMPUTE))
            or launch.get('source_approval_sha256') != sha256(resolve(root, SOURCE))
            or launch.get('session') != session or type(launch.get('maximum_submissions')) is not int
            or launch['maximum_submissions'] != 1 or type(launch.get('automatic_retries')) is not int
            or launch['automatic_retries'] != 0):
        raise ValueError('explicit one-use launch decision binding')
    return source, compute, launch, session


def evidence_names(root):
    account, permission, model = (read_json(root, n) for n in (ACCOUNT, PERMISSION, MODEL))
    return sorted({ACCOUNT, PERMISSION, BYTES, MODEL, account['provider_evidence'], permission['use_assessment'],
                   model['provider_evidence']})


def check_evidence(root, lock_name, protocol, session):
    kernel = protocol['kernel_ids'][session]
    if not re.fullmatch(r'[A-Za-z0-9_-]+/[A-Za-z0-9_-]+', kernel):
        raise ValueError('consuming kernel/account binding unresolved or invalid')
    owner = kernel.split('/')[0]
    dataset = {k: protocol['dataset'][k] for k in ('ref', 'version')}
    model_ref = protocol['model']['kaggle_source']
    account, permission, byte_receipt, model = (read_json(root, n) for n in (ACCOUNT, PERMISSION, BYTES, MODEL))
    if (account.get('status') != 'verified' or account.get('scope') != SCOPE or account.get('consuming_account') != owner
            or account.get('dataset') != dataset or account.get('model_source') != model_ref
            or account.get('competition') != protocol['competition']['ref'] or not account.get('verified_at')):
        raise ValueError('account attachment receipt missing or mismatched')
    if sha256(resolve(root, account['provider_evidence'])) != account.get('provider_evidence_sha256'):
        raise ValueError('account provider evidence drift')
    provider = read_json(root, account['provider_evidence'])
    attachments = {(row.get('ref'), row.get('version')) for row in provider.get('dataset_attachments', [])
                   if isinstance(row, dict) and row.get('attachment_confirmed') is True and type(row.get('version')) is int}
    owner_m, slug_m, version_m = model_ref.split('/')
    if (provider.get('authenticated_account') != owner or (dataset['ref'], dataset['version']) not in attachments
            or (f'{owner_m}/{slug_m}', int(version_m)) not in attachments
            or protocol['competition']['ref'] not in provider.get('competition_attachments', [])):
        raise ValueError('provider evidence does not confirm the account and exact wheel/model/competition attachments')
    facts = read_json(root, permission['use_assessment'])
    if sha256(resolve(root, permission['use_assessment'])) != permission.get('use_assessment_sha256'):
        raise ValueError('private use assessment drift')
    required = ('licence_holder', 'recipients_and_roles', 'access_controls', 'publication_intent',
                'applicable_agreements', 'output_and_payload_handling', 'licence_evidence')
    if facts.get('consuming_account') != owner or facts.get('dataset') != dataset or any(not facts.get(k) for k in required):
        raise ValueError('private use assessment lacks deployment facts or licence evidence')
    if (permission.get('status') != 'approved' or permission.get('approval_kind') != 'direct_consumption_permission'
            or permission.get('scope') != SCOPE or permission.get('dataset') != protocol['dataset']
            or permission.get('review_lock_sha256') != sha256(resolve(root, lock_name))
            or permission.get('protocol_sha256') != sha256(resolve(root, PROTOCOL))
            or permission.get('trusted_artifacts_sha256') != protocol['bundle']['approved_manifest_sha256']
            or permission.get('requirements_lock_sha256') != protocol['bundle']['requirements_lock_sha256']
            or permission.get('permission_outcome') != 'permitted_for_reviewed_use'
            or permission.get('outstanding_conditions') != [] or not str(permission.get('reviewer_response', '')).strip()):
        raise ValueError('direct-consumption permission missing, conditional or outside the reviewed use')
    expected_bytes = {'integrity_passed': True, 'wheel_bytes_verified': protocol['bundle']['wheel_count'],
                      'dataset_ref': dataset['ref'], 'requested_version': dataset['version'],
                      'trusted_artifacts_sha256': protocol['bundle']['approved_manifest_sha256'],
                      'installation_requirements_sha256': protocol['bundle']['requirements_lock_sha256']}
    if any(byte_receipt.get(k) != v for k, v in expected_bytes.items()) or type(byte_receipt.get('requested_version')) is not int:
        raise ValueError('mounted wheel byte verification missing or mismatched')
    if (model.get('status') != 'verified' or model.get('model_source') != model_ref
            or model.get('tree_sha256') != protocol['model']['tree_sha256']
            or model.get('file_count') != protocol['model']['file_count'] or model.get('bytes') != protocol['model']['bytes']
            or model.get('mounted_path') != protocol['model']['mounted_path']
            or sha256(resolve(root, model['provider_evidence'])) != model.get('provider_evidence_sha256')):
        raise ValueError('model snapshot verification missing or mismatched')
    bindings = {name: sha256(resolve(root, name)) for name in evidence_names(root)}
    for name in (SOURCE, COMPUTE, LAUNCH):
        if read_json(root, name).get('evidence_bindings') != bindings:
            raise ValueError('decision not bound to the attachment, permission, byte and model evidence: ' + name)
    return bindings


def check_reservation(root, lock_name, protocol, session):
    execution, reservation = read_json(root, EXECUTION), read_json(root, RESERVATION)
    expected = {'review_lock': lock_name, 'review_sha256': sha256(resolve(root, lock_name)), 'scope': SCOPE,
                'source_approval_sha256': sha256(resolve(root, SOURCE)),
                'compute_authorization_sha256': sha256(resolve(root, COMPUTE)), 'session': session}
    if any(execution.get(k) != v for k, v in expected.items()):
        raise ValueError('execution lock not bound to the decisions')
    attempt = execution.get('attempt_id')
    if not isinstance(attempt, str) or not ATTEMPT.fullmatch(attempt) or attempt in protocol['consumed_attempts']:
        raise ValueError('attempt id invalid or already consumed')
    if read_json(root, LAUNCH).get('execution_sha256') != sha256(resolve(root, EXECUTION)):
        raise ValueError('launch decision not bound to the execution lock')
    if (reservation.get('status') != 'reserved' or reservation.get('attempt_id') != attempt
            or reservation.get('execution_sha256') != sha256(resolve(root, EXECUTION))
            or reservation.get('events') != ['reserve']
            or reservation.get('seconds') != SESSION_LIMITS[session]['authorized_seconds']):
        raise ValueError('reservation missing, consumed or not bound to the execution lock')
    if read_json(root, LAUNCH).get('reservation_sha256') != sha256(resolve(root, RESERVATION)):
        raise ValueError('launch decision not bound to the reservation')
    return execution


def check_claim(root, execution):
    claim = read_json(root, CLAIM)
    if (claim.get('status') != 'claimed' or claim.get('attempt_id') != execution['attempt_id']
            or claim.get('execution_sha256') != sha256(resolve(root, EXECUTION))
            or claim.get('reservation_sha256') != sha256(resolve(root, RESERVATION)) or not claim.get('claimed_at')):
        raise ValueError('launch claim missing or not bound to this attempt')
    return claim


def require_live(root=None, need_claim=True):
    """Every live condition, checked before installation, model, GPU or provider activity. Raises LiveRefused with
    all reasons found; returns (protocol, execution) only when the attempt may run."""
    root = ROOT if root is None else Path(root)
    reasons = []
    try:
        protocol = load_protocol(root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise LiveRefused([f'protocol unreadable: {type(exc).__name__}: {exc}']) from exc
    pending = unresolved(protocol)
    if pending:
        reasons.append('unresolved placeholders: ' + ', '.join(pending))
    execution = None
    try:
        lock_name = review_lock(root)
        check_sources(root, lock_name)
        _, _, _, session = check_decisions(root, lock_name, protocol)
        check_evidence(root, lock_name, protocol, session)
        execution = check_reservation(root, lock_name, protocol, session)
        if need_claim:
            check_claim(root, execution)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        reasons.append(f'authorization: {type(exc).__name__}: {exc}')
    if reasons:
        raise LiveRefused(reasons)
    return protocol, execution


def require(root=None):
    """The process-level gate used by every live entry point: returns the bound execution lock or refuses."""
    return require_live(root)[1]


def consume_runtime(working, root=None):
    """Persist the provider-session one-use marker before target side effects; never retry on conflict."""
    execution = require(root)
    working = Path(working)
    if not working.is_dir() or working.is_symlink():
        raise ValueError('invalid provider working directory')
    marker = working / ('.' + execution['attempt_id'] + '.runtime-consumed.json')
    with marker.open('x', encoding='utf-8') as stream:
        json.dump({'status': 'consumed', 'attempt_id': execution['attempt_id'], 'scope': SCOPE,
                   'provider_run_type': os.environ.get('KAGGLE_KERNEL_RUN_TYPE')}, stream)
        stream.flush()
        os.fsync(stream.fileno())
    return marker


def verify_runtime_claim(working, root=None):
    execution = require(root)
    marker = Path(working) / ('.' + execution['attempt_id'] + '.runtime-consumed.json')
    if marker.is_symlink() or not marker.is_file() or marker.stat().st_size > 1024:
        raise PermissionError('runtime claim missing')
    value = json.loads(marker.read_bytes())
    if value.get('status') != 'consumed' or value.get('attempt_id') != execution['attempt_id'] or value.get('scope') != SCOPE:
        raise PermissionError('runtime claim mismatch')
    return marker


def rehearsal_gate():
    """CPU rehearsal only: explicit opt-in, no visible GPU, never a live authority (unchanged R4 semantics)."""
    if os.environ.get('SSV_REHEARSAL') != '1' or os.environ.get('CUDA_VISIBLE_DEVICES', '') != '':
        raise PermissionError('rehearsal mode requires SSV_REHEARSAL=1 and no visible GPU')
    return {'mode': 'rehearsal', 'attempt_id': None}
