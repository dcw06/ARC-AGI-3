"""progress_subgoal_v1 question set (DRAFT: not frozen; no model calls).

Question: can a model describe an action's observed effects without confusing visible change with progress, or a
temporal sequence with a cause, and can it verify a stated subgoal mechanically without claiming the subgoal helps?

Three levels are kept apart, and each question family belongs to one:
- observed change (`visual_effect`, `region_changed`): frame comparison only;
- confirmed progress (`progress_status`, `claim_progress`): only an allowed environment signal;
- hypothesized usefulness (`claim_usefulness`): never established by this evidence; a gate-only family;
and two applications of them:
- causal restraint (`claim_causal`, `effect_hypothesis`): repetition strengthens a hypothesis, never a cause;
- subgoal verification (`subgoal_status`, `subgoal_decision`): the record's own success test, invalidation evidence and
  action budget, applied mechanically.

Conditions (one isolated difference per comparison):
- `raw_evidence`: per transition, the dispatched action, dispatch status, the frame before, the returned frames as
  returned, and the environment fields; plus the subgoal record where one was adopted;
- `raw_plus_computed_record`: the same plus, per transition, `computed_measurements` derived from the
  transition_evidence_v1 record (the WS3 treatment, here applied to sequences);
- `raw_plus_computed_record_plus_safeguard`: byte-identical evidence to the previous condition; only the system
  prompt adds a constant, case-independent three-level safeguard (SAFEGUARD).
Primary comparison (protocol v1, the two default arms): safeguard vs computed (does an explicit level rule reduce
over-claims, and at what cost in over-hedging?). Optional, only under the protocol's predeclared WS3-v1 rule:
computed vs raw (with `raw_evidence` as a third arm).

Every key is derived three ways and must agree, or the build fails:
1. contract: transition_evidence_v1 records (transition.history) plus subgoal.py;
2. reference: the import-free reference.py;
3. construction: the per-transition facts each fixture recorded while building it.
A single key policy (`rule`) maps those facts to answers; the facts themselves come from the three sources.
"""
import copy
import hashlib
import itertools
import json
import random

from research.progress_subgoal_v1 import fixtures as F, reference as REF, subgoal as S
from research.transition_evidence_v1 import transition as T, vocabulary as V

VERSION = 'progress_subgoal_v1_questions_draft'
ALL_CONDITIONS = ('raw_evidence', 'raw_plus_computed_record', 'raw_plus_computed_record_plus_safeguard')
# Protocol v1: two primary arms that differ in one thing only (the constant safeguard text in the system prompt;
# the evidence is byte-identical). `raw_evidence` is an optional third arm, added only by the predeclared WS3-v1
# decision rule in reports/progress_subgoal_v1_protocol_v1.md; `build(..., conditions=ALL_CONDITIONS)` supports it.
PRIMARY_CONDITIONS = ('raw_plus_computed_record', 'raw_plus_computed_record_plus_safeguard')
CONDITIONS = PRIMARY_CONDITIONS
COMPARISONS = {'safeguard_vs_computed': ('raw_plus_computed_record', 'raw_plus_computed_record_plus_safeguard'),
               'computed_vs_raw': ('raw_evidence', 'raw_plus_computed_record')}  # the second only with the third arm
DECISION_PARTITION = 'evaluation'
SUPPORT = ['supported', 'contradicted', 'not_established']
ANSWERS = {
    'visual_effect': ['no_observed_change', 'changed_then_returned', 'final_frame_differs', 'indeterminate'],
    'region_changed': ['yes', 'no', 'cannot_tell'],
    'progress_status': ['confirmed', 'unknown'],
    'claim_progress': SUPPORT,
    'claim_usefulness': SUPPORT,
    'claim_causal': SUPPORT,
    'effect_hypothesis': ['strengthened', 'weakened', 'insufficient_evidence'],
    'subgoal_status': ['achieved', 'not_achieved', 'cannot_tell'],
    'subgoal_decision': ['stop_achieved', 'abandon_invalidated', 'abandon_budget_exhausted', 'continue'],
}
FAMILIES = tuple(ANSWERS)
LEVEL = {'visual_effect': 'observed_change', 'region_changed': 'observed_change',
         'progress_status': 'confirmed_progress', 'claim_progress': 'confirmed_progress',
         'claim_usefulness': 'hypothesized_usefulness', 'claim_causal': 'causal_restraint',
         'effect_hypothesis': 'causal_restraint', 'subgoal_status': 'subgoal_verification',
         'subgoal_decision': 'subgoal_verification'}
# claim_usefulness is keyed not_established everywhere, so "always not_established" scores 1.0: accuracy there is
# not diagnostic, and the family is used only through its over-claim gate.
ROLES = {'primary': tuple(f for f in FAMILIES if f != 'claim_usefulness'), 'gate_only': ('claim_usefulness',)}
ROLE_OF = {f: role for role, fams in ROLES.items() for f in fams}
UNCERTAIN = {'visual_effect': 'indeterminate', 'region_changed': 'cannot_tell', 'progress_status': 'unknown',
             'claim_progress': 'not_established', 'claim_usefulness': 'not_established',
             'claim_causal': 'not_established', 'effect_hypothesis': 'insufficient_evidence',
             'subgoal_status': 'cannot_tell'}
