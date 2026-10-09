"""Track 3 runtime v2 connected CPU rehearsals (no model, no GPU, no provider; Linux only).

Staged inputs replicate the provider mounts from local, hash-verified sources:
  <work>/input/datasets/driessmit1/arc3-vllm-h100-wheelhouse-v3/   the 174 trusted wheels (hard links to a local
      copy) plus the three version-1 publisher metadata files (README.md, SHA256SUMS, requirements.lock);
  <work>/input/competitions/arc-prize-2026-arc-agi-3/{arc_agi_3_wheels,environment_files}   the 31 competition
      game wheels and 30 development game files from the manifest-locked offline archive.
The runtime v2 code itself then verifies every byte against its pins, exactly as on the target.

  interpreters  run runtime v2 `prepare` (real model and game venvs) and probe both import closures, including the
                model host's live-path modules, the effective vLLM argv and the pinned tokenizer-library versions;
  session       run the first cell in rehearsal mode with staged inputs (real installs, real game interpreter for the
                supervisor/worker/monitor, real model interpreter for the host with the scripted transport, offline
                engine, injected GPU) and replay the evidence with the runtime v2 target evaluator.
Sources come from the repository or, with --review N, from the extracted review-snapshot payload.
Receipts state that they are CPU rehearsals: installation timings here are not target timings.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
WHEEL_DATASET = Path('datasets/driessmit1/arc3-vllm-h100-wheelhouse-v3')
COMPETITION = Path('competitions/arc-prize-2026-arc-agi-3')


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def stage_inputs(work, wheels, metadata, root=ROOT):
    """Build the replica mounts; refuse any source that does not match the runtime v2 pins."""
    protocol = json.loads((root / 'research/stagnation_supervision_runtime_v2/protocol.json').read_bytes())
    manifest = json.loads((root / 'research/stagnation_supervision_runtime_v2/trusted_manifest.json').read_bytes())
    inputs = Path(work) / 'input'
    dataset = inputs / WHEEL_DATASET
    dataset.mkdir(parents=True)
    for row in manifest['artifacts']:
        source = Path(wheels) / row['filename']
        try:
            os.link(source, dataset / row['filename'])
        except OSError:
            shutil.copyfile(source, dataset / row['filename'])
    for name, digest in protocol['dataset']['publisher_metadata_sha256'].items():
        if sha(Path(metadata) / name) != digest:
            raise ValueError('publisher metadata differs from the pinned version-1 file: ' + name)
        shutil.copyfile(Path(metadata) / name, dataset / name)
    offline = json.loads((root / 'reports/phase4_v2_offline_package.json').read_bytes())
    archive = root / 'evidence/phase4-v2-development-offline.zip'
    if sha(archive) != offline['archive_sha256']:
        raise ValueError('development archive hash')
    competition = inputs / COMPETITION
    with zipfile.ZipFile(archive) as bundle:
        for name, info in offline['files'].items():
            target = (competition / 'arc_agi_3_wheels' / name.removeprefix('wheels/') if name.startswith('wheels/')
                      else competition / name)
            target.parent.mkdir(parents=True, exist_ok=True)
            data = bundle.read(name)
            if len(data) != info['bytes'] or hashlib.sha256(data).hexdigest() != info['sha256']:
                raise ValueError('archive member drift: ' + name)
            target.write_bytes(data)
    return inputs


def source_root(work, review):
    if review is None:
        return ROOT
    from scripts.stagnation_supervision_runtime_v2_package import extract, folder_for
    _, _, payload = extract(folder_for(review))
    target = Path(work) / 'source'
    for name, data in payload.items():
        (target / name).parent.mkdir(parents=True, exist_ok=True)
        (target / name).write_bytes(data)
    return target


MODEL_PROBE = r'''
import importlib, importlib.metadata as m, json, sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root))
out = {'python': sys.version.split()[0], 'prefix': sys.prefix, 'imports': {}, 'errors': {}}
for name in ('research.stagnation_supervision_runtime_v2.host', 'research.stagnation_supervision_runtime_v2.model_binding',
             'research.stagnation_supervision_v1.closed_loop.model_service', 'research.stagnation_supervision_v1.closed_loop.server_config',
             'research.stagnation_supervision_v1.closed_loop.token_bridge', 'research.stagnation_supervision_v1.closed_loop.rehearsal',
             'certification.phase4_integrated_v2.model_process', 'certification.phase4_integrated_v2.model_artifact',
             'certification.phase4_integrated_v2.model_transport', 'certification.phase4_integrated_v2.tokenizer_binding',
             'certification.phase4_v6.target_install_probe_r5', 'transformers', 'tokenizers', 'jinja2', 'torch', 'vllm',
             'vllm.entrypoints.openai.api_server'):
    try:
        module = importlib.import_module(name)
        out['imports'][name] = getattr(module, '__file__', None)
    except BaseException as exc:
        out['errors'][name] = type(exc).__name__ + ': ' + str(exc)[:300]
out['versions'] = {n: m.version(n) for n in ('torch', 'vllm', 'transformers', 'tokenizers', 'jinja2', 'numpy')}
out['game_packages_absent'] = all(importlib.util.find_spec(n) is None for n in ('arc_agi', 'arcengine'))
from certification.phase4_integrated_v2.model_process import ModelService, load_operational_primary
from research.stagnation_supervision_v1.closed_loop.server_config import cache_disabled_argv
from dataclasses import replace
primary = replace(load_operational_primary(root), model_path=Path('/MODEL'))
argv, env = ModelService(primary)._argv_and_env()
argv = cache_disabled_argv(argv)
protocol = json.loads((root / 'research/stagnation_supervision_runtime_v2/protocol.json').read_bytes())
expected = [x.replace('{python}', sys.executable).replace('{model_path}', '/MODEL') for x in protocol['server']['argv']]
out['effective_argv_equals_verified_runtime'] = argv == expected
out['effective_env_includes_verified_runtime'] = all(env.get(k) == v for k, v in protocol['server']['env'].items())
from research.stagnation_supervision_v1.closed_loop.model_service import SupervisionModelService
from research.stagnation_supervision_v1.closed_loop.rehearsal import FixtureTokenizer
SupervisionModelService('unused', lambda r: None, tokenizer=FixtureTokenizer(), check_versions=True)
out['pinned_tokenizer_library_versions_accepted'] = True
from certification.phase4_v6.target_install_probe_r5 import MODEL_CHECK
compile(MODEL_CHECK, 'model_check', 'exec')
out['model_check_compiles'] = True
print(json.dumps(out))
'''

GAME_PROBE = r'''
import importlib, importlib.metadata as m, json, sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root))
out = {'python': sys.version.split()[0], 'imports': {}, 'errors': {}}
for name in ('research.stagnation_supervision_runtime_v2.supervisor', 'research.stagnation_supervision_runtime_v2.worker',
             'research.stagnation_supervision_runtime_v2.monitor', 'research.stagnation_supervision_runtime_v2.resources',
             'research.stagnation_supervision_v1.closed_loop.runner', 'research.stagnation_supervision_v1.closed_loop.engine',
             'research.stagnation_supervision_v1.closed_loop.bridge', 'research.stagnation_supervision_v1.closed_loop.contract',
             'research.stagnation_supervision_v1.supervision', 'research.stagnation_supervision_v1.detector',
             'research.stagnation_supervision_v1.intervention', 'research.transition_evidence_v2.transition',
             'research.grounded_action_v1.engine', 'agent.framework_adapter', 'agent.state', 'agent.representation',
             'certification.phase4_integrated_v2.monitor', 'certification.phase4_integrated_v2.telemetry',
             'certification.phase4_integrated_v2.async_telemetry', 'evaluation.phase4_runner', 'evaluation.phase4_target',
             'scripts.run_grounded_action_v1_engine_local', 'arc_agi', 'arcengine'):
    try:
        module = importlib.import_module(name)
        out['imports'][name] = getattr(module, '__file__', None)
    except BaseException as exc:
        out['errors'][name] = type(exc).__name__ + ': ' + str(exc)[:300]
out['versions'] = {n: m.version(n) for n in ('arc-agi', 'arcengine', 'numpy', 'requests', 'pydantic', 'python-dotenv')}
out['model_packages_absent'] = all(importlib.util.find_spec(n) is None for n in ('torch', 'vllm', 'transformers'))
print(json.dumps(out))
'''


PREPARE = r'''
import json, sys, time
from pathlib import Path
root, inputs, scratch, output, seconds = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), int(sys.argv[5])
sys.path.insert(0, str(root))
from research.stagnation_supervision_runtime_v2.mounts import competition_mount, wheelhouse_mount
from research.stagnation_supervision_runtime_v2.prepare import prepare
started = time.monotonic()
manifest = json.loads((root / 'reports/phase4_v2_offline_package.json').read_bytes())
mount = competition_mount(root, inputs=inputs)
pair = prepare(scratch, output, wheelhouse_mount(root, inputs=inputs), mount / 'arc_agi_3_wheels', manifest, started,
               root=root, install_seconds=seconds)
print(json.dumps(pair))
'''


def interpreters(work, inputs, root, install_seconds, host_python):
    """Real runtime v2 installation on staged inputs (host interpreter with pip), then import probes in each venv."""
    output = Path(work) / 'prepare-output'
    scratch = Path(work) / 'prepare-scratch'
    scratch.mkdir()
    (Path(work) / 'tmp').mkdir(exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'VIRTUAL_ENV')}
    env.update(CUDA_VISIBLE_DEVICES='', PYTHONDONTWRITEBYTECODE='1', SSV_REHEARSAL='1', TMPDIR=str(Path(work) / 'tmp'))
    value = subprocess.run([host_python, '-c', PREPARE, str(root), str(inputs), str(scratch), str(output),
                            str(install_seconds)], env=env, capture_output=True, text=True, timeout=install_seconds + 120)
    path = output / 'control/installation.json'
    receipt = json.loads(path.read_bytes()) if path.exists() else {}
    if value.returncode != 0:
        return {'installation': receipt, 'prepare_stderr': value.stderr[-3000:], 'probes': None}
    pair = json.loads(value.stdout.strip().splitlines()[-1])
    probes = {}
    for role, code in (('model', MODEL_PROBE), ('game', GAME_PROBE)):
        value = subprocess.run([pair[role], '-c', code, str(root)], env=env, capture_output=True, text=True, timeout=600)
        probes[role] = json.loads(value.stdout.strip().splitlines()[-1]) if value.returncode == 0 else {
            'returncode': value.returncode, 'stderr': value.stderr[-2000:]}
    shutil.rmtree(scratch)
    return {'installation': {k: receipt.get(k) for k in ('passed', 'error', 'installation_seconds', 'override', 'evidence_class',
                                                         'model_bundle', 'torch_contract', 'game_wheels', 'model_install',
                                                         'model_process_cleanup', 'elapsed_seconds')},
            'probes': probes}


def session(work, inputs, root, *, session_id, seconds, install_seconds, host_python, groups=None, actions=None,
            review=None):
    """The first cell (or the embedded notebook cell) in rehearsal mode with staged inputs."""
    env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH' and not k.startswith(('SSV_', 'AEH_'))}
    working = Path(work) / 'working'
    working.mkdir()
    (Path(work) / 'tmp').mkdir()
    env.update(SSV_REHEARSAL='1', CUDA_VISIBLE_DEVICES='', TMPDIR=str(Path(work) / 'tmp'),
               SSV_RUNTIME_V2_STAGED_INPUTS=str(inputs), SSV_RUNTIME_V2_REHEARSAL_INSTALL_SECONDS=str(install_seconds),
               SSV_REHEARSAL_WORKING=str(working), SSV_REHEARSAL_SECONDS=str(seconds))
    if groups:
        env['SSV_REHEARSAL_GROUPS'] = groups
    if actions:
        env['SSV_REHEARSAL_ACTIONS'] = str(actions)
    begin = time.monotonic()
    if review is not None:
        from scripts.stagnation_supervision_runtime_v2_package import MODE_LINE, extract, folder_for
        _, code, _ = extract(folder_for(review))
        code = code.replace(MODE_LINE, "MODE = 'rehearsal'\n").replace("SESSION = '1'\n", f"SESSION = '{session_id}'\n")
        cell = Path(work) / 'cell.py'
        cell.write_text(code, encoding='utf-8')
        value = subprocess.run([host_python, str(cell)], cwd=work, env=env, capture_output=True, text=True,
                               timeout=seconds + 600)
    else:
        code = ('import sys,time\nsys.path.insert(0, sys.argv[1])\n'
                'from research.stagnation_supervision_runtime_v2.launch import notebook_entry\n'
                'notebook_entry(__import__("pathlib").Path(sys.argv[1]), time.monotonic(), "rehearsal", sys.argv[2])\n')
        value = subprocess.run([host_python, '-c', code, str(root), session_id], cwd=work, env=env,
                               capture_output=True, text=True, timeout=seconds + 600)
    wall = time.monotonic() - begin
    output = working / 'stagnation-supervision-v1-runtime-v2'
    from research.stagnation_supervision_v1.closed_loop.bridge import session_spec
    from research.stagnation_supervision_v1.closed_loop.runner import protocol
    from research.stagnation_supervision_runtime_v2.report import study_report
    spec = session_spec(protocol(), session_id)
    if groups:
        spec = {**spec, 'schedule': [s for s in spec['schedule'] if s['pair_id'] in groups.split(',')]}
    if actions:
        spec = {**spec, 'limits': {**spec['limits'], 'actions_per_episode': actions}}
    evaluation = study_report(output, spec, mode='rehearsal', session=session_id, internal_seconds=seconds)
    first = json.loads((output / 'control/notebook-cost.json').read_bytes()) if (output / 'control/notebook-cost.json').exists() else None
    installation = json.loads((output / 'control/installation.json').read_bytes()) if (output / 'control/installation.json').exists() else None
    return {'returncode': value.returncode, 'stderr_tail': value.stderr[-1500:] if value.returncode else '',
            'wall_seconds': round(wall, 3), 'first_cell': first,
            'installation': None if installation is None else {k: installation.get(k) for k in (
                'passed', 'error', 'installation_seconds', 'override', 'evidence_class', 'elapsed_seconds', 'interpreters')},
            'evaluation': evaluation, 'output': str(output)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['interpreters', 'session'])
    parser.add_argument('--wheels', type=Path, required=True)
    parser.add_argument('--publisher-metadata', type=Path, required=True)
    parser.add_argument('--work', type=Path)
    parser.add_argument('--review', type=int)
    parser.add_argument('--session', choices=('1', '2'), default='1')
    parser.add_argument('--seconds', type=int, default=5100)
    parser.add_argument('--install-seconds', type=int, default=1800)
    parser.add_argument('--groups')
    parser.add_argument('--actions', type=int)
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--host-python', default='/usr/bin/python3',
                        help='notebook-equivalent interpreter: CPython 3.12 with pip (manages the venvs)')
    args = parser.parse_args()
    work = Path(args.work or tempfile.mkdtemp(prefix='ssv-rt2-staged-'))
    work.mkdir(parents=True, exist_ok=True)
    inputs = stage_inputs(work, args.wheels, args.publisher_metadata)
    root = source_root(work, args.review)
    if args.command == 'interpreters':
        result = interpreters(work, inputs, root, args.install_seconds, args.host_python)
    else:
        result = session(work, inputs, root, session_id=args.session, seconds=args.seconds, host_python=args.host_python,
                         install_seconds=args.install_seconds, groups=args.groups, actions=args.actions, review=args.review)
    result = {'schema': 'stagnation_supervision_runtime_v2_staged_rehearsal_v1', 'command': args.command,
              'source': 'review_r%d_extracted_payload' % args.review if args.review else 'repository',
              'evidence_class': 'cpu_rehearsal_scripted_model_injected_gpu_not_target_evidence',
              'driver_python': sys.version.split()[0], 'host_python': args.host_python, 'gpu_runs': 0,
              'provider_calls': 0, **result}
    text = json.dumps(result, indent=1, sort_keys=True, default=str)
    if args.receipt:
        args.receipt.write_text(text + '\n', encoding='utf-8')
    print(text[-6000:])
    shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
