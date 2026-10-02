"""Independent offline evaluator for feedback-action decisions.

Imports only the standard library and `research.transition_evidence_v1.reference` (itself import-free). It never
imports the adapter, the evidence view or `transition.py`: it re-parses raw model output, re-derives the shown
window, evidence statuses and prediction outcomes from the raw transitions, and scores only mechanically checkable
things:

- citations: the ref must be an earlier transition shown in the window, and its claim must match that transition;
- untested versus ineffective: per-action evidence status at the decision, and failed or unknown dispatches read as
  "no observed change";
- contradictions: a prediction falsified by the next transition, and whether the following decision revises. A
  revision is scored only relative to a previous statement actually present in that decision's request (read from
  the retained request bytes, `previous_model_statement`), about the falsifying transition and carrying the same
  prediction; otherwise the result is `previous_statement_absent`, never `recognized`;
- legality of the action against the legal actions recorded with the decision;
- predictions: closed-vocabulary fields compared with the next transition.

Free text (`hypothesis`, `if_different`) is retained and length-checked, never scored for plausibility.

Record identity (transition_evidence_v2 format): every cited and every dispatched transition is also reported by its
`record_id`, `<episode_id>#<action_index>`, derived here from the raw identity (the evaluator does not import version
2 code; a test checks agreement with `transition_evidence_v2.transition.record_id`). Model-facing refs stay `T<n>`.
"""
import hashlib
import json

from research.transition_evidence_v1 import reference as REF

VERSION = 'feedback_action_v1_evaluator'
WINDOW = 8
BOUNDARY = {'reset_acknowledged', 'level_completed', 'level_count_decreased', 'terminal_state'}
VISUAL = ('no_observed_change', 'changed_then_returned', 'final_frame_differs')
CLAIMS = VISUAL + ('indeterminate', 'dispatch_failed', 'outcome_unknown', 'level_completed', 'reset_acknowledged',
                   'same_state_as_now', 'different_state_from_now')
FIELDS = ('hypothesis', 'status', 'supporting', 'conflicting', 'prediction', 'if_different')

# Evidence status of one exact action (id and coordinates) at a decision, over the shown window only.
NO_CHANGE_SAME_STATE = 'no_change_same_state'      # latest same-state observation: nothing differed
TRANSIENT_SAME_STATE = 'transient_same_state'      # latest same-state observation: changed, then returned
CHANGED_SAME_STATE = 'changed_same_state'          # latest same-state observation: the final frame differed
INDETERMINATE_SAME_STATE = 'indeterminate_same_state'
TESTED_OTHER_STATE = 'tested_other_state'          # observed only from other states
OUTCOME_UNKNOWN_ONLY = 'outcome_unknown_only'      # dispatched, never observed
FAILED_ONLY = 'failed_only'                        # every dispatch failed: untested, not ineffective
UNTESTED = 'untested'
STATUSES = (NO_CHANGE_SAME_STATE, TRANSIENT_SAME_STATE, CHANGED_SAME_STATE, INDETERMINATE_SAME_STATE,
            TESTED_OTHER_STATE, OUTCOME_UNKNOWN_ONLY, FAILED_ONLY, UNTESTED)


def record_id(raw):
    identity = raw['identity']
    return f"{identity['episode_id']}#{identity['action_index']}"


def cited_record_id(cite, raws):
    """The record_id an in-range ref resolves to (shown or not), else None (malformed, future or invented)."""
    ref = cite.get('ref') if isinstance(cite, dict) else None
    if not isinstance(ref, str) or ref[:1] != 'T' or not ref[1:].isdigit():
        return None
    for raw in raws:
        if raw['identity']['action_index'] == int(ref[1:]):
            return record_id(raw)
    return None


def grid_key(grid):
    return hashlib.sha256(json.dumps(grid, separators=(',', ':')).encode()).hexdigest()


def action_key(action):
    data = action.get('action_data') or {}
    return (action['action_id'], data['x'], data['y']) if 'x' in data else (action['action_id'],)


