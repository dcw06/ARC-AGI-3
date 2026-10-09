"""Run scripted CPU rehearsals of the runtime2 package and evaluate each independently (CPU only; Linux).

Every rehearsal installs fixture wheels into a real temporary venv, starts the scripted stub server as an owned
process group, runs the complete frozen questionnaire schedule (5,852 calls) through the derived lifecycle, cancels,
cleans up and finalizes evidence; then scripts/evaluate_progress_subgoal_v1_runtime2.py evaluates the retained folder
with the harness-declared protocol. Receipts are labelled scripted_cpu_rehearsal: never GPU or model evidence, and
the scripted answers' labels are not results.

Usage: python scripts/rehearse_progress_subgoal_v1_runtime2.py --base DIR [--scenario NAME ...] [--out FILE]
"""
import argparse
import json
import os
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# scenario -> (fault, policy, expectation)
SCENARIOS = {
    'nominal_scripted': ('none', 'scripted', {'lifecycle_passed': True, 'run_status': 'complete',
                                              'technically_complete': True}),
    'nominal_oracle': ('none', 'oracle', {'lifecycle_passed': True, 'run_status': 'complete',
                                          'technically_complete': True}),
    'timeout_once': ('timeout_once', 'scripted', {'lifecycle_passed': True, 'run_status': 'complete',
                                                  'technically_complete': False}),
    'consecutive_timeouts': ('consecutive_timeouts', 'scripted', {'lifecycle_passed': False,
                                                                  'run_status': 'incomplete',
                                                                  'stop_reason': 'consecutive_timeouts',
                                                                  'technically_complete': False}),
    'not_idle': ('not_idle', 'scripted', {'lifecycle_passed': False, 'run_status': 'incomplete',
                                          'stop_reason': 'transport_failure', 'technically_complete': False}),
    'http_error': ('http_error', 'scripted', {'lifecycle_passed': False, 'run_status': 'incomplete',
                                              'stop_reason': 'transport_failure', 'technically_complete': False}),
    'token_mismatch': ('token_mismatch', 'scripted', {'lifecycle_passed': True, 'run_status': 'complete',
                                                      'technically_complete': False}),
    'admission_cutoff': ('admission_cutoff', 'scripted', {'run_status': 'incomplete',
                                                          'stop_reason': 'admission_cutoff',
                                                          'technically_complete': False}),
}


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=1) + '\n').encode()


def summarize(name, result, protocol, value, seconds):
    run = value.get('run') or {}
    stopped = (result.get('cleanup') or {}).get('server') or {}
    return {'scenario': name, 'seconds': round(seconds, 1), 'evidence_class': result.get('evidence_class'),
            'gpu_compatibility_evidence': result.get('gpu_compatibility_evidence'),
            'lifecycle_verdict_passed': result.get('passed'), 'failed_stage': result.get('failed_stage'),
            'error': (result.get('error') or '')[:300] or None, 'cleanup_verified': result.get('cleanup_verified'),
            'server_group_absent': stopped.get('groups_absent'),
            'lifecycle_deadline_met': (result.get('lifecycle_deadline') or {}).get('met'),
            'requests_issued': (result.get('ledger') or {}).get('issued'),
            'requests_by_kind': (result.get('ledger') or {}).get('by_kind'),
            'request_cap': protocol['limits']['maximum_model_requests'],
            'questionnaire_stage': result.get('questionnaire'),
            'evaluator': {'lifecycle_passed': value['lifecycle_passed'], 'lifecycle_errors': value['lifecycle_errors'][:5],
                          'manifest_verified': value['evidence']['manifest_verified'],
                          'call_errors': value['call_errors'][:5], 'run_status': run.get('status'),
                          'stop_reason': run.get('stop_reason'), 'calls_recorded': run.get('calls_recorded'),
                          'counts': run.get('counts'), 'gate_status': value['gate_status'], 'gate': value['gate'],
                          'technically_complete': value['technically_complete']},
            'note': 'scripted CPU stub with scripted answers: labels here are not results'}


def check(summary, expected):
    ev = summary['evaluator']
    observed = {'lifecycle_passed': ev['lifecycle_passed'], 'run_status': ev['run_status'],
                'stop_reason': ev['stop_reason'], 'technically_complete': ev['technically_complete']}
    return {k: observed[k] == v for k, v in expected.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--scenario', action='append', choices=sorted(SCENARIOS))
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if sys.platform != 'linux':
        raise SystemExit('Linux required for process-group and CPU fixture controls')
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    from research.progress_subgoal_v1_runtime2.rehearsal import scenario
    from scripts.evaluate_progress_subgoal_v1_runtime2 import evaluate_output
    args.base.mkdir(parents=True, exist_ok=True)
    rows = []
    for name in args.scenario or sorted(SCENARIOS):
        fault, policy, expected = SCENARIOS[name]
        folder = args.base / f'{name}-{int(time.time())}'
        begun = time.monotonic()
        result, protocol = scenario(ROOT, folder, fault, policy)
        seconds = time.monotonic() - begun
        # The harness-declared protocol and the independent evaluation are kept beside (never inside) the evidence.
        (folder / 'declared-protocol.json').write_bytes(encoded(protocol))
        value = evaluate_output(folder / 'evidence', mode='rehearsal', root=ROOT, protocol=protocol)
        (folder / 'evaluation.json').write_bytes(encoded(value))
        summary = summarize(name, result, protocol, value, seconds)
        summary['expected'] = expected
        summary['as_expected'] = check(summary, expected)
        summary['evidence_dir'] = str(folder / 'evidence')
        rows.append(summary)
        print(json.dumps({k: summary[k] for k in ('scenario', 'seconds', 'as_expected', 'failed_stage')}), flush=True)
    record = {'schema': 'progress_subgoal_v1_runtime2_cpu_rehearsals_v1', 'evidence_class': 'scripted_cpu_rehearsal',
              'gpu_compatibility_evidence': False, 'gpu_used': False, 'model_calls': 0, 'provider_calls': 0,
              'python': platform.python_version(), 'platform': platform.platform(), 'scenarios': rows,
              'all_as_expected': all(all(r['as_expected'].values()) for r in rows)}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes((json.dumps(record, sort_keys=True, indent=1) + '\n').encode())
    print(json.dumps({'all_as_expected': record['all_as_expected']}))
    return 0 if record['all_as_expected'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
