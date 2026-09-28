"""Evidence comprehension v2: failure-decomposition questions and two isolated comparisons (revision 2).

Revision 2 (review of 8e3eb5b): the frame_since_step question states that "stayed_same" compares final
returned frames only, so it is not read as the absence of intermediate changes.

Informed by the evidence comprehension v1 result (attempt ecv1-4458251e): its questions and answers are
development material now, not an untouched validation set. Every question here is new, asked about fresh
seeded trajectories (`trajectories.py`).

Families decompose the v1 failures into mechanically checkable steps. Targets are the composite families
the next decision rests on; components locate where reading breaks and are reported, never gated.

Tracks and conditions (each candidate differs from the baseline by exactly one registered intervention):
- baseline: the v1 questionnaire system prompt and the live history field, for every family;
- control_candidate (control families only): the baseline prompt plus one sentence telling the model to
  intersect the coordinate rule with legal_actions;
- history_candidate (history families only): the baseline prompt with the history field replaced by the
  normalized, information-equivalent records of `representation.py`.

Keys are computed here from the shown entries and independently in `independent.py` from raw frames and
outcomes; the build fails on any disagreement.
"""
import copy
import hashlib
import json
import random

from research.evidence_comprehension_v1 import probes as V1
from research.evidence_comprehension_v2 import representation as R

VERSION = 'evidence_comprehension_v2_r2'
FROZEN_PATH = __import__('pathlib').Path(__file__).with_name('probes.json')


def load_frozen(path=FROZEN_PATH):
    """(frozen question set, its SHA-256). Runtime code reads the frozen file, never the builder."""
    raw = __import__('pathlib').Path(path).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()
MODEL = V1.MODEL
BASE_PROMPT = V1.SYSTEM_PROMPT  # frozen v1 questionnaire prompt (a test checks it against v1's frozen file)

# The single registered control intervention: inserted after the argument rules, before the effect note.
CONTROL_INSTRUCTION = (
    'To find which available actions take coordinates, intersect the two rules above: an action takes x and y '
    'only if it is ACTION6, and it is available only if its action_id is in legal_actions. When 6 is not in '
    'legal_actions, no available action takes coordinates, even if ACTION6 appears in the history.')
_SPLIT = V1.LIVE_ARGUMENT_RULES + '\n'
CONTROL_PROMPT = BASE_PROMPT.replace(_SPLIT, V1.LIVE_ARGUMENT_RULES + ' ' + CONTROL_INSTRUCTION + '\n', 1)

TRACKS = {
    'control': {'targets': ('legal_coordinate_actions',),
                'components': ('legal_actions', 'action6_legal', 'coordinate_rule')},
    'history': {'targets': ('tried_unchanged', 'outcome_class', 'observed_effect'),
                'components': ('step_action_match', 'dispatch_status', 'any_change', 'final_equals_pre',
                               'frame_since_step', 'qualifying_steps')},
}
FAMILIES = tuple(f for t in TRACKS.values() for f in (*t['components'], *t['targets']))
TRACK_OF = {f: name for name, t in TRACKS.items() for f in (*t['components'], *t['targets'])}
CONDITIONS = {'baseline': None, 'control_candidate': 'control', 'history_candidate': 'history'}
PARTITIONS = ('withheld', 'development', 'transfer')
GATE_PARTITION = 'withheld'
PASSES = {'withheld': 2, 'development': 1, 'transfer': 1}  # repetition policy (fixed before any call)

OUTCOMES = V1.OUTCOMES
OUTCOME_LEGEND = V1.OUTCOME_LEGEND
STATUSES = ('acknowledged', 'dispatch_failed', 'outcome_unknown')


def system_prompt(condition):
    return CONTROL_PROMPT if condition == 'control_candidate' else BASE_PROMPT


def present(observation, condition):
    """The observation a condition shows; only the history candidate changes it."""
    return R.candidate_observation(observation) if condition == 'history_candidate' else copy.deepcopy(observation)


# ------------------------------------------------------------------ answer schemas

