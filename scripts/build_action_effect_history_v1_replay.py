"""Build a self-contained visual replay of the archived action-effect history v1 attempt (no model, no GPU).

Reads only the hash-verified archive. Frames are shown exactly as recorded, and changed cells are
computed from the frames. Repeat opportunities use the frozen evaluator's own definitions. The
bottom-row marker is a post-hoc exploratory annotation, never a policy input or frozen metric.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'reports/action_effect_history_v1_archive.json'
OUTPUT = ROOT / 'reports/action_effect_history_v1_replay/index.html'
TEMPLATE = Path(__file__).with_name('action_effect_history_v1_replay_template.html')
EPISODES = 'reports/runs/action-effect-history-v1/download/action-effect-history-v1/worker/run/episodes/'
HEX = '0123456789abcdef'


def archived_members():
    lock = json.loads(LOCK.read_bytes())
    archive = ROOT / lock['archive']
    if hashlib.sha256(archive.read_bytes()).hexdigest() != lock['archive_sha256']:
        raise ValueError('archive hash mismatch')
    members = {}
    with zipfile.ZipFile(archive) as bundle:
        for name, row in lock['members'].items():
            if name.startswith(EPISODES):
                raw = bundle.read(name)
                if hashlib.sha256(raw).hexdigest() != row['sha256']:
                    raise ValueError('episode member hash mismatch: ' + name)
                members[name] = json.loads(raw)
    return lock, members


def encode_frame(grid, table):
    text = ''.join(HEX[v] for row in grid for v in row)
    key = hashlib.sha256(f'{len(grid)}x{len(grid[0])}:{text}'.encode()).hexdigest()[:16]
    table.setdefault(key, {'h': len(grid), 'w': len(grid[0]), 'cells': text})
    return key


def changed_cells(before, after):
    if len(before) != len(after) or any(len(a) != len(b) for a, b in zip(before, after)):
        return None  # dimension change: not comparable cell by cell
    return [[x, y] for y, row in enumerate(after) for x, value in enumerate(row) if before[y][x] != value]


def repeat_marks(steps):
    """Per-step marks matching the frozen evaluator's immediate-repeat definitions."""
    from research.action_effect_history_v1.evaluate import frame_key
    marks = []
    for i, s in enumerate(steps):
        mark = None
        if i > 0:
            prev = steps[i - 1]['effect_record']
            if (prev['status'] == 'acknowledged' and prev['final_frame_changed'] is False and prev['level_delta'] == 0
                    and frame_key(steps[i - 1]['before']) == frame_key(s['before'])):
                if s['action'] == steps[i - 1]['action']:
                    mark = 'repeat'
                elif s['action']['action_id'] == steps[i - 1]['action']['action_id']:
                    mark = 'type_repeat'
                else:
                    mark = 'switched'
        marks.append(mark)
    return marks


def step_view(episode, step, mark, table):
    before = step['before']['frames'][-1]
    returned = step['after']['frames']
    changes = [changed_cells(before, frame) for frame in returned]
    flat = [c for frame in changes if frame for c in frame]
    height = len(before)
    call = episode['calls'][step['call_index']]
    observation = json.loads(call['request']['messages'][1]['content'])['observation']
    seen = observation.get('action_effect_history')
    record = step['effect_record']
    return {'index': step['index'], 'action': step['action'], 'mark': mark,
            'before': encode_frame(before, table), 'returned': [encode_frame(f, table) for f in returned],
            'changes': changes, 'changed': sum(len(c) for c in changes if c),
            'bottom_row_only': bool(flat) and all(y == height - 1 for _, y in flat),
            'effect': {k: record[k] for k in ('status', 'changed_cells_by_frame', 'final_frame_changed',
                                              'level_delta', 'reset', 'returned_frame_count', 'state_after')},
            'levels': [step['before']['levels_completed'], step['after']['levels_completed']],
            'saw': {'recent_actions': observation.get('recent_actions'),
                    'history': seen['entries'] if seen else None,
                    'omitted': seen['omitted_entries'] if seen else None},
            'call': {'index': step['call_index'], 'response': call['response'], 'finish': call['finish_reason'],
                     'seconds': round(call['returned_at'] - call['started_at'], 3),
                     'prompt_tokens': call['server_prompt_tokens'],
                     'completion_tokens': call['server_completion_tokens'],
                     'request_sha256': call['request_sha256']}}


def build_data():
    lock, members = archived_members()
    evaluation = lock['evaluation']['evaluation']
    metrics = {m['episode_id']: m for m in evaluation['episodes']}
    table, episodes = {}, {}
    for name, episode in sorted(members.items()):
        marks = repeat_marks(episode['steps'])
        m = metrics[episode['episode_id']]
        episodes[episode['episode_id']] = {
            'episode_id': episode['episode_id'], 'pair_id': episode['pair_id'], 'arm': episode['arm'],
            'block': episode['block'], 'game_id': episode['game_id'], 'order': episode['order_in_pair'],
            'stop_reason': episode['stop_reason'], 'initial': encode_frame(episode['initial']['frames'][-1], table),
            'legal': episode['initial']['available_actions'],
            'steps': [step_view(episode, s, mk, table) for s, mk in zip(episode['steps'], marks)],
            'metrics': {k: m[k] for k in ('immediate_repeats', 'immediate_repeat_opportunities',
                                          'immediate_repeat_rate', 'type_repeats_after_no_change',
                                          'observable_change_rate', 'distinct_actions', 'distinct_action_ids',
                                          'levels_gained', 'prompt_tokens', 'completion_tokens')}}
    pairs = [{k: p[k] for k in ('pair_id', 'block', 'game_id', 'class', 'reason')} for p in evaluation['pairs']]
    return {'attempt_id': lock['attempt_id'], 'archive_sha256': lock['archive_sha256'],
            'run_manifest_sha256': lock['run_manifest_sha256'],
            'technically_complete': lock['evaluation']['technically_complete'],
            'behaviour_result': evaluation['behaviour_result'], 'solving_result': evaluation['solving_result'],
            'pooled': evaluation['pooled'], 'pairs': pairs, 'episodes': episodes, 'frames': table}


def render(data):
    template = TEMPLATE.read_text(encoding='utf-8')
    payload = json.dumps(data, separators=(',', ':'), sort_keys=True).replace('</', '<\\/')
    if template.count('/*__DATA__*/null') != 1:
        raise ValueError('template data slot')
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
        print(json.dumps({'output': OUTPUT.relative_to(ROOT).as_posix(), 'bytes': len(html.encode()),
                          'distinct_frames': len(json.loads(json.dumps(build_data()['frames'])))}))
