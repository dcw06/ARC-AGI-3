"""Stored-v1 records built from a saved claude_arc_v1 run (events.jsonl).

One record is one action and everything the game returned for it: the board before, every returned frame
in order, and the public fields. Nothing here reads game source or hidden state.
"""
import hashlib
import json
from collections import defaultdict

import numpy as np

FRAME_POLICY = 'all-returned-frames-v1'


def frame_id(frame):
    """Content identifier: the same cells always give the same ID."""
    a = np.asarray(frame, dtype=np.uint8)
    return hashlib.sha256(bytes(a.shape) + a.tobytes()).hexdigest()[:16]


def action_name(action):
    return 'RESET' if action['action_id'] == 0 else 'ACTION%d' % action['action_id']


def load_run(events_path, trajectory_id=None):
    """Return {game_id: {'initial': obs, 'records': [...]}} in play order."""
    games = defaultdict(lambda: {'initial': None, 'records': []})
    resets = defaultdict(int)
    trajectory_id = trajectory_id or str(events_path).split('/')[-2]
    with open(events_path) as handle:
        for line in handle:
            event = json.loads(line)
            kind = event['kind']
            if kind == 'initial_observation':
                games[event['game_id']]['initial'] = event['observation']
            elif kind == 'transition':
                game = event['game_id']
                before, after, action = event['before'], event['after'], event['action']
                seq = len(games[game]['records']) + 1
                if action['action_id'] == 0:
                    resets[game] += 1
                frames = [np.asarray(f, dtype=np.uint8) for f in after['frames']]
                before_frame = np.asarray(before['frames'][-1], dtype=np.uint8)
                data = action.get('action_data') or {}
                games[game]['records'].append({
                    'memory_id': '%s:%s:e%04d' % (game.split('-')[0], trajectory_id, seq),
                    'game_id': game,
                    'trajectory_id': trajectory_id,
                    'event_seq': seq,
                    'reset_id': resets[game],
                    'level_observed': before['levels_completed'],
                    'action': {'id': action_name(action), 'x': data.get('x'), 'y': data.get('y')},
                    'before_frame': before_frame,
                    'before_frame_id': frame_id(before_frame),
                    'response_frames': frames,
                    'response_frame_ids': [frame_id(f) for f in frames],
                    'legal_before': list(before['available_actions']),
                    'legal_after': list(after['available_actions']),
                    'state_after': after['state'],
                    'level_after': after['levels_completed'],
                    'frame_policy_version': FRAME_POLICY,
                    'source_transition_ids': [event['transition_id']],
                    'dispatch': event['dispatch'],
                })
    return dict(games)