TARGET = {'development': 12, 'coverage_dryrun': 120, 'evaluation': 120}
# Larger targets where an over-claim denominator would otherwise fall below its floor.
TARGET_FACTOR = {'progress_status': 1.5, 'claim_progress': 1.5, 'subgoal_status': 1.5}
FLOORS = {'primary_questions': 100, 'shortcut_disagreement': 20, 'critical_class_contexts': 20,
          'over_claim_denominator_contexts': 100, 'abandonment_questions': 20, 'uncertain_keyed_questions': 100}

BASE_PROMPT = (
    "This is a retrospective questionnaire about a short sequence of actions in a grid game. It is not a decision: "
    "do not choose an action. Answer using only the supplied evidence. Return only one compact JSON object matching "
    "the supplied answer schema, with no rationale or Markdown.\n"
    "Evidence: 'transitions' are in order; in each, 'dispatched_action' is the action that was sent, 'frame_before' is "
    "the frame before it, and 'returned_frames' are the frames the game returned after it, in order. A frame is a list "
    "of rows (grid[y][x]; x is the column, y the row); a valid frame is a non-empty rectangle of integers 0 to 15. A "
    "dispatch that failed was not delivered; an outcome that is unknown may have been delivered but its result was not "
    "observed. Environment fields are what the game reported. 'subgoal_record', when present, is a plan statement "
    "written before these transitions.")
SAFEGUARD = (
    "\nKeep three levels separate. (1) Observed change: what differs between frames. (2) Confirmed progress: only a "
    "reported increase in completed levels, or a WIN state; a visible change is not progress, and the absence of a "
    "report does not show that no progress occurred. (3) Usefulness: whether a change or a subgoal helps complete the "
    "level is a hypothesis this evidence cannot establish; achieving a subgoal is neither progress nor proof that it "
    "helps. A change that follows an action may have happened on its own; repeated consistent results strengthen an "
    "effect hypothesis but do not establish a cause or its mechanism. When the evidence cannot decide, give the answer "
    "that says so; when it can, give the definite answer.")
SYSTEM_PROMPTS = {'raw_evidence': BASE_PROMPT, 'raw_plus_computed_record': BASE_PROMPT,
                  'raw_plus_computed_record_plus_safeguard': BASE_PROMPT + SAFEGUARD}

# ------------------------------------------------------------------ wording


def rect_text(xywh):
    x, y, w, h = xywh
    return f'the rectangle of cells with x from {x} to {x + w - 1} and y from {y} to {y + h - 1} (inclusive)'


def action_text(action):
    data = action.get('action_data') or {}
    return f"ACTION{action['action_id']}" + (f" with x={data['x']}, y={data['y']}" if data else '')


CLAIM_TEXT = {
    'progress_confirmed': lambda c, a: 'After the last action, the environment confirmed progress (a completed level '
                                       'or a win).',
    'no_progress': lambda c, a: 'The last action made no progress toward completing the level.',
    'region_helps': lambda c, a: f'Changing {rect_text(c["regions"][a[1]])} helps complete the level.',
    'subgoal_helps': lambda c, a: 'Achieving the subgoal in the subgoal record helps complete the level.',
    'caused_region_change': lambda c, a: f'The last action caused cells inside {rect_text(c["regions"][a[1]])} to '
                                         'change.',
    'change_caused_change': lambda c, a: (f'In the last transition, the change inside {rect_text(c["regions"][a[1]])} '
                                          f'caused the change inside {rect_text(c["regions"][a[2]])}.'),
    'mechanism_identified': lambda c, a: (f'The evidence identifies the full mechanism by which '
                                          f'{action_text(c["actions"][a[1]])} changes the cells inside '
                                          f'{rect_text(c["regions"][a[2]])}.'),
}
CLAIM_FAMILY = {'progress_confirmed': 'claim_progress', 'no_progress': 'claim_progress',
                'region_helps': 'claim_usefulness', 'subgoal_helps': 'claim_usefulness',
                'caused_region_change': 'claim_causal', 'change_caused_change': 'claim_causal',
                'mechanism_identified': 'claim_causal'}
REGION_RULE = ('Apply this rectangle rule to a transition: "yes" if some valid returned frame with the same dimensions '
               'as the frame before differs from it inside the rectangle; "no" if frames were returned, every one is '
               'valid with the same dimensions, and none differs inside it; otherwise "cannot_tell".')


