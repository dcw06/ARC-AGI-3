"""Tier B probe: CPU-only scripted check for a second continuation-appropriate development game (Track 3).

Approved scope: CPU only, offline engine, no model. Written and committed before it was run.

Candidates, in the order written in protocol v1 (the no-coordinate replacement order frozen for
action-effect-history v1, after wa30): ls20-9607627b, tr87-cd924810, g50t-5849a774. All three are in the
development partition of config/holdout_ledger.yaml (checked below); no holdout game is opened.

Procedure per candidate (one fixed policy; no other policy is tried):
- games are restored from the manifest-verified development archive (`research.grounded_action_v1.engine.
  restore_game_mount`), game seed 0, offline `Arcade` through `agent.framework_adapter.LocalFrameworkAdapter`;
- 12 actions from the action-effect-history v1 environment check's own `scripted(step, legal)` (imported from
  scripts/check_action_effect_history_v1_environments.py, not copied): legal ids in rotation, ACTION6 on its fixed
  lattice; the episode stops early at WIN or GAME_OVER, with no reset;
- every step becomes a transition_evidence_v2 raw transition (frames, levels, state, full_reset and the reported
  available actions before and after) and a v2 record; a dispatch exception is retained as `outcome_unknown`.

Criterion (protocol v1, continuation-appropriate case), over acknowledged, observed steps:
  qualifies  <=>  at least 75% of them reach a final frame new to the episode
                  AND their median changed-cell count (final frame vs pre-action frame) is greater than 4,
  and at least 6 such steps exist (a probe stopped by GAME_OVER after fewer steps cannot qualify).
Candidates are probed in order and probing stops at the first that qualifies; every probed candidate is reported.
Limitation, stated before running: the rotation alternates opposite actions, which can return to earlier frames, so
a game can fail this criterion while still rewarding continued action under another policy. That is a property
of this fixed probe, not of the game, and no second policy is tried.

The result is written once; a second run refuses to overwrite it. Run:
  python -m research.stagnation_supervision_v1.tier_b_probe
"""
import importlib.util
import json
from pathlib import Path
import statistics
import tempfile

from research.transition_evidence_v2 import transition as T2, vocabulary as V

VERSION = 'stagnation_supervision_v1_tier_b_probe'
ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / 'reports/stagnation_supervision_v1_tier_b_probe.json'
CANDIDATES = ('ls20-9607627b', 'tr87-cd924810', 'g50t-5849a774')
STEPS = 12
MIN_NEW_FRACTION = 0.75
MIN_MEDIAN_CELLS = 4  # strictly greater than
MIN_OBSERVED_STEPS = 6


