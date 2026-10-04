# Derived from scripts/build_ws3_questionnaire_v1_review.py by scripts/derive_progress_subgoal_v1.py; edit the derivation, not this file.
"""Freeze a runnable, GPU-disabled review notebook for the evidence-comprehension questionnaire."""
import argparse
import base64
import hashlib
import json
import lzma
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVISION = 'r1'
OUT = ROOT / f'notebooks/progress-subgoal-v1-review-{REVISION}'
MARKER = '    # PSV1_AUTHORITY_SIDECARS: reviewed packaging inserts bound approvals here.\n'
MODE_LINE = "MODE='live'\n"
REVIEW_DOCUMENTS = ('reports/progress_subgoal_v1_protocol_v2.md', 'reports/progress_subgoal_v1_protocol_v1.md',
                    'reports/progress_subgoal_v1_protocol_draft.md', 'reports/progress_subgoal_v1_probe_summary.json',
                    'reports/ws3_questionnaire_token_audit.json', 'reports/evidence_comprehension_v3_results.md',
                    'reports/ws3_event_specification.md',
                    'research/progress_subgoal_v1/decision_rules.json', 'research/progress_subgoal_v1/rules.py',
                    'research/progress_subgoal_v1/third_arm_decision.json',
                    'research/progress_subgoal_v1/evaluation_seed.json',
                    'research/progress_subgoal_v1/rehearsal_results.json', 'research/progress_subgoal_v1/rehearse.py',
                    'research/progress_subgoal_v1/derive.py', 'research/progress_subgoal_v1/token_audit.py',
                    'scripts/build_progress_subgoal_v1.py', 'scripts/derive_progress_subgoal_v1.py',
                    'scripts/progress_subgoal_v1_package.py', 'scripts/review_progress_subgoal_v1_notebook.py',
                    'scripts/build_progress_subgoal_v1_review.py', 'scripts/check_progress_subgoal_v1.py',
                    'tests/test_progress_subgoal_v1.py', 'tests/test_progress_subgoal_v1_rules.py',
                    'tests/test_progress_subgoal_v1_runner.py', 'tests/test_transition_evidence_v1.py',
                    'tests/test_progress_subgoal_v1_schedule.py', 'tests/test_evidence_comprehension_v1_transport.py',
                    'tests/test_progress_subgoal_v1_connected.py', 'tests/test_progress_subgoal_v1_snapshot.py',
                    'tests/test_progress_subgoal_v1_diagnostics.py', 'tests/test_progress_subgoal_v1_packaging.py',
                    'tests/test_progress_subgoal_v1_launch.py', 'tests/psv1_diagnostics_fixtures.py',
                    'tests/psv1_diagnostics_module_fixture.py')


# The notebook carries the import closure of its entry points, not whole directories: v1's broad inventory
# (822 kB) left no room for the v2 question set under the 900 kB upload guard. Imports are followed
# statically (including function-level imports and dotted module names or repository file paths written as
# strings); data files read by path are listed explicitly, as v1 listed them.
ENTRY_POINTS = ('research/progress_subgoal_v1/launch.py', 'research/progress_subgoal_v1/evaluate_run.py',
                'research/progress_subgoal_v1/rehearse_run.py', 'scripts/run_grounded_action_v1_engine_local.py',
                'certification/phase4_integrated_v2/gated_exec.py')
DATA_FILES = ('research/progress_subgoal_v1/probes.json', 'research/evidence_comprehension_v1/probes.json',
              'research/action_effect_v1/fixtures.json', 'research/action_effect_history_v1/protocol.json',
              'reports/phase4_v2_offline_package.json', 'reports/phase4_torch_wheel_inspection.json',
              'reports/phase4_transient_v2_protocol.json', 'reports/m0_profiles/m0-q3vl30-instruct.json',
              'reports/perception_stage_b_v1_case_protocol.json', 'reports/integrated_case_v1/initial_observation.json',
              'reports/integrated_case_v1/geometry_reference.json',
              'certification/phase4_integrated_v2/tokenizer_manifest.json')