def question_text(ctx, family, arg):
    if family in ('claim_progress', 'claim_usefulness', 'claim_causal'):
        return (f'Claim: "{CLAIM_TEXT[arg[0]](ctx, arg)}" Answer "supported" only if the evidence establishes the claim, '
                '"contradicted" if the evidence shows it is false, and otherwise "not_established".')
    if family == 'visual_effect':
        return ('Compare each returned frame of the last transition with its frame before. "no_observed_change": frames '
                'were returned, every one is valid, and none differs; "changed_then_returned": some valid returned frame '
                'differs, and the final returned frame is valid and identical to the frame before; '
                '"final_frame_differs": the final returned frame is valid and differs (including in dimensions); '
                '"indeterminate": otherwise (the dispatch failed, the outcome is unknown, no valid final frame was '
                'returned, or no valid frame differs but some returned frames are invalid).')
    if family == 'region_changed':
        return f'{REGION_RULE} What is the result for the last transition and {rect_text(ctx["regions"][arg[0]])}?'
    if family == 'progress_status':
        return ('Does the evidence confirm progress after the last action: a reported increase in completed levels, or '
                'a win? Answer "confirmed" or "unknown".')
    if family == 'effect_hypothesis':
        return (f'Hypothesis: "{action_text(ctx["actions"][arg[0]])} is followed by a change inside '
                f'{rect_text(ctx["regions"][arg[1]])}." {REGION_RULE} Trials: transitions that dispatched exactly this '
                'action whose result is "yes" or "no". Controls: transitions that dispatched any other action whose '
                'result is "yes" or "no". A change between observations also counts as a control that changed the '
                'rectangle: the earlier transition left an observed frame (its valid final returned frame, or its frame '
                'before if its dispatch failed; never after an unknown outcome) and the next frame before differs from '
                'it inside the rectangle; an unchanged gap is not a control. Answer "weakened" if any trial left the '
                'rectangle unchanged or any control changed it; otherwise "strengthened" if at least two trials '
                'changed it and at least one control transition left it unchanged; otherwise '
                '"insufficient_evidence".')
    if family == 'subgoal_status':
        return ('Apply the subgoal record\'s success test to every frame before and every valid final returned frame '
                '(intermediate returned frames do not count). "achieved" if any of them meets the test; otherwise '
                '"cannot_tell" if some transition\'s outcome is unknown, or it was acknowledged without a valid final '
                'returned frame; otherwise "not_achieved".')
    if family == 'subgoal_decision':
        return ('Apply the subgoal record\'s rules in this order: "stop_achieved" if its success test is met (as for '
                'the success question: frames before and valid final returned frames only); otherwise '
                '"abandon_invalidated" if any of its invalidation conditions is met (an attempt leaves the target '
                'rectangle unchanged only if its rectangle result is "no"); otherwise "abandon_budget_exhausted" if the '
                'number of transitions shown (each dispatched action counts, including failed and unknown ones) is at '
                'least its action budget; otherwise "continue".')
    raise ValueError(family)


def response_schema(family):
    return {'type': 'object', 'properties': {'answer': {'type': 'string', 'enum': list(ANSWERS[family])}},
            'required': ['answer'], 'additionalProperties': False}


# ------------------------------------------------------------------ presentations


def raw_view(ctx):
    steps = []
    for n, raw in enumerate(ctx['raws']):
        outcome = raw['outcome']
        step = {'step': n, 'dispatched_action': copy.deepcopy(raw['dispatched']),
                'dispatch': {'status': outcome['status'], 'reason': outcome.get('reason')},
                'frame_before': copy.deepcopy(raw['before']['frames'][-1]),
                'environment_before': {k: raw['before'].get(k) for k in ('levels_completed', 'state', 'full_reset')}}
        if outcome['status'] == 'acknowledged':
            step['returned_frames'] = copy.deepcopy(outcome['after'].get('frames') or [])
            step['environment_after'] = {k: outcome['after'].get(k) for k in ('levels_completed', 'state', 'full_reset')}
        else:
            step['returned_frames'] = 'none observed'
            step['environment_after'] = 'not observed'
        steps.append(step)
    view = {'transitions': steps}
    if ctx['subgoal'] is not None:
        view['subgoal_record'] = copy.deepcopy(ctx['subgoal'])
    return view


def computed_view(record):
    m = record['measurements']
    frames = [{'index': f['index'], 'valid': f['valid'], **({'reason': f['reason']} if not f['valid'] else {
        'comparability_to_frame_before': f['vs_pre']['comparability'],
        'changed_cells_vs_frame_before': f['vs_pre']['changed_cells'],
        'changed_bbox_xyxy_vs_frame_before': f['vs_pre'].get('changed_bbox_xyxy'),
        'changed_cells_vs_previous_frame': f['vs_previous']['changed_cells']})} for f in m['frames']]
    return {'computed_by': 'deterministic tool from the evidence above, not the model',
            'observation_availability': record['observations']['availability'],
            'returned_frames': frames, 'any_returned_frame_differs': m['any_returned_frame_differs'],
            'final_frame_equals_frame_before': m['final_frame_equals_pre'], 'visual_effect': m['visual_effect'],
            'environment_events': record['environment']['events'],
            'progress': {k: v for k, v in record['progress'].items() if k != 'source'},
            'continuity_with_previous_transition': record['continuity']}


