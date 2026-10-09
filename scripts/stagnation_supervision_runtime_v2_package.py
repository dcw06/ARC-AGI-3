"""Track 3 runtime v2 packaging (no upload, provider call, reservation, approval or GPU).

  python -m scripts.stagnation_supervision_runtime_v2_package review-build --revision 1
      freeze notebooks/stagnation-supervision-v1-runtime-v2-review-r<N>/ (GPU disabled; not an approval)
  python -m scripts.stagnation_supervision_runtime_v2_package review-check --revision 1 [--record]
      verify every binding and artifact, compile every embedded Python file, execute the notebook cell with no GPU,
      a decoy nvidia-smi and a private TMPDIR (it must refuse at the runtime v2 gate before installation, model or
      GPU use and remove its extracted source), then CPU-rehearse the same embedded cell in rehearsal mode (one game
      group, three arms) and replay it with the runtime v2 target evaluator; --record writes the write-once receipt
      reports/stagnation_supervision_runtime_v2_review_check_r<N>.json
  python -m scripts.stagnation_supervision_runtime_v2_package launch-build
      try to build the launch package in memory; it must refuse in this checkout
"""
import argparse
import ast
import base64
import hashlib
import json
import lzma
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DECOY = '#!/bin/sh\necho "$0 $*" >> "{log}"\nexit 1\n'
MODE_LINE = "MODE = 'live'\n"


def folder_for(revision):
    return ROOT / f'notebooks/stagnation-supervision-v1-runtime-v2-review-r{revision}'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def extract(folder):
    """(lock, code, {name: bytes}) after verifying bindings, artifacts, metadata and the embedded payload."""
    folder = Path(folder)
    lock = json.loads((folder / 'review-source-lock.json').read_bytes())
    for name, digest in lock['artifacts'].items():
        if sha((folder / name).read_bytes()) != digest:
            raise ValueError('review artifact drift: ' + name)
    for name, digest in lock['bindings'].items():
        if sha((ROOT / name).read_bytes()) != digest:
            raise ValueError('reviewed source drift: ' + name)
    metadata = json.loads((folder / 'kernel-metadata.json').read_bytes())
    if (metadata['enable_gpu'] is not False or metadata['enable_tpu'] is not False or metadata['enable_internet'] is not False
            or metadata['is_private'] is not True or lock['gpu_enabled'] is not False or lock['authorized_seconds'] != 0):
        raise ValueError('review metadata must stay private, offline and GPU-disabled')
    code = json.loads((folder / 'profile.ipynb').read_bytes())['cells'][1]['source']
    if code.count(MODE_LINE) != 1:
        raise ValueError('the frozen review cell must run in live mode only')
    tree = ast.parse(code)
    packed = next(n.value.args[0].args[0].args[0].value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == 'payload' for t in n.targets))
    bindings = next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'bindings' for t in n.targets))
    payload = {n: base64.b64decode(v) for n, v in json.loads(lzma.decompress(base64.b85decode(packed))).items()}
    if set(payload) != set(bindings) or bindings != lock['bindings']:
        raise ValueError('embedded inventory differs from the lock')
    for name, raw in payload.items():
        if sha(raw) != bindings[name]:
            raise ValueError('embedded source drift: ' + name)
        if name.endswith('.py'):
            compile(raw, name, 'exec')
    return lock, code, payload


def refusal(code):
    with tempfile.TemporaryDirectory(prefix='ssv-rt2-review-check-') as base:
        base = Path(base)
        decoy, calls = base / 'bin', base / 'nvidia-smi-calls.log'
        decoy.mkdir()
        (decoy / 'nvidia-smi').write_text(DECOY.format(log=calls))
        (decoy / 'nvidia-smi').chmod(0o755)
        tmp = base / 'tmp'
        tmp.mkdir()
        env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'VIRTUAL_ENV') and not k.startswith('SSV_')}
        env.update(PATH=f"{decoy}:{env.get('PATH', '')}", CUDA_VISIBLE_DEVICES='', TMPDIR=str(tmp), TMP=str(tmp), TEMP=str(tmp))
        cell = base / 'review_cell.py'
        cell.write_text(code, encoding='utf-8')
        process = subprocess.run([sys.executable, '-I', str(cell)], cwd=base, env=env, capture_output=True, text=True,
                                 timeout=300)
        return {'exit_code': process.returncode,
                'refused_at_live_gate': 'LiveRefused' in process.stderr,
                'refusal': next((l for l in process.stderr.splitlines() if 'LiveRefused:' in l), None),
                'nvidia_smi_called': calls.exists(), 'temporary_files_left': sorted(p.name for p in tmp.iterdir()),
                'kaggle_paths_touched': Path('/kaggle').exists(), 'stderr_tail': process.stderr[-1500:]}


