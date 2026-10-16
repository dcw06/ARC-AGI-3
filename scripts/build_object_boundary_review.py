"""Create a private self-contained review page; no server, model or network."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from certification.phase4_multimodal_preflight_v3.images import PALETTE
from research.object_discovery_boundaries_v1.reference_audit import digest

def build(preparation,output):
    preparation,output=Path(preparation).resolve(),Path(output)
    manifest=json.loads((preparation/'preparation-manifest.json').read_bytes())
    for name,pin in manifest.items():
        p=preparation/name
        if not p.resolve().is_relative_to(preparation) or p.is_symlink() or digest(p.read_bytes())!=pin:
            raise ValueError('review preparation differs')
    name='references/review-draft.json'
    if name not in manifest:raise ValueError('review source is not bound')
    review=json.loads((preparation/name).read_bytes())
    data=json.dumps(dict(review=review,palette=PALETTE),allow_nan=False).replace('<','\\u003c')
    template=Path(__file__).with_name('object_boundary_review.html').read_text(encoding='utf-8')
    if template.count('__BOUNDARY_REVIEW_DATA__')!=1:raise ValueError('review template marker differs')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as f:f.write(template.replace('__BOUNDARY_REVIEW_DATA__',data))
    return dict(private_review=str(output),frames=len(review['frames']),regions=sum(len(f['regions']) for f in review['frames']),
                model_calls=0,provider_calls=0,automatic_review_approvals=0)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--preparation',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();print(json.dumps(build(a.preparation,a.output),indent=2))
