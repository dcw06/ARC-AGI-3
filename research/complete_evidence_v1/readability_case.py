"""Freeze one tn36 example and build the two inputs for the one-record readability rehearsal.

Example: the decision after 46 actions, and the earlier "run" at action 12. It is the only repeat in tn36
that is in the same attempt, out of the agent's view, and has a mixed switch setting.
  A  self-contained keyframe plus ordered changes (M-key-v1)
  B  the earlier board as differences from the supplied current board (M-ref-v1)
Both use the same record, the same common context and the same questions, inside a 2,048-token older-memory
allowance that includes the reading instructions, headers and provenance.

Writes the frozen inputs, token counts and the reviewer forms, and a sealed evaluation record holding the
correct answers (taken from the original frames). No Opus request is made here.
Usage: readability_case.py <events.jsonl> <out_dir> [version=1]
Version 1 writes frozen/ and the sealed record. Version 2 uses the corrected reading instructions and
writes only frozen_v2/: the record, context, questions, sealed answers and rubric must be identical to
version 1, and the script stops if they are not.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research'))
from complete_evidence_v1 import formats_v2 as F, records  # noqa: E402
from complete_evidence_v1.opus_count import MODEL, OpusCounter  # noqa: E402

GAME, DECISION, EARLIER, ALLOWANCE = 'tn36', 46, 12, 2048
MAX_TOKENS, EFFORT = 8000, 'high'
HEX = '0123456789abcdef'
BARS = [(42, 42, x, x + 2) for x in (20, 25, 30, 35, 40)]   # y0, y1, x0, x1
STEMS = [(44, 46, x, x) for x in (21, 26, 31, 36, 41)]
PIECE_ROWS = (13, 16)

SYSTEM = ('You are checking whether a text record from a grid game can be read correctly. Use only the material '
          'in the user message. Do not guess: where the material does not let you determine something, answer '
          '"cannot determine". Reply with one JSON object in the requested form and nothing else.')
CONTEXT_NOTE = (
    'The game board has 64 columns and 64 rows. Each cell holds one colour, written as a hexadecimal digit '
    '(0-9, a-f; upper and lower case mean the same). x is the column counted from the left starting at 0; '
    'y is the row counted from the top starting at 0. In the current board below, each line reads "yy|" then '
    'that row\'s 64 cells in groups of 8 separated by spaces, so the cell at column x is character x%8 of '
    'group x//8 (both counted from 0). In the recent history, changed_cells lists runs '
    '[x_first, x_last, y, colour_before, colour_after] of cells that differ between the board before that '
    'action and the last frame it returned.')
QUESTIONS = '''The board has ten switches. Five "bars": row 42, columns 20-22, 25-27, 30-32, 35-37 and 40-42. Five "stems": rows 44-46, columns 21, 26, 31, 36 and 41. Every cell of one switch has the same colour. The board also has a "piece": the block of colour b that occupies rows 13-16, columns 30-33 on the current board.

The older memory holds one earlier action record. Answer these about it.

Q1. Immediately before the action in that record, what colour was each bar (left to right) and each stem (left to right)?
Q2. What happened when the action ran? State how many frames it returned; which columns and rows the piece occupied in frame 3; how many cells of the last returned frame differ from the board before the action; whether the level was completed; and describe in one or two sentences what the frames show.
Q3. Is the switch configuration immediately before that earlier action the same as the switch configuration on the current board? List any switches that differ.

Reply with this JSON object:
{"q1_bars_left_to_right": ["colour", "colour", "colour", "colour", "colour"],
 "q1_stems_left_to_right": ["colour", "colour", "colour", "colour", "colour"],
 "q2_frames_returned": number,
 "q2_piece_columns_in_frame_3": [first, last],
 "q2_piece_rows_in_frame_3": [first, last],
 "q2_cells_different_in_last_frame": number,
 "q2_level_completed": true or false,
 "q2_what_the_frames_show": "text",
 "q3_same_configuration": true or false,
 "q3_switches_that_differ": ["bar 1" ... "stem 5", or empty]}'''


def sha(frame):
    a = np.asarray(frame, dtype=np.uint8)
    return hashlib.sha256(a.tobytes()).hexdigest()


def hex_rows(frame):
    """Same layout as the saved agent's prompt (research/claude_arc_v1/policy.py)."""
    rows = []
    for y, row in enumerate(frame):
        text = ''.join(HEX[int(v)] for v in row)
        rows.append('%02d|' % y + ' '.join(text[i:i + 8] for i in range(0, 64, 8)))
    return rows


