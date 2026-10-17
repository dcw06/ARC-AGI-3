"""One-to-one instance/mask scoring. Unreviewed labels never produce a verdict."""
import math
from .masks import cells,boundary,validate_predictions


def assignment(weights):
    """Maximum-weight rectangular assignment, with deterministic index ties."""
    nr=len(weights);nc=len(weights[0]) if nr else 0
    if not nr or not nc:return []
    n=max(nr,nc)
    cost=[[-(weights[i][j] if i<nr and j<nc else 0.) for j in range(n)] for i in range(n)]
    u=[0.]*(n+1);v=[0.]*(n+1);p=[0]*(n+1);way=[0]*(n+1)
    for i in range(1,n+1):
        p[0]=i;j0=0;minimum=[math.inf]*(n+1);used=[False]*(n+1)
        while True:
            used[j0]=True;i0=p[j0];delta=math.inf;j1=0
            for j in range(1,n+1):
                if not used[j]:
                    cur=cost[i0-1][j-1]-u[i0]-v[j]
                    if cur<minimum[j]:minimum[j]=cur;way[j]=j0
                    if minimum[j]<delta:delta=minimum[j];j1=j
            for j in range(n+1):
                if used[j]:u[p[j]]+=delta;v[j]-=delta
                else:minimum[j]-=delta
            j0=j1
            if p[j0]==0:break
        while True:
            j1=way[j0];p[j0]=p[j1];j0=j1
            if j0==0:break
    return sorted((p[j]-1,j-1) for j in range(1,n+1) if p[j] and p[j]<=nr and j<=nc)


def reviewed_regions(frame,disposition='include'):
    """Validated reviewed references with the given disposition ('include' by default, or 'ignore')."""
    if disposition not in ('include','ignore'):raise ValueError('include or ignore disposition required')
    if (type(frame.get('inventory_policy')) is not str or not frame['inventory_policy'].strip()
            or type(frame.get('regions')) is not list or len(frame['regions'])>256):
        raise ValueError('reviewed inventory policy/regions required')
    ids=[r['id'] for r in frame['regions']]
    if any(type(i) is not str or not i for i in ids) or len(ids)!=len(set(ids)):
        raise ValueError('unique reference IDs required')
    by_id={r['id']:r for r in frame['regions']};result=[]
    for r in frame['regions']:
        if r.get('disposition') not in ('include','ignore','ambiguous') or r.get('mask_reviewed') is not True:
            raise ValueError('every reference needs an explicit mask/disposition review')
        mask=cells(r['cells']);seen={r['id']};parent=r.get('parent_id')
        while parent is not None:
            if parent not in by_id or parent in seen:raise ValueError('invalid reference hierarchy')
            seen.add(parent);parent=by_id[parent].get('parent_id')
        if r['disposition']==disposition:result.append((r,mask))
    return result


def _one_to_one(refs,selected,match_iou):
    """Pairs (i, j) of a maximum-cardinality, then maximum-IoU, one-to-one matching at IoU >= match_iou."""
    overlaps=[[len(a&b)/len(a|b) for _,b in selected] for _,a in refs]
    bonus=max(len(refs),len(selected))+1
    weights=[[bonus+v if v>=match_iou else 0. for v in row] for row in overlaps]
    return overlaps,[(i,j) for i,j in assignment(weights) if weights[i][j]>0]


def score_frame(predictions,frame,*,level='whole',match_iou=.5):
    if type(match_iou) not in (int,float) or not math.isfinite(match_iou) or not 0<match_iou<=1:
        raise ValueError('frozen IoU match threshold required')
    if level not in ('whole','parts'):raise ValueError('explicit hierarchy level required')
    masks=validate_predictions(predictions)
    # Explicit empty predictions remain failed proposals in this denominator.
    # References are nonempty, so their IoU is zero and they cannot match.
    selected=[(p,m) for p,m in zip(predictions,masks) if p['level']==level]
    in_level=lambda r:(r.get('parent_id') is None)==(level=='whole')
    refs=[(r,m) for r,m in reviewed_regions(frame) if in_level(r)]
    ignored=[(r,m) for r,m in reviewed_regions(frame,'ignore') if in_level(r)]
    exhaustive=frame.get('reference_exhaustive_confirmed') is True
    ambiguous=any(r['disposition']=='ambiguous' for r in frame['regions'])
    # Unresolved ambiguity prevents false-positive claims even after a checked box.
    full=exhaustive and not ambiguous
    overlaps,pairs=_one_to_one(refs,selected,match_iou)
    # Ignore regions are neutral (owner decision, October 16, 2026). Included references are matched first; each
    # prediction left unmatched may then match one ignore region one-to-one at the same IoU threshold, and is
    # removed from the scored prediction count: neither a hit nor a false positive.
    used={j for _,j in pairs}
    leftover=[k for k in range(len(selected)) if k not in used]
    ignored_overlaps,ignored_pairs=_one_to_one(ignored,[selected[k] for k in leftover],match_iou)
    ignored_matches=[dict(region_id=ignored[i][0]['id'],prediction_id=selected[leftover[j]][0]['id'],
                          iou=ignored_overlaps[i][j]) for i,j in ignored_pairs]
    matched=[]
    for i,j in pairs:
        ref,a=refs[i];pred,b=selected[j];ea,eb=boundary(a),boundary(b);common=len(ea&eb)
        matched.append(dict(reference_id=ref['id'],prediction_id=pred['id'],iou=overlaps[i][j],
            exact_mask=a==b,boundary_precision=common/len(eb),boundary_recall=common/len(ea),
            boundary_f1=2*common/(len(ea)+len(eb))))
    nr,nm=len(refs),len(pairs);np=len(selected)-len(ignored_pairs)
    return dict(level=level,match_iou=match_iou,matching='maximum eligible cardinality, then summed IoU',
        reference_count=nr,prediction_count=np,raw_prediction_count=len(selected),matched_count=nm,matches=matched,
        ignored_region_count=len(ignored),ignored_region_matches=ignored_matches,
        ignore_policy='neutral: a prediction matching an ignore region (after included references) is excluded '
                      'from the prediction count; neither a hit nor a false positive',
        labelled_reference_coverage=nm/nr if nr else None,
        detection_precision=nm/np if full and np else None,
        detection_recall=nm/nr if full and nr else None,
        false_positive_count=np-nm if full else None,
        unadjudicated_unmatched_predictions=np-nm if not full else 0,
        mean_iou_over_all_labelled_objects=sum(r['iou'] for r in matched)/nr if nr else None,
        exact_mask_fraction=sum(r['exact_mask'] for r in matched)/nr if nr else None,
        boundary_f1_over_all_labelled_objects=sum(r['boundary_f1'] for r in matched)/nr if nr else None,
        reference_inventory_complete=full,passing_verdict=None,
        qualification='Declared hierarchy stratum only. Unmatched references contribute zero; no automatic advancement threshold is supplied.')
