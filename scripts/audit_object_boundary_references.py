"""Audit private frame-bound references locally; never start model inference."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research.object_discovery_boundaries_v1.reference_audit import audit

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--preparation',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();result=audit(a.preparation);out=Path(a.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,sort_keys=True)
    print(json.dumps(result['summary'],indent=2))
