# Derived from scripts/control_interface_action_selection_v2_package.py at 5a21dd3 by research/feedback_action_v1/derive_runtime.py; edit the derivation.
"""Feedback-action v1 packaging (no upload, no reservation, no approval, no GPU).

  python scripts/feedback_action_v1_package.py review-build --revision 1
      freeze notebooks/feedback-action-v1-review-r<N>/ (GPU disabled; review snapshot, not an approval)
  python scripts/feedback_action_v1_package.py review-check --revision 1
      execute that notebook's code locally with no GPU and a decoy nvidia-smi; it must stop at the live gate before
      any installation, model or GPU activity; writes reports/feedback_action_v1_review_check_r<N>.json
  python scripts/feedback_action_v1_package.py review-rehearse --revision 1
      execute the same cell with only its MODE token switched to 'rehearsal': the full connected session (scripted
      model, real offline engine) from the extracted payload; writes reports/feedback_action_v1_review_rehearsal_r<N>.json
  python scripts/feedback_action_v1_package.py launch-build
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
from research.feedback_action_v1.live.binding import LiveRefused, check_sources, sha256  # noqa: E402
from research.feedback_action_v1.live.notebook import build_review, launch_artifacts  # noqa: E402

DECOY = '#!/bin/sh\necho "$0 $*" >> "{log}"\nexit 1\n'


def review_folder(revision):
    return ROOT / f'notebooks/feedback-action-v1-review-r{revision}'


def review_check(revision):
    folder = review_folder(revision)
    lock = json.loads((folder / 'review-source-lock.json').read_text(encoding='utf-8'))
    check_sources(ROOT, (folder / 'review-source-lock.json').relative_to(ROOT).as_posix())
    for name, digest in lock['artifacts'].items():
        if sha256(folder / name) != digest:
            raise SystemExit(f'review artifact drift: {name}')
    code = json.loads((folder / 'profile.ipynb').read_text(encoding='utf-8'))['cells'][1]['source']
    with tempfile.TemporaryDirectory(prefix='feedback-action-v1-review-check-') as base:
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
            'schema': 'feedback_action_v1_review_check_v1', 'review_revision': revision,
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
    out = ROOT / f'reports/feedback_action_v1_review_check_r{revision}.json'
    out.write_text(json.dumps(receipt, indent=1) + '\n', encoding='utf-8')
    return receipt


def review_rehearse(revision, session=1, seconds=2400):
    """The frozen cell with only MODE switched: one connected rehearsal session from the extracted payload."""
    from research.grounded_action_v1.engine import restore_game_mount
    from scripts.evaluate_feedback_action_v1 import evaluate_output
    folder = review_folder(revision)
    code = json.loads((folder / 'profile.ipynb').read_text(encoding='utf-8'))['cells'][1]['source']
    if code.count("MODE = 'live'\n") != 1:
        raise SystemExit('frozen notebook must run in live mode only')
    base = Path.home() / 'fa1-review'
    base.mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(dir=base))
    games = restore_game_mount(work / 'games')
    (work / 'working').mkdir()
    env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'VIRTUAL_ENV') and not k.startswith('FA1_')}
    env.update(FA1_REHEARSAL='1', CUDA_VISIBLE_DEVICES='', FA1_REHEARSAL_WORKING=str(work / 'working'),
               FA1_REHEARSAL_GAMES=str(games), FA1_REHEARSAL_SECONDS=str(seconds), FA1_REHEARSAL_SESSION=str(session),
               TMPDIR=str(work))
    for key in ('FA1_REHEARSAL_GAME_PYTHON', 'FA1_REHEARSAL_MODEL_PYTHON', 'FA1_REHEARSAL_TOKENIZER',
                'FA1_REHEARSAL_GRAMMAR'):
        if os.environ.get(key):
            env[key] = os.environ[key]
    cell_file = work / 'review_cell.py'
    cell_file.write_text(code.replace("MODE = 'live'\n", "MODE = 'rehearsal'\n"), encoding='utf-8')
    process = subprocess.run([sys.executable, '-I', str(cell_file)], cwd=work, env=env, capture_output=True,
                             text=True, timeout=seconds + 600)
    output = work / 'working' / 'feedback-action-v1'
    value = evaluate_output(output, mode='rehearsal', rehearsal_seconds=seconds) if output.exists() else None
    leftovers = sorted(p.name for p in work.iterdir() if p.name.startswith('feedback-action-v1-source-'))
    receipt = {'schema': 'feedback_action_v1_review_rehearsal_v1', 'review_revision': revision,
               'review_lock_sha256': sha256(folder / 'review-source-lock.json'), 'session': session,
               'evidence_class': 'scripted_cpu_rehearsal_from_extracted_payload', 'gpu_compatibility_evidence': False,
               'interpreters': {'game': env.get('FA1_REHEARSAL_GAME_PYTHON', 'review interpreter'),
                                'model': env.get('FA1_REHEARSAL_MODEL_PYTHON', 'review interpreter')},
               'pinned_tokenizer': bool(env.get('FA1_REHEARSAL_TOKENIZER')),
               'grammar_checked': env.get('FA1_REHEARSAL_GRAMMAR') == '1',
               'exit_code': process.returncode, 'extracted_source_left': leftovers,
               'technically_complete': bool(value and value['technically_complete']),
               'lifecycle_errors': value['lifecycle_errors'] if value else ['no output'],
               'evaluation': {k: value['evaluation'][k] for k in ('replay_passed', 'session', 'failure_rules',
                                                                  'session_2_permitted', 'technical_validity')}
               if value and value['evaluation'] else None,
               'stderr_tail': process.stderr[-1500:]}
    receipt['passed'] = process.returncode == 0 and receipt['technically_complete'] and not leftovers
    out = ROOT / f'reports/feedback_action_v1_review_rehearsal_r{revision}.json'
    out.write_text(json.dumps(receipt, indent=1) + '\n', encoding='utf-8')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['review-build', 'review-check', 'review-rehearse', 'launch-build'])
    parser.add_argument('--session', type=int, default=1)
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
    if args.command == 'review-rehearse':
        receipt = review_rehearse(args.revision, args.session)
        print(json.dumps({k: receipt[k] for k in ('passed', 'exit_code', 'technically_complete', 'lifecycle_errors',
                                                   'evaluation')}, indent=1))
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
