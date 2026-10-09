"""Compose reports/feedback_action_v1/cpu_verification.json from the retained CPU check records (read-only inputs).

Inputs (each produced by its own script and retained under reports/):
  feedback_action_v1/runtime_install_check.json      scripts/check_feedback_action_v1_runtime.py
  feedback_action_v1/cpu_checks_<label>.json         scripts/run_feedback_action_v1_checks.py
  feedback_action_v1_review_check_r<N>.json          scripts/feedback_action_v1_package.py review-check
  feedback_action_v1_review_rehearsal_r<N>.json      scripts/feedback_action_v1_package.py review-rehearse
  research/feedback_action_v1/token_audit.json       research/feedback_action_v1/token_audit.py
Nothing here is GPU, model, provider-mount or approval evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    path = ROOT / name
    return json.loads(path.read_bytes()) if path.is_file() else None


def digest(name):
    path = ROOT / name
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--revision', type=int, default=1)
    args = parser.parse_args()
    install = read('reports/feedback_action_v1/runtime_install_check.json')
    audit = read('research/feedback_action_v1/token_audit.json')
    check = read(f'reports/feedback_action_v1_review_check_r{args.revision}.json')
    rehearsal = read(f'reports/feedback_action_v1_review_rehearsal_r{args.revision}.json')
    suites = {p.stem.removeprefix('cpu_checks_'): read(p.relative_to(ROOT).as_posix())
              for p in sorted((ROOT / 'reports/feedback_action_v1').glob('cpu_checks_*.json'))}
    lock = f'notebooks/feedback-action-v1-review-r{args.revision}/review-source-lock.json'
    record = {
        'schema': 'feedback_action_v1_cpu_verification_v1',
        'evidence_class': 'cpu_only_scripted_model_not_gpu_or_model_evidence',
        'review_revision': args.revision, 'review_lock_sha256': digest(lock),
        'gpu_used': False, 'model_calls': 0, 'provider_calls': 0, 'approvals_created': 0, 'reservations_created': 0,
        'runtime_install_check': install and {
            'passed': install['passed'], 'installation_seconds': install['installation_seconds'],
            'bundle_wheels_verified': install['installation']['bundle']['wheel_bytes_verified'],
            'model_versions': install['installation']['model']['versions'],
            'torch_cuda_build': install['installation']['model'].get('torch_cuda_build'),
            'game_versions': install['installation']['game']['versions'],
            'model_closure': install['installation']['model_closure'],
            'game_closure': install['installation']['game_closure'],
            'process_cleanup': install['process_cleanup'],
            'engine_tests': {k: install['engine_tests'][k] for k in ('modules', 'game_package_versions', 'exit_code',
                                                                     'summary')} if install.get('engine_tests') else None},
        'token_audit': audit and {
            'tokenizer_revision': audit['tokenizer_revision'], 'versions': audit['versions'],
            'forms': len(audit['forms']), 'max_prompt_tokens': audit['max_prompt_tokens'],
            'all_forms_within_limits': audit['all_forms_within_limits'],
            'longest_candidate_response_with_end_of_turn': {
                option: {fmt: v['with_end_of_turn'] for fmt, v in rows.items()}
                for option, rows in audit['completions']['candidate_by_free_text_option'].items()},
            'english_like_reference': {fmt: v['with_end_of_turn'] for fmt, v in
                                       audit['completions']['candidate_natural_ascii_reference'].items()},
            'grammar': audit['grammar'] and audit['grammar']['xgrammar_version']},
        'review_check': check and {k: check[k] for k in ('passed', 'refused_at_live_gate', 'nvidia_smi_called',
                                                          'temporary_files_left', 'refusal')},
        'review_rehearsal': rehearsal and {k: rehearsal[k] for k in ('passed', 'technically_complete', 'interpreters',
                                                                      'pinned_tokenizer', 'grammar_checked',
                                                                      'evaluation', 'extracted_source_left')},
        'suites': {label: value and {'executable': value['executable'], 'packages': value['packages'],
                                     'rehearsal_environment': value['rehearsal_environment'],
                                     'summary': value['summary'], 'passed': value['passed']}
                   for label, value in suites.items()},
    }
    record['all_passed'] = bool(install and install['passed'] and check and check['passed'] and rehearsal
                                and rehearsal['passed'] and suites and all(v and v['passed'] for v in suites.values()))
    out = ROOT / 'reports/feedback_action_v1/cpu_verification.json'
    out.write_text(json.dumps(record, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({'all_passed': record['all_passed'], 'suites': {k: v and v['summary'] for k, v in
                                                                     record['suites'].items()}}, indent=1))


if __name__ == '__main__':
    main()
