"""Successor runtime binding for feedback-action v1 sessions (hand-written glue; import is inert).

Every runtime piece is reused, not re-implemented:
- the model side (bundle integrity, hash-pinned offline install, host/GPU facts, model mount and tree digest, server
  process ownership) is the verified runtime controller `certification/direct_publisher_smoke_v1`, byte-identical to
  the files embedded by the control-interface action-selection v2 GPU run (review lock beeb6719...);
- the game side reuses the reviewed competition-wheel verification (`certification.phase4_v6.clean_environment`) and
  manifest-bound game staging (`certification.phase4_integrated_v2.game_assets`) that action-effect history v1 ran
  live, installed with the same verified `install()` from a hash-pinned 31-wheel lock;
- `verify_cache_disabled` is the verified runtime's server-log check (runtime_controls.py), copied verbatim.

This module only binds them to `runtime.json`, records what each interpreter must import, and checks it. The
experiment protocol (`protocol.json`) is not read or changed here.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = 'research/feedback_action_v1/live/runtime.json'
SCHEMA = 'feedback_action_v1_runtime_v1'
SCOPE = 'feedback-action-v1'
PREFIX_FLAGS = ('--enable-prefix-caching', '--no-enable-prefix-caching')

# The modules each interpreter executes, including those it imports lazily inside functions on its live path.
# Embedding uses the over-approximated closure of all of them (every import anywhere in a reachable file); the
# in-interpreter check imports exactly these entries and their module-level imports, as the interpreter would.
ENTRIES = {
    # the notebook's first cell, in the pinned image interpreter: standard library only
    'first_cell': ['scripts.feedback_action_v1_launch', 'research.feedback_action_v1.live.binding',
                   'research.feedback_action_v1.live.runtime', 'research.feedback_action_v1.live.authority',
                   'research.feedback_action_v1.live.launch', 'research.feedback_action_v1.live.notebook',
                   'research.feedback_action_v1.live.owner_gates',
                   'certification.direct_publisher_smoke_v1.host', 'certification.direct_publisher_smoke_v1.install',
                   'certification.direct_publisher_smoke_v1.preflight',
                   'certification.phase4_integrated_v2.game_assets', 'certification.phase4_integrated_v2.dependencies',
                   'certification.phase4_integrated_v2.evidence', 'certification.phase4_v6.clean_environment'],
    # supervisor, worker, monitor, runner and the offline engine, in the game interpreter (competition wheels)
    'game': ['research.feedback_action_v1.live.supervisor', 'research.feedback_action_v1.live.worker',
             'research.feedback_action_v1.live.monitor', 'research.feedback_action_v1.live.resources',
             'research.feedback_action_v1.live.runner', 'research.feedback_action_v1.live.engine',
             'research.feedback_action_v1.live.policy', 'research.feedback_action_v1.live.evidence',
             'research.feedback_action_v1.live.service', 'research.feedback_action_v1.live.rehearsal',
             'research.feedback_action_v1.live.authority', 'research.feedback_action_v1.live.binding',
             'research.feedback_action_v1.live.runtime', 'research.feedback_action_v1.live.owner_gates',
             'research.feedback_action_v1.live.notebook',
             'certification.phase4_integrated_v2.gated_exec', 'certification.phase4_integrated_v2.bridge',
             'certification.phase4_integrated_v2.model_transport', 'certification.phase4_integrated_v2.response_evidence',
             'certification.phase4_integrated_v2.monitor_diagnostics', 'certification.phase4_integrated_v2.async_telemetry',
             'certification.phase4_v2.package', 'research.grounded_action_v1.engine',
             'certification.phase4_v1.lifecycle', 'agent.state', 'agent.framework_adapter', 'agent.action',
             'certification.phase4_transient_v2.contract', 'research.action_effect_history_v1.contract',
             'scripts.run_grounded_action_v1_engine_local', 'evaluation.phase4_target', 'evaluation.phase4_runner',
             'arc_agi'],
    # the model host and the request contract, in the model interpreter (trusted 174-wheel lock)
    'model': ['research.feedback_action_v1.live.host', 'research.feedback_action_v1.live.service',
              'research.feedback_action_v1.live.policy', 'research.feedback_action_v1.live.rehearsal',
              'research.feedback_action_v1.live.fake_server', 'research.feedback_action_v1.live.runtime',
              'research.feedback_action_v1.live.authority', 'research.feedback_action_v1.live.binding',
              'research.feedback_action_v1.live.owner_gates', 'research.feedback_action_v1.live.notebook',
              'certification.phase4_integrated_v2.bridge', 'certification.phase4_integrated_v2.tokenizer_binding',
              'certification.phase4_integrated_v2.model_transport', 'certification.phase4_integrated_v2.response_evidence',
              'certification.phase4_transient_v2.action_contract',
              'certification.direct_publisher_smoke_v1.server', 'certification.direct_publisher_smoke_v1.host',
              'certification.direct_publisher_smoke_v1.preflight', 'transformers', 'requests'],
}
# Data files the embedded code reads at runtime (checked by running the connected rehearsal from an extracted payload).
DATA_FILES = ('research/feedback_action_v1/live/runtime.json', 'research/feedback_action_v1/live/protocol.json',
              'research/feedback_action_v1/live/owner_gates.json',
              'research/feedback_action_v1/live/game_requirements.lock',
              'research/feedback_action_v1/live/derivation.json',
              'certification/direct_publisher_smoke_v1/proposal.json',
              'certification/direct_publisher_smoke_v1/trusted_manifest.json',
              'certification/direct_publisher_smoke_v1/trusted_requirements.lock',
              'certification/phase4_integrated_v2/tokenizer_manifest.json',
              'reports/phase4_v2_offline_package.json', 'reports/phase4_transient_v2_protocol.json')


class RuntimeBindingError(ValueError):
    pass


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(root=ROOT):
    """runtime.json, validated: frozen runtime invariants and the hashes of the game-side inputs it names."""
    root = Path(root)
    runtime = json.loads((root / RUNTIME).read_bytes())
    if runtime.get('schema') != SCHEMA or runtime.get('scope') != SCOPE:
        raise RuntimeBindingError('not the feedback-action v1 runtime binding')
    life = runtime['lifecycle']
    ints = ('authorized_seconds', 'internal_seconds', 'cleanup_reserve_seconds', 'installation_seconds',
            'startup_ceiling_seconds', 'pair_admission_seconds', 'maximum_attempts', 'maximum_policy_calls',
            'maximum_canaries', 'automatic_retries')
    if (any(type(life.get(k)) is not int for k in ints) or life['maximum_attempts'] != 1
            or life['automatic_retries'] != 0 or life['maximum_canaries'] != 1 or life['maximum_policy_calls'] != 192
            or not 0 < life['installation_seconds'] < life['internal_seconds'] - life['cleanup_reserve_seconds']
            or not life['internal_seconds'] + life['cleanup_reserve_seconds'] <= life['authorized_seconds']
            or life['sessions'] != [1, 2]):
        raise RuntimeBindingError('runtime lifecycle limits')
    argv = runtime['server']['argv']
    if (argv.count('--no-enable-prefix-caching') != 1 or '--enable-prefix-caching' in argv
            or argv[argv.index('--served-model-name') + 1] != runtime['model']['model_id']
            or argv[argv.index('--max-model-len') + 1] != '65536' or argv[:3] != ['{python}', '-m',
                                                                                  'vllm.entrypoints.openai.api_server']):
        raise RuntimeBindingError('server argv: prefix caching must be disabled once; model and context frozen')
    game = runtime['game']
    if sha256(root / game['manifest']) != game['manifest_sha256'] or sha256(root / game['requirements']) != game[
            'requirements_sha256']:
        raise RuntimeBindingError('game manifest or game lock differs from its binding')
    lock = game_lock(root, runtime)
    if len(lock) != game['wheel_count']:
        raise RuntimeBindingError('game lock wheel count')
    if runtime['model'].get('source_kind') != 'dataset':
        raise RuntimeBindingError('the verified runtime attaches the model as a version-pinned dataset')
    return runtime


def game_lock(root, runtime):
    """The 31 hash pins, which must equal the competition wheel inventory of the frozen manifest exactly."""
    from certification.direct_publisher_smoke_v1.preflight import normalize, pins
    root = Path(root)
    manifest = json.loads((root / runtime['game']['manifest']).read_bytes())
    expected = {}
    for name, info in manifest['files'].items():
        if name.startswith('wheels/'):
            filename = name.split('/', 1)[1]
            dist, version = filename.split('-')[:2]
            expected[normalize(dist)] = (version, info['sha256'])
    found = pins((root / runtime['game']['requirements']).read_text(encoding='utf-8'), require_hashes=True)
    if found != expected:
        raise RuntimeBindingError('game lock and the frozen competition wheel inventory disagree')
    return found


def unresolved(runtime):
    """Dotted paths of every value still carrying the placeholder prefix (the reference package's rule)."""
    prefix, found = runtime['placeholder_prefix'], []

    def walk(value, path):
        if isinstance(value, dict):
            for key, item in value.items():
                if key != 'placeholder_prefix':
                    walk(item, f'{path}.{key}' if path else key)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f'{path}[{index}]')
        elif isinstance(value, str) and value.startswith(prefix):
            found.append(path)
    walk(runtime, '')
    return found


