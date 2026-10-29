"""M1 extension: observation-local effects, without changing the pinned M1 payload."""
from collections import Counter
from .scene import extract_scene, identity_candidates


def object_effects(before, after):
    """Return computed differences and explicitly uncertain identity interpretations."""
    a, b = extract_scene(before, 'before'), extract_scene(after, 'after')
    if (len(before), len(before[0])) != (len(after), len(after[0])):
        return dict(status='dimensions_changed', candidates=[], unmatched_before=[],
                    unmatched_after=[], adjacency_changes=[], co_motion_groups=[])
    links = identity_candidates([a], b)
    left, right = Counter(x['before'] for x in links), Counter(x['after'] for x in links)
    regions = {r['id']: r for s in (a, b) for r in s['regions']}
    changed = {(r, c) for r, row in enumerate(before) for c, v in enumerate(row) if v != after[r][c]}
    candidates = []
    mapping = {}
    for link in links:
        old, new = regions[link['before']], regions[link['after']]
        unique = left[old['id']] == right[new['id']] == 1
        both_changed = bool(changed.intersection(map(tuple, old['cells']))) and bool(changed.intersection(map(tuple, new['cells'])))
        delta = link['translation']
        kind = ('translation_candidate' if delta and any(delta) and both_changed else
                'unchanged_mask' if old['cells'] == new['cells'] else 'mask_change_candidate')
        candidates.append(dict(before=old['id'], after=new['id'], kind=kind,
            displacement=delta, unique_within_candidates=unique, both_changed=both_changed,
            appearance=dict(color=old['color'], shape=old['shape']),
            alternatives=['same_entity', 'different_entities']))
        if unique:
            mapping[old['id']] = new['id']
    old_rel = {tuple(sorted(mapping[x] for x in r['regions'])) for r in a['relations']
               if all(x in mapping for x in r['regions'])}
    mapped = set(mapping.values())
    new_rel = {tuple(sorted(r['regions'])) for r in b['relations'] if all(x in mapped for x in r['regions'])}
    groups = {}
    for c in candidates:
        if c['kind'] == 'translation_candidate' and c['unique_within_candidates']:
            groups.setdefault(tuple(c['displacement']), []).append(c['before'])
    return dict(status='comparable', candidates=candidates,
        unmatched_before=[r['id'] for r in a['regions'] if not left[r['id']]],
        unmatched_after=[r['id'] for r in b['regions'] if not right[r['id']]],
        adjacency_changes=[dict(kind=kind, after_region_ids=list(pair), identity_conditional=True)
                           for kind, pairs in [('lost', old_rel-new_rel), ('gained', new_rel-old_rel)]
                           for pair in sorted(pairs)],
        co_motion_groups=[dict(displacement=list(d), before_region_ids=ids, status='tentative_group')
                          for d, ids in sorted(groups.items()) if len(ids) > 1])


def transition_effects(snapshot):
    """Every returned frame, including transients; boundaries never imply motion."""
    observations = {o['id']: o for o in snapshot['observations']}
    records = []
    for t in snapshot['transitions']:
        previous = observations[t['before_observation_id']]
        for current in (o for o in snapshot['observations'] if o['transition_id'] == t['id']):
            effect = (dict(status='segment_boundary', candidates=[]) if current['segment'] != previous['segment']
                      else object_effects(previous['grid'], current['grid']))
            records.append(dict(episode_id=snapshot['episode_id'], transition_id=t['id'],
                before_observation_id=previous['id'], after_observation_id=current['id'], effect=effect))
            previous = current
    return dict(version='mac_object_effects_v1', records=records)