def rehearsal(code, *, group='b1-ar25', actions=12, seconds=1500):
    """The embedded cell in rehearsal mode (scripted model, offline engine, injected GPU), replayed independently."""
    from research.grounded_action_v1.engine import restore_game_mount
    from research.stagnation_supervision_v1.closed_loop import bridge as B
    from research.stagnation_supervision_v1.closed_loop.runner import protocol
    from research.stagnation_supervision_runtime_v2.target_evaluate import evaluate_target
    env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH' and not k.startswith(('SSV_', 'AEH_'))}
    with tempfile.TemporaryDirectory(prefix='ssv-rt2-notebook-rehearsal-') as tmp:
        work = Path(tmp)
        games = restore_game_mount(work / 'games')
        (work / 'working').mkdir()
        (work / 'tmp').mkdir()
        short = dict(env, SSV_REHEARSAL='1', CUDA_VISIBLE_DEVICES='', TMPDIR=str(work / 'tmp'),
                     SSV_REHEARSAL_GAMES=str(games), SSV_REHEARSAL_WORKING=str(work / 'working'),
                     SSV_REHEARSAL_SECONDS=str(seconds), SSV_REHEARSAL_GROUPS=group,
                     SSV_REHEARSAL_ACTIONS=str(actions))
        cell = work / 'cell.py'
        cell.write_text(code.replace(MODE_LINE, "MODE = 'rehearsal'\n"), encoding='utf-8')
        process = subprocess.run([sys.executable, str(cell)], cwd=work, env=short, capture_output=True, text=True,
                                 timeout=seconds + 120)
        if process.returncode != 0:
            raise ValueError('packaged CPU rehearsal failed: ' + process.stderr[-2000:])
        spec = B.session_spec(protocol(), '1')
        spec = {**spec, 'schedule': [s for s in spec['schedule'] if s['pair_id'] == group],
                'limits': {**spec['limits'], 'actions_per_episode': actions}}
        output = work / 'working/stagnation-supervision-v1-runtime-v2'
        evaluation = evaluate_target(output, spec, mode='rehearsal', session='1', internal_seconds=seconds)
        outer = json.loads((output / 'control/outer.json').read_bytes())
        first = json.loads((output / 'control/notebook-cost.json').read_bytes())
        leaked = sorted(p.name for p in (work / 'tmp').iterdir() if p.name.startswith('stagnation-supervision-runtime-v2-source-'))
        return {'technically_complete': evaluation['technically_complete'], 'problems': evaluation['problems'],
                'episodes': outer['run_evidence'].get('episodes'), 'installation': first.get('installation'),
                'runtime_binding': first.get('runtime_binding'),
                'cleanup': {k: outer.get(k) for k in ('process_groups_exited', 'independent_gpu_cleanup_verified',
                                                      'scratch_removed')},
                'first_cell_cleanup_verified': first.get('first_cell_cleanup_verified'), 'source_leaked': leaked}


def review_check(revision, record=False):
    folder = folder_for(revision)
    lock, code, payload = extract(folder)
    refused = refusal(code)
    rehearsed = rehearsal(code)
    receipt = {'schema': 'stagnation_supervision_runtime_v2_review_check_v1', 'review_revision': revision,
               'review_lock_sha256': sha((folder / 'review-source-lock.json').read_bytes()),
               'source_bindings_verified': len(payload), 'all_embedded_python_compiled': True,
               'live_refusal': {k: v for k, v in refused.items() if k != 'stderr_tail'},
               'cpu_rehearsal_of_embedded_cell': rehearsed,
               'evidence_class': 'scripted_cpu_rehearsal_injected_gpu', 'gpu_compatibility_evidence': False,
               'gpu_runs': 0, 'provider_calls': 0, 'authorized_seconds': 0}
    receipt['passed'] = (refused['exit_code'] != 0 and refused['refused_at_live_gate'] and not refused['nvidia_smi_called']
                         and not refused['temporary_files_left'] and not refused['kaggle_paths_touched']
                         and rehearsed['technically_complete'] and not rehearsed['problems']
                         and all(v is True for v in rehearsed['cleanup'].values())
                         and rehearsed['first_cell_cleanup_verified'] is True and not rehearsed['source_leaked'])
    if not receipt['passed']:
        print(refused['stderr_tail'], file=sys.stderr)
    destination = ROOT / f'reports/stagnation_supervision_runtime_v2_review_check_r{revision}.json'
    if record:
        comparable = {k: v for k, v in receipt.items()}
        if destination.exists():
            raise FileExistsError('the review-check receipt is write-once: ' + str(destination))
        with destination.open('x', encoding='utf-8') as stream:
            json.dump(comparable, stream, indent=1, sort_keys=True)
            stream.write('\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['review-build', 'review-check', 'launch-build'])
    parser.add_argument('--revision', type=int, default=1)
    parser.add_argument('--record', action='store_true')
    args = parser.parse_args()
    if args.command == 'review-build':
        from research.stagnation_supervision_runtime_v2.notebook import build_review
        lock = build_review(folder_for(args.revision), revision=args.revision)
        print(json.dumps({k: v for k, v in lock.items() if k != 'bindings'}, indent=1))
        return 0
    if args.command == 'review-check':
        receipt = review_check(args.revision, args.record)
        print(json.dumps(receipt, indent=1))
        return 0 if receipt['passed'] else 1
    from research.stagnation_supervision_runtime_v2.authority import LiveRefused
    from research.stagnation_supervision_runtime_v2.notebook import launch_artifacts
    try:
        launch_artifacts(ROOT)
    except LiveRefused as exc:
        print('launch package refused:\n  ' + '\n  '.join(exc.reasons))
        return 1
    print('the live gate passed unexpectedly; this checkout must not contain authority')
    return 2


if __name__ == '__main__':
    sys.exit(main())
