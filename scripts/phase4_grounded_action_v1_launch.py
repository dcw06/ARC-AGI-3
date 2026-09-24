"""First-cell Stage B target lifecycle; launch only with separate reviewed authority."""
import argparse
import json
from pathlib import Path
import tempfile
import time

from certification.phase4_integrated_v2.evidence import EvidenceStore
from research.grounded_action_v1.authority import consume_runtime, require

ROOT = Path(__file__).resolve().parents[1]


def run(output, working, *, started, root=ROOT):
    require(root)
    if not 0 <= time.monotonic() - started < 450:
        raise TimeoutError('Stage B first-cell installation deadline')
    consume_runtime(working, root)  # One attempt is consumed before installation.
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    control = EvidenceStore(output, 'control')
    error = None
    report = None
    try:
        manifest = json.loads((root / 'reports/phase4_v2_offline_package.json').read_bytes())
        mount = Path('/kaggle/input/competitions/arc-prize-2026-arc-agi-3')
        candidates = [Path('/kaggle/input/datasets/driessmit1/arc3-vllm-h100-wheelhouse-v3'),
                      Path('/kaggle/input/arc3-vllm-h100-wheelhouse-v3')]
        wheelhouse = next(path for path in candidates if path.is_dir())
        with tempfile.TemporaryDirectory(prefix='stage-b-dependencies-') as folder:
            from certification.phase4_integrated_v2.game_assets import stage_games
            from certification.phase4_integrated_v2.prepare import prepare
            from certification.phase4_integrated_v2.dependencies import freeze, thaw
            rootdir = Path(folder)
            games = stage_games(mount / 'environment_files', rootdir / 'games', manifest)
            pair = prepare(rootdir, output, wheelhouse,
                           mount / 'arc_agi_3_wheels', manifest, started)
            try:
                freeze(rootdir)
                from research.grounded_action_v1.target_supervisor import run_live
                report = run_live(output, working, pair['game'], pair['model'], games,
                                  started=started, claimed=True, prepared=True)
            finally:
                thaw(rootdir)
    except Exception as exc:
        error = type(exc).__name__ + ': ' + str(exc)[:256]
    elapsed = time.monotonic() - started
    if elapsed >= 3300:
        error = error or 'Stage B first-cell hard deadline exceeded'
    receipt = {'scope': 'stage_b_first_cell', 'elapsed_seconds': elapsed,
               'error': error, 'dependency_trees_removed':
               not Path(folder).exists() if 'folder' in locals() else None,
               'provider_reconciliation_required': True, 'phase4_complete': False,
               'study_status': report['status'] if report else None}
    control.save('notebook-cost.json', receipt)
    if error or report is None or report['status'] != 'development_study_complete_pending_archive_review':
        raise RuntimeError(error or 'Stage B target supervisor did not complete')
    return receipt


def main():
    require()  # No installation, provider query or GPU use without Stage B authority.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--working', type=Path, required=True)
    parser.add_argument('--started', type=float, required=True)
    args = parser.parse_args()
    run(args.output, args.working, started=args.started)


if __name__ == '__main__':
    main()
