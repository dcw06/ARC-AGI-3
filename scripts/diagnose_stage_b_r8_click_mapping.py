"""Offline click-mapping check for the R8 diagnosis (no model calls, no GPU).

Each probe starts a fresh seed-0 ar25 episode in the manifest-verified offline development
engine, confirms the exact R8 initial state, dispatches one ACTION6 and records what changed.
This is evaluation-only evidence about the engine's response to click coordinates. It is not
a policy input, and it reveals no more than one click's visible effect per probe.
"""
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'reports/perception_stage_b_r8_click_mapping.json'
R8_INITIAL = '2318e77b3f8aceb099c4e7b625ede6b23bf465b59e0575c587e5964ff29636d9'
# (label, x, y, why) — x is the column, y the row, as sent in R8's ACTION6 action_data.
PROBES = [
    ('r8_control_click', 16, 16, 'R8 control clicks, both actions (harness validation)'),
    ('r8_target_click_1', 17, 16, 'R8 target arm, first action'),
    ('reference_A_solid', 20, 15, 'inside reviewer object A, colour 5'),
    ('reference_A_marking', 19, 16, 'inside A on a colour-0 marking'),
    ('reference_A_left_edge', 18, 16, 'A left edge, one cell right of the (17,16) click'),
    ('reference_B_solid', 37, 20, 'inside reviewer object B'),
    ('reference_C_solid', 52, 48, 'inside reviewer object C'),
    ('stripe', 31, 10, 'colour-10 stripe (reviewer non-object region)'),
    ('far_background', 5, 5, 'background far from every object'),
]


NON_CLICK_ACTIONS = [1, 2, 3, 4, 5, 7]


def probe(games, recordings, label, x, y, action_id=6):
    from research.grounded_action_v1.engine import DevelopmentAdapter
    adapter = DevelopmentAdapter(label, games, recordings)
    try:
        before = adapter.bootstrap()
        if before.canonical_hash != R8_INITIAL:
            raise ValueError('initial state differs from R8')
        grid = before.latest_frame.tolist()
        data = {'x': x, 'y': y} if action_id == 6 else {}
        post, _ = adapter.dispatch({'action_id': action_id, 'action_data': data}, before)
        frames = [f.tolist() for f in post.frames]
        changes = [sum(a != b for ra, rb in zip(grid, f) for a, b in zip(ra, rb)) if len(f) == len(grid) else None
                   for f in frames]
        changed_cells = sorted({(cx, cy) for f in frames if len(f) == len(grid)
                                for cy, row in enumerate(f) for cx, v in enumerate(row) if grid[cy][cx] != v})
        return {'label': label, 'action_id': action_id, 'x': x, 'y': y,
                'value_at_click': grid[y][x] if action_id == 6 else None,
                'returned_frames': len(frames), 'changed_cells_per_frame': changes,
                'state_hash_changed': post.canonical_hash != before.canonical_hash,
                'levels_before': before.levels_completed, 'levels_after': post.levels_completed,
                'state_after': str(post.state.name if hasattr(post.state, 'name') else post.state),
                'changed_bbox': [min(c[0] for c in changed_cells), min(c[1] for c in changed_cells),
                                 max(c[0] for c in changed_cells), max(c[1] for c in changed_cells)] if changed_cells else None}
    finally:
        adapter.close()


def main():
    from research.grounded_action_v1.engine import restore_game_mount
    with tempfile.TemporaryDirectory() as folder:
        games = restore_game_mount(Path(folder) / 'games')
        rows = []
        for label, x, y, why in PROBES:
            row = probe(games, Path(folder) / 'recordings', label, x, y)
            row['why'] = why
            rows.append(row)
        for action_id in NON_CLICK_ACTIONS:
            row = probe(games, Path(folder) / 'recordings', f'action_{action_id}', None, None, action_id)
            row['why'] = 'one non-coordinate action from the R8 initial state'
            rows.append(row)
    report = {'scope': 'offline development engine; evaluation-only click-mapping evidence; not a policy input',
              'game': 'ar25-0c556536', 'seed': 0, 'initial_state_hash': R8_INITIAL,
              'coordinate_convention': 'action_data x = column, y = row of the 64x64 display frame', 'probes': rows,
              'model_calls': 0, 'gpu_runs': 0}
    OUTPUT.write_text(json.dumps(report, indent=2) + '\n')
    for r in rows:
        where = f"({r['x']:2d},{r['y']:2d}) value={r['value_at_click']:2d}" if r['action_id'] == 6 else f"ACTION{r['action_id']}".ljust(16)
        print(f"{r['label']:24s} {where} changed={r['changed_cells_per_frame']} "
              f"frames={r['returned_frames']} levels {r['levels_before']}->{r['levels_after']} bbox={r['changed_bbox']}")


if __name__ == '__main__':
    main()