def present(ctx, records, condition):
    view = raw_view(ctx)
    if condition != 'raw_evidence':
        for step, record in zip(view['transitions'], records):
            step['computed_measurements'] = computed_view(record)
    return view


# The reviewed runner stack (WS3 questionnaire v1, from evidence comprehension v1-v3) serves this pinned model with
# thinking disabled; requests use its exact shape so the reviewed service, host and tokenizer admission apply.
MODEL = 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8'
MAX_TOKENS = 32


def make_request(evidence, probe):
    """The request for one question: the arm's system prompt, the context's evidence and the question."""
    user = {'evidence': evidence, 'question': probe['question']}
    return {'model': MODEL,
            'messages': [{'role': 'system', 'content': SYSTEM_PROMPTS[probe['condition']]},
                         {'role': 'user', 'content': json.dumps(user, sort_keys=True, separators=(',', ':'))}],
            'temperature': 0, 'seed': 0, 'max_tokens': MAX_TOKENS, 'chat_template_kwargs': {'enable_thinking': False},
            'response_format': {'type': 'json_schema', 'json_schema': {
                'name': f"{VERSION}_{probe['family']}", 'strict': True, 'schema': response_schema(probe['family'])}}}


def build_request(value, probe):
    return make_request(value['contexts'][probe['context_id']], probe)


# ------------------------------------------------------------------ facts: three independent sources


class ContractFacts:
    """From transition_evidence_v1 records (the contract) and subgoal.py."""

    def __init__(self, ctx):
        self.ctx, self.raws = ctx, ctx['raws']
        self.records = T.history(self.raws)
        self._cache = {}

    def visual(self):
        return self.records[-1]['measurements']['visual_effect']['status']

    def progress(self):
        return self.records[-1]['progress']['status']

    def region(self, name):
        return S.region_status(self.raws[-1], self.records[-1], self.ctx['regions'][name])

    def hypothesis_full(self, action, name):
        if (action, name) not in self._cache:
            self._cache[(action, name)] = S.effect_hypothesis(self.raws, self.records, self.ctx['actions'][action],
                                                              self.ctx['regions'][name])
        return self._cache[(action, name)]

    def hypothesis(self, action, name):
        return self.hypothesis_full(action, name)['status']

    def subgoal_full(self):
        if 'subgoal' not in self._cache:
            self._cache['subgoal'] = S.check(self.ctx['subgoal'], self.raws)
        return self._cache['subgoal']

    def subgoal(self):
        c = self.subgoal_full()
        return c['status'], c['decision']


class ReferenceFacts:
    """From the import-free reference."""

    def __init__(self, ctx):
        self.ctx, self.raws = ctx, ctx['raws']

    def visual(self):
        return REF.visual(self.raws[-1])

    def progress(self):
        return REF.progress(self.raws[-1])

    def region(self, name):
        return REF.region(self.raws[-1], self.ctx['regions'][name])

    def hypothesis(self, action, name):
        return REF.hypothesis(self.raws, self.ctx['actions'][action], self.ctx['regions'][name])

    def subgoal(self):
        return REF.subgoal(self.ctx['subgoal'], self.raws)


class ConstructionFacts:
    """From the facts each fixture recorded while building it. Never reads `unobservable`."""

    def __init__(self, ctx):
        self.ctx, self.facts = ctx, ctx['evaluator_only']['facts']

    def visual(self):
        return self.facts[-1]['visual']

    def progress(self):
        return self.facts[-1]['progress']

    def region(self, name):
        return self.facts[-1]['region'][name]

    def hypothesis(self, action, name):
        action = self.ctx['actions'][action]
        trials, controls, autonomous = [], [], False
        for f in self.facts:
            autonomous |= f['gap'] is not None and f['gap'][name] == 'yes'
            (trials if f['dispatched'] == action else controls).append(f['region'][name])
        if 'no' in trials or 'yes' in controls or autonomous:
            return 'weakened'
        return 'strengthened' if trials.count('yes') >= 2 and 'no' in controls else 'insufficient_evidence'

    def subgoal(self):
        sg = self.ctx['subgoal']
        if any(f['target_met_before'] or f['target_met_final'] for f in self.facts):
            return 'achieved', 'stop_achieved'
        status = 'cannot_tell' if any(f['unobserved_final'] for f in self.facts) else 'not_achieved'
        invalid = False
        for item in sg['invalidation_evidence']:  # fixtures always target R1
            if item['kind'] == 'no_region_change_after_attempts':
                invalid |= sum(f['dispatched'] == item['action'] and f['region']['R1'] == 'no'
                               for f in self.facts) >= item['attempts']
            else:
                invalid |= any(f['state_after'] == item['state'] for f in self.facts)
        if invalid:
            return status, 'abandon_invalidated'
        return status, 'abandon_budget_exhausted' if len(self.facts) >= sg['action_budget'] else 'continue'


