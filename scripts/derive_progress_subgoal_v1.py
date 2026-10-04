"""Derive the progress_subgoal_v1 review packaging and its regressions from the reviewed WS3 questionnaire v1 files.

Same pattern as scripts/derive_ws3_questionnaire_v1.py: each target is its WS3 source with WS3's banner line removed,
the global renames of research/progress_subgoal_v1/derive.py (plus the diagnostics-fixture rename), and that file's
own substitutions, each required to match an exact number of times. WS3 files are read, never edited; their SHA-256
at derivation time is recorded (SOURCE_SHA256) so later changes are detected. The runtime itself is derived by
research/progress_subgoal_v1/derive.py; `stale()` here covers both.

Targets (new, track-named files): the review-package builder, the package/approval/launch script, the notebook
review, the local check, and the snapshot, schedule, diagnostics and connected regressions with the diagnostics
fixtures. The question-set builder (scripts/build_progress_subgoal_v1.py) is hand-written: it needs the seed.

Usage: python scripts/derive_progress_subgoal_v1.py [--check]
"""
import argparse
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.progress_subgoal_v1 import derive as RUNTIME  # noqa: E402

BANNER = '# Derived from {source} by scripts/derive_progress_subgoal_v1.py; edit the derivation, not this file.\n'
GLOBAL = RUNTIME.GLOBAL + (('ws3q_diagnostics', 'psv1_diagnostics'),)
ARMS = "('raw_plus_computed_record', 'raw_plus_computed_record_plus_safeguard')"

DOCS_START = 'REVIEW_DOCUMENTS = ('
DOCS_NEW = """REVIEW_DOCUMENTS = ('reports/progress_subgoal_v1_protocol_v2.md', 'reports/progress_subgoal_v1_protocol_v1.md',
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
                    'tests/test_progress_subgoal_v1_launch.py', 'tests/test_progress_subgoal_v1_timing.py',
                    'tests/psv1_diagnostics_fixtures.py',
                    'tests/psv1_diagnostics_module_fixture.py')
"""
SUITES_OLD = """SUITES = {'probe_set_keys_scoring_and_analysis': 'tests.test_ws3_questionnaire_draft',
          'transition_records_and_fixtures': 'tests.test_transition_evidence_v1',
          'schedule_admission_and_interrupted_gate': 'tests.test_progress_subgoal_v1_schedule',
          'transport_cancellation_and_cache_metrics': 'tests.test_evidence_comprehension_v1_transport',  # reused
          'diagnostics_recorder': 'tests.test_progress_subgoal_v1_diagnostics',
          'connected_path_rehearsals': 'tests.test_progress_subgoal_v1_connected',
          'runtime_derivation_and_inventory': 'tests.test_progress_subgoal_v1_derivation'}"""
SUITES_NEW = """SUITES = {'probe_set_keys_scoring_and_analysis': 'tests.test_progress_subgoal_v1',
          'frozen_decision_rules': 'tests.test_progress_subgoal_v1_rules',
          'runtime_derivation_adapters_and_frozen_set': 'tests.test_progress_subgoal_v1_runner',
          'transition_records_and_fixtures': 'tests.test_transition_evidence_v1',
          'schedule_admission_and_interrupted_gate': 'tests.test_progress_subgoal_v1_schedule',
          'transport_cancellation_and_cache_metrics': 'tests.test_evidence_comprehension_v1_transport',  # reused
          'diagnostics_recorder': 'tests.test_progress_subgoal_v1_diagnostics',
          'connected_path_rehearsals': 'tests.test_progress_subgoal_v1_connected',
          'packaging_derivation_and_inventory': 'tests.test_progress_subgoal_v1_packaging',
          'launcher_attachment_rejection': 'tests.test_progress_subgoal_v1_launch',
          'rehearsal_fault_placement': 'tests.test_progress_subgoal_v1_timing'}"""

