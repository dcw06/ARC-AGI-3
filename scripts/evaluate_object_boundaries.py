"""CPU-only scoring of supplied, frame-bound masks against a reviewed reference."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research.object_discovery_boundaries_v1.evaluation import evaluate
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('preparation','review','predictions','output','experiment-manifest','experiment-manifest-sha256'):p.add_argument('--'+name,required=True)
    p.add_argument('--level',choices=('whole','parts'),action='append');p.add_argument('--match-iou',type=float,default=.5)
    a=p.parse_args();result=evaluate(a.preparation,a.review,a.predictions,levels=tuple(a.level or ['whole']),match_iou=a.match_iou,
        experiment_manifest=a.experiment_manifest,experiment_manifest_sha256=a.experiment_manifest_sha256)
    with Path(a.output).open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,sort_keys=True)
    print(json.dumps(result,indent=2))
