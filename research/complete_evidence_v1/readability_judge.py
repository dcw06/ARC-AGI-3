"""Score reader answer forms (human or agent) and Opus responses against the sealed answers, by the rubric fixed beforehand.

Usage: readability_judge.py <report_dir>
Scores the eight structured items. The free-text item is listed for judging by hand.
"""
import json
import sys
from pathlib import Path


def norm(value):
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, list):
        return [norm(v) for v in value]
    return value


def score(answers, key):
    def same(field):
        return norm(answers.get(field)) == norm(key[field])

    def status(ok, fields):
        if any('cannot determine' in json.dumps(norm(answers.get(f))) for f in fields) or any(answers.get(f) is None for f in fields):
            return 'cannot determine'
        return 'correct' if ok else 'wrong'
    items = {'bars': ['q1_bars_left_to_right'], 'stems': ['q1_stems_left_to_right'], 'frames': ['q2_frames_returned'],
             'piece_columns': ['q2_piece_columns_in_frame_3'], 'piece_rows': ['q2_piece_rows_in_frame_3'],
             'last_frame': ['q2_cells_different_in_last_frame'], 'level': ['q2_level_completed'],
             'match': ['q3_same_configuration', 'q3_switches_that_differ']}
    return {name: status(all(same(f) for f in fields), fields) for name, fields in items.items()}


def main(report_dir):
    report_dir = Path(report_dir)
    key = json.loads((report_dir / 'sealed/evaluation_record.json').read_text())['answer_key']
    rows = []
    for folder, pattern in (('human', 'reviewer*.json'), ('agent_readers', 'reader*.json')):
        for path in sorted((report_dir / folder).glob(pattern)):
            form = json.loads(path.read_text())
            rows.append(('%s/%s' % (folder, path.name), form.get('input_read'), form.get('read_order'), form['answers']))
    for path in sorted((report_dir / 'responses').glob('*.json')):
        result = json.loads(path.read_text())
        rows.append((path.name, result['input'], result['outcome'], result.get('answers') or {}))
    out = []
    for name, which, note, answers in rows:
        marks = score(answers, key)
        out.append({'source': name, 'input': which, 'note': note, 'items': marks,
                    'all_structured_correct': all(v == 'correct' for v in marks.values()),
                    'free_text_to_judge_by_hand': answers.get('q2_what_the_frames_show')})
        print(name, which, note, marks)
    (report_dir / 'scores.json').write_text(json.dumps(out, indent=1))
    if not rows:
        print('nothing to score yet')


if __name__ == '__main__':
    main(sys.argv[1])