def environment_check_module():
    path = ROOT / 'scripts/check_action_effect_history_v1_environments.py'
    spec = importlib.util.spec_from_file_location('check_action_effect_history_v1_environments', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def development_games():
    return set(json.loads((ROOT / 'config/holdout_ledger.yaml').read_text(encoding='utf-8'))['development'])


def observation(obs):
    return {'frames': [f.tolist() for f in obs.frames], 'levels_completed': int(obs.levels_completed),
            'state': obs.state.name, 'full_reset': bool(obs.full_reset),
            'available_actions': sorted(int(a) for a in obs.available_actions)}


def assess(records):
    """The criterion over acknowledged, observed steps (records from transition_evidence_v2.history)."""
    seen, new, cells = set(), [], []
    for r in records:
        seen.add(r['observations']['before_frames_sha256'][-1])
        frames = r['measurements']['frames']
        if r['dispatch']['status'] != V.ACKNOWLEDGED or not frames or not frames[-1]['valid']:
            continue
        final = frames[-1]
        new.append(final['sha256'] not in seen)
        seen.add(final['sha256'])
        count = final['vs_pre']['changed_cells']
        cells.append(count['value'] if count['status'] == 'measured' else None)
    measured = [c for c in cells if c is not None]
    fraction = sum(new) / len(new) if new else None
    median = statistics.median(measured) if measured else None
    qualifies = (len(new) >= MIN_OBSERVED_STEPS and fraction >= MIN_NEW_FRACTION and median is not None
                 and median > MIN_MEDIAN_CELLS)
    return {'observed_steps': len(new), 'new_frame_steps': sum(new), 'new_frame_fraction': fraction,
            'changed_cells_per_step': cells, 'median_changed_cells': median, 'qualifies': bool(qualifies)}


def probe(game_id, games, recordings, scripted):
    from arc_agi import Arcade, OperationMode
    from arcengine import GameState
    from agent.action import ActionDecision
    from agent.framework_adapter import LocalFrameworkAdapter
    adapter = LocalFrameworkAdapter(Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=str(games),
                                           recordings_dir=str(recordings)), seed_by_game={game_id: 0})
    adapter.open_scorecard(tags=['stagnation-supervision-v1-tier-b-probe'])
    raws, error, terminal, client = [], None, None, None
    try:
        client = adapter.bootstrap(game_id)
        obs = client.observation
        for step in range(STEPS):
            if obs.state in (GameState.WIN, GameState.GAME_OVER):
                terminal = obs.state.name
                break
            action = scripted(step, obs.available_actions)
            raw = {'identity': {'episode_id': 'tier-b-' + game_id, 'action_index': step},
                   'before': observation(obs), 'proposal': None, 'dispatched': action,
                   'environment_source': 'offline_development_engine_scripted_probe'}
            try:
                post = adapter.dispatch(client, ActionDecision(**action, source='tier_b_probe',
                                                               decision_id=f'tier-b-{game_id}-{step}'))
            except Exception as exc:  # retained; never a no-op observation
                raw['outcome'] = {'status': 'outcome_unknown', 'reason': type(exc).__name__ + ': ' + str(exc)[:160]}
                raws.append(raw)
                break
            raw['outcome'] = {'status': 'acknowledged', 'after': observation(post)}
            raws.append(raw)
            obs = post
        if terminal is None and obs.state in (GameState.WIN, GameState.GAME_OVER):
            terminal = obs.state.name
    except Exception as exc:
        error = type(exc).__name__ + ': ' + str(exc)[:200]
    finally:
        closed = True
        try:
            if client is not None:
                adapter.finalize_client(client)
            adapter.close_scorecard()
        except Exception as exc:
            closed, error = False, error or type(exc).__name__ + ': ' + str(exc)[:200]
    records = T2.history(raws) if raws else []
    problems = T2.verify_history(records, raws) if raws else []
    steps = [{'step': r['identity']['action_index'], 'action': r['action']['dispatched'],
              'dispatch': r['dispatch']['status'], 'visual_effect': r['measurements']['visual_effect']['status'],
              'events': r['environment']['events'], 'available_actions_before': r['context']['available_actions_before']}
             for r in records]
    return {'game_id': game_id, 'error': error, 'closed': closed, 'terminal_state': terminal,
            'dispatches': len(raws), 'record_problems': problems, 'steps': steps, **assess(records)}


def run():
    development = development_games()
    if not set(CANDIDATES) <= development:
        raise ValueError('a Tier B candidate is not in the development partition')
    scripted = environment_check_module().scripted
    from research.grounded_action_v1.engine import restore_game_mount
    results, selected = [], None
    with tempfile.TemporaryDirectory() as folder:
        games = restore_game_mount(Path(folder) / 'games')
        for game_id in CANDIDATES:
            result = probe(game_id, games, Path(folder) / 'rec' / game_id, scripted)
            results.append(result)
            if result['qualifies'] and not result['error']:
                selected = game_id
                break
    return {'version': VERSION, 'candidates_in_order': list(CANDIDATES), 'policy': 'action-effect-history v1 '
            'environment-check scripted(step, legal), 12 steps, game seed 0, stop at WIN/GAME_OVER, no reset',
            'criterion': {'min_new_frame_fraction': MIN_NEW_FRACTION, 'median_changed_cells_greater_than':
                          MIN_MEDIAN_CELLS, 'min_observed_steps': MIN_OBSERVED_STEPS},
            'probed': results, 'selected': selected,
            'unprobed': [g for g in CANDIDATES if g not in {r['game_id'] for r in results}]}


if __name__ == '__main__':
    if RESULTS.exists():
        raise SystemExit('refusing to overwrite the write-once result: ' + str(RESULTS))
    result = run()
    RESULTS.write_text(json.dumps(result, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    for r in result['probed']:
        print(r['game_id'], 'qualifies' if r['qualifies'] else 'does not qualify', r['observed_steps'],
              r['new_frame_fraction'], r['median_changed_cells'], r['terminal_state'], r['error'] or '')
    print('selected:', result['selected'])