def _enum(*values):
    return {'type': 'string', 'enum': list(values)}


ANSWER_SCHEMAS = {
    'legal_actions': V1.ID_LIST,
    'action6_legal': _enum('yes', 'no'),
    'coordinate_rule': V1.ID_LIST,
    'legal_coordinate_actions': V1.ID_LIST,
    'step_action_match': _enum('yes', 'no', 'not_shown'),
    'dispatch_status': _enum(*STATUSES, 'not_shown'),
    'any_change': _enum('yes', 'no', 'not_observed', 'not_shown'),
    'final_equals_pre': _enum('yes', 'no', 'not_observed', 'not_shown'),
    'frame_since_step': _enum('stayed_same', 'changed_at_least_once', 'cannot_tell', 'not_shown'),
    'qualifying_steps': {'type': 'array', 'items': {'type': 'integer', 'minimum': 0, 'maximum': 63}, 'maxItems': 8},
    'tried_unchanged': V1.ANSWER_SCHEMAS['tried_unchanged'],
    'outcome_class': V1.ANSWER_SCHEMAS['outcome_class'],
    'observed_effect': V1.ANSWER_SCHEMAS['observed_effect'],
}
# At least the longest schema-valid answer, pretty-printed, under the pinned tokenizer (checked by the audit).
MAX_TOKENS = {'legal_actions': 64, 'action6_legal': 16, 'coordinate_rule': 64, 'legal_coordinate_actions': 64,
              'step_action_match': 16, 'dispatch_status': 16, 'any_change': 16, 'final_equals_pre': 16,
              'frame_since_step': 16, 'qualifying_steps': 64, 'tried_unchanged': 320, 'outcome_class': 32,
              'observed_effect': 32}
SET_FAMILIES = ('legal_actions', 'coordinate_rule', 'legal_coordinate_actions', 'qualifying_steps')


def response_schema(family):
    return {'type': 'object', 'properties': {'answer': copy.deepcopy(ANSWER_SCHEMAS[family])},
            'required': ['answer'], 'additionalProperties': False}


def response_format(family):
    return {'type': 'json_schema', 'json_schema': {'name': f'{VERSION}_{family}', 'strict': True,
                                                   'schema': response_schema(family)}}


# ------------------------------------------------------------------ questions (identical across conditions)

action_text = V1.action_text
QUALIFY_RULE = ('An entry qualifies if it was acknowledged, its final returned frame did not differ from the frame '
                'before it, and no later shown entry had a final returned frame that differed or had an unknown '
                'outcome. A dispatch that failed was not delivered and never qualifies.')