def rule(facts, family, arg):
    """The key policy. Usefulness is never established; a cause is at most contradicted by an absent change."""
    if family == 'visual_effect':
        return facts.visual()
    if family == 'region_changed':
        return facts.region(arg[0])
    if family == 'progress_status':
        return facts.progress()
    if family == 'claim_progress':
        confirmed = facts.progress() == V.CONFIRMED
        if arg[0] == 'progress_confirmed':
            return 'supported' if confirmed else 'not_established'
        return 'contradicted' if confirmed else 'not_established'  # no_progress: absence of a report is not evidence
    if family == 'claim_usefulness':
        return 'not_established'
    if family == 'claim_causal':
        if arg[0] == 'caused_region_change':
            return 'contradicted' if facts.region(arg[1]) == 'no' else 'not_established'
        if arg[0] == 'change_caused_change':
            return 'contradicted' if 'no' in (facts.region(arg[1]), facts.region(arg[2])) else 'not_established'
        return 'not_established'  # mechanism_identified
    if family == 'effect_hypothesis':
        return facts.hypothesis(*arg)
    if family == 'subgoal_status':
        return facts.subgoal()[0]
    if family == 'subgoal_decision':
        return facts.subgoal()[1]
    raise ValueError(family)


def keys(ctx, family, arg, sources=(ContractFacts, ReferenceFacts, ConstructionFacts)):
    return [rule(source(ctx), family, arg) for source in sources]


# ------------------------------------------------------------------ predeclared shortcuts


def _tri(measure):
    return 'cannot_tell' if measure['status'] != 'measured' else ('yes' if measure['value'] else 'no')


def shortcuts(f, family, arg, key):
    """Answers available without reading the evidence correctly; they include the error patterns under test (a change
    read as progress, absence of a report read as no progress, a sequence read as a cause, repetition read as a
    mechanism, an achieved subgoal read as progress or as useful, a failed or unknown outcome read as no change)."""
    focus = f.records[-1]
    m = focus['measurements']
    differs = _tri(m['any_returned_frame_differs'])
    sub = f.subgoal_full() if f.ctx['subgoal'] is not None else None
    achieved = sub is not None and sub['status'] == S.ACHIEVED
    uncertain = UNCERTAIN.get(family)
    # "never uncertain": the key, except that the uncertain answer is replaced by a definite one
    if family == 'visual_effect':
        final = _tri(m['final_frame_equals_pre'])
        return {'final_frame_only': {'yes': 'no_observed_change', 'no': 'final_frame_differs'}.get(final, 'indeterminate'),
                'never_uncertain': 'no_observed_change' if key == uncertain else key,
                'always_final_frame_differs': 'final_frame_differs'}
    if family == 'region_changed':
        return {'frame_level_change': differs, 'never_uncertain': 'no' if key == uncertain else key,
                'always_no': 'no'}
    if family == 'progress_status':
        return {'always_unknown': 'unknown', 'change_means_progress': 'confirmed' if differs == 'yes' else 'unknown',
                'change_or_subgoal_as_progress': 'confirmed' if differs == 'yes' or achieved else key}
    if family == 'claim_progress':
        if arg[0] == 'progress_confirmed':
            over = 'supported' if differs == 'yes' or achieved else key
        else:  # "no progress": asserted when nothing changed or nothing was reported
            over = 'supported' if differs == 'no' or f.progress() == V.UNKNOWN else key
        return {'always_not_established': 'not_established', 'over_claim': over}
    if family == 'claim_usefulness':
        useful = (achieved if arg[0] == 'subgoal_helps' else f.region(arg[1]) == 'yes')
        return {'always_not_established': 'not_established', 'change_means_useful': 'supported' if useful else key}
    if family == 'claim_causal':
        if arg[0] == 'caused_region_change':
            consistent = f.region(arg[1]) == 'yes'
        elif arg[0] == 'change_caused_change':
            consistent = f.region(arg[1]) == f.region(arg[2]) == 'yes'
        else:
            t = f.hypothesis_full(arg[1], arg[2])['tally']
            consistent = t['trials_changed'] >= 1 and not t['trials_unchanged']
        return {'always_not_established': 'not_established', 'consistency_as_cause': 'supported' if consistent else key}
    if family == 'effect_hypothesis':
        t = f.hypothesis_full(*arg)['tally']
        return {'always_insufficient': 'insufficient_evidence',
                'trials_only': 'weakened' if t['trials_unchanged'] else 'strengthened' if t['trials_changed'] >= 2
                else 'insufficient_evidence',
                'consistent_trials_as_strengthened': 'strengthened' if t['trials_changed'] >= 1 and
                not t['trials_unchanged'] else key}
    if family == 'subgoal_status':
        test = f.ctx['subgoal']['success_test']
        any_frame = any(S.meets_test(g, test) for raw in f.raws if raw['outcome']['status'] == 'acknowledged'
                        for g in raw['outcome']['after'].get('frames') or [])
        return {'always_not_achieved': 'not_achieved', 'never_uncertain': 'not_achieved' if key == uncertain else key,
                'any_returned_frame_counts': 'achieved' if any_frame else key}
    if family == 'subgoal_decision':
        used = sub['actions_used'] >= sub['action_budget']
        return {'never_abandon': 'stop_achieved' if achieved else 'continue',
                'budget_only': 'stop_achieved' if achieved else 'abandon_budget_exhausted' if used else 'continue',
                'invalidation_only': 'stop_achieved' if achieved else 'abandon_invalidated' if sub['invalidation_met']
                else 'continue'}
    raise ValueError(family)


