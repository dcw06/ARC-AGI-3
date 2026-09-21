"""Trace one archived ft09 transition to its next request; no runtime execution."""
import collections
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/phase4_ft09_information_v1'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def main():
    historical = ROOT / 'reports/phase4_closed_loop_v1_inspection/inspection-lock.json'
    lock = json.loads(historical.read_bytes())
    for name, expected in lock['bindings'].items():
        assert digest((ROOT/name).read_bytes()) == expected, name
    archive = ROOT / lock['input_archive']
    assert digest(archive.read_bytes()) == lock['input_archive_sha256']
    OUT.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        prefix = 'output/phase4-closed-loop-v1/worker/'
        def read(name):
            return json.loads(z.read(prefix+name))
        name = 'cl1-02-no_concrete_examples-step-01.json'
        next_name = 'cl1-02-no_concrete_examples-step-02.json'
        step, following = read(name), read(next_name)
        before, after = read(step['pre']), read(step['post'])
        assert following['pre'] == step['post']
        grid = before['frames'][-1]
        final = after['frames'][-1]
        summaries = []
        for index, frame in enumerate(after['frames']):
            changes = [(x,y,c,frame[y][x]) for y,row in enumerate(grid) for x,c in enumerate(row) if c != frame[y][x]]
            summaries.append(dict(index_zero_based=index, changed_cells=len(changes),
                bbox_xyxy=None if not changes else [min(p[0] for p in changes),min(p[1] for p in changes),
                    max(p[0] for p in changes),max(p[1] for p in changes)],
                color_transitions=dict(collections.Counter(f'{p[2]}->{p[3]}' for p in changes)),
                changed_pixels_xy_before_after=changes))
        request = following['request']
        user = json.loads(request['messages'][1]['content'])['observation']
        assert grid == final == user['current_grid'] == user['previous_grid'] == user['recent_final_grids'][0]
        assert user['recent_actions'] == [6]
        assert step['action'] == following['action'] == {'action_id':6,'action_data':{'x':32,'y':32}}
        assert len(after['frames']) == 5 and len(request['messages']) == 2
        assert before['levels_completed'] == after['levels_completed'] == 0
        source_lock = json.loads((ROOT/'notebooks/phase4-closed-loop-v1-review-r1/review-source-lock.json').read_bytes())
        for path in ('agent/representation.py','certification/phase4_closed_loop_v1/contract.py','reports/phase4_v2_offline_package.json'):
            assert digest((ROOT/path).read_bytes()) == source_lock['bindings'][path]
        manifest = json.loads((ROOT/'reports/phase4_v2_offline_package.json').read_bytes())
        game_path = 'environment_files/ft09/0d8bbf25/ft09.py'
        with zipfile.ZipFile(ROOT/'evidence/phase4-v2-development-offline.zip') as games:
            source = games.read(game_path)
        assert digest(source) == manifest['files'][game_path]['sha256']
        source_lines = source.decode().splitlines()
        source_evidence = {'label':'privileged retrospective interpretation; never a policy input',
            'path':game_path,'sha256':digest(source),'start_line':2328,'end_line':2371,
            'text':'\n'.join(source_lines[2327:2371])}
        evidence = dict(scope='offline_single_case_information_trace_v1',input_archive_sha256=digest(archive.read_bytes()),
            historical_lock_sha256=digest(historical.read_bytes()),episode='cl1-02-no_concrete_examples',
            step_one_based=2,record=name,next_record=next_name,
            record_sha256=digest(z.read(prefix+name)),next_record_sha256=digest(z.read(prefix+next_name)),
            action=step['action'],next_action=following['action'],pre=step['pre'],post=step['post'],
            frames=summaries,policy_observation_keys=sorted(user),recent_actions=user['recent_actions'],
            history_compaction=user['history_compaction'],all_policy_grids_equal_pre_and_final=True,
            policy_message_roles=[m['role'] for m in request['messages']],
            next_request_sha256=following['request_sha256'],
            levels_completed_before=0,levels_completed_after=0,
            raw_frames=after['frames'],pre_frame=grid,next_policy_observation=user)
        for filename, data in [('observation_trace.json',evidence),('source_interpretation_evidence.json',source_evidence)]:
            (OUT/filename).write_bytes((json.dumps(data,indent=2)+'\n').encode())
        # Use the recovered renderer solely as a visualization of retained numeric grids.
        from inspect_phase4_closed_loop_v1 import png
        images=[grid]+after['frames']
        strip=[sum([frame[y] for frame in images],[]) for y in range(64)]
        (OUT/'frame_sequence.png').write_bytes(png(strip,scale=3,click={'x':32,'y':32}))
    print(json.dumps({'historical_bindings_verified':len(lock['bindings']),
        'changes_per_frame':[f['changed_cells'] for f in summaries],
        'bounds':[f['bbox_xyxy'] for f in summaries],
        'colors':[f['color_transitions'] for f in summaries],
        'history':user['history_compaction'],'gpu_runs':0},indent=2))

if __name__ == '__main__':
    main()