def question_text(family, arg=None):
    if family == 'legal_actions':
        return V1.question_text('available_actions')
    if family == 'action6_legal':
        return 'Is action_id 6 in legal_actions? Answer "yes" or "no".'
    if family == 'coordinate_rule':
        return ('According to the control rules, which action_ids require x and y coordinates in action_data, whether '
                'or not they are in legal_actions now? Answer with the list of every such action_id, or an empty list.')
    if family == 'legal_coordinate_actions':
        return V1.question_text('coordinate_actions')
    if family == 'step_action_match':
        return (f'According to action_effect_history, was the action dispatched at step {arg["step"]} exactly '
                f'{action_text(arg["action"])} (same action_id and same action_data)? Answer "yes", "no", or '
                f'"not_shown" if no entry with step {arg["step"]} is shown.')
    if family == 'dispatch_status':
        return (f'According to action_effect_history, was the action dispatched at step {arg} acknowledged by the '
                'game ("acknowledged"), not delivered ("dispatch_failed"), or possibly delivered with its result not '
                f'observed ("outcome_unknown")? Answer "not_shown" if no entry with step {arg} is shown.')
    if family == 'any_change':
        return (f'According to action_effect_history, for the action dispatched at step {arg}, did any returned '
                'frame differ from the frame before that action? Answer "yes" or "no"; "not_observed" if no frame '
                f'was returned because the dispatch failed or its outcome is unknown; "not_shown" if no entry with '
                f'step {arg} is shown.')
    if family == 'final_equals_pre':
        return (f'According to action_effect_history, for the action dispatched at step {arg}, was the final '
                'returned frame the same as the frame before that action? Answer "yes" or "no"; "not_observed" if '
                'no frame was returned because the dispatch failed or its outcome is unknown; "not_shown" if no '
                f'entry with step {arg} is shown.')
    if family == 'frame_since_step':
        return (f'According to action_effect_history, has the frame stayed the same since step {arg} started? '
                f'Consider the entry at step {arg} and every later shown entry. Answer "changed_at_least_once" if any '
                'of them was acknowledged with a final returned frame that differs from the frame before it; '
                'otherwise "cannot_tell" if any of them had an unknown outcome; otherwise "stayed_same". '
                '"stayed_same" compares final returned frames only: an intermediate returned frame may still have '
                f'differed. Answer "not_shown" if no entry with step {arg} is shown.')
    if family == 'qualifying_steps':
        return ('Using only the entries shown in action_effect_history, list the step of every entry whose action was '
                'dispatched on the frame that is still current and left it unchanged. ' + QUALIFY_RULE +
                ' Answer with a list of step numbers, or an empty list.')
    if family == 'tried_unchanged':
        return V1.question_text('tried_unchanged')
    if family == 'outcome_class':
        return V1.question_text('outcome_class', arg)
    if family == 'observed_effect':
        return V1.question_text('observed_effect', arg)
    raise ValueError(family)


def build_request(context, probe):
    user = {'observation': context['observation'], 'question': probe['question']}
    return {'model': MODEL, 'messages': [
        {'role': 'system', 'content': system_prompt(probe['condition'])},
        {'role': 'user', 'content': json.dumps(user, sort_keys=True, separators=(',', ':'))}],
        'temperature': 0, 'seed': 0, 'max_tokens': MAX_TOKENS[probe['family']],
        'chat_template_kwargs': {'enable_thinking': False}, 'response_format': response_format(probe['family'])}


# ------------------------------------------------------------------ primary keys (from shown baseline entries)

outcome_class = V1.outcome_class
action_of = V1.action_of


def _entry(entries, step):
    match = [e for e in entries if e['step'] == step]
    return match[0] if match else None


def qualifying(entries):
    found = []
    for entry in reversed(entries):
        kind = outcome_class(entry)
        if kind == 'dispatch_failed':
            continue
        if kind in ('final_frame_changed', 'outcome_unknown'):
            break
        found.append(entry)
    return list(reversed(found))


def primary_key(observation, family, arg=None):
    """Keys from the baseline history field (the candidate is checked to carry the same entries)."""
    legal = sorted(observation['legal_actions'])
    entries = observation['action_effect_history']['entries']
    if family == 'legal_actions':
        return legal
    if family == 'action6_legal':
        return 'yes' if 6 in legal else 'no'
    if family == 'coordinate_rule':
        return [6]
    if family == 'legal_coordinate_actions':
        return [6] if 6 in legal else []
    if family == 'step_action_match':
        entry = _entry(entries, arg['step'])
        return 'not_shown' if entry is None else 'yes' if action_of(entry) == arg['action'] else 'no'
    if family in ('dispatch_status', 'any_change', 'final_equals_pre', 'frame_since_step', 'outcome_class'):
        entry = _entry(entries, arg)
        if entry is None:
            return 'not_shown'
        if family == 'dispatch_status':
            return entry['status']
        if family == 'outcome_class':
            return outcome_class(entry)
        if family == 'frame_since_step':
            later = [e for e in entries if e['step'] >= arg]
            if any(e['status'] == 'acknowledged' and e['final_frame_changed'] for e in later):
                return 'changed_at_least_once'
            return 'cannot_tell' if any(e['status'] == 'outcome_unknown' for e in later) else 'stayed_same'
        if entry['status'] != 'acknowledged':
            return 'not_observed'
        if family == 'any_change':
            return 'yes' if any(c is None or c > 0 for c in entry['changed_cells_by_frame']) else 'no'
        return 'no' if entry['final_frame_changed'] else 'yes'
    if family == 'qualifying_steps':
        return [e['step'] for e in qualifying(entries)]
    if family == 'tried_unchanged':
        return V1.primary_key(observation, 'tried_unchanged')
    if family == 'observed_effect':
        return V1.primary_key(observation, 'observed_effect', arg)
    raise ValueError(family)