# ------------------------------------------------------------------ candidates, classes, gates


def candidate_args(ctx, family):
    regions = sorted(ctx['regions'])
    if family in ('visual_effect', 'progress_status'):
        return [()]
    if family == 'region_changed':
        return [(r,) for r in regions]
    if family == 'claim_progress':
        return [('progress_confirmed',), ('no_progress',)]
    if family == 'claim_usefulness':
        return [('region_helps', r) for r in regions] + ([('subgoal_helps',)] if ctx['subgoal'] else [])
    if family == 'claim_causal':
        return ([('caused_region_change', r) for r in regions] +
                [('change_caused_change', a, b) for a in regions for b in regions if a != b] +
                [('mechanism_identified', 'A', 'R1'), ('mechanism_identified', 'A', 'R2')])
    if family == 'effect_hypothesis':
        return [('A', 'R1'), ('A', 'R2'), ('B', 'R1')]
    if family in ('subgoal_status', 'subgoal_decision'):
        return [()] if ctx['subgoal'] else []
    raise ValueError(family)


CRITICAL_CLASSES = ('visible_change_without_progress', 'transient_change', 'change_between_observations',
                    'confirmed_progress', 'progress_without_visible_change', 'unobserved_last_outcome',
                    'simultaneous_changes', 'hypothesis_strengthened', 'subgoal_achieved_without_progress',
                    'subgoal_achieved_with_confirmed_progress', 'subgoal_disconfirmed', 'subgoal_budget_exhausted',
                    'subgoal_unobserved')


def critical_classes(f):
    """Classes of the context, from the contract facts (never from fixture labels)."""
    focus = f.records[-1]
    differs = _tri(focus['measurements']['any_returned_frame_differs'])
    out = []
    if differs == 'yes' and f.progress() == V.UNKNOWN:
        out.append('visible_change_without_progress')
    if f.visual() == V.CHANGED_THEN_RETURNED:
        out.append('transient_change')
    if any(S.gap_status(f.raws[n - 1], f.raws[n], r) == S.YES for n in range(1, len(f.raws))
           for r in f.ctx['regions'].values()):
        out.append('change_between_observations')
    if f.progress() == V.CONFIRMED:
        out.append('confirmed_progress')
        if differs == 'no':
            out.append('progress_without_visible_change')
    if f.visual() == V.INDETERMINATE:
        out.append('unobserved_last_outcome')
    if sum(f.region(r) == S.YES for r in f.ctx['regions']) >= 2:
        out.append('simultaneous_changes')
    if any(f.hypothesis(*a) == S.STRENGTHENED for a in candidate_args(f.ctx, 'effect_hypothesis')):
        out.append('hypothesis_strengthened')
    if f.ctx['subgoal'] is not None:
        sub = f.subgoal_full()
        if sub['status'] == S.ACHIEVED:
            out.append('subgoal_achieved_with_confirmed_progress' if sub['confirmed_progress_transitions']
                       else 'subgoal_achieved_without_progress')
        out += {S.ABANDON_INVALIDATED: ['subgoal_disconfirmed'], S.ABANDON_BUDGET: ['subgoal_budget_exhausted']}.get(
            sub['decision'], [])
        if sub['status'] == S.CANNOT_TELL:
            out.append('subgoal_unobserved')
    return out


