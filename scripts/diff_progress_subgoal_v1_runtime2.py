"""Runtime-only source diff: the superseded package (review r4, old runtime) against the runtime2 successor.

Read-only and CPU only. Writes reports/progress_subgoal_v1_runtime2_source_diff.json with:
- the file-level comparison of review r4's bound sources with the successor's runtime payload (unchanged, removed,
  added, and changed-in-place, which must be empty);
- semantic checks that nothing scientific changed: the exact call order, every one of the 5,852 scheduled requests
  (and the HTTP body each runtime sends), arms and system prompts, answer schemas, sampling settings, the admission
  and stop-rule constants, the frozen package limits, the served model and tokenizer identity, and the vLLM argv;
- the runtime configuration that did change, old against new.

Usage: python scripts/diff_progress_subgoal_v1_runtime2.py
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
R4 = 'notebooks/progress-subgoal-v1-review-r4'
OUT = 'reports/progress_subgoal_v1_runtime2_source_diff.json'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def classify(name):
    if name.startswith('research/progress_subgoal_v1/'):
        return 'old_runtime_modules_of_this_package_and_offline_scorer'
    if name.startswith(('research/transition_evidence_v1/', 'research/evidence_comprehension_v1/',
                        'research/evidence_comprehension_v2/', 'research/action_effect_history_v1/',
                        'research/action_effect_v1/')):
        return 'reused_modules_no_longer_needed_at_runtime'
    if name.startswith('config/'):
        return 'config_closure_of_old_runtime'
    if name.startswith(('certification/', 'evaluation/', 'agent/', 'scripts/')):
        return 'old_runtime_closure_certification_evaluation_agent_scripts'
    return 'other_scopes_records_and_old_runtime_data'


def file_diff(root):
    from research.progress_subgoal_v1_runtime2.notebook import source_names
    old = json.loads((root / R4 / 'review-source-lock.json').read_bytes())['bindings']
    new = {n: sha((root / n).read_bytes()) for n in source_names(root)}
    unchanged = sorted(n for n in old if n in new and old[n] == new[n])
    changed = sorted(n for n in old if n in new and old[n] != new[n])
    removed = sorted(n for n in old if n not in new)
    added = sorted(n for n in new if n not in old)
    groups = {}
    for name in removed:
        groups.setdefault(classify(name), []).append(name)
    return {'old_review_lock': R4 + '/review-source-lock.json',
            'old_review_lock_sha256': sha((root / R4 / 'review-source-lock.json').read_bytes()),
            'old_bound_files': len(old), 'successor_payload_files': len(new),
            'unchanged': unchanged, 'changed_in_place': changed, 'added': added,
            'removed_by_group': {k: v for k, v in sorted(groups.items())},
            'removed_count': len(removed)}


def semantic(root):
    from research.action_effect_history_v1.service import request_hash
    from research.progress_subgoal_v1 import probes as P, questions as Q, schedule as S
    from research.progress_subgoal_v1_runtime2 import questionnaire as QN
    from research.progress_subgoal_v1_runtime2.binding import load_protocol
    protocol = load_protocol(root)
    # The old runner's order and requests (research/progress_subgoal_v1/runner.py) from the same frozen file.
    frozen_old, digest_old = P.load_frozen(P.FROZEN_PATH)
    contexts = {c['context_id']: c for c in frozen_old['contexts']}
    probes = {p['probe_id']: p for p in frozen_old['probes']}
    old_order = S.call_order(frozen_old)
    old_requests = [P.build_request(contexts[probes[i]['context_id']], probes[i]) for _, _, i in old_order]
    frozen_new, digest_new, rows = QN.scheduled(root)
    new_order = [(phase, pass_id, probe_id) for _, phase, pass_id, probe_id, _ in rows]
    new_requests = [row[4] for row in rows]
    # HTTP bodies: the old transport sent json.dumps(request, separators=(',', ':')); the verified client sends
    # json.dumps(body). Only whitespace may differ; the decoded JSON must be identical.
    old_bodies = [json.dumps(r, separators=(',', ':')).encode() for r in old_requests]
    new_bodies = [json.dumps(r).encode() for r in new_requests]
    bodies_equal = all(json.loads(a) == json.loads(b) for a, b in zip(old_bodies, new_bodies))
    old_hashes = [request_hash(r) for r in old_requests]
    new_hashes = [request_hash(r) for r in new_requests]
    old_launch = json.loads((root / 'config/m0_launch_spec_q3vl30.json').read_bytes())['argv']
    old_argv = ['--no-enable-prefix-caching' if a == '--enable-prefix-caching' else a for a in old_launch]  # host.derived_argv
    new_argv = [a.replace('{port}', str(protocol['server']['port'])) for a in protocol['server']['argv']]
    old_argv = [a.replace('{port}', '8000') for a in old_argv]
    manifest = json.loads((root / 'certification/phase4_integrated_v2/tokenizer_manifest.json').read_bytes())
    rules = json.loads((root / 'research/progress_subgoal_v1/decision_rules.json').read_bytes())['package_limits']
    limits = protocol['limits']
    checks = {
        'same_frozen_question_set': digest_old == digest_new == protocol['experiment']['probe_set_sha256'],
        'same_call_order': old_order == new_order,
        'scheduled_calls': len(new_order),
        'same_requests_all_scheduled_calls': old_requests == new_requests,
        'same_request_hashes': old_hashes == new_hashes,
        'request_digest': QN.request_digest(new_hashes),
        'http_bodies_decode_identically': bodies_equal and len(old_bodies) == len(new_bodies),
        'arms': frozen_new['conditions'],
        'arms_differ_only_in_system_prompt': all(
            a['messages'][1] == b['messages'][1] and {k: v for k, v in a.items() if k != 'messages'}
            == {k: v for k, v in b.items() if k != 'messages'}
            for a, b in _arm_pairs(frozen_new, contexts, probes)),
        'system_prompts_equal_question_module': frozen_new['system_prompts'] == {
            c: Q.SYSTEM_PROMPTS[c] for c in frozen_new['conditions']},
        'safeguard_arm_prompt_is_base_plus_safeguard': (
            Q.SYSTEM_PROMPTS['raw_plus_computed_record_plus_safeguard'] == Q.BASE_PROMPT + Q.SAFEGUARD),
        'answer_schemas_strict_enum': all(
            r['response_format']['json_schema']['strict'] is True
            and r['response_format']['json_schema']['schema'] == Q.response_schema(probes[i]['family'])
            for r, (_, _, i) in zip(new_requests, new_order)),
        'sampling': sorted({json.dumps({k: r[k] for k in ('model', 'temperature', 'seed', 'max_tokens',
                                                           'chat_template_kwargs')}, sort_keys=True)
                            for r in new_requests}),
        'stop_rules': {'admission_cutoff_seconds': S.ADMISSION_CUTOFF_SECONDS,
                       'per_call_timeout_seconds': S.PER_CALL_TIMEOUT_SECONDS,
                       'cancellation_verify_seconds': S.CANCELLATION_VERIFY_SECONDS,
                       'per_call_bound_seconds': S.PER_CALL_BOUND_SECONDS,
                       'max_consecutive_timeouts': S.MAX_CONSECUTIVE_TIMEOUTS,
                       'source': 'research/progress_subgoal_v1/schedule.py (imported unchanged by both runtimes)'},
        'successor_timing_equals_frozen': protocol['experiment']['call_timing'] == QN.frozen_timing(),
        'package_limits_equal_frozen_rules': (
            limits['internal_seconds'] == rules['internal_seconds']
            and limits['admission_cutoff_seconds'] == rules['admission_cutoff_seconds']
            and limits['cleanup_reserve_seconds'] == rules['cleanup_reserve_seconds']
            and limits['authorized_seconds'] == rules['maximum_reservation_seconds_per_session']
            and limits['maximum_attempts'] == rules['maximum_attempts']
            and limits['automatic_retries'] == rules['automatic_retries']),
        'served_model': [Q.MODEL, protocol['server']['served_model_name'], protocol['model']['model_id']],
        'model_revision': protocol['model']['revision'],
        'tokenizer_manifest_revision': manifest['revision'],
        'vllm_argv_equal_old_derived_argv': old_argv == new_argv,
        'prefix_caching_disabled_both': '--no-enable-prefix-caching' in old_argv and '--no-enable-prefix-caching' in new_argv,
        'scoring_module': 'research/progress_subgoal_v1/score.py (unchanged; the successor evaluator imports it and '
                          'the unchanged score_call rule from research/progress_subgoal_v1/evaluate_run.py)',
    }
    checks['nothing_scientific_changed'] = all(checks[k] is True for k in (
        'same_frozen_question_set', 'same_call_order', 'same_requests_all_scheduled_calls', 'same_request_hashes',
        'http_bodies_decode_identically', 'arms_differ_only_in_system_prompt', 'system_prompts_equal_question_module',
        'safeguard_arm_prompt_is_base_plus_safeguard', 'answer_schemas_strict_enum', 'successor_timing_equals_frozen',
        'package_limits_equal_frozen_rules', 'vllm_argv_equal_old_derived_argv')) and len(checks['sampling']) == 1
    return checks


def _arm_pairs(frozen, contexts, probes):
    from research.progress_subgoal_v1 import probes as P
    pairs = {}
    for p in frozen['probes']:
        pairs.setdefault(p['pair_id'], {})[p['condition']] = p
    for pair in pairs.values():
        if len(pair) == 2:
            a, b = (pair[c] for c in frozen['conditions'])
            yield (P.build_request(contexts[a['context_id']], a), P.build_request(contexts[b['context_id']], b))


def runtime_changes(root):
    old_meta = json.loads((root / R4 / 'kernel-metadata.json').read_bytes())
    protocol = json.loads((root / 'research/progress_subgoal_v1_runtime2/protocol.json').read_bytes())
    primary = (root / 'config/operational_primary.yaml').read_text(encoding='utf-8')
    return {
        'kernel_metadata_old_r4': {k: old_meta.get(k) for k in ('dataset_sources', 'model_sources',
                                                                 'competition_sources', 'docker_image')},
        'wheel_dataset': {'old': 'driessmit1/arc3-vllm-h100-wheelhouse-v3 (unversioned), mounted at '
                                 '/kaggle/input/datasets/driessmit1/... or /kaggle/input/arc3-vllm-h100-wheelhouse-v3 '
                                 '(first existing), verified by certification/phase4_v6/target_install_probe.'
                                 'verify_wheelhouses against the original wheelhouse metadata (SHA256SUMS 44029b36..., '
                                 'wheelhouse-manifest.json bc016164..., 179 listed entries)',
                          'new': {'dataset': protocol['dataset'], 'bundle': protocol['bundle']}},
        'installation': {'old': 'certification/phase4_integrated_v2/prepare.prepare: two venvs (model: vllm 0.19.0, '
                                'torch 2.10.0, transformers 4.57.6, numpy 2.2.6; game: arc-agi/arcengine from the '
                                'competition mount arc_agi_3_wheels, 31 wheels per reports/phase4_v2_offline_package.json), '
                                '450 s deadline',
                         'new': 'certification/direct_publisher_smoke_v1/install.py: one venv (--without-pip, host pip '
                                '--python), --no-index --require-hashes --only-binary=:all: from the flat mount with the '
                                'trusted hash-pinned lock (174 wheels), pip check, exact versions, imports, torch CUDA '
                                'build 12.8; no game environment'},
        'model': {'old': 'Kaggle Model qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1 at '
                         '/kaggle/input/models/qwen-lm/qwen-3-vl/transformers/30b-a3b-instruct-fp8/1, tree 052ab27f... '
                         '(config/operational_primary.yaml, reports/m0_profiles/m0-q3vl30-instruct.json)',
                  'new': protocol['model']},
        'old_model_tree_in_operational_primary': '052ab27f06c28261e143b8c1638382d107b034692bc0cd1792ec4e02ddab8627' in primary,
        'image': {'old': 'unpinned (provider default image)', 'new': protocol['kaggle_image']},
        'runtime_requirements_new': protocol['runtime'],
        'server_env_new': protocol['server']['env'],
        'canary': {'old': 'research/action_effect_history_v1/service.canary_request (action JSON) validated by '
                          'certification/phase4_transient_v2/action_contract.validate_canary',
                   'new': 'verified runtime S3 canary ("Reply with the single word: ok"), plus I1-I4 compatibility '
                          'probes and C1-C3 cancellation probes'},
        'cache_verification': {'old': 'per-call /metrics counters (prefix_cache_queries_total == 0) inside the model host',
                               'new': 'argv check plus every retained startup configuration entry '
                                      'enable_prefix_caching=False in the server log (runtime_controls.verify_cache_disabled)'},
        'timeout_idle_verification': {'old': 'host-side /metrics polling every 0.25 s within 15 s (uncounted)',
                                      'new': 'counted /metrics reads (QIDLE), one per second, each <= 1 s, within the '
                                             'same 15 s window; at most 15 per timed-out call and 750 per session'},
        'token_admission': {'old': 'in-process pinned tokenizer: prompt <= 60,000 and prompt + 32 <= 65,536 before '
                                   'each call; evaluator checks tokenizer/server parity',
                            'new': 'frozen offline audit of all 5,852 requests with the pinned tokenizer (bound by '
                                   'request digest); every server-reported prompt count must equal it (evaluator)'},
        'lifecycle': {'old': 'first cell -> supervisor -> worker (gated_exec) + monitor process groups; model host via '
                             'Unix-socket bridge; 3,300 s internal; 450 s install deadline',
                      'new': 'certification/direct_publisher_smoke_v1 lifecycle: host facts, bundle integrity, install, '
                             'GPU facts (exactly one RTX PRO 6000), model tree, server start (own process group), '
                             'TCP readiness, counted HTTP ledger, cutoff alarm, cleanup reserve, final deadline, '
                             'evidence manifest; limits ' + json.dumps(protocol['limits'], sort_keys=True)},
        'request_accounting': {'old': 'questionnaire allow-list and 5,852-call ceiling in the model host',
                               'new': 'counted ledger: S1-S3, I1-I4, Q00000-Q05851, QIDLE (<= 750), C1-C3; '
                                      'cap ' + str(protocol['limits']['maximum_model_requests'])},
        'authority': {'old': 'reports/progress_subgoal_v1_{source_approval,compute_authorization}.json, '
                             'research/progress_subgoal_v1/{execution_lock,reservation}.json (none exist)',
                      'new': 'runtime2 scope: separate source/compute approvals, account-attachment, direct-use '
                             'permission and byte-verification receipts, execution lock, reservation, launch claim and '
                             'receipt (none exist; private records are git-ignored)'},
    }


def main():
    root = ROOT
    record = {'schema': 'progress_subgoal_v1_runtime2_source_diff_v1', 'files': file_diff(root),
              'semantic_checks': semantic(root), 'runtime_changes': runtime_changes(root),
              'gpu_used': False, 'model_calls': 0, 'provider_calls': 0}
    (root / OUT).write_bytes((json.dumps(record, sort_keys=True, indent=1) + '\n').encode())
    files = record['files']
    print(json.dumps({'unchanged': len(files['unchanged']), 'changed_in_place': files['changed_in_place'],
                      'added': len(files['added']), 'removed': files['removed_count'],
                      'nothing_scientific_changed': record['semantic_checks']['nothing_scientific_changed']}, indent=1))
    return 0 if record['semantic_checks']['nothing_scientific_changed'] and not files['changed_in_place'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