PACKAGES = ('agent', 'certification', 'evaluation', 'research', 'scripts')
# Build- and review-time modules of this package: hash-bound as review documents, never in the runtime inventory.
BUILD_ONLY = ('rehearse.py', 'derive.py', 'token_audit.py', 'rules.py')


_TRACKED = []


def _tracked():
    """Files tracked by git. Packaging depends only on tracked content, never on incidental workspace files (e.g. an
    extracted archive member that happens to exist locally)."""
    if not _TRACKED:
        import subprocess
        out = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True, check=True).stdout
        _TRACKED.append(frozenset(n for n in out.decode().split('\0') if n))
    return _TRACKED[0]


def _sidecar(name):
    """This protocol's approval, reservation, review and launch records, and its own notebook folders: never runtime
    dependencies, whether or not they are tracked. Without this, committing a review lock added it to its own
    inventory. (Other stacks' files reached through reused modules, e.g. the phase4 authority's review lock, are
    unchanged, so shared files stay identical to what earlier launches packaged.)"""
    from research.progress_subgoal_v1 import authority
    records = {authority.REVIEW, authority.SOURCE, authority.COMPUTE, authority.EXECUTION, authority.RESERVATION,
               'reports/progress_subgoal_v1_launch_claim.json', 'reports/progress_subgoal_v1_launch.json',
               'reports/progress_subgoal_v1_prelaunch.json', 'reports/progress_subgoal_v1_package_review.json'}
    return name in records or name.startswith('notebooks/progress-subgoal-v1-')


def _module_file(name):
    parts = name.split('.')
    if parts[0] not in PACKAGES:
        return None
    path = ROOT.joinpath(*parts)
    for candidate in (path.with_suffix('.py'), path / '__init__.py'):
        if candidate.is_file():
            return candidate.relative_to(ROOT).as_posix()
    return None


def _dependencies(name):
    import ast
    path = ROOT / name
    package = Path(name).parent.as_posix().replace('/', '.')
    modules, files = set(), set()
    for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ''
            if node.level:
                anchor = package.split('.')[:len(package.split('.')) - node.level + 1]
                base = '.'.join(anchor + ([base] if base else []))
            modules.add(base)
            modules.update(f'{base}.{alias.name}' for alias in node.names)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) < 200:
            text = node.value
            if text.split('.')[0] in PACKAGES and all(p.isidentifier() for p in text.split('.')):
                modules.add(text)
            elif (text.endswith(('.py', '.json', '.yaml')) and '/' in text and text in _tracked()
                  and not _sidecar(text)):
                files.add(text)
    for module in modules:
        parts = module.split('.')
        for n in range(1, len(parts) + 1):
            found = _module_file('.'.join(parts[:n]))
            if found:
                files.add(found)
    return files


def inventory():
    names = set(DATA_FILES)
    names.update(p.relative_to(ROOT).as_posix() for p in (ROOT / 'config').iterdir()
                 if p.is_file() and p.suffix in ('.json', '.yaml') and p.relative_to(ROOT).as_posix() in _tracked())
    seen = set()
    queue = list(ENTRY_POINTS) + sorted(p.relative_to(ROOT).as_posix()
                                        for p in (ROOT / 'research/progress_subgoal_v1').glob('*.py')
                                        if p.relative_to(ROOT).as_posix() in _tracked() and p.name not in BUILD_ONLY)
    while queue:
        name = queue.pop()
        if name in seen:
            continue
        seen.add(name)
        if name.endswith('.py'):
            queue.extend(sorted(_dependencies(name) - seen))
    names = {n for n in names | seen if '__pycache__' not in n}
    missing = [n for n in names if not (ROOT / n).is_file() or (ROOT / n).is_symlink()]
    if missing:
        raise ValueError('missing or linked review source: ' + ', '.join(sorted(missing)[:5]))
    untracked = sorted(n for n in names if n not in _tracked())
    if untracked:  # an untracked module import would make the package depend on the workspace
        raise ValueError('untracked review source: ' + ', '.join(untracked[:5]))
    return sorted(names)


