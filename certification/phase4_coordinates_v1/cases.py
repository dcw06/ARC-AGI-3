"""Deterministic source-bound coordinate pairs; no game-source access."""
import copy,hashlib,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SEED=20260922
BASELINE='Return {"color": integer} for the cell at the supplied x,y.'
EXPLICIT=BASELINE+' Here x selects the column, y selects the row, and the requested value is grid[y][x].'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
def request_hash(request):return sha(json.dumps(request,sort_keys=True).encode())
def canary_request(model):
    from certification.phase4_grounding_v1.cases import canary_request as historical
    return historical(model)
def generate():
    # Existing builder checks the retained archive digest and reads observations only.
    from scripts.build_grounding_diagnostic_v1 import build
    old=build();historical=json.loads((ROOT/'certification/phase4_grounding_v1/cases.json').read_bytes())
    sources=[]
    for c,p in zip(old['cases.json'],old['provenance.json']):
        if c['task']['kind']=='coordinate':
            sources.append({'source_group':p['episode_id'],'kind':'retained','game_id':p['game_id'],
                'grid':c['task']['grid'],'provenance':p['frames']})
    for size in (8,16,32):
        # SHA-256 stream avoids platform-specific random-library algorithms.
        values=[]
        for block in range((size*size+31)//32):
            values.extend(b%16 for b in hashlib.sha256(f'{SEED}:{size}:{block}'.encode()).digest())
        sources.append({'source_group':f'synthetic-{size}','kind':'synthetic','game_id':None,
            'grid':[values[y*size:(y+1)*size] for y in range(size)],'provenance':{'seed':SEED,'algorithm':'sha256(seed:size:block), bytes modulo 16'}})
    rows=[];color_counts=Counter()
    template=next(c['request'] for c in historical if c['task']['kind']=='coordinate')
    for group_index,source in enumerate(sources):
        grid=source['grid'];size=len(grid)
        if any(len(row)!=size for row in grid):raise ValueError('square required')
        for stratum in ('boundary','interior'):
            eligible=[(x,y) for y in range(size) for x in range(y+1,size)
                if grid[y][x]!=grid[x][y] and
                (x in (0,size-1) or y in (0,size-1))==(stratum=='boundary')]
            if not eligible:raise ValueError('no discriminating coordinate')
            def rank(p):
                x,y=p;colors=(grid[y][x],grid[x][y])
                tie=sha(f'{SEED}:{source["source_group"]}:{stratum}:{x}:{y}'.encode())
                return (sum(color_counts[c] for c in colors),max(color_counts[c] for c in colors),tie)
            x,y=min(eligible,key=rank);color_counts.update((grid[y][x],grid[x][y]))
            for direction,(cx,cy) in enumerate(((x,y),(y,x))):
                pair_id=f'p{group_index}-{stratum}-{direction}'
                order=('baseline','explicit') if (group_index+direction)%2==0 else ('explicit','baseline')
                for condition in order:
                    request=copy.deepcopy(template)
                    payload={'instruction':BASELINE if condition=='baseline' else EXPLICIT,
                        'kind':'coordinate','grid':grid,'x':cx,'y':cy}
                    request['messages'][1]['content']=json.dumps(payload,sort_keys=True,separators=(',',':'))
                    rows.append({'case_id':pair_id+'-'+condition,'pair_id':pair_id,'condition':condition,
                        'source_group':source['source_group'],'source_kind':source['kind'],'game_id':source['game_id'],
                        'size':size,'stratum':stratum,'provenance':source['provenance'],'grid_sha256':sha(encoded(grid)),
                        'expected_color':grid[cy][cx],'transposed_color':grid[cx][cy],
                        'request':request,'request_sha256':request_hash(request)})
    return rows

def load():
    rows=json.loads(Path(__file__).with_name('cases.json').read_bytes())
    if rows!=generate():raise ValueError('case inventory/order/provenance drift')
    return rows

def load_cases():
    # Runtime uses the source-lock-bound bytes, without loading archives into the GPU session.
    rows=json.loads(Path(__file__).with_name('cases.json').read_bytes())
    if len(rows)!=56 or len({r['case_id'] for r in rows})!=56:raise ValueError('inventory')
    for r in rows:
        if r['request_sha256']!=request_hash(r['request']):raise ValueError('request drift')
    return rows
