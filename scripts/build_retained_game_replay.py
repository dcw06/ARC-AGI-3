"""Private, offline viewer of retained Track 3 public-game actions. No execution or model calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def local_path(value):
    path = Path(value).resolve()
    # Retained Windows worktree evidence paths exceed MAX_PATH.
    if os.name == 'nt' and not str(path).startswith('\\\\?\\'):
        return Path('\\\\?\\'+str(path))
    return path


def verified_episodes(folder):
    folder = local_path(folder)
    raw_manifest = (folder/'manifest.json').read_bytes()
    manifest = json.loads(raw_manifest)
    if manifest['version'] != 'stagnation_supervision_evidence_v1':
        raise ValueError('unsupported evidence manifest')
    names = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}-{'manifest.json'}
    if names != set(manifest['files']):
        raise ValueError('evidence inventory mismatch')
    values = {}
    for name, row in manifest['files'].items():
        target = folder/name
        target.resolve().relative_to(folder.resolve())
        if target.is_symlink():
            raise ValueError('symlinked evidence')
        raw = target.read_bytes()
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('evidence hash/size mismatch: '+name)
        values[name] = json.loads(raw)
    run = values['run.json']
    if run.get('kind') != 'offline_development_engine' or run.get('status') != 'complete':
        raise ValueError('viewer requires a completed offline development run')
    expected = {'episodes/'+row['episode_id']+'.json' for row in run['episodes']}
    if len(expected) != len(run['episodes']) or expected != set(values)-{'run.json'}:
        raise ValueError('episode index mismatch')
    episodes = []
    for row in run['episodes']:
        episode = values['episodes/'+row['episode_id']+'.json']
        if any(episode[key] != row[key] for key in ('episode_id','status','stop_reason')):
            raise ValueError('episode summary mismatch')
        episodes.append(episode)
    return hashlib.sha256(raw_manifest).hexdigest(), episodes


def build_data(folder, arm='continuation'):
    digest, episodes = verified_episodes(folder)
    frames, selected = {}, []

    def frame(grid):
        h, w = len(grid), len(grid[0])
        if h > 64 or w > 64 or any(len(row) != w for row in grid):
            raise ValueError('invalid recorded frame dimensions')
        if any(type(cell) is not int or not 0 <= cell <= 15 for row in grid for cell in row):
            raise ValueError('invalid recorded frame value')
        cells = ''.join('0123456789abcdef'[cell] for row in grid for cell in row)
        key = hashlib.sha256(f'{h}x{w}:{cells}'.encode()).hexdigest()
        frames[key] = {'h':h,'w':w,'cells':cells}
        return key

    for episode in episodes:
        if episode['arm'] != arm:
            continue
        game = episode['game_id'].split('-')[0]
        if game not in ('ar25','wa30','ls20','s5i5'):
            raise ValueError('unreviewed public game: '+game)
        steps = []
        for step in episode['steps']:
            if step['status'] != 'acknowledged':
                raise ValueError('viewer only displays acknowledged actions')
            call = episode['calls'][step['call_index']]
            steps.append({'action':step['action'],'before':frame(step['before']['frames'][-1]),
                'after':[frame(g) for g in step['after']['frames']],
                'level_before':step['before']['levels_completed'],'level_after':step['after']['levels_completed'],
                'state':step['after']['state'],'changed_cells':step['effect_record']['changed_cells_by_frame'],
                'call_seconds':round(call['returned_at']-call['started_at'],3),
                'dispatch_seconds':round(step['returned_at']-step['dispatch_started_at'],3)})
        selected.append({'id':episode['episode_id'],'game':game,'arm':arm,'block':episode['block'],
                         'stop_reason':episode['stop_reason'],'initial':frame(episode['initial']['frames'][-1]),
                         'initial_levels':episode['initial']['levels_completed'],'steps':steps})
    if not selected:
        raise ValueError('no matching retained episodes')
    return {'provenance':'Retained Track 3 research run; real Qwen decisions, local offline public-game engine.',
            'qualification':'Historical replay. No fresh run or official hidden-game score. No new model calls.',
            'manifest_sha256':digest,'episodes':selected,'frames':frames}


def private_output(path):
    path = Path(path).resolve()
    for parent in path.parents:
        if (parent/'.git').exists():
            checked = subprocess.run(['git','-C',str(parent),'check-ignore','-q','--',str(path)],capture_output=True)
            if checked.returncode != 0:
                raise ValueError('raw replay output must be git-ignored or outside a repository')
            break
    return path


def build(folder, output, arm='continuation'):
    output = private_output(output)
    data = build_data(folder,arm)
    template = Path(__file__).with_name('retained_game_replay_template.html').read_text(encoding='utf-8')
    payload = json.dumps(data,separators=(',',':')).replace('<','\\u003c').replace('&','\\u0026')
    if template.count('__RETAINED_DATA__') != 1:
        raise ValueError('viewer data placeholder drift')
    raw = template.replace('__RETAINED_DATA__',payload).encode()
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('xb') as stream:
        stream.write(raw)
    receipt = {'viewer_sha256':hashlib.sha256(raw).hexdigest(),'input_manifest_sha256':data['manifest_sha256'],
               'episodes':len(data['episodes']),'actions':sum(len(e['steps']) for e in data['episodes']),
               'frames':len(data['frames']),'arm':arm,'model_calls':0,'provider_calls':0,'fresh_attempts':0}
    output.with_suffix('.receipt.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True,help='retained worker/run directory')
    parser.add_argument('--output',type=Path,required=True,help='new private HTML file; must not exist')
    parser.add_argument('--arm',choices=('continuation','periodic','triggered'),default='continuation')
    args = parser.parse_args()
    print(json.dumps(build(args.run,args.output,args.arm)))