def shown_window(raws, limit=WINDOW):
    """Indices of the transitions shown to the next decision (current segment, at most `limit`, oldest first)."""
    if not raws:
        return []
    segments = REF.sequence(raws)
    if set(REF.facts(raws[-1])['events']) & BOUNDARY:
        return []
    current = segments[-1][0]
    indices = [i for i, (segment, _) in enumerate(segments) if segment == current]
    return indices[-limit:]


def evidence_status(raws, shown, current_frame, key):
    here = grid_key(current_frame)
    mine = [i for i in shown if action_key(raws[i]['dispatched']) == key]
    observed = [i for i in mine if REF.facts(raws[i])['dispatch'] == 'acknowledged']
    same = [i for i in observed if grid_key(raws[i]['before']['frames'][-1]) == here]
    if same:
        visual = REF.facts(raws[same[-1]])['visual']
        return {'no_observed_change': NO_CHANGE_SAME_STATE, 'changed_then_returned': TRANSIENT_SAME_STATE,
                'final_frame_differs': CHANGED_SAME_STATE}.get(visual, INDETERMINATE_SAME_STATE)
    if observed:
        return TESTED_OTHER_STATE
    if any(REF.facts(raws[i])['dispatch'] == 'outcome_unknown' for i in mine):
        return OUTCOME_UNKNOWN_ONLY
    if mine:
        return FAILED_ONLY
    return UNTESTED


def claim_holds(claim, raw, current_frame):
    f = REF.facts(raw)
    if claim in ('no_observed_change', 'changed_then_returned', 'final_frame_differs', 'indeterminate'):
        return f['visual'] == claim
    if claim == 'dispatch_failed':
        return f['dispatch'] == 'failed'
    if claim == 'outcome_unknown':
        return f['dispatch'] == 'outcome_unknown'
    if claim in ('level_completed', 'reset_acknowledged'):
        return claim in f['events']
    same = grid_key(raw['before']['frames'][-1]) == grid_key(current_frame)
    return same if claim == 'same_state_as_now' else not same


def citation_category(cite, raws, shown, current_frame):
    """supported | wrong_claim | failure_read_as_no_change | earlier_not_shown | not_earlier | malformed"""
    ref = cite.get('ref') if isinstance(cite, dict) else None
    if not isinstance(ref, str) or ref[:1] != 'T' or not ref[1:].isdigit() or cite.get('claim') not in CLAIMS:
        return 'malformed'
    index = int(ref[1:])
    by_index = {raw['identity']['action_index']: n for n, raw in enumerate(raws)}
    if index not in by_index:
        return 'not_earlier'
    n = by_index[index]
    if n not in shown:
        return 'earlier_not_shown'
    if claim_holds(cite['claim'], raws[n], current_frame):
        return 'supported'
    if cite['claim'] == 'no_observed_change' and REF.facts(raws[n])['dispatch'] != 'acknowledged':
        return 'failure_read_as_no_change'
    return 'wrong_claim'


def parse_output(content, finish_reason, arm):
    """(value, problem). Independent of the adapter's parser."""
    if finish_reason == 'length':
        return None, 'truncated'
    try:
        value = json.loads(content)
    except (TypeError, ValueError):
        return None, 'not_json'
    expected = {'action'} if arm == 'baseline' else {'action', 'hypothesis_test'}
    if not isinstance(value, dict) or not set(value) <= expected:
        return None, 'unexpected_fields'
    return value, None


def action_problem(action, legal):
    if not isinstance(action, dict) or set(action) != {'action_id', 'action_data'}:
        return 'malformed_action'
    if type(action['action_id']) is not int or action['action_id'] not in legal:
        return 'illegal_action'
    data = action['action_data']
    if action['action_id'] == 6:
        if not isinstance(data, dict) or set(data) != {'x', 'y'} or any(
                type(v) is not int or not 0 <= v <= 63 for v in data.values()):
            return 'bad_coordinates'
    elif data != {}:
        return 'unexpected_action_data'
    return None


