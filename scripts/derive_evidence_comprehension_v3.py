"""Derive the evidence-comprehension v3 runner, package scripts and regressions from v2's reviewed files.

v2's files (themselves derived from v1's, and bound by v2's review lock `de9642c6…82a3`) ran live as attempt
ecv2-65759c16 and are reused, not edited. Each derived v3 file is its v2 source with v2's banner line removed,
the global renames below (v2 -> v3 names, paths, attempt prefix `ecv3-`, rehearsal environment `ECV3_`), and that
file's own substitutions, each required to match an exact number of times.

Hand-written v3 runtime (not derived): research/evidence_comprehension_v3/{schedule,service,fake_server,
evidence,transport}.py re-export or minimally subclass v1/v2 objects, and the question-set modules.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BANNER = '# Derived from {source} by scripts/derive_evidence_comprehension_v3.py; edit the derivation, not this file.\n'
GLOBAL = (('evidence_comprehension_v2', 'evidence_comprehension_v3'),
          ('evidence-comprehension-v2', 'evidence-comprehension-v3'),
          ('ECV2_', 'ECV3_'),
          ('ecv2-', 'ecv3-'),
          ('tests.ecv2_diagnostics', 'tests.ecv3_diagnostics'),
          ('comprehension v2', 'comprehension v3'))
SLOW_WITHHELD_PASS_1, SLOW_WITHHELD_PASS_2 = 0.12, 0.05  # rehearsal: cutoff inside withheld pass 1 / pass 2
STRIP_SUFFIX = "{{v.removesuffix('_tool_assisted') for v in {name}['gate'].values()}}"
V2 = 'research/evidence_comprehension_v2/'


def src(name):
    return name.replace('evidence_comprehension_v3', 'evidence_comprehension_v2').replace(
        'ecv3_diagnostics', 'ecv2_diagnostics')


DERIVED = {
    'research/evidence_comprehension_v3/authority.py': (
        ("'maximum_questionnaire_calls': 8004,", "'maximum_questionnaire_calls': 6054,", 1),
        ("'supervisor.py', 'evidence.py', 'fake_server.py', 'trajectories.py', 'representation.py')}\n",
         "'supervisor.py', 'evidence.py', 'fake_server.py', 'cases.py', 'representation.py')}\n"
         "REQUIRED_SOURCE |= {'research/evidence_comprehension_v2/' + name for name in  # v2's modules, reused unchanged\n"
         "                    ('probes.py', 'representation.py', 'score.py', 'evidence.py', 'independent.py',\n"
         "                     'schedule.py', 'fake_server.py')}\n", 1),
    ),
    'research/evidence_comprehension_v3/host.py': (),
    'research/evidence_comprehension_v3/worker.py': (
        ("SLOW_LATENCY = {'slow_withheld_pass_1': 0.08, 'slow_withheld_pass_2': 0.04}",
         f"SLOW_LATENCY = {{'slow_withheld_pass_1': {SLOW_WITHHELD_PASS_1}, "
         f"'slow_withheld_pass_2': {SLOW_WITHHELD_PASS_2}}}", 1),
    ),
    'research/evidence_comprehension_v3/runner.py': (),
    'research/evidence_comprehension_v3/resources.py': (),
    'research/evidence_comprehension_v3/monitor.py': (),
    'research/evidence_comprehension_v3/supervisor.py': (),
    'scripts/evidence_comprehension_v3_launch.py': (),
    'scripts/evidence_comprehension_v3_package.py': (
        ("'A retrospective questionnaire: 4,532 frozen questions in 8,004 scheduled calls (the withheld partition '",
         "'A retrospective questionnaire: 3,390 frozen questions in 6,054 scheduled calls (the withheld partition '", 1),
    ),
    'scripts/build_evidence_comprehension_v3_review.py': (
        ("'compute authorization and one fresh reservation. 4,532 frozen questions in '\n"
         "                                     '8,004 scheduled calls and one canary; no game actions.'",
         "'compute authorization and one fresh reservation. 3,390 frozen questions in '\n"
         "                                     '6,054 scheduled calls and one canary; no game actions.'", 1),
        ("'ARC3 Evidence Comprehension V2 Review '", "'ARC3 Evidence Comprehension V3 Review '", 1),
        ("                    'reports/evidence_comprehension_v1_baseline_freeze.json',\n",
         "                    'reports/evidence_comprehension_v1_baseline_freeze.json',\n"
         "                    'reports/evidence_comprehension_v2_results.md', 'reports/evidence_comprehension_v3_design.md',\n",
         1),
    ),
    'scripts/review_evidence_comprehension_v3_notebook.py': (),
    'scripts/rehearse_evidence_comprehension_v3.py': (),
    'scripts/evaluate_evidence_comprehension_v3.py': (
        ("    gate_status = analysis['withheld_status'] if analysis else 'incomplete'",
         "    gate_status = ('complete' if analysis and set(analysis['completeness']['primary'].values()) == {'complete'}\n"
         "                   else 'incomplete')  # v3: primary completeness of both tracks", 1),
    ),
    'scripts/check_evidence_comprehension_v3.py': (),
    'tests/test_evidence_comprehension_v3_connected.py': (
        ("{'answered': 8004}", "{'answered': 6054}", 1),
        ("['families']['withheld']['baseline']['outcome_class']['correct']",
         "['families']['withheld']['original']['B0_normalized_history']['outcome_class']['correct']", 2),
        ("probes[c['probe_id']]['condition'] == 'baseline'", "probes[c['probe_id']]['condition'] == 'B0_normalized_history'", 1),
        ("truncate(truncated / 'worker/run', 3472)", "truncate(truncated / 'worker/run', 2664)", 1),
        ("calls_recorded=3472", "calls_recorded=2664", 1),
        ("set(result['gate'].values()), {'incomplete'}", STRIP_SUFFIX.format(name='result') + ", {'incomplete'}", 1),
        ("set(value['gate'].values()), {'incomplete'}", STRIP_SUFFIX.format(name='value') + ", {'incomplete'}", 1),
        ("        self.assertEqual(value['gate'][track], 'incomplete')",
         "        self.assertTrue(value['gate'][track].startswith('incomplete'))", 1),
    ),
    'tests/test_evidence_comprehension_v3_schedule.py': (
        ("report['withheld_status']", "report['completeness']['withheld_schedule']", 3),
        ("        self.assertEqual(set(report['verdicts'].values()), {'incomplete'})",
         "        self.assertEqual({v.removesuffix('_tool_assisted') for v in report['verdicts'].values()}, {'incomplete'})", 1),
        ("        self.assertEqual(set(report['verdicts'].values()), {'baseline_meets_criterion'})",
         "        self.assertEqual({v.removesuffix('_tool_assisted') for v in report['verdicts'].values()},\n"
         "                         {'baseline_meets_criterion'})", 1),
    ),
    'tests/test_evidence_comprehension_v3_snapshot.py': (),
    'tests/test_evidence_comprehension_v3_diagnostics.py': (),
    'tests/ecv3_diagnostics_fixtures.py': (),
    'tests/ecv3_diagnostics_module_fixture.py': (),
}
ALLOWED_V2 = ("research/evidence_comprehension_v2/' + name",)


def derive_one(target):
    source = src(target)
    lines = (ROOT / source).read_text(encoding='utf-8').splitlines(keepends=True)
    if lines and lines[0].startswith('# Derived from '):
        lines = lines[1:]
    text = ''.join(lines)
    for old, new in GLOBAL:
        text = text.replace(old, new)
    for old, new, count in DERIVED[target]:
        found = text.count(old)
        if found != count:
            raise ValueError(f'{target}: expected {count} of {old[:70]!r}, found {found}')
        text = text.replace(old, new)
    residue = text
    for allowed in ALLOWED_V2 + ('reports/evidence_comprehension_v2_results.md',):
        residue = residue.replace(allowed, '')
    if 'evidence_comprehension_v2' in residue or 'ecv2-' in residue or 'ECV2_' in residue:
        raise ValueError(f'{target}: unexpected remaining v2 reference')
    return BANNER.format(source=source) + text


def derive():
    return {target: derive_one(target) for target in DERIVED}


def stale():
    return [t for t, text in derive().items()
            if not (ROOT / t).is_file() or (ROOT / t).read_text(encoding='utf-8') != text]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    if parser.parse_args().check:
        drift = stale()
        if drift:
            raise SystemExit('derived files differ from the derivation: ' + ', '.join(drift))
        print(f'{len(DERIVED)} derived files match the derivation')
        sys.exit(0)
    for target, text in derive().items():
        (ROOT / target).write_text(text, encoding='utf-8', newline='\n')
    print(f'wrote {len(DERIVED)} derived files')