# Review of bc0c1b9 [P1]: the launcher must reject invalid provider attachments even with HTTP 200 (the failure that
# affected Track 3 R6; rule adapted from Track 3's validate_response in 7063a11). Every invalid* field is retained,
# including unknown ones and model sources; any present field that is non-empty or not a list fails the launch; the
# attempt stays consumed (never retried) and the CLI exits non-zero because the receipt carries an error.
ATTACHMENT_HELPER_ANCHOR = "def launch(root, backend):\n"
ATTACHMENT_HELPER = '''KNOWN_ATTACHMENT_ERRORS = ('invalid_dataset_sources', 'invalid_model_sources', 'invalid_competition_sources',
                           'invalid_kernel_sources', 'invalidDatasetSources', 'invalidModelSources',
                           'invalidCompetitionSources', 'invalidKernelSources')


def attachment_errors(response):
    """{name: value} for every invalid* field the provider response carries (known names and any other key whose name
    starts with 'invalid'), and the sorted names that reject the launch (present and non-empty, or not a list)."""
    if isinstance(response, dict):
        fields, read = set(response), response.get
    else:
        fields, read = set(getattr(response, '__dict__', {})) | set(dir(response)), lambda n: getattr(response, n, None)
    names = {n for n in fields if isinstance(n, str) and n.lstrip('_').lower().startswith('invalid')}
    names = {n.lstrip('_') for n in names} | set(KNOWN_ATTACHMENT_ERRORS)
    present = {}
    for name in sorted(names):
        value = read(name)
        if value is None and not isinstance(response, dict):
            value = getattr(response, '_' + name, None)
        if value is not None and not callable(value):
            present[name] = value if isinstance(value, (list, str, int, float, bool, dict)) else repr(value)
    rejected = sorted(n for n, v in present.items() if not isinstance(v, list) or v)
    return present, rejected


'''
LAUNCH_OLD = """        response = backend.push(path(root, PACKAGE))
        receipt.update(status='provider_response_received', url=response.url,
                       provider_version=response.version_number, error=response.error)
        for name in ('invalid_dataset_sources', 'invalid_competition_sources',
                     'invalid_kernel_sources'):
            receipt[name] = getattr(response, name, None)
"""
LAUNCH_NEW = """        response = backend.push(path(root, PACKAGE))
        read = response.get if isinstance(response, dict) else lambda n: getattr(response, n, None)
        receipt.update(status='provider_response_received', url=read('url'),
                       provider_version=read('version_number'), error=read('error'))
        present, rejected = attachment_errors(response)
        receipt['provider_attachment_errors'] = present  # every invalid* field, kept as returned
        if rejected:  # HTTP 200 is not acceptance: a rejected attachment fails this (consumed) attempt
            receipt.update(status='provider_rejected_attachments_no_retry',
                           error='provider rejected attachments: ' + ', '.join(rejected))
        elif not receipt['error'] and not receipt['url']:
            receipt.update(status='provider_result_requires_reconciliation_no_retry',
                           error='provider response without a kernel url')
"""

SIDECAR_HELPER = '''def _sidecar(name):
    """This protocol's approval, reservation, review and launch records, and its own notebook folders: never runtime
    dependencies, whether or not they are tracked. Without this, committing a review lock added it to its own
    inventory. (Other stacks' files reached through reused modules, e.g. the phase4 authority's review lock, are
    unchanged, so shared files stay identical to what earlier launches packaged.)"""
    import importlib.util  # by file path: the builder also runs as a plain script (repository not on sys.path)
    spec = importlib.util.spec_from_file_location('_psv1_authority', ROOT / 'research/progress_subgoal_v1/authority.py')
    authority = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(authority)
    records = {authority.REVIEW, authority.SOURCE, authority.COMPUTE, authority.EXECUTION, authority.RESERVATION,
               'reports/progress_subgoal_v1_launch_claim.json', 'reports/progress_subgoal_v1_launch.json',
               'reports/progress_subgoal_v1_prelaunch.json', 'reports/progress_subgoal_v1_package_review.json'}
    return name in records or name.startswith('notebooks/progress-subgoal-v1-')


'''