def block_problem(block):
    if not isinstance(block, dict) or set(block) != set(FIELDS):
        return 'missing_or_extra_fields'
    if block['status'] not in ('new', 'retained', 'revised'):
        return 'bad_status'
    for name in ('hypothesis', 'if_different'):
        if not isinstance(block[name], str) or not block[name].strip() or len(block[name]) > 240:
            return 'bad_text'
    for name in ('supporting', 'conflicting'):
        if not isinstance(block[name], list) or len(block[name]) > 4:
            return 'bad_citation_list'
        for cite in block[name]:
            if not isinstance(cite, dict) or set(cite) != {'ref', 'claim'}:
                return 'missing_reference'
    p = block['prediction']
    if not isinstance(p, dict) or set(p) != {'visual_effect', 'level_completed', 'changed_region_xyxy'}:
        return 'unobservable_prediction'
    if p['visual_effect'] not in VISUAL or type(p['level_completed']) is not bool:
        return 'unobservable_prediction'
    region = p['changed_region_xyxy']
    if region is not None:
        if (not isinstance(region, list) or len(region) != 4 or any(type(v) is not int or not 0 <= v <= 63 for v in region)
                or region[0] > region[2] or region[1] > region[3]):
            return 'unobservable_prediction'
        if p['visual_effect'] == 'no_observed_change':
            return 'region_with_no_change'
    return None


def changed_cells_any_frame(raw):
    """Every [x, y] differing from the pre-action frame in any valid returned frame of the same shape."""
    pre = raw['before']['frames'][-1]
    cells = set()
    for grid in raw['outcome']['after'].get('frames') or []:
        if REF.flat(grid) is None or len(grid) != len(pre) or len(grid[0]) != len(pre[0]):
            continue
        cells |= {(x, y) for y, row in enumerate(grid) for x, v in enumerate(row) if v != pre[y][x]}
    return cells


def score_prediction(prediction, raw):
    """'correct' | 'incorrect' | 'unscoreable', with the field-level comparison."""
    f = REF.facts(raw)
    if f['dispatch'] != 'acknowledged' or f['visual'] == 'indeterminate':
        return {'result': 'unscoreable', 'reason': f"dispatch {f['dispatch']}, visual {f['visual']}"}
    fields = {'visual_effect': prediction['visual_effect'] == f['visual'],
              'level_completed': prediction['level_completed'] == ('level_completed' in f['events'])}
    region = prediction['changed_region_xyxy']
    if region is not None:
        x0, y0, x1, y1 = region
        fields['changed_region_xyxy'] = all(x0 <= x <= x1 and y0 <= y <= y1 for x, y in changed_cells_any_frame(raw))
    return {'result': 'correct' if all(fields.values()) else 'incorrect', 'fields': fields, 'observed': f['visual']}


def previous_statement_from_request(user_content):
    """The carried statement exactly as sent (top level of the user message), or None if none was sent."""
    try:
        value = json.loads(user_content)
    except (TypeError, ValueError):
        return None
    statement = value.get('previous_model_statement') if isinstance(value, dict) else None
    if not isinstance(statement, dict) or statement.get('record') != 'model_statement' or statement.get('available') is not True:
        return None
    return statement


def statement_matches(statement, prior):
    return (statement is not None and statement.get('about') == prior['ref']
            and statement.get('prediction') == prior['prediction'])


def opportunities(raws, shown, current_frame, legal, arm):
    """What this decision could have done, from the evidence shown and the legal actions alone (computed for every
    decision, whether or not the output turns out valid, so an invalid output never removes an opportunity)."""
    keys = {action_key(raws[i]['dispatched']) for i in shown}
    repeatable = sorted(k for k in keys if k[0] in legal
                        and evidence_status(raws, shown, current_frame, k) == NO_CHANGE_SAME_STATE)
    tried = {raws[i]['dispatched']['action_id'] for i in shown if REF.facts(raws[i])['dispatch'] == 'acknowledged'}
    untested = sorted(a for a in legal if a not in tried)
    return {'repeat': bool(repeatable), 'repeatable_keys': [list(k) for k in repeatable],
            'untested_type': bool(untested), 'untested_types': untested,
            'citation': arm == 'candidate' and bool(shown)}


