"""Derive the WS3 transition-questionnaire runner, package scripts and regressions from v3's reviewed files.

v3's files (derived from v2's, themselves from v1's; bound by v3's review lock `66713c62…5cfd`) ran live as attempt
ecv3-089bf11f and are reused, not edited. Each derived WS3 file is its v3 source with v3's banner line removed, the
global renames below (v3 -> WS3 names, paths, attempt prefix `ws3q-`, rehearsal environment `WS3Q_`), and that file's
own substitutions, each required to match an exact number of times.

Hand-written WS3 runtime (not derived): research/ws3_questionnaire_v1/{probes,score,schedule,service,fake_server,
evidence,transport}.py, which adapt the frozen question set or re-export reviewed objects unchanged.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BANNER = '# Derived from {source} by scripts/derive_ws3_questionnaire_v1.py; edit the derivation, not this file.\n'
GLOBAL = (('evidence_comprehension_v3', 'ws3_questionnaire_v1'),
          ('evidence-comprehension-v3', 'ws3-questionnaire-v1'),
          ('ECV3_', 'WS3Q_'),
          ('ecv3-', 'ws3q-'),
          ('tests.ecv3_diagnostics', 'tests.ws3q_diagnostics'),
          ('comprehension v3', 'ws3 questionnaire v1'))
TARGET_TO_SOURCE = (('ws3_questionnaire_v1', 'evidence_comprehension_v3'), ('ws3q_diagnostics', 'ecv3_diagnostics'))
STRIP = "{{{name}.removesuffix('_tool_assisted')}}"

REQUIRED_OLD = """REQUIRED_SOURCE = {'research/ws3_questionnaire_v1/' + name for name in
                   ('authority.py', 'probes.py', 'probes.json', 'independent.py', 'score.py', 'schedule.py',
                    'transport.py', 'service.py', 'host.py', 'worker.py', 'runner.py', 'monitor.py', 'resources.py',
                    'supervisor.py', 'evidence.py', 'fake_server.py', 'cases.py', 'representation.py')}
REQUIRED_SOURCE |= {'research/evidence_comprehension_v2/' + name for name in  # v2's modules, reused unchanged
                    ('probes.py', 'representation.py', 'score.py', 'evidence.py', 'independent.py',
                     'schedule.py', 'fake_server.py')}
"""
REQUIRED_NEW = """REQUIRED_SOURCE = {'research/ws3_questionnaire_v1/' + name for name in
                   ('authority.py', 'probes.py', 'probes.json', 'score.py', 'schedule.py', 'transport.py',
                    'service.py', 'host.py', 'worker.py', 'runner.py', 'monitor.py', 'resources.py', 'supervisor.py',
                    'evidence.py', 'fake_server.py')}
REQUIRED_SOURCE |= {'research/transition_evidence_v1/' + name for name in  # the questionnaire and its records
                    ('questionnaire.py', 'score.py', 'transition.py', 'reference.py', 'vocabulary.py', 'fixtures.py')}
REQUIRED_SOURCE |= {'research/evidence_comprehension_v2/' + name for name in  # v2's modules, reused unchanged
                    ('score.py', 'evidence.py', 'schedule.py', 'fake_server.py')}
"""
DOCS_START = "REVIEW_DOCUMENTS = ("
DOCS_NEW = """REVIEW_DOCUMENTS = ('reports/ws3_questionnaire_design_draft_r2.md', 'reports/ws3_questionnaire_design_draft.md',
                    'reports/ws3_event_specification.md', 'reports/ws3_gap_report.md',
                    'reports/ws3_transition_replay_v1.md', 'reports/ws3_questionnaire_v1_probe_summary.json',
                    'reports/ws3_questionnaire_token_audit.json', 'reports/ws3_questionnaire_v1_rehearsal_results.json',
                    'reports/ws3_questionnaire_v1_review.md', 'reports/evidence_comprehension_v3_results.md',
                    'scripts/build_ws3_questionnaire_v1.py', 'scripts/audit_ws3_questionnaire_tokens.py',
                    'scripts/derive_ws3_questionnaire_v1.py', 'scripts/ws3_questionnaire_v1_package.py',
                    'scripts/review_ws3_questionnaire_v1_notebook.py', 'scripts/build_ws3_questionnaire_v1_review.py',
                    'scripts/check_ws3_questionnaire_v1.py', 'tests/test_ws3_questionnaire_draft.py',
                    'tests/test_transition_evidence_v1.py', 'tests/test_ws3_questionnaire_v1_derivation.py',
                    'tests/test_ws3_questionnaire_v1_schedule.py', 'tests/test_evidence_comprehension_v1_transport.py',
                    'tests/test_ws3_questionnaire_v1_connected.py', 'tests/test_ws3_questionnaire_v1_snapshot.py',
                    'tests/test_ws3_questionnaire_v1_diagnostics.py', 'tests/ws3q_diagnostics_fixtures.py',
                    'tests/ws3q_diagnostics_module_fixture.py')
