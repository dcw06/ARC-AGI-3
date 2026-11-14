"""Revised-format check on saved decisions: does the needed evidence survive within the Opus budgets?

Usage: m0_revised.py <events.jsonl> <game> <out_dir> <decision>:<needed>[,<needed>...] ...
`decision` is the number of completed actions; each `needed` event is, on its own, a record a reviewer
would accept as sufficient (my guess, unreviewed). The guesses are used only for reporting.
Opus budgets stay at 512 / 1,024 / 2,048. The scorer pair limit tested is 8,192 with 4,096 for the
description. No Opus request is made.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research'))
from complete_evidence_v1 import formats, formats_v2 as F, records  # noqa: E402
from complete_evidence_v1.m0_example import LAMBDA, REVISION, SCORER, relative_rank, select  # noqa: E402
from complete_evidence_v1.opus_count import MODEL, OpusCounter  # noqa: E402

WINDOW, BUDGETS, Q_LIMIT, PAIR_LIMIT = 2, (512, 1024, 2048), 4096, 8192
# Cells a reviewer must be able to read to see the earlier setting (rows y0-y1, columns x0-x1). tn36: the
# switch panel.
STATE_AREA = {'tn36': (41, 47, 19, 43)}


def preserved(text, record, current, area):
    """What the delivered text lets a reader reconstruct."""
    before, known, frames = F.decode(text, current=current, shape=record['before_frame'].shape)
    real = record['before_frame']
    out = {'board_cells_given': round(float(known.mean()), 3),
           'given_cells_correct': bool(np.array_equal(before[known], real[known])),
           'all_frames_present': len(frames) == len(record['response_frames'])}
    last, real_last = frames[-1], record['response_frames'][-1]
    cells = known | (real_last != real)
    out['last_frame_correct_where_given'] = bool(np.array_equal(last[cells], real_last[cells]))
    out['outcome_fields_present'] = 'result state=%s level=%d' % (record['state_after'], record['level_after']) in text
    if area:
        y0, y1, x0, x1 = area
        out['state_area_fully_given'] = bool(known[y0:y1 + 1, x0:x1 + 1].all())
        out['state_area_correct'] = bool(np.array_equal(before[y0:y1 + 1, x0:x1 + 1][known[y0:y1 + 1, x0:x1 + 1]],
                                                        real[y0:y1 + 1, x0:x1 + 1][known[y0:y1 + 1, x0:x1 + 1]]))
    return out


def main(events_path, game, out_dir, specs):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = next(v for k, v in records.load_run(events_path).items() if k.startswith(game))
    recs = data['records']
    initial = np.asarray(data['initial']['frames'][-1], dtype=np.uint8)
    counter = OpusCounter()
    tok = AutoTokenizer.from_pretrained(SCORER, revision=REVISION)
    device = 'mps' if torch.backends.mps.is_available() else 'cpu'
    model = AutoModelForSequenceClassification.from_pretrained(SCORER, revision=REVISION).to(device).eval()
    notes = {name: counter.count(text, 'reading note ' + name) for name, text in F.READING_NOTES.items()}
    report = {'game': game, 'opus_model': MODEL, 'scorer': SCORER, 'scorer_revision': REVISION, 'device': device,
              'budgets': BUDGETS, 'scorer_limits': {'description': Q_LIMIT, 'pair': PAIR_LIMIT},
              'reading_note_opus_tokens': notes, 'selection': 'relative rank, lambda %.2f, sim-v0 (provisional)' % LAMBDA,
              'opus_response': 'saved-input-only (no request made)', 'decisions': []}
    for spec in specs:
        decision, needed = spec.split(':')
        decision, needed = int(decision), [int(e) for e in needed.split(',')]
        done = recs[:decision]
        current = done[-1]['response_frames'][-1]
        older = done[:-WINDOW]
        query = F.q_key(initial, done[-1]['legal_after'], done, WINDOW)
        q_len = len(tok(query, add_special_tokens=False)['input_ids'])
        tag = 'd%d' % decision
        (out_dir / ('%s_description.txt' % tag)).write_text(query)
        entry = {'decision': decision, 'next_event': decision + 1, 'action_taken': recs[decision]['action'],
                 'needed_events_unreviewed_guess': needed, 'older_candidates': len(older),
                 'description_scorer_tokens': q_len, 'description_fits_768': q_len <= 768,
                 'description_fits_%d' % Q_LIMIT: q_len <= Q_LIMIT, 'formats': {}}
        builders = {'M-key-v1': lambda r: F.m_key(r), 'M-ref-v1': lambda r: F.m_ref(r, current),
                    'M-region-v1': lambda r: F.m_region(r, done)}
        for name, build in builders.items():
            texts = [build(r) for r in older]
            rows, scores = [], []
            start = time.time()
            for r, text in zip(older, texts):
                enc = tok(query, text, truncation=False, return_tensors='pt')
                n = int(enc['input_ids'].shape[1])
                row = {'event': r['event_seq'], 'pair_tokens': n, 'accepted': q_len <= Q_LIMIT and n <= PAIR_LIMIT,
                       'fits_starting_limits': q_len <= 768 and n <= 2048}
                if row['accepted']:
                    with torch.no_grad():
                        row['score'] = model(**{k: v.to(device) for k, v in enc.items()}).logits.float().view(-1)[0].item()
                row['opus_tokens'] = counter.count(text, '%s %s %s e%d' % (game, tag, name, r['event_seq']))
                rows.append(row)
            seconds = time.time() - start
            ok = [i for i, row in enumerate(rows) if row['accepted']]
            scores = [rows[i]['score'] for i in ok]
            rank = relative_rank(scores)
            for position, j in enumerate(sorted(range(len(ok)), key=lambda j: -scores[j]), 1):
                rows[ok[j]]['rank'] = position
            cost = [rows[i]['opus_tokens'] for i in ok]
            by_event = {r['event_seq']: t for r, t in zip(older, texts)}
            fmt = {'pairs': len(rows), 'pairs_accepted': len(ok),
                   'pairs_within_starting_limits': sum(row['fits_starting_limits'] for row in rows),
                   'pair_tokens_median_max': [float(np.median([row['pair_tokens'] for row in rows])),
                                              max(row['pair_tokens'] for row in rows)],
                   'record_opus_tokens_min_median_max': [min(cost), float(np.median(cost)), max(cost)],
                   'records_fitting_alone': {str(b): sum(c <= b for c in cost) for b in BUDGETS},
                   'score_min_median_max': [round(min(scores), 3), round(float(np.median(scores)), 3), round(max(scores), 3)],
                   'scoring_seconds': round(seconds, 1), 'needed': {}, 'u_selection': {}}
            for e in needed:
                row = next(x for x in rows if x['event'] == e)
                record = recs[e - 1]
                pack = F.READING_NOTES[name] + '\n\n' + by_event[e]
                (out_dir / ('%s_%s_needed_e%d.txt' % (tag, name, e))).write_text(pack)
                fmt['needed'][str(e)] = {
                    'u_rank': row.get('rank'), 'record_opus_tokens': row['opus_tokens'],
                    'pack_with_reading_note_opus_tokens': counter.count(pack, '%s %s %s needed pack e%d' % (game, tag, name, e)),
                    'record_fits': {str(b): row['opus_tokens'] <= b for b in BUDGETS},
                    'preserved': preserved(by_event[e], record, current, STATE_AREA.get(game))}
            for budget in BUDGETS:
                chosen, used, _ = select([older[i] for i in ok], rank, cost, budget)
                fmt['u_selection'][str(budget)] = {'selected_events': chosen, 'opus_tokens_used': used,
                                                   'needed_included': [e for e in needed if e in chosen]}
                (out_dir / ('%s_%s_u_pack_%d.txt' % (tag, name, budget))).write_text(
                    F.READING_NOTES[name] + '\n\n' + '\n\n'.join(by_event[e] for e in sorted(chosen)))
            fmt['rows'] = rows
            entry['formats'][name] = fmt
        # the earlier formats, counted through the same log so every reported number has its payload on record
        old = {'M-rle-v1 F-all': lambda r: formats.m_rle(r, 'F-all'),
               'M-rle-v1r F-end': lambda r: formats.m_rle(r, 'F-end', True),
               'M-diff-v1 F-all': lambda r: formats.m_diff(r, 'F-all'),
               'M-diff-v1 F-end': lambda r: formats.m_diff(r, 'F-end')}
        entry['earlier_formats_needed_record_opus_tokens'] = {
            name: {str(e): counter.count(build(recs[e - 1]), '%s %s %s e%d' % (game, tag, name, e)) for e in needed}
            for name, build in old.items()}
        report['decisions'].append(entry)
    (out_dir / 'm0_revised.json').write_text(json.dumps(report, indent=1))
    for entry in report['decisions']:
        print('\ndecision', entry['decision'], 'needed', entry['needed_events_unreviewed_guess'],
              'description tokens', entry['description_scorer_tokens'])
        print(' earlier formats:', entry['earlier_formats_needed_record_opus_tokens'])
        for name, fmt in entry['formats'].items():
            print(' ', name, {k: v for k, v in fmt.items() if k not in ('rows', 'needed', 'u_selection')})
            for e, v in fmt['needed'].items():
                print('    needed', e, v)
            for b, v in fmt['u_selection'].items():
                print('    U at', b, v)
    print(report['reading_note_opus_tokens'])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
