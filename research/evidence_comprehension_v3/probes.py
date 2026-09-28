"""Evidence comprehension v3 (revision 1): two narrow comparisons against v2's best conditions.

Informed by the v2 result (attempt ecv2-65759c16); v2's questions are development material.

Track A, control (unaided reference against computed control metadata):
- A0_intersect: v2's control_candidate prompt (baseline plus the intersect instruction; 0.883 in v2) and the
  live history field;
- A1_computed_control_metadata: A0 plus one computed field (representation.control_metadata). It precomputes
  the tested relationship; success means improved interface usability, not learned intersection.
- Secondary, non-gating: every eligible context is also asked with its matched synthetic counterfactual history
  (ACTION6 events replaced; cases.counterfactual), under A0 and A1.

Track B, history (unaided reference against tool-assisted):
- B0_normalized_history: v2's history_candidate (normalized records);
- B1_tool_eligibility: B0 plus per-entry tool fields (representation.eligibility). Results are tool-assisted.

Questions, answer schemas, keys, shortcuts and balancing are v2's, unchanged; v3 asks a subset of families.
"""
import copy
import hashlib
import json
import random

from research.evidence_comprehension_v2 import probes as V2
from research.evidence_comprehension_v2 import representation as R2
from research.evidence_comprehension_v3 import representation as R

VERSION = 'evidence_comprehension_v3_r1'
FROZEN_PATH = __import__('pathlib').Path(__file__).with_name('probes.json')
MODEL = V2.MODEL
MAX_TOKENS = V2.MAX_TOKENS

TRACKS = {
    'control': {'targets': ('legal_coordinate_actions',), 'components': ('legal_actions', 'action6_legal'),
                'reference': 'A0_intersect', 'candidate': 'A1_computed_control_metadata', 'suffix': ''},
    'history': {'targets': ('tried_unchanged',),
                'components': ('step_action_match', 'any_change', 'qualifying_steps', 'outcome_class',
                               'observed_effect'),
                'reference': 'B0_normalized_history', 'candidate': 'B1_tool_eligibility', 'suffix': '_tool_assisted'},
}
TRACK_OF = {f: name for name, t in TRACKS.items() for f in (*t['components'], *t['targets'])}
CONDITIONS = {t[role]: name for name, t in TRACKS.items() for role in ('reference', 'candidate')}
VARIANTS = ('original', 'counterfactual')
GATE_PARTITION = 'withheld'
PASSES = {'withheld': 2, 'development': 1, 'transfer': 1}


def load_frozen(path=FROZEN_PATH):
    raw = __import__('pathlib').Path(path).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def system_prompt(condition):
    return V2.CONTROL_PROMPT if CONDITIONS[condition] == 'control' else V2.BASE_PROMPT


def present(observation, condition):
    if condition == 'A0_intersect':
        return copy.deepcopy(observation)
    if condition == 'A1_computed_control_metadata':
        return R.with_control_metadata(observation)
    if condition == 'B0_normalized_history':
        return R2.candidate_observation(observation)
    if condition == 'B1_tool_eligibility':
        return R.with_tool_eligibility(observation)
    raise ValueError(condition)


def build_request(context, probe):
    user = {'observation': context['observation'], 'question': probe['question']}
    return {'model': MODEL, 'messages': [
        {'role': 'system', 'content': system_prompt(probe['condition'])},
        {'role': 'user', 'content': json.dumps(user, sort_keys=True, separators=(',', ':'))}],
        'temperature': 0, 'seed': 0, 'max_tokens': MAX_TOKENS[probe['family']],
        'chat_template_kwargs': {'enable_thinking': False}, 'response_format': V2.response_format(probe['family'])}


def question_args(observation, all_steps, rng, balancer):
    """v2's balanced arguments, keeping the first question of each v3 family."""
    kept, seen = [], set()
    for family, arg in V2.question_args(observation, all_steps, rng, balancer):
        if family in TRACK_OF and family not in seen:
            seen.add(family)
            kept.append((family, arg))
    return kept


def make_probes(partition, context_id, variant, observation, args, template):
    probes = []
    for n, (family, arg) in enumerate(args):
        track = TRACK_OF[family]
        if variant == 'counterfactual' and track != 'control':
            continue
        key = V2.primary_key(observation, family, arg)
        shortcuts = V2.shortcut_answers(family, arg, observation)
        strata = V2.strata(observation, family, arg, key, template) + [f'variant:{variant}']
        for role in ('reference', 'candidate'):
            condition = TRACKS[track][role]
            probes.append({
                'probe_id': f'{partition}:{condition}:{variant}:{context_id}-{n:02d}',
                'pair_id': f'{partition}:{variant}:{context_id}-{n:02d}',
                'variant_pair_id': f'{partition}:{condition}:{context_id}-{n:02d}',
                'context_id': f'{partition}:{condition}:{variant}:{context_id}',
                'source_context': context_id, 'partition': partition, 'condition': condition, 'role': role,
                'variant': variant, 'track': track,
                'family_role': 'target' if family in TRACKS[track]['targets'] else 'component',
                'family': family, 'arg': arg, 'question': V2.question_text(family, arg), 'key': key,
                'strata': strata,
                'shortcuts_correct': sorted(k for k, v in shortcuts.items() if V2.same_answer(family, v, key))})
    return probes


def rng_for(context_id):
    return random.Random(hashlib.sha256(f'{VERSION}:{context_id}'.encode()).hexdigest())