TARGETS = {
    'scripts/build_progress_subgoal_v1_review.py': ('scripts/build_ws3_questionnaire_v1_review.py', (
        # Review revision r3; r1 and r2 are kept as history (r1's lock pulled itself into the inventory once
        # committed, review of bc0c1b9; r2 bound the fixed slow-fault latencies replaced by derived ones).
        ("REVISION = 'r2'", "REVISION = 'r3'", 1),
        ("PACKAGES = ('agent', 'certification', 'evaluation', 'research', 'scripts')",
         "PACKAGES = ('agent', 'certification', 'evaluation', 'research', 'scripts')\n"
         "# Build- and review-time modules of this package: hash-bound as review documents, never in the runtime inventory.\n"
         "BUILD_ONLY = ('rehearse.py', 'derive.py', 'token_audit.py', 'rules.py')", 1),
        ("                                        if p.relative_to(ROOT).as_posix() in _tracked())",
         "                                        if p.relative_to(ROOT).as_posix() in _tracked() and p.name not in BUILD_ONLY)", 1),
        # Review of bc0c1b9 [P1]: once the review lock is committed it is a tracked JSON path named in authority.py,
        # so the scanner pulled the lock into its own inventory (277 files instead of the frozen 276). Approval and
        # review sidecars are never runtime dependencies: exclude them explicitly.
        ("            elif text.endswith(('.py', '.json', '.yaml')) and '/' in text and text in _tracked():",
         "            elif (text.endswith(('.py', '.json', '.yaml')) and '/' in text and text in _tracked()\n"
         "                  and not _sidecar(text)):", 1),
        ("def _module_file(name):", SIDECAR_HELPER + "def _module_file(name):", 1),
        ("'compute authorization and one fresh reservation. 3,116 frozen questions in '\n"
         "                                     '5,616 scheduled calls and one canary; no game actions.'",
         "'compute authorization and one fresh reservation. 3,062 frozen questions in '\n"
         "                                     '5,852 scheduled calls and one canary; no game actions.'", 1),
        ("'ARC3 WS3 Questionnaire V1 Review '", "'ARC3 Progress Subgoal V1 Review '", 1),
    )),
    'scripts/progress_subgoal_v1_package.py': ('scripts/ws3_questionnaire_v1_package.py', (
        ("'A retrospective transition questionnaire: 3,116 frozen questions in 5,616 scheduled calls (the withheld partition '",
         "'A retrospective questionnaire on change, progress and subgoal completion: 3,062 frozen questions in 5,852 '\n"
         "        'scheduled calls (the evaluation partition '", 1),
        (ATTACHMENT_HELPER_ANCHOR, ATTACHMENT_HELPER + ATTACHMENT_HELPER_ANCHOR, 1),
        (LAUNCH_OLD, LAUNCH_NEW, 1),
    )),
    'scripts/review_progress_subgoal_v1_notebook.py': ('scripts/review_ws3_questionnaire_v1_notebook.py', ()),
    'scripts/check_progress_subgoal_v1.py': ('scripts/check_ws3_questionnaire_v1.py', (
        (SUITES_OLD, SUITES_NEW, 1),
    )),
    'tests/test_progress_subgoal_v1_snapshot.py': ('tests/test_ws3_questionnaire_v1_snapshot.py', ()),
    'tests/test_progress_subgoal_v1_diagnostics.py': ('tests/test_ws3_questionnaire_v1_diagnostics.py', ()),
    'tests/psv1_diagnostics_fixtures.py': ('tests/ws3q_diagnostics_fixtures.py', ()),
    'tests/psv1_diagnostics_module_fixture.py': ('tests/ws3q_diagnostics_module_fixture.py', ()),
    'tests/test_progress_subgoal_v1_schedule.py': ('tests/test_ws3_questionnaire_v1_schedule.py', (
        # this evaluator takes the decision partition explicitly and reports per-arm readiness, not one verdict
        ("analyze(PROBES, {k: v for k, v in passes.items()})", "analyze(PROBES, dict(passes), GATE_PARTITION)", 1),
        ("analyze(PROBES, passes)", "analyze(PROBES, passes, GATE_PARTITION)", 2),
        ("report['completeness']['withheld']", "report['completeness']['primary']", 3),
        ("        self.assertEqual({report['verdict'].removesuffix('_tool_assisted')}, {'incomplete'})",
         "        self.assertEqual({r['status'] for r in report['readiness'].values()}, {'incomplete'})", 1),
        ("        self.assertEqual({report['verdict'].removesuffix('_tool_assisted')},\n"
         "                         {'reference_meets_criterion'})",
         "        self.assertEqual({r['status'] for r in report['readiness'].values()},\n"
         "                         {'eligible_for_memory_or_supervision'})", 1),
        ("pass 2 is cut (2,500 calls per pass).", "pass 2 is cut (2,790 calls per pass).", 1),
    )),
    'tests/test_progress_subgoal_v1_connected.py': ('tests/test_ws3_questionnaire_v1_connected.py', (
        ("{'answered': 5616}", "{'answered': 5852}", 1),
        ("['families']['withheld']['raw_evidence']['progress_status']['correct']",
         "['families']['raw_plus_computed_record']['progress_status']['correct']", 3),
        ("probes[c['probe_id']]['condition'] == 'raw_evidence'",
         "probes[c['probe_id']]['condition'] == 'raw_plus_computed_record'", 1),
        ("('incomplete', 'interrupted_evidence', 5616))", "('incomplete', 'interrupted_evidence', 5852))", 1),
        ("(False, 'incomplete', {'questionnaire': 'incomplete'}))",
         f"(False, 'incomplete', {{arm: 'incomplete' for arm in {ARMS}}}))", 1),
        ("truncate(truncated / 'worker/run', 2500)  # keep withheld pass 1 only",
         "truncate(truncated / 'worker/run', 2790)  # keep withheld pass 1 only", 1),
        ("calls_recorded=2500", "calls_recorded=2790", 1),
        ("{v.removesuffix('_tool_assisted') for v in result['gate'].values()}", "set(result['gate'].values())", 1),
        ("{v.removesuffix('_tool_assisted') for v in value['gate'].values()}", "set(value['gate'].values())", 1),
        ("        track = next(p['track'] for p in json.loads(Path('research/progress_subgoal_v1/probes.json').read_bytes())\n"
         "                      ['probes'] if p['probe_id'] == timed['probe_id'])\n"
         "        self.assertNotEqual(value['gate'][track], 'candidate_clear_improvement_tool_assisted')",
         "        arm = next(p['condition'] for p in json.loads(Path('research/progress_subgoal_v1/probes.json').read_bytes())\n"
         "                   ['probes'] if p['probe_id'] == timed['probe_id'])\n"
         "        self.assertNotEqual(value['gate'][arm], 'eligible_for_memory_or_supervision')", 1),
    )),
}
# SHA-256 of each WS3 source when this derivation was written (branch ws3-action-effects at c8f4c42).
SOURCE_SHA256 = {
    'scripts/build_ws3_questionnaire_v1_review.py': '1b4554863cc48242139b52b8b4050b35827ac8a06937abf8cd8326a922dd674a',
    'scripts/ws3_questionnaire_v1_package.py': 'caeed9eafc3d876afe61f1a5b2d7f14f1baa60261281aa17e6c2327abe4ddfe0',
    'scripts/review_ws3_questionnaire_v1_notebook.py': '62ee7bedb024cd961dcfe01e781109bb9e45f09ff59315e5f0903d9b35543ddf',
    'scripts/check_ws3_questionnaire_v1.py': '0d7d1deb322c7cdc036192ae274afaadf683152a64334708a71cc5cdff41c524',
    'tests/test_ws3_questionnaire_v1_snapshot.py': '4e299926e660dae515890bb4629b9182b408be80c5af4ec70d2c5290048043f7',
    'tests/test_ws3_questionnaire_v1_diagnostics.py': '99a7f8c5b1e2a9e8e8f2cfe8814c1ccd5d21c16da6cbf63e99dc1dcfff0df588',
    'tests/ws3q_diagnostics_fixtures.py': '70071294237822b47b77ab011f97711adb8799e649d623b1062a91b617b8f6ee',
    'tests/ws3q_diagnostics_module_fixture.py': '3b6eda1af799e91dc1b6d050ae6a6f6220b039a886c6062df5f724f1c5863dd6',
    'tests/test_ws3_questionnaire_v1_schedule.py': 'b5761557769f31ad83a16c66d564edb406dce643cd5ad888323e9c45ea7ed189',
    'tests/test_ws3_questionnaire_v1_connected.py': '11dcf6c119b5cf92a8dcb62e1c4a7fb6a09c70027d47670873404fe1cda158ae',
}


