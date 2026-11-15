"""Write the pilot configurations: one file per condition, each the November 6 configuration plus its switches.

Every condition starts each game by repeating the first 100 saved actions of the November 6 run (no model
calls) and then plays 100 more. The files are written with live_enabled false: nothing can run from them
until that is changed on purpose, and a run still needs the command-line consent flags.

Usage: make_configs.py   (writes config/recovery_v1/*.json)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTROL = ROOT / 'config/claude_arc_v1.opus55_competition.json'
BASELINES = ROOT / 'reports/arc_agi3_loss_audit/data/headroom.json'
SAVED = '.cache/claude_arc_runs/opus55-competition-20261106T054112Z/events.jsonl'
# The five games where the November 6 run had already spent more than the human baseline on its unfinished level.
GAMES = ['tn36', 'su15', 'bp35', 'cd82', 'lf52']
RESUMED, NEW = 100, 100

# The level check: first when actions on the level reach the human baseline, but not before 30 actions.
LEVEL = {'model_may_reset': True, 'stall_level_ratio': 1.0, 'stall_level_floor': 30}
CONDITIONS = {
    'r0_control': {},
    'r0m_reset_allowed': {'model_may_reset': True},
    'r1_board': {'model_may_reset': True, 'stall_window': 6},
    'r1_level': dict(LEVEL),
    'r2a_replay': {**LEVEL, 'replay_after_reset': True},
    'r2b_payback': {**LEVEL, 'recovery_pricing': True},
    'r2_payback_replay': {**LEVEL, 'recovery_pricing': True, 'replay_after_reset': True},
}


def main():
    control = json.loads(CONTROL.read_text())
    meta = json.loads(BASELINES.read_text())['meta']
    baselines = {g.split('-')[0]: v['baseline'] for g, v in meta.items() if g.split('-')[0] in GAMES}
    out = ROOT / 'config/recovery_v1'
    out.mkdir(parents=True, exist_ok=True)
    for name, switches in CONDITIONS.items():
        value = {**control, 'live_enabled': False, 'mode': 'online', 'games': GAMES,
                 'max_actions_per_game': RESUMED + NEW,
                 # One call per new action plus room for rejected replies; resumed actions make no call.
                 'max_model_calls': len(GAMES) * NEW + 200,
                 'resume_events': SAVED, 'resume_actions': RESUMED, **switches}
        if switches.get('stall_level_ratio'):
            value['level_baselines'] = baselines
        (out / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')
        print('wrote', name)
    # Live mechanics check: all five games, level check and replay on, two new actions each. It shows
    # whether the saved positions replay on the live games and whether the first check is answered in the
    # right form. The pay-back rule is left out: with two actions left it would refuse every reset.
    smoke = {**control, 'live_enabled': False, 'mode': 'online', 'games': GAMES,
             'max_actions_per_game': RESUMED + 2, 'max_model_calls': 30, 'resume_events': SAVED,
             'resume_actions': RESUMED, **CONDITIONS['r2a_replay'], 'level_baselines': baselines}
    (out / 'live_check.json').write_text(json.dumps(smoke, indent=2) + '\n')
    print('wrote live_check')


if __name__ == '__main__':
    main()
