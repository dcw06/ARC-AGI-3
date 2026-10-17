"""Evaluate supplied masks against a source-bound human boundary review, offline."""
import json
from pathlib import Path
from .reference_audit import canonical,digest,validate_grid
from .scoring import score_frame
from .prepare import requests_for


def verified_preparation(preparation):
    preparation=Path(preparation).resolve()
    manifest=json.loads((preparation/'preparation-manifest.json').read_bytes())
    for name,pin in manifest.items():
        p=preparation/name
        if p.is_symlink() or not p.resolve().is_relative_to(preparation) or digest(p.read_bytes())!=pin:
            raise ValueError('prepared artifact differs: '+name)
    required={'protocol.json','references/review-draft.json','inputs/requests.jsonl'}
    if not required<=set(manifest):raise ValueError('required preparation artifacts not bound')
    requests_for(preparation/'inputs')
    root=Path(__file__).resolve().parents[2]
    protocol=json.loads((preparation/'protocol.json').read_bytes())
    if not protocol.get('source_sha256'):raise ValueError('preparation source binding missing')
    for name,pin in protocol['source_sha256'].items():
        p=root/name
        if not p.resolve().is_relative_to(root) or digest(p.read_bytes())!=pin:
            raise ValueError('evaluating source differs: '+name)
    return json.loads((preparation/'references/review-draft.json').read_bytes())


def validate_review(review,source):
    if (review.get('schema')!='object_boundary_reference_review_v1'
            or review.get('source_preparation_manifest_sha256')!=source['source_preparation_manifest_sha256']
            or type(review.get('frames')) is not list or len(review['frames'])!=len(source['frames'])):
        raise ValueError('review source/schema differs')
    for frame,old in zip(review['frames'],source['frames']):
        validate_grid(frame['grid'])
        if (frame['case_id']!=old['case_id'] or frame['grid_sha256']!=old['grid_sha256']
                or canonical(frame['grid'])!=canonical(old['grid'])
                or digest(canonical(frame['grid']))!=frame['grid_sha256']):
            raise ValueError('review frame/grid differs')
        if (type(frame.get('reference_exhaustive_confirmed')) is not bool
                or type(frame.get('reviewer')) is not str or not frame['reviewer'].strip()
                or len(frame['regions'])>256):
            raise ValueError('explicit reviewer and completeness state required')
        old_ids={r['id'] for r in old['regions']}
        if not old_ids<={r['id'] for r in frame['regions']}:
            raise ValueError('source regions removed; retain with an explicit disposition')
    return True


def evaluate(preparation,review_path,prediction_path,*,levels=('whole',),match_iou=.5):
    preparation=Path(preparation)
    source=verified_preparation(preparation)
    review_raw=Path(review_path).read_bytes();review=json.loads(review_raw);validate_review(review,source)
    raw=Path(prediction_path).read_bytes();predictions=json.loads(raw)
    if predictions.get('schema')!='object_boundary_predictions_v1':raise ValueError('prediction schema differs')
    rows=predictions['frames'];by_case={f['case_id']:f for f in rows}
    if len(rows)!=len(by_case) or set(by_case)!={f['case_id'] for f in review['frames']}:
        raise ValueError('missing/duplicate/unexpected predicted frames')
    if not levels or len(set(levels))!=len(levels) or any(l not in ('whole','parts') for l in levels):
        raise ValueError('explicit unique evaluated hierarchy levels required')
    results=[]
    for frame in review['frames']:
        pred=by_case[frame['case_id']]
        if pred['grid_sha256']!=frame['grid_sha256']:raise ValueError('prediction frame hash differs')
        valid=pred.get('model_response_valid')
        if type(valid) is not bool:raise ValueError('explicit model_response_valid boolean required')
        # An invalid response counts as zero objects found and stays in the totals (owner decision, October 16,
        # 2026); it is also reported as a format failure. It may not carry salvaged objects.
        if not valid and pred.get('objects')!=[]:raise ValueError('invalid model response supplies objects')
        if any(p.get('level') not in levels for p in pred['objects']):
            raise ValueError('prediction includes undeclared hierarchy level')
        results.append(dict(case_id=frame['case_id'],response_valid=valid,format_failure=not valid,
            strata={level:score_frame(pred['objects'],frame,level=level,match_iou=match_iou) for level in levels}))
    return dict(schema='object_boundary_evaluation_v1',frames=results,
        format_failure_frames=[r['case_id'] for r in results if r['format_failure']],
        invalid_response_policy='zero objects found; kept in all denominators and listed as a format failure',
        review_sha256=digest(review_raw),prediction_sha256=digest(raw),
        preparation_manifest_sha256=digest((preparation/'preparation-manifest.json').read_bytes()),
        passing_verdict=None,model_calls=0,provider_calls=0,
        qualification='Geometry evaluation of supplied predictions. Does not certify a model run or invent reference/advancement approval.')
