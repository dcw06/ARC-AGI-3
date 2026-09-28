"""Derive the evidence-comprehension v2 runner, package scripts and regressions from v1's reviewed files.

v1's supervised questionnaire stack ran live (attempt ecv1-4458251e) and is hash-locked by its r3 review
lock, so it is reused, not edited. Each derived v2 file is exactly its v1 source with:
1. the global renames below (v1 names, paths, attempt prefix and rehearsal environment -> v2), then
2. that file's own substitutions, each required to match an exact number of times.

Nothing else differs; `--check` (and tests/test_evidence_comprehension_v2_derivation.py) fails if a derived
file drifts from this derivation. Behaviour that is genuinely new for v2 lives in hand-written modules:
research/evidence_comprehension_v2/{schedule,service,fake_server}.py (frozen schedule, v2 allow-list,
scripted v2 answers) and the question-set modules. transport.py and evidence.py re-export v1 unchanged.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BANNER = '# Derived from {source} by scripts/derive_evidence_comprehension_v2.py; edit the derivation, not this file.\n'
GLOBAL = (('evidence_comprehension_v1', 'evidence_comprehension_v2'),
          ('evidence-comprehension-v1', 'evidence-comprehension-v2'),
          ('ECV_', 'ECV2_'),
          ('ecv1-', 'ecv2-'),
          ('tests.ecv_diagnostics', 'tests.ecv2_diagnostics'),
          ('comprehension v1', 'comprehension v2'))
V1 = 'research/evidence_comprehension_v2/'  # post-rename spelling of v1's package path

# Rehearsal timing for v2's 8,004 scheduled calls (v1 had 1,308). The live values are unchanged.
REHEARSAL_SECONDS = 900
CUTOFF_REHEARSAL_SECONDS = 600  # admission cutoff at 300 s
SLOW_WITHHELD_PASS_1, SLOW_WITHHELD_PASS_2 = 0.08, 0.04

CALLS_V1 = """def calls(output):
    return [json.loads(p.read_bytes()) for p in sorted((output / 'worker/run/calls').glob('*.json'))]


