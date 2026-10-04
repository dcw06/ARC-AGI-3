# Derived from scripts/check_ws3_questionnaire_v1.py by scripts/derive_progress_subgoal_v1.py; edit the derivation, not this file.
"""Run every local suite for the questionnaire with retained diagnostics (no model calls, no GPU).

Each invocation writes a diagnostics record under reports/progress_subgoal_v1_diagnostics/
(named by run id) and, for a full run, the summary reports/progress_subgoal_v1_rehearsal_results.json.
The record keeps, per test and subtest: name, wall-clock and monotonic start/end, duration, outcome
and traceback, host load before and after, and a flag when the wall clock stepped relative to the
monotonic clock. Rehearsal-based tests also append each rehearsal's fault, evidence directory,
receipts and subprocess exit codes (see tests/test_progress_subgoal_v1_connected.run_fault).
Evidence directories are never deleted by the check.

--self-test runs a small suite with deliberate failures, errors and a failing subtest through the
same recorder and verifies that every one of them is retained.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
import traceback
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS = ROOT / 'reports/progress_subgoal_v1_diagnostics'
SUMMARY = ROOT / 'reports/progress_subgoal_v1_rehearsal_results.json'
SUITES = {'probe_set_keys_scoring_and_analysis': 'tests.test_progress_subgoal_v1',
          'frozen_decision_rules': 'tests.test_progress_subgoal_v1_rules',
          'runtime_derivation_adapters_and_frozen_set': 'tests.test_progress_subgoal_v1_runner',
          'transition_records_and_fixtures': 'tests.test_transition_evidence_v1',
          'schedule_admission_and_interrupted_gate': 'tests.test_progress_subgoal_v1_schedule',
          'transport_cancellation_and_cache_metrics': 'tests.test_evidence_comprehension_v1_transport',  # reused
          'diagnostics_recorder': 'tests.test_progress_subgoal_v1_diagnostics',
          'connected_path_rehearsals': 'tests.test_progress_subgoal_v1_connected',
          'packaging_derivation_and_inventory': 'tests.test_progress_subgoal_v1_packaging',
          'launcher_attachment_rejection': 'tests.test_progress_subgoal_v1_launch',
          'rehearsal_fault_placement': 'tests.test_progress_subgoal_v1_timing',
          'run_evidence_finalization': 'tests.test_progress_subgoal_v1_evidence'}
CLOCK_STEP_SECONDS = 2.0  # wall-clock minus monotonic drift above this, within one test, is flagged


def loadavg():
    try:
        return [round(v, 2) for v in os.getloadavg()]
    except OSError:
        return None


def host():
    info = {'hostname': platform.node(), 'platform': platform.platform(), 'python': sys.version.split()[0],
            'cpus': os.cpu_count(), 'loadavg': loadavg()}
    try:
        meminfo = Path('/proc/meminfo').read_text().splitlines()
        info['memory_kib'] = {line.split(':')[0]: int(line.split()[1]) for line in meminfo
                              if line.split(':')[0] in ('MemTotal', 'MemAvailable')}
    except OSError:
        info['memory_kib'] = None
    return info


def git_state():
    def git(*args):
        try:
            return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, timeout=60).stdout.strip()
        except Exception as exc:
            return 'unavailable: ' + type(exc).__name__
    status = git('status', '--porcelain')
    return {'commit': git('rev-parse', 'HEAD'),
            'dirty_paths': status.splitlines() if status and not status.startswith('unavailable') else status}


def _restore(name, previous):
    """Put an environment variable back as it was (None means it was unset)."""
    if previous is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous


class Recorder(unittest.TextTestResult):
    """Keeps a record for every test and subtest, whatever its outcome.

    Class, module and suite fixture errors (setUpClass, setUpModule, tearDownClass...) reach the result
    without startTest; they are kept as separate fixture records, never dropped or allowed to crash
    the recorder."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records, self.current = [], None
        self._outer_test = None  # the enclosing PSV1_CURRENT_TEST, restored after each test (nested recorders)

    @staticmethod
    def _clock():
        return {'wall': time.time(), 'monotonic': time.monotonic(), 'loadavg': loadavg()}

    def startTest(self, test):
        self.current = {'test': test.id(), 'start': self._clock(), 'outcome': None, 'subtests': [], 'detail': None}
        self._outer_test = os.environ.get('PSV1_CURRENT_TEST')
        os.environ['PSV1_CURRENT_TEST'] = test.id()
        super().startTest(test)

    def stopTest(self, test):
        end = self._clock()
        record = self.current
        record['end'] = end
        record['duration_seconds'] = round(end['monotonic'] - record['start']['monotonic'], 3)
        step = (end['wall'] - record['start']['wall']) - (end['monotonic'] - record['start']['monotonic'])
        record['wall_minus_monotonic_seconds'] = round(step, 3)
        record['wall_clock_step'] = abs(step) > CLOCK_STEP_SECONDS
        if record['outcome'] is None:
            record['outcome'] = 'failure' if any(s['outcome'] != 'success' for s in record['subtests']) else 'success'
        self.records.append(record)
        self.current = None
        _restore('PSV1_CURRENT_TEST', self._outer_test)
        super().stopTest(test)

    def _in_test(self, test):
        return self.current is not None and self.current['test'] == test.id()

    def _set(self, test, outcome, err=None):
        detail = ''.join(traceback.format_exception(*err))[-4000:] if err is not None else None
        if not self._in_test(test):
            # A fixture error outside any running test (for example setUpClass): its own record.
            self.records.append({'test': str(test), 'kind': 'fixture', 'outcome': outcome, 'detail': detail,
                                 'at': self._clock(), 'subtests': []})
            return
        self.current['outcome'] = outcome
        if detail is not None:
            self.current['detail'] = detail

    def addSuccess(self, test):
        super().addSuccess(test)
        self._set(test, 'success')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._set(test, 'failure', err)

    def addError(self, test, err):
        super().addError(test, err)
        self._set(test, 'error', err)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._set(test, 'skipped')
        if self._in_test(test):
            self.current['detail'] = reason

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if not self._in_test(test):
            self._set(subtest, 'error' if err is not None else 'success', err)
            return
        entry = {'subtest': subtest.id(), 'at_monotonic': time.monotonic(),
                 'outcome': 'success' if err is None else
                 ('failure' if issubclass(err[0], test.failureException) else 'error')}
        if err is not None:
            entry['detail'] = ''.join(traceback.format_exception(*err))[-4000:]
        self.current['subtests'].append(entry)


