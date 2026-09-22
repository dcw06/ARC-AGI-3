"""Freeze observation-only ar25 case references; no game API or model calls."""
import argparse, hashlib, json, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/integrated_case_v1'
ARCHIVE = 'evidence/phase4-closed-loop-v1-r1-completed-v1.zip'
ARCHIVE_SHA = '994dc62307777a1adf301986aa2548bb9dad84ab438963d20392736abd493f9d'
BASE = 'output/phase4-closed-loop-v1/worker/'

def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def normalize(points):
    x0, y0 = min(x for x,y in points), min(y for x,y in points)
    return sorted([[x-x0,y-y0] for x,y in points], key=lambda p:(p[1],p[0]))

def transforms(points):
    result = {}
    for reflect in (False, True):
        for turns in range(4):
            out=[]
            for x,y in points:
                if reflect:x=-x
                for _ in range(turns):x,y=-y,x
                out.append((x,y))
            result[('reflect_x_then_' if reflect else '')+f'rotate_cw_{turns*90}']=normalize(out)
    return result

def build():
    raw=(ROOT/ARCHIVE).read_bytes();assert sha(raw)==ARCHIVE_SHA
    with zipfile.ZipFile(ROOT/ARCHIVE) as z:
        state=json.loads(z.read(BASE+'state.json'))
        ep=next(e for e in state['episodes'] if e['episode_id']=='cl1-00-no_concrete_examples')
        member=BASE+ep['initial_observation']; observation_raw=z.read(member)
        observation=json.loads(observation_raw)
    grid=observation['frames'][-1]
    assert len(grid)==64 and all(len(r)==64 for r in grid)
    objects=[]
    # Observation-selected ROIs, explicitly annotations, not discovered game entities.
    for oid,box,colors in [('A',[18,15,26,23],[0,5]),('B',[36,15,44,23],[4]),('C',[51,45,59,53],[11])]:
        x0,y0,x1,y1=box
        cells=[[x,y] for y in range(y0,y1+1) for x in range(x0,x1+1) if grid[y][x] in colors]
        markings=[[x,y,grid[y][x]] for x,y in cells if oid=='A' and grid[y][x]==0]
        occupied={tuple(p) for p in cells}
        contour=[p for p in cells if any((p[0]+dx,p[1]+dy) not in occupied for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)))]
        objects.append({'id':oid,'bbox':box,'cells':cells,'silhouette':normalize(cells),
                        'boundary_cells':contour,'colors':colors,'markings':markings})
    relations=[]
    for a,b in ((objects[0],objects[1]),(objects[0],objects[2]),(objects[1],objects[2])):
        relations.append({'from':a['id'],'to':b['id'],'valid_normalized_transforms':[
            k for k,v in transforms(a['cells']).items() if v==b['silhouette']]})
    return {'initial_observation.json':observation,
            'geometry_reference.json':{'annotation_scope':'reviewer-only visible ROI masks, not game entities or rules',
                'background_color':9,'objects':objects,'relations':relations,
                'other_visible_regions':'color 10 vertical stripe x30..32 y0..62; color 11 right border x63; color 5 bottom row y63. No UI or mechanics meaning assigned.'},
            'case.json':{'id':'integrated-ar25-v1','game_id':ep['game_id'],'environment_seed':0,'request_seed':0,
                'source_archive':ARCHIVE,'source_archive_sha256':ARCHIVE_SHA,'source_member':member,
                'source_member_sha256':sha(observation_raw),'source_episode':ep['episode_id'],
                'initial_canonical_hash':observation['canonical_hash'],'frame_index':len(observation['frames'])-1,
                'grid_sha256':sha(encode(grid)),'available_actions':observation['available_actions'],
                'max_actions_per_arm':8,'arms':['unassisted_control','structured_diagnostic'],
                'max_model_calls':26,'max_canaries':1,'max_generated_tokens':19584,
                'provider_seconds_authorized':0,'status':'frozen_specification_pending_review_and_implementation'}}

def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');args=p.parse_args()
    values=build()
    if args.check:
        for name,value in values.items():assert (OUT/name).read_bytes()==encode(value),name
        lock=json.loads((OUT/'spec-lock.json').read_bytes())
        for name,digest in lock['bindings'].items():assert sha((ROOT/name).read_bytes())==digest,name
        assert all(len(o['cells'])==45 for o in values['geometry_reference.json']['objects'])
        assert len(values['geometry_reference.json']['objects'][0]['markings'])==5
        print('Case provenance, geometry, and specification lock verified; zero model calls/actions.')
    else:
        OUT.mkdir(parents=True,exist_ok=True)
        for name,value in values.items():
            with (OUT/name).open('xb') as f:f.write(encode(value))
        paths=[OUT/n for n in values]+[OUT/'protocol.md',OUT/'rubric.md',Path(__file__).resolve(),
            ROOT/'reports/solving_development_boundary_v1.json',ROOT/'certification/phase4_transient_v2/protocol.json',
            ROOT/'certification/phase4_coordinates_v2/tokenizer_manifest.json']
        with (OUT/'spec-lock.json').open('xb') as f:
            f.write(encode({'status':'specification_only_not_launch_authority','bindings':{
                p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in paths}}))
        print('Frozen specification; no launch authority.')

if __name__=='__main__':main()