# ------------------------------------------------------------------ predeclared shortcuts (before any answers)

def _latest(entries):
    return entries[-1] if entries else None


def shortcut_answers(family, arg, observation):
    """Answers a model could give without reading the evidence correctly, including the v1 error patterns
    (`always_six`, transient read as no change). Fixed before any model answers exist."""
    entries = observation['action_effect_history']['entries']
    legal = sorted(observation['legal_actions'])
    ids_in_history = sorted({e['action_id'] for e in entries})
    six_in_history = 6 in ids_in_history
    if family == 'legal_actions':
        return {'all_seven': [1, 2, 3, 4, 5, 6, 7], 'ids_in_history': ids_in_history or [1]}
    if family == 'action6_legal':
        return {'always_yes': 'yes', 'always_no': 'no', 'six_in_history': 'yes' if six_in_history else 'no'}
    if family == 'coordinate_rule':
        return {'always_six': [6], 'legal_intersection': [6] if 6 in legal else []}
    if family == 'legal_coordinate_actions':
        return {'always_six': [6], 'always_empty': [], 'six_if_in_history': [6] if six_in_history else []}
    if family == 'step_action_match':
        entry = _entry(entries, arg['step'])
        loose = 'not_shown' if entry is None else 'yes' if entry['action_id'] == arg['action']['action_id'] else 'no'
        return {'always_yes': 'yes', 'always_no': 'no', 'ignore_coordinates': loose}
    if family in ('dispatch_status', 'any_change', 'final_equals_pre', 'frame_since_step', 'outcome_class'):
        entry = _entry(entries, arg)
        latest = _latest(entries)
        if family == 'dispatch_status':
            return {'always_acknowledged': 'acknowledged',
                    'latest_entry_status': latest['status'] if latest else 'not_shown'}
        if family == 'outcome_class':
            kind = outcome_class(entry) if entry else 'not_shown'
            return {'latest_entry_outcome': outcome_class(latest) if latest else 'not_shown',
                    'always_no_change': 'acknowledged_no_change',
                    'transient_as_no_change': 'acknowledged_no_change' if kind == 'changed_then_returned' else kind}
        if family == 'any_change':
            final_only = ('not_shown' if entry is None else 'not_observed' if entry['status'] != 'acknowledged'
                          else 'yes' if entry['final_frame_changed'] else 'no')
            return {'always_no': 'no', 'final_frame_only': final_only,
                    'null_as_no_change': 'no' if entry is not None and entry['status'] != 'acknowledged'
                    else primary_key(observation, family, arg)}
        if family == 'final_equals_pre':
            return {'always_yes': 'yes', 'null_as_no_change': 'yes' if entry is not None and
                    entry['status'] != 'acknowledged' else primary_key(observation, family, arg)}
        if family == 'frame_since_step':
            own = ('not_shown' if entry is None else 'changed_at_least_once' if entry['status'] == 'acknowledged'
                   and entry['final_frame_changed'] else 'cannot_tell' if entry['status'] == 'outcome_unknown'
                   else 'stayed_same')
            ignore_unknown = primary_key(observation, family, arg)
            return {'always_stayed_same': 'stayed_same', 'only_that_entry': own,
                    'unknown_as_unchanged': 'stayed_same' if ignore_unknown == 'cannot_tell' else ignore_unknown}
    if family in ('qualifying_steps', 'tried_unchanged'):
        every = [e for e in entries if outcome_class(e) in ('acknowledged_no_change', 'changed_then_returned')]
        strict = [e for e in qualifying(entries) if outcome_class(e) == 'acknowledged_no_change']
        with_failed = [e for e in entries if outcome_class(e) in ('acknowledged_no_change', 'changed_then_returned',
                                                                   'dispatch_failed')]
        if family == 'qualifying_steps':
            return {'empty': [], 'every_unchanged_entry': [e['step'] for e in every],
                    'transient_excluded': [e['step'] for e in strict],
                    'failed_included': [e['step'] for e in with_failed]}
        unique = lambda rows: [a for i, a in enumerate(map(action_of, rows)) if a not in list(map(action_of, rows))[:i]]
        return {'empty': [], 'every_unchanged_entry': unique(every), 'transient_excluded': unique(strict),
                'failed_included': unique(with_failed)}
    if family == 'observed_effect':
        base = V1.shortcut_answers('observed_effect', arg, observation)
        key = primary_key(observation, family, arg)
        return {**base, 'transient_as_no_change': 'acknowledged_no_change' if key == 'changed_then_returned' else key}
    raise ValueError(family)


