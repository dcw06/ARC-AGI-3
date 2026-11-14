"""tn36 development case: did the earlier result matter, and did the agent's notes already hold it?

In tn36 the agent sets switches and presses "run" (a click at x=37, y=55). For every run this lists the
earlier runs made from the same board (row 1, the step counter, ignored), whether the returned frames
were the same, whether the earlier run was among the 8 actions still shown, what the run cost in actions,
and whether any note the agent was given cited an earlier same-board run.

Usage: tn36_case.py <events.jsonl> <out.json>
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from complete_evidence_v1 import records  # noqa: E402

RUN, COUNTER_ROW, WINDOW = (37, 55), 1, 8


def strip(frame):
    out = frame.copy()
    out[COUNTER_ROW] = 0
    return out.tobytes()


def main(events_path, out_path):
    recs = next(v for k, v in records.load_run(events_path).items() if k.startswith('tn36'))['records']
    requests = []
    with open(events_path) as handle:
        for line in handle:
            if '"model_entered"' in line and 'tn36' in line[:300]:
                event = json.loads(line)
                if event['attempt'] == 0:
                    requests.append(json.loads(event['request']['messages'][1]['content'])['evidence'])
    chosen = [r for r in recs if r['action']['id'] != 'RESET']  # request k chose chosen[k]
    request_for = {r['event_seq']: requests[k] for k, r in enumerate(chosen)}

    runs = [r for r in recs if (r['action']['x'], r['action']['y']) == RUN]
    rows, previous_run = [], 0
    for r in runs:
        same = [p for p in runs if p['event_seq'] < r['event_seq'] and strip(p['before_frame']) == strip(r['before_frame'])]
        evidence = request_for[r['event_seq']]
        cited = sorted({i for h in evidence['hypotheses'] for i in h.get('evidence_ids', [])})
        row = {'event': r['event_seq'], 'reset': r['reset_id'],
               'actions_spent_since_previous_run': r['event_seq'] - previous_run,
               'earlier_same_board_runs': [p['event_seq'] for p in same],
               'level_change': r['level_after'] > r['level_observed']}
        if same:
            latest = same[-1]
            row.update(
                same_frames_as_latest=(len(latest['response_frames']) == len(r['response_frames']) and all(
                    strip(a) == strip(b) for a, b in zip(latest['response_frames'], r['response_frames']))),
                latest_in_same_attempt=latest['reset_id'] == r['reset_id'],
                latest_still_shown=latest['event_seq'] >= r['event_seq'] - WINDOW,
                notes_citing_an_earlier_same_board_run=[
                    {'id': h['id'], 'status': h['status'], 'statement': h['statement'], 'evidence_ids': h['evidence_ids']}
                    for h in evidence['hypotheses']
                    if any(i in ('t%d' % p['event_seq'], 'o%d' % p['event_seq']) for p in same for i in h['evidence_ids'])],
                notes_given=[{'id': h['id'], 'status': h['status'], 'statement': h['statement'],
                              'evidence_ids': h['evidence_ids']} for h in evidence['hypotheses']],
                oldest_evidence_cited_in_notes=min((int(i[1:]) for i in cited if i[1:].isdigit()), default=None))
        rows.append(row)
        previous_run = r['event_seq']
    repeats = [x for x in rows if x['earlier_same_board_runs']]
    summary = {
        'actions_in_game': len(chosen), 'runs': len(runs), 'runs_repeating_an_earlier_board': len(repeats),
        'repeats_with_identical_frames': sum(x['same_frames_as_latest'] for x in repeats),
        'repeats_whose_latest_earlier_run_was_still_shown': sum(x['latest_still_shown'] for x in repeats),
        'repeats_in_same_attempt_not_shown': sum(x['latest_in_same_attempt'] and not x['latest_still_shown'] for x in repeats),
        'repeats_across_the_reset_not_shown': sum(not x['latest_in_same_attempt'] and not x['latest_still_shown'] for x in repeats),
        'repeats_not_shown_with_a_note_citing_an_earlier_same_board_run': sum(
            bool(x['notes_citing_an_earlier_same_board_run']) and not x['latest_still_shown'] for x in repeats),
        'actions_spent_on_repeats_not_shown': sum(x['actions_spent_since_previous_run'] for x in repeats if not x['latest_still_shown']),
        'any_run_changed_level': any(x['level_change'] for x in rows)}
    Path(out_path).write_text(json.dumps({'summary': summary, 'runs': rows}, indent=1))
    print(json.dumps(summary, indent=1))
    print('event reset cost earlier_same_board same_frames same_attempt shown notes_citing oldest_cited')
    for x in repeats:
        print(x['event'], x['reset'], x['actions_spent_since_previous_run'], x['earlier_same_board_runs'],
              x['same_frames_as_latest'], x['latest_in_same_attempt'], x['latest_still_shown'],
              [n['id'] + ':' + ','.join(n['evidence_ids']) for n in x['notes_citing_an_earlier_same_board_run']],
              x['oldest_evidence_cited_in_notes'])
    return rows


if __name__ == '__main__':
    rows = main(sys.argv[1], sys.argv[2])
    for event in (55, 98):
        row = next(x for x in rows if x['event'] == event)
        print('\nnotes given before the run at action %d:' % event)
        for n in row['notes_given']:
            print('  [%s] %s (%s)' % (n['status'][:4], n['statement'], ','.join(n['evidence_ids'])))
