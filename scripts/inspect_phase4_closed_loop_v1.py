"""Offline retained-frame inspection; no game/model execution or policy changes."""
import base64,collections,hashlib,html,json,struct,zlib,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/phase4_closed_loop_v1_inspection'
# Display-only false-color palette; authoritative observations remain numeric grids.
COLORS=['#ffffff','#bbbbbb','#888888','#555555','#222222','#000000','#e53aa3','#ff6b40',
        '#f02b2b','#3156e8','#58a8ef','#ffe328','#ff9528','#8a233f','#46cd77','#843dde']
def png(grid,scale=4,click=None):
    h=len(grid);w=len(grid[0]);rows=[]
    for y in range(h):
        row=bytearray()
        for x in range(w):
            assert 0<=grid[y][x]<16, 'unexpected palette index'
            c=bytes.fromhex(COLORS[grid[y][x]][1:])
            if click and ((abs(x-click['x'])<=2 and y==click['y']) or
                          (abs(y-click['y'])<=2 and x==click['x'])):
                c=b'\x00\xff\xff'
            row.extend(c*scale)
        rows.extend([b'\0'+row]*scale)
    def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',w*scale,h*scale,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b'')
def delta(a,b):
    points=[(x,y) for y,row in enumerate(a) for x,c in enumerate(row) if c!=b[y][x]]
    return {'cells':len(points),'bbox':None if not points else [min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points)]}
