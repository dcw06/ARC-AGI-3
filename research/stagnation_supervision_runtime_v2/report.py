"""Post-run study report for runtime v2 evidence (hand-written; CPU only; reads retained evidence, never repairs it).

The endpoints are computed by the unchanged frozen evaluator (closed_loop/evaluate.py via the runtime v2 target
evaluator). This module only arranges them so that the quantities the protocol keeps apart stay apart:
  behavioural_recovery       loop exit plus quiet period at detector-defined opportunities (primary endpoint);
  state_novelty_in_windows   new frames and new (state, action) pairs inside those windows (never the endpoint);
  completed_levels           environment-reported level increases (the solving endpoint);
  false_interruptions        the provisional gate over reviewed continuation controls only (wa30), with the
                             all-cases rate reported as descriptive;
  realised_cost              calls, tokens and latency per arm;
and adds the descriptive ls20 display/oscillation report required by the 2026-10-02 retention decision. Nothing
here feeds a decision rule; display-driven novelty cannot become recovery or solving credit.
"""
from pathlib import Path


def study_report(output, spec, *, mode='live', session='1', internal_seconds=None):
    from research.stagnation_supervision_runtime_v2.target_evaluate import evaluate_target
    from research.stagnation_supervision_runtime_v2.verification import display_report
    target = evaluate_target(output, spec, mode=mode, session=session, internal_seconds=internal_seconds)
    trajectory = target['trajectory']
    recovery = trajectory.get('recovery') or {}
    endpoints = {
        'behavioural_recovery': {arm: {k: a.get(k) for k in ('episodes', 'opportunities', 'status', 'recovery_rate_decided',
                                                             'actions_to_exit', 'censored_horizon_firings', 'per_episode')}
                                 for arm, a in recovery.items()},
        'state_novelty_in_windows': {arm: {k: a.get(k) for k in ('new_frames_in_window', 'new_state_action_pairs_in_window')}
                                     for arm, a in recovery.items()},
        'completed_levels': {'per_arm': trajectory.get('solving'),
                             'level_completed_in_recovery_windows': {arm: a.get('level_completed_in_window')
                                                                     for arm, a in recovery.items()}},
        'false_interruptions': trajectory.get('false_interruptions'),
        'false_interruptions_calls': trajectory.get('false_interruptions_calls'),
        'realised_cost': trajectory.get('realised_cost'),
    }
    ls20 = []
    try:
        from research.stagnation_supervision_v1.closed_loop import bridge as B
        from research.stagnation_supervision_v1.closed_loop.evaluate import _replay_module
        from research.stagnation_supervision_v1.closed_loop.evidence import load_verified
        run = load_verified(Path(output) / 'worker/run')
        replay = _replay_module()
        for episode in run['episodes']:
            if episode['game_id'].startswith('ls20') and episode['steps']:
                raws = [replay.raw_step(episode['episode_id'], s, None, B.SOURCE) for s in episode['steps']]
                ls20.append({'episode_id': episode['episode_id'], 'arm': episode['arm'], **display_report(raws)})
    except Exception as exc:  # the report is descriptive; its failure never changes the technical verdict
        ls20 = [{'error': f'{type(exc).__name__}: {str(exc)[:200]}'}]
    return {'version': 'stagnation_supervision_runtime_v2_study_report_v1', 'mode': mode, 'session': session,
            'technically_complete': target['technically_complete'], 'target_accepted': target['target_accepted'],
            'lifecycle_verified': target['lifecycle_verified'], 'problems': target['problems'],
            'endpoints': endpoints if target['trajectory'].get('technically_complete') else None,
            'endpoints_withheld_reason': None if target['trajectory'].get('technically_complete') else
            'a technically incomplete run reports no outcome result (protocol v2 section 9)',
            'ls20_display_and_oscillation': {'decision': 'reports/stagnation_supervision_v1_ls20_decision.json',
                                             'episodes': ls20,
                                             'scope': 'descriptive post-hoc report; not an endpoint, label, gate or mask'},
            'limitations': ['exposed development games; not real-game or generalisation evidence',
                            'ls20 is exploratory: display-driven novelty and oscillation; not a gate control',
                            'the false-interruption gate is not certifiable with one reviewed control (wa30)']}
