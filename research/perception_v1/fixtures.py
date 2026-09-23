"""Visible geometry fixtures from retained ar25 and deterministic synthetic grids."""
import hashlib,itertools,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
D4=tuple(('mirror_left_right_then_' if mirror else '')+'rotate_cw_'+str(turn*90)
         for mirror in (False,True) for turn in range(4))

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def normalize(cells):
    cells=set(map(tuple,cells));x=min(x for x,y in cells);y=min(y for x,y in cells)
    return {(a-x,b-y) for a,b in cells}
def transform(cells,name):
    points=normalize(cells)
    if name.startswith('mirror'):points={(-x,y) for x,y in points}
    for _ in range(int(name.rsplit('_',1)[1])//90):points={(-y,x) for x,y in points}
    return normalize(points)
def transforms(a,b):return [t for t in D4 if transform(a,t)==normalize(b)]
def inverse(name):
    if name.startswith('mirror'):return name
    return 'rotate_cw_'+str((-int(name.rsplit('_',1)[1]))%360)
def bbox(cells):return [min(x for x,y in cells),min(y for x,y in cells),max(x for x,y in cells),max(y for x,y in cells)]
def occupancy(cells):
    cells=set(map(tuple,cells));x0,y0,x1,y1=bbox(cells);w=x1-x0+1;h=y1-y0+1
    result=[]
    for j in range(3):
        row=[]
        for i in range(3):
            region={(x,y) for y in range(y0+j*h//3,y0+(j+1)*h//3) for x in range(x0+i*w//3,x0+(i+1)*w//3)}
            row.append(int(bool(region) and 2*len(region&cells)>=len(region)))
        result.append(row)
    return result
def reference(grid,objects,regions):
    records=[]
    for name,cells,markings in objects:
        points=sorted(map(tuple,cells));colors=sorted({grid[y][x] for x,y in points})
        records.append({'id':name,'cells':[list(p) for p in points],'bbox':bbox(points),'colors':colors,
            'occupancy':occupancy(points),'has_markings':bool(markings),'marking_colors':sorted(set(markings))})
    relations=[{'a':a['id'],'b':b['id'],'transforms':transforms(a['cells'],b['cells'])}
               for a,b in itertools.combinations(records,2)]
    return {'objects':records,'non_object_regions':regions,'relations':relations}
def build():
    obs_path=ROOT/'reports/integrated_case_v1/initial_observation.json'
    ref_path=ROOT/'reports/integrated_case_v1/geometry_reference.json'
    obs=json.loads(obs_path.read_bytes());old=json.loads(ref_path.read_bytes());grid=obs['frames'][-1]
    objects=[(o['id'],o['cells'],[m[2] for m in o['markings']]) for o in old['objects']]
    # Only reviewer-visible boxes; never import game source or inferred game roles.
    regions=[r['bbox'] for r in old['other_visible_regions'] if 'bbox' in r]
    cases=[{'id':'P1','source_group':'ar25-initial','source':{'observation':obs_path.relative_to(ROOT).as_posix(),
        'observation_sha256':hashlib.sha256(obs_path.read_bytes()).hexdigest(),
        'reviewer_reference_sha256':hashlib.sha256(ref_path.read_bytes()).hexdigest()},'grid':grid,
        'reference':reference(grid,objects,regions),'chiral_scoring':False}]
    f={(1,0),(2,0),(0,1),(1,1),(1,2)}
    assert not any(t.startswith('mirror') for t in transforms(f,f))
    for index in range(2,6):
        grid=[[9]*64 for _ in range(64)];objects=[];regions=[]
        shapes=[f,transform(f,'rotate_cw_90' if index==2 else 'mirror_left_right_then_rotate_cw_0')]
        if index==5:shapes=[f,{(0,0),(1,0),(2,0),(1,1),(1,2)}]
        for k,shape in enumerate(shapes):
            cells={(x*3+dx+8+30*k,y*3+dy+10+20*k) for x,y in shape for dx in range(3) for dy in range(3)}
            color=5 if index==5 else (4 if k==0 else 11)
            for x,y in cells:grid[y][x]=color
            markings=[]
            if index==4 and k==0:
                x,y=sorted(cells)[len(cells)//2];grid[y][x]=0;markings=[0]
            objects.append((chr(65+k),cells,markings))
        if index==4:
            for row in grid:row[29:32]=[10]*3
            regions=[[29,0,31,63]]
        cases.append({'id':'P'+str(index),'source_group':'synthetic-P'+str(index),'source':{'generator':'research/perception_v1/fixtures.py'},
            'grid':grid,'reference':reference(grid,objects,regions),'chiral_scoring':index in (2,3)})
    for c in cases:c['grid_sha256']=digest(c['grid'])
    return cases
def gold(case):
    return {'objects':[{**{k:v for k,v in o.items() if k!='cells'},'description':'fixture'} for o in case['reference']['objects']],
        'non_object_regions':[{'bbox':b,'description':'visible region'} for b in case['reference']['non_object_regions']],
        'relations':[{'a':r['a'],'b':r['b'],'same_shape':bool(r['transforms']),
            'transform':r['transforms'][0] if r['transforms'] else 'different_shape'} for r in case['reference']['relations']]}
