"""Frozen comprehension probes with mechanically verifiable answers (revision 2).

Each probe pairs one observation context with one retrospective question. Primary keys are computed
here from the entries shown to the model; `independent.py` recomputes every key from raw frames and
outcomes without this module or the record code, and the two must agree.

Revision 2 (review of r1 at 064bb9a):
- the prompt states the controls as facts and never asks for an action choice;
- synthetic histories are continuous trajectories: each acknowledged result's final frame is the
  next action's starting frame (asserted), so "the frame that is still current" is well defined;
- entries whose count is null for a dimension change contradict the live description text; they
  appear only in a separate legacy-description group with a matched corrected-description copy;
- archived live observations are asked the same questions with and without their grids.
"""
import copy
import hashlib
import json
import random

from research.action_effect_history_v1.contract import SYSTEM_PROMPT as LIVE_PROMPT, history_field
from research.action_effect_v1.records import EffectHistory, effect_record

VERSION = 'evidence_comprehension_v1_r2'
MODEL = 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8'
# Per-family completion caps: at least the longest schema-valid answer even when pretty-printed, measured with
# the pinned tokenizer (ids 41, recall 41, labels 13, eight actions 297 tokens), so no valid answer is truncated.
MAX_TOKENS = {'available_actions': 64, 'coordinate_actions': 64, 'recall_action': 64, 'outcome_class': 32,
              'observed_effect': 32, 'tried_unchanged': 320}


def _live_sentence(start, end):
    """A verbatim span of the live prompt (so the factual control rules are exactly what the policy saw)."""
    i = LIVE_PROMPT.index(start)
    j = LIVE_PROMPT.index(end, i) + len(end)
    return LIVE_PROMPT[i:j]


LIVE_ARGUMENT_RULES = _live_sentence('ACTION6 is the only action that takes arguments', 'takes empty action_data {}.')
LIVE_EFFECT_NOTE = _live_sentence('An action being legal does not mean its effect is known', 'omitted from this prompt.')
LIVE_CHOICE_IMPERATIVE = 'choose exactly one action_id from legal_actions'  # removed: this is not a policy decision
SYSTEM_PROMPT = (
    "This is a retrospective questionnaire about one ARC-AGI-3 game observation. It is not a policy decision: "
    "do not choose or take an action. Answer the question using only the supplied observation. Return only one "
    "compact JSON object matching the supplied answer schema, with no rationale or Markdown.\n"
    "Controls: legal_actions lists the action_ids that may be chosen for the next action; reset (action 0) is "
    "never one of them. " + LIVE_ARGUMENT_RULES + "\n" + LIVE_EFFECT_NOTE)

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
CORRECTED_FIELDS_TEXT = (
    'changed_cells_by_frame counts cells that differ from the frame before that action; a count is null when that '
    'returned frame has different dimensions from the frame before it (so it differs); the whole field is null when '
    'the dispatch failed or its outcome is unknown, not that nothing changed')

# Conditions. Only evidence_only enters the main gate; the others are matched, separately reported groups.
GATE_CONDITION = 'evidence_only'
CONDITIONS = ('evidence_only', 'legacy_description', 'corrected_description', 'archived_with_grids',
              'archived_without_grids')
MATCHED = (('legacy_description', 'corrected_description'), ('archived_with_grids', 'archived_without_grids'))
GRID_FIELDS = ('current_grid', 'previous_grid', 'recent_final_grids')

GENERATED_KINDS = {'no_change': 4, 'final_change': 2, 'transient': 2, 'dispatch_failed': 2, 'outcome_unknown': 2}
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


def response_schema(family):
    return {'type': 'object', 'properties': {'answer': copy.deepcopy(ANSWER_SCHEMAS[family])},
            'required': ['answer'], 'additionalProperties': False}


def response_format(family):
    return {'type': 'json_schema', 'json_schema': {'name': f'{VERSION}_{family}', 'strict': True,
                                                   'schema': response_schema(family)}}


def action_text(action):
    data = action['action_data']
    return (f'ACTION6 with action_data {{"x": {data["x"]}, "y": {data["y"]}}}' if action['action_id'] == 6
            else f'ACTION{action["action_id"]} with empty action_data')


