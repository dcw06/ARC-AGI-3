"""Exact labelled-cell hits, not bounding-box or obstacle-mechanics accuracy."""


def match_points(regions, points):
    if (type(points) is not list or len(points) > 96
            or any(type(p) is not dict or type(p.get('cell_xy')) is not list
                   or len(p['cell_xy']) != 2
                   or any(type(v) is not int or not 0 <= v < 64 for v in p['cell_xy']) for p in points)):
        raise ValueError('validated board-cell points required')
    cells = [{tuple(p) for p in region['target_points']} for region in regions]
    edges = {r:[p for p,point in enumerate(points) if tuple(point['cell_xy']) in mask]
             for r,mask in enumerate(cells)}
    owners = {}
    def augment(r, seen):
        for p in edges[r]:
            if p in seen:
                continue
            seen.add(p)
            if p not in owners or augment(owners[p],seen):
                owners[p] = r
                return True
        return False
    for r in edges:
        augment(r,set())
    return [{'reference_id':regions[r]['id'],'point_index':p} for p,r in sorted(owners.items())]


def score_case(reference, points, task):
    if task not in ('objects','barrier_candidates'):
        raise ValueError('unknown task')
    regions = reference['regions']
    if task == 'barrier_candidates':
        regions = [r for r in regions if r['kind'] == 'obstacle']
    strata = {}
    for name, refs in [('whole_regions',[r for r in regions if r['parent_id'] is None]),
                       ('parts',[r for r in regions if r['parent_id'] is not None])]:
        matches = match_points(refs,points)
        strata[name] = {'labelled_regions':len(refs),'matched_regions':len(matches),'matches':matches,
                        'coverage':len(matches)/len(refs) if refs else None,
                        'unmatched_point_indices_for_review':[i for i in range(len(points))
                                                             if i not in {m['point_index'] for m in matches}]}
    return {'case_id':reference['case_id'],'task':task,'localization':strata,
            'exhaustive_precision':None,'collision_accuracy':None,'full_mask_accuracy':None,
            'qualification':'Partial references. A point hit does not prove object extent, identity, role or blocking behavior.'}


def score_target(reference, target_region_id, points):
    """A cued single-object query earns credit only for its declared target."""
    refs = [r for r in reference['regions'] if r['id'] == target_region_id]
    if len(refs) != 1:
        raise ValueError('one predeclared target reference required')
    matches = match_points(refs,points)
    valid = len(points) <= 1
    return {'case_id':reference['case_id'],'target_region_id':target_region_id,
            'response_valid':valid,'point_count':len(points),
            'target_hit':valid and len(matches) == 1,
            'response_error':None if valid else 'multiple points for single-target prompt',
            'qualification':'Exact labelled-cell containment; center accuracy, click execution and gameplay untested.'}
