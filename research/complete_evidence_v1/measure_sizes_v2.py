"""Cross-game sizes of the revised formats, with the same fixed encoding rules for every game.

Usage: measure_sizes_v2.py <events.jsonl> <out_dir>
Scorer tokens: M-key-v1 for every record; for 20 random decisions per game and up to 10 random older
records each, the Q-key-v1 description and the M-key / M-ref / M-region records.
Opus tokens: the same 200 records as the first sample (8 per game, seed 20261113), each paired with a
random later decision, counted through the logged token-counting helper. The earlier formats are
re-counted through the same log so their payloads are on record too.
"""
import csv
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research'))
from complete_evidence_v1 import formats, formats_v2 as F, records  # noqa: E402
from complete_evidence_v1.m0_example import REVISION, SCORER  # noqa: E402
from complete_evidence_v1.opus_count import MODEL, OpusCounter  # noqa: E402

BUDGETS, SEED = (512, 1024, 2048), 20261113
LIMITS = ((768, 2048), (2048, 4096), (4096, 8192))


def dist(values, limits=()):
    v = np.array(values)
    out = {'n': int(v.size), 'min': int(v.min()), 'median': float(np.median(v)),
           'p90': float(np.percentile(v, 90)), 'max': int(v.max())}
    out.update({'share_le_%d' % lim: round(float((v <= lim).mean()), 4) for lim in limits})
    return out