def competition_mount(ref, base=Path('/kaggle/input')):
    """The attached competition directory: both provider layouts are accepted, exactly one must exist.

    The verified runtime attached the competition but never read its files; this layout rule mirrors the verified
    dataset mount rule (`host.dataset_mount`). The contents are verified by hash before any use."""
    base = Path(base)
    candidates = [base / 'competitions' / ref, base / ref]
    found = [c for c in candidates if c.is_dir() and not c.is_symlink()]
    if len(found) != 1:
        raise RuntimeBindingError(f'competition {ref} must have exactly one unambiguous mount; checked '
                                  + ', '.join(map(str, candidates)))
    return found[0]


def verify_game_wheels(wheels, root=ROOT, runtime=None):
    """The 31 competition wheels against the frozen manifest (sizes and hashes; nothing extra)."""
    from certification.phase4_v6.clean_environment import verify_environment_wheels
    runtime = runtime or load(root)
    manifest = json.loads((Path(root) / runtime['game']['manifest']).read_bytes())
    count = verify_environment_wheels(Path(wheels), manifest)
    game_lock(root, runtime)
    return {'game_wheels_verified': count, 'manifest_sha256': runtime['game']['manifest_sha256'],
            'requirements_sha256': runtime['game']['requirements_sha256']}


def module_file(root, name):
    base = Path(root).joinpath(*name.split('.'))
    for candidate in (base.with_suffix('.py'), base / '__init__.py'):
        if candidate.is_file():
            return candidate
    return None