def evaluate_decision(raws, decision, prior=None):
    """One decision against the raw transitions dispatched before it.

    decision: {'arm', 'legal_actions', 'current_frame', 'response': {'content', 'finish_reason'},
               'previous_statement': the carried statement present in the request, or None}
    prior: {'ref': 'T<n>', 'prediction': ...} when the previous decision's prediction was falsified by T<n>.
    """
    if prior is not None and not statement_matches(decision.get('previous_statement'), prior):
        prior = dict(prior, absent=True)
    shown = shown_window(raws)
    result = {'shown_refs': [f"T{raws[i]['identity']['action_index']}" for i in shown],
              'opportunities': opportunities(raws, shown, decision['current_frame'], decision['legal_actions'],
                                             decision['arm'])}
    value, problem = parse_output(decision['response'].get('content'), decision['response'].get('finish_reason'),
                                  decision['arm'])
    result['output_problem'] = problem
    if prior is not None and decision['arm'] == 'candidate':
        result['revision'] = 'previous_statement_absent' if prior.get('absent') else None
    if value is None:
        result['action_problem'] = problem
        result['procedure_problem'] = problem if decision['arm'] == 'candidate' else None
        if prior is not None and not prior.get('absent'):
            result['revision'] = 'procedure_invalid' if decision['arm'] == 'candidate' else None
        return result
    action = value.get('action')
    result['action_problem'] = action_problem(action, decision['legal_actions'])
    if result['action_problem'] is None:
        key = action_key(action)
        result['action_key'] = list(key)
        result['chosen_status'] = evidence_status(raws, shown, decision['current_frame'], key)
        result['opportunities']['untested_type_chosen'] = key[0] in result['opportunities']['untested_types']
    if decision['arm'] != 'candidate':
        return result
    block = value.get('hypothesis_test')
    result['procedure_problem'] = block_problem(block)
    if result['procedure_problem'] is not None:
        if prior is not None and not prior.get('absent'):
            result['revision'] = 'procedure_invalid'
        return result
    result['citations'] = {name: [citation_category(c, raws, shown, decision['current_frame']) for c in block[name]]
                           for name in ('supporting', 'conflicting')}
    result['cited_record_ids'] = {name: [cited_record_id(c, raws) for c in block[name]]
                                  for name in ('supporting', 'conflicting')}
    result['cites_nothing_with_evidence_shown'] = bool(shown) and not (block['supporting'] or block['conflicting'])
    result['prediction'] = block['prediction']
    if result['action_problem'] is None and result['chosen_status'] == NO_CHANGE_SAME_STATE:
        refs = {c['ref'] for c in block['supporting'] + block['conflicting']}
        latest = [i for i in shown if action_key(raws[i]['dispatched']) == key]
        result['repeat_cites_its_no_change'] = f"T{raws[latest[-1]]['identity']['action_index']}" in refs
    if prior is not None and not prior.get('absent'):
        cited = any(c['ref'] == prior['ref'] for c in block['conflicting'])
        revised = block['status'] == 'revised'
        result['revision'] = ('recognized' if cited and revised else 'revised_not_cited' if revised else
                              'cited_not_revised' if cited else 'not_recognized')
    return result