def derive_one(target):
    source, subs = TARGETS[target]
    lines = (ROOT / source).read_text(encoding='utf-8').splitlines(keepends=True)
    if lines and lines[0].startswith('# Derived from '):
        lines = lines[1:]
    text = ''.join(lines)
    for old, new in GLOBAL:
        text = text.replace(old, new)
    for old, new, count in subs:
        found = text.count(old)
        if found != count:
            raise ValueError(f'{target}: expected {count} of {old[:70]!r}, found {found}')
        text = text.replace(old, new)
    if target == 'scripts/build_progress_subgoal_v1_review.py':
        i = text.index(DOCS_START)
        j = text.index(')\n', i) + 2
        text = text[:i] + DOCS_NEW + text[j:]
    for residue in ('ws3_questionnaire_v1', 'ws3-questionnaire-v1', 'WS3Q_', 'ws3q', 'ws3_questionnaire_draft',
                    '_tool_assisted', "'track'"):
        if residue in text:
            raise ValueError(f'{target}: unexpected remaining reference {residue!r}')
    return BANNER.format(source=source) + text


def derive():
    return {target: derive_one(target) for target in TARGETS}


def source_hashes():
    return {source: hashlib.sha256((ROOT / source).read_bytes()).hexdigest() for source, _ in TARGETS.values()}


def stale():
    """Packaging and runtime targets that differ from their derivations."""
    return [t for t, text in derive().items()
            if not (ROOT / t).is_file() or (ROOT / t).read_text(encoding='utf-8') != text] + RUNTIME.stale()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    if parser.parse_args().check:
        drift = stale()
        if drift:
            raise SystemExit('derived files differ from the derivation: ' + ', '.join(drift))
        print(f'{len(TARGETS)} packaging and {len(RUNTIME.DERIVED)} runtime derived files match the derivation')
        sys.exit(0)
    for target, text in derive().items():
        (ROOT / target).write_text(text, encoding='utf-8', newline='\n')
    print(f'wrote {len(TARGETS)} derived files')
    print(source_hashes())