def _imports(path, module, lazy=True):
    """Modules named by import statements, __import__('x') or importlib.import_module('x'). With lazy=False only
    statements executed when the module is imported count (function bodies are skipped)."""
    tree = ast.parse(Path(path).read_bytes(), filename=str(path))
    package = module if path.name == '__init__.py' else module.rpartition('.')[0]
    names = []
    pending = [tree]
    while pending:
        node = pending.pop()
        if isinstance(node, ast.Import):
            names += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parts = package.split('.')
                base = '.'.join(parts[:len(parts) - node.level + 1])
                stem = f'{base}.{node.module}' if node.module else base
            else:
                stem = node.module
            names.append(stem)
            names += [f'{stem}.{alias.name}' for alias in node.names if alias.name != '*']
        elif (isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant)
              and isinstance(node.args[0].value, str)):
            func = node.func
            called = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ''
            if called in ('__import__', 'import_module'):
                names.append(node.args[0].value)
        for child in ast.iter_child_nodes(node):
            if lazy or not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                pending.append(child)
    return names


def closure(entries, root=ROOT, lazy=True):
    """(repository files, external top-level modules) reachable from `entries` by static import analysis.

    lazy=True over-approximates on purpose (imports inside functions count): every file an interpreter could import
    is embedded. lazy=False follows only module-level imports: what importing the entries executes."""
    root = Path(root)
    seen, files, external = set(), set(), set()
    pending = list(entries)
    while pending:
        name = pending.pop()
        if not name or name in seen:
            continue
        seen.add(name)
        path = module_file(root, name)
        if path is None:
            top = name.split('.')[0]
            if module_file(root, top) is None and not (root / top).is_dir():
                external.add(top)
            continue
        files.add(path.relative_to(root).as_posix())
        parts = name.split('.')
        for i in range(1, len(parts)):  # parent packages execute their __init__ (and its imports) first
            pending.append('.'.join(parts[:i]))
        pending.extend(_imports(path, name, lazy))
    return sorted(files), sorted(external - set(sys.stdlib_module_names) - {'__future__'})