def evaluate_trajectory(trajectory):
    """Per-decision results and episode metrics for one trajectory. Steps of one trajectory are not independent."""
    raws, steps = trajectory['raws'], trajectory['steps']
    rows, prior = [], None
    for step in steps:
        before = raws[:step['raws_before']]
        sent = previous_statement_from_request(step.get('request_user_content'))
        row = evaluate_decision(before, {**step, 'arm': trajectory['arm'], 'previous_statement': sent}, prior)
        row['previous_statement_in_request'] = sent is not None
        row['dispatched'] = step['dispatched_index'] is not None
        prior = None
        if step['dispatched_index'] is not None:
            raw = raws[step['dispatched_index']]
            f = REF.facts(raw)
            row['outcome'] = {'dispatch': f['dispatch'], 'visual': f['visual'], 'events': f['events']}
            row['record_id'] = record_id(raw)
            if row.get('prediction') is not None:
                row['prediction_result'] = score_prediction(row['prediction'], raw)
                if row['prediction_result']['result'] == 'incorrect':
                    prior = {'ref': f"T{raw['identity']['action_index']}", 'prediction': row['prediction']}
        rows.append(row)
    return {'version': VERSION, 'arm': trajectory['arm'], 'environment': trajectory['environment'],
            'decisions': rows, 'metrics': metrics(trajectory, rows)}


def count(items):
    out = {}
    for item in items:
        out[item] = out.get(item, 0) + 1
    return dict(sorted(out.items()))


def metrics(trajectory, rows):
    raws = trajectory['raws']
    facts = [REF.facts(r) for r in raws]
    repeats = [r for r in rows if r.get('chosen_status') == NO_CHANGE_SAME_STATE and r['dispatched']]
    cites = [c for r in rows for name in ('supporting', 'conflicting') for c in r.get('citations', {}).get(name, [])]
    predictions = [r['prediction_result']['result'] for r in rows if 'prediction_result' in r]
    revisions = [r['revision'] for r in rows if r.get('revision') is not None]
    return {
        'decisions': len(rows),
        'dispatched': sum(r['dispatched'] for r in rows),
        'invalid_actions': count(r['action_problem'] for r in rows if r['action_problem'] is not None),
        'invalid_procedures': count(r['procedure_problem'] for r in rows if r.get('procedure_problem') is not None),
        'dispatch_outcomes': count(f['dispatch'] for f in facts),
        'chosen_status': count(r['chosen_status'] for r in rows if 'chosen_status' in r),
        'exact_repeats_after_no_change_same_state': len(repeats),
        'of_which_followed_by_visible_change_or_level': sum(
            r['outcome']['visual'] in ('final_frame_differs', 'changed_then_returned') or
            'level_completed' in r['outcome']['events'] for r in repeats),
        'citations': count(cites),
        'predictions': count(predictions),
        'revision_after_contradiction': count(revisions),
        'levels_completed': sum('level_completed' in f['events'] for f in facts),
        'wins': sum(f['progress'] == 'confirmed' and 'terminal_state' in f['events'] for f in facts),
        'stop_reason': trajectory['stop_reason'],
        'prompt_chars': sum(s['prompt_chars'] for s in trajectory['steps']),
        'completion_tokens': sum(s['response'].get('completion_tokens') or 0 for s in trajectory['steps']),
        'rates': rates(trajectory['arm'], rows),
    }


# ---- rates with explicit denominators (protocol v2 §8)
#
# Every rate is {'numerator', 'denominator', 'status', 'value', 'minimum'}:
# - status 'undefined' when the denominator is 0 (value None): never reported as 0;
# - status 'insufficient' when 0 < denominator < minimum (value None; 'observed' kept for description);
# - status 'not_applicable' for a candidate-only rate in the baseline arm.
# Failure-inclusive: every decision (model call) is in the denominator of each rate whose opportunity it had, and an
# invalid output or invalid procedure block counts as the unfavourable outcome. A run that fails more can therefore
# never obtain a better rate, and an episode stopped at the decision-call cap keeps every call it made.

MINIMUMS = {  # per (game, arm), pooled over the two blocks; per episode the minimum is 1 (defined iff denominator > 0)
    'repeat_after_no_change': 5, 'repeat_after_no_change_valid_only': 5, 'untested_type_chosen': 5,
    'citation_supply': 10, 'unsupported_citation': 10, 'prediction_accuracy': 10, 'revision_recognized': 3,
    'invalid_action': 1, 'invalid_procedure': 1}
CANDIDATE_ONLY = ('citation_supply', 'unsupported_citation', 'prediction_accuracy', 'revision_recognized',
                  'invalid_procedure')