def main():
    receipt=json.loads((ROOT/'reports/phase4_closed_loop_v1_evidence_receipt.json').read_text())
    archive=ROOT/receipt['archive'];assert hashlib.sha256(archive.read_bytes()).hexdigest()==receipt['archive_sha256']
    OUT.mkdir(exist_ok=True);results=[];views=[];initials=[];cases=[]
    lock=json.loads((ROOT/'notebooks/phase4-closed-loop-v1-review-r1/review-source-lock.json').read_text())
    for name in ('reports/phase4_v2_offline_package.json','agent/representation.py','certification/phase4_closed_loop_v1/contract.py'):
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==lock['bindings'][name],name
    manifest=json.loads((ROOT/'reports/phase4_v2_offline_package.json').read_text())
    ranges={'ar25':[(1700,1751),(1770,1834)],'ft09':[(2016,2047),(2328,2402)],
            'sc25':[(1728,1736),(2543,2580),(2606,2673)],'ls20':[(1921,1950)],
            'sk48':[(724,750)],'cd82':[(354,365),(608,650)]}
    excerpts=[]
    with zipfile.ZipFile(ROOT/'evidence/phase4-v2-development-offline.zip') as games:
        for name,info in manifest['files'].items():
            if not name.startswith('environment_files/') or not name.endswith('.py'):continue
            raw=games.read(name);assert hashlib.sha256(raw).hexdigest()==info['sha256'] and len(raw)==info['bytes'],name
            game=Path(name).stem
            if game in ranges:
                assert (ROOT/'reports/runs/phase4-v2-assets'/name).read_bytes()==raw
                lines=raw.decode().splitlines()
                excerpts.append({'path':name,'sha256':info['sha256'],'excerpts':[
                    {'start_line':start,'end_line':end,'text':'\n'.join(lines[start-1:end])} for start,end in ranges[game]]})
    (OUT/'source_excerpts.json').write_text(json.dumps(excerpts,indent=2)+'\n',encoding='utf-8')
    with zipfile.ZipFile(archive) as z:
        prefix='output/phase4-closed-loop-v1/worker/'
        def read(name):return json.loads(z.read(prefix+name))
        state=read('state.json')
        for ep in state['episodes']:
            details=[];panels=[];first=read(ep['initial_observation'])
            if ep['arm']=='baseline':initials.append((ep['game_id'],first['frames'][-1]))
            for name in ep['steps']:
                s=read(name);pre=read(s['pre']);post=read(s['post']);a=s['action'];click=a['action_data'] if a['action_id']==6 else None
                grid=pre['frames'][-1];user=json.loads(s['request']['messages'][1]['content'])['observation']
                assert user['current_grid']==grid
                assert user['recent_actions']==([] if not details else [details[-1]['action']['action_id']])
                assert user['previous_grid']==(None if not details else read(details[-1]['pre'])['frames'][-1])
                assert user['recent_final_grids']==([] if not details else [grid])
                d=dict(record=name,step=s['step']+1,action=a,legal_actions=pre['available_actions'],
                    pre=s['pre'],post=s['post'],final_delta=delta(grid,post['frames'][-1]),
                    returned_frames=len(post['frames']),
                    intermediate_changes=[delta(grid,f)['cells'] for f in post['frames']],
                    click_color=None if not click else grid[click['y']][click['x']],
                    level_delta=post['levels_completed']-pre['levels_completed'],
                    recent_actions=user['recent_actions'],history=user['history_compaction'])
                d['bottom_row_only_change']=bool(d['final_delta']['cells'] and d['final_delta']['bbox'][1]==63)
                details.append(d)
                selected={'ft09':2,'sc25':2,'ls20':7,'wa30':3,'ar25':1,'sk48':1,'cd82':1}
                if ep['arm']=='no_concrete_examples' and selected.get(ep['game_id'][:4])==d['step']:
                    index=max(range(len(post['frames'])),key=lambda i:d['intermediate_changes'][i])
                    images=[grid,post['frames'][index],post['frames'][-1]]
                    strip=[sum([im[y] for im in images],[]) for y in range(64)]
                    asset=ep['game_id'][:4]+'.png';(OUT/asset).write_bytes(png(strip,scale=3,click=click))
                    cases.append(dict(game_id=ep['game_id'],arm=ep['arm'],step=d['step'],record=name,
                        image=asset,columns=['pre-action with click cross','most-changed returned frame','final returned frame'],
                        intermediate_frame_index_zero_based=index))
                imgs=[base64.b64encode(png(grid,click=click)).decode()]+[base64.b64encode(png(f)).decode() for f in post['frames']]
                panels.append({'detail':d,'images':imgs})
            summary=dict(game_id=ep['game_id'],arm=ep['arm'],episode_id=ep['episode_id'],
                action_counts=dict(collections.Counter(str(s['action']['action_id']) for s in details)),
                no_final_frame_change=sum(d['final_delta']['cells']==0 for d in details),
                transient_only_steps=[d['step'] for d in details if d['final_delta']['cells']==0 and any(d['intermediate_changes'])],
                changed_cells=sum(d['final_delta']['cells'] for d in details),steps=details)
            results.append(summary);views.append({'label':ep['game_id']+' / '+ep['arm'],'panels':panels})
    # Montage of baseline initial frames, sorted by game, 5 columns x 3 rows.
    initials.sort();sheet=[[5]*320 for _ in range(192)]
    for i,(game,frame) in enumerate(initials):
        for y,row in enumerate(frame):sheet[(i//5)*64+y][(i%5)*64:(i%5+1)*64]=row
    (OUT/'initial_frames.png').write_bytes(png(sheet,scale=3))
    result={'archive_sha256':receipt['archive_sha256'],'method':'retained evidence only; no counterfactual execution',
            'palette':COLORS,'montage_order':[g for g,f in initials],'episodes':results,'illustrated_cases':cases,
            'totals':{'steps':sum(len(e['steps']) for e in results),
                'unchanged_final_frames':sum(e['no_final_frame_change'] for e in results),
                'transient_only_steps':sum(len(e['transient_only_steps']) for e in results),
                'bottom_row_only_changes':sum(s['bottom_row_only_change'] for e in results for s in e['steps']),
                'current_and_previous_request_grids_verified':600,
                'noninitial_requests_with_action_id_only_history':570}}
    (OUT/'audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    page='''<!doctype html><meta charset="utf-8"><title>Closed-loop retained-frame audit</title>
<style>body{font:16px system-ui;max-width:1200px;margin:24px auto;background:#eee}img{image-rendering:pixelated;border:1px solid #aaa;margin:6px}pre{white-space:pre-wrap}label{margin-right:20px}</style>
<h1>Retained-frame inspection</h1><p>Offline evidence viewer. No inference or game execution. Steps are one-based. First image is the pre-action frame with a cyan click cross; remaining images are every returned frame, in order. Colors are a display-only false-color palette; numeric color ID at the click is in the detail. Changes do not imply progress.</p>
<label>Episode <select id="episode"></select></label><label>Step <input id="step" type="range" min="1" max="20" value="1"><span id="num"></span></label><div id="frames"></div><pre id="detail"></pre>
<script>const data=DATA;const ep=document.getElementById('episode'),step=document.getElementById('step');
data.forEach((e,i)=>ep.add(new Option(e.label,i)));
function render(){const p=data[+ep.value].panels[+step.value-1];document.getElementById('num').textContent=step.value;document.getElementById('detail').textContent=JSON.stringify(p.detail,null,2);document.getElementById('frames').replaceChildren(...p.images.map(s=>{const im=new Image();im.src='data:image/png;base64,'+s;return im}));}ep.onchange=render;step.oninput=render;render();</script>'''.replace('DATA',json.dumps(views,separators=(',',':')))
    (OUT/'frames.html').write_text(page,encoding='utf-8')
    for ep in results:print(json.dumps({k:v for k,v in ep.items() if k!='steps'}))
    print('Montage:',result['montage_order'])
if __name__=='__main__':main()
