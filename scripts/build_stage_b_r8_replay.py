"""Build a self-contained visual replay of the archived Stage B R8 pair (no model calls, no GPU).

Reads only the hash-verified R8 archive and the reviewer geometry reference. Frames are shown
exactly as recorded; changed cells are computed from the frames; reviewer annotations are
evaluation-only and were never part of any policy request.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'reports/perception_stage_b_r8_archive.json'
REFERENCE = ROOT / 'reports/integrated_case_v1/geometry_reference.json'
OUTPUT = ROOT / 'reports/perception_stage_b_r8_replay/index.html'
TRAJECTORY = 'reports/runs/phase4-grounded-action-v1-r8/download/phase4-grounded-action-v1/worker/trajectory.json'


def archived_trajectory():
    lock = json.loads(LOCK.read_bytes())
    archive = ROOT / lock['archive']
    if hashlib.sha256(archive.read_bytes()).hexdigest() != lock['archive_sha256']:
        raise ValueError('archive hash mismatch')
    with zipfile.ZipFile(archive) as bundle:
        raw = bundle.read(TRAJECTORY)
    if hashlib.sha256(raw).hexdigest() != lock['members'][TRAJECTORY]['sha256']:
        raise ValueError('trajectory member hash mismatch')
    return json.loads(raw), lock['archive_sha256'], hashlib.sha256(raw).hexdigest()


def changed_cells(before, after):
    if len(before) != len(after) or any(len(a) != len(b) for a, b in zip(before, after)):
        return None  # dimension change: not comparable cell by cell
    return [[x, y] for y, row in enumerate(after) for x, value in enumerate(row) if before[y][x] != value]


def call_view(call, index):
    response = json.loads(call['response'])
    return {'index': index, 'stage': call['stage'], 'status': call['status'], 'finish_reason': call['finish_reason'],
            'started_at': call['started_at'], 'returned_at': call['returned_at'],
            'seconds': round(call['returned_at'] - call['started_at'], 3),
            'prompt_tokens': call['server_prompt_tokens'], 'tokenizer_prompt_tokens': call['tokenizer_prompt_tokens'],
            'completion_tokens': call['server_completion_tokens'], 'response': response,
            'response_text': call['response'], 'request_sha256': call['request_sha256'],
            'system_prompt': call['request']['messages'][0]['content']}


def step_view(episode, step):
    before = step['before']['frames'][-1]
    returned = step['after']['frames']
    changes = [changed_cells(before, frame) for frame in returned]
    truth_changed = [bool(c) if c is not None else True for c in changes]
    any_change = any(truth_changed)
    calls = episode['calls']
    decision = call_view(calls[step['decision_call']], step['decision_call'])
    prediction = call_view(calls[step['prediction_call']], step['prediction_call'])
    feedback = call_view(calls[step['feedback_call']], step['feedback_call'])
    predicted = step['prediction']['prediction']
    reported = [feedback['response'].get(f'frame_{i}_changed') for i in range(len(returned))]
    expected_assessment = 'supported' if (predicted == 'change') == any_change else 'contradicted'
    history = json.loads(calls[step['decision_call']]['request']['messages'][1]['content'])['observation']
    return {'index': step['index'], 'action': step['action'], 'target': step.get('target'),
            'before': step['before']['frames'], 'before_levels': step['before']['levels_completed'],
            'returned': returned, 'after_levels': step['after']['levels_completed'], 'after_state': step['after']['state'],
            'changes': changes, 'any_change': any_change,
            'prediction': step['prediction'], 'prediction_correct': (predicted == 'change') == any_change,
            'feedback': step['feedback'], 'feedback_reported': reported, 'feedback_truth': truth_changed,
            'feedback_frames_correct': [r == t for r, t in zip(reported, truth_changed)],
            'assessment_expected': expected_assessment,
            'assessment_correct': step['feedback'].get('assessment') == expected_assessment,
            'history_seen': {'recent_actions': history['recent_actions'],
                             'retained_transitions': history['history_compaction']['retained_transitions'],
                             'previous_grid_equals_current': history['previous_grid'] == history['current_grid']
                             if history['previous_grid'] is not None else None,
                             'recent_final_grids': len(history['recent_final_grids'])},
            'timeline': {'committed_at': step['committed_at'], 'dispatch_started_at': step['dispatch_started_at'],
                         'returned_at': step['returned_at']},
            'calls': [decision, prediction, feedback]}


def build_data():
    trajectory, archive_sha, trajectory_sha = archived_trajectory()
    reference = json.loads(REFERENCE.read_bytes())
    arms = [{'arm': ep['arm'], 'steps': [step_view(ep, s) for s in ep['steps']]} for ep in trajectory['episodes']]
    annotations = [{'id': o['id'], 'bbox': o['bbox'], 'cells': o['cells']} for o in reference['objects']]
    return {'archive_sha256': archive_sha, 'trajectory_sha256': trajectory_sha, 'version': trajectory['version'],
            'calls': trajectory['calls'], 'dispatches': trajectory['dispatches'],
            'prompt_tokens': trajectory['prompt_tokens'], 'completion_tokens': trajectory['completion_tokens'],
            'game_id': trajectory['episodes'][0]['initial']['game_id'], 'arms': arms,
            'annotations': annotations, 'annotation_scope': reference['annotation_scope'],
            'other_regions': reference['other_visible_regions']}


def render(data):
    template = (Path(__file__).with_name('stage_b_r8_replay_template.html')).read_text(encoding='utf-8')
    payload = json.dumps(data, separators=(',', ':'), sort_keys=True).replace('</', '<\\/')
    return template.replace('/*__DATA__*/null', payload)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='regenerate in memory and compare with the committed page')
    args = parser.parse_args()
    html = render(build_data())
    if args.check:
        if OUTPUT.read_text(encoding='utf-8') != html:
            raise SystemExit('replay page differs from archived evidence rendering')
        print('replay page matches archived evidence')
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(html, encoding='utf-8', newline='\n')
        print(json.dumps({'output': OUTPUT.relative_to(ROOT).as_posix(), 'bytes': len(html.encode())}))
