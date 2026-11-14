"""Cross-game check of the shift-capable description rule (Q-key-v2) against the original (Q-key-v1).

Uses the same 500 decisions as the Phase 1 scorer-pair sample (20 per game, from scorer_pairs_v2.csv).
For each: scorer tokens under both rules, whether Q-key-v2 decodes back to the recent frames exactly, and
whether it is within the provisional 4,096-token description limit. Failures are kept.
Usage: q_key2_check.py <events.jsonl> <scorer_pairs_v2.csv> <out.json>
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from complete_evidence_v1 import formats_v2 as F, records  # noqa: E402
from complete_evidence_v1.m0_example import REVISION, SCORER  # noqa: E402

LIMIT = 4096


def main(events_path, pairs_csv, out_path):
    games = {k.split('-')[0]: v for k, v in records.load_run(events_path).items()}
    wanted = sorted({(r['game'], int(r['decision'])) for r in csv.DictReader(open(pairs_csv))})
    tok = Tokenizer.from_file(hf_hub_download(SCORER, 'tokenizer.json', revision=REVISION))
    tok.no_truncation()
    rows = []
    for game, decision in wanted:
        data = games[game]
        done = data['records'][:decision]
        current = done[-1]['response_frames'][-1]
        initial = np.asarray(data['initial']['frames'][-1], dtype=np.uint8)
        legal = done[-1]['legal_after']
        q2 = F.q_key2(initial, legal, done, 2)
        lossless = True
        for recent in done[-2:]:
            before, _, frames = F.decode(F.recent_q2(recent, current), current=current)
            lossless &= bool(np.array_equal(before, recent['before_frame']) and len(frames) == len(recent['response_frames'])
                             and all(a.shape == b.shape and np.array_equal(a, b) for a, b in zip(frames, recent['response_frames'])))
        rows.append({'game': game, 'decision': decision,
                     'recent_frames': [len(r['response_frames']) for r in done[-2:]],
                     'q1': len(tok.encode(F.q_key(initial, legal, done, 2), add_special_tokens=False).ids),
                     'q2': len(tok.encode(q2, add_special_tokens=False).ids), 'lossless': lossless,
                     'uses_shift': 'shifted' in q2})
    over = [r for r in rows if r['q2'] > LIMIT]
    by_game = {}
    for r in over:
        by_game.setdefault(r['game'], []).append(r['decision'])
    summary = {'decisions': len(rows), 'limit': LIMIT,
               'q1_within_limit': sum(r['q1'] <= LIMIT for r in rows), 'q2_within_limit': sum(r['q2'] <= LIMIT for r in rows),
               'q2_all_lossless': all(r['lossless'] for r in rows), 'q2_using_shift': sum(r['uses_shift'] for r in rows),
               'q1_median_max': [float(np.median([r['q1'] for r in rows])), max(r['q1'] for r in rows)],
               'q2_median_max': [float(np.median([r['q2'] for r in rows])), max(r['q2'] for r in rows)],
               'q2_over_limit_by_game': by_game,
               'q2_over_limit': sorted(over, key=lambda r: -r['q2'])}
    Path(out_path).write_text(json.dumps({'summary': summary, 'rows': rows}, indent=1))
    print(json.dumps({k: v for k, v in summary.items() if k != 'q2_over_limit'}, indent=1))
    for r in summary['q2_over_limit'][:25]:
        print(r)


if __name__ == '__main__':
    main(*sys.argv[1:4])
