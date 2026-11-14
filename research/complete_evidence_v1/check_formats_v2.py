"""Check that the revised formats decode back to the original cells.

M-key: every record. M-ref and M-region: `pairs` random (decision, older record) pairs per game.
For M-region the check covers the cells the text gives; the share of cells given is reported.
Usage: check_formats_v2.py <events.jsonl> [pairs=40] [seed=1]
"""
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from complete_evidence_v1 import formats_v2 as F, records  # noqa: E402


def same_frames(decoded, real):
    return len(decoded) == len(real) and all(a.shape == b.shape and np.array_equal(a, b) for a, b in zip(decoded, real))


def main(events_path, pairs=40, seed=1):
    rng = random.Random(seed)
    bad = {'M-key-v1': 0, 'M-ref-v1': 0, 'M-region-v1': 0}
    count = dict.fromkeys(bad, 0)
    given = []
    for _, data in sorted(records.load_run(events_path).items()):
        recs = data['records']
        for r in recs:
            before, _, frames = F.decode(F.m_key(r))
            count['M-key-v1'] += 1
            bad['M-key-v1'] += not (np.array_equal(before, r['before_frame']) and same_frames(frames, r['response_frames']))
        for _ in range(pairs):
            t = rng.randint(3, len(recs))
            r = recs[rng.randint(1, t - 2) - 1]
            current = recs[t - 1]['response_frames'][-1]
            before, _, frames = F.decode(F.m_ref(r, current), current=current)
            count['M-ref-v1'] += 1
            bad['M-ref-v1'] += not (np.array_equal(before, r['before_frame']) and same_frames(frames, r['response_frames']))
            before, known, frames = F.decode(F.m_region(r, recs[:t]), shape=r['before_frame'].shape)
            ok = np.array_equal(before[known], r['before_frame'][known]) and len(frames) == len(r['response_frames'])
            for got, real in zip(frames, r['response_frames']):
                if ok and real.shape == r['before_frame'].shape:
                    cells = known | (real != r['before_frame'])
                    ok = got.shape == real.shape and np.array_equal(got[cells], real[cells])
            count['M-region-v1'] += 1
            bad['M-region-v1'] += not ok
            given.append(float(known.mean()))
    print('checked', count, 'mismatches', bad)
    print('M-region share of board cells given: median %.2f, 10th pct %.2f, min %.2f' % (
        np.median(given), np.percentile(given, 10), min(given)))
    return bad


if __name__ == '__main__':
    result = main(sys.argv[1], *[int(a) for a in sys.argv[2:4]])
    sys.exit(1 if any(result.values()) else 0)
