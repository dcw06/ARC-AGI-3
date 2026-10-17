"""Explicit local freeze, separate from scoring; no inferred review or approval.

Commit the manifest (and retain its SHA256 in an independent review record)
before invoking an evaluator. Re-freezing a changed review is a new experiment
revision, never a repair of an old result. Retrospective freezes must say so.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.object_discovery_boundaries_v1.experiment import source_pins
from research.object_discovery_boundaries_v1.reference_audit import canonical,digest
from research.object_discovery_boundaries_v1.scoring import score_frame


def freeze(references,output,*,reference_sha256,experiment_id,chronology,seed_inputs=None,preparation=None):
    raw=Path(references).read_bytes()
    if digest(raw)!=reference_sha256:raise ValueError('reference differs from previously reviewed digest')
    if chronology not in ('before_inference','retrospective_audit') or not experiment_id.strip():
        raise ValueError('explicit experiment identity and honest freeze chronology required')
    refs=json.loads(raw)
    for frame in refs['frames']:score_frame([],frame)
    manifests={kind:digest((Path(folder)/name).read_bytes()) for kind,folder,name in (
        ('seed_inputs',seed_inputs,'manifest.json'),('preparation',preparation,'preparation-manifest.json')) if folder is not None}
    if not manifests:raise ValueError('at least one experiment input manifest required')
    frozen=dict(schema='object_boundary_experiment_v1',experiment_id=experiment_id,reference_sha256=reference_sha256,
        input_manifest_sha256=manifests,evaluation_source_sha256=source_pins(),levels=['whole'],match_iou=.5,
        chronology=chronology,frozen_at_utc=datetime.now(timezone.utc).isoformat(),
        owner_review_inferred=False,compute_authorized=False)
    payload=canonical(frozen)
    with Path(output).open('xb') as stream:stream.write(payload)
    return digest(payload)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('references','reference-sha256','output','experiment-id','chronology'):parser.add_argument('--'+name,required=True)
    parser.add_argument('--seed-inputs');parser.add_argument('--preparation')
    args=parser.parse_args()
    print(freeze(args.references,args.output,reference_sha256=args.reference_sha256,
        experiment_id=args.experiment_id,chronology=args.chronology,seed_inputs=args.seed_inputs,preparation=args.preparation))
