"""Independent record audit; not an online engine replay or billing certificate."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from arcengine import GameState
from agent.state import Observation
from .config import strict_json


def check_observation(value):
    frames = tuple(np.asarray(f) for f in value['frames'])
    if not frames or any(f.ndim != 2 or not np.issubdtype(f.dtype, np.integer) or f.size == 0
                         or f.min() < 0 or f.max() > 255 for f in frames):
        raise ValueError('invalid observed frames')
    observation = Observation(value['game_id'], tuple(f.astype(np.uint8) for f in frames),
        GameState[value['state']], value['levels_completed'], value['win_levels'], 'audit-guid',
        tuple(value['available_actions']), value['full_reset'])
    if observation.canonical_hash != value['observation_sha256']:
        raise ValueError('observation hash mismatch')


def audit(folder):
    root = Path(folder)
    summary = strict_json((root / 'summary.json').read_bytes())
    if summary.get('report_revision') != 2:
        raise ValueError('report revision 2 required for coverage and final-state checks')
    previous, sequence, acknowledged, initial, current = '0' * 64, 0, {}, {}, {}
    pending, card, closed, calls, responses = None, None, False, 0, 0
    config = recorded_summary = None
    attempted, selected, last_dispatch = set(), None, {}
    for line in (root / 'events.jsonl').read_text(encoding='utf-8').splitlines():
        row = strict_json(line)
        actual = row.pop('sha256')
        raw = json.dumps(row, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        sequence += 1
        if row['sequence'] != sequence or row['previous_sha256'] != previous or hashlib.sha256(raw).hexdigest() != actual:
            raise ValueError('event-chain corruption')
        previous = actual
        kind, game = row['kind'], row.get('game_id')
        if pending is not None and kind in ('make_entered', 'model_entered'):
            raise ValueError('continued after unresolved dispatch')
        if kind == 'configuration':
            if config is not None:
                raise ValueError('multiple configurations')
            config = row['config']
        elif kind == 'inventory':
            if selected is not None or len(set(row['selected'])) != len(row['selected']):
                raise ValueError('duplicate inventory or selected games')
            selected = row['selected']
        elif kind == 'make_entered':
            if selected is None or game not in selected or game in attempted:
                raise ValueError('unselected or duplicate game initialization attempt')
            attempted.add(game)
            last_dispatch[game] = 'not_attempted'
        elif kind == 'summary':
            if recorded_summary is not None:
                raise ValueError('multiple summary events')
            recorded_summary = row['summary']
        elif kind == 'scorecard_open_acknowledged':
            if card is not None:
                raise ValueError('multiple scorecards')
            card = row['card_id']
        elif kind == 'initial_observation':
            if game not in attempted or game in current:
                raise ValueError('duplicate game initialization')
            check_observation(row['observation'])
            current[game] = row['observation']
            initial[game] = row['observation']['levels_completed']
        elif kind == 'model_entered':
            if game not in current:
                raise ValueError('model call without an initialized game')
            calls += 1
        elif kind == 'model_returned':
            responses += 1
        elif kind == 'dispatch_entered':
            if pending is not None:
                raise ValueError('dispatch after unresolved outcome')
            action = row['action']
            if (type(action['action_id']) is not int or not 1 <= action['action_id'] <= 7
                    or action['action_id'] not in current[game]['available_actions']):
                raise ValueError('illegal dispatched action')
            data = action['action_data']
            if action['action_id'] == 6:
                if set(data) != {'x', 'y'} or any(type(v) is not int or not 0 <= v <= 63 for v in data.values()):
                    raise ValueError('invalid click')
            elif data:
                raise ValueError('arguments on a non-coordinate action')
            pending = game, action
            last_dispatch[game] = 'outcome_unknown'
        elif kind == 'dispatch_not_sent':
            if pending is None or pending[0] != game:
                raise ValueError('pre-dispatch rejection without a pending dispatch')
            pending = None
            last_dispatch[game] = 'not_sent'
        elif kind == 'transition':
            check_observation(row['before'])
            check_observation(row['after'])
            if pending != (game, row['action']) or row['before'] != current[game] or row['dispatch'] != 'acknowledged':
                raise ValueError('transition continuity mismatch')
            before = np.asarray(row['before']['frames'][-1])
            frames = [np.asarray(f) for f in row['after']['frames']]
            shape = all(f.shape == before.shape for f in frames)
            facts = {'any_frame_changed': any(not np.array_equal(before, f) for f in frames) if shape else None,
                     'final_frame_changed': not np.array_equal(before, frames[-1]) if shape else None,
                     'level_increased': row['after']['levels_completed'] > row['before']['levels_completed']}
            if row['observed'] != facts:
                raise ValueError('effect derivation mismatch')
            for predicate, check in row['prediction_checks'].items():
                if predicate not in facts or check['observed'] != facts[predicate]:
                    raise ValueError('prediction observation mismatch')
                expected = None if check['predicted'] is None or facts[predicate] is None else check['predicted'] == facts[predicate]
                if check['correct'] != expected:
                    raise ValueError('prediction score mismatch')
            current[game], pending = row['after'], None
            acknowledged[game] = acknowledged.get(game, 0) + 1
            last_dispatch[game] = 'acknowledged'
        elif kind == 'scorecard_close_acknowledged':
            closed = True
    if config is None or recorded_summary is None:
        raise ValueError('missing configuration or final summary event')
    # Only the finalization clock/status is added after the event log has closed.
    for key, value in recorded_summary.items():
        if key not in ('elapsed_seconds', 'full_lifecycle_complete') and summary.get(key) != value:
            raise ValueError('summary differs from finalized event evidence: ' + key)
    if summary['elapsed_seconds'] > config['run_seconds'] and summary['full_lifecycle_complete']:
        raise ValueError('accepted over-deadline lifecycle')
    if calls > config['max_model_calls']:
        raise ValueError('model request cap exceeded')
    seen = set()
    for row in summary['games']:
        game = row['game_id']
        if game in seen:
            raise ValueError('duplicate summary game')
        seen.add(game)
        if row['actions_acknowledged'] != acknowledged.get(game, 0):
            raise ValueError('summary action mismatch')
        uncertain = int(pending is not None and pending[0] == game)
        if type(row['actions_uncertain']) is not int or row['actions_uncertain'] != uncertain:
            raise ValueError('summary uncertain-action mismatch')
        if row['actions_acknowledged'] + row['actions_uncertain'] > config['max_actions_per_game']:
            raise ValueError('action cap exceeded')
        if row['levels_completed'] is not None and row['levels_completed'] != current[game]['levels_completed'] - initial[game]:
            raise ValueError('summary completion mismatch')
        expected_state = current[game]['state'] if game in current else None
        if row.get('final_state') != expected_state:
            raise ValueError('summary final-state mismatch')
        if row.get('last_dispatch_status') != last_dispatch.get(game):
            raise ValueError('summary last-dispatch status mismatch')
        if row['stop_reason'] in ('win', 'game_over') and row['stop_reason'] != (expected_state or '').lower():
            raise ValueError('terminal stop reason contradicts final state')
        if row['stop_reason'] == 'action_cap' and expected_state in ('WIN', 'GAME_OVER'):
            raise ValueError('terminal final state mislabeled as action_cap')
    if seen != attempted:
        raise ValueError('attempted-game coverage mismatch')
    if selected is not None and (summary['selected_games'] != selected
            or summary['games_not_started'] != [g for g in selected if g not in attempted]):
        raise ValueError('selected/unstarted game accounting mismatch')
    if card != summary['scorecard_id']:
        raise ValueError('scorecard binding mismatch')
    if summary['full_lifecycle_complete'] and (summary['problems'] or not closed or pending is not None):
        raise ValueError('successful receipt contradicts evidence')
    return {'record_integrity_verified': True, 'events': sequence, 'model_requests_entered': calls,
            'model_responses_recorded': responses, 'actions_acknowledged': sum(acknowledged.values()),
            'actions_uncertain': int(pending is not None), 'games_attempted': len(attempted),
            'levels_recorded': sum(r['levels_completed'] or 0 for r in summary['games']),
            'engine_replay_verified': False, 'provider_billing_verified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder')
    print(json.dumps(audit(parser.parse_args().folder), sort_keys=True))
