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
from .audit import audit_continuation
from research.feedback_summary_probe_v1.audit import audit_recognition_request
from .interface import recognition_key, recognition_request
from .live_contract import check_checkpoints, verify_inputs, MAX_PROMPT_TOKENS
from .live_worker import ADMISSION_SECONDS, MODEL, WORKER_SECONDS, canary, request_plan
from .scoring import score_recognition
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


def audit_study(output, inputs, *, token_audit, replay_factory):
    """Check all checkpoint conditions and replies, including invalid answers.

    Dependencies must be supplied independently. Fake dependencies are useful
    for CPU testing and cannot establish real-model or provider certification.
    """
    if token_audit is None or replay_factory is None:
        raise ValueError('independent native-token audit and engine replay are required')
    output, inputs = Path(output), Path(inputs)
    verify_inputs(inputs, sha(inputs/'manifest.json'))
    checkpoints = check_checkpoints(loads((inputs/'checkpoints.json').read_bytes())['checkpoints'])
    expected, responses = {'canary': canary()}, {}
    expected_interleaving = [('HTTP', 'canary')]
    rows, recognition_expected, summaries = [], [], []
    prefix_dispatches = new_dispatches = 0
    for checkpoint in checkpoints:
        identity = checkpoint['checkpoint_id']
        for variant in checkpoint['order']:
            recognition_id = identity+'/'+variant+'/recognition'
            expected[recognition_id] = recognition_request(checkpoint['base_request'], variant)
            audit_recognition_request(checkpoint, variant, expected[recognition_id])
            expected_interleaving.append(('HTTP', recognition_id))
            recognition_expected.append((checkpoint, variant, recognition_id))
        for variant in checkpoint['order']:
            name = identity+'-'+variant
            events = lines(output/(name+'.jsonl'))
            replay = replay_factory(checkpoint, variant)
            if replay is None:
                raise ValueError('independent replay engine missing')
            row = audit_continuation(checkpoint, variant, events, model=MODEL, replay_engine=replay)
            if (row['reason'] in ('deadline', 'exception') or not row['restoration_complete'] or
                    row['unconfirmed_model_call'] or row['unconfirmed_dispatch']):
                raise ValueError('checkpoint condition schedule cut off')
            rows.append(row)
            summaries.append({key: value for key, value in events[-1].items() if key != 'kind'})
            prefix_dispatches += row['prefix_dispatches']
            new_dispatches += row['continuation_dispatches']
            local = 0
            for event in events:
                kind = event['kind']
                if kind == 'request':
                    request_id = identity+'/'+variant+'/'+str(local)
                    expected[request_id] = event['body']
                    expected_interleaving.append(('HTTP', request_id))
                elif kind == 'response':
                    responses[identity+'/'+variant+'/'+str(local)] = event['text']
                    local += 1
                elif kind in ('bootstrap_intent', 'prefix_dispatch_intent', 'dispatch_intent', 'closed'):
                    operation = ('bootstrap' if kind == 'bootstrap_intent' else 'close' if kind == 'closed' else 'dispatch')
                    expected_interleaving.append(('engine', name, operation))
    calls, effects = audit_transport(lines(output/'transport.jsonl'), expected, token_audit=token_audit)
    if [call['id'] for call in calls] != list(expected):
        raise ValueError('whole HTTP request schedule differs')
    if calls[0]['content'].strip() != 'ok':
        raise ValueError('canary content differs')
    by_id = {call['id']: call for call in calls}
    if any(by_id[identity]['content'] != text for identity, text in responses.items()):
        raise ValueError('continuation answer differs from retained HTTP reply')
    recognition = []
    for checkpoint, variant, identity in recognition_expected:
        recognition.append({'checkpoint_id': checkpoint['checkpoint_id'], 'game_id': checkpoint['game_id'],
                            'stratum': checkpoint['stratum'], 'variant': variant,
                            'score': score_recognition(by_id[identity]['content'], recognition_key(checkpoint['base_request']))})
    actual_interleaving = [(call['transport_index'], ('HTTP', call['id'])) for call in calls]
    resets = dispatches = closes = 0
    for effect in effects:
        operation = effect.get('operation')
        if operation not in ('bootstrap', 'dispatch', 'close'):
            raise ValueError('unknown engine admission')
        resets += operation == 'bootstrap'
        dispatches += operation == 'dispatch'
        closes += operation == 'close'
        expected_effect = {'kind': 'engine_admission', 'episode': effect.get('episode'), 'operation': operation,
                           'bootstrap_attempts': resets, 'dispatch_attempts': dispatches, 'close_attempts': closes,
                           'transport_index': effect['transport_index']}
        if not _same(effect, expected_effect):
            raise ValueError('engine admission counters/fields differ')
        actual_interleaving.append((effect['transport_index'], ('engine', effect['episode'], operation)))
    if [event for _, event in sorted(actual_interleaving)] != expected_interleaving:
        raise ValueError('request and engine admission interleaving differs')
    worker = loads((output/'worker-result.json').read_bytes())
    raw_recognition = [{'checkpoint_id': checkpoint['checkpoint_id'], 'variant': variant, 'text': by_id[identity]['content']}
                       for checkpoint, variant, identity in recognition_expected]
    expected_worker = {'schema': 'feedback_summary_probe_worker_v1', 'error': None, 'recognition': raw_recognition,
                       'continuations': summaries, 'bootstrap_attempts': resets, 'dispatch_attempts': dispatches,
                       'close_attempts': closes, 'closed_scorecards': closes, 'lifecycle_certified': False}
    if set(worker) != set(expected_worker) | {'ledger'} or any(
            not _same(worker[key], value) for key, value in expected_worker.items()):
        raise ValueError('worker summaries, recognition replies or engine totals differ')
    ledger = worker['ledger']
    kinds = dict(Counter(_kind(call['id']) for call in calls))
    if (type(ledger) is not dict or ledger.get('refusals') != [] or
            not _same(ledger.get('maximum_model_requests'), 81) or
            not _same(ledger.get('issued'), len(calls)) or not _same(ledger.get('by_kind'), kinds) or
            type(ledger.get('entries')) is not list or len(ledger['entries']) != len(calls)):
        raise ValueError('worker ledger summary differs')
    for entry, call in zip(ledger['entries'], calls):
        expected_entry = {key: value for key, value in call['admission'].items() if key not in ('kind', 'request_kind')}
        expected_entry.update(kind=call['admission']['request_kind'], outcome='http_200')
        if (set(entry) != set(expected_entry) | {'seconds'} or
                any(not _same(entry[key], value) for key, value in expected_entry.items()) or
                not _number(entry['seconds'], 0, 30.001)):
            raise ValueError('worker HTTP ledger entry differs')
    plan = {item['id'] for item in request_plan(checkpoints)}
    if (len(checkpoints) != 8 or len(rows) != 16 or len(recognition) != 16 or resets != 16 or closes != 16 or
            prefix_dispatches != 36 or not 0 <= new_dispatches <= 64 or
            dispatches != prefix_dispatches+new_dispatches or resets+dispatches > 116 or
            len(calls) != 17+sum(row['policy_calls'] for row in rows) or len(calls) > 81 or
            any(call['id'] not in plan for call in calls)):
        raise ValueError('frozen study counts or scope differ')
    return {'schema': 'feedback_summary_probe_independent_content_v1', 'content_replay_passed': True,
            'lifecycle_certified': False, 'outcome_claim_permitted': False,
            'recognition': recognition, 'continuations': rows, 'generations': len(calls),
            'recognition_generations': len(recognition), 'policy_generations': len(responses),
            'bootstrap_resets': resets, 'prefix_dispatches': prefix_dispatches,
            'continuation_dispatches': new_dispatches, 'local_scorecards': closes,
            'offline_actions_including_bootstraps': resets+dispatches,
            'prompt_tokens': sum(call['usage']['prompt_tokens'] for call in calls),
            'completion_tokens': sum(call['usage']['completion_tokens'] for call in calls),
            'native_tokens_independently_rechecked': True,
            'qualification': 'Content and cost verification only. Scripted or fake dependencies do not establish model performance or live lifecycle completion.'}


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
    checkpoints = check_checkpoints(loads((inputs/'checkpoints.json').read_bytes())['checkpoints'])
    required.update(checkpoint['checkpoint_id']+'-'+variant+'.jsonl'
                    for checkpoint in checkpoints for variant in checkpoint['order'])
    if not required <= set(evidence):
        raise ValueError('required worker evidence omitted from lifecycle inventory')
    collected = {'provisional-result.json', 'return-witness.json', 'provider.log',
                 'provider-notebook.ipynb', 'provider-saved-snapshot.json'}
    allowed = set(evidence) | collected | {'provider-receipt.json'}
    actual = {path.relative_to(output).as_posix() for path in output.rglob('*') if path.is_file()}
    if actual - allowed or any(path.is_symlink() for path in output.rglob('*')):
        raise ValueError('unbound or unsafe evidence outside the final lifecycle inventory')
    marker = 'FEEDBACK_SUMMARY_PROBE_RETURNED '+sha(output/'return-witness.json')
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
    return {**content, 'schema': 'feedback_summary_probe_independent_evaluation_v1', 'technically_complete': True,
            'lifecycle_certified': True, 'outcome_claim_permitted': True, 'review_lock_sha256': pin,
            'input_manifest_sha256': lock['input_manifest_sha256'],
            'source_inventory_sha256': lock['source_inventory_sha256'],
            'run_evidence_sha256': digest({path.relative_to(output).as_posix(): sha(path)
                                           for path in sorted(output.rglob('*')) if path.is_file()}),
            'qualification': 'Eight correlated exposed checkpoints across six games; paired descriptive results only. Provider lifecycle and independent content replay both passed.'}