UNFAVOURABLE = ('repeat_after_no_change', 'repeat_after_no_change_valid_only', 'unsupported_citation',
                'invalid_action', 'invalid_procedure')
# Descriptive only, never used for advancement: dropping invalid decisions from the denominator means an invalid
# output in place of a repeat would *lower* this rate (tested), so failing could look like improvement.
DESCRIPTIVE_ONLY = ('repeat_after_no_change_valid_only',)


def rate(numerator, denominator, minimum=1, applicable=True):
    out = {'numerator': numerator, 'denominator': denominator, 'minimum': minimum}
    if not applicable:
        return {**out, 'status': 'not_applicable', 'value': None}
    if denominator == 0:
        return {**out, 'status': 'undefined', 'value': None}
    if denominator < minimum:
        return {**out, 'status': 'insufficient', 'value': None, 'observed': numerator / denominator}
    return {**out, 'status': 'defined', 'value': numerator / denominator}


def counts(arm, rows):
    """(numerator, denominator) per rate for one episode."""
    valid = [r for r in rows if r['action_problem'] is None]
    at_repeat = [r for r in rows if r['opportunities']['repeat']]
    at_untested = [r for r in rows if r['opportunities']['untested_type']]
    at_citation = [r for r in rows if r['opportunities']['citation']]
    cites = [c for r in rows for name in ('supporting', 'conflicting') for c in r.get('citations', {}).get(name, [])]
    scored = [r for r in rows if 'prediction_result' in r and r['prediction_result']['result'] != 'unscoreable']
    failed_blocks = [r for r in rows if r.get('procedure_problem') is not None]
    revisions = [r['revision'] for r in rows if r.get('revision') not in (None, 'previous_statement_absent')]
    is_repeat = lambda r: r['action_problem'] is None and r.get('chosen_status') == NO_CHANGE_SAME_STATE
    return {
        'repeat_after_no_change': (sum(is_repeat(r) or r['action_problem'] is not None for r in at_repeat),
                                   len(at_repeat)),
        'repeat_after_no_change_valid_only': (sum(is_repeat(r) for r in at_repeat if r in valid),
                                              sum(r in valid for r in at_repeat)),
        'untested_type_chosen': (sum(r['opportunities'].get('untested_type_chosen') is True for r in at_untested),
                                 len(at_untested)),
        'citation_supply': (sum(r.get('procedure_problem') is None and 'citations' in r and
                                bool(r['citations']['supporting'] or r['citations']['conflicting'])
                                for r in at_citation), len(at_citation)),
        'unsupported_citation': (sum(c != 'supported' for c in cites), len(cites)),
        'prediction_accuracy': (sum(r['prediction_result']['result'] == 'correct' for r in scored),
                                len(scored) + len(failed_blocks)),
        'revision_recognized': (revisions.count('recognized'), len(revisions)),
        'invalid_action': (len(rows) - len(valid), len(rows)),
        'invalid_procedure': (len(failed_blocks), len(rows)),
    }


def rates(arm, rows, minimums=None):
    minimums = minimums or {name: 1 for name in MINIMUMS}
    return {name: rate(n, d, minimums[name], arm == 'candidate' or name not in CANDIDATE_ONLY)
            for name, (n, d) in counts(arm, rows).items()}


def aggregate(evaluations):
    """Pool episodes of one (game, arm) descriptively, applying the protocol minimums. Episodes stay the unit of
    analysis: pooled values are descriptions, never step-level samples."""
    arms = {e['arm'] for e in evaluations}
    if len(arms) != 1:
        raise ValueError('aggregate one arm at a time')
    arm = arms.pop()
    totals = {}
    for e in evaluations:
        for name, (n, d) in counts(arm, e['decisions']).items():
            a, b = totals.get(name, (0, 0))
            totals[name] = (a + n, b + d)
    return {name: rate(n, d, MINIMUMS[name], arm == 'candidate' or name not in CANDIDATE_ONLY)
            for name, (n, d) in totals.items()}