def changed_runs(old, new):
    """Same run rule as the saved agent's changed_cells."""
    runs = []
    ys, xs = np.nonzero(old != new)
    for y, x in zip(ys.tolist(), xs.tolist()):
        pair = (HEX[int(old[y, x])], HEX[int(new[y, x])])
        if runs and runs[-1][2] == y and runs[-1][1] == x - 1 and (runs[-1][3], runs[-1][4]) == pair:
            runs[-1][1] = x
        else:
            runs.append([x, x, y, pair[0], pair[1]])
    return runs


def switch_colours(frame, switches):
    out = []
    for y0, y1, x0, x1 in switches:
        values = set(frame[y0:y1 + 1, x0:x1 + 1].ravel().tolist())
        assert len(values) == 1, 'switch is not one colour'
        out.append(HEX[values.pop()])
    return out


def piece_box(frame):
    ys, xs = np.nonzero(frame[PIECE_ROWS[0] - 4:PIECE_ROWS[1] + 5] == 11)
    return [int(xs.min()), int(xs.max())], [int(ys.min()) + PIECE_ROWS[0] - 4, int(ys.max()) + PIECE_ROWS[0] - 4]


def main(events_path, out_dir, version=1):
    out = Path(out_dir)
    frozen = out / ('frozen' if version == 1 else 'frozen_v%d' % version)
    notes = F.READING_NOTES if version == 1 else F.READING_NOTES_V2
    tag = '' if version == 1 else ' v%d' % version
    for path in ((frozen, out / 'sealed', out / 'human', out / 'responses') if version == 1 else (frozen,)):
        path.mkdir(parents=True, exist_ok=True)
    recs = next(v for k, v in records.load_run(events_path).items() if k.startswith(GAME))['records']
    done = recs[:DECISION]
    current = done[-1]['response_frames'][-1]
    record = recs[EARLIER - 1]
    recent = done[-2:]
    observation_ids = {}
    with open(events_path) as handle:
        for line in handle:
            if '"transition"' in line and GAME in line[:300]:
                event = json.loads(line)
                if event['game_id'].startswith(GAME) and event['transition_id'] in ('t%d' % DECISION, 't%d' % EARLIER):
                    observation_ids[event['transition_id']] = {
                        'after_observation_sha256': event['after']['observation_sha256'],
                        'before_observation_sha256': event['before']['observation_sha256']}

    # ---- common context
    history = [{'transition_id': r['source_transition_ids'][0],
                'action': ('ACTION6 x=%d y=%d' % (r['action']['x'], r['action']['y'])) if r['action']['x'] is not None else r['action']['id'],
                'frames_returned': len(r['response_frames']),
                'changed_cells': changed_runs(r['before_frame'], r['response_frames'][-1]),
                'state': r['state_after'], 'levels_completed': r['level_after']} for r in recent]
    context = '\n'.join(
        ['== CONTEXT ==', CONTEXT_NOTE, '',
         'Current board: observation o%d (the board after %d actions). levels_completed=%d, state=%s.' % (
             DECISION, DECISION, done[-1]['level_after'], done[-1]['state_after'])]
        + hex_rows(current)
        + ['Legal actions now: %s (ACTION6 clicks one cell x,y).' % ','.join(map(str, done[-1]['legal_after'])), '',
           'Recent history, the two most recent actions:']
        + [json.dumps(h, separators=(',', ':')) for h in history])

    # ---- the two older-memory sections
    provenance = 'Source: game %s, saved run %s, action %d (transition t%d). One record, selected by hand.' % (
        GAME, record['trajectory_id'], EARLIER, EARLIER)
    reference = ('In this record "current" means the current board given above, observation o%d.' % DECISION
                 if version == 1 else
                 'In this record "current" means the current board given above, observation o%d: the board before '
                 'this action is rebuilt from o%d.' % (DECISION, DECISION))
    sections = {
        'A': '\n'.join(['== OLDER MEMORY ==', provenance, notes['M-key-v1'], '', F.m_key(record)]),
        'B': '\n'.join(['== OLDER MEMORY ==', provenance, reference, notes['M-ref-v1'], '', F.m_ref(record, current)])}
    question_block = '== QUESTIONS ==\n' + QUESTIONS
    counter = OpusCounter()
    counts = {'model': MODEL, 'allowance': ALLOWANCE, 'counts_are_estimates': True,
              'reading_instructions_version': version,
              'system': counter.count(SYSTEM, 'readability system'),
              'common_context': counter.count(context, 'readability common context'),
              'questions': counter.count(question_block, 'readability questions'), 'inputs': {}}
    requests = {}
    for name, section in sections.items():
        user = '\n\n'.join([context, section, question_block])
        request = {'model': MODEL, 'max_tokens': MAX_TOKENS, 'thinking': {'type': 'adaptive'},
                   'output_config': {'effort': EFFORT}, 'system': SYSTEM,
                   'messages': [{'role': 'user', 'content': user}]}
        requests[name] = request
        record_text = section.split('\n\n', 1)[1]
        memory_tokens = counter.count(section, 'readability%s older-memory section %s' % (tag, name))
        counts['inputs'][name] = {
            'format': 'M-key-v1' if name == 'A' else 'M-ref-v1',
            'older_memory_section_tokens': memory_tokens, 'within_allowance': memory_tokens <= ALLOWANCE,
            'record_alone_tokens': counter.count(record_text, 'readability record %s' % name),
            'record_sha256': hashlib.sha256(record_text.encode()).hexdigest(),
            'full_request_input_tokens': counter.count_request(request, 'readability%s full request %s' % (tag, name)),
            'older_memory_characters': len(section)}
        (frozen / ('older_memory_%s.txt' % name)).write_text(section + '\n')
        (frozen / ('input_%s.txt' % name)).write_text(
            '[system]\n' + SYSTEM + '\n\n[user]\n' + user + '\n')
    (frozen / 'requests.json').write_text(json.dumps(requests, indent=1))
    (frozen / 'common_context.txt').write_text(context + '\n')
    (frozen / 'questions.txt').write_text(question_block + '\n')
    (frozen / 'token_counts.json').write_text(json.dumps(counts, indent=1))
    np.savez_compressed(
        frozen / 'source_frames.npz', current_board=current, earlier_before=record['before_frame'],
        earlier_frames=np.stack(record['response_frames']),
        **{'recent_%s_before' % r['source_transition_ids'][0]: r['before_frame'] for r in recent},
        **{'recent_%s_frames' % r['source_transition_ids'][0]: np.stack(r['response_frames']) for r in recent})

    # ---- both records must decode to the original frames
    for name, text, cur in (('A', F.m_key(record), None), ('B', F.m_ref(record, current), current)):
        before, _, frames = F.decode(text, current=cur)
        assert np.array_equal(before, record['before_frame']) and len(frames) == len(record['response_frames'])
        assert all(np.array_equal(a, b) for a, b in zip(frames, record['response_frames'])), name

    # ---- sealed evaluation record: correct answers from the original frames
    before, frames = record['before_frame'], record['response_frames']
    bars_then, stems_then = switch_colours(before, BARS), switch_colours(before, STEMS)
    bars_now, stems_now = switch_colours(current, BARS), switch_colours(current, STEMS)
    differ = ['bar %d' % (i + 1) for i in range(5) if bars_then[i] != bars_now[i]] + \
             ['stem %d' % (i + 1) for i in range(5) if stems_then[i] != stems_now[i]]
    columns, rows = piece_box(frames[2])
    last_diff = np.argwhere(frames[-1] != before)
    per_frame = []
    for i, frame in enumerate(frames, 1):
        d = frame != before
        cols_i, rows_i = piece_box(frame)
        per_frame.append({'frame': i, 'cells_different_from_before': int(d.sum()),
                          'rows_changed': sorted(set(np.nonzero(d)[0].tolist())),
                          'piece_columns': cols_i, 'piece_rows': rows_i,
                          'colour_a_cells_in_rows_51_59': int((frame[51:60] == 10).sum()),
                          'colour_9_columns_in_rows_41_47': (lambda xs: [int(xs.min()), int(xs.max())] if xs.size else None)(
                              np.nonzero((frame[41:48] == 9) & (before[41:48] != 9))[1])})
    key = {
        'q1_bars_left_to_right': bars_then, 'q1_stems_left_to_right': stems_then,
        'q2_frames_returned': len(frames), 'q2_piece_columns_in_frame_3': columns, 'q2_piece_rows_in_frame_3': rows,
        'q2_cells_different_in_last_frame': int(len(last_diff)), 'q2_level_completed': record['level_after'] > record['level_observed'],
        'q3_same_configuration': not differ, 'q3_switches_that_differ': differ}
    sealed = {
        'warning': 'Correct answers. Not part of any input. Reviewers must not open this before submitting.',
        'example': {'game': GAME, 'run': record['trajectory_id'], 'decision_after_actions': DECISION,
                    'earlier_record_action': EARLIER, 'action_actually_taken_next': recs[DECISION]['action'],
                    'why_this_example': 'only tn36 repeat that is in the same attempt, out of view, with a mixed setting'},
        'identities': {
            'current_board': {'observation': 'o%d' % DECISION, 'cells_sha256': sha(current),
                              'event_log': observation_ids.get('t%d' % DECISION)},
            'reference_board_for_input_B': {'observation': 'o%d' % DECISION, 'cells_sha256': sha(current)},
            'earlier_before_board': {'cells_sha256': sha(before), 'event_log': observation_ids.get('t%d' % EARLIER)},
            'earlier_frames_cells_sha256': [sha(f) for f in frames],
            'recent_history_transitions': [r['source_transition_ids'][0] for r in recent]},
        'answer_key': key,
        'supporting_facts_from_frames': {
            'current_board_bars': bars_now, 'current_board_stems': stems_now,
            'cells_where_earlier_before_board_differs_from_current': int((before != current).sum()),
            'rows_of_those_cells': sorted(set(np.nonzero(before != current)[0].tolist())),
            'last_frame_differing_cells_xy_before_after': [
                [int(x), int(y), HEX[before[y, x]], HEX[frames[-1][y, x]]] for y, x in last_diff.tolist()],
            'state_after': record['state_after'], 'level_before_and_after': [record['level_observed'], record['level_after']],
            'per_frame': per_frame},
        'rubric_fixed_before_any_response': {
            'structured_items': {
                'bars': 'q1_bars_left_to_right equals the key exactly',
                'stems': 'q1_stems_left_to_right equals the key exactly',
                'frames': 'q2_frames_returned equals the key',
                'piece_columns': 'q2_piece_columns_in_frame_3 equals the key',
                'piece_rows': 'q2_piece_rows_in_frame_3 equals the key',
                'last_frame': 'q2_cells_different_in_last_frame equals the key',
                'level': 'q2_level_completed equals the key',
                'match': 'q3_same_configuration and q3_switches_that_differ both equal the key'},
            'free_text_item': 'q2_what_the_frames_show states nothing that contradicts supporting_facts_from_frames, '
                              'judged by hand and recorded with the reason',
            'a_reader_recovers_the_facts': 'all eight structured items correct and the free-text item not contradicted',
            'colours': 'compared as hexadecimal digits, ignoring case',
            'cannot_determine': 'counts as not recovered and is reported separately from a wrong answer'}}
    over = [n for n, v in counts['inputs'].items() if not v['within_allowance']]
    if version != 1:
        existing = json.loads((out / 'sealed' / 'evaluation_record.json').read_text())
        same_key = existing['answer_key'] == key and existing['rubric_fixed_before_any_response'] == sealed['rubric_fixed_before_any_response']
        files = sorted(p for p in frozen.iterdir() if p.name != 'manifest.json')
        manifest = {'reading_instructions_version': version, 'over_allowance': over,
                    'answer_key_and_rubric_equal_sealed_record': same_key,
                    'reconstruction': 'both records decode to the original board and all %d frames' % len(frames),
                    'sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
        (frozen / 'manifest.json').write_text(json.dumps(manifest, indent=1))
        print(json.dumps(counts, indent=1))
        print(json.dumps({k: v for k, v in manifest.items() if k != 'sha256'}, indent=1))
        assert same_key, 'answer key or rubric differs from the sealed record'
        if over:
            raise SystemExit('older memory exceeds the allowance for: %s' % over)
        return
    assert not over, 'older memory exceeds the allowance'
    (out / 'sealed' / 'evaluation_record.json').write_text(json.dumps(sealed, indent=1))

    form = {'reviewer': '', 'input_read': 'A or B', 'read_order': 'first or second', 'minutes_taken': None,
            'opened_anything_else': False, 'answers': {k: None for k in key} | {'q2_what_the_frames_show': None},
            'what_was_hard_or_missing': ''}
    (out / 'human' / 'answer_form.json').write_text(json.dumps(form, indent=1))
    print(json.dumps(counts, indent=1))
    print('key items:', len(key), '| frames:', len(frames), '| recent:', [h['transition_id'] for h in history])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1)