def same_answer(family, a, b):
    if family in SET_FAMILIES:
        return set(a) == set(b)
    if family == 'tried_unchanged':
        return {json.dumps(x, sort_keys=True) for x in a} == {json.dumps(x, sort_keys=True) for x in b}
    return a == b


# ------------------------------------------------------------------ balanced question selection

def _absent_step(observation, all_steps):
    """Steps not shown (before a reset or level boundary, or omitted) and the next step not yet taken."""
    shown = [e['step'] for e in observation['action_effect_history']['entries']]
    hidden = [s for s in all_steps if s not in shown]
    return hidden, max(all_steps) + 1 if all_steps else 0


class Balancer:
    """Chooses question arguments so that no key label and no predeclared shortcut dominates a family: among a
    context's candidate arguments, the one minimising (uses of its key label so far) + (uses so far of the most
    used shortcut that would answer it correctly), ties broken by the seeded generator. Uses only keys and
    shortcuts, never model answers. Deterministic for a given partition order."""

    def __init__(self):
        self.counts = {}

    @staticmethod
    def label(family, key):
        if isinstance(key, str):
            return key
        return 'empty' if key == [] else 'non_empty'

    def _signature(self, family, observation, arg):
        key = primary_key(observation, family, arg)
        right = [name for name, v in shortcut_answers(family, arg, observation).items() if same_answer(family, v, key)]
        return ('label', self.label(family, key)), [('shortcut', name) for name in right]

    def choose(self, rng, family, observation, candidates):
        scored = []
        for n, c in enumerate(candidates):
            label, shortcuts = self._signature(family, observation, c)
            cost = self.counts.get((family, label), 0) + max((self.counts.get((family, s), 0) for s in shortcuts), default=0)
            scored.append((cost, rng.random(), n))
        chosen = candidates[min(scored)[2]]
        label, shortcuts = self._signature(family, observation, chosen)
        for item in (label, *shortcuts):
            self.counts[(family, item)] = self.counts.get((family, item), 0) + 1
        return chosen


def _neighbour(rng, action):
    data = action['action_data']
    axis = rng.choice(('x', 'y'))
    delta = rng.choice((-1, 1)) if 0 < data[axis] < 63 else (1 if data[axis] == 0 else -1)
    return {'action_id': 6, 'action_data': dict(data, **{axis: data[axis] + delta})}


