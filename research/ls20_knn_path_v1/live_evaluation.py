"""Independent request, reply, restored-content and live-lifecycle evaluation.

audit_study checks retained evidence without promoting it to live certification.
evaluate additionally requires exact reviewed source, final lifecycle witnesses,
and an independently collected version-bound provider completion.
"""
from collections import Counter
import json
import math
from pathlib import Path, PurePosixPath

from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_io import sha
from research.initial_geometry_assistance_v1.model_io import validate_reply
from .live_contract import verify_inputs, MAX_PROMPT_TOKENS
from .live_worker import ADMISSION_SECONDS, MODEL, WORKER_SECONDS, canary, request_plan
from .source_closure import safe_member


def loads(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError('duplicate retained JSON key')
            value[key] = item
        return value
    def nonfinite(_):
        raise ValueError('non-finite retained JSON')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def lines(path):
    return [loads(raw) for raw in Path(path).read_text(encoding='utf-8').splitlines()]


def _same(left, right):
    return digest(left) == digest(right)


def _number(value, lower, upper):
    return type(value) in (int, float) and math.isfinite(value) and lower <= value < upper


def _kind(identity):
    return 'canary' if identity == 'canary' else 'recognition' if identity.endswith('/recognition') else 'policy'


def audit_transport(events, expected, *, token_audit=None):
    """Bind one native-counted body to one admission and one complete HTTP reply."""
    index, records, effects = 0, [], []
    seen, previous_issued = set(), -1
    while index < len(events):
        event = events[index]
        if type(event) is not dict:
            raise ValueError('non-object transport event')
        if event.get('kind') == 'engine_admission':
            effects.append(dict(event, transport_index=index))
            index += 1
            continue
        if event.get('kind') != 'HTTP_request' or index+2 >= len(events):
            raise ValueError('missing request/admission/response sequence')
        request, admission, response = events[index:index+3]
        if (set(request) != {'kind', 'id', 'body', 'native_prompt_tokens'} or
                type(request['id']) is not str or request['id'] not in expected):
            raise ValueError('unexpected HTTP request identity/fields')
        identity = request['id']
        if identity in seen or not _same(request['body'], expected[identity]):
            raise ValueError('duplicate or drifted HTTP request')
        if (type(admission) is not dict or set(admission) != {
                'kind', 'id', 'request_kind', 'method', 'path', 'sequence', 'issued_at', 'outcome'} or
                admission['kind'] != 'HTTP_admission' or admission['id'] != identity or
                admission['request_kind'] != _kind(identity) or admission['method'] != 'POST' or
                admission['path'] != '/v1/chat/completions' or admission['outcome'] is not None or
                type(admission['sequence']) is not int or admission['sequence'] != len(records)+1 or
                not _number(admission['issued_at'], 0, ADMISSION_SECONDS) or
                admission['issued_at'] < previous_issued or
                type(response) is not dict or set(response) != {'kind', 'id', 'status', 'raw'} or
                response['kind'] != 'HTTP_response' or response['id'] != identity or
                type(response['status']) is not int or response['status'] != 200 or
                type(response['raw']) is not str):
            raise ValueError('HTTP admission/response differs')
        count = request['native_prompt_tokens']
        if type(count) is not int or not 0 < count <= MAX_PROMPT_TOKENS:
            raise ValueError('native prompt audit ceiling/type differs')
        if token_audit is not None:
            independent = token_audit(request['body'])
            if type(independent) is not int or independent != count:
                raise ValueError('independent native prompt count differs')
        reply = loads(response['raw'])
        content = validate_reply(request['body'], reply, count)
        records.append({'id': identity, 'content': content, 'admission': admission,
                        'usage': reply['usage'], 'transport_index': index})
        seen.add(identity)
        previous_issued = admission['issued_at']
        index += 3
    return records, effects


from .audit import audit_study


def evaluate(output, inputs, review_lock, provider, *, token_audit=None, replay_factory=None):
    """Certify only an exact reviewed run with independent provider completion.

    The collector must capture the version-bound provider status, saved source,
    and log independently. Notebook-authored completion files are insufficient.
    """
    if token_audit is None or replay_factory is None:
        raise ValueError('live evaluation requires independent native-token and engine replay')
    from .live_operator import validate_saved, verify_review
    from .live_runtime import SCOPE
    output, inputs, review_lock = Path(output), Path(inputs), Path(review_lock)
    source = Path(__file__).resolve().parents[2]
    lock, pin = verify_review(review_lock.parent, source)
    if pin != sha(review_lock):
        raise ValueError('evaluation review-lock identity differs')
    verify_inputs(inputs, lock['input_manifest_sha256'])
    result = loads((output/'provisional-result.json').read_bytes())
    witness = loads((output/'return-witness.json').read_bytes())
    if (result.get('review_lock_sha256') != pin or not _same(result.get('scope'), SCOPE) or
            result.get('error') is not None or type(result.get('worker_exit')) is not int or
            result['worker_exit'] != 0 or result.get('temporary_and_source_removed') is not True or
            result.get('lifecycle_finalized') is not False or witness.get('error') is not None or
            not _number(witness.get('elapsed_seconds'), 0, WORKER_SECONDS) or
            witness.get('provisional_result_sha256') != sha(output/'provisional-result.json') or
            witness.get('provider_COMPLETE_and_exact_return_marker_required') is not True or
            result.get('source_inventory_sha256') != lock['source_inventory_sha256']):
        raise ValueError('exact package lifecycle/witness not complete within deadline')
    for key in ('process_cleanup', 'final_process_cleanup'):
        cleanup = result.get(key, {})
        if (cleanup.get('groups_absent') is not True or cleanup.get('interrupted') != [] or
                cleanup.get('error') is not None or type(cleanup.get('groups')) is not list or
                not cleanup['groups'] or any(group.get('ownership') != 'registered' or
                    group.get('groups_absent') is not True or group.get('error') is not None or
                    group.get('interrupted') != [] or group.get('remaining_members') != []
                    for group in cleanup['groups'])):
            raise ValueError('process ownership/cleanup incomplete')
    gpu_cleanup = result.get('GPU_cleanup', {})
    if gpu_cleanup.get('gpu_cleanup_verified') is not True or not _same(gpu_cleanup.get('gpu_processes'), 0):
        raise ValueError('GPU cleanup incomplete')
    if 'RTX PRO 6000' not in result.get('GPU', {}).get('name', ''):
        raise ValueError('allocated accelerator differs')
    from research.initial_geometry_assistance_v1.game_wheels import GAME_WHEEL_SOURCE
    wheels = result.get('game_wheels', {})
    if (not _same(wheels.get('source'), GAME_WHEEL_SOURCE) or not _same(wheels.get('wheel_count'), 31) or
            wheels.get('game_environment_receipt_sha256') != lock['game_receipt_sha256']):
        raise ValueError('mounted game-wheel verification differs')
    evidence = result.get('evidence_sha256')
    if type(evidence) is not dict:
        raise ValueError('lifecycle evidence inventory missing')
    for name, expected in evidence.items():
        if sha(safe_member(output, name)) != expected:
            raise ValueError('retained run evidence changed or unsafe')
    required = {'transport.jsonl', 'worker-result.json', 'worker-config.json', 'vllm.log', 'worker.log'}
    required.add('ls20-knn-path.jsonl')
    if not required <= set(evidence):
        raise ValueError('required worker evidence omitted from lifecycle inventory')
    collected = {'provisional-result.json', 'return-witness.json', 'provider.log',
                 'provider-notebook.ipynb', 'provider-saved-snapshot.json'}
    allowed = set(evidence) | collected | {'provider-receipt.json'}
    actual = {path.relative_to(output).as_posix() for path in output.rglob('*') if path.is_file()}
    if actual - allowed or any(path.is_symlink() for path in output.rglob('*')):
        raise ValueError('unbound or unsafe evidence outside the final lifecycle inventory')
    marker = 'LS20_KNN_PATH_V1_RETURNED '+sha(output/'return-witness.json')
    if (type(provider) is not dict or provider.get('status') != 'COMPLETE' or
            provider.get('kernel_id') != lock['kernel_id'] or type(provider.get('version')) is not int or
            provider['version'] < 1 or provider.get('log_sha256') != sha(output/'provider.log') or
            (output/'provider.log').read_text(encoding='utf-8').count(marker) != 1 or
            provider.get('submitted_source_sha256') != sha(output/'provider-notebook.ipynb')):
        raise ValueError('version-bound provider COMPLETE/source/return marker missing')
    snapshot_path = output/'provider-saved-snapshot.json'
    if provider.get('saved_snapshot_sha256') != sha(snapshot_path):
        raise ValueError('provider source/settings receipt changed')
    snapshot = loads(snapshot_path.read_bytes())
    saved_source = loads(snapshot['source']) if type(snapshot.get('source')) is str else snapshot.get('source')
    if not _same(saved_source, loads((output/'provider-notebook.ipynb').read_bytes())):
        raise ValueError('retained provider source differs from saved snapshot')
    saved = validate_saved(snapshot, lock, pin, provider['version'])
    if saved['authority']['attempt_id'] != result.get('attempt_id'):
        raise ValueError('provider authority names another attempt')
    content = audit_study(output, inputs, token_audit=token_audit, replay_factory=replay_factory)
    return {**content, 'schema': 'ls20_knn_path_independent_evaluation_v1', 'technically_complete': content['study_schedule_complete'],
            'lifecycle_certified': True, 'outcome_claim_permitted': False, 'review_lock_sha256': pin,
            'input_manifest_sha256': lock['input_manifest_sha256'],
            'source_inventory_sha256': lock['source_inventory_sha256'],
            'run_evidence_sha256': digest({path.relative_to(output).as_posix(): sha(path)
                                           for path in sorted(output.rglob('*')) if path.is_file()}),
            'qualification': 'One assisted k=4 floor-color and cross-navigation probe. No discovery, level-solving or comparative improvement claim.'}