def run_suites(suites, run_id, directory=DIAGNOSTICS, label=None, runner_factory=None):
    """Run each requested suite, keeping its record even if the runner itself raises.

    Success requires every requested suite to have completed and passed; a suite whose runner raised is
    recorded as not completed, with the exception's traceback, and the remaining suites still run.
    KeyboardInterrupt and SystemExit are recorded and then re-raised."""
    runner_factory = runner_factory or (lambda: unittest.TextTestRunner(verbosity=0, resultclass=Recorder))
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    rehearsals = directory / f'{run_id}.rehearsals.jsonl'
    # A nested run (the diagnostics suite calls run_suites inside the full check) must not disturb the
    # enclosing run's logging: both variables are restored exactly, including when an exception escapes.
    previous_log, previous_test = os.environ.get('PSV1_DIAGNOSTICS_LOG'), os.environ.get('PSV1_CURRENT_TEST')
    os.environ['PSV1_DIAGNOSTICS_LOG'] = str(rehearsals)
    record = {'run_id': run_id, 'label': label, 'command': [sys.executable, *sys.argv], 'cwd': os.getcwd(),
              'git': git_state(), 'host_at_start': host(),
              'started': {'wall': time.time(), 'monotonic': time.monotonic()}, 'suites': {}}
    record['requested_suites'] = list(suites)
    try:
        for suite_label, name in suites.items():
            begun = time.monotonic()
            try:
                outcome = runner_factory().run(unittest.defaultTestLoader.loadTestsFromName(name))
            except BaseException as exc:
                record['suites'][suite_label] = {
                    'module': name, 'completed': False, 'passed': False, 'seconds': round(time.monotonic() - begun, 1),
                    'runner_exception': ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-6000:]}
                if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                    raise
                continue
            record['suites'][suite_label] = {
                'module': name, 'completed': True, 'tests_run': outcome.testsRun, 'failures': len(outcome.failures),
                'errors': len(outcome.errors), 'passed': outcome.wasSuccessful(),
                'seconds': round(time.monotonic() - begun, 1), 'tests': getattr(outcome, 'records', [])}
    finally:
        _restore('PSV1_DIAGNOSTICS_LOG', previous_log)
        _restore('PSV1_CURRENT_TEST', previous_test)
        record['ended'] = {'wall': time.time(), 'monotonic': time.monotonic()}
        record['host_at_end'] = host()
        record['rehearsals'] = ([json.loads(line) for line in rehearsals.read_text().splitlines() if line.strip()]
                                if rehearsals.exists() else [])
        record['all_passed'] = (list(record['suites']) == record['requested_suites'] and bool(record['suites'])
                                and all(s['completed'] and s['passed'] for s in record['suites'].values()))
        (directory / f'{run_id}.json').write_text(json.dumps(record, indent=1) + '\n')
    return record


# ------------------------------------------------------------------ self-test with deliberate failures