def role_modules(role, root=ROOT):
    """What one interpreter imports on its live path: the role's entries (including the external packages named
    there) and their module-level repository closure."""
    files, external = closure(ENTRIES[role], root, lazy=False)
    modules = set(external)
    for name in files:
        if name.endswith('/__init__.py'):
            name = name[:-len('/__init__.py')]
        elif name.endswith('.py'):
            name = name[:-3]
        modules.add(name.replace('/', '.'))
    return sorted(modules)


IMPORT_CHECK = '''import importlib, json, sys
root, modules, absent = sys.argv[1], json.loads(sys.argv[2]), json.loads(sys.argv[3])
sys.path.insert(0, root)
imported, failed = [], {}
for name in modules:
    try:
        importlib.import_module(name)
        imported.append(name)
    except BaseException as exc:
        failed[name] = type(exc).__name__ + ': ' + str(exc)[:200]
present = [name for name in absent if importlib.util.find_spec(name) is not None]
print(json.dumps({'imported': len(imported), 'failed': failed, 'forbidden_present': present,
                  'executable': sys.executable, 'prefix': sys.prefix}))
'''
# A game interpreter must not see the model stack and the model interpreter must not see the game engine.
FORBIDDEN = {'game': ['torch', 'vllm', 'transformers'], 'model': ['arc_agi', 'arcengine']}