# Over-claim gates (scoring r1: valid answers only). A context is an opportunity when it has a member question with a
# valid answer; it counts as an over-claim when, in either pass, a valid answer to a member question is the
# affirmative one. Invalid answers count against accuracy and validity instead. Members: (family, claim or None, keys).
# Revision r2: "no progress" asserted where only the absence of a report exists is a readiness gate (absence of
# reported progress is not proof of no progress), with a larger opportunity target so 2% has usable resolution.
OVER_CLAIM_GATES = {
    'false_progress': {'members': [('progress_status', None, ('unknown',)),
                                   ('claim_progress', 'progress_confirmed', ('not_established',))],
                       'affirmative': {'progress_status': 'confirmed', 'claim_progress': 'supported'}},
    'unsupported_causal_claim': {'members': [('claim_causal', None, ('not_established', 'contradicted')),
                                             ('effect_hypothesis', None, ('weakened', 'insufficient_evidence'))],
                                 'affirmative': {'claim_causal': 'supported', 'effect_hypothesis': 'strengthened'}},
    'unsupported_usefulness_claim': {'members': [('claim_usefulness', None, ('not_established',))],
                                     'affirmative': {'claim_usefulness': 'supported'}},
    'false_subgoal_success': {'members': [('subgoal_status', None, ('not_achieved', 'cannot_tell'))],
                              'affirmative': {'subgoal_status': 'achieved'}},
    'false_no_progress': {'members': [('claim_progress', 'no_progress', ('not_established',))],
                          'affirmative': {'claim_progress': 'supported'}},
}
# Valid-opportunity floor per gate (contexts). false_no_progress needs more: at <= 2%, 150 contexts tolerate 3.
GATE_FLOORS = {**{g: 100 for g in OVER_CLAIM_GATES}, 'false_no_progress': 150}
# Selection: questions per (claim, key) group where the equal cap would be too small (absolute counts).
GROUP_TARGET = {('no_progress', 'not_established'): 180}


def gate_member(gate, probe):
    return any(probe['family'] == fam and (claim is None or probe['claim'] == claim) and probe['key'] in ks
               for fam, claim, ks in OVER_CLAIM_GATES[gate]['members'])


# ------------------------------------------------------------------ build


