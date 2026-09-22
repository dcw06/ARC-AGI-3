"""Freeze or verify offline coordinate cases; no model execution."""
import argparse,json,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from certification.phase4_coordinates_v2.cases import generate,encoded,sha
from certification.phase4_coordinates_v2.score import truth
def build(check=False):
    rows=generate();counts=Counter();by_source={}
    for row in rows:
        a,b=truth(row);assert a==row['expected_color'] and b==row['transposed_color']
        if row['condition']=='baseline':counts[a]+=1
        by_source[row['source_group']]={'kind':row['source_kind'],'size':row['size'],'game_id':row['game_id']}
    report={'status':'offline_coding_milestone_not_launch_authority','cases':len(rows),'paired_targets':len(rows)//2,
        'source_groups':by_source,'target_colors_per_condition':{str(c):counts[c] for c in range(16)},
        'selection_seed':20260922,'model_calls':0,'authorized_seconds':0,
        'boundary_targets_per_condition':sum(r['condition']=='baseline' and r['stratum']=='boundary' for r in rows),
        'interior_targets_per_condition':sum(r['condition']=='baseline' and r['stratum']=='interior' for r in rows)}
    for name,value in [('certification/phase4_coordinates_v2/cases.json',rows),('reports/phase4_coordinates_v2_inventory.json',report)]:
        path=ROOT/name;raw=encoded(value)
        if check:assert path.read_bytes()==raw,name
        else:
            with path.open('xb') as f:f.write(raw)
    print(json.dumps(report,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');build(p.parse_args().check)
