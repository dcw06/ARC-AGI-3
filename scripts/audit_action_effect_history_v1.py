"""Worst-case request audit for the action-effect-history comparison (no model calls).

--build (development env): construct exact requests from each case's real initial observation.
--tokenize (pinned tokenizer env): count prompt tokens with the frozen Qwen3-VL tokenizer.
"""
import argparse
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REQUESTS = ROOT / '.cache/action_effect_history_v1_audit_requests.json'
REPORT = ROOT / 'reports/action_effect_history_v1_token_audit.json'
CASES = ('ar25-0c556536', 's5i5-18d95033', 'wa30-ee6fef47')
MAX_FRAMES_PER_ENTRY = 8


def worst_history():
    """Four current-segment entries, each at the admitted maximum of returned frames and changes."""
    from research.action_effect_v1.records import EffectHistory, VERSION
    history = EffectHistory(limit=16)
    for step in range(4):
        history.append({'version': VERSION, 'action_id': 6, 'action_data': {'x': 63, 'y': 63}, 'status': 'acknowledged',
                        'returned_frame_count': MAX_FRAMES_PER_ENTRY, 'changed_cells_by_frame': [4096] * MAX_FRAMES_PER_ENTRY,
                        'final_frame_changed': True, 'level_delta': 0, 'reset': False})
    return history


def build():
    from arc_agi import Arcade, OperationMode
    from agent.framework_adapter import LocalFrameworkAdapter
    from agent.state import GameRuntimeState
    from research.grounded_action_v1.engine import restore_game_mount
    from research.action_effect_history_v1 import contract
    rows = []
    with tempfile.TemporaryDirectory() as folder:
        games = restore_game_mount(Path(folder) / 'games')
        for game_id in CASES:
            adapter = LocalFrameworkAdapter(Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=str(games),
                                                   recordings_dir=str(Path(folder) / 'rec')), seed_by_game={game_id: 0})
            adapter.open_scorecard(tags=['token-audit-bootstrap-only'])
            client = adapter.bootstrap(game_id)
            obs = client.observation
            first = GameRuntimeState(obs, action_budget_limit=12)
            # Steady state without dispatching: replay the initial observation as two prior transitions
            # so the payload carries current, previous and recent final grids (the admitted maximum).
            steady = GameRuntimeState(obs, action_budget_limit=12)
            for i in range(2):
                steady.counters.conservative_spent_actions += 1
                steady.replace_observation(obs, action_id=6 if 6 in obs.available_actions else sorted(obs.available_actions)[0],
                                           action_data={'x': 63, 'y': 63} if 6 in obs.available_actions else {}, transition_id=f'audit-{i}')
            for label, runtime, history in (('first_baseline', first, None), ('first_history', first, None),
                                            ('steady_baseline', steady, None), ('steady_history_worst', steady, worst_history())):
                arm = 'history' if 'history' in label else 'baseline'
                rows.append({'game_id': game_id, 'label': label, 'arm': arm,
                             'request': contract.policy_request(runtime, arm, history)})
            adapter.finalize_client(client)
            adapter.close_scorecard()
    REQUESTS.parent.mkdir(exist_ok=True)
    REQUESTS.write_text(json.dumps(rows))
    print('built', len(rows), 'requests')


def tokenize(folder):
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(folder), local_files_only=True, trust_remote_code=False)
    rows = json.loads(REQUESTS.read_bytes())
    out = []
    for row in rows:
        r = row['request']
        ids = tokenizer.apply_chat_template(r['messages'], tokenize=True, add_generation_prompt=True, truncation=False,
                                            **r['chat_template_kwargs'])
        size = len(json.dumps(r).encode())
        out.append({'game_id': row['game_id'], 'label': row['label'], 'prompt_tokens': len(ids),
                    'max_completion_tokens': r['max_tokens'], 'request_bytes': size,
                    'within_limits': len(ids) <= 60000 and len(ids) + r['max_tokens'] <= 65536})
    report = {'scope': 'exact requests from each case initial observation; steady state carries current, previous and '
                       'one recent final grid; worst history = 4 entries x 8 frames x 4096 changed cells',
              'tokenizer': 'pinned Qwen3-VL-30B-A3B-Instruct-FP8 tokenizer (.cache/phase4-tokenizer)',
              'rows': out, 'max_prompt_tokens': max(r['prompt_tokens'] for r in out),
              'history_field_overhead_tokens': {g: next(r['prompt_tokens'] for r in out if r['game_id'] == g and r['label'] == 'steady_history_worst')
                                                - next(r['prompt_tokens'] for r in out if r['game_id'] == g and r['label'] == 'steady_baseline')
                                                for g in CASES},
              'model_calls': 0}
    REPORT.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}, indent=1))
    for r in out:
        print(r)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=('build', 'tokenize'))
    p.add_argument('--tokenizer', type=Path, default=ROOT / '.cache/phase4-tokenizer')
    a = p.parse_args()
    build() if a.mode == 'build' else tokenize(a.tokenizer)
