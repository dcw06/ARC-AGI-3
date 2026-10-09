"""Static import and data closure of the runtime v2 notebook payload (hand-written; CPU only; never imports targets).

The R4/R6/R7 payloads embedded a broad inventory (every agent/, certification/, evaluation/ and config/ file:
1,111-1,118 files, within 10 KB of the 900,000-byte notebook guard) without a closure proof. Runtime v2 embeds
exactly the closure of its process entry points plus explicitly listed inputs, and proves it three ways:
1. this static scan (AST, including function-level imports, relative imports, `-m`/`__import__` module strings,
   `Path(__file__).with_name(...)` siblings and repository-relative path literals) reports no unresolved project
   import;
2. every closure module is compiled, and top-level imports are executed from an extracted payload in each real
   interpreter (tests and scripts/check_stagnation_supervision_runtime_v2_closure.py);
3. the connected CPU rehearsals run the process tree from the extracted payload in the real game and model
   interpreters installed by the runtime v2 installer.
"""
import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ('agent', 'certification', 'evaluation', 'research', 'scripts')
ENTRY_MODULES = (
    'research.stagnation_supervision_runtime_v2.launch',      # first cell (notebook interpreter)
    'research.stagnation_supervision_runtime_v2.supervisor',  # game interpreter, -m
    'research.stagnation_supervision_runtime_v2.worker',      # game interpreter, -m via gated_exec
    'research.stagnation_supervision_runtime_v2.monitor',     # game interpreter, -m
    'research.stagnation_supervision_runtime_v2.host',        # model interpreter, -m
)
ENTRY_FILES = ('certification/phase4_integrated_v2/gated_exec.py',)  # executed by path
# Inputs read by code paths the scan cannot see as literals, or bound for review rather than execution.
EXPLICIT = (
    'research/stagnation_supervision_runtime_v2/protocol.json',
    'research/stagnation_supervision_runtime_v2/derivation.json',
    'research/stagnation_supervision_runtime_v2/proposal.json',
    'research/stagnation_supervision_runtime_v2/trusted_manifest.json',
    'research/stagnation_supervision_runtime_v2/trusted_requirements.lock',
    'research/stagnation_supervision_runtime_v2/closure.py',
    'research/stagnation_supervision_v1/closed_loop/protocol.json',
    'research/stagnation_supervision_v1/trigger_spec.json',
    'reports/phase4_v2_offline_package.json',
    'reports/phase4_torch_wheel_inspection.json',
    'reports/m0_profiles/m0-q3vl30-instruct.json',
    'config/operational_primary.yaml',
    'config/m0_launch_spec_q3vl30.json',
    'certification/phase4_integrated_v2/tokenizer_manifest.json',
    'reports/stagnation_supervision_v1_token_audit.json',
    'reports/stagnation_supervision_v1_ls20_decision.json',
    'reports/stagnation_supervision_v1_protocol_v2.md',
)
DATA_SUFFIXES = ('.json', '.yaml', '.yml', '.lock', '.md', '.txt', '.py', '.csv')
# Statically reachable only through function-level imports or literals inside functions that no Track 3 process
# calls (another experiment's live authority and launch tooling, the superseded R4 launcher and gate records, and
# Phase 4 workload/notebook builders behind evaluation.phase4_execution.authority). None was in the R4 payload
# except the superseded launcher; none is executed by the runtime v2 entry points. They are not embedded, so no
# other scope's approval, claim, reservation or credential-handling code travels with this package. The scan does
# not follow them; the extracted-payload checks and rehearsals would fail if any were needed.
EXCLUDED = {
    'scripts/stagnation_supervision_v1_launch.py': 'superseded R4 launcher (runtime v2 launch.py replaces it)',
    'notebooks/stagnation-supervision-v1-review-r1/review-source-lock.json': 'frozen R4 gate literal; gate unused',
    'scripts/phase4_integrated_v2_launch.py': 'Phase 4 integrated v2 launch tooling (another scope)',
    'scripts/phase4_install_kaggle.py': 'provider credential/install helper (never in a notebook payload)',
    'notebooks/phase4-integrated-v2-review-r3/review-source-lock.json': 'another scope review lock',
    'reports/phase4_integrated_v2_source_approval.json': 'another scope approval record',
    'reports/phase4_integrated_v2_compute_authorization.json': 'another scope approval record',
    'reports/phase4_integrated_v2_pilot_launch.json': 'another scope launch record',
    'reports/phase4_integrated_v2_pilot_prelaunch.json': 'another scope launch record',
    'config/phase4_integrated_v2_execution/execution_lock.json': 'another scope execution lock',
    'config/phase4_integrated_v2_launch_claim.json': 'another scope launch claim',
    'config/phase4_integrated_v2_reservation.json': 'another scope reservation',
    'scripts/build_e1_four_cell_notebook.py': 'E1 notebook builder behind evaluation.phase4_execution.authority',
    'scripts/build_m0_profile_notebook.py': 'M0 notebook builder behind evaluation.phase4_execution.authority',
    'scripts/build_phase4_target_notebook.py': 'Phase 4 notebook builder behind evaluation.phase4_execution',
    'scripts/evaluate_phase4_prescreen.py': 'Phase 4 prescreen behind evaluation.phase4_execution',
    'scripts/phase4_budget.py': 'Phase 4 budget tool behind evaluation.phase4_execution',
    'scripts/profile_m0_openai.py': 'M0 profiler behind E1/M0 builders',
    'scripts/run_e1_four_cell.py': 'E1 runner behind E1 builders',
    'scripts/run_e1_whole_run.py': 'E1 runner behind E1 builders',
    'scripts/run_phase4_service.py': 'Phase 4 service behind evaluation.phase4_runner.supervise',
    'scripts/run_phase4_target.py': 'Phase 4 target runner behind evaluation.phase4_target.run',
    'certification/phase4_integrated_v2/authority.py': 'another scope live gate (ModelProxy.start/live_probes unused)',
}