def _select(pool, family, target, rng, errors):
    """Each key (claims: each claim-and-key pair) gets the same cap, filled round-robin across strata. A stratum is
    the set of predeclared shortcuts that would answer correctly, so every trap is represented, not only the common
    ones. Selection reads observable facts only (keys and shortcuts), never fixture labels."""
    groups = {}
    for ctx, f in pool:
        for arg in candidate_args(ctx, family):
            ks = keys(ctx, family, arg)
            if len(set(ks)) != 1:
                errors.append((ctx['id'], family, arg, ks))
            signature = tuple(sorted(n for n, v in shortcuts(f, family, arg, ks[0]).items() if v == ks[0]))
            groups.setdefault((arg[0] if arg and arg[0] in CLAIM_FAMILY else None, ks[0]), {}).setdefault(
                signature, []).append((ctx, f, arg, ks[0]))
    if not groups:
        return []
    equal_cap = -(-int(target * TARGET_FACTOR.get(family, 1)) // len(groups))
    scale = target / TARGET['evaluation']  # development keeps the same proportions
    chosen_all = []
    for group_key in sorted(groups, key=str):
        group = groups[group_key]
        cap = max(equal_cap, round(GROUP_TARGET[group_key] * scale)) if group_key in GROUP_TARGET else equal_cap
        queues = []
        for name in sorted(group):
            rng.shuffle(group[name])
            queues.append(group[name])
        chosen, used = [], set()
        while len(chosen) < cap and any(queues):
            for queue in queues:
                if queue and len(chosen) < cap:
                    queue.sort(key=lambda c: c[0]['id'] in used)  # prefer contexts not yet used in this group
                    chosen.append(queue.pop(0))
                    used.add(chosen[-1][0]['id'])
        chosen_all += chosen
    return chosen_all


def build(partition, seed=None, count=None, conditions=PRIMARY_CONDITIONS):
    """Contexts, probes and schedule for one partition. The evaluation partition needs the seed drawn at freeze.
    `conditions` defaults to the two primary arms; the questions and keys do not depend on it."""
    if partition == DECISION_PARTITION and not seed:
        raise ValueError('the evaluation partition is built only at the freeze, with its recorded seed')
    if not conditions or set(conditions) - set(ALL_CONDITIONS) or len(set(conditions)) != len(conditions):
        raise ValueError('conditions must be distinct members of ALL_CONDITIONS')
    conditions = tuple(c for c in ALL_CONDITIONS if c in conditions)
    pool = [(ctx, ContractFacts(ctx)) for ctx in F.generate(partition, seed, count)]
    rng = random.Random(hashlib.sha256(f'{VERSION}:{partition}:{seed}:select'.encode()).hexdigest())
    probes, contexts, errors = [], {}, []
    classes = {ctx['id']: critical_classes(f) for ctx, f in pool}
    for family in FAMILIES:
        for ctx, f, arg, key in _select(pool, family, TARGET[partition], rng, errors):
            answers = shortcuts(f, family, arg, key)
            right = sorted(n for n, v in answers.items() if v == key)
            suffix = ':'.join((family,) + tuple(arg))
            for condition in conditions:
                cid = f"{partition}:{condition}:{ctx['id']}"
                if cid not in contexts:
                    contexts[cid] = present(ctx, f.records, condition)
                probes.append({'probe_id': f'{cid}:{suffix}', 'pair_id': f"{partition}:{ctx['id']}:{suffix}",
                               'context_id': cid, 'case_context': f"{partition}:{ctx['id']}",
                               'source_context': ctx['id'], 'partition': partition, 'condition': condition,
                               'family': family, 'level': LEVEL[family], 'role': ROLE_OF[family], 'arg': list(arg),
                               'claim': arg[0] if arg and arg[0] in CLAIM_FAMILY else None,
                               'question': question_text(ctx, family, arg), 'key': key,
                               'uncertain_key': key == UNCERTAIN.get(family),
                               'fixture_family': ctx['family'], 'critical_classes': classes[ctx['id']],
                               'shortcuts_correct': right, 'shortcut_answers': answers})
    if errors:
        raise ValueError(f'key derivations disagree: {errors[:5]}')
    value = {'version': VERSION, 'partition': partition, 'conditions': list(conditions),
             'system_prompts': {c: SYSTEM_PROMPTS[c] for c in conditions}, 'contexts': contexts,
             'probes': probes, 'schedule': schedule(probes, partition, conditions)}
    return value


SCHEDULE_SEED = 'progress-subgoal-v1-schedule'


def conditions_of(probes):
    """The arms present in a probe set, in canonical order."""
    present_ = {p['condition'] for p in probes}
    return tuple(c for c in ALL_CONDITIONS if c in present_)


def comparisons_of(conditions):
    return {name: pair for name, pair in COMPARISONS.items() if set(pair) <= set(conditions)}


def schedule(probes, partition, conditions=None):
    """Decision partitions: two passes; each question's conditions adjacent, their order cycling through every
    permutation (two arms: alternating) in seeded question order; pass 2 is pass 1 exactly reversed. Development: one
    pass."""
    conditions = conditions or conditions_of(probes)
    orders = list(itertools.permutations(range(len(conditions))))
    rng = random.Random(hashlib.sha256(f'{SCHEDULE_SEED}:{partition}'.encode()).hexdigest())
    groups = {}
    for p in probes:
        groups.setdefault(p['case_context'], {}).setdefault(p['pair_id'], {})[p['condition']] = p['probe_id']
    ids, k = [], 0
    cases = sorted(groups)
    rng.shuffle(cases)
    for case in cases:
        for pair in sorted(groups[case]):
            ids += [groups[case][pair][conditions[i]] for i in orders[k % len(orders)]]
            k += 1
    order = [{'partition': partition, 'pass': 'pass_1', 'probe_ids': ids}]
    if partition != 'development':
        order.append({'partition': partition, 'pass': 'pass_2', 'probe_ids': ids[::-1]})
    return order


def coverage(probes, partition, strict=True):
    """Coverage floors on a decision-shaped partition (first condition; the others ask the same questions)."""
    first = conditions_of(probes)[0]
    held = [p for p in probes if p['partition'] == partition and p['condition'] == first]
    report, failures = {'families': {}, 'critical_classes': {}, 'over_claim_denominators': {}}, []
    for family in FAMILIES:
        group = [p for p in held if p['family'] == family]
        counts = {}
        for p in group:
            for name in p['shortcuts_correct']:
                counts[name] = counts.get(name, 0) + 1
        best = max(counts.values(), default=0)
        keys_ = {}
        for p in group:
            keys_[p['key']] = keys_.get(p['key'], 0) + 1
        row = {'n': len(group), 'role': ROLE_OF[family], 'level': LEVEL[family], 'keys': keys_,
               'best_shortcut_accuracy': round(best / len(group), 4) if group else None,
               'shortcut_disagreement_n': len(group) - best}
        report['families'][family] = row
        if ROLE_OF[family] == 'primary' and (row['n'] < FLOORS['primary_questions']
                                             or row['shortcut_disagreement_n'] < FLOORS['shortcut_disagreement']):
            failures.append((family, row['n'], row['shortcut_disagreement_n']))
    for name in CRITICAL_CLASSES:
        n = len({p['case_context'] for p in held if name in p['critical_classes']})
        report['critical_classes'][name] = n
        if n < FLOORS['critical_class_contexts']:
            failures.append((name, n))
    for gate in OVER_CLAIM_GATES:
        n = len({p['case_context'] for p in held if gate_member(gate, p)})
        report['over_claim_denominators'][gate] = n
        if n < GATE_FLOORS[gate]:
            failures.append((gate, n))
    abandon = sum(p['family'] == 'subgoal_decision' and p['key'] == S.ABANDON_INVALIDATED for p in held)
    uncertain = sum(p['uncertain_key'] for p in held)
    report['abandonment_questions'], report['uncertain_keyed_questions'] = abandon, uncertain
    if abandon < FLOORS['abandonment_questions']:
        failures.append(('abandonment_questions', abandon))
    if uncertain < FLOORS['uncertain_keyed_questions']:
        failures.append(('uncertain_keyed_questions', uncertain))
    report['failures'] = failures
    if failures and strict:
        raise ValueError(f'coverage below the floors: {failures}')
    return report
