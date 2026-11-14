"""Prepare one controlled test of whether useful older memory improves Opus's prediction.

Case: vc33, the decision after 43 actions (development case D10). The agent's next action was a click at
x=24, y=56. Older action 38 was the same click with the two compartments it affects in the same state.
Opus is asked to predict the last frame that click returns, under three inputs that differ only in the
older-memory section:
  none        decision-time input only
  useful      plus a B version 2 pack holding action 38
  irrelevant  plus a B version 2 pack of similar size holding a record that does not touch those cells
Nothing is sent here. The design and scoring rule are frozen and hashed first; only then is the answer
(the recorded result of action 44) computed and written to a sealed file.

Usage: actor_test_prep.py <events.jsonl> <agent_review_comparison.json> <out_dir>
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research'))
from complete_evidence_v1 import formats_v2 as F, records  # noqa: E402
from complete_evidence_v1.opus_count import MODEL, OpusCounter  # noqa: E402
from complete_evidence_v1.review_packet import action_text, decision_input  # noqa: E402

GAME, DECISION, USEFUL, UNCERTAINTY = 'vc33', 43, [38], 'U3'
ALLOWANCE, MAX_TOKENS, EFFORT, REPEATS = 2048, 8000, 'high', 2
HEX = '0123456789abcdef'
SYSTEM = ('You are predicting what one action will do in an unfamiliar grid game. Use only the material in the '
          'user message. Reply with one JSON object in the requested form and nothing else.')
QUESTION = '''== PREDICTION ==
The next action will be {action}. Predict the last frame the game returns for that action.

Reply with this JSON object:
{{"changed_regions": [{{"x_first": number, "x_last": number, "y_first": number, "y_last": number, "colour_after": "hex digit"}}],
 "any_change_outside_row_0": true or false,
 "level_completed": true or false,
 "confidence": "low" or "medium" or "high",
 "basis": "one or two sentences naming what in the input you relied on"}}

"changed_regions" lists every rectangle of cells whose colour in that last frame differs from the current board, with the colour those cells have afterwards. Use one rectangle per block of cells that end up one colour. Give an empty list if you predict that no cell changes. Do not list cells that keep their colour.'''


def play_changes(before, after):
    """Changed cells outside row 0 as a frozenset of (y, x, new colour)."""
    ys, xs = np.nonzero(before != after)
    return frozenset((int(y), int(x), int(after[y, x])) for y, x in zip(ys, xs) if y != 0)


def main(events_path, comparison_path, out_dir):
    out = Path(out_dir)
    for sub in ('frozen', 'sealed', 'responses'):
        (out / sub).mkdir(parents=True, exist_ok=True)
    recs = next(v for k, v in records.load_run(events_path).items() if k.startswith(GAME))['records']
    done = recs[:DECISION]
    current = done[-1]['response_frames'][-1]
    target = recs[DECISION]  # action 44: only its action is used below until the sealed step
    comparison = json.loads(Path(comparison_path).read_text())['D10']
    cited = next(u for u in comparison['uncertainties'] if u['id'] == UNCERTAINTY)['cited_actions']
    counter = OpusCounter()
    level, attempt = done[-1]['level_after'], done[-1]['reset_id']

    def pack(events):
        chosen = [recs[e - 1] for e in events]
        return F.pack_b2(GAME, chosen[0]['trajectory_id'], DECISION, chosen, [F.m_ref2(r, current) for r in chosen])
    useful_pack = pack(USEFUL)
    useful_tokens = counter.count(useful_pack, 'actor test useful pack')
    touched = {(y, x) for e in USEFUL for y, x, _ in play_changes(recs[e - 1]['before_frame'], recs[e - 1]['response_frames'][-1])}
    options = []
    for r in done[:-2]:
        if (r['level_observed'], r['reset_id']) != (level, attempt) or r['level_after'] != level or len(r['response_frames']) != 1:
            continue
        if r['event_seq'] in cited or r['event_seq'] in USEFUL or r['action'] == target['action']:
            continue
        cells = {(y, x) for y, x, _ in play_changes(r['before_frame'], r['response_frames'][-1])}
        if not cells or cells & touched:
            continue
        tokens = counter.count(pack([r['event_seq']]), 'actor test irrelevant candidate e%d' % r['event_seq'])
        options.append((abs(tokens - useful_tokens), r['event_seq'], tokens))
    _, irrelevant_event, irrelevant_tokens = min(options)
    irrelevant_pack = pack([irrelevant_event])

    context = decision_input(done, DECISION)
    question = QUESTION.format(action='ACTION6 at x=%d, y=%d' % (target['action']['x'], target['action']['y']))
    sections = {'none': None, 'useful': useful_pack, 'irrelevant': irrelevant_pack}
    requests, counts = {}, {}
    for name, section in sections.items():
        user = '\n\n'.join(p for p in (context, section, question) if p)
        requests[name] = {'model': MODEL, 'max_tokens': MAX_TOKENS, 'thinking': {'type': 'adaptive'},
                          'output_config': {'effort': EFFORT}, 'system': SYSTEM, 'messages': [{'role': 'user', 'content': user}]}
        (out / 'frozen' / ('input_%s.txt' % name)).write_text('[system]\n' + SYSTEM + '\n\n[user]\n' + user + '\n')
        counts[name] = {'older_memory_section_tokens': counter.count(section, 'actor test section %s' % name) if section else 0,
                        'full_request_input_tokens': counter.count_request(requests[name], 'actor test full request %s' % name)}
        assert counts[name]['older_memory_section_tokens'] <= ALLOWANCE
    (out / 'frozen' / 'requests.json').write_text(json.dumps(requests, indent=1))
    np.savez_compressed(out / 'frozen' / 'source_frames.npz', current_board=current,
                        useful_before=recs[USEFUL[0] - 1]['before_frame'], useful_last=recs[USEFUL[0] - 1]['response_frames'][-1],
                        irrelevant_before=recs[irrelevant_event - 1]['before_frame'],
                        irrelevant_last=recs[irrelevant_event - 1]['response_frames'][-1])
    scorer = ROOT / 'research/complete_evidence_v1/actor_test_score.py'
    useful_record = recs[USEFUL[0] - 1]
    same_local = bool(np.array_equal(useful_record['before_frame'][50:59, 10:41], current[50:59, 10:41]))
    design = {
        'question': 'Does supplying one useful older record improve the prediction of the next action\'s result?',
        'case': {'game': GAME, 'development_case': 'D10', 'decision_after_actions': DECISION,
                 'action_to_predict': action_text(target['action']), 'why': 'it is the action the saved agent actually took next, '
                 'so its recorded result is the answer', 'uncertainty_from_agent_review': UNCERTAINTY},
        'conditions': {'none': 'decision-time input only',
                       'useful': 'plus B version 2 pack with action(s) %s' % USEFUL,
                       'irrelevant': 'plus B version 2 pack with action %d, chosen by rule' % irrelevant_event},
        'irrelevant_rule': 'older than the two recent actions, same level and attempt, one frame, changes something in the play area, '
                           'touches none of the cells the useful record changes, is not the action to predict, was not cited for '
                           'this uncertainty by the history reviewer; among those, the pack closest in tokens to the useful pack',
        'irrelevant_candidates_considered': len(options),
        'eligibility_checked_without_the_answer': {
            'rows_50_58_columns_10_40_identical_before_useful_action_and_now': same_local,
            'cells_where_board_before_useful_action_differs_from_current': int((useful_record['before_frame'] != current).sum()),
            'useful_action_equals_action_to_predict': useful_record['action'] == target['action']},
        'model_settings': {k: v for k, v in requests['none'].items() if k not in ('system', 'messages')},
        'requests_planned': {name: REPEATS for name in sections}, 'older_memory_allowance': ALLOWANCE,
        'token_counts_estimates': counts, 'useful_pack_tokens': useful_tokens, 'irrelevant_pack_tokens': irrelevant_tokens,
        'primary_outcome': 'F1 of predicted against actual changed cells of the last returned frame, rows 1-63, right new colour required',
        'reading_rule': {'benefit observed on this case': 'mean F1 of useful exceeds mean F1 of none and of irrelevant by at least 0.10 each',
                         'no benefit observed on this case': 'either difference is below 0.10',
                         'unresolved': 'the two requests of any condition differ by more than 0.5 in F1'},
        'scoring_rule_sha256': hashlib.sha256(scorer.read_bytes()).hexdigest(),
        'frozen_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((out / 'frozen').iterdir())
                          if p.name != 'design.json'}}
    (out / 'frozen' / 'design.json').write_text(json.dumps(design, indent=1))

    # ---- only now: the answer, from the recorded result of the action the agent actually took
    last = target['response_frames'][-1]
    ys, xs = np.nonzero(last != current)
    actual = play_changes(current, last)
    sealed = {
        'warning': 'Answer. Not part of any input. Computed after the design and scoring rule were frozen.',
        'design_sha256': hashlib.sha256((out / 'frozen' / 'design.json').read_bytes()).hexdigest(),
        'action': action_text(target['action']), 'frames_returned': len(target['response_frames']),
        'changed_cells_x_y_colour_after': [[int(x), int(y), HEX[int(last[y, x])]] for y, x in zip(ys, xs)],
        'any_change_outside_row_0': bool(actual), 'level_completed': target['level_after'] > target['level_observed'],
        'state_after': target['state_after'],
        'eligibility': {
            'useful_record_play_area_change_equals_answer': play_changes(useful_record['before_frame'], useful_record['response_frames'][-1]) == actual,
            'irrelevant_record_play_area_change_equals_answer': play_changes(recs[irrelevant_event - 1]['before_frame'], recs[irrelevant_event - 1]['response_frames'][-1]) == actual,
            'most_recent_same_click_t42_play_area_change_equals_answer': play_changes(recs[41]['before_frame'], recs[41]['response_frames'][-1]) == actual}}
    (out / 'sealed' / 'answer_key.json').write_text(json.dumps(sealed, indent=1))
    print(json.dumps({k: design[k] for k in ('conditions', 'irrelevant_candidates_considered', 'eligibility_checked_without_the_answer',
                                             'token_counts_estimates', 'useful_pack_tokens', 'irrelevant_pack_tokens')}, indent=1))
    print('irrelevant record:', irrelevant_event, action_text(recs[irrelevant_event - 1]['action']))
    print('sealed eligibility flags:', sealed['eligibility'])


if __name__ == '__main__':
    main(*sys.argv[1:4])