def module_path(root, dotted):
    base = Path(root, *dotted.split('.'))
    for candidate in (base.with_suffix('.py'), base / '__init__.py'):
        if candidate.is_file():
            return candidate
    return None


def _resolve_from(root, path, node):
    if node.level == 0:
        return node.module or ''
    package = list(Path(path).relative_to(root).parent.parts)  # a module's or an __init__'s own package
    base = package[:len(package) - (node.level - 1)] if node.level > 1 else package
    return '.'.join(base + ([node.module] if node.module else []))


def scan(root, path):
    """(project modules, data files, third-party top-level names, unresolved project references) of one file."""
    root, path = Path(root), Path(path)
    tree = ast.parse(path.read_bytes(), filename=str(path))
    modules, data, third, unresolved = set(), set(), set(), set()

    def excluded(dotted):
        base = dotted.replace('.', '/')
        return base + '.py' in EXCLUDED or base + '/__init__.py' in EXCLUDED

    def want(dotted):
        top = dotted.split('.')[0]
        if top in PROJECT:
            if module_path(root, dotted) is not None:
                modules.add(dotted)
                return True
            if not excluded(dotted):  # an excluded module may be absent from an extracted payload by design
                unresolved.add(dotted)
        elif top and top not in sys.stdlib_module_names and top != '__future__':
            third.add(top)
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                want(alias.name)
        elif isinstance(node, ast.ImportFrom):
            base = _resolve_from(root, path, node)
            if base and base.split('.')[0] in PROJECT:
                if module_path(root, base) is not None:
                    modules.add(base)
                elif not excluded(base):
                    unresolved.add(base)
                for alias in node.names:
                    sub = base + '.' + alias.name
                    if module_path(root, sub) is not None:
                        modules.add(sub)
            elif base:
                want(base)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'with_name':
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                sibling = path.with_name(node.args[0].value)
                if sibling.is_file():
                    data.add(sibling.relative_to(root).as_posix())
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
            if (value.split('.')[0] in PROJECT and '.' in value and ' ' not in value and '/' not in value
                    and module_path(root, value) is not None):
                modules.add(value)
            elif ('/' in value and not value.startswith('/') and '..' not in value and '\n' not in value
                  and value.endswith(DATA_SUFFIXES) and (root / value).is_file()):
                data.add(value)
    return modules, data, third, unresolved


def closure(root=ROOT, entries=ENTRY_MODULES, files=ENTRY_FILES, explicit=EXPLICIT):
    root = Path(root)
    import json
    # Every frozen science file the protocol binds by hash travels with the payload: the gate re-hashes them in the
    # extracted source, and reviewers see the exact detector, supervision, outcome and evaluator code.
    science = json.loads((root / 'research/stagnation_supervision_runtime_v2/protocol.json').read_bytes())['science']['files']
    queue = [module_path(root, m).relative_to(root).as_posix() for m in entries] + list(files)
    queue += [n for n in science if n.endswith('.py')]
    seen, data, third, unresolved, skipped = set(), set(explicit) | {n for n in science if not n.endswith('.py')}, {}, set(), set()
    while queue:
        name = queue.pop()
        if name in EXCLUDED:
            skipped.add(name)
            continue
        if name in seen:
            continue
        seen.add(name)
        path = root / name
        parts = Path(name).parts
        for i in range(1, len(parts)):  # every enclosing package initialiser
            init = Path(*parts[:i], '__init__.py').as_posix()
            if (root / init).is_file() and init not in seen:
                queue.append(init)
        if not name.endswith('.py'):
            continue
        modules, found, names, missing = scan(root, path)
        unresolved |= {f'{name}: {m}' for m in missing}
        for top in names:
            third.setdefault(top, set()).add(name)
        for dotted in modules:
            queue.append(module_path(root, dotted).relative_to(root).as_posix())
        for item in found:
            if item in EXCLUDED:
                skipped.add(item)
            elif item.endswith('.py'):
                queue.append(item)  # scripts loaded by spec_from_file_location are code, not data
            else:
                data.add(item)
    code = sorted(n for n in seen if n.endswith('.py'))
    missing_data = sorted(d for d in data if not (root / d).is_file())
    return {'code': code, 'data': sorted(d for d in data if d not in seen or not d.endswith('.py')),
            'third_party': {k: sorted(v) for k, v in sorted(third.items())},
            'unresolved_project_imports': sorted(unresolved), 'missing_data': missing_data,
            'excluded_reachable': {k: EXCLUDED[k] for k in sorted(skipped)},
            'files': sorted(set(code) | data)}