def question_text(family, arg=None):
    if family == 'available_actions':
        return 'Which action_ids may be chosen for the next action? Answer with the list of every such action_id.'
    if family == 'coordinate_actions':
        return ('Among the action_ids that may be chosen for the next action, which require x and y coordinates in '
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
                'not delivered and does not count. Answer with a list of actions, each listed once, or an empty list.')
    raise ValueError(family)


def build_request(context, probe):
    user = {'observation': context['observation'], 'question': probe['question']}
    return {'model': MODEL, 'messages': [{'role': 'system', 'content': SYSTEM_PROMPT},
                                         {'role': 'user', 'content': json.dumps(user, sort_keys=True, separators=(',', ':'))}],
            'temperature': 0, 'seed': 0, 'max_tokens': MAX_TOKENS[probe['family']],
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


# ------------------------------------------------------------------ continuous synthetic trajectories

def encode_frame(grid):
    return f'{len(grid)}x{len(grid[0])}:' + ''.join('0123456789abcdef'[v] for row in grid for v in row)


def decode_frame(text):
    size, cells = text.split(':')
    h, w = map(int, size.split('x'))
    return [[int(cells[y * w + x], 16) for x in range(w)] for y in range(h)]


def mutate(rng, grid):
    """A deterministic local change: one rectangle recoloured (every cell in it differs)."""
    h, w = len(grid), len(grid[0])
    out = [row[:] for row in grid]
    rh, rw = rng.randint(1, 5), rng.randint(1, 6)
    y0, x0 = rng.randrange(h - rh + 1), rng.randrange(w - rw + 1)
    colour = rng.randrange(16)
    for y in range(y0, y0 + rh):
        for x in range(x0, x0 + rw):
            out[y][x] = colour if colour != grid[y][x] else (colour + 1) % 16
    return out


def trajectory(rng, base, steps):
    """Continuous events from (action, kind) steps. Each event records the frame it started from."""
    current, events = base, []
    for action, kind in steps:
        event = {'action': action, 'kind': kind, 'pre': encode_frame(current)}
        if kind == 'no_change':
            event['returned'] = [encode_frame(current)]
        elif kind == 'final_change':
            current = mutate(rng, current)
            event['returned'] = [encode_frame(current)]
        elif kind == 'transient':
            event['returned'] = [encode_frame(mutate(rng, current)), encode_frame(current)]
        elif kind == 'dimension_change':
            current = [row[:-4] for row in current[:-4]]
            event['returned'] = [encode_frame(current)]
        elif kind == 'outcome_unknown':
            # Nothing was observed for this dispatch; the game may or may not have changed by the next frame.
            if rng.random() < 0.5:
                current = mutate(rng, current)
        elif kind != 'dispatch_failed':
            raise ValueError(kind)
        events.append(event)
    return {'events': events, 'final': encode_frame(current)}


def continuity_errors(context):
    """Adjacent-state consistency: each event starts from the frame the previous one left current."""
    errors = []
    events = context['events']
    for i, event in enumerate(events):
        following = events[i + 1]['pre'] if i + 1 < len(events) else context['final']
        if 'returned' in event and event['returned'][-1] != following:
            errors.append(f'{context["context_id"]}: event {i} final frame is not the next starting frame')
        if event['kind'] == 'dispatch_failed' and event['pre'] != following:
            errors.append(f'{context["context_id"]}: failed dispatch {i} changed the frame')
    return errors


def history_of(context):
    history = EffectHistory(limit=64)
    for event in context['events']:
        pre = {'frames': [decode_frame(event['pre'])], 'levels_completed': 0}
        if event['kind'] == 'dispatch_failed':
            outcome = {'status': 'dispatch_failed', 'error': 'request rejected before acknowledgement'}
        elif event['kind'] == 'outcome_unknown':
            outcome = {'status': 'outcome_unknown', 'reason': 'response timeout after send'}
        else:
            outcome = {'status': 'acknowledged', 'post': {'frames': [decode_frame(f) for f in event['returned']],
                                                          'levels_completed': 0, 'full_reset': False,
                                                          'state': 'NOT_FINISHED'}}
        history.append(effect_record(pre, event['action'], outcome))
    return history


def synthetic_observation(context, corrected=False):
    field = history_field(history_of(context))
    if corrected:
        field = {**field, 'fields': CORRECTED_FIELDS_TEXT}
    last = context['events'][-1]['action']['action_id'] if context['events'] else None
    return {'legal_actions': list(context['legal_actions']), 'levels_completed': 0, 'win_levels': 8,
            'state': 'NOT_FINISHED', 'recent_actions': [] if last is None else [last], 'action_effect_history': field}


def without_grids(observation):
    return {k: v for k, v in observation.items() if k not in GRID_FIELDS}


def _click(x, y):
    return {'action_id': 6, 'action_data': {'x': x, 'y': y}}


def _simple(ident):
    return {'action_id': ident, 'action_data': {}}


# Hand-designed contexts, one targeted distinction each; every shown step is asked about.
DESIGNED = (
    ('same click: no change, then failed, then another click', [6],
     [(_click(20, 12), 'no_change'), (_click(20, 12), 'dispatch_failed'), (_click(33, 40), 'no_change')]),
    ('failed and unknown dispatches around acknowledged no-change', [1, 2, 3, 4, 5],
     [(_simple(2), 'dispatch_failed'), (_simple(2), 'no_change'), (_simple(3), 'outcome_unknown'),
      (_simple(4), 'no_change')]),
    ('final change, transient change, no change, failed click', [1, 2, 3, 4, 5, 6, 7],
     [(_simple(1), 'final_change'), (_simple(2), 'transient'), (_simple(3), 'no_change'),
      (_click(8, 50), 'dispatch_failed')]),
    ('near-miss clicks around one that changed the frame', [6, 7],
     [(_click(10, 10), 'no_change'), (_click(11, 10), 'no_change'), (_click(10, 11), 'final_change'),
      (_click(10, 10), 'no_change')]),
    ('only failed or unknown dispatches', [1, 2, 3, 4],
     [(_simple(1), 'dispatch_failed'), (_simple(1), 'dispatch_failed'), (_simple(2), 'outcome_unknown')]),
    ('repeated transient changes, then failed and no change', [2, 3, 4, 7],
     [(_simple(7), 'transient'), (_simple(7), 'transient'), (_simple(3), 'dispatch_failed'), (_simple(3), 'no_change')]),
    ('unknown, no change, failed, then final change; older entries omitted', [1, 2, 3, 4, 6],
     [(_click(5, 5), 'no_change'), (_simple(4), 'outcome_unknown'), (_simple(4), 'no_change'),
      (_simple(1), 'dispatch_failed'), (_simple(4), 'final_change'), (_simple(2), 'no_change')]),
    ('different actions that each changed nothing on the same frame', [1, 2, 3, 4, 5, 6],
     [(_simple(1), 'final_change'), (_simple(2), 'no_change'), (_click(30, 30), 'no_change'),
      (_simple(5), 'no_change')]),
)
# Dimension changes contradict the live description text; they appear only in the legacy/corrected groups.
DESIGNED_DIMENSION = (
    ('dimension change, then no change, then unknown', [5, 7],
     [(_simple(5), 'dimension_change'), (_simple(5), 'no_change'), (_simple(7), 'outcome_unknown')]),
    ('no change, dimension change, then two no-change actions', [1, 2, 3, 4],
     [(_simple(1), 'no_change'), (_simple(2), 'dimension_change'), (_simple(3), 'no_change'), (_simple(1), 'no_change')]),
    ('click no change, dimension change, same click again', [6, 7],
     [(_click(12, 40), 'no_change'), (_simple(7), 'dimension_change'), (_click(12, 40), 'no_change')]),
)


def generated_steps(rng, legal, length):
    """Seeded action/kind steps with exact repeats, near-miss clicks and ids that are not currently legal."""
    kinds = [k for k, weight in GENERATED_KINDS.items() for _ in range(weight)]
    steps = []
    for _ in range(length):
        roll = rng.random()
        clicks = [a for a, _ in steps if a['action_id'] == 6]
        if steps and roll < 0.25:
            action = copy.deepcopy(rng.choice(steps)[0])  # exact repeat
        elif clicks and roll < 0.40:
            base = rng.choice(clicks)['action_data']
            action = _click(base['x'] + 1 if base['x'] < 63 else base['x'] - 1, base['y'])  # near-miss click
        else:
            pool = legal if roll < 0.9 else [i for i in range(1, 8) if i not in legal] or legal
            ident = rng.choice(pool)
            action = _click(rng.randrange(64), rng.randrange(64)) if ident == 6 else _simple(ident)
        steps.append((action, rng.choice(kinds)))
    return steps


def synthetic_contexts(base, count=36, seed='evidence-comprehension-v1-r2'):
    rng = random.Random(hashlib.sha256(seed.encode()).hexdigest())
    lengths = [0, 1, 2, 3, 4, 5, 6, 7, 2, 3, 4, 5]
    contexts = []
    for i in range(count):
        legal = LEGAL_SETS[i % len(LEGAL_SETS)]
        contexts.append({'context_id': f'syn-{i:02d}', 'source': 'synthetic', 'legal_actions': legal,
                         **trajectory(rng, base, generated_steps(rng, legal, lengths[i % len(lengths)]))})
    for prefix, table in (('des', DESIGNED), ('dim', DESIGNED_DIMENSION)):
        for i, (why, legal, steps) in enumerate(table):
            contexts.append({'context_id': f'{prefix}-{i:02d}', 'source': 'synthetic_designed', 'design': why,
                             'legal_actions': legal, **trajectory(rng, base, steps)})
    return contexts


# ------------------------------------------------------------------ probe selection

def probe_args(observation, rng, exhaustive=False):
    """Question arguments for one context, chosen to cover shown, omitted and absent steps and actions."""
    entries = observation['action_effect_history']['entries']
    omitted = observation['action_effect_history']['omitted_entries']
    steps = [e['step'] for e in entries]
    earlier = steps[:-1] or steps  # prefer a step other than the latest, so 'latest' is not a shortcut
    args = [('available_actions', None), ('coordinate_actions', None), ('recall_action', 'latest')]
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
        args.append(('observed_effect', _click(moved['x'], moved['y'])))  # near-miss click
    untried = [i for i in sorted(observation['legal_actions']) if i != 6 and _simple(i) not in tried]
    if untried:
        args.append(('observed_effect', _simple(rng.choice(untried))))
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
    if any(e['status'] == 'acknowledged' and None in e['changed_cells_by_frame'] for e in entries):
        tags.append('dimension_change_in_history')
    if not entries:
        tags.append('empty_history')
    return tags


# ------------------------------------------------------------------ shortcut answers

def shortcut_answers(family, arg, observation):
    """Answers a model could give without reading the evidence correctly (fixed before any model answers)."""
    entries = observation['action_effect_history']['entries']
    if family == 'available_actions':
        return {'all_seven': [1, 2, 3, 4, 5, 6, 7], 'ids_in_history': sorted({e['action_id'] for e in entries} or {1})}
    if family == 'coordinate_actions':
        return {'always_six': [6], 'always_empty': []}
    if family == 'recall_action':
        return {'latest_entry': action_of(entries[-1]) if entries else 'not_shown'}
    if family == 'outcome_class':
        return {'latest_entry_outcome': outcome_class(entries[-1]) if entries else 'not_shown',
                'always_no_change': 'acknowledged_no_change'}
    if family == 'observed_effect':
        same_type = [e for e in entries if e['action_id'] == arg['action_id']]
        return {'always_not_observed': 'not_observed',
                'ignore_coordinates': outcome_class(same_type[-1]) if same_type else 'not_observed'}
    if family == 'tried_unchanged':
        unchanged = []
        for e in entries:
            if outcome_class(e) in ('acknowledged_no_change', 'changed_then_returned') and action_of(e) not in unchanged:
                unchanged.append(action_of(e))
        return {'every_unchanged_entry': unchanged, 'empty': []}
    raise ValueError(family)


def same_answer(family, a, b):
    if family in ('available_actions', 'coordinate_actions'):
        return set(a) == set(b)
    if family == 'tried_unchanged':
        return ({json.dumps(x, sort_keys=True) for x in a} == {json.dumps(x, sort_keys=True) for x in b})
    return a == b


def make_probes(context_id, condition, observation, args, match_group=None):
    probes = []
    for n, (family, arg) in enumerate(args):
        key = primary_key(observation, family, arg)
        shortcuts = shortcut_answers(family, arg, observation)
        probes.append({'probe_id': f'{condition}:{context_id}-{n:02d}', 'context_id': f'{condition}:{context_id}',
                       'source_context': context_id, 'condition': condition, 'family': family, 'arg': arg,
                       'question': question_text(family, arg), 'key': key,
                       'strata': strata(observation, family, arg, key),
                       'shortcuts_correct': sorted(k for k, v in shortcuts.items() if same_answer(family, v, key)),
                       'match_group': match_group})
    return probes
