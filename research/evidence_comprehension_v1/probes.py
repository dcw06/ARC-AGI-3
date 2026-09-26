"""Frozen comprehension probes with mechanically verifiable answers (construction and primary keys).

Each probe pairs one observation context with one question. Contexts use the exact observation
format and history field the live history arm received. Primary keys are computed here from the
entries shown to the model; `independent.py` recomputes every key from raw frames and outcomes
without this module or the record code, and the two must agree.

Nothing here recommends an action. The questions ask what the observation says, not what to do.
"""
import copy
import hashlib
import json
import random

from research.action_effect_history_v1.contract import SYSTEM_PROMPT as LIVE_PROMPT, history_field
from research.action_effect_v1.records import EffectHistory, effect_record

VERSION = 'evidence_comprehension_v1'
MODEL = 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8'
MAX_TOKENS = 192

# The live control text, verbatim: everything after the live prompt's first line (which is about
# choosing an action). The model is told the same things about its controls as in the live run.
CONTROL_TEXT = LIVE_PROMPT.split('\n', 1)[1]
SYSTEM_PROMPT = (
    "You are reviewing one ARC-AGI-3 game observation. Answer the question about it using only the "
    "supplied observation. Return only one compact JSON object matching the supplied answer schema, "
    "with no rationale or Markdown.\n" + CONTROL_TEXT)

OUTCOMES = ('final_frame_changed', 'changed_then_returned', 'acknowledged_no_change',
            'dispatch_failed', 'outcome_unknown')
OUTCOME_LEGEND = (
    'final_frame_changed: the action was acknowledged and its final returned frame differs from the frame '
    'before it; changed_then_returned: acknowledged, an earlier returned frame differed but the final returned '
    'frame equals the frame before it; acknowledged_no_change: acknowledged and no returned frame differed; '
    'dispatch_failed: the action was not delivered to the game; outcome_unknown: the action may have been '
    'delivered but its result was not observed.')
FAMILIES = ('available_actions', 'coordinate_actions', 'recall_action', 'outcome_class', 'observed_effect',
            'tried_unchanged')

# Synthetic outcome templates: fixture cases whose records are built by the real record code.
TEMPLATES = {'acknowledged_no_change': ('identical_frames',),
             'final_frame_changed': ('movement', 'disappearance', 'colour_only'),
             'changed_then_returned': ('intermediate_return',),
             'dimension_change': ('dimension_change',),
             'dispatch_failed': ('dispatch_failed',),
             'outcome_unknown': ('outcome_unknown',)}
LEGAL_SETS = ([1, 2, 3, 4, 5, 6, 7], [1, 2, 3, 4, 5], [6], [1, 3, 5, 7], [1, 2, 3, 4, 6], [1, 2, 3, 4],
              [6, 7], [5, 7], [2, 4, 5, 6], [1, 2, 3, 4, 5, 7])  # half include ACTION6

ACTION_SCHEMA = {'type': 'object', 'properties': {
    'action_id': {'type': 'integer', 'minimum': 0, 'maximum': 7},
    'action_data': {'type': 'object', 'properties': {'x': {'type': 'integer', 'minimum': 0, 'maximum': 63},
                                                     'y': {'type': 'integer', 'minimum': 0, 'maximum': 63}},
                    'additionalProperties': False}},
    'required': ['action_id', 'action_data'], 'additionalProperties': False}
ID_LIST = {'type': 'array', 'items': {'type': 'integer', 'minimum': 0, 'maximum': 7}, 'maxItems': 8}
ANSWER_SCHEMAS = {
    'available_actions': ID_LIST,
    'coordinate_actions': ID_LIST,
    'recall_action': {'anyOf': [{'type': 'string', 'enum': ['not_shown']}, ACTION_SCHEMA]},
    'outcome_class': {'type': 'string', 'enum': [*OUTCOMES, 'not_shown']},
    'observed_effect': {'type': 'string', 'enum': [*OUTCOMES, 'not_observed']},
    'tried_unchanged': {'type': 'array', 'items': ACTION_SCHEMA, 'maxItems': 8},
}


def response_format(family):
    schema = {'type': 'object', 'properties': {'answer': copy.deepcopy(ANSWER_SCHEMAS[family])},
              'required': ['answer'], 'additionalProperties': False}
    return {'type': 'json_schema', 'json_schema': {'name': f'{VERSION}_{family}', 'strict': True, 'schema': schema}}