def main(events_path, out_dir):
    out_dir = Path(out_dir)
    games = records.load_run(events_path)
    tok = Tokenizer.from_file(hf_hub_download(SCORER, 'tokenizer.json', revision=REVISION))
    tok.no_truncation()

    def n(text):
        return len(tok.encode(text, add_special_tokens=False).ids)

    summary = {'scorer': SCORER, 'scorer_revision': REVISION, 'opus_model': MODEL, 'seed': SEED}
    summary['scorer_m_key_all_records'] = dist([n(F.m_key(r)) for d in games.values() for r in d['records']], [1276, 2044])

    rng = random.Random(SEED + 1)
    pairs = []
    for game, data in sorted(games.items()):
        recs = data['records']
        initial = np.asarray(data['initial']['frames'][-1], dtype=np.uint8)
        for t in sorted(rng.sample(range(3, len(recs) + 1), 20)):
            done = recs[:t]
            current = done[-1]['response_frames'][-1]
            q = n(F.q_key(initial, done[-1]['legal_after'], done, 2))
            for e in sorted(rng.sample(range(1, t - 1), min(10, t - 2))):
                r = recs[e - 1]
                pairs.append({'game': game.split('-')[0], 'decision': t, 'event': e, 'q_key': q,
                              'M-key-v1': n(F.m_key(r)), 'M-ref-v1': n(F.m_ref(r, current)),
                              'M-region-v1': n(F.m_region(r, done)), 'M-ref-v1 F-end': n(F.m_ref(r, current, 'F-end'))})
    with open(out_dir / 'scorer_pairs_v2.csv', 'w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(pairs[0]))
        writer.writeheader()
        writer.writerows(pairs)
    decisions = {(p['game'], p['decision']): p['q_key'] for p in pairs}
    summary['scorer_description_q_key'] = dist(list(decisions.values()), [768, 2048, 4096])
    summary['scorer_pairs'] = {'pairs': len(pairs), 'decisions': len(decisions)}
    for name in ('M-key-v1', 'M-ref-v1', 'M-region-v1', 'M-ref-v1 F-end'):
        entry = dist([p[name] for p in pairs])
        for q_lim, pair_lim in LIMITS:
            entry['pairs_fit_%d_%d' % (q_lim, pair_lim)] = round(float(np.mean(
                [p['q_key'] <= q_lim and p['q_key'] + p[name] + 4 <= pair_lim for p in pairs])), 4)
        summary['scorer_pairs'][name] = entry

    # Opus sample: same records as measure_opus_sizes.py
    counter = OpusCounter()
    rng = random.Random(SEED)
    rows, jobs = [], []
    for game, data in sorted(games.items()):
        recs = data['records']
        for rec in sorted(rng.sample(recs, 8), key=lambda r: r['event_seq']):
            rows.append({'game': game.split('-')[0], 'event': rec['event_seq'], 'frames': len(rec['response_frames']),
                         '_rec': rec, '_recs': recs})
    pick = random.Random(SEED + 2)
    for row in rows:
        rec, recs = row.pop('_rec'), row.pop('_recs')
        t = pick.randint(min(rec['event_seq'] + 2, len(recs)), len(recs))
        row['decision'] = t
        current = recs[t - 1]['response_frames'][-1]
        texts = {'M-key-v1': F.m_key(rec), 'M-ref-v1': F.m_ref(rec, current), 'M-region-v1': F.m_region(rec, recs[:t]),
                 'M-key-v1 F-end': F.m_key(rec, 'F-end'), 'M-ref-v1 F-end': F.m_ref(rec, current, 'F-end'),
                 'm_rle_F-all': formats.m_rle(rec, 'F-all'), 'm_rle_F-all_r': formats.m_rle(rec, 'F-all', True),
                 'm_rle_F-end': formats.m_rle(rec, 'F-end'), 'm_rle_F-end_r': formats.m_rle(rec, 'F-end', True),
                 'm_diff_F-all': formats.m_diff(rec, 'F-all'), 'm_diff_F-end': formats.m_diff(rec, 'F-end'),
                 'board_rle': '\n'.join(formats.board_lines(rec['before_frame'])),
                 'board_rle_r': '\n'.join(formats.board_lines(rec['before_frame'], True)),
                 'board_hex': '\n'.join(''.join(formats.HEX[v] for v in r) for r in rec['before_frame'])}
        before, known, _ = F.decode(texts['M-region-v1'], shape=rec['before_frame'].shape)
        row['region_cells_given'] = round(float(known.mean()), 3)
        jobs += [(row, key, text) for key, text in texts.items()]
    with ThreadPoolExecutor(4) as pool:
        for (row, key, _), value in zip(jobs, pool.map(
                lambda j: counter.count(j[2], '%s e%d %s' % (j[0]['game'], j[0]['event'], j[1])), jobs)):
            row[key] = value
    with open(out_dir / 'opus_sample_v2.csv', 'w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    old = {(r['game'], r['event']): r for r in csv.DictReader(open(out_dir / 'opus_sample.csv'))}
    summary['earlier_counts_reproduced'] = all(
        int(old[(r['game'], str(r['event']))][k]) == r[k] for r in rows
        for k in ('m_rle_F-all', 'm_rle_F-all_r', 'm_rle_F-end', 'm_rle_F-end_r', 'm_diff_F-all', 'm_diff_F-end',
                  'board_rle', 'board_rle_r', 'board_hex'))
    summary['opus_sample'] = {'records': len(rows), 'note_tokens': {
        k: counter.count(v, 'reading note ' + k) for k, v in F.READING_NOTES.items()}}
    for name in ('M-key-v1', 'M-ref-v1', 'M-region-v1', 'M-key-v1 F-end', 'M-ref-v1 F-end'):
        summary['opus_sample'][name] = dist([r[name] for r in rows], BUDGETS)
    summary['opus_sample']['M-region-v1']['cells_given_median'] = float(np.median([r['region_cells_given'] for r in rows]))
    by_game = {}
    for g in sorted({r['game'] for r in rows}):
        v = [r['M-ref-v1'] for r in rows if r['game'] == g]
        by_game[g] = {'median': float(np.median(v)), 'fit_1024': sum(x <= 1024 for x in v), 'of': len(v)}
    summary['opus_m_ref_by_game'] = by_game
    (out_dir / 'sizes_v2.json').write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