def cell(hashes, packed):
    return ('import base64,hashlib,json,lzma,pathlib,shutil,sys,tempfile,time\n'
            'started=time.monotonic()\n'
            + MODE_LINE +
            "source=pathlib.Path(tempfile.mkdtemp(prefix='evidence-comprehension-source-'))\n"
            'try:\n'
            f'    bindings={hashes!r}\n'
            f'    payload=json.loads(lzma.decompress(base64.b85decode({packed!r})))\n'
            '    if set(payload)!=set(bindings): raise ValueError("source inventory")\n'
            '    for name,encoded in payload.items():\n'
            '        raw=base64.b64decode(encoded,validate=True)\n'
            '        if hashlib.sha256(raw).hexdigest()!=bindings[name]: raise ValueError("source hash: "+name)\n'
            '        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)\n'
            + MARKER +
            '    sys.path.insert(0,str(source))\n'
            '    from research.progress_subgoal_v1.launch import notebook_entry\n'
            '    notebook_entry(source,started,MODE)\n'
            'finally:\n'
            '    shutil.rmtree(source)\n')


def build(output=OUT):
    output = Path(output)
    if output.exists():
        raise FileExistsError('review revisions are immutable; create a new revision')
    payload = {name: (ROOT / name).read_bytes() for name in inventory()}
    hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in payload.items()}
    packed = base64.b85encode(lzma.compress(json.dumps({n: base64.b64encode(r).decode() for n, r in payload.items()},
                                                       sort_keys=True).encode(), preset=6)).decode()
    notebook = {'nbformat': 4, 'nbformat_minor': 4,
                'metadata': {'kernelspec': {'name': 'python3', 'display_name': 'Python 3', 'language': 'python'}},
                'cells': [{'cell_type': 'markdown', 'metadata': {},
                           'source': '# Evidence progress subgoal v1: review snapshot\n'
                                     'GPU disabled. The runnable cell requires separately bound source approval, '
                                     'compute authorization and one fresh reservation. 3,062 frozen questions in '
                                     '5,852 scheduled calls and one canary; no game actions.'},
                          {'cell_type': 'code', 'metadata': {}, 'execution_count': None, 'outputs': [],
                           'source': cell(hashes, packed)}]}
    metadata = {'id': 'daichongwei06/arc3-progress-subgoal-v1-review-' + REVISION,
                'title': 'ARC3 Progress Subgoal V1 Review ' + REVISION.upper(), 'code_file': 'profile.ipynb',
                'language': 'python', 'kernel_type': 'notebook', 'is_private': True, 'enable_gpu': False,
                'enable_tpu': False, 'enable_internet': False, 'competition_sources': ['arc-prize-2026-arc-agi-3'],
                'dataset_sources': ['driessmit1/arc3-vllm-h100-wheelhouse-v3'],
                'model_sources': ['qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1']}
    encoded = (json.dumps(notebook, indent=2) + '\n').encode()
    if len(encoded) >= 900000:
        raise ValueError('review notebook exceeds the upload size guard: %d bytes' % len(encoded))
    output.mkdir(parents=True)
    (output / 'profile.ipynb').write_bytes(encoded)
    (output / 'kernel-metadata.json').write_bytes((json.dumps(metadata, indent=2) + '\n').encode())
    lock = {'status': 'reviewed_launch_source', 'scope': 'progress-subgoal-v1', 'revision': REVISION,
            'bindings': hashes, 'artifacts': {n: hashlib.sha256((output / n).read_bytes()).hexdigest()
                                              for n in ('profile.ipynb', 'kernel-metadata.json')},
            'review_documents': {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in REVIEW_DOCUMENTS},
            'authorized_seconds': 0, 'gpu_launch_authorized': False}
    (output / 'review-source-lock.json').write_bytes((json.dumps(lock, indent=2) + '\n').encode())
    return lock


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    lock = build(args.output)
    print(json.dumps({'files': len(lock['bindings']), 'notebook_bytes': (args.output / 'profile.ipynb').stat().st_size}))