def question_args(observation, all_steps, rng, balancer):
    """Arguments for one context: one question per control family and a fixed set per history family."""
    entries = observation['action_effect_history']['entries']
    hidden, beyond = _absent_step(observation, all_steps)
    steps = [e['step'] for e in entries]
    step_choices = steps + [rng.choice(hidden) if hidden else beyond]
    args = [('legal_actions', None), ('action6_legal', None), ('coordinate_rule', None),
            ('legal_coordinate_actions', None)]
    # Exact-action matching: the same action, a neighbouring click, the same id with other data, another id.
    variants = []
    for entry in entries:
        action = action_of(entry)
        variants.append({'step': entry['step'], 'action': action})
        if action['action_id'] == 6:
            variants.append({'step': entry['step'], 'action': _neighbour(rng, action)})
        else:
            other = [i for i in (1, 2, 3, 4, 5, 7) if i != action['action_id']]
            variants.append({'step': entry['step'], 'action': {'action_id': rng.choice(other), 'action_data': {}}})
    absent_step = step_choices[-1]
    variants.append({'step': absent_step, 'action': action_of(entries[0]) if entries else
                     {'action_id': 6, 'action_data': {'x': rng.randrange(64), 'y': rng.randrange(64)}}})
    for _ in range(2):
        args.append(('step_action_match', balancer.choose(rng, 'step_action_match', observation, variants)))
    for family in ('dispatch_status', 'any_change', 'final_equals_pre', 'frame_since_step'):
        args.append((family, balancer.choose(rng, family, observation, step_choices)))
    for _ in range(2):
        args.append(('outcome_class', balancer.choose(rng, 'outcome_class', observation, step_choices)))
    args += [('qualifying_steps', None), ('tried_unchanged', None)]
    tried = [action_of(e) for e in entries]
    effects = [copy.deepcopy(a) for a in tried]
    effects += [_neighbour(rng, a) for a in tried if a['action_id'] == 6]
    untried = [{'action_id': i, 'action_data': {}} for i in sorted(observation['legal_actions'])
               if i != 6 and {'action_id': i, 'action_data': {}} not in tried]
    effects += untried[:1] or [{'action_id': 6, 'action_data': {'x': rng.randrange(64), 'y': rng.randrange(64)}}]
    for _ in range(2):
        args.append(('observed_effect', balancer.choose(rng, 'observed_effect', observation, effects)))
    unique = []
    for arg in args:  # the same question twice in one context would count one request twice
        if arg not in unique:
            unique.append(arg)
    return unique


# ------------------------------------------------------------------ strata and probes

def strata(observation, family, arg, key, template):
    tags = [f'template:{template}']
    entries = observation['action_effect_history']['entries']
    legal = observation['legal_actions']
    six_in_history = any(e['action_id'] == 6 for e in entries)
    if TRACK_OF[family] == 'control':
        tags.append(('six_legal' if 6 in legal else 'six_not_legal') + ('_six_in_history' if six_in_history else ''))
    if not entries:
        tags.append('empty_history')
    if key in ('not_shown', 'not_observed'):
        tags.append(key)
    if family == 'step_action_match' and key == 'no':
        entry = _entry(entries, arg['step'])
        tags.append('neighbouring_click' if entry['action_id'] == 6 == arg['action']['action_id'] else 'different_action')
    if family == 'observed_effect' and key == 'not_observed' and arg['action_id'] == 6:
        tags.append('neighbouring_click')
    if isinstance(arg, int):
        entry = _entry(entries, arg)
        if entry is not None:
            tags.append(f'entry:{outcome_class(entry)}')
    return tags


def make_probes(partition, context_id, condition, observation, args, template):
    probes = []
    for n, (family, arg) in enumerate(args):
        track = TRACK_OF[family]
        if CONDITIONS[condition] not in (None, track):
            continue
        key = primary_key(observation, family, arg)
        shortcuts = shortcut_answers(family, arg, observation)
        probes.append({'probe_id': f'{partition}:{condition}:{context_id}-{n:02d}',
                       'pair_id': f'{partition}:{context_id}-{n:02d}', 'context_id': f'{partition}:{condition}:{context_id}',
                       'source_context': context_id, 'partition': partition, 'condition': condition, 'track': track,
                       'role': 'target' if family in TRACKS[track]['targets'] else 'component',
                       'family': family, 'arg': arg, 'question': question_text(family, arg), 'key': key,
                       'strata': strata(observation, family, arg, key, template),
                       'shortcuts_correct': sorted(k for k, v in shortcuts.items() if same_answer(family, v, key))})
    return probes


def rng_for(context_id):
    return random.Random(hashlib.sha256(f'{VERSION}:{context_id}'.encode()).hexdigest())
