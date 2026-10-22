"""Publish the retained ls20 CPU-r6 replay subset, with no private audit records.

Requires Pillow 12.2.0 only for GIF export. The inputs are independently pinned;
the exporter verifies every displayed PNG/action/encounter against the journal.
Existing output directories are never overwritten. No game or model runs.
"""
import argparse
import base64
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from certification.phase4_multimodal_preflight_v3.images import PALETTE, png
from research.initial_geometry_assistance_v1.geometry import digest
from research.ls20_knn_path_v1.geometry import player

PINS={
    'viewer':'fccbc5f97f15406d1cc0d0ebb7a42a0918cdd67c2c020803581784967140207a',
    'result':'8b9a406943364e24372f644d8439b0aae944a4d9622a7869dbd729add655f8c8',
    'events':'326aac236e864dac18b7379e4369416c71deeeeb8d900994694a0495e31c57ba',
}
NAMES={1:'UP',2:'DOWN',3:'LEFT',4:'RIGHT'}


def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return json.dumps(value,ensure_ascii=True,separators=(',',':')).replace('<','\\u003c')
def write_json(path,value):path.write_bytes((json.dumps(value,sort_keys=True,indent=2,ensure_ascii=True)+'\n').encode())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('viewer','result','events','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    inputs={name:getattr(args,name).read_bytes() for name in PINS}
    if any(sha(inputs[n])!=v for n,v in PINS.items()):raise ValueError('Pinned retained input differs')
    if args.output.exists():raise FileExistsError('Preserve existing publications; use a new output directory')
    import PIL
    from PIL import Image,ImageSequence
    if PIL.__version__!='12.2.0':raise ValueError('Use the recorded Pillow 12.2.0 for reproducible GIFs')
    html=inputs['viewer'].decode()
    prefix='const frames='
    start=html.index(prefix)+len(prefix)
    frames,end=json.JSONDecoder().raw_decode(html[start:])
    boundary=start+end
    if not html[boundary:].startswith(',summary='):raise ValueError('Unexpected viewer data layout')
    summary_start=boundary+len(',summary=')
    _,summary_end=json.JSONDecoder().raw_decode(html[summary_start:])
    result=json.loads(inputs['result'])
    r=result['result']
    events=[json.loads(line) for line in inputs['events'].splitlines()]
    if (r!=result['independent_audit']['result'] or not result['independent_audit']['content_replay_verified'] or
            digest(events)!=result['content_sha256'] or r['success'] or r['levels_gained']!=1 or
            r['new_dispatches']!=114 or r['reason']!='cross_contact_cap' or r['model_calls']!=0):
        raise ValueError('Retained outcome/content verification differs')
    initial=next(e['observation'] for e in events if e['kind']=='initial')
    transitions=[e for e in events if e['kind']=='transition']
    states=[initial]+[e['record']['after'] for e in transitions]
    if len(frames)!=115 or len(transitions)!=114:raise ValueError('Replay length differs')
    encounters=[];by_move={};move=0
    for e in events:
        if e['kind']=='transition':
            if e['record']['step']!=move or e['record']['before']!=states[move]:raise ValueError('Discontinuous transition')
            move+=1
        if e['kind']=='encounter':
            receipt=e['receipt']
            if receipt['after_sha256']!=digest(states[move]) or receipt['before_sha256']!=digest(states[move-1]):
                raise ValueError('Encounter differs from its actual action')
            changes=receipt['floor_changes']
            event=dict(index=receipt['index'],after_move=move,level=states[move]['levels_completed']+1,
                object_id=receipt['object_id'],kind=receipt['object_id'].split(':',1)[0],
                visible_yellow_cells_before=changes['visible_yellow_cells_before'],
                visible_yellow_cells_after=changes['visible_yellow_cells_after'])
            encounters.append(event);by_move.setdefault(move,[]).append(event['object_id'])
    if len(encounters)!=11:raise ValueError('Encounter count differs')
    raw_images=[];log=[];count=0
    for i,(frame,obs) in enumerate(zip(frames,states)):
        if not frame['image'].startswith('data:image/png;base64,'):raise ValueError('Only embedded retained PNGs are allowed')
        raw=base64.b64decode(frame['image'].split(',',1)[1],validate=True)
        if raw!=png(obs['grid'],cell=7):raise ValueError('Displayed board differs from retained pixels')
        expected_action='Initial board' if i==0 else NAMES[transitions[i-1]['record']['action']['action_id']]
        count+=len(by_move.get(i,[]))
        if (frame['center']!=player(obs['grid'])['center'] or frame['level']!=obs['levels_completed'] or
                frame['action']!=expected_action or frame['encounters']!=by_move.get(i,[]) or frame['encounter_count']!=count):
            raise ValueError('Displayed action/state/encounter metadata differs')
        raw_images.append(raw)
        item=deepcopy(frame);item['image']=f'frames/{i:03d}.png';item['step']=i
        log.append(item)
    summary=dict(
        source_commit='caf0b92ce3cfd5c220e887e947a879408dbc5204',
        success=False,reason=r['reason'],requested_levels=3,levels_gained=1,levels_observed=2,moves=114,
        level_results=[dict(level=1,moves=13,passed=True),dict(level=2,moves=101,passed=False),dict(level=3,moves=0,passed=False,reached=False)],
        encounters=encounters,encounter_count=11,observed_relocations=sum(e['kind']=='observed_relocation' for e in events),
        independently_replayed=True,GPU_jobs=0,neural_generations=0,
        qualification='Deterministic supplied-rule controller. Level 1 passed; level 2 not completed; level 3 not reached.',
        source_result_sha256=PINS['result'],source_events_sha256=PINS['events'])
    # Keep the reviewed controls and self-contained images, replacing only the
    # embedded private summary with the explicit publication whitelist.
    public_html=html[:start]+encoded(frames)+',summary='+encoded(summary)+html[summary_start+summary_end:]
    public_html=public_html.replace('Every retained event matched fresh-engine replay.',
        'The retained run matched fresh-engine replay. Level 1 passed; level 2 did not complete; level 3 was not reached.')
    metadata=json.dumps(dict(frames=log,summary=summary))
    for pattern in (r'[A-Za-z]:[\\/]',r'/mnt/',r'/home/',r'(?i)authorization:',r'(?i)bearer\s+',r'(?i)kaggle_key',r'(?i)access_token'):
        if re.search(pattern,metadata):raise ValueError('Private path or credential marker in publication metadata')
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'frames').mkdir()
    for i,raw in enumerate(raw_images):(args.output/f'frames/{i:03d}.png').write_bytes(raw)
    (args.output/'index.html').write_bytes(public_html.encode())
    write_json(args.output/'replay.json',dict(summary=summary,frames=log))
    write_json(args.output/'encounters.json',encounters)
    for name,indices in (('level-1.gif',range(0,14)),('level-2.gif',range(13,115))):
        images=[]
        for i in indices:
            image=Image.frombytes('P',(64,64),bytes(v for row in states[i]['grid'] for v in row))
            image.putpalette([v for color in PALETTE for v in color]+[0]*(768-48))
            images.append(image.resize((448,448),Image.Resampling.NEAREST))
        duration=[1000]+[450]*(len(images)-2)+[1200]
        images[0].save(args.output/name,save_all=True,append_images=images[1:],duration=duration,loop=0,disposal=1,optimize=True)
        with Image.open(args.output/name) as gif:
            decoded=list(ImageSequence.Iterator(gif))
            if len(decoded)!=len(images):raise ValueError('GIF omitted replay frames')
            # Seek explicitly; iterator frames share the underlying decoder.
            for j,i in enumerate(indices):
                gif.seek(j)
                with Image.open(io.BytesIO(raw_images[i])) as original:
                    if gif.convert('RGB').tobytes()!=original.convert('RGB').tobytes():raise ValueError('GIF pixels differ')
    readme='''# ls20 object-memory replay

**Level 1 passed; level 2 did not complete; level 3 was not reached.**
This is the retained CPU-r6 run from `caf0b92`: 114 moves, 11 saved encounter
events and two engine-side relocations. Fresh-engine replay matched the run.
No new game play, model inference or GPU job was performed for this export.

## Level 1: passed in 13 moves

![Level 1 replay: 13 moves, ending with the next board appearing](level-1.gif)

The final image in this clip is the new level-2 board shown after completion.

## Level 2: both new rings encountered; level not completed

![Level 2 replay: 101 moves; stops at the cross-contact cap](level-2.gif)

The controller remembered both ring arrivals, but timer-aware planning remains
unfinished. It stopped at the cross-contact cap after two relocations; there
was no reset request during the episode. Seeing or encountering an object is
not a level pass. This is a deterministic controller with supplied conventions,
not an unaided VLM-solving result.

## Interactive replay and records

- [Download the self-contained interactive replay](index.html?raw=1), then open
  the downloaded HTML in your browser. It includes play/pause, frame selection,
  native mouse coordinates, goals and encounter events. GitHub's file preview
  does not execute interactive HTML.
- [Frame-by-frame action log](actions.md)
- [Structured replay data](replay.json)
- [Saved encounter events](encounters.json)
- [File hashes and source provenance](manifest.json)
- [Results and limitations](../ls20_object_memory_v1_CPU_results_2026-10-22.md)

Images preserve the actual 64x64 board colors, enlarged to 448x448 using exact
7x7 blocks. The export includes the 115 observed frames and their action and
encounter metadata. It excludes private audit, installation, approval, account
and provider-operation records. These published observations are development
data, not an unseen evaluation set.
'''
    (args.output/'README.md').write_bytes(readme.encode())
    rows=['# Frame-by-frame action log','','114 moves; level 1 passed, level 2 incomplete. Each image is the board **after** its listed action.',
        'A counter increase displays the next board; the completing action belongs to the previous board.','',
        '| Step | Action | Completed levels | Player center | Goal | Encounter events |',
        '| --- | --- | --- | --- | --- | --- |']
    for f in log:
        rows.append(f"| [{f['step']}]({f['image']}) | {f['action']} | {f['level']} | {tuple(f['center'])} | {f['goal'] or '-'} | {', '.join(f['encounters']) or '-'} |")
    (args.output/'actions.md').write_bytes(('\n'.join(rows)+'\n').encode())
    files={p.relative_to(args.output).as_posix():dict(sha256=sha(p.read_bytes()),bytes=p.stat().st_size)
        for p in sorted(args.output.rglob('*')) if p.is_file()}
    write_json(args.output/'manifest.json',dict(version=1,source_commit=summary['source_commit'],source_input_sha256=PINS,
        exporter_sha256=sha(Path(__file__).read_bytes()),pillow_version=PIL.__version__,frames=115,moves=114,
        original_pixels_verified=True,GIF_pixels_verified=True,files=files,
        publication_scope='Replay boards/actions/encounters only; no credentials or unrelated private records.'))
    print(json.dumps(dict(output=str(args.output),frames=115,moves=114,encounters=11,files=len(files)+1,
        bytes=sum(p.stat().st_size for p in args.output.rglob('*') if p.is_file()),new_game_actions=0,new_model_generations=0,GPU_jobs=0)))


if __name__=='__main__':main()