def action_text(action):
    data = action['action_data']
    return (f'ACTION6 with action_data {{"x": {data["x"]}, "y": {data["y"]}}}' if action['action_id'] == 6
            else f'ACTION{action["action_id"]} with empty action_data')


def question_text(family, arg=None):
    if family == 'available_actions':
        return 'Which action_ids can be chosen for the next action? Answer with the list of every such action_id.'
    if family == 'coordinate_actions':
        return ('Among the action_ids that can be chosen for the next action, which require x and y coordinates in '
                'action_data? Answer with the list of every such action_id, or an empty list.')
    if family == 'recall_action':
        if arg == 'latest':
            return ('Which exact action (action_id and action_data) was dispatched most recently according to '
                    'action_effect_history? Answer "not_shown" if the history has no entries.')
        return (f'Which exact action (action_id and action_data) was dispatched at step {arg} according to '
                f'action_effect_history? Answer "not_shown" if no entry with step {arg} is shown.')
    if family == 'outcome_class':
        return (f'According to action_effect_history, what was the outcome of the action dispatched at step {arg}? '
                f'Answer "not_shown" if no entry with step {arg} is shown. Labels: {OUTCOME_LEGEND}')
    if family == 'observed_effect':
        return (f'What does action_effect_history show for the most recent dispatch of exactly {action_text(arg)} '
                '(same action_id and same action_data)? Answer "not_observed" if the history shows no dispatch of '
                f'exactly this action. Labels: {OUTCOME_LEGEND}')
    if family == 'tried_unchanged':
        return ('Using only the entries shown in action_effect_history, list every exact action (action_id and '
                'action_data) that was already dispatched on the frame that is still current and left it unchanged. '
                'An entry counts if it was acknowledged, its final returned frame did not differ from the frame before '
                'it, and no later entry changed the final frame or had an unknown outcome. A dispatch that failed was '
                'not delivered and does not count. Answer with a list of actions, oldest first, each listed once, or '
                'an empty list.')
    raise ValueError(family)


def build_request(context, probe):
    user = {'observation': context['observation'], 'question': probe['question']}
    return {'model': MODEL, 'messages': [{'role': 'system', 'content': SYSTEM_PROMPT},
                                         {'role': 'user', 'content': json.dumps(user, sort_keys=True, separators=(',', ':'))}],
            'temperature': 0, 'seed': 0, 'max_tokens': MAX_TOKENS,
            'chat_template_kwargs': {'enable_thinking': False}, 'response_format': response_format(probe['family'])}


# ------------------------------------------------------------------ primary keys (from shown entries)

def outcome_class(entry):
    if entry['status'] == 'dispatch_failed':
        return 'dispatch_failed'
    if entry['status'] == 'outcome_unknown':
        return 'outcome_unknown'
    if entry['final_frame_changed']:
        return 'final_frame_changed'
    if any(c is None or c > 0 for c in entry['changed_cells_by_frame']):
        return 'changed_then_returned'
    return 'acknowledged_no_change'


def action_of(entry):
    return {'action_id': entry['action_id'], 'action_data': dict(entry['action_data'])}


def primary_key(observation, family, arg=None):
    legal = sorted(observation['legal_actions'])
    entries = observation['action_effect_history']['entries']
    if family == 'available_actions':
        return legal
    if family == 'coordinate_actions':
        return [6] if 6 in legal else []
    if family in ('recall_action', 'outcome_class'):
        match = entries[-1:] if arg == 'latest' else [e for e in entries if e['step'] == arg]
        if not match:
            return 'not_shown'
        return action_of(match[0]) if family == 'recall_action' else outcome_class(match[0])
    if family == 'observed_effect':
        match = [e for e in entries if action_of(e) == arg]
        return outcome_class(match[-1]) if match else 'not_observed'
    if family == 'tried_unchanged':
        found = []
        for entry in reversed(entries):
            kind = outcome_class(entry)
            if kind == 'dispatch_failed':
                continue
            if kind in ('final_frame_changed', 'outcome_unknown'):
                break
            if action_of(entry) not in found:
                found.append(action_of(entry))
        return list(reversed(found))
    raise ValueError(family)


# ------------------------------------------------------------------ synthetic contexts

def fixture_cases(fixtures):
    return {case['case_id']: case for case in fixtures['cases']}


