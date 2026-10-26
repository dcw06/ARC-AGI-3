"""Evidence-memory request contracts; no model, provider or game calls."""
import json
import unittest

from research.ls20_instruction_v1.policy import make_request as instructed_request
from research.ls20_memory_evidence_v1.flow import run_episode
from research.ls20_memory_evidence_v1.policy import LABEL, evidence, make_request


def board(marks):
    grid = [[0]*64 for _ in range(64)]
    for (x, y), color in marks.items():
        for dy in range(2):
            for dx in range(2):
                grid[y+dy][x+dx] = color
    return dict(grid=grid, legal_actions=[1, 2, 3, 4], state='NOT_FINISHED', levels_completed=0)


def record(step, before, after, action):
    return dict(step=step, before=before, after=after, action=dict(action_id=action, action_data={}),
                predicted_visible_change='unknown')


# A moving 2x2 mark and an identical static mark; action 1 moves up five cells, action 3 is blocked.
START = board({(20, 30): 2, (50, 10): 2})
MOVED = board({(20, 25): 2, (50, 10): 2})
HISTORY = [record(0, START, MOVED, 1), record(1, MOVED, MOVED, 3), record(2, MOVED, MOVED, 3)]


class EvidenceRequest(unittest.TestCase):
    def test_request_is_the_instructed_request_plus_one_block(self):
        body = make_request(START, MOVED, HISTORY, 'Synthetic rules')
        content = body['messages'][1]['content']
        self.assertTrue(content[2]['text'].startswith(LABEL+'\n'))
        del content[2]
        self.assertEqual(body, instructed_request(START, MOVED, HISTORY, 'Synthetic rules'))

    def test_moved_region_blocked_streak_and_static_copy(self):
        block = evidence(START, HISTORY)
        first = block['recent_transitions'][0]
        self.assertEqual([(m['dx'], m['dy'], m['x'], m['y']) for m in first['moved_regions']], [(0, -5, [20, 21], [25, 26])])
        self.assertEqual([t['changed_cells'] for t in block['recent_transitions']], [8, 0, 0])
        self.assertEqual(block['recent_steps_without_moved_region'], 2)
        self.assertEqual(block['action_summary'], [
            dict(action_id=1, taken=1, any_change=1, region_moved=1, displacements=[[0, -5, 1]]),
            dict(action_id=3, taken=2, any_change=0, region_moved=0, displacements=[])])

    def test_colour_ids_come_with_the_rendered_palette(self):
        from certification.phase4_multimodal_preflight_v3.images import PALETTE
        block = evidence(START, HISTORY)
        self.assertEqual(block['rendered_palette'], {str(i): list(rgb) for i, rgb in enumerate(PALETTE)})
        self.assertTrue(all(str(r['color']) in block['rendered_palette'] for r in block['current_regions']))

    def test_block_is_a_function_of_observed_history_only(self):
        self.assertEqual(make_request(START, MOVED, HISTORY, 'Synthetic rules'),
                         make_request(START, MOVED, json.loads(json.dumps(HISTORY)), 'Synthetic rules'))
        self.assertEqual(evidence(START, [])['transitions_recorded'], 0)
        with self.assertRaisesRegex(ValueError, 'observed history'):
            make_request(START, START, HISTORY, 'Synthetic rules')

    def test_block_supplies_no_route_labels_or_future(self):
        text = make_request(START, MOVED, HISTORY, 'Synthetic rules')['messages'][1]['content'][2]['text'].lower()
        for word in ('player', 'cross', 'goal', 'target', 'route', 'solution', 'destination', 'wall'):
            self.assertNotIn(word, text)
        self.assertEqual(len(evidence(START, HISTORY)['recent_transitions']), 3)

    def test_recent_window_is_bounded(self):
        history = [record(i, MOVED, MOVED, 3) for i in range(9)]
        block = evidence(MOVED, history)
        self.assertEqual((block['transitions_recorded'], len(block['recent_transitions'])), (9, 6))
        self.assertEqual(block['recent_transitions'][0]['step'], 3)

    def test_episode_requests_carry_the_block_and_replay_identically(self):
        class Engine:
            def __init__(self): self.count = 0
            def bootstrap(self): return board({(20, 30): 2})
            def dispatch(self, action):
                self.count += 1
                return board({(20, 30-5*self.count): 2}) if self.count < 3 else dict(board({(20, 15): 2}), levels_completed=1)
            def close(self): return dict(closed=True, local_scorecard_opened=True, local_scorecard_closed=True, online_calls=0)
        answer = json.dumps(dict(action_id=1, action_data={}, predicted_visible_change='yes'))
        runs = []
        for _ in range(2):
            events = []
            result = run_episode(board({(20, 30): 2}), 'Synthetic rules', Engine(), lambda _: answer, events.append,
                                 deadline=10, now=lambda: 0)
            runs.append(events)
        self.assertTrue(result['level1_passed'])
        self.assertEqual(runs[0], runs[1])
        bodies = [e['body'] for e in runs[0] if e['kind'] == 'request']
        blocks = [json.loads(b['messages'][1]['content'][2]['text'].split('\n', 1)[1]) for b in bodies]
        self.assertEqual([b['transitions_recorded'] for b in blocks], [0, 1, 2])
        self.assertEqual(blocks[2]['action_summary'][0]['displacements'], [[0, -5, 2]])


if __name__ == '__main__':
    unittest.main()