def rewrite(output, name, mutate):
    \"\"\"Change one retained run file and re-hash it into the manifest (a consistent forgery).\"\"\"
    folder = output / 'worker/run'
    path = folder / name
    value = json.loads(path.read_bytes())
    mutate(value)
    raw = encode(value)
    path.write_bytes(raw)
    manifest = json.loads((folder / MANIFEST).read_bytes())
    manifest['files'][name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    (folder / MANIFEST).write_bytes(encode(manifest))
"""
CALLS_V2 = """def calls(output):
    return load_unverified_calls(output / 'worker/run')  # v2 keeps calls in one append-only log


def rewrite(output, name, mutate):
    \"\"\"Change one retained run record and re-hash it into the manifest (a consistent forgery).\"\"\"
    forge(output / 'worker/run', name, mutate)
"""
TRUNCATE_V1 = """            folder = truncated / 'worker/run'
            manifest = json.loads((folder / MANIFEST).read_bytes())
            for c in retained[454:]:
                name = f'calls/{c["index"]:05d}.json'
                (folder / name).unlink()
                del manifest['files'][name]
            (folder / MANIFEST).write_bytes(encode(manifest))
            rewrite(truncated, 'run.json', lambda v: v.update(calls_recorded=454))
"""
TRUNCATE_V2 = """            truncate(truncated / 'worker/run', 3472)  # keep withheld pass 1 only
            rewrite(truncated, 'run.json', lambda v: v.update(calls_recorded=3472))
"""
SCHEDULE_CALL = ("    order = call_order(frozen['probes'])\n", "    order = call_order(frozen)\n", 1)
DERIVED = {
    'research/evidence_comprehension_v2/authority.py': ('research/evidence_comprehension_v1/authority.py', (
        ("REVIEW = 'notebooks/evidence-comprehension-v2-review-r3/review-source-lock.json'",
         "REVIEW = 'notebooks/evidence-comprehension-v2-review-r1/review-source-lock.json'", 1),
        ("'maximum_questionnaire_calls': 1308,", "'maximum_questionnaire_calls': 8004,", 1),
        ("                    'supervisor.py', 'evidence.py')}\n",
         "                    'supervisor.py', 'evidence.py', 'fake_server.py', 'trajectories.py', 'representation.py')}\n"
         "REQUIRED_SOURCE |= {'research/evidence_comprehension_v1/' + name for name in  # v1's modules, reused unchanged\n"
         "                    ('probes.py', 'probes.json', 'score.py', 'schedule.py', 'transport.py', 'service.py',\n"
         "                     'evidence.py', 'fake_server.py')}\n", 1),
    )),
    'research/evidence_comprehension_v2/host.py': ('research/evidence_comprehension_v1/host.py', ()),
    'research/evidence_comprehension_v2/worker.py': ('research/evidence_comprehension_v1/worker.py', (
        ("'slow_gate_pass_1', 'slow_gate_pass_2') + HOST_FAULTS",
         "'slow_withheld_pass_1', 'slow_withheld_pass_2') + HOST_FAULTS", 1),
        ("# Rehearsal per-call latencies chosen so the admission cutoff falls inside gate pass 1 or gate pass 2.\n"
         "SLOW_LATENCY = {'slow_gate_pass_1': 0.35, 'slow_gate_pass_2': 0.12}",
         "# Rehearsal per-call latencies chosen so the admission cutoff falls inside withheld pass 1 or pass 2.\n"
         f"SLOW_LATENCY = {{'slow_withheld_pass_1': {SLOW_WITHHELD_PASS_1}, "
         f"'slow_withheld_pass_2': {SLOW_WITHHELD_PASS_2}}}", 1),
    )),
    'research/evidence_comprehension_v2/runner.py': ('research/evidence_comprehension_v1/runner.py', (SCHEDULE_CALL,)),
    'research/evidence_comprehension_v2/resources.py': ('research/evidence_comprehension_v1/resources.py', ()),
    'research/evidence_comprehension_v2/monitor.py': ('research/evidence_comprehension_v1/monitor.py', (
        ("(output / 'worker/run/calls/00000.json').exists()", "(output / 'worker/run/calls.jsonl').exists()", 1),
    )),
    'research/evidence_comprehension_v2/supervisor.py': ('research/evidence_comprehension_v1/supervisor.py', ()),
    'scripts/evidence_comprehension_v2_launch.py': ('scripts/evidence_comprehension_v1_launch.py', ()),
    'scripts/evidence_comprehension_v2_package.py': ('scripts/evidence_comprehension_v1_package.py', (
        ("'A retrospective questionnaire: 654 frozen questions in two passes (1,308 calls) and one canary; no game '",
         "'A retrospective questionnaire: 4,532 frozen questions in 8,004 scheduled calls (the withheld partition '\n"
         "        'twice) and one canary; no game '", 1),
    )),
    'scripts/build_evidence_comprehension_v2_review.py': ('scripts/build_evidence_comprehension_v1_review.py', (
        ("REVISION = 'r3'", "REVISION = 'r1'", 1),
        None,  # REVIEW_DOCUMENTS: filled in below
        None,  # inventory(): filled in below
        ("'compute authorization and one fresh reservation. 654 frozen questions in two '\n"
         "                                     'passes (1,308 calls) and one canary; no game actions.'",
         "'compute authorization and one fresh reservation. 4,532 frozen questions in '\n"
         "                                     '8,004 scheduled calls and one canary; no game actions.'", 1),
        ("'ARC3 Action Effect History V1 Review '", "'ARC3 Evidence Comprehension V2 Review '", 1),
    )),
    'scripts/review_evidence_comprehension_v2_notebook.py': ('scripts/review_evidence_comprehension_v1_notebook.py', (
        ('REHEARSAL_SECONDS = 480', f'REHEARSAL_SECONDS = {REHEARSAL_SECONDS}', 1),
    )),
    'scripts/rehearse_evidence_comprehension_v2.py': ('scripts/rehearse_evidence_comprehension_v1.py', (
        ("def rehearse(fault='none', seconds=480,", f"def rehearse(fault='none', seconds={REHEARSAL_SECONDS},", 1),
        ("parser.add_argument('--seconds', type=int, default=480)",
         f"parser.add_argument('--seconds', type=int, default={REHEARSAL_SECONDS})", 1),
    )),
    'scripts/evaluate_evidence_comprehension_v2.py': ('scripts/evaluate_evidence_comprehension_v1.py', (
        SCHEDULE_CALL,
        ("    gate_status = analysis['gate_status'] if analysis else 'incomplete'",
         "    gate_status = analysis['withheld_status'] if analysis else 'incomplete'", 1),
        ("            'gate': analysis['gate'] if analysis else None,",
         "            'gate': analysis['verdicts'] if analysis else None,", 1),
    )),
    'scripts/check_evidence_comprehension_v2.py': ('scripts/check_evidence_comprehension_v1.py', (
        ("'transport_cancellation_and_cache_metrics': 'tests.test_evidence_comprehension_v2_transport',",
         "'transport_cancellation_and_cache_metrics': 'tests.test_evidence_comprehension_v1_transport',  # reused", 1),
        ("'connected_path_rehearsals': 'tests.test_evidence_comprehension_v2_connected'}",
         "'connected_path_rehearsals': 'tests.test_evidence_comprehension_v2_connected',\n"
         "          'runtime_derivation_and_inventory': 'tests.test_evidence_comprehension_v2_derivation'}", 1),
    )),
    'tests/test_evidence_comprehension_v2_connected.py': ('tests/test_evidence_comprehension_v1_connected.py', (
        ('REHEARSAL_SECONDS = 480', f'REHEARSAL_SECONDS = {REHEARSAL_SECONDS}', 1),
        ('CUTOFF_REHEARSAL_SECONDS = 420  # admission cutoff at 120 s',
         f'CUTOFF_REHEARSAL_SECONDS = {CUTOFF_REHEARSAL_SECONDS}  # admission cutoff at '
         f'{CUTOFF_REHEARSAL_SECONDS - 300} s', 1),
        ("{'answered': 1308}", "{'answered': 8004}", 1),
        ("value['analysis']['both_correct']['evidence_only/recall_action']['correct']",
         "value['analysis']['families']['withheld']['baseline']['outcome_class']['correct']", 1),
        ("changed['analysis']['both_correct']['evidence_only/recall_action']['correct']",
         "changed['analysis']['families']['withheld']['baseline']['outcome_class']['correct']", 1),
        ("            flip = next(c for c in retained if c['phase'] == 'gate_pass_1'\n"
         "                        and probes[c['probe_id']]['family'] == 'recall_action' and c['response'].startswith('{')\n",
         "            flip = next(c for c in retained if c['phase'] == 'withheld_pass_1'\n"
         "                        and probes[c['probe_id']]['family'] == 'outcome_class'\n"
         "                        and probes[c['probe_id']]['condition'] == 'baseline' and c['response'].startswith('{')\n"
         "                        and int(hashlib.sha256(c['probe_id'].encode()).hexdigest(), 16) % 100 >= 12\n", 1),
        ("            wrong = 'not_shown' if probes[flip['probe_id']]['key'] != 'not_shown' else {'action_id': 1, 'action_data': {}}",
         "            wrong = 'not_shown' if probes[flip['probe_id']]['key'] != 'not_shown' else 'dispatch_failed'", 1),
        ("from research.evidence_comprehension_v2.evidence import MANIFEST, encode",
         "from research.evidence_comprehension_v2.evidence import forge, load_unverified_calls, truncate", 1),
        (CALLS_V1, CALLS_V2, 1),
        ("                direct = [json.loads(p.read_bytes()) for p in sorted((Path(tmp) / 'run/calls').glob('*.json'))]",
         "                direct = load_unverified_calls(Path(tmp) / 'run')", 1),
        (TRUNCATE_V1, TRUNCATE_V2, 1),
        ("        family = next(p['family'] for p in", "        track = next(p['track'] for p in", 1),
        ("        self.assertEqual(value['gate'][family], 'incomplete')",
         "        self.assertEqual(value['gate'][track], 'incomplete')", 1),
        ("(('slow_gate_pass_1', 'gate_pass_1'), ('slow_gate_pass_2', 'gate_pass_2'))",
         "(('slow_withheld_pass_1', 'withheld_pass_1'), ('slow_withheld_pass_2', 'withheld_pass_2'))", 1),
    )),
    'tests/test_evidence_comprehension_v2_schedule.py': ('tests/test_evidence_comprehension_v1_schedule.py', (
        ("from research.evidence_comprehension_v2.probes import GATE_CONDITION",
         "from research.evidence_comprehension_v2.evidence import load_unverified_calls\n"
         "from research.evidence_comprehension_v2.probes import GATE_PARTITION", 1),
        ("            third = json.loads((Path(folder) / 'run/calls/00002.json').read_bytes())",
         "            third = load_unverified_calls(Path(folder) / 'run')[2]  # v2 keeps calls in one log", 2),
        ("PROBES = json.loads(B.OUTPUT.read_bytes())['probes']",
         "FROZEN = json.loads(B.OUTPUT.read_bytes())\nPROBES = FROZEN['probes']", 1),
        ("S.call_order(PROBES)", "S.call_order(FROZEN)", 3),
        ("S.call_order(frozen['probes'])", "S.call_order(frozen)", 1),
        ("p['condition'] == GATE_CONDITION", "p['partition'] == GATE_PARTITION", 3),
        ("        self.assertEqual(len(order), 2 * len(PROBES))\n"
         "        self.assertEqual([i for ph, _, i in order if ph == 'gate_pass_1'], gate)\n"
         "        self.assertEqual([i for ph, _, i in order if ph == 'gate_pass_2'], gate[::-1])\n",
         "        self.assertEqual(len(order), sum(2 if p['partition'] == GATE_PARTITION else 1 for p in PROBES))\n"
         "        first = [i for ph, _, i in order if ph == 'withheld_pass_1']\n"
         "        self.assertEqual(sorted(first), sorted(gate))\n"
         "        self.assertEqual([i for ph, _, i in order if ph == 'withheld_pass_2'], first[::-1])\n", 1),
        ("'scheduled_calls': 2 * len(frozen['probes'])}", "'scheduled_calls': len(S.call_order(frozen))}", 1),
        ("report['gate_status']", "report['withheld_status']", 3),
        ("        self.assertNotIn('criterion_met', report['gate'].values())",
         "        self.assertEqual(set(report['verdicts'].values()), {'incomplete'})", 1),
        ("        # 3.5 s per call: gate pass 1 completes, pass 2 is cut.\n"
         "        passes, admission, started, clock = simulate(3.5)",
         "        # 0.5 s per call: withheld pass 1 completes, pass 2 is cut.\n"
         "        passes, admission, started, clock = simulate(0.5)", 1),
        ("        passes, admission, started, clock = simulate(0.5)\n        report = analyze(PROBES, passes)",
         "        passes, admission, started, clock = simulate(0.2)\n        report = analyze(PROBES, passes)", 1),
        ("        self.assertEqual(set(report['gate'].values()), {'criterion_met'})",
         "        self.assertEqual(set(report['verdicts'].values()), {'baseline_meets_criterion'})", 1),
        ("        self.assertEqual(started, 2 * len(PROBES))", "        self.assertEqual(started, len(S.call_order(FROZEN)))", 1),
    )),
    'tests/test_evidence_comprehension_v2_snapshot.py': ('tests/test_evidence_comprehension_v1_snapshot.py', ()),
    'tests/test_evidence_comprehension_v2_diagnostics.py': ('tests/test_evidence_comprehension_v1_diagnostics.py', ()),
    'tests/ecv2_diagnostics_fixtures.py': ('tests/ecv_diagnostics_fixtures.py', ()),
    'tests/ecv2_diagnostics_module_fixture.py': ('tests/ecv_diagnostics_module_fixture.py', ()),
}

REVIEW_DOCUMENTS_V1_START = 'REVIEW_DOCUMENTS = ('
REVIEW_DOCUMENTS_V2 = '''REVIEW_DOCUMENTS = ('reports/evidence_comprehension_v2_protocol.md', 'reports/evidence_comprehension_v2_protocol_r1.md',
                    'reports/evidence_comprehension_v2_probe_summary.json',
                    'reports/evidence_comprehension_v2_token_audit.json',
                    'reports/evidence_comprehension_v2_rehearsal_results.json',
                    'reports/evidence_comprehension_v2_review.md',
                    'reports/evidence_comprehension_v1_baseline_freeze.json',
                    'scripts/build_evidence_comprehension_v2.py', 'scripts/audit_evidence_comprehension_v2_tokens.py',
                    'scripts/derive_evidence_comprehension_v2.py', 'scripts/evidence_comprehension_v2_package.py',
                    'scripts/review_evidence_comprehension_v2_notebook.py',
                    'scripts/build_evidence_comprehension_v2_review.py', 'scripts/check_evidence_comprehension_v2.py',
                    'tests/test_evidence_comprehension_v2.py', 'tests/test_evidence_comprehension_v2_derivation.py',
                    'tests/test_evidence_comprehension_v2_schedule.py', 'tests/test_evidence_comprehension_v1_transport.py',
                    'tests/test_evidence_comprehension_v2_connected.py', 'tests/test_evidence_comprehension_v2_snapshot.py',
                    'tests/test_evidence_comprehension_v2_diagnostics.py', 'tests/ecv2_diagnostics_fixtures.py',
                    'tests/ecv2_diagnostics_module_fixture.py')
'''
INVENTORY_V2 = '''# The notebook carries the import closure of its entry points, not whole directories: v1's broad inventory
# (822 kB) left no room for the v2 question set under the 900 kB upload guard. Imports are followed
# statically (including function-level imports and dotted module names or repository file paths written as
# strings); data files read by path are listed explicitly, as v1 listed them.
ENTRY_POINTS = ('scripts/evidence_comprehension_v2_launch.py', 'scripts/evaluate_evidence_comprehension_v2.py',
                'scripts/rehearse_evidence_comprehension_v2.py', 'scripts/run_grounded_action_v1_engine_local.py',
                'certification/phase4_integrated_v2/gated_exec.py')
DATA_FILES = ('research/evidence_comprehension_v2/probes.json', 'research/evidence_comprehension_v1/probes.json',
              'research/action_effect_v1/fixtures.json', 'research/action_effect_history_v1/protocol.json',
              'reports/phase4_v2_offline_package.json', 'reports/phase4_torch_wheel_inspection.json',
              'reports/phase4_transient_v2_protocol.json', 'reports/m0_profiles/m0-q3vl30-instruct.json',
              'reports/perception_stage_b_v1_case_protocol.json', 'reports/integrated_case_v1/initial_observation.json',
              'reports/integrated_case_v1/geometry_reference.json',
              'certification/phase4_integrated_v2/tokenizer_manifest.json')
PACKAGES = ('agent', 'certification', 'evaluation', 'research', 'scripts')


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
            elif text.endswith(('.py', '.json', '.yaml')) and '/' in text and (ROOT / text).is_file():
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
                 if p.is_file() and p.suffix in ('.json', '.yaml'))
    seen = set()
    queue = list(ENTRY_POINTS) + sorted(p.relative_to(ROOT).as_posix()
                                        for p in (ROOT / 'research/evidence_comprehension_v2').glob('*.py'))
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
    return sorted(names)
'''


def _between(text, start, end):
    i = text.index(start)
    j = text.index(end, i) + len(end)
    return text[i:j]


def derive_one(target):
    source, rules = DERIVED[target]
    text = (ROOT / source).read_text(encoding='utf-8')
    for old, new in GLOBAL:
        text = text.replace(old, new)
    for rule in rules:
        if rule is None:
            continue
        old, new, count = rule
        found = text.count(old)
        if found != count:
            raise ValueError(f'{target}: expected {count} of {old[:70]!r}, found {found}')
        text = text.replace(old, new)
    if target == 'scripts/build_evidence_comprehension_v2_review.py':
        documents = _between(text, REVIEW_DOCUMENTS_V1_START, "'scripts/replay_evidence_comprehension_v2_run_a.py')\n")
        text = text.replace(documents, REVIEW_DOCUMENTS_V2, 1)
        old_inventory = _between(text, 'def inventory():', '    return sorted(names)\n')
        text = text.replace(old_inventory, INVENTORY_V2, 1)
    if 'evidence_comprehension_v1' in text.replace('research/evidence_comprehension_v1/', '').replace(
            'tests.test_evidence_comprehension_v1_transport', '').replace(
            'tests/test_evidence_comprehension_v1_transport', '').replace(
            'evidence_comprehension_v1_baseline_freeze', ''):
        raise ValueError(f'{target}: unexpected remaining v1 reference')
    return BANNER.format(source=source) + text


def derive():
    return {target: derive_one(target) for target in DERIVED}


def stale():
    return [t for t, text in derive().items()
            if not (ROOT / t).is_file() or (ROOT / t).read_text(encoding='utf-8') != text]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='fail if any derived file differs from the derivation')
    args = parser.parse_args()
    if args.check:
        drift = stale()
        if drift:
            raise SystemExit('derived files differ from the derivation: ' + ', '.join(drift))
        print(f'{len(DERIVED)} derived files match the derivation')
        sys.exit(0)
    for target, text in derive().items():
        (ROOT / target).write_text(text, encoding='utf-8', newline='\n')
    print(f'wrote {len(DERIVED)} derived files')