def synthetic_history(events, cases):
    history = EffectHistory(limit=64)
    for event in events:
        case = cases[event['template']]
        history.append(effect_record(case['pre'], event['action'], case['outcome']))
    return history


def synthetic_observation(context, cases):
    history = synthetic_history(context['events'], cases)
    last = context['events'][-1]['action']['action_id'] if context['events'] else None
    return {'legal_actions': list(context['legal_actions']), 'levels_completed': 0, 'win_levels': 8,
            'state': 'NOT_FINISHED', 'recent_actions': [] if last is None else [last],
            'action_effect_history': history_field(history)}


def generate_events(rng, legal, length):
    """Seeded synthetic action sequence with exact repeats, near-miss clicks and non-legal history ids."""
    weights = {'acknowledged_no_change': 4, 'final_frame_changed': 2, 'changed_then_returned': 2,
               'dispatch_failed': 2, 'outcome_unknown': 2}
    kinds = [k for k in TEMPLATES for _ in range(weights.get(k, 1))]
    events = []
    for _ in range(length):
        roll = rng.random()
        if events and roll < 0.25:
            action = copy.deepcopy(rng.choice(events)['action'])  # exact repeat
        elif events and roll < 0.40 and any(e['action']['action_id'] == 6 for e in events):
            base = rng.choice([e for e in events if e['action']['action_id'] == 6])['action']['action_data']
            action = {'action_id': 6, 'action_data': {'x': min(63, base['x'] + rng.choice((-1, 1))) if base['x'] else 1,
                                                      'y': base['y']}}  # near-miss click
        else:
            pool = legal if roll < 0.9 else [i for i in range(1, 8) if i not in legal] or legal
            ident = rng.choice(pool)
            action = {'action_id': ident,
                      'action_data': {'x': rng.randrange(64), 'y': rng.randrange(64)} if ident == 6 else {}}
        events.append({'action': action, 'template': rng.choice(TEMPLATES[rng.choice(kinds)])})
    return events


def _click(x, y):
    return {'action_id': 6, 'action_data': {'x': x, 'y': y}}


def _simple(ident):
    return {'action_id': ident, 'action_data': {}}


# Hand-designed contexts, one targeted distinction each; every shown step is asked about.
DESIGNED = (
    ('same click: no change, then failed, then another click', [6],
     [(_click(20, 12), 'identical_frames'), (_click(20, 12), 'dispatch_failed'), (_click(33, 40), 'identical_frames')]),
    ('failed and unknown dispatches around acknowledged no-change', [1, 2, 3, 4, 5],
     [(_simple(2), 'dispatch_failed'), (_simple(2), 'identical_frames'), (_simple(3), 'outcome_unknown'),
      (_simple(4), 'identical_frames')]),
    ('final change, transient change, no change, failed click', [1, 2, 3, 4, 5, 6, 7],
     [(_simple(1), 'movement'), (_simple(2), 'intermediate_return'), (_simple(3), 'identical_frames'),
      (_click(8, 50), 'dispatch_failed')]),
    ('dimension change, then no change, then unknown', [5, 7],
     [(_simple(5), 'dimension_change'), (_simple(5), 'identical_frames'), (_simple(7), 'outcome_unknown')]),
    ('near-miss clicks around one that changed the frame', [6, 7],
     [(_click(10, 10), 'identical_frames'), (_click(11, 10), 'identical_frames'), (_click(10, 11), 'movement'),
      (_click(10, 10), 'identical_frames')]),
    ('only failed or unknown dispatches', [1, 2, 3, 4],
     [(_simple(1), 'dispatch_failed'), (_simple(1), 'dispatch_failed'), (_simple(2), 'outcome_unknown')]),
    ('repeated transient changes, then failed and no change', [2, 3, 4, 7],
     [(_simple(7), 'intermediate_return'), (_simple(7), 'intermediate_return'), (_simple(3), 'dispatch_failed'),
      (_simple(3), 'identical_frames')]),
    ('unknown, no change, failed, then final change; older entries omitted', [1, 2, 3, 4, 6],
     [(_click(5, 5), 'identical_frames'), (_simple(4), 'outcome_unknown'), (_simple(4), 'identical_frames'),
      (_simple(1), 'dispatch_failed'), (_simple(4), 'colour_only'), (_simple(2), 'identical_frames')]),
)


