"""Exact Opus token counts for a random sample of records, from the free token-counting endpoint.

Usage: measure_opus_sizes.py <events.jsonl> <out_dir> [per_game=8] [seed=20261113]
Reads ANTHROPIC_API_KEY from the repository .env. Only public board text is sent. No model is run.
"""
import csv
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research'))
from complete_evidence_v1 import formats, records  # noqa: E402

MODEL = 'claude-opus-5-5'
LIMITS = (512, 1024, 2048)


def api_key():
    for line in (ROOT / '.env').read_text().splitlines():
        if line.startswith('ANTHROPIC_API_KEY='):
            return line.split('=', 1)[1].strip().strip('"\'')
    raise SystemExit('no ANTHROPIC_API_KEY in .env')


def main(events_path, out_dir, per_game=8, seed=20261113):
    out_dir = Path(out_dir)
    client = anthropic.Anthropic(api_key=api_key(), max_retries=6)

    def count(text):
        try:
            return client.messages.count_tokens(
                model=MODEL, messages=[{'role': 'user', 'content': text}]).input_tokens
        except anthropic.BadRequestError as error:  # for example a record too long for the model
            return 'error: %s' % str(error)[:80]

    rng = random.Random(seed)
    jobs, rows = [], []
    for game, data in sorted(records.load_run(events_path).items()):
        for rec in sorted(rng.sample(data['records'], per_game), key=lambda r: r['event_seq']):
            row = {'game': game.split('-')[0], 'event': rec['event_seq'], 'frames': len(rec['response_frames'])}
            rows.append(row)
            texts = {'m_rle_F-all': formats.m_rle(rec, 'F-all'), 'm_rle_F-all_r': formats.m_rle(rec, 'F-all', True),
                     'm_rle_F-end': formats.m_rle(rec, 'F-end'), 'm_rle_F-end_r': formats.m_rle(rec, 'F-end', True),
                     'm_diff_F-all': formats.m_diff(rec, 'F-all'), 'm_diff_F-end': formats.m_diff(rec, 'F-end'),
                     'board_rle': '\n'.join(formats.board_lines(rec['before_frame'])),
                     'board_rle_r': '\n'.join(formats.board_lines(rec['before_frame'], True)),
                     'board_hex': '\n'.join(''.join(formats.HEX[v] for v in r) for r in rec['before_frame'])}
            for key, text in texts.items():
                row[key + '_chars'] = len(text)
                jobs.append((row, key, text))
    overhead = count('x')
    note = count(formats.READING_NOTE)
    with ThreadPoolExecutor(4) as pool:
        for (row, key, _), value in zip(jobs, pool.map(lambda j: count(j[2]), jobs)):
            row[key] = value
    with open(out_dir / 'opus_sample.csv', 'w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {'model': MODEL, 'sample_records': len(rows), 'per_game': per_game, 'seed': seed,
               'one_character_message_tokens': overhead, 'reading_note_tokens': note, 'formats': {}}
    for key in [k for k in rows[0] if k not in ('game', 'event', 'frames') and not k.endswith('_chars')]:
        good = np.array([r[key] for r in rows if isinstance(r[key], int)])
        entry = {'counted': int(good.size), 'errors': len(rows) - int(good.size), 'min': int(good.min()),
                 'median': float(np.median(good)), 'p90': float(np.percentile(good, 90)), 'max': int(good.max())}
        for limit in LIMITS:  # a record that could not be counted does not fit
            entry['share_le_%d' % limit] = round(float((good <= limit).sum()) / len(rows), 4)
        summary['formats'][key] = entry
    (out_dir / 'opus_sizes.json').write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], *[int(a) for a in sys.argv[3:5]])
