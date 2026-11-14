"""Prepare the materials for the two-role agent review of the 12 frozen full-history cases.

Role 1 (evidence needed): stage 1 gets only the decision-time input; stage 2 gets the complete history up
to the decision as an index, change lists, board text and pictures. It never gets a pack or a type label.
Role 2 (pack reader): gets only the decision-time input, a picture of the current board, the B version 2
pack, and probe questions about named cells. It never gets the history.
The probe answers and per-frame facts go into a sealed key, computed from the original frames.

Usage: agent_review_prep.py <events.jsonl> <cases_frozen.json> <format_check_v2_dir> <out_dir>
"""
import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research'))
from complete_evidence_v1 import records  # noqa: E402
from complete_evidence_v1.review_packet import PALETTE, action_text, changed_runs, decision_input, hex_rows  # noqa: E402

SEED, SCALE, PER_ROW = 20261128, 4, 8
RGB = [tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in PALETTE]
HEX = '0123456789abcdef'


def tile(frame):
    rgb = np.array(RGB, dtype=np.uint8)[frame]
    return Image.fromarray(rgb, 'RGB').resize((frame.shape[1] * SCALE, frame.shape[0] * SCALE), Image.NEAREST)


def sheet(frames, captions):
    w, h = frames[0].shape[1] * SCALE, frames[0].shape[0] * SCALE
    rows = (len(frames) + PER_ROW - 1) // PER_ROW
    image = Image.new('RGB', (min(len(frames), PER_ROW) * (w + 6) + 6, rows * (h + 18) + 6), (238, 240, 243))
    draw = ImageDraw.Draw(image)
    for i, (frame, caption) in enumerate(zip(frames, captions)):
        x, y = 6 + (i % PER_ROW) * (w + 6), 6 + (i // PER_ROW) * (h + 18)
        if frame.shape == frames[0].shape:
            image.paste(tile(frame), (x, y))
        draw.text((x, y + h + 2), caption, fill=(20, 30, 45))
    return image


def box(mask):
    ys, xs = np.nonzero(mask)
    return 'none' if not len(ys) else 'x%d-%d y%d-%d' % (xs.min(), xs.max(), ys.min(), ys.max())


def history_files(done, folder):
    (folder / 'images').mkdir(parents=True, exist_ok=True)
    (folder / 'boards').mkdir(exist_ok=True)
    index = ['One line per past action, oldest first. "last frame vs before" compares the last returned frame with the '
             'board before that action. Pictures: images/aNNN.png shows the board before, then every returned frame, '
             'left to right and top to bottom. boards/aNNN.txt has the board before and the last frame as text.', '']
    changes = ['Changes per action. Runs are [x_first, x_last, y, colour_before, colour_after]. Each frame is compared '
               'with the one before it (frame 1 with the board before the action).', '']
    for r in done:
        before, frames = r['before_frame'], r['response_frames']
        tag = 'a%03d' % r['event_seq']
        same = all(f.shape == before.shape for f in frames)
        last = int((frames[-1] != before).sum()) if same else -1
        peak = max(int((f != before).sum()) for f in frames) if same else -1
        index.append('%s | %s | level %d attempt %d | %d frame%s | last frame vs before: %s cells changed, box %s | '
                     'largest change in any frame: %s cells | after: %s, levels completed %d' % (
                         tag, action_text(r['action']), r['level_observed'], r['reset_id'] + 1, len(frames),
                         '' if len(frames) == 1 else 's', last if same else 'board size changed',
                         box(frames[-1] != before) if same else '-', peak if same else '-', r['state_after'], r['level_after']))
        changes.append('%s %s (%d frames)' % (tag, action_text(r['action']), len(frames)))
        previous = before
        for k, frame in enumerate(frames, 1):
            runs = changed_runs(previous, frame)
            n = int((frame != previous).sum()) if frame.shape == previous.shape else -1
            shown = json.dumps(runs, separators=(',', ':')) if isinstance(runs, list) and len(runs) <= 40 else \
                '(too many runs to list: see the picture)'
            changes.append('  frame %d/%d: %s cells differ from the frame before it %s' % (k, len(frames), n, shown))
            previous = frame
        if len(frames) > 1 and same:
            runs = changed_runs(before, frames[-1])
            changes.append('  last frame vs board before the action: %d cells %s' % (
                last, json.dumps(runs, separators=(',', ':')) if isinstance(runs, list) and len(runs) <= 40 else '(too many runs to list)'))
        sheet([before] + list(frames), ['before'] + ['f%d' % k for k in range(1, len(frames) + 1)]).save(folder / 'images' / (tag + '.png'))
        (folder / 'boards' / (tag + '.txt')).write_text(
            'Board before action %d:\n' % r['event_seq'] + '\n'.join(hex_rows(before))
            + '\n\nLast returned frame (%d of %d):\n' % (len(frames), len(frames)) + '\n'.join(hex_rows(frames[-1])) + '\n')
    (folder / 'history_index.txt').write_text('\n'.join(index) + '\n')
    (folder / 'history_changes.txt').write_text('\n'.join(changes) + '\n')


def probes_for(record, current, rng):
    """Cells to ask about, chosen from the frames by a fixed rule. Returns (questions, answers)."""
    before, frames = record['before_frame'], record['response_frames']
    out = []

    def pick(mask, n):
        cells = np.argwhere(mask)
        return [tuple(int(v) for v in cells[i]) for i in rng.sample(range(len(cells)), min(n, len(cells)))]
    if frames[-1].shape == before.shape:
        for y, x in pick(frames[-1] != before, 2):
            out.append(('before', y, x, before))
            out.append(('frame %d' % len(frames), y, x, frames[-1]))
        if len(frames) >= 3:
            k = len(frames) // 2
            transient = (frames[k - 1] != before) & (frames[-1] == before)
            for y, x in pick(transient, 1):
                out.append(('frame %d' % k, y, x, frames[k - 1]))
        if current.shape == before.shape:
            for y, x in pick((before != current) & (frames[-1] == before), 2):
                out.append(('before', y, x, before))
        static = np.ones(before.shape, dtype=bool)
        for f in frames:
            static &= f == before
        for y, x in pick(static, 1):
            out.append(('before', y, x, before))
    questions = [{'which_board': w, 'x': x, 'y': y} for w, y, x, _ in out]
    answers = [HEX[int(f[y, x])] for _, y, x, f in out]
    return questions, answers


def main(events_path, cases_path, check_dir, out_dir):
    out, check_dir = Path(out_dir), Path(check_dir)
    frozen = {c['case']: c for c in json.loads(Path(cases_path).read_text())['cases']}
    subset = json.loads((check_dir / 'review_packet/subset_frozen.json').read_text())['subset']
    results = {c['case']: c for c in json.loads((check_dir / 'results.json').read_text())['cases']}
    games = {k.split('-')[0]: v for k, v in records.load_run(events_path).items()}
    rng = random.Random(SEED)
    key, lock = {}, {}
    for name in subset:
        case = frozen[name]
        recs = games[case['game']]['records']
        decision = case['decision_after_actions']
        done = recs[:decision]
        current = done[-1]['response_frames'][-1]
        text = decision_input(done, decision) + '\n'
        one, two = out / 'materials/role1' / name, out / 'materials/role2' / name
        (one / 'stage1').mkdir(parents=True, exist_ok=True)
        (one / 'stage2').mkdir(exist_ok=True)
        two.mkdir(parents=True, exist_ok=True)
        (one / 'stage1' / 'decision_input.txt').write_text(text)
        history_files(done, one / 'stage2')
        (two / 'decision_input.txt').write_text(text)
        tile(current).save(two / 'current_board.png')
        pack = (check_dir / 'packs' / ('%s_B2.txt' % name)).read_text()
        (two / 'pack_B2.txt').write_text(pack)
        questions, entry = [], {'records': []}
        for e in case['earlier_records']:
            r = recs[e['event'] - 1]
            qs, answers = probes_for(r, current, rng)
            start = len(questions)
            questions += [dict(q, id='P%d' % (start + i + 1), record_action=r['event_seq']) for i, q in enumerate(qs)]
            before, frames = r['before_frame'], r['response_frames']
            entry['records'].append({
                'action_number': r['event_seq'], 'action': action_text(r['action']), 'level': r['level_observed'],
                'attempt': r['reset_id'] + 1, 'frames_returned': len(frames),
                'cells_differing_from_board_before_per_frame': [int((f != before).sum()) for f in frames],
                'cells_of_last_frame_differing_from_board_before': int((frames[-1] != before).sum()),
                'level_completed': r['level_after'] > r['level_observed'], 'state_after': r['state_after'],
                'cells_where_board_before_differs_from_current': int((before != current).sum()),
                'probe_answers': {'P%d' % (start + i + 1): a for i, a in enumerate(answers)}})
        (two / 'probes.json').write_text(json.dumps(questions, indent=1))
        entry.update(game=case['game'], decision=decision, type=case['type'],
                     pack_opus_tokens=results[name]['pack']['opus_tokens'],
                     pack_fits_2048=results[name]['pack']['fits_active']['2048'],
                     pack_sha256=results[name]['pack']['sha256'])
        key[name] = entry
        lock[name] = {'pack_sha256': hashlib.sha256(pack.rstrip('\n').encode()).hexdigest(),
                      'decision_input_sha256': hashlib.sha256(text.encode()).hexdigest(),
                      'history_records': len(done), 'history_images': len(list((one / 'stage2/images').glob('*.png')))}
        assert lock[name]['pack_sha256'] == results[name]['pack']['sha256']
    (out / 'sealed').mkdir(exist_ok=True)
    (out / 'sealed' / 'key_from_frames.json').write_text(json.dumps(key, indent=1))
    (out / 'frozen_inputs.json').write_text(json.dumps({
        'representation': 'B version 2 (M-ref-v2), 2,048-token working allowance', 'subset': subset,
        'cases_file_sha256': hashlib.sha256(Path(cases_path).read_bytes()).hexdigest(), 'cases': lock}, indent=1))
    for name in subset:
        print(name, frozen[name]['game'], 'decision', frozen[name]['decision_after_actions'], lock[name]['history_records'],
              'records', '| probes', sum(len(r['probe_answers']) for r in key[name]['records']), '| fits', key[name]['pack_fits_2048'])


if __name__ == '__main__':
    main(*sys.argv[1:5])