def synthetic_contexts(count=36, seed='evidence-comprehension-v1'):
    rng = random.Random(hashlib.sha256(seed.encode()).hexdigest())
    lengths = [0, 1, 2, 3, 4, 5, 6, 7, 2, 3, 4, 5]
    generated = [{'context_id': f'syn-{i:02d}', 'source': 'synthetic', 'grids': False,
                  'legal_actions': LEGAL_SETS[i % len(LEGAL_SETS)],
                  'events': generate_events(rng, LEGAL_SETS[i % len(LEGAL_SETS)], lengths[i % len(lengths)])}
                 for i in range(count)]
    designed = [{'context_id': f'des-{i:02d}', 'source': 'synthetic_designed', 'grids': False, 'design': why,
                 'legal_actions': legal, 'events': [{'action': a, 'template': t} for a, t in events]}
                for i, (why, legal, events) in enumerate(DESIGNED)]
    return generated + designed


# ------------------------------------------------------------------ probe selection

def probe_args(observation, rng, exhaustive=False):
    """Question arguments for one context, chosen to cover shown, omitted and absent steps and actions."""
    entries = observation['action_effect_history']['entries']
    omitted = observation['action_effect_history']['omitted_entries']
    steps = [e['step'] for e in entries]
    args = [('available_actions', None), ('coordinate_actions', None), ('recall_action', 'latest')]
    earlier = steps[:-1] or steps  # prefer a step other than the latest, so 'latest' is not a shortcut
    if steps:
        args.append(('recall_action', rng.choice(earlier)))
        chosen = steps if exhaustive else [rng.choice(earlier), rng.choice(steps)]
        args.extend(('outcome_class', step) for step in chosen)
    absent = rng.randrange(omitted) if omitted else (max(steps) + 1 if steps else 0)
    args.append(('recall_action' if rng.random() < 0.5 else 'outcome_class', absent))
    tried = [action_of(e) for e in entries]
    if tried:
        repeated = [a for a in tried if tried.count(a) > 1]  # most recent of several dispatches
        args.append(('observed_effect', rng.choice(repeated or tried)))
    clicks = [a for a in tried if a['action_id'] == 6]
    for axis in (('x', 'y') if clicks else ()):
        base = rng.choice(clicks)['action_data']
        moved = dict(base, **{axis: base[axis] + 1 if base[axis] < 63 else base[axis] - 1})
        args.append(('observed_effect', {'action_id': 6, 'action_data': moved}))  # near-miss click
    untried = [i for i in sorted(observation['legal_actions']) if i != 6 and {'action_id': i, 'action_data': {}} not in tried]
    if untried:
        args.append(('observed_effect', {'action_id': rng.choice(untried), 'action_data': {}}))
    args.append(('tried_unchanged', None))  # the question restricts it to the entries shown
    return args


def strata(observation, family, arg, key):
    tags = []
    entries = observation['action_effect_history']['entries']
    legal = observation['legal_actions']
    if family in ('available_actions', 'coordinate_actions') and any(e['action_id'] not in legal for e in entries):
        tags.append('history_has_unavailable_ids')
    if family in ('recall_action', 'outcome_class') and key == 'not_shown':
        tags.append('absent_step')
    if family == 'observed_effect' and key == 'not_observed':
        tags.append('near_miss_click' if arg['action_id'] == 6 else 'untried_action')
    if family in ('outcome_class', 'observed_effect'):
        match = ([e for e in entries if e['step'] == arg] if family == 'outcome_class'
                 else [e for e in entries if action_of(e) == arg][-1:])
        if match and match[0]['status'] == 'acknowledged' and None in match[0]['changed_cells_by_frame']:
            tags.append('dimension_change')
    if not entries:
        tags.append('empty_history')
    return tags


def make_probes(context, observation, rng):
    probes = []
    for n, (family, arg) in enumerate(probe_args(observation, rng, context.get('source') == 'synthetic_designed')):
        key = primary_key(observation, family, arg)
        probes.append({'probe_id': f'{context["context_id"]}-{n:02d}', 'context_id': context['context_id'],
                       'family': family, 'arg': arg, 'question': question_text(family, arg), 'key': key,
                       'strata': strata(observation, family, arg, key),
                       'condition': 'full_observation' if context['grids'] else 'evidence_only'})
    return probes
