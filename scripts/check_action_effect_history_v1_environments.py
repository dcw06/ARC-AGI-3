"""CPU environment/dispatch compatibility check for the selected cases (technical fields only).

Drives the same offline dispatch path the runner uses with a fixed scripted sequence of legal
actions (no model). Records only whether each dispatch was acknowledged with well-formed frames,
and whether a terminal state stopped the episode. It deliberately does not compute changed cells,
level counts or any other effect, so it is not treatment evidence.
"""
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'reports/action_effect_history_v1_environment_check.json'
CASES = ('ar25-0c556536', 's5i5-18d95033', 'wa30-ee6fef47')
LATTICE = [(8, 8), (24, 8), (40, 8), (56, 8), (8, 24), (24, 24), (40, 24), (56, 24), (8, 40), (24, 40), (40, 40), (56, 40)]


def scripted(step, legal):
    legal = sorted(legal)
    action_id = legal[step % len(legal)]
    return {'action_id': action_id, 'action_data': {'x': LATTICE[step][0], 'y': LATTICE[step][1]} if action_id == 6 else {}}


def check(game_id, games, recordings):
    from arc_agi import Arcade, OperationMode
    from arcengine import GameState
    from agent.action import ActionDecision
    from agent.framework_adapter import LocalFrameworkAdapter
    adapter = LocalFrameworkAdapter(Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=str(games),
                                           recordings_dir=str(recordings)), seed_by_game={game_id: 0})
    card = adapter.open_scorecard(tags=['environment-compatibility-check'])
    rows, error, terminal = [], None, None
    client = None
    try:
        client = adapter.bootstrap(game_id)
        obs = client.observation
        bootstrap_ok = len(obs.frames) >= 1 and all(f.shape == (64, 64) for f in obs.frames)
        for step in range(12):
            if obs.state in (GameState.WIN, GameState.GAME_OVER):
                terminal = obs.state.name
                break
            action = scripted(step, obs.available_actions)
            try:
                post = adapter.dispatch(client, ActionDecision(**action, source='environment_check',
                                                               decision_id=f'check-{game_id}-{step}'))
            except Exception as exc:  # retained as a technical failure, never as a no-op
                rows.append({'step': step, 'action_id': action['action_id'], 'status': 'dispatch_exception',
                             'error': type(exc).__name__ + ': ' + str(exc)[:160]})
                break
            frames = list(post.frames)
            rows.append({'step': step, 'action_id': action['action_id'], 'status': 'acknowledged',
                         'returned_frames': len(frames), 'empty_frame_response': len(frames) == 0,
                         'frames_64x64': bool(frames) and all(f.shape == (64, 64) for f in frames)})
            obs = post
    except Exception as exc:
        error = type(exc).__name__ + ': ' + str(exc)[:200]
        bootstrap_ok = False if client is None else locals().get('bootstrap_ok', False)
    finally:
        closed = True
        try:
            if client is not None:
                adapter.finalize_client(client)
            adapter.close_scorecard()
        except Exception as exc:
            closed, error = False, error or type(exc).__name__ + ': ' + str(exc)[:200]
    compatible = (error is None and bootstrap_ok and closed and rows and
                  all(r['status'] == 'acknowledged' and r['frames_64x64'] and not r['empty_frame_response'] for r in rows))
    return {'game_id': game_id, 'compatible': bool(compatible), 'bootstrap_frames_ok': bootstrap_ok,
            'dispatches': len(rows), 'stopped_by_terminal_state': terminal is not None,
            'scorecard_and_client_closed': closed, 'error': error, 'dispatch_records': rows}


def main():
    from research.grounded_action_v1.engine import restore_game_mount
    with tempfile.TemporaryDirectory() as folder:
        games = restore_game_mount(Path(folder) / 'games')
        results = [check(g, games, Path(folder) / 'rec' / g) for g in CASES]
    report = {'scope': 'technical compatibility only: acknowledgement, frame count/shape, terminal stop, closure; '
                       'no changed-cell, level or effect statistics are computed; not treatment evidence',
              'script': 'fixed scripted legal actions, no model', 'results': results,
              'all_compatible': all(r['compatible'] for r in results)}
    OUTPUT.write_text(json.dumps(report, indent=2) + '\n')
    for r in results:
        print(r['game_id'], 'compatible' if r['compatible'] else 'INCOMPATIBLE', 'dispatches', r['dispatches'],
              'terminal-stop' if r['stopped_by_terminal_state'] else '', r['error'] or '')


if __name__ == '__main__':
    main()
