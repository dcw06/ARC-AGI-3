"""New version of the diagnostic inventory; preserve the original protocol draft."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.build_grounding_diagnostic_v1 import build,summary,SYSTEM
from certification.phase4_grounding_v1.cases import request_hash
from certification.phase4_grounding_v1.answers import recompute,schema

def component_targets(grid):
    seen=set();groups=[]
    for y,row in enumerate(grid):
        for x,color in enumerate(row):
            if (x,y) in seen:continue
            todo=[(x,y)];seen.add((x,y));points=[]
            while todo:
                px,py=todo.pop();points.append((px,py))
                for nx,ny in ((px-1,py),(px+1,py),(px,py-1),(px,py+1)):
                    if 0<=ny<len(grid) and 0<=nx<len(row) and (nx,ny) not in seen and grid[ny][nx]==color:
                        seen.add((nx,ny));todo.append((nx,ny))
            groups.append((color,points))
    eligible=[(color,points) for color,points in groups if 2<=len(points)<len(grid)*len(grid[0])//2 and
              sum(c==color and len(p)==len(points) for c,p in groups)==1]
    if not eligible:raise ValueError('no unique visible region')
    return min(eligible,key=lambda cp:(len(cp[1]),cp[0]))

def generate():
    old=build();rows=[]
    model=json.loads((ROOT/'certification/phase4_transient_v2/protocol.json').read_bytes())['model_binding']['model_id']
    for case,answer,provenance in zip(old['cases.json'],old['answers.json'],old['provenance.json']):
        task=case['task'];expected=answer['expected']
        instruction=json.loads(case['request']['messages'][1]['content'])['instruction']
        if task['kind']=='locate':
            color,points=component_targets(task['grid']);task={'kind':'locate','grid':task['grid'],'color':color,'area':len(points)}
            expected=summary(points)
            instruction='Locate the unique four-neighbor connected region of the specified color and area (number of cells). Return count, inclusive bbox [xmin,ymin,xmax,ymax], and first {x,y} cell in row-major order.'
        assert expected==recompute(task)
        request={'model':model,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps({'instruction':instruction,**task},sort_keys=True,separators=(',',':'))}],
            'temperature':0,'seed':0,'max_tokens':128,'chat_template_kwargs':{'enable_thinking':False},'response_format':schema(task['kind'])}
        rows.append({'case_id':case['case_id'],'game_id':provenance['game_id'],'source_group':provenance['episode_id'],
            'task':task,'request':request,'request_sha256':request_hash(request),'expected':expected,'sources':provenance['frames']})
    return rows

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
    raw=(json.dumps(generate(),sort_keys=True,indent=2)+'\n').encode();path=ROOT/'certification/phase4_grounding_v1/cases.json'
    if args.check:assert path.read_bytes()==raw,'inventory drift'
    else:
        with path.open('xb') as f:f.write(raw)
    print('12 cases; four correlated source groups; mechanical answers independently verified; no model calls')