"""

DERIVED = {
    'research/ws3_questionnaire_v1/authority.py': (
        ("'maximum_questionnaire_calls': 6054,", "'maximum_questionnaire_calls': 5616,", 1),
        ("REVIEW = 'notebooks/ws3-questionnaire-v1-review-r1/review-source-lock.json'",
         "REVIEW = 'notebooks/ws3-questionnaire-v1-review-r2/review-source-lock.json'", 1),
        (REQUIRED_OLD, REQUIRED_NEW, 1),
    ),
    'research/ws3_questionnaire_v1/host.py': (),
    'research/ws3_questionnaire_v1/worker.py': (
        ("SLOW_LATENCY = {'slow_withheld_pass_1': 0.12, 'slow_withheld_pass_2': 0.05}",
         "SLOW_LATENCY = {'slow_withheld_pass_1': 0.13, 'slow_withheld_pass_2': 0.06}", 1),
    ),
    'research/ws3_questionnaire_v1/runner.py': (),
    'research/ws3_questionnaire_v1/resources.py': (),
    'research/ws3_questionnaire_v1/monitor.py': (),
    'research/ws3_questionnaire_v1/supervisor.py': (),
    'scripts/ws3_questionnaire_v1_launch.py': (),
    'scripts/ws3_questionnaire_v1_package.py': (
        ("'A retrospective questionnaire: 3,390 frozen questions in 6,054 scheduled calls (the withheld partition '",
         "'A retrospective transition questionnaire: 3,116 frozen questions in 5,616 scheduled calls (the withheld partition '",
         1),
    ),
    'scripts/build_ws3_questionnaire_v1_review.py': (
        ("REVISION = 'r1'", "REVISION = 'r2'", 1),
        ("            elif text.endswith(('.py', '.json', '.yaml')) and '/' in text and (ROOT / text).is_file():",
         "            elif text.endswith(('.py', '.json', '.yaml')) and '/' in text and text in _tracked():", 1),
        ("def _module_file(name):", '_TRACKED = []\n\n\ndef _tracked():\n    """Files tracked by git. Packaging depends only on tracked content, never on incidental workspace files (e.g. an\n    extracted archive member that happens to exist locally)."""\n    if not _TRACKED:\n        import subprocess\n        out = subprocess.run([\'git\', \'ls-files\', \'-z\'], cwd=ROOT, capture_output=True, check=True).stdout\n        _TRACKED.append(frozenset(n for n in out.decode().split(\'\\0\') if n))\n    return _TRACKED[0]\n\n\ndef _module_file(name):', 1),
        ("                 if p.is_file() and p.suffix in ('.json', '.yaml'))",
         "                 if p.is_file() and p.suffix in ('.json', '.yaml') and p.relative_to(ROOT).as_posix() in _tracked())", 1),
        ("                                        for p in (ROOT / 'research/ws3_questionnaire_v1').glob('*.py'))",
         "                                        for p in (ROOT / 'research/ws3_questionnaire_v1').glob('*.py')\n"
         "                                        if p.relative_to(ROOT).as_posix() in _tracked())", 1),
        ("        raise ValueError('missing or linked review source: ' + ', '.join(sorted(missing)[:5]))\n",
         "        raise ValueError('missing or linked review source: ' + ', '.join(sorted(missing)[:5]))\n"
         "    untracked = sorted(n for n in names if n not in _tracked())\n"
         "    if untracked:  # an untracked module import would make the package depend on the workspace\n"
         "        raise ValueError('untracked review source: ' + ', '.join(untracked[:5]))\n", 1),
        ("'compute authorization and one fresh reservation. 3,390 frozen questions in '\n"
         "                                     '6,054 scheduled calls and one canary; no game actions.'",
         "'compute authorization and one fresh reservation. 3,116 frozen questions in '\n"
         "                                     '5,616 scheduled calls and one canary; no game actions.'", 1),
        ("'ARC3 Evidence Comprehension V3 Review '", "'ARC3 WS3 Questionnaire V1 Review '", 1),
    ),
    'scripts/review_ws3_questionnaire_v1_notebook.py': (),
    'scripts/rehearse_ws3_questionnaire_v1.py': (),
    'scripts/evaluate_ws3_questionnaire_v1.py': (
        ("    gate_status = ('complete' if analysis and set(analysis['completeness']['primary'].values()) == {'complete'}\n"
         "                   else 'incomplete')  # v3: primary completeness of both tracks",
         "    gate_status = ('complete' if analysis and analysis['completeness']['withheld'] == 'complete'\n"
         "                   else 'incomplete')  # WS3: every withheld answer; the verdict applies its own policy", 1),
        ("            'gate': analysis['verdicts'] if analysis else None,",
         "            'gate': ({'questionnaire': 'incomplete' if recovered else analysis['verdict']}\n"
         "                     if analysis else None),", 1),
        # Review of 95aef4f: recovered (interrupted) evidence keeps its answers for descriptive analysis, but it is
        # never technically complete and never carries a promotable verdict.
        ("        evidence = {'verified': True}\n",
         "        recovered = run.get('evidence_recovery')\n"
         "        evidence = {'verified': True, 'recovered': bool(recovered)}\n"
         "        if recovered:\n"
         "            evidence['evidence_recovery'] = recovered\n", 1),
        ("    evidence, analysis, run_summary, calls_errors = {'verified': False}, None, None, []\n",
         "    evidence, analysis, run_summary, calls_errors, recovered = {'verified': False}, None, None, [], None\n", 1),
        ("    gate_status = ('complete' if analysis and analysis['completeness']['withheld'] == 'complete'\n",
         "    gate_status = ('complete' if analysis and analysis['completeness']['withheld'] == 'complete' and not recovered\n", 1),
        ("            'technically_complete': (not lifecycle and evidence['verified'] and not calls_errors\n"
         "                                     and gate_status == 'complete'),",
         "            'technically_complete': (not lifecycle and evidence['verified'] and not calls_errors and not recovered\n"
         "                                     and run_summary['status'] == 'complete' and gate_status == 'complete'),", 1),
    ),
    'scripts/check_ws3_questionnaire_v1.py': (
        ("SUITES = {'probe_set_keys_scoring_and_analysis': 'tests.test_ws3_questionnaire_v1',",
         "SUITES = {'probe_set_keys_scoring_and_analysis': 'tests.test_ws3_questionnaire_draft',\n"
         "          'transition_records_and_fixtures': 'tests.test_transition_evidence_v1',", 1),
    ),
    'tests/test_ws3_questionnaire_v1_connected.py': (
        ("{'answered': 6054}", "{'answered': 5616}", 1),
        ("['families']['withheld']['original']['B0_normalized_history']['outcome_class']['correct']",
         "['families']['withheld']['raw_evidence']['progress_status']['correct']", 2),
        ("probes[c['probe_id']]['family'] == 'outcome_class'", "probes[c['probe_id']]['family'] == 'progress_status'", 1),
        ("probes[c['probe_id']]['condition'] == 'B0_normalized_history'",
         "probes[c['probe_id']]['condition'] == 'raw_evidence'", 1),
        ("            wrong = 'not_shown' if probes[flip['probe_id']]['key'] != 'not_shown' else 'dispatch_failed'",
         "            wrong = 'unknown' if probes[flip['probe_id']]['key'] == 'confirmed' else 'confirmed'", 1),
        ("            # 2. A forged request hash, an out-of-order call and broken token parity are rejected.\n",
         "            # 1b. Review of 95aef4f: a write interrupted after the last commit leaves recovered evidence. Its\n"
         "            # answers are still scored descriptively, but it is never technically complete or promotable.\n"
         "            interrupted = work / 'interrupted'\n"
         "            shutil.copytree(output, interrupted)\n"
         "            (interrupted / 'worker/run/manifest.json.tmp').write_bytes(b'{\"partial')\n"
         "            result = evaluate_output(interrupted, mode='rehearsal', rehearsal_seconds=REHEARSAL_SECONDS)\n"
         "            self.assertTrue(result['run_evidence']['recovered'])\n"
         "            self.assertEqual(result['run_evidence']['evidence_recovery']['ignored_temporary_files'],\n"
         "                             ['manifest.json.tmp'])\n"
         "            self.assertEqual((result['run']['status'], result['run']['stop_reason'], result['run']['calls_recorded']),\n"
         "                             ('incomplete', 'interrupted_evidence', 5616))\n"
         "            self.assertEqual(result['analysis']['families']['withheld']['raw_evidence']['progress_status']['correct'],\n"
         "                             baseline)\n"
         "            self.assertEqual((result['technically_complete'], result['gate_status'], result['gate']),\n"
         "                             (False, 'incomplete', {'questionnaire': 'incomplete'}))\n"
         "            # 2. A forged request hash, an out-of-order call and broken token parity are rejected.\n", 1),
        ("truncate(truncated / 'worker/run', 2664)", "truncate(truncated / 'worker/run', 2500)", 1),
        ("calls_recorded=2664", "calls_recorded=2500", 1),
        # WS3 policy: a missing regression-check answer withholds promotion; it makes the verdict incomplete only when
        # the missing answer is primary or in an over-claim gate. Either way, nothing may be promoted.
        # Monitor loss: the worker may finish gracefully (canceled) or be killed mid-write, in which case the committed
        # partial run is recovered (interrupted_evidence). Either way the evidence must verify.
        ("'cancel': ('canceled', True), 'monitor_exit': ('canceled', True),",
         "'cancel': ('canceled', True), 'monitor_exit': (('canceled', 'interrupted_evidence'), True),", 1),
        ("                    self.assertEqual(value['run']['stop_reason'], stop)",
         "                    self.assertIn(value['run']['stop_reason'], stop if isinstance(stop, tuple) else (stop,))", 1),
        ("        self.assertTrue(value['gate'][track].startswith('incomplete'))",
         "        self.assertNotEqual(value['gate'][track], 'candidate_clear_improvement_tool_assisted')", 1),
    ),
    'tests/test_ws3_questionnaire_v1_schedule.py': (
        ("report['completeness']['withheld_schedule']", "report['completeness']['withheld']", 3),
        ("{v.removesuffix('_tool_assisted') for v in report['verdicts'].values()}", STRIP.format(name="report['verdict']"), 2),
        ("{'baseline_meets_criterion'}", "{'reference_meets_criterion'}", 1),
        ("        # 0.5 s per call: withheld pass 1 completes, pass 2 is cut.\n"
         "        passes, admission, started, clock = simulate(0.5)",
         "        # 0.7 s per call: withheld pass 1 completes, pass 2 is cut (2,500 calls per pass).\n"
         "        passes, admission, started, clock = simulate(0.7)", 1),
    ),
    'tests/test_ws3_questionnaire_v1_snapshot.py': (),
    'tests/test_ws3_questionnaire_v1_diagnostics.py': (),
    'tests/ws3q_diagnostics_fixtures.py': (),
    'tests/ws3q_diagnostics_module_fixture.py': (),
}


def src(target):
    for new, old in TARGET_TO_SOURCE:
        target = target.replace(new, old)
    return target


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
    if target == 'scripts/build_ws3_questionnaire_v1_review.py':
        i = text.index(DOCS_START)
        j = text.index(')\n', i) + 2
        text = text[:i] + DOCS_NEW + text[j:]
    residue = text.replace('reports/evidence_comprehension_v3_results.md', '')  # cited on purpose: informed the design
    if 'evidence_comprehension_v3' in residue or 'ecv3-' in residue or 'ECV3_' in residue:
        raise ValueError(f'{target}: unexpected remaining v3 reference')
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