class _DeliberateFailures(unittest.TestCase):
    def test_a_passes(self):
        self.assertTrue(True)

    def test_b_fails(self):
        self.assertEqual(1, 2, 'deliberate assertion failure')

    def test_c_errors(self):
        raise RuntimeError('deliberate error')

    def test_d_failing_subtest(self):
        for n in (1, 2):
            with self.subTest(n=n):
                self.assertNotEqual(n, 2, 'deliberate subtest failure')

    def test_e_records_a_rehearsal(self):
        from tests.test_progress_subgoal_v1_connected import record_rehearsal
        record_rehearsal('self_test_fault', 480, Path(tempfile.gettempdir()) / 'self-test-evidence',
                         {'study_status': 'failed', 'elapsed_seconds': 1.0}, None, None)
        self.fail('deliberate failure after recording a rehearsal')


def self_test(directory):
    record = run_suites({'deliberate_failures': __name__ + '._DeliberateFailures',
                         'fixture_error_after_a_passing_suite': 'tests.psv1_diagnostics_fixtures.SetUpClassFails'},
                        'self-test', directory, label='recorder self-test with deliberate failures')
    fixture = [t for t in record['suites']['fixture_error_after_a_passing_suite'].get('tests', [])
               if t.get('kind') == 'fixture']
    tests = {t['test'].rsplit('.', 1)[1]: t for t in record['suites']['deliberate_failures']['tests']}
    checks = {
        'suite_marked_failed': record['all_passed'] is False,
        'all_five_tests_recorded': set(tests) == {'test_a_passes', 'test_b_fails', 'test_c_errors',
                                                  'test_d_failing_subtest', 'test_e_records_a_rehearsal'},
        'pass_recorded': tests.get('test_a_passes', {}).get('outcome') == 'success',
        'failure_traceback_retained': tests.get('test_b_fails', {}).get('outcome') == 'failure'
        and 'deliberate assertion failure' in (tests['test_b_fails'].get('detail') or ''),
        'error_traceback_retained': tests.get('test_c_errors', {}).get('outcome') == 'error'
        and 'deliberate error' in (tests['test_c_errors'].get('detail') or ''),
        'subtest_failure_retained': tests.get('test_d_failing_subtest', {}).get('outcome') == 'failure'
        and [s['outcome'] for s in tests['test_d_failing_subtest']['subtests']] == ['success', 'failure']
        and 'deliberate subtest failure' in (tests['test_d_failing_subtest']['subtests'][1].get('detail') or ''),
        'durations_and_clocks_recorded': all(isinstance(t['duration_seconds'], float) and 'wall_clock_step' in t
                                             for t in tests.values()),
        'rehearsal_linked_to_test': any(r.get('fault') == 'self_test_fault'
                                        and str(r.get('test')).endswith('test_e_records_a_rehearsal')
                                        for r in record['rehearsals']),
        'host_and_git_recorded': bool(record['host_at_start'].get('cpus')) and 'commit' in record['git'],
        'setupclass_error_retained': len(fixture) == 1 and 'deliberate setUpClass failure' in (fixture[0]['detail'] or ''),
        'every_requested_suite_recorded': list(record['suites']) == record['requested_suites'],
    }
    return {'self_test_passed': all(checks.values()), 'checks': checks,
            'record': 'reports/progress_subgoal_v1_diagnostics/self-test.json'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', default=time.strftime('run-%Y%m%dT%H%M%SZ', time.gmtime()))
    parser.add_argument('--label')
    parser.add_argument('--suites', nargs='*', choices=list(SUITES),
                        help='a subset; the summary report is only rewritten for a full run')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        result = self_test(DIAGNOSTICS)
        print(json.dumps(result, indent=1))
        raise SystemExit(0 if result['self_test_passed'] else 1)
    chosen = {k: SUITES[k] for k in (args.suites or SUITES)}
    record = run_suites(chosen, args.run_id, label=args.label)
    summary = {'scope': 'local CPU rehearsals only; CPU fake of the model server with scripted answers; '
                        'no model calls or GPU runs',
               'run_id': args.run_id,
               'diagnostics': f'reports/progress_subgoal_v1_diagnostics/{args.run_id}.json',
               'requested_suites': record['requested_suites'],
               'suites': {k: {x: v.get(x) for x in ('module', 'completed', 'tests_run', 'failures', 'errors', 'passed',
                                                    'seconds')} for k, v in record['suites'].items()},
               'all_passed': record['all_passed'], 'model_calls': 0, 'gpu_runs': 0,
               'token_audit': 'reports/progress_subgoal_v1_token_audit.json'}
    if not args.suites:
        SUMMARY.write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=1))
    if not record['all_passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
