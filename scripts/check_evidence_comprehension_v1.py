"""Run every local suite for the questionnaire with retained diagnostics (no model calls, no GPU).

Each invocation writes a diagnostics record under reports/evidence_comprehension_v1_diagnostics/
(named by run id) and, for a full run, the summary reports/evidence_comprehension_v1_rehearsal_results.json.
The record keeps, per test and subtest: name, wall-clock and monotonic start/end, duration, outcome
and traceback, host load before and after, and a flag when the wall clock stepped relative to the
monotonic clock. Rehearsal-based tests also append each rehearsal's fault, evidence directory,
receipts and subprocess exit codes (see tests/test_evidence_comprehension_v1_connected.run_fault).
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
DIAGNOSTICS = ROOT / 'reports/evidence_comprehension_v1_diagnostics'
SUMMARY = ROOT / 'reports/evidence_comprehension_v1_rehearsal_results.json'
SUITES = {'probe_set_keys_scoring_and_analysis': 'tests.test_evidence_comprehension_v1',
          'schedule_admission_and_interrupted_gate': 'tests.test_evidence_comprehension_v1_schedule',
          'transport_cancellation_and_cache_metrics': 'tests.test_evidence_comprehension_v1_transport',
          'connected_path_rehearsals': 'tests.test_evidence_comprehension_v1_connected'}
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


class Recorder(unittest.TextTestResult):
    """Keeps a record for every test and subtest, whatever its outcome."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records, self.current = [], None

    @staticmethod
    def _clock():
        return {'wall': time.time(), 'monotonic': time.monotonic(), 'loadavg': loadavg()}

    def startTest(self, test):
        self.current = {'test': test.id(), 'start': self._clock(), 'outcome': None, 'subtests': [], 'detail': None}
        os.environ['ECV_CURRENT_TEST'] = test.id()
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
        os.environ.pop('ECV_CURRENT_TEST', None)
        super().stopTest(test)

    def _set(self, outcome, err=None):
        self.current['outcome'] = outcome
        if err is not None:
            self.current['detail'] = ''.join(traceback.format_exception(*err))[-4000:]

    def addSuccess(self, test):
        super().addSuccess(test)
        self._set('success')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._set('failure', err)

    def addError(self, test, err):
        super().addError(test, err)
        self._set('error', err)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._set('skipped')
        self.current['detail'] = reason

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        entry = {'subtest': subtest.id(), 'at_monotonic': time.monotonic(),
                 'outcome': 'success' if err is None else
                 ('failure' if issubclass(err[0], test.failureException) else 'error')}
        if err is not None:
            entry['detail'] = ''.join(traceback.format_exception(*err))[-4000:]
        self.current['subtests'].append(entry)


def run_suites(suites, run_id, directory=DIAGNOSTICS, label=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    rehearsals = directory / f'{run_id}.rehearsals.jsonl'
    os.environ['ECV_DIAGNOSTICS_LOG'] = str(rehearsals)
    record = {'run_id': run_id, 'label': label, 'command': [sys.executable, *sys.argv], 'cwd': os.getcwd(),
              'git': git_state(), 'host_at_start': host(),
              'started': {'wall': time.time(), 'monotonic': time.monotonic()}, 'suites': {}}
    try:
        for suite_label, name in suites.items():
            begun = time.monotonic()
            runner = unittest.TextTestRunner(verbosity=0, resultclass=Recorder)
            outcome = runner.run(unittest.defaultTestLoader.loadTestsFromName(name))
            record['suites'][suite_label] = {
                'module': name, 'tests_run': outcome.testsRun, 'failures': len(outcome.failures),
                'errors': len(outcome.errors), 'passed': outcome.wasSuccessful(),
                'seconds': round(time.monotonic() - begun, 1), 'tests': outcome.records}
    finally:
        os.environ.pop('ECV_DIAGNOSTICS_LOG', None)
        record['ended'] = {'wall': time.time(), 'monotonic': time.monotonic()}
        record['host_at_end'] = host()
        record['rehearsals'] = ([json.loads(line) for line in rehearsals.read_text().splitlines() if line.strip()]
                                if rehearsals.exists() else [])
        record['all_passed'] = bool(record['suites']) and all(s['passed'] for s in record['suites'].values())
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
        from tests.test_evidence_comprehension_v1_connected import record_rehearsal
        record_rehearsal('self_test_fault', 480, Path(tempfile.gettempdir()) / 'self-test-evidence',
                         {'study_status': 'failed', 'elapsed_seconds': 1.0}, None, None)
        self.fail('deliberate failure after recording a rehearsal')


def self_test(directory):
    record = run_suites({'deliberate_failures': __name__ + '._DeliberateFailures'}, 'self-test', directory,
                        label='recorder self-test with deliberate failures')
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
    }
    return {'self_test_passed': all(checks.values()), 'checks': checks,
            'record': 'reports/evidence_comprehension_v1_diagnostics/self-test.json'}


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
               'diagnostics': f'reports/evidence_comprehension_v1_diagnostics/{args.run_id}.json',
               'suites': {k: {x: v[x] for x in ('module', 'tests_run', 'failures', 'errors', 'passed', 'seconds')}
                          for k, v in record['suites'].items()},
               'all_passed': record['all_passed'], 'model_calls': 0, 'gpu_runs': 0,
               'token_audit': 'reports/evidence_comprehension_v1_token_audit.json'}
    if not args.suites:
        SUMMARY.write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=1))
    if not record['all_passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
