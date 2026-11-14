"""Write a small cross-game packet of delivered records for human reading.

Games: the three development games named in the protocol (bp35, lf52, ls20) and the three games besides
tn36 where the repeat audit could assess an action (cd82, ka59, vc33). For each, the record from the Opus
size sample whose M-ref-v1 size is the game's lower median. Nothing is chosen by how well any method did.
Usage: make_packet.py <events.jsonl> <report_dir>
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research'))
from complete_evidence_v1 import formats_v2 as F, records  # noqa: E402
from complete_evidence_v1.opus_count import OpusCounter  # noqa: E402

GAMES = ('bp35', 'lf52', 'ls20', 'cd82', 'ka59', 'vc33')


def main(events_path, report_dir):
    report_dir = Path(report_dir)
    out = report_dir / 'interpretability_packet'
    out.mkdir(exist_ok=True)
    sample = list(csv.DictReader(open(report_dir / 'data/opus_sample_v2.csv')))
    games = {k.split('-')[0]: v for k, v in records.load_run(events_path).items()}
    counter = OpusCounter()
    index = ['# Reading packet: delivered records from six games', '',
             'For each record a reviewer should answer from the text alone, before opening anything else:',
             'what was the board state that mattered, what did the action do, and what is missing or misleading?',
             'M-ref-v1 must be read together with the current board of its decision (`*_current_board.txt`).', '',
             '| Game | Record | Decision | Frames | M-key-v1 | M-ref-v1 | M-region-v1 | Region cells given |',
             '|---|---|---|---|---|---|---|---|']
    for game in GAMES:
        rows = sorted((r for r in sample if r['game'] == game), key=lambda r: int(r['M-ref-v1']))
        row = rows[(len(rows) - 1) // 2]
        recs = games[game]['records']
        event, decision = int(row['event']), int(row['decision'])
        rec, current = recs[event - 1], recs[decision - 1]['response_frames'][-1]
        texts = {'M-key-v1': F.m_key(rec), 'M-ref-v1': F.m_ref(rec, current), 'M-region-v1': F.m_region(rec, recs[:decision])}
        stem = '%s_e%d_d%d' % (game, event, decision)
        sizes = []
        for name, text in texts.items():
            (out / ('%s_%s.txt' % (stem, name))).write_text(F.READING_NOTES[name] + '\n\n' + text + '\n')
            sizes.append(counter.count(text, 'packet %s %s' % (stem, name)))
            assert sizes[-1] == int(row[name])
        (out / ('%s_current_board.txt' % stem)).write_text('\n'.join(F.board_lines(current, True)) + '\n')
        index.append('| %s | %d | %d | %s | %d | %d | %d | %.0f%% |' % (
            game, event, decision, row['frames'], sizes[0], sizes[1], sizes[2], 100 * float(row['region_cells_given'])))
    index += ['', 'Sizes are Opus tokens for the record alone (estimates from the token-counting endpoint).',
              'No reviewer has read these yet.']
    (out / 'README.md').write_text('\n'.join(index) + '\n')
    print('\n'.join(index))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
