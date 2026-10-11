"""CPU-only review reproductions. Pass a checkout of edc9566 as the sole argument.

No provider, GPU, model, approval or reservation operations. Project source is not
edited. All evidence fixtures use TemporaryDirectory; the one sleeping child is
terminated and reaped in finally. Output is JSON lines, not an approval receipt.
"""
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

REPO = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(REPO))
from scripts import feedback_action_v1_launch as L
from research.feedback_action_v1 import live_evaluation as LE
from research.feedback_action_v1.live.fake_server import FakeServer
from research.feedback_action_v1.live.policy import validate_policy_request
from research.feedback_action_v1.live.service import validate_ready
from tests.test_feedback_action_v1_live_evaluation import SyntheticSpec, synthetic_session


def show(case, **value):
    print(json.dumps(dict(case=case, **value), sort_keys=True))


children = []


def spawn(*_args, **_kwargs):
    child = subprocess.Popen(
        [sys.executable, '-c', 'import time; time.sleep(30)'],
        start_new_session=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    children.append(child)
    return child


with tempfile.TemporaryDirectory() as tmp:
    folder = Path(tmp)
    try:
        with patch.object(L.threading.Thread, 'start', side_effect=KeyboardInterrupt('review injection')):
            L.run_supervisor(folder / 'output', folder, sys.executable, sys.executable, folder,
                             started=time.monotonic(), mode='rehearsal', internal_seconds=10,
                             session=1, root=REPO, spawn=spawn)
    except KeyboardInterrupt:
        show('startup_interruption', child_alive=children[0].poll() is None,
             cleanup_receipt=(folder / 'output/control/first-cell-supervisor-cleanup.json').exists())
    finally:
        for child in children:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=5)
            child.stdout.close()
        show('reproduction_child_cleanup', all_reaped=all(p.poll() is not None for p in children))


clock = [59.9]
original_save = L.EvidenceStore.save


def delayed_final_save(self, name, value, **kwargs):
    if name == 'notebook-cost.json':
        clock[0] = 60.1
    return original_save(self, name, value, **kwargs)


with tempfile.TemporaryDirectory() as tmp, \
        patch.dict(os.environ, {'FA1_REHEARSAL': '1', 'CUDA_VISIBLE_DEVICES': ''}), \
        patch.object(L, 'run_supervisor', return_value={
            'status': 'study_complete_pending_independent_evaluation', 'first_cell_cleanup_verified': True}), \
        patch.object(L.time, 'monotonic', side_effect=lambda: clock[0]), \
        patch.object(L.EvidenceStore, 'save', delayed_final_save):
    receipt = L.run(Path(tmp) / 'output', Path(tmp), started=0, root=REPO,
                    mode='rehearsal', internal_seconds=60)
    show('finalization_deadline', error=receipt['error'], recorded_elapsed=receipt['elapsed_seconds'],
         final_elapsed=clock[0], limit=60, study_status=receipt['study_status'])


run, spec = synthetic_session('reset')
with SyntheticSpec(spec):
    original = LE.evaluate_session(run, session=1, mode='live')
    show('synthetic_baseline', technical_validity=original['technical_validity'], problems=original['problems'])
    changes = [
        ('system_prompt', lambda q: q['messages'][0].update(content='Unfrozen system prompt')),
        ('model_id', lambda q: q.update(model='different/model')),
        ('schema', lambda q: q['response_format'].update(json_schema={
            'name': 'wrong', 'strict': False, 'schema': {}})),
        ('message_role', lambda q: q['messages'][0].update(role='user')),
    ]
    for label, change in changes:
        forged = copy.deepcopy(run)
        call = forged['episodes'][0]['calls'][0]
        change(call['request'])
        call['request_sha256'] = LE.canonical_digest(call['request'])
        result = LE.evaluate_session(forged, session=1, mode='live')
        try:
            validate_policy_request(call['request'])
            host = 'accepted'
        except Exception:
            host = 'refused'
        show('request_contract_' + label, host_contract=host,
             replay_passed=result['replay_passed'], technical_validity=result['technical_validity'],
             session_2_permitted=result['session_2_permitted'], problems=result['problems'])
    for label in ('current_grid', 'legal_actions', 'false_win', 'run_totals'):
        forged = copy.deepcopy(run)
        call = forged['episodes'][0]['calls'][0]
        if label in ('current_grid', 'legal_actions'):
            user = json.loads(call['request']['messages'][1]['content'])
            user['observation'][label] = [[15]] if label == 'current_grid' else [1, 2, 7]
            call['request']['messages'][1]['content'] = json.dumps(user, sort_keys=True, separators=(',', ':'))
            call['request_sha256'] = LE.canonical_digest(call['request'])
        elif label == 'false_win':
            forged['episodes'][0]['stop_reason'] = 'win'
        else:
            forged['calls'] = forged['dispatches'] = 0
        result = LE.evaluate_session(forged, session=1, mode='live')
        show('replay_' + label, replay_passed=result['replay_passed'],
             technical_validity=result['technical_validity'], session_2_permitted=result['session_2_permitted'],
             problems=result['problems'])
    first = original


ready = {'artifact': {'review_only': True}, 'startup_seconds': 1,
         'canary_audit': FakeServer().service.canary_audit}
validate_ready(ready, {'review_only': True})
for field, value in [('server_completion_tokens', 129), ('server_completion_tokens', 0),
                     ('server_completion_tokens', True), ('both_prompt_counts', -1)]:
    forged = copy.deepcopy(ready)
    audit = forged['canary_audit']['audit']
    if field == 'both_prompt_counts':
        audit['server_prompt_tokens'] = audit['tokenizer_prompt_tokens'] = value
    else:
        audit[field] = value
    try:
        validate_ready(forged, {'review_only': True})
        status = 'accepted'
    except Exception as exc:
        status = 'refused: ' + str(exc)
    show('canary_token_audit', field=field, value=value, result=status)


def second_block(spec):
    for pair in spec['schedule']:
        pair['block'] = 2


run2, spec2 = synthetic_session('reset', spec_change=second_block)
with SyntheticSpec(spec2):
    second = LE.evaluate_session(run2, session=2, mode='live')
    forged = copy.deepcopy(run2)
    next(e for e in forged['episodes'] if e['arm'] == 'candidate')['calls'][0]['response'] = 'not valid JSON'
    rerun = LE.evaluate_session(forged, session=2, mode='live')
pooled = LE.evaluate_sessions(first, second, [run, forged])
show('pooled_input_binding', first_validity=first['technical_validity'],
     original_second_validity=second['technical_validity'], altered_second_validity=rerun['technical_validity'],
     pool_technically_valid_both_sessions=pooled['technically_valid_both_sessions'],
     pooled_candidate_invalid=pooled['exploratory_thresholds']['invalid_action']['candidate'])
