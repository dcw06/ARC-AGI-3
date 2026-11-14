"""Apply the fixed A and B encoding rules to the 20 frozen development cases and measure them.

A = M-key-v1, B = M-ref-v1, both with reading instructions version 2, exactly as in the readability
rehearsal. No case-specific changes are made; every failure is kept. No Opus request is made: Opus
token counts come from the free token-counting endpoint and are logged with their payloads.

Usage: dev_format_check.py <events.jsonl> <cases_frozen.json> <out_dir>
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research'))
from complete_evidence_v1 import formats_v2 as F, records  # noqa: E402
from complete_evidence_v1.m0_example import REVISION, SCORER  # noqa: E402
from complete_evidence_v1.opus_count import MODEL, OpusCounter  # noqa: E402

BUDGETS = (512, 1024, 2048)
SCORER_LIMITS = {'proposed': (768, 2048), 'tested': (4096, 8192)}  # (description, pair)
PAIR_SPECIAL = 4


def rendered_pack(name, game, run, decision, recs_chosen, texts):
    events = [r['event_seq'] for r in recs_chosen]
    many = len(events) > 1
    lines = ['== OLDER MEMORY ==',
             'Source: game %s, saved run %s, action%s %s (transition%s %s). %s, selected by rule.' % (
                 game, run, 's' if many else '', ' and '.join(map(str, events)), 's' if many else '',
                 ', '.join('t%d' % e for e in events), '%d records' % len(events) if many else 'One record')]
    if name == 'B':
        lines.append('In %s "current" means the current board given above, observation o%d: the board before '
                     '%s is rebuilt from o%d.' % ('these records' if many else 'this record', decision,
                                                   'each action' if many else 'this action', decision))
    lines += [F.READING_NOTES_V2['M-key-v1' if name == 'A' else 'M-ref-v1'], '', '\n\n'.join(texts)]
    return '\n'.join(lines)


def main(events_path, cases_path, out_dir):
    out_dir = Path(out_dir)
    (out_dir / 'packs').mkdir(parents=True, exist_ok=True)
    frozen = json.loads(Path(cases_path).read_text())
    games = {k.split('-')[0]: v for k, v in records.load_run(events_path).items()}
    counter = OpusCounter()
    tok = Tokenizer.from_file(hf_hub_download(SCORER, 'tokenizer.json', revision=REVISION))
    tok.no_truncation()

    def scorer_tokens(text):
        return len(tok.encode(text, add_special_tokens=False).ids)

    results = []
    for case in frozen['cases']:
        if case.get('unfilled'):
            results.append(case)
            continue
        game, decision = case['game'], case['decision_after_actions']
        data = games[game]
        recs = data['records']
        done = recs[:decision]
        current = done[-1]['response_frames'][-1]
        assert hashlib.sha256(current.tobytes()).hexdigest() == case['current_board_cells_sha256']
        initial = np.asarray(data['initial']['frames'][-1], dtype=np.uint8)
        description = scorer_tokens(F.q_key(initial, done[-1]['legal_after'], done, 2))
        chosen = [recs[e['event'] - 1] for e in case['earlier_records']]
        row = {k: case[k] for k in ('case', 'type', 'game', 'decision_after_actions')}
        row.update(reference_board={'observation': case['current_board_observation'],
                                    'cells_sha256': case['current_board_cells_sha256']},
                   description_scorer_tokens=description,
                   description_fits={k: description <= v[0] for k, v in SCORER_LIMITS.items()}, records=[], formats={})
        texts = {'A': [F.m_key(r) for r in chosen], 'B': [F.m_ref(r, current) for r in chosen]}
        for i, r in enumerate(chosen):
            entry = {'event': r['event_seq'], 'frames': len(r['response_frames']),
                     'share_of_board_differing_from_current': case['earlier_records'][i]['share_of_board_differing']}
            for name in ('A', 'B'):
                text = texts[name][i]
                try:
                    before, _, frames = F.decode(text, current=current if name == 'B' else None)
                    ok = (np.array_equal(before, r['before_frame']) and len(frames) == len(r['response_frames'])
                          and all(a.shape == b.shape and np.array_equal(a, b) for a, b in zip(frames, r['response_frames'])))
                except Exception as error:  # a decoding error is a failure to record, not to hide
                    ok = False
                    entry['%s_decode_error' % name] = repr(error)[:200]
                pair = description + scorer_tokens(text) + PAIR_SPECIAL
                entry[name] = {'reconstructs_all_frames': bool(ok),
                               'opus_tokens': counter.count(text, 'format check %s %s e%d' % (case['case'], name, r['event_seq'])),
                               'scorer_record_tokens': scorer_tokens(text), 'scorer_pair_tokens': pair,
                               'pair_fits': {k: description <= v[0] and pair <= v[1] for k, v in SCORER_LIMITS.items()}}
                entry[name]['fits_alone'] = {str(b): entry[name]['opus_tokens'] <= b for b in BUDGETS}
            third = texts['B'][i].split('\n')[2]
            entry['B_earlier_board_given_as'] = ('same as current' if 'same as current' in third else
                                                 'differences from current' if ' vs current' in third else 'full board (fallback)')
            row['records'].append(entry)
        for name in ('A', 'B'):
            pack = rendered_pack(name, game, chosen[0]['trajectory_id'], decision, chosen, texts[name])
            (out_dir / 'packs' / ('%s_%s.txt' % (case['case'], name))).write_text(pack + '\n')
            tokens = counter.count(pack, 'format check %s pack %s' % (case['case'], name))
            row['formats'][name] = {'pack_opus_tokens': tokens, 'pack_fits': {str(b): tokens <= b for b in BUDGETS},
                                    'records_opus_tokens': sum(e[name]['opus_tokens'] for e in row['records']),
                                    'all_records_reconstruct': all(e[name]['reconstructs_all_frames'] for e in row['records']),
                                    'all_pairs_fit': {k: all(e[name]['pair_fits'][k] for e in row['records']) for k in SCORER_LIMITS},
                                    'pack_sha256': hashlib.sha256(pack.encode()).hexdigest()}
        results.append(row)
    summary = {'opus_model': MODEL, 'scorer': SCORER, 'scorer_revision': REVISION, 'budgets': BUDGETS,
               'scorer_limits_description_pair': SCORER_LIMITS, 'reading_instructions_version': 2,
               'cases_file_sha256': hashlib.sha256(Path(cases_path).read_bytes()).hexdigest(),
               'counts_are_estimates': True, 'opus_requests_sent': 0, 'cases': results}
    (out_dir / 'results.json').write_text(json.dumps(summary, indent=1))
    print('case type game dec | frames | A rec/pack  B rec/pack | A fits 512/1024/2048 | B fits | B mode | recon A/B | desc | pairs prop/tested A, B')
    for r in results:
        if r.get('unfilled'):
            continue
        a, b = r['formats']['A'], r['formats']['B']
        fit = lambda f: ''.join('Y' if f['pack_fits'][str(x)] else '-' for x in BUDGETS)  # noqa: E731
        print(r['case'], r['type'][:5], r['game'], r['decision_after_actions'], '|', [e['frames'] for e in r['records']], '|',
              a['records_opus_tokens'], a['pack_opus_tokens'], ' ', b['records_opus_tokens'], b['pack_opus_tokens'], '|',
              fit(a), '|', fit(b), '|', [e['B_earlier_board_given_as'][:4] for e in r['records']], '|',
              a['all_records_reconstruct'], b['all_records_reconstruct'], '|', r['description_scorer_tokens'], '|',
              a['all_pairs_fit'], b['all_pairs_fit'])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
