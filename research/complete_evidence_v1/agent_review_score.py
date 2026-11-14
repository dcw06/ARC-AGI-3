"""Score the pack-reader submissions against the key computed from the original frames.

Checked per record: the action, frames returned, cells of the last frame differing from the board before,
level completed, each per-frame count the reader gave, and every probe colour. Prose is not scored here.
Usage: agent_review_score.py <agent_review_dir>
"""
import json
import re
import sys
from pathlib import Path


def norm_action(text):
    return re.sub(r'[^a-z0-9=]+', ' ', str(text).lower()).strip()


def main(review_dir):
    review = Path(review_dir)
    key = json.loads((review / 'sealed/key_from_frames.json').read_text())
    out = {}
    for name, truth in key.items():
        path = review / 'submissions/role2' / ('%s_pack_reading.json' % name)
        if not path.exists():
            out[name] = {'submitted': False}
            continue
        sub = json.loads(path.read_text())
        checks, wrong, undetermined = 0, [], []

        def check(label, got, want):
            nonlocal checks
            checks += 1
            if isinstance(got, str) and 'cannot determine' in got.lower() or got is None:
                undetermined.append(label)
            elif got != want:
                wrong.append({'item': label, 'reader': got, 'frames': want})
        records = sub.get('records', [])
        for i, t in enumerate(truth['records']):
            r = records[i] if i < len(records) else {}
            tag = 'action %d' % t['action_number']
            check(tag + ': action number', r.get('action_number'), t['action_number'])
            got_action = norm_action(r.get('action', ''))
            checks += 1
            if not all(part in got_action for part in norm_action(t['action']).split()):
                wrong.append({'item': tag + ': action', 'reader': r.get('action'), 'frames': t['action']})
            check(tag + ': frames returned', r.get('frames_returned'), t['frames_returned'])
            check(tag + ': cells of last frame differing', r.get('cells_of_last_frame_differing_from_board_before'),
                  t['cells_of_last_frame_differing_from_board_before'])
            check(tag + ': level completed', r.get('level_completed'), t['level_completed'])
            for f in r.get('frames', []):
                k = f.get('frame')
                if isinstance(k, int) and 1 <= k <= t['frames_returned']:
                    check('%s: frame %d cells differing from before' % (tag, k), f.get('cells_differing_from_board_before'),
                          t['cells_differing_from_board_before_per_frame'][k - 1])
            given = {p.get('id'): str(p.get('colour', '')).strip().lower() for p in sub.get('probe_answers', [])}
            for pid, colour in t['probe_answers'].items():
                check('probe %s' % pid, given.get(pid), colour)
        out[name] = {'submitted': True, 'checks': checks, 'correct': checks - len(wrong) - len(undetermined),
                     'wrong': wrong, 'cannot_determine': undetermined,
                     'probes': sum(len(t['probe_answers']) for t in truth['records']),
                     'probes_correct': sum(1 for t in truth['records'] for pid, c in t['probe_answers'].items()
                                           if {p.get('id'): str(p.get('colour', '')).strip().lower()
                                               for p in sub.get('probe_answers', [])}.get(pid) == c),
                     'reader_flags': [x for r in records for x in (r.get('cannot_determine') or [])],
                     'hard_or_missing': sub.get('what_was_hard_or_missing', '')}
    (review / 'role2_scores.json').write_text(json.dumps(out, indent=1))
    for name, s in out.items():
        if not s['submitted']:
            print(name, 'not submitted')
            continue
        print(name, '%d/%d checks correct' % (s['correct'], s['checks']), '| probes %d/%d' % (s['probes_correct'], s['probes']),
              '| wrong:', [(w['item'], w['reader'], w['frames']) for w in s['wrong']], '| undetermined:', s['cannot_determine'])


if __name__ == '__main__':
    main(sys.argv[1])