def import_check(python, role, root, processes, deadline, log, env=None):
    """Import every repository module of the role's closure inside `python` (an owned process group)."""
    import importlib.util  # noqa: F401  (the check script uses importlib.util in the child)
    modules = role_modules(role, root)
    environment = dict(env or os.environ)
    environment.update(PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1', MPLBACKEND='Agg', CUDA_VISIBLE_DEVICES='')
    for key in ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV'):
        environment.pop(key, None)
    code = 'import importlib.util\n' + IMPORT_CHECK
    result = processes.command([str(python), '-I', '-c', code, str(Path(root).resolve()), json.dumps(modules),
                                json.dumps(FORBIDDEN[role])], log, deadline, environment, f'{role} import closure')
    report = json.loads(result.stdout.strip().splitlines()[-1])
    if report['failed'] or report['forbidden_present'] or report['imported'] != len(modules):
        raise RuntimeBindingError(f'{role} interpreter import closure: failed {sorted(report["failed"])[:5]}, '
                                  f'forbidden {report["forbidden_present"]}')
    return {'modules': len(modules), 'imported': report['imported'], 'forbidden_absent': FORBIDDEN[role]}


def prepare(root, scratch, bundle, competition, deadline, processes, *, python=sys.executable, check=lambda: None,
            bundle_inputs=None, receipt=None):
    """Both interpreters, on the first-cell installation deadline (reused verified install for each):

    model: verify the publisher flat mount (174 trusted wheels, publisher metadata), hash-pinned offline install of
           the trusted lock, pip check, exact versions, imports and the torch CUDA build; then the model-side import
           closure with the game engine absent.
    game:  verify the 31 competition wheels against the frozen manifest, hash-pinned offline install of the game
           lock, pip check, exact versions and imports; then the game-side import closure with the model stack absent.
    """
    from certification.direct_publisher_smoke_v1.install import InstallFailed, install, verify_bundle
    root, scratch = Path(root), Path(scratch)
    runtime = load(root)
    receipt = {} if receipt is None else receipt  # the caller's dict, retained by the caller on success or failure
    receipt.update(scope='feedback_action_v1_interpreter_pair', passed=False, error=None)

    def within():
        check()
        if time.monotonic() >= deadline:
            raise TimeoutError('installation deadline reached')
    # Kaggle notebooks set MPLBACKEND to the Jupyter inline backend (module://matplotlib_inline.backend_inline),
    # which the isolated interpreters do not have. The game engine imports matplotlib, so the verified installer's
    # package checks failed on it (session 1, attempt 1, October 11, 2026). Both installations therefore run with
    # the non-interactive backend, as the import checks and the supervisor launch already do.
    environment = {**os.environ, 'MPLBACKEND': 'Agg'}
    try:
        receipt['bundle'] = verify_bundle(bundle, runtime['dataset'], runtime['bundle'], within, inputs=bundle_inputs)
        within()
        receipt['model'] = install(bundle, scratch / 'model' / 'venv', runtime['runtime'], deadline,
                                   scratch / 'model-install.log', python=python, environment=environment,
                                   processes=processes)
        within()
        wheels = Path(competition) / runtime['competition']['game_wheels']
        receipt['game_wheels'] = verify_game_wheels(wheels, root, runtime)
        receipt['game'] = install(wheels, scratch / 'game' / 'venv', runtime['game']['runtime'], deadline,
                                  scratch / 'game-install.log', python=python, environment=environment,
                                  processes=processes, requirements=root / runtime['game']['requirements'])
        within()
        receipt['model_closure'] = import_check(receipt['model']['python'], 'model', root, processes, deadline,
                                                scratch / 'model-install.log')
        receipt['game_closure'] = import_check(receipt['game']['python'], 'game', root, processes, deadline,
                                               scratch / 'game-install.log')
        within()
        receipt['passed'] = True
        return {'model': receipt['model']['python'], 'game': receipt['game']['python']}
    except (InstallFailed, RuntimeBindingError, OSError, ValueError) as exc:
        receipt['error'] = type(exc).__name__ + ': ' + str(exc)[:512]
        raise


def expected_artifact(root=ROOT):
    """The model artifact identity the host must report: the reviewed tree digest of the pinned snapshot."""
    return {'tree_sha256': load(root)['model']['tree_sha256']}


# Copied verbatim from the verified runtime (research/control_interface_action_selection_v2/runtime_controls.py at
# 5a21dd3, sha256 recorded in derivation.json): the server log must confirm prefix caching disabled.
def verify_cache_disabled(log):
    with Path(log).open('rb') as stream:
        stream.seek(max(0, Path(log).stat().st_size - 2097152))
        text = stream.read().decode('utf-8', errors='replace')
    values = re.findall(r"enable_prefix_caching(?:['\"])?\s*[:=]\s*(True|False)", text)
    if not values or any(value != 'False' for value in values):
        raise ValueError('server log does not confirm prefix caching disabled')
    return {'disabled': True, 'confirmation': 'all retained startup configuration entries say enable_prefix_caching=False',
            'matches': len(values)}
