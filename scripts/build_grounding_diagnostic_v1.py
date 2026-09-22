"""Build an offline review-only dataset from retained observations, never game source."""
import argparse,hashlib,json,zipfile
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ARCHIVE='evidence/phase4-closed-loop-v1-r1-completed-v1.zip'
ARCHIVE_SHA='994dc62307777a1adf301986aa2548bb9dad84ab438963d20392736abd493f9d'
BASE='output/phase4-closed-loop-v1/worker/'
OUT='reports/grounding_diagnostic_v1'
GAMES=('ar25','ft09','ls20','sc25')
SYSTEM=('Read only the supplied integer grids. Coordinates are zero-based: x is column increasing right, '
        'y is row increasing down; grid[y][x]. Bounds are inclusive. Color IDs are numeric symbols, '
        'not named colors. Return only the requested JSON object, with integer values and null where specified. '
        'Do not propose actions or infer game rules.')

def encode(obj):return (json.dumps(obj,sort_keys=True,indent=2)+'\n').encode()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def validate_grid(grid):
    if not isinstance(grid,list) or not 1<=len(grid)<=64:raise ValueError('rows')
    if not isinstance(grid[0],list) or not 1<=len(grid[0])<=64:raise ValueError('columns')
    if any(not isinstance(row,list) or len(row)!=len(grid[0]) or any(type(c) is not int or not 0<=c<=15 for c in row) for row in grid):raise ValueError('grid values/shape')
def summary(points):
    if not points:return {'count':0,'bbox':None,'first':None}
    first=min(points,key=lambda p:(p[1],p[0]))
    return {'count':len(points),'bbox':[min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)],'first':{'x':first[0],'y':first[1]}}
def answer(task):
    g=task.get('grid')
    if task['kind']=='coordinate':return {'color':g[task['y']][task['x']]}
    if task['kind']=='locate':return summary([(x,y) for y,row in enumerate(g) for x,c in enumerate(row) if c==task['color']])
    a,b=task['before'],task['after']
    if len(a)!=len(b) or any(len(r)!=len(s) for r,s in zip(a,b)):raise ValueError('shape mismatch')
    result=summary([(x,y) for y,row in enumerate(a) for x,c in enumerate(row) if c!=b[y][x]])
    p=result['first'];result['first_change']=None if p is None else {'before':a[p['y']][p['x']],'after':b[p['y']][p['x']]}
    return result

def build():
    raw=(ROOT/ARCHIVE).read_bytes();assert digest(raw)==ARCHIVE_SHA,'historical archive drift'
    cases=[];answers=[];provenance=[]
    with zipfile.ZipFile(ROOT/ARCHIVE) as z:
        def read(name):
            value=json.loads(z.read(BASE+name))
            if 'frames' in value:
                for grid in value['frames']:validate_grid(grid)
            return value
        def source(name,index):return {'member':BASE+name,'sha256':digest(z.read(BASE+name)),'frame_index':index}
        state=read('state.json')
        for game in GAMES:
            ep=next(e for e in state['episodes'] if e['game_id'].startswith(game+'-') and e['arm']=='no_concrete_examples')
            name=ep['initial_observation'];frames=read(name)['frames'];g=frames[-1]
            counts=Counter(c for row in g for c in row);color=min(counts,key=lambda c:(counts[c],c))
            xy=next((x,y) for y,row in enumerate(g) for x,c in enumerate(row) if x!=y and x<len(g) and y<len(g[0]) and c!=g[x][y])
            tasks=[({'kind':'locate','grid':g,'color':color},[source(name,len(frames)-1)]),
                   ({'kind':'coordinate','grid':g,'x':xy[0],'y':xy[1]},[source(name,len(frames)-1)])]
            selected=None
            for stepname in ep['steps']:
                step=read(stepname);pre=read(step['pre'])['frames'];post=read(step['post'])['frames']
                for index,frame in enumerate(post):
                    # One genuine unchanged pair; three genuine changed pairs.
                    if (frame==pre[-1])==(game=='ar25'):
                        selected=({'kind':'changes','before':pre[-1],'after':frame},
                                  [source(step['pre'],len(pre)-1),source(step['post'],index)])
                        break
                if selected:break
            assert selected,game
            tasks.append(selected)
            for task,refs in tasks:
                cid=f'g{len(cases)+1:02d}';expected=answer(task)
                instruction={'locate':'For all cells of the specified color, return count, bbox [xmin,ymin,xmax,ymax], and first {x,y} in row-major order. Use null bbox/first for no cells.',
                    'coordinate':'Return {"color": integer} for the cell at the supplied x,y.',
                    'changes':'Compare before and after cellwise. Return count, bbox [xmin,ymin,xmax,ymax], first {x,y} in row-major order, and first_change {before,after} colors. Use null bbox/first/first_change when count is zero.'}[task['kind']]
                request={'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':json.dumps({'instruction':instruction,**task},sort_keys=True,separators=(',',':'))}]}
                cases.append({'case_id':cid,'task':task,'request':request})
                answers.append({'case_id':cid,'expected':expected})
                provenance.append({'case_id':cid,'game_id':ep['game_id'],'episode_id':ep['episode_id'],'frames':refs})
    return {'cases.json':cases,'answers.json':answers,'provenance.json':provenance}

def verify_answers(data):
    # Independently flatten/enumerate pixels, rather than call answer()/summary().
    for case,truth in zip(data['cases.json'],data['answers.json']):
        assert case['case_id']==truth['case_id'];t=case['task'];expected=truth['expected']
        if t['kind']=='coordinate':
            assert expected=={'color':t['grid'][t['y']][t['x']]};continue
        grid=t.get('grid',t.get('before'));w=len(grid[0]);flat=sum(grid,[])
        indices=[i for i,c in enumerate(flat) if (c==t['color'] if t['kind']=='locate' else c!=t['after'][i//w][i%w])]
        xs=[i%w for i in indices];ys=[i//w for i in indices]
        assert expected['count']==len(indices)
        assert expected['bbox']==([min(xs),min(ys),max(xs),max(ys)] if indices else None)
        assert expected['first']==({'x':xs[0],'y':ys[0]} if indices else None)
        if t['kind']=='changes':assert expected['first_change']==({'before':flat[indices[0]],'after':t['after'][ys[0]][xs[0]]} if indices else None)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    data=build();verify_answers(data);folder=ROOT/OUT
    if args.check:
        for name,value in data.items():assert (folder/name).read_bytes()==encode(value),name
        lock=json.loads((folder/'review-lock.json').read_bytes())
        for name,h in lock['bindings'].items():assert digest((ROOT/name).read_bytes())==h,name
    else:
        folder.mkdir(parents=True,exist_ok=False)
        for name,value in data.items():(folder/name).write_bytes(encode(value))
        names=[OUT+'/'+n for n in data]+['scripts/build_grounding_diagnostic_v1.py','reports/grounding_diagnostic_v1_protocol.md','tests/test_grounding_diagnostic_v1.py']
        lock={'status':'draft_pending_protocol_review_no_model_authority','archive':ARCHIVE,'archive_sha256':ARCHIVE_SHA,'model_calls_authorized':0,
              'bindings':{n:digest((ROOT/n).read_bytes()) for n in names}}
        (folder/'review-lock.json').write_bytes(encode(lock))
    print(json.dumps({'cases':len(data['cases.json']),'mechanical_answers_verified':True,'model_calls':0,'mode':'check' if args.check else 'build'}))

if __name__=='__main__':main()
