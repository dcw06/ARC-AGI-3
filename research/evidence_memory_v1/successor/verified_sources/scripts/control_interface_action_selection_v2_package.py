# Derived by scripts/build_control_interface_action_selection_v2.py; edit the derivation.
"""Direct publisher smoke test packaging (no upload, no reservation, no GPU).

  python scripts/control_interface_action_selection_v2_package.py review-build --revision 1
      freeze notebooks/control-interface-action-selection-v2-review-r<N>/ (GPU disabled; review snapshot, not an approval)
  python scripts/control_interface_action_selection_v2_package.py review-check --revision 1
      execute that notebook's code locally with no GPU and a decoy nvidia-smi; it must stop at the live gate before
      any installation, model or GPU activity; writes reports/control_interface_action_selection_v2_review_check_r<N>.json
  python scripts/control_interface_action_selection_v2_package.py launch-build
      build the launch package; refuses unless every live-gate condition holds
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.control_interface_action_selection_v2.binding import LiveRefused, check_sources, sha256  # noqa: E402
from research.control_interface_action_selection_v2.notebook import build_review, launch_artifacts  # noqa: E402

DECOY = '#!/bin/sh\necho "$0 $*" >> "{log}"\nexit 1\n'


def review_folder(revision):
    return ROOT / f'notebooks/control-interface-action-selection-v2-review-r{revision}'


def review_check(revision):
    folder = review_folder(revision)
    lock = json.loads((folder / 'review-source-lock.json').read_text(encoding='utf-8'))
    check_sources(ROOT, (folder / 'review-source-lock.json').relative_to(ROOT).as_posix())
    for name, digest in lock['artifacts'].items():
        if sha256(folder / name) != digest:
            raise SystemExit(f'review artifact drift: {name}')
    code = json.loads((folder / 'profile.ipynb').read_text(encoding='utf-8'))['cells'][1]['source']
    with tempfile.TemporaryDirectory(prefix='control-interface-review-check-') as base:
        base = Path(base)
        decoy_dir, calls = base / 'bin', base / 'nvidia-smi-calls.log'
        decoy_dir.mkdir()
        (decoy_dir / 'nvidia-smi').write_text(DECOY.format(log=calls))
        (decoy_dir / 'nvidia-smi').chmod(0o755)
        tmp = base / 'tmp'
        tmp.mkdir()
        env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'VIRTUAL_ENV')}
        env.update(PATH=f"{decoy_dir}:{env.get('PATH', '')}", CUDA_VISIBLE_DEVICES='', TMPDIR=str(tmp))
        cell_file = base / 'review_cell.py'
        cell_file.write_text(code, encoding='utf-8')
        process = subprocess.run([sys.executable, '-I', str(cell_file)], cwd=base, env=env, capture_output=True,
                                 text=True, timeout=300)
        leftovers = sorted(p.name for p in tmp.iterdir())
        receipt = {
            'schema': 'control_interface_action_selection_v2_review_check_v1', 'review_revision': revision,
            'review_lock_sha256': sha256(folder / 'review-source-lock.json'),
            'evidence_class': 'scripted_cpu_rehearsal', 'gpu_compatibility_evidence': False,
            'exit_code': process.returncode,
            'refused_at_live_gate': 'LiveRefused' in process.stderr,
            'refusal': next((line for line in process.stderr.splitlines() if 'LiveRefused' in line), None),
            'nvidia_smi_called': calls.exists(),
            'temporary_files_left': leftovers,
            'kaggle_paths_touched': Path('/kaggle').exists(),
            'stderr_tail': process.stderr[-1500:],
        }
    receipt['passed'] = (receipt['exit_code'] != 0 and receipt['refused_at_live_gate']
                         and not receipt['nvidia_smi_called'] and not leftovers)
    out = ROOT / f'reports/control_interface_action_selection_v2_review_check_r{revision}.json'
    out.write_text(json.dumps(receipt, indent=1) + '\n', encoding='utf-8')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['review-build', 'review-check', 'launch-build'])
    parser.add_argument('--revision', type=int, default=1)
    args = parser.parse_args()
    if args.command == 'review-build':
        print(json.dumps({k: v for k, v in build_review(review_folder(args.revision)).items() if k != 'bindings'},
                         indent=1))
        return 0
    if args.command == 'review-check':
        receipt = review_check(args.revision)
        print(json.dumps({k: receipt[k] for k in ('passed', 'exit_code', 'refused_at_live_gate', 'nvidia_smi_called',
                                                   'temporary_files_left', 'refusal')}, indent=1))
        return 0 if receipt['passed'] else 1
    try:
        launch_artifacts(ROOT)
    except LiveRefused as exc:
        print('launch package refused:\n  ' + '\n  '.join(exc.reasons))
        return 1
    print('the live gate passed; writing the launch package is a separate, explicitly authorized step')
    return 0


if __name__ == '__main__':
    sys.exit(main())
