"""Saved play, in one shape, for the recovery measures.

A trace is one game played once:
    {'source', 'game', 'initial': first board, 'initial_avail', 'win_levels', 'steps': [...]}
A step is one counted action and what the game returned:
    {'a': 'ACTION1'..'ACTION7' or 'RESET', 'x', 'y', 'by': 'model' or 'controller',
     'state', 'lc': levels completed after, 'full_reset', 'avail', 'nf': frames returned,
     'frame': last returned board, 'notes': the agent's hypothesis list after this action or None}
The RESET that opens a game is not a step. Nothing here reads game source.

Two sources:
  load_events      a claude_arc_v1 run (events.jsonl): our own harness.
  load_recordings  public ARC replay recordings as kept by the loss audit (final board of each step only).
"""
import json
import pickle
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
NOV6 = ROOT / '.cache/claude_arc_runs/opus55-competition-20261106T054112Z/events.jsonl'
RECORDINGS = ROOT / '.cache/arc_loss_audit/rec'
CACHE = ROOT / '.cache/recovery_v1'


def _name(action_id):
    return 'RESET' if action_id == 0 else 'ACTION%d' % action_id


def _notes(content):
    """The hypothesis list in a model reply, as comparable tuples, or None when it cannot be read."""
    try:
        value = json.loads(content)
        return tuple((h['id'], h['statement'], h['status']) for h in value['hypotheses'])
    except Exception:
        return None


def load_events(path=NOV6, source=None):
    path = Path(path)
    source = source or path.parent.name
    cached = CACHE / (source + '.pkl')
    if cached.exists() and cached.stat().st_mtime > path.stat().st_mtime:
        return pickle.loads(cached.read_bytes())
    traces, pending = {}, {}
    with path.open() as handle:
        for line in handle:
            event = json.loads(line)
            kind = event['kind']
            if kind == 'initial_observation':
                seen = event['observation']
                traces[event['game_id']] = {
                    'source': source, 'game': event['game_id'],
                    'initial': np.asarray(seen['frames'][-1], dtype=np.uint8),
                    'initial_avail': list(seen['available_actions']),
                    'win_levels': seen['win_levels'], 'steps': []}
            elif kind == 'model_returned':
                pending[event['game_id']] = _notes(event['content'])
            elif kind == 'transition':
                after, action = event['after'], event['action']
                data = action.get('action_data') or {}
                controller = action['action_id'] == 0
                traces[event['game_id']]['steps'].append({
                    'a': _name(action['action_id']), 'x': data.get('x'), 'y': data.get('y'),
                    'by': 'controller' if controller else 'model',
                    'state': after['state'], 'lc': after['levels_completed'],
                    'full_reset': after['full_reset'], 'avail': list(after['available_actions']),
                    'nf': len(after['frames']),
                    'frame': np.asarray(after['frames'][-1], dtype=np.uint8),
                    # a controller reset makes no model call, so the notes are the ones already held
                    'notes': None if controller else pending.get(event['game_id'])})
    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(pickle.dumps(traces))
    return traces


def load_recording(json_path):
    json_path = Path(json_path)
    meta = json.loads(json_path.read_text())
    frames = np.load(json_path.with_suffix('.npz'))['frames']
    steps = meta['steps']
    if not steps or steps[0]['a'] != 'RESET':
        raise ValueError('recording does not open with RESET: ' + json_path.name)
    trace = {'source': meta['label'], 'game': meta['game'], 'initial': frames[0],
             'initial_avail': list(steps[0]['avail'] or []), 'win_levels': None, 'steps': []}
    for step, frame in zip(steps[1:], frames[1:]):
        trace['steps'].append({
            'a': step['a'], 'x': step['x'], 'y': step['y'], 'by': 'model',
            'state': step['state'], 'lc': step['lc'] or 0, 'full_reset': bool(step['full_reset']),
            'avail': list(step['avail'] or []), 'nf': step['nf'], 'frame': frame, 'notes': None})
    return trace


def load_recordings(folder=RECORDINGS):
    """{(label, game): trace} for every saved public recording."""
    out = {}
    for path in sorted(Path(folder).glob('*.json')):
        trace = load_recording(path)
        out[(trace['source'], trace['game'])] = trace
    return out
