"""Measure text sizes of the Appendix B formats on a saved run, in scoring-model tokens.

Usage: measure_sizes.py <events.jsonl> <out_dir>
Checks that every lossless format decodes back to the original cells, then writes per-record and
per-decision sizes. No truncation is applied anywhere.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np
from huggingface_hub import hf_hub_download, model_info
from tokenizers import Tokenizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from complete_evidence_v1 import formats, records  # noqa: E402

SCORER = 'BAAI/bge-reranker-v2-m3'
PAIR_LIMIT, QUERY_LIMIT, PAIR_SPECIAL = 2048, 768, 4  # <s> q </s></s> m </s>


def main(events_path, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    revision = model_info(SCORER).sha
    tok = Tokenizer.from_file(hf_hub_download(SCORER, 'tokenizer.json', revision=revision))
    tok.no_truncation()
    tok.no_padding()

    def n(text):
        return len(tok.encode(text, add_special_tokens=False).ids)

    games = records.load_run(events_path)
    cache = {}

    def board_tokens(frame, merge):
        key = (records.frame_id(frame), merge)
        if key not in cache:
            cache[key] = n('\n'.join(formats.board_lines(frame, merge)))
        return cache[key]

    rec_rows, dec_rows, mismatches = [], [], 0
    for game, data in sorted(games.items()):
        recs = data['records']
        initial = np.asarray(data['initial']['frames'][-1], dtype=np.uint8)
        for t in range(len(recs) + 1):  # decision t is taken after t completed records
            legal = recs[t - 1]['legal_after'] if t else data['initial']['available_actions']
            board = recs[t - 1]['response_frames'][-1] if t else initial
            row = {'game': game.split('-')[0], 'decision': t,
                   'board_rle': board_tokens(board, False), 'board_rle_r': board_tokens(board, True)}
            for policy in ('F-all', 'F-end'):
                for merge in (False, True):
                    row['q_%s%s' % (policy, '_r' if merge else '')] = n(
                        formats.q_exec(initial, legal, recs[:t], policy, 2, merge))
            dec_rows.append(row)
        for rec in recs:
            row = {'game': game.split('-')[0], 'event': rec['event_seq'], 'action': rec['action']['id'],
                   'frames': len(rec['response_frames']), 'level': rec['level_observed'],
                   'changed_final': int((rec['response_frames'][-1].shape != rec['before_frame'].shape)
                                        or (rec['response_frames'][-1] != rec['before_frame']).sum())}
            for policy in ('F-all', 'F-end'):
                for merge in (False, True):
                    text = formats.m_rle(rec, policy, merge)
                    before, frames = formats.parse_m_rle(text)
                    wanted = dict(enumerate(rec['response_frames'], 1))
                    if policy == 'F-end':
                        wanted = {len(wanted): wanted[len(wanted)]}
                    ok = np.array_equal(before, rec['before_frame']) and frames.keys() == wanted.keys() and all(
                        np.array_equal(frames[k], wanted[k]) for k in wanted)
                    mismatches += not ok
                    row['m_rle_%s%s' % (policy, '_r' if merge else '')] = n(text)
                row['m_diff_%s' % policy] = n(formats.m_diff(rec, policy))
            rec_rows.append(row)

    for name, rows in (('records.csv', rec_rows), ('decisions.csv', dec_rows)):
        with open(out_dir / name, 'w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def dist(values, limits):
        v = np.array(values)
        out = {'n': int(v.size), 'min': int(v.min()), 'median': float(np.median(v)),
               'p90': float(np.percentile(v, 90)), 'max': int(v.max())}
        out.update({'share_le_%d' % lim: round(float((v <= lim).mean()), 4) for lim in limits})
        return out

    memory_room = PAIR_LIMIT - QUERY_LIMIT - PAIR_SPECIAL
    summary = {'scorer': SCORER, 'scorer_revision': revision, 'events': str(events_path),
               'games': len(games), 'records': len(rec_rows), 'decisions': len(dec_rows),
               'reconstruction_mismatches': int(mismatches),
               'frames_per_response': dist([r['frames'] for r in rec_rows], []),
               'share_multi_frame': round(float(np.mean([r['frames'] > 1 for r in rec_rows])), 4),
               'description_tokens': {k: dist([r[k] for r in dec_rows], [QUERY_LIMIT])
                                      for k in dec_rows[0] if k not in ('game', 'decision')},
               'memory_tokens': {k: dist([r[k] for r in rec_rows], [memory_room, PAIR_LIMIT - PAIR_SPECIAL])
                                 for k in rec_rows[0] if k.startswith('m_')}}
    # Pairs that fit with no cutting: description within its limit and description + memory within the pair limit.
    pair = {}
    for q_key, m_key in (('q_F-all', 'm_rle_F-all'), ('q_F-end', 'm_rle_F-end'), ('q_F-all_r', 'm_rle_F-all_r'),
                         ('q_F-end_r', 'm_rle_F-end_r'), ('q_F-end_r', 'm_diff_F-all'),
                         ('board_rle_r', 'm_diff_F-all')):
        fit = total = 0
        for game in sorted({r['game'] for r in rec_rows}):
            mem = [r[m_key] for r in rec_rows if r['game'] == game]
            for d in (r for r in dec_rows if r['game'] == game):
                older = np.array(mem[:d['decision']])
                total += older.size
                if d[q_key] <= QUERY_LIMIT:
                    fit += int((older + d[q_key] + PAIR_SPECIAL <= PAIR_LIMIT).sum())
        pair['%s + %s' % (q_key, m_key)] = {'pairs': total, 'fit': fit, 'share': round(fit / total, 4)}
    summary['pairs_fit_without_cutting'] = pair
    summary['per_game_board_rle_r_median'] = {
        g: float(np.median([r['board_rle_r'] for r in dec_rows if r['game'] == g]))
        for g in sorted({r['game'] for r in dec_rows})}
    (out_dir / 'scorer_sizes.json').write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
