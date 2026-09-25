"""Record each development game's initial control set (bootstrap only; no actions dispatched).

Used by the case-selection rule, which must not depend on any action outcome. Reads the
manifest-verified offline development games; makes no model calls.
"""
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'reports/action_effect_history_v1_control_inventory.json'


def main():
    from arc_agi import Arcade, OperationMode
    from agent.framework_adapter import LocalFrameworkAdapter
    from research.grounded_action_v1.engine import restore_game_mount
    ledger = json.loads((ROOT / 'config/holdout_ledger.yaml').read_bytes())
    rows = []
    with tempfile.TemporaryDirectory() as folder:
        games = restore_game_mount(Path(folder) / 'games')
        for game_id in ledger['development']:
            adapter = LocalFrameworkAdapter(Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=str(games),
                                                   recordings_dir=str(Path(folder) / 'recordings')),
                                            seed_by_game={game_id: 0})
            adapter.open_scorecard(tags=['control-inventory-bootstrap-only'])
            client = adapter.bootstrap(game_id)
            obs = client.observation
            frame = obs.latest_frame
            rows.append({'game_id': game_id, 'available_actions': sorted(int(a) for a in obs.available_actions),
                         'frame_shape': [int(frame.shape[0]), int(frame.shape[1])], 'returned_frames': len(obs.frames),
                         'win_levels': obs.win_levels, 'initial_canonical_hash': obs.canonical_hash})
            adapter.finalize_client(client)
            adapter.close_scorecard()
    report = {'scope': 'initial observation only, seed 0; zero actions dispatched; no outcomes inspected',
              'source': 'config/holdout_ledger.yaml development partition', 'games': rows}
    OUTPUT.write_text(json.dumps(report, indent=2) + '\n')
    for r in rows:
        print(r['game_id'], r['available_actions'], r['frame_shape'], 'win_levels', r['win_levels'])


if __name__ == '__main__':
    main()
