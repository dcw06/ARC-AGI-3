"""Cases for evidence comprehension v3: fresh seeded trajectories and matched synthetic counterfactual histories.

Informed by the v2 result; v2's questions (including its withheld partition) are development material. The
generation rules, templates, frames and record code are v2's (research/evidence_comprehension_v2/
trajectories.py), unchanged. What v3 changes:
- new seeds and per-template counts (enriched for stale-unchanged and same-frame-repeat trajectories);
- declared enrichment for the control comparison: every context whose legal set excludes ACTION6 (except the
  empty-history template) is redrawn until its shown history contains ACTION6;
- no observation may equal any v2 observation or any other v3 observation.

Synthetic counterfactual histories (Track A, secondary): for a context whose legal set excludes ACTION6 and whose
shown history contains ACTION6, the matched variant replaces every ACTION6 event of the trajectory (shown or not)
with one legal simple action, keeping every frame, outcome, level and reset exactly. The observation is then
rebuilt by the real record code from the altered events, so every action reference (history entries and
recent_actions) is consistent with the alteration. These histories are synthetic counterfactuals: they were never
played.
"""
import copy
import hashlib
import json
import random

from research.evidence_comprehension_v2 import trajectories as T

WITHHELD_COUNTS = {'mixed': 12, 'near_miss_clicks': 12, 'transient': 12, 'failed_and_unknown': 12,
                   'same_frame_repeats': 16, 'stale_unchanged': 20, 'level_boundary': 12, 'reset_boundary': 12,
                   'long_with_omitted': 12, 'empty_history': 8}
DEVELOPMENT_COUNTS = {name: 3 for name, _ in T.TEMPLATES}
PARTITIONS = {'withheld': ('evidence-comprehension-v3-withheld', WITHHELD_COUNTS),
              'development': ('evidence-comprehension-v3-development', DEVELOPMENT_COUNTS)}
MAX_REDRAWS = 200
COUNTERFACTUAL_SEED = 'evidence-comprehension-v3-counterfactual'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def shown_has_click(observation):
    return any(e['action_id'] == 6 for e in observation['action_effect_history']['entries'])


def contexts(base, partition, seen):
    """Seeded trajectories for one partition. `seen` holds canonical observations already used (v2's and v3's)."""
    seed, counts = PARTITIONS[partition]
    rng = random.Random(hashlib.sha256(seed.encode()).hexdigest())
    templates = dict(T.TEMPLATES)
    result = []
    for name, _ in T.TEMPLATES:
        for i in range(counts[name]):
            with_six = len(result) % 2 == 0
            context_id = f'{partition[:3]}-{name}-{i:02d}'
            for _ in range(MAX_REDRAWS):
                legal = rng.choice(T.LEGAL_WITH_6 if with_six else T.LEGAL_WITHOUT_6)
                trajectory = {'context_id': context_id, 'partition': partition, 'template': name,
                              'legal_actions': list(legal),
                              **T.run(rng, base, templates[name](rng, legal), levels=rng.randrange(T.WIN_LEVELS - 2))}
                observation = T.observation(trajectory)
                enrich = not with_six and name != 'empty_history'
                if canonical(observation) not in seen and (not enrich or shown_has_click(observation)):
                    break
            else:
                raise ValueError(f'{context_id}: no admissible draw in {MAX_REDRAWS}')
            seen.add(canonical(observation))
            errors = T.continuity_errors(trajectory)
            if errors:
                raise ValueError(errors[0])
            result.append(trajectory)
    return result


def counterfactual_eligible(trajectory):
    return 6 not in trajectory['legal_actions'] and shown_has_click(T.observation(trajectory))


def counterfactual(trajectory):
    """The matched synthetic counterfactual: every ACTION6 event replaced by one legal simple action."""
    if not counterfactual_eligible(trajectory):
        raise ValueError('not eligible for a counterfactual history')
    rng = random.Random(hashlib.sha256(f'{COUNTERFACTUAL_SEED}:{trajectory["context_id"]}'.encode()).hexdigest())
    replacement = {'action_id': rng.choice(sorted(i for i in trajectory['legal_actions'] if i != 6)), 'action_data': {}}
    events = [dict(e, action=copy.deepcopy(replacement)) if e['action']['action_id'] == 6 else copy.deepcopy(e)
              for e in trajectory['events']]
    return {**trajectory, 'events': events, 'variant': 'counterfactual', 'replacement_action': replacement,
            'source': 'synthetic_counterfactual_history'}
