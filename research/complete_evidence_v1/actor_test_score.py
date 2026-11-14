"""Scoring rule for the one-case actor prediction test. Fixed before the answer was computed.

A response gives rectangles of cells it predicts will have a different colour in the last returned frame.
Predicted cells are those inside a rectangle whose stated colour differs from the current board.
Primary outcome: F1 between predicted and actual changed cells (a cell counts only with the right new
colour), over the play area, which is every row except row 0 (the counter strip).
If neither side has any changed cell the F1 is 1; if only one side has, it is 0.
Secondary: the same over all rows; exact match; level_completed; any_change_outside_row_0.

Usage: actor_test_score.py <test_dir>
"""
import json
import sys
from pathlib import Path

import numpy as np

HEX = '0123456789abcdef'


def predicted_cells(answers, current):
    """{(y, x): colour} for cells the response says will change. Raises ValueError on a malformed answer."""
    cells = {}
    regions = answers.get('changed_regions')
    if not isinstance(regions, list):
        raise ValueError('changed_regions is not a list')
    height, width = current.shape
    for region in regions:
        colour = HEX.index(str(region['colour_after']).strip().lower())
        x0, x1, y0, y1 = (int(region[k]) for k in ('x_first', 'x_last', 'y_first', 'y_last'))
        if not (0 <= x0 <= x1 < width and 0 <= y0 <= y1 < height):
            raise ValueError('region outside the board: %s' % region)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if int(current[y, x]) != colour:
                    cells[(y, x)] = colour
    return cells


def f1(predicted, actual):
    if not predicted and not actual:
        return {'tp': 0, 'predicted': 0, 'actual': 0, 'precision': 1.0, 'recall': 1.0, 'f1': 1.0, 'exact': True}
    tp = sum(1 for cell, colour in predicted.items() if actual.get(cell) == colour)
    precision = tp / len(predicted) if predicted else 0.0
    recall = tp / len(actual) if actual else 0.0
    return {'tp': tp, 'predicted': len(predicted), 'actual': len(actual), 'precision': round(precision, 4),
            'recall': round(recall, 4), 'f1': round(2 * precision * recall / (precision + recall), 4) if tp else 0.0,
            'exact': predicted == actual}


def score(answers, current, key):
    actual = {(y, x): HEX.index(c) for x, y, c in key['changed_cells_x_y_colour_after']}
    try:
        predicted = predicted_cells(answers or {}, current)
    except (ValueError, KeyError, TypeError) as error:
        return {'valid': False, 'error': str(error)[:200], 'play_area': {'f1': 0.0, 'exact': False}}
    play = lambda cells: {k: v for k, v in cells.items() if k[0] != 0}  # noqa: E731
    return {'valid': True, 'play_area': f1(play(predicted), play(actual)), 'all_rows': f1(predicted, actual),
            'level_completed_correct': answers.get('level_completed') == key['level_completed'],
            'any_change_outside_row_0_correct': answers.get('any_change_outside_row_0') == key['any_change_outside_row_0'],
            'confidence': answers.get('confidence'), 'basis': answers.get('basis')}


def main(test_dir):
    test = Path(test_dir)
    key = json.loads((test / 'sealed/answer_key.json').read_text())
    current = np.load(test / 'frozen/source_frames.npz')['current_board']
    rows = []
    for path in sorted((test / 'responses').glob('*.json')):
        result = json.loads(path.read_text())
        rows.append({'request': result['tag'], 'condition': result['condition'], 'outcome': result['outcome'],
                     'score': score(result.get('answers'), current, key)})
    by = {}
    for row in rows:
        by.setdefault(row['condition'], []).append(row['score']['play_area']['f1'])
    means = {c: round(sum(v) / len(v), 4) for c, v in by.items()}
    summary = {'requests': rows, 'mean_play_area_f1': means}
    if {'useful', 'none', 'irrelevant'} <= set(means):
        summary['useful_minus_none'] = round(means['useful'] - means['none'], 4)
        summary['useful_minus_irrelevant'] = round(means['useful'] - means['irrelevant'], 4)
        spread = max(max(v) - min(v) for v in by.values())
        summary['largest_spread_within_a_condition'] = round(spread, 4)
        summary['reading'] = ('unresolved: repeats of one condition differ by more than 0.5' if spread > 0.5 else
                              'benefit observed on this case' if min(summary['useful_minus_none'], summary['useful_minus_irrelevant']) >= 0.10
                              else 'no benefit observed on this case')
    (test / 'scores.json').write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main(sys.argv[1])
