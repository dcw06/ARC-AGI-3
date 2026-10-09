"""Derive the progress_subgoal_v1 runtime successor (runtime2) from the verified direct-publisher runtime.

No network, installation, GPU, provider call, approval or reservation. The questionnaire's science is not touched:
its frozen question set, requests, arms, schedule, scoring and stop rules are imported unchanged from
research/progress_subgoal_v1 (their hashes are recorded and must equal the hashes review r4 bound).

Basis: the runtime that ran successfully on GPU, origin/wheelhouse-replacement-audit at 5a21dd3:
- certification/direct_publisher_smoke_v1/ (the shared controller: host facts, flat-mount wheel integrity,
  hash-pinned offline install without ensurepip, dataset-backed model mount and tree pin, vLLM server process
  group, counted HTTP ledger, deadlines, cancellation probes, cleanup) is copied byte-identically;
- research/control_interface_action_selection_v2/{binding,run,notebook,launch,evidence,runtime_controls,rehearsal,
  rehearsal_stub}.py and two of its scripts are derived here by counted substitutions (new scope and paths, the
  questionnaire stage in place of the action-selection stage, this experiment's frozen configuration checks).
The protocol is derived from the copied controller's protocol.json with the same model/argv/placeholder changes the
verified research packages applied (dataset-backed private model snapshot with REPLACE_WITH_ placeholders, prefix
caching disabled), plus this experiment's frozen limits, request plan and experiment record.

Usage:
  python scripts/build_progress_subgoal_v1_runtime2.py --basis DIR [--write]
      DIR holds the 5a21dd3 basis files at their repository paths, e.g. from
      `git archive 5a21dd3 research/control_interface_action_selection_v2 scripts certification/direct_publisher_smoke_v1 | tar -x -C DIR`;
      every basis file's SHA-256 is checked first. Without --write the derived files are compared, not written.
  python scripts/build_progress_subgoal_v1_runtime2.py --check
      without the basis: the copied controller, every derived output and the generated records against
      derivation.json, and the experiment sources against the hashes review r4 bound.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASIS_COMMIT = '5a21dd3'
BASIS_REF = 'origin/wheelhouse-replacement-audit'
OLD = 'research/control_interface_action_selection_v2'
SMOKE = 'certification/direct_publisher_smoke_v1'
NEW = 'research/progress_subgoal_v1_runtime2'
SCOPE = 'progress-subgoal-v1-runtime2'
SUPERSEDED_LOCK = 'notebooks/progress-subgoal-v1-review-r4/review-source-lock.json'
SUPERSEDED_LOCK_SHA256 = 'e7e1518ba6e23b9b3d4a24a6de25aaac94df5663e31dbf884859fd44eeff70f2'
HEADER = '# Derived from {source} ({commit}) by scripts/build_progress_subgoal_v1_runtime2.py; edit the derivation.\n'
OLD_HEADER = '# Derived by scripts/build_control_interface_action_selection_v2.py; edit the derivation.\n'

# SHA-256 of every basis file at 5a21dd3 (checked before any derivation).
BASIS_SHA256 = {
    OLD + '/__init__.py': '42e947c03c585549674be9ba3c0d17b394674d58df2ae90c95f5569675ae3372',
    OLD + '/binding.py': 'ff2ddcf04e811f00eb6002485968c88ad1c383eeeb9dfdb01514b1458b18bad1',
    OLD + '/evidence.py': '7347a23c8e06f8ee8fd88a5a37aad6472a3652bde6f776057650151e0dec26fa',
    OLD + '/launch.py': '1148e4ee138102cc8ada817318aa01643163d101827c43d19c7748b925d7a682',
    OLD + '/notebook.py': 'a208d642caa0a5c6e5126432ab3a0c034157b224cab117a59224749d2a3e1c15',
    OLD + '/rehearsal.py': '942c644714f7f5a4126a90203846ea196433f5f4a0d012fb3c7955ca108eb3c7',
    OLD + '/rehearsal_stub.py': '763d2afecfb35960b519d2a7f0a9c803e3675bb9b2bb60e85d5e17164648307d',
    OLD + '/run.py': 'a6fd4d76e90ba23ca1015b08f7e300005acab7be2c2ac616ab404679d6bf5b69',
    OLD + '/runtime_controls.py': 'd2e8fa1051de4b63109480f85536913cf1e3171546db4f16eb10bc80339a0603',
    OLD + '/protocol.json': 'b1ef5b2c759e0451197b08b49417b7f5ce4e864c8d52d297e5876954a3f68de9',
    OLD + '/trusted_manifest.json': '91ad9ede70c4fdf027cf5739a828f9063dc07c22c6010a64ebd1af0db8f0462b',
    OLD + '/trusted_requirements.lock': 'ba80d35062245421daf1cae65474281952cc0c44fb46e11cf7f68d0ece496406',
    'scripts/control_interface_action_selection_v2_package.py':
        '66f215eb350bc3e30c9cdea1b353046af203a5d00c31a983b41d037602f25b68',
    'scripts/check_control_interface_embedded_inputs.py':
        'a6f9a327fbfdb142c749294e5f694eda109d71c05d82ce231295d1f74b67dde7',
}
# The shared controller, copied byte-identically from 5a21dd3 (same SHA-256 as the basis).
SMOKE_SHA256 = {
    SMOKE + '/__init__.py': '08c32bf5bc6167ad1202120f90a00043271310c34896d33188c78e2049eb2665',
    SMOKE + '/accounting.py': '121e56d47afa86dcf44db1476cf68b734fa3ab7fdd9a002ce6a9e35dbd5e94ca',
    SMOKE + '/binding.py': '81991b497bf9289b05230151597aa34cc70729554f881e35dbc19abdb68c1651',
    SMOKE + '/client.py': 'd83c463384a54506d6aea1ca00217111b3daa4601d3dee10c6f0b0b0c4d45c37',
    SMOKE + '/evidence.py': 'd9be6ad7bbe9e09ed3297b2bb1af9f4909aef95d78d39adef226d7c94cb4ed65',
    SMOKE + '/host.py': '6eab062887c5ba4460f4a5f953da8b6b17fc7ddf40404ec74e9d10bbb8c1c9a8',
    SMOKE + '/install.py': '568ef619fce6fc8ed03eda07e7a240f079e017379e1494f4a6b95672cad0019b',
    SMOKE + '/launch.py': '1751bc29b1ea59214bd69e18743e211288c33c2b05934fd98e4891f9b03f4bff',
    SMOKE + '/notebook.py': '96382e1fa675f42765946805241804f60a3b4178ec713bcf1f3bcd4a3214e406',
    SMOKE + '/preflight.py': '369a39a09c4f5f97b0d92613c3ecc6aa281779af4721a4154fe98576e4fc3b0d',
    SMOKE + '/proposal.json': 'cb5e1cee9903861e16960664c4d392821fb880e4125c7bce1865ea69573a600c',
    SMOKE + '/protocol.json': 'b0c3757e0d12b0b3839bbbf9f67e2ca133637f13a46c52e113c3494b9c24c106',
    SMOKE + '/rehearsal.py': '7e20699eb610e438d050b90b379aa673ce848ab16825ee76c4a0ec916db3b246',
    SMOKE + '/rehearsal_stub.py': '5ffec6525399a51379ffde7864571263ca3f99661723a7ebe07e8a8631202d0e',
    SMOKE + '/run.py': 'ba9e75e5ad7e0f952fea224fc3aff9b4950e1850b9d318354fe45c5ee21705b1',
    SMOKE + '/server.py': 'e3cbdf0949f21fc2edb6f8c781a55aaeacf3410aa4f5794e3ebe420f2bcee888',
    SMOKE + '/trusted_manifest.json': '91ad9ede70c4fdf027cf5739a828f9063dc07c22c6010a64ebd1af0db8f0462b',
    SMOKE + '/trusted_requirements.lock': 'ba80d35062245421daf1cae65474281952cc0c44fb46e11cf7f68d0ece496406',
}
# Hand-written for this successor (not derived by substitution); recorded with their hashes.
ADAPTERS = (NEW + '/questionnaire.py', 'scripts/evaluate_progress_subgoal_v1_runtime2.py',
            'scripts/audit_progress_subgoal_v1_runtime2.py', 'scripts/build_progress_subgoal_v1_runtime2.py')

GLOBAL = (('research.control_interface_action_selection_v2', 'research.progress_subgoal_v1_runtime2'),
          ('research/control_interface_action_selection_v2', NEW),
          ('control_interface_action_selection_v2', 'progress_subgoal_v1_runtime2'),
          ('control-interface-action-selection-v2', SCOPE))
RESIDUE = ('control_interface', 'control-interface', 'action_selection', 'action-selection', 'cia-',
           'Control Interface', 'run_cases', 'probe as P')

# ------------------------------------------------------------------ replacement blocks

RUNTIME_CONTROLS_OLD_BODY = '''import hashlib
import json
from pathlib import Path
import re
from . import probe as P


def validate_protocol(root, protocol):
'''
RUNTIME_CONTROLS_NEW_HEAD = '''import hashlib
import json
from pathlib import Path
import re
from . import questionnaire as QN

# The unchanged progress_subgoal_v1 sources the live and rehearsal paths import or read (every module-level import
# of these resolves inside this set; scripts/build_progress_subgoal_v1_runtime2.py recomputes it). Their hashes are
# the ones review r4 bound: the science is reused, never edited.
EXPERIMENT_SOURCES = {experiment_sources!r}
DECISION_RULES = 'research/progress_subgoal_v1/decision_rules.json'
DECISION_RULES_SHA256 = '38c8de63a875e54949fc0ecede9c0dd2b0b603901aad4a3f8348fd6b92089af2'
RUNTIME_PROBES = ('S1', 'S2', 'S3', 'I1', 'I2', 'I3', 'I4', 'C1', 'C2', 'C3')  # the verified runtime's, unchanged
RUNTIME_REQUESTS = 11  # C2 may read /metrics twice
MAXIMUM_MODEL_REQUESTS = RUNTIME_REQUESTS + 5852 + QN.IDLE_READS_PER_TIMEOUT * QN.MAX_TIMED_OUT_CALLS
PROMPT_TOKEN_CEILING, CONTEXT_TOKENS = 60000, 65536


def experiment_record(root):
    """The frozen experiment configuration recomputed from the unchanged sources (never read from the protocol)."""
    from research.action_effect_history_v1.service import request_hash
    from research.progress_subgoal_v1 import questions as Q
    from research.progress_subgoal_v1 import schedule as S
    frozen, digest, rows = QN.scheduled(root)
    requests = [row[4] for row in rows]
    phases = {{}}
    for _, phase, _, _, _ in rows:
        phases[phase] = phases.get(phase, 0) + 1
    if frozen['system_prompts'] != {{c: Q.SYSTEM_PROMPTS[c] for c in frozen['conditions']}}:
        raise ValueError('frozen system prompts differ from the question module')
    shapes = {{json.dumps({{k: v for k, v in r.items() if k not in ('messages', 'response_format')}}, sort_keys=True)
              for r in requests}}
    formats = {{(r['response_format']['type'], r['response_format']['json_schema']['strict']) for r in requests}}
    return {{'probe_set': QN.FROZEN, 'probe_set_sha256': digest, 'scheduled_calls': len(rows), 'phases': phases,
            'distinct_requests': len({{request_hash(r) for r in requests}}),
            'request_digest': QN.request_digest([request_hash(r) for r in requests]),
            'arms': list(frozen['conditions']),
            'system_prompt_sha256': {{c: hashlib.sha256(p.encode()).hexdigest()
                                     for c, p in sorted(frozen['system_prompts'].items())}},
            'decision_source_partition': frozen['decision_source_partition'],
            'request_settings': sorted(json.loads(s) for s in shapes),
            'response_format': sorted([list(f) for f in formats]),
            'max_tokens': Q.MAX_TOKENS, 'served_model': Q.MODEL,
            'call_timing': QN.frozen_timing(), 'per_call_bound_seconds': S.PER_CALL_BOUND_SECONDS,
            'max_consecutive_timeouts': S.MAX_CONSECUTIVE_TIMEOUTS,
            'admission_cutoff_seconds': S.ADMISSION_CUTOFF_SECONDS,
            'idle_check': {{'poll_seconds': QN.IDLE_POLL_SECONDS, 'read_timeout_seconds': QN.IDLE_READ_TIMEOUT_SECONDS,
                           'reads_per_timeout': QN.IDLE_READS_PER_TIMEOUT,
                           'max_timed_out_calls': QN.MAX_TIMED_OUT_CALLS}},
            'prefix_caching': False, 'prompt_token_ceiling': PROMPT_TOKEN_CEILING, 'context_tokens': CONTEXT_TOKENS}}


def validate_protocol(root, protocol):
    experiment = protocol['experiment']
    expected = experiment_record(root)
    drift = sorted(k for k, v in expected.items() if experiment.get(k) != v)
    if drift:
        raise ValueError('frozen experiment configuration drift: ' + ', '.join(drift))
    raw = (Path(root) / DECISION_RULES).read_bytes()
    if hashlib.sha256(raw).hexdigest() != DECISION_RULES_SHA256 or experiment.get('decision_rules_sha256') != DECISION_RULES_SHA256:
        raise ValueError('frozen decision rules drift')
    package, limits = json.loads(raw)['package_limits'], protocol['limits']
    if (package['sessions'] != 1 or limits['authorized_seconds'] != package['maximum_reservation_seconds_per_session']
            or any(limits[k] != package[k] for k in ('internal_seconds', 'admission_cutoff_seconds',
                                                     'cleanup_reserve_seconds', 'maximum_attempts', 'automatic_retries'))
            or limits.get('environment_actions') != 0 or limits.get('scorecards') != 0
            or limits['maximum_model_requests'] != MAXIMUM_MODEL_REQUESTS):
        raise ValueError('limits differ from the frozen package limits')
    audit = QN.token_audit(root)
    tokens = audit.get('prompt_tokens')
    if (audit.get('passed') is not True or audit.get('probe_set_sha256') != expected['probe_set_sha256']
            or audit.get('request_digest') != expected['request_digest'] or not isinstance(tokens, list)
            or len(tokens) != expected['scheduled_calls']
            or any(type(t) is not int or not 0 < t <= PROMPT_TOKEN_CEILING or t + expected['max_tokens'] > CONTEXT_TOKENS
                   for t in tokens)
            or audit.get('max_tokens_check', {{}}).get('all_cover') is not True):
        raise ValueError('token audit missing, incomplete or not bound to actual requests')
    if protocol['server']['served_model_name'] != expected['served_model']:
        raise ValueError('served model differs from the frozen requests')
'''

RUNTIME_CONTROLS_OLD_TAIL = '''    argv = protocol['server']['argv']
    if argv.count('--no-enable-prefix-caching') != 1 or '--enable-prefix-caching' in argv:
        raise ValueError('prefix caching must be explicitly disabled')
    requests = protocol['requests']
    if len({r['id'] for r in requests}) != len(requests) or sum(r.get('max_issues', 1) for r in requests) != 131:
        raise ValueError('frozen counted request cap drift')
    research = [r for r in requests if r['kind'] == 'action_selection']
    expected = [{'id': r['id'], 'kind': 'action_selection', 'method': 'POST', 'path': '/v1/chat/completions',
                 'timeout_seconds': 60} for r in P.schedule(cases)]
    if research != expected:
        raise ValueError('research request plan drift')
'''
RUNTIME_CONTROLS_NEW_TAIL = '''    argv = protocol['server']['argv']
    if argv.count('--no-enable-prefix-caching') != 1 or '--enable-prefix-caching' in argv:
        raise ValueError('prefix caching must be explicitly disabled')
    requests = protocol['requests']
    if (len({r['id'] for r in requests}) != len(requests)
            or sum(r.get('max_issues', 1) for r in requests) != MAXIMUM_MODEL_REQUESTS):
        raise ValueError('frozen counted request cap drift')
    research = [r for r in requests if r['kind'] in (QN.KIND, QN.IDLE_KIND)]
    if research != QN.request_plan(expected['scheduled_calls'], expected['call_timing']['timeout_seconds']):
        raise ValueError('questionnaire request plan drift')
    if [r['id'] for r in requests if r not in research] != list(RUNTIME_PROBES):
        raise ValueError('runtime probe plan drift')
'''

RUN_STAGE_OLD = '''        from research.progress_subgoal_v1_runtime2.probe import run_cases
        from research.progress_subgoal_v1_runtime2.runtime_controls import verify_cache_disabled
        if experiment_root is None:
            raise ValueError('frozen experiment root required')
        stage('cache_config', lambda: verify_cache_disabled(workdir / 'server.log'))
        result['action_selection'] = stage('action_selection', lambda: run_cases(experiment_root, client, evidence, clock))
        telemetry('after_action_selection')
'''
RUN_STAGE_NEW = '''        from research.progress_subgoal_v1_runtime2.questionnaire import run_questionnaire
        from research.progress_subgoal_v1_runtime2.runtime_controls import verify_cache_disabled
        if experiment_root is None:
            raise ValueError('frozen experiment root required')
        stage('cache_config', lambda: verify_cache_disabled(workdir / 'server.log'))
        result['questionnaire'] = stage('questionnaire', lambda: run_questionnaire(experiment_root, client, evidence,
                                                                                   clock, protocol))
        telemetry('after_questionnaire')
'''

NOTEBOOK_CASES_OLD = ("    names += ['research/control_interface_action_selection_v1/cases.json', "
                      "'research/control_interface_action_selection_v1/cases-lock.json', PACKAGE + '/derivation.json', "
                      "PACKAGE + '/token-audit.json']\n")
NOTEBOOK_CASES_NEW = ("    from research.progress_subgoal_v1_runtime2.runtime_controls import EXPERIMENT_SOURCES\n"
                      "    names += list(EXPERIMENT_SOURCES) + [PACKAGE + '/derivation.json', PACKAGE + '/token-audit.json']\n")
NOTEBOOK_MARKDOWN_OLD = """                           '# Milestone E paired action selection v1 (development observations only)\\n'
                           'One attempt: offline install from the verified flat publisher mount with our trusted '
                           'hash-pinned requirements, pinned model startup, at most 131 counted '
                           'model requests (startup and cancellation probes included), cancellation, cleanup and '
                           'retained evidence. 120 paired research completions; zero game actions. No solving or game-progress claim. This notebook refuses to run unless the dataset/account and direct-use evidence, '
"""
NOTEBOOK_MARKDOWN_NEW = """                           '# progress_subgoal_v1 questionnaire on the verified runtime (runtime2)\\n'
                           'One attempt: offline install from the verified flat publisher mount with our trusted '
                           'hash-pinned requirements, pinned model startup, at most 6,613 counted '
                           'model requests (startup, idle-check and cancellation probes included), cancellation, cleanup and '
                           'retained evidence. The frozen questionnaire: 3,062 questions in 5,852 scheduled calls; zero game actions. '
                           'Scores and readiness come only from the independent evaluator. This notebook refuses to run unless the dataset/account and direct-use evidence, '
"""
NOTEBOOK_LOCK_OLD = """    lock = {'status': 'review_snapshot_not_approved_not_compute_authority', 'scope': 'progress-subgoal-v1-runtime2',
            'bindings': bindings, 'artifacts': {n: hashlib.sha256(d).hexdigest() for n, d in artifacts.items()},
            'unresolved_placeholders': pending, 'gpu_enabled': False}
"""
NOTEBOOK_LOCK_NEW = """    lock = {'status': 'review_snapshot_not_approved_not_compute_authority', 'scope': 'progress-subgoal-v1-runtime2',
            'bindings': bindings, 'artifacts': {n: hashlib.sha256(d).hexdigest() for n, d in artifacts.items()},
            'unresolved_placeholders': pending, 'gpu_enabled': False,
            'revision': output.name.rsplit('-', 1)[1], 'supersedes': dict(SUPERSEDES),
            'review_documents': {n: sha256(Path(root) / n) for n in REVIEW_DOCUMENTS},
            'authorized_seconds': 0, 'gpu_launch_authorized': False}
"""
NOTEBOOK_CONSTANTS_OLD = "SIZE_GUARD = 900000\n"
NOTEBOOK_CONSTANTS_NEW = """SIZE_GUARD = 900000
# The superseded review package of the same experiment (old runtime). It stays byte-identical; nothing is inherited.
SUPERSEDES = {'review_lock': 'notebooks/progress-subgoal-v1-review-r4/review-source-lock.json',
              'review_lock_sha256': 'e7e1518ba6e23b9b3d4a24a6de25aaac94df5663e31dbf884859fd44eeff70f2'}
# Hash-bound for review, never part of the runtime payload: the protocol, frozen rules and decisions, the independent
# evaluator and token audit tooling, the derivation, and this successor's reports.
REVIEW_DOCUMENTS = ('reports/progress_subgoal_v1_protocol_v2.md', 'research/progress_subgoal_v1/decision_rules.json',
                    'research/progress_subgoal_v1/third_arm_decision.json',
                    'research/progress_subgoal_v1/evaluation_seed.json', 'research/progress_subgoal_v1/score.py',
                    'research/progress_subgoal_v1/evaluate_run.py', 'research/progress_subgoal_v1/token_audit.py',
                    'scripts/evaluate_progress_subgoal_v1_runtime2.py', 'scripts/audit_progress_subgoal_v1_runtime2.py',
                    'scripts/build_progress_subgoal_v1_runtime2.py', 'scripts/progress_subgoal_v1_runtime2_package.py',
                    'reports/progress_subgoal_v1_runtime2_binding_inventory.md',
                    'reports/progress_subgoal_v1_runtime2_source_diff.md',
                    'reports/progress_subgoal_v1_runtime2_source_diff.json',
                    'reports/progress_subgoal_v1_runtime2_budget.json')
"""

REHEARSAL_NEW = '''"""Fixture installation plus local scripted HTTP, timeout/cancellation and cleanup. Zero GPU/model calls.

The complete frozen questionnaire (all 5,852 scheduled calls, built from the frozen question set) runs through the
derived lifecycle against the scripted stub. The stub's answers are scripted (research.progress_subgoal_v1.fake_server
rules, or the keys for `oracle`); labels from a rehearsal are not results. Returns (result, declared protocol): the
declared protocol is what an independent evaluation of the rehearsal must use."""
import copy
import os
from pathlib import Path
import sys
import time

from certification.direct_publisher_smoke_v1 import host
from certification.direct_publisher_smoke_v1 import rehearsal as fixtures
from . import binding, questionnaire as QN, run

FAULTS = ('none', 'timeout_once', 'consecutive_timeouts', 'not_idle', 'http_error', 'token_mismatch',
          'admission_cutoff')
POLICIES = ('scripted', 'oracle')
# The reviewed rehearsal timing (research/progress_subgoal_v1/worker.py: 2 s calls, 3 s idle verification).
TIMING = {'timeout_seconds': 2.0, 'teardown_seconds': 1, 'verify_seconds': 3.0, 'margin_seconds': 4}
LIMITS = {'internal_seconds': 1500, 'admission_cutoff_seconds': 1200, 'cleanup_reserve_seconds': 300,
          'installation_seconds': 180, 'startup_ceiling_seconds': 120, 'model_verification_seconds': 10}
# admission_cutoff: the stub adds latency so the frozen admission rule stops the schedule inside withheld pass 1.
CUTOFF_LIMITS = dict(LIMITS, internal_seconds=400, admission_cutoff_seconds=100)
CUTOFF_LATENCY_SECONDS = 0.03
# The fixture installation needs a host interpreter with pip (>= 22.3) to manage the fresh venv; a rehearsal harness
# whose own interpreter has no pip names one here (CPU rehearsal only; the live path always uses its own).
HOST_PYTHON_ENV = 'PSV1R2_REHEARSAL_HOST_PYTHON'


def declared_protocol(root, pins, model, tree, port, fault):
    protocol = copy.deepcopy(binding.load_protocol(root))
    protocol['dataset'], protocol['bundle'] = pins['dataset'], pins['bundle']
    protocol['runtime'].update(packages={'fixturea': '1.0', 'fixtureb': '1.0'}, imports=['fixturea', 'fixtureb'])
    protocol['runtime'].pop('torch_cuda_build')
    protocol['model'].update(mounted_path=str(model), tree_sha256=tree, required_files=['config.json'],
                             shard_glob='model-*.bin', shard_count=1)
    protocol['model'].pop('source_kind')  # isolated fixture tree, not a real Kaggle dataset mount
    protocol['server'].update(port=port, terminate_grace_seconds=2, kill_grace_seconds=2)
    protocol['limits'].update(CUTOFF_LIMITS if fault == 'admission_cutoff' else LIMITS)
    protocol['experiment']['call_timing'] = dict(TIMING)
    for item in protocol['requests']:
        item['timeout_seconds'] = (TIMING['timeout_seconds'] if item['kind'] == QN.KIND
                                   else QN.IDLE_READ_TIMEOUT_SECONDS if item['kind'] == QN.IDLE_KIND else 5)
    protocol['server']['env']['PYTHONPATH'] = str(root)
    return protocol


def scenario(root, folder, fault='none', policy='scripted'):
    if fault not in FAULTS or policy not in POLICIES:
        raise ValueError('rehearsal scenario')
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    inputs = folder / 'trusted'
    bundle = folder / 'bundle'
    pins = fixtures.fixture_bundle(bundle, inputs)
    model = folder / 'model'
    tree = fixtures.fixture_model(model)
    protocol = declared_protocol(root, pins, model, tree, fixtures.free_port(), fault)
    latency = CUTOFF_LATENCY_SECONDS if fault == 'admission_cutoff' else 0.0
    # -m uses the fixture venv's interpreter without installing any research/game packages.
    argv = lambda py: [py, '-m', 'research.progress_subgoal_v1_runtime2.rehearsal_stub',
        '--port', str(protocol['server']['port']), '--served', protocol['server']['served_model_name'],
        '--questionnaire-fault', fault, '--policy', policy, '--latency', str(latency), '--root', str(root)]
    result = run.run('rehearsal', protocol, folder / 'evidence', time.monotonic(), bundle=bundle,
        workdir=folder / 'work', python=os.environ.get(HOST_PYTHON_ENV) or sys.executable, trusted_inputs=inputs,
        server_argv=argv,
        experiment_root=root, model_check=lambda check: host.verify_model(protocol['model'], check))
    return result, protocol
'''

REHEARSAL_STUB_NEW = '''"""Local HTTP fixture, not a model. Exercises the complete bounded controller on CPU.

Questionnaire requests (strict json_schema response format) get scripted answers: `scripted` applies the reviewed
rehearsal rule of research.progress_subgoal_v1.fake_server.ScriptedAnswers (mostly correct; deterministic wrong,
invalid, truncated and pass-2-divergent answers), `oracle` answers every key. Prompt-token usage is the frozen offline
token audit's count for that request, so the controller's parity check is exercised. Faults act on questionnaire
call FAULT_AT (0-based) and, for consecutive timeouts, the call after it."""
import argparse
import json
from pathlib import Path
import threading
import time
from http.server import ThreadingHTTPServer
from certification.direct_publisher_smoke_v1 import rehearsal_stub as base

FAULT_AT = 7
HANG_SECONDS = 60
LOCK = threading.Lock()


class Handler(base.Handler):
    questionnaire_fault = 'none'
    policy = 'scripted'
    latency = 0.0
    answers = tokens = keys = None
    calls = 0
    busy = False

    def do_GET(self):
        if self.path == '/metrics' and Handler.busy:  # not_idle: the hung request is still reported running
            text = (f'vllm:num_requests_running{{model_name="{self.served}"}} 1.0\\n'
                    f'vllm:num_requests_waiting{{model_name="{self.served}"}} 0.0\\n')
            return self._send(200, text.encode(), 'text/plain')
        return super().do_GET()

    def do_POST(self):
        from research.progress_subgoal_v1.fake_server import TRUNCATED, request_sha
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
        if self.path != '/v1/chat/completions':
            return self._send(404, {'error': 'not found'})
        if body.get('stream'):
            return self._stream(body)
        questionnaire = (body.get('response_format') or {}).get('type') == 'json_schema'
        content, finish, usage = base.answer(body), 'stop', {'prompt_tokens': 100, 'completion_tokens': 1}
        if questionnaire:
            with LOCK:
                n = Handler.calls
                Handler.calls += 1
            fault = self.questionnaire_fault
            if self.latency:
                time.sleep(self.latency)
            hang = ((fault in ('timeout_once', 'not_idle') and n == FAULT_AT)
                    or (fault == 'consecutive_timeouts' and n in (FAULT_AT, FAULT_AT + 1)))
            if hang:
                if fault == 'not_idle':
                    Handler.busy = True
                time.sleep(HANG_SECONDS)
                return None  # the client has closed the connection
            if fault == 'http_error' and n == FAULT_AT:
                return self._send(500, {'error': 'scripted server error'})
            digest = request_sha(body)
            content = (json.dumps({'answer': self.keys[digest]}) if self.policy == 'oracle'
                       else self.answers(body))
            completion = max(1, min(31, len(content) // 3))
            if content.startswith(TRUNCATED):
                content, finish, completion = content[len(TRUNCATED):], 'length', 32
            usage = {'prompt_tokens': self.tokens[digest] + (1 if fault == 'token_mismatch' and n == FAULT_AT else 0),
                     'completion_tokens': completion}
        self._send(200, {'model': self.served, 'choices': [{'index': 0,
            'message': {'role': 'assistant', 'content': content}, 'finish_reason': finish}],
            'usage': usage})


def prepare(root):
    """Scripted answers and the frozen token audit's prompt-token count for every scheduled request."""
    from research.action_effect_history_v1.service import request_hash
    from research.progress_subgoal_v1.fake_server import ScriptedAnswers
    from research.progress_subgoal_v1_runtime2 import questionnaire as QN
    frozen, _, rows = QN.scheduled(root)
    audit = QN.token_audit(root)
    probes = {p['probe_id']: p for p in frozen['probes']}
    tokens, keys = {}, {}
    for n, (_, _, _, probe_id, request) in enumerate(rows):
        digest = request_hash(request)
        tokens[digest] = audit['prompt_tokens'][n]
        keys[digest] = probes[probe_id]['key']
    return ScriptedAnswers(), tokens, keys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--served', required=True)
    parser.add_argument('--questionnaire-fault', choices=('none', 'timeout_once', 'consecutive_timeouts', 'not_idle',
                                                          'http_error', 'token_mismatch', 'admission_cutoff'),
                        default='none')
    parser.add_argument('--policy', choices=('scripted', 'oracle'), default='scripted')
    parser.add_argument('--latency', type=float, default=0.0)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    Handler.answers, Handler.tokens, Handler.keys = prepare(args.root)
    print('SCRIPTED CPU STUB: no model, no GPU; enable_prefix_caching=False', flush=True)
    Handler.served, Handler.questionnaire_fault = args.served, args.questionnaire_fault
    Handler.policy, Handler.latency = args.policy, args.latency
    ThreadingHTTPServer.daemon_threads = True
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
'''


def derivations(experiment_sources):
    """target -> (basis, [(old, new, count)]) applied after the global renames."""
    package = 'scripts/progress_subgoal_v1_runtime2_package.py'
    embedded = 'scripts/check_progress_subgoal_v1_runtime2_embedded_inputs.py'
    return {
        NEW + '/__init__.py': (OLD + '/__init__.py', [
            ('"""Milestone E paired retained-observation development probe; imports have no effects."""',
             '"""progress_subgoal_v1 questionnaire on the verified direct-publisher runtime; imports have no effects."""', 1)]),
        NEW + '/binding.py': (OLD + '/binding.py', [
            ("CLAIM = 'config/progress_subgoal_v1_runtime2_launch_claim.json'",
             "CLAIM = 'reports/progress_subgoal_v1_runtime2_launch_claim.json'  # never in config/ (old r4 inventory)", 1),
            ("ATTEMPT = re.compile(r'cia-[a-zA-Z0-9-]{8,80}')", "ATTEMPT = re.compile(r'psv1r2-[a-zA-Z0-9-]{8,80}')", 1),
            ("'control-interface action selection live path refused: '",
             "'progress_subgoal_v1 runtime2 live path refused: '", 1),
            ("raise ValueError('not the direct publisher smoke v1 protocol')",
             "raise ValueError('not the progress_subgoal_v1 runtime2 protocol')", 1),
            ("            or limits['maximum_model_requests'] != 131\n",
             "            or limits['maximum_model_requests'] != 6613\n", 1),
            ("    required |= {'research/control_interface_action_selection_v1/cases.json', "
             "'research/control_interface_action_selection_v1/cases-lock.json', PACKAGE + '/derivation.json', "
             "PACKAGE + '/token-audit.json'}\n",
             "    from .runtime_controls import EXPERIMENT_SOURCES\n"
             "    required |= set(EXPERIMENT_SOURCES) | {PACKAGE + '/derivation.json', PACKAGE + '/token-audit.json'}\n", 1),
        ]),
        NEW + '/runtime_controls.py': (OLD + '/runtime_controls.py', [
            (RUNTIME_CONTROLS_OLD_BODY, RUNTIME_CONTROLS_NEW_HEAD.format(experiment_sources=tuple(experiment_sources)), 1),
            # the action-selection experiment checks are replaced by validate_protocol's head above
            ("""    cases = P.load_cases(root)
    experiment = protocol['experiment']
    if (experiment.get('schedule') != P.schedule(cases) or experiment.get('arms') != list(P.ARMS)
            or experiment.get('cases_sha256') != hashlib.sha256((Path(root) / P.CASE_PACKAGE / 'cases.json').read_bytes()).hexdigest()
            or experiment.get('system_sha256') != hashlib.sha256(P.SYSTEM.encode()).hexdigest()
            or experiment.get('prefix_caching') is not False or experiment.get('research_requests') != 120
            or experiment.get('max_tokens') != 128 or experiment.get('prompt_token_ceiling') != 60000
            or protocol['limits'].get('environment_actions') != 0 or protocol['limits'].get('scorecards') != 0):
        raise ValueError('frozen experiment configuration drift')
    if experiment.get('research_seconds') != 1500:
        raise ValueError('research phase ceiling drift')
    audit = json.loads((Path(root) / P.PACKAGE / 'token-audit.json').read_bytes())
    rows = audit['requests']
    expected_tokens = [(c['case_id'], arm, P.digest(P.request_for(c, arm, protocol['server']['served_model_name'])))
                       for c in cases for arm in P.ARMS]
    if (audit.get('passed') is not True or audit.get('cases_sha256') != experiment['cases_sha256']
            or [(r['case_id'], r['arm'], r['request_sha256']) for r in rows] != expected_tokens
            or any(type(r.get('prompt_tokens')) is not int or not 0 < r['prompt_tokens'] <= 60000 for r in rows)):
        raise ValueError('token audit missing, incomplete or not bound to actual requests')
    if experiment.get('shared_output_contract_sha256') != P.digest(P.OUTPUT_CONTRACT):
        raise ValueError('shared output contract drift')
""", '', 1),
            (RUNTIME_CONTROLS_OLD_TAIL, RUNTIME_CONTROLS_NEW_TAIL, 1),
        ]),
        NEW + '/run.py': (OLD + '/run.py', [
            ('-> startup probes -> inference -> cancellation probes -> termination and cleanup -> retained evidence.',
             '-> startup probes -> inference -> cache configuration -> the frozen questionnaire -> cancellation probes\n'
             '-> termination and cleanup -> retained evidence.', 1),
            ("NOT_ESTABLISHED = ['solving ability, level progress or action usefulness', 'Phase 4 completion', "
             "'throughput or capacity limits',\n                   'behaviour beyond the frozen request plan']",
             "NOT_ESTABLISHED = ['questionnaire scores, completeness or readiness (only the independent evaluator decides "
             "them)',\n                   'solving ability, level progress or action usefulness', 'Phase 4 completion',\n"
             "                   'throughput or capacity limits', 'behaviour beyond the frozen request plan']", 1),
            (RUN_STAGE_OLD, RUN_STAGE_NEW, 1),
            ("prefix='control-interface-probe-'", "prefix='progress-subgoal-v1-runtime2-'", 1),
        ]),
        NEW + '/evidence.py': (OLD + '/evidence.py', [
            ("LIVE = 'gpu_progress_subgoal_v1_runtime2_development_probe'",
             "LIVE = 'gpu_progress_subgoal_v1_questionnaire_attempt'", 1),
            ("            result['model_action_selection_evidence'] = bool(result.get('passed'))\n"
             "            result['evidence_scope'] = 'retained-observation development probe; no game progress measured'\n",
             "            result['model_questionnaire_replies_retained'] = bool(result.get('questionnaire'))\n"
             "            result['evidence_scope'] = ('retained questionnaire replies on synthetic transitions; scores, '\n"
             "                                        'completeness and readiness only from the independent evaluator')\n",
             1),
        ]),
        NEW + '/notebook.py': (OLD + '/notebook.py', [
            ("prefix='direct-publisher-smoke-source-'", "prefix='progress-subgoal-v1-source-'", 1),
            ("raise SystemExit('smoke test failed; evidence in /kaggle/working/progress-subgoal-v1-runtime2')",
             "raise SystemExit('questionnaire lifecycle failed; evidence in /kaggle/working/progress-subgoal-v1-runtime2')", 1),
            (NOTEBOOK_CONSTANTS_OLD, NOTEBOOK_CONSTANTS_NEW, 1),
            (NOTEBOOK_CASES_OLD, NOTEBOOK_CASES_NEW, 1),
            (NOTEBOOK_MARKDOWN_OLD, NOTEBOOK_MARKDOWN_NEW, 1),
            ("'title': 'ARC3 Control Interface Action Selection V1 Review'",
             "'title': 'ARC3 Progress Subgoal V1 Runtime2 Review'", 1),
            ('    """This ARC-AGI-3 smoke package must retain its reviewed competition binding."""',
             '    """This ARC-AGI-3 package must retain its reviewed competition binding."""', 1),
            (NOTEBOOK_LOCK_OLD, NOTEBOOK_LOCK_NEW, 1),
        ]),
        NEW + '/launch.py': (OLD + '/launch.py', []),
        NEW + '/rehearsal.py': (OLD + '/rehearsal.py', [('<WHOLE>', REHEARSAL_NEW, 1)]),
        NEW + '/rehearsal_stub.py': (OLD + '/rehearsal_stub.py', [('<WHOLE>', REHEARSAL_STUB_NEW, 1)]),
        package: ('scripts/control_interface_action_selection_v2_package.py', [
            ('"""Direct publisher smoke test packaging (no upload, no reservation, no GPU).',
             '"""progress_subgoal_v1 runtime2 packaging (no upload, no reservation, no GPU).', 1),
            ('review-build --revision 1', 'review-build --revision 5', 1),
            ('review-check --revision 1', 'review-check --revision 5', 1),
            ("prefix='control-interface-review-check-'", "prefix='psv1-runtime2-review-check-'", 1),
            ("    parser.add_argument('--revision', type=int, default=1)",
             "    parser.add_argument('--revision', type=int, default=5)", 1),
            ("    check_sources(ROOT, (folder / 'review-source-lock.json').relative_to(ROOT).as_posix())\n"
             "    for name, digest in lock['artifacts'].items():\n"
             "        if sha256(folder / name) != digest:\n"
             "            raise SystemExit(f'review artifact drift: {name}')\n",
             "    check_sources(ROOT, (folder / 'review-source-lock.json').relative_to(ROOT).as_posix())\n"
             "    for name, digest in lock['artifacts'].items():\n"
             "        if sha256(folder / name) != digest:\n"
             "            raise SystemExit(f'review artifact drift: {name}')\n"
             "    for name, digest in lock.get('review_documents', {}).items():\n"
             "        if sha256(ROOT / name) != digest:\n"
             "            raise SystemExit(f'review document drift: {name}')\n", 1),
        ]),
        embedded: ('scripts/check_control_interface_embedded_inputs.py', [
            ("def check(notebook, package='research.control_interface_action_selection_v1'):\n"
             "    if package not in ('research.control_interface_action_selection_v1', 'research.progress_subgoal_v1_runtime2'):\n",
             "def check(notebook, package='research.progress_subgoal_v1_runtime2'):\n"
             "    if package != 'research.progress_subgoal_v1_runtime2':\n", 1),
            ("prefix='control-interface-extracted-check-'", "prefix='psv1-runtime2-extracted-check-'", 1),
            ("    parser.add_argument('--version', type=int, choices=(1, 2), default=1)\n", '', 1),
            ("    folder = ROOT / f'notebooks/control-interface-action-selection-v{args.version}-review-r{args.revision}'\n"
             "    record = check(json.loads((folder / 'profile.ipynb').read_bytes()),\n"
             "                   f'research.control_interface_action_selection_v{args.version}')\n",
             "    folder = ROOT / f'notebooks/progress-subgoal-v1-runtime2-review-r{args.revision}'\n"
             "    record = check(json.loads((folder / 'profile.ipynb').read_bytes()))\n", 1),
        ]),
    }


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=1) + '\n').encode()


def apply(target, basis_text, replacements, source):
    text = basis_text.removeprefix(OLD_HEADER)
    whole = [r for r in replacements if r[0] == '<WHOLE>']
    if whole:  # rewritten around the basis's structure; the report shows the diff against the basis
        text = whole[0][1]
    else:
        for old, new in GLOBAL:
            text = text.replace(old, new)
        for old, new, count in replacements:
            found = text.count(old)
            if found != count:
                raise ValueError(f'{target}: expected {count} of {old[:80]!r}, found {found}')
            text = text.replace(old, new)
    for residue in RESIDUE:
        if residue in text:
            raise ValueError(f'{target}: unexpected remaining reference {residue!r}')
    return (HEADER.format(source=source, commit=BASIS_COMMIT) + text).encode()


# ------------------------------------------------------------------ the experiment's unchanged sources


def _module_file(root, name):
    parts = name.split('.')
    if parts[0] not in ('research', 'certification', 'scripts', 'agent', 'evaluation'):
        return None
    path = Path(root).joinpath(*parts)
    for candidate in (path.with_suffix('.py'), path / '__init__.py'):
        if candidate.is_file():
            return candidate.relative_to(root).as_posix()
    return None


def _import_nodes(tree, function_level):
    """Import statements executed at import time (never descending into function bodies), or all of them."""
    if function_level:
        return [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    found, stack = [], list(tree.body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            found.append(node)
        elif not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            stack.extend(ast.iter_child_nodes(node))
    return found


def imports(root, name, *, function_level, text=None):
    """Repository modules imported by `name` (at import time only, or also inside functions)."""
    tree = ast.parse(text if text is not None else (Path(root) / name).read_text(encoding='utf-8'))
    package = Path(name).parent.as_posix().replace('/', '.')
    nodes = _import_nodes(tree, function_level)
    found = set()
    for node in nodes:
        if isinstance(node, ast.Import):
            modules = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ''
            if node.level:
                anchor = package.split('.')[:len(package.split('.')) - node.level + 1]
                base = '.'.join(anchor + ([base] if base else []))
            modules = [base] + [f'{base}.{a.name}' for a in node.names]
        else:
            continue
        for module in modules:
            parts = module.split('.')
            for n in range(1, len(parts) + 1):
                found_file = _module_file(root, '.'.join(parts[:n]))
                if found_file:
                    found.add(found_file)
    return found


RUNTIME_MODULES = ('binding', 'run', 'notebook', 'launch', 'evidence', 'runtime_controls', 'questionnaire',
                   'rehearsal', 'rehearsal_stub', '__init__')
DATA_FILES = ('research/progress_subgoal_v1/probes.json', 'research/progress_subgoal_v1/decision_rules.json')


def experiment_sources(root=ROOT, texts=None):
    """The unchanged experiment files reached from the runtime: every import of the successor's runtime modules and
    of the copied controller (including function-level ones), then import-time imports of reused modules.
    `texts` supplies derived module texts not yet written."""
    root = Path(root)
    texts = texts or {}
    own = {f'{NEW}/{m}.py' for m in RUNTIME_MODULES} | set(SMOKE_SHA256)
    own = {n for n in own if n.endswith('.py')}
    reused, queue = set(), []
    for name in sorted(own):
        text = texts[name].decode() if name in texts else None
        queue += sorted(imports(root, name, function_level=True, text=text) - own)
    while queue:
        name = queue.pop()
        if name in reused:
            continue
        reused.add(name)
        queue += sorted(imports(root, name, function_level=False) - own - reused)
    for name in list(reused):  # every package __init__ on the way
        parts = name.split('/')[:-1]
        for n in range(2, len(parts) + 1):
            init = '/'.join(parts[:n]) + '/__init__.py'
            if (root / init).is_file():
                reused.add(init)
    return sorted(reused | set(DATA_FILES))


def lazy_imports_not_packaged(root=ROOT):
    """Function-level imports of reused modules that fall outside the packaged set (never executed by the
    successor's runtime or rehearsal paths; the isolated extracted-payload rehearsal confirms the executed path)."""
    sources = set(experiment_sources(root))
    own = {f'{NEW}/{m}.py' for m in RUNTIME_MODULES} | set(SMOKE_SHA256)
    out = {}
    for name in sorted(s for s in sources if s.endswith('.py')):
        missing = sorted(imports(root, name, function_level=True) - sources - own)
        if missing:
            out[name] = missing
    return out


def r4_bindings(root=ROOT):
    return json.loads((Path(root) / SUPERSEDED_LOCK).read_bytes())['bindings']


# ------------------------------------------------------------------ the protocol


def protocol_record(root=ROOT):
    from research.progress_subgoal_v1_runtime2 import questionnaire as QN
    from research.progress_subgoal_v1_runtime2.runtime_controls import (DECISION_RULES_SHA256, MAXIMUM_MODEL_REQUESTS,
                                                                        experiment_record)
    root = Path(root)
    protocol = json.loads((root / SMOKE / 'protocol.json').read_bytes())
    protocol.update(schema='progress_subgoal_v1_runtime2_protocol', scope=SCOPE, placeholder_prefix='REPLACE_WITH_',
                    kernel_id='REPLACE_WITH_OWNER/arc3-progress-subgoal-v1-runtime2',
                    purpose='progress_subgoal_v1 frozen questionnaire (change, progress and subgoal claims) on the '
                            'verified runtime; zero game actions; scores only from the independent evaluator')
    # As the verified research packages: a dataset-backed private model snapshot (bindings left as placeholders)
    # pinned by its complete tree digest, and prefix caching disabled.
    protocol['model'].update(source_kind='dataset', kaggle_source='REPLACE_WITH_MODEL_OWNER/REPLACE_WITH_MODEL_DATASET/1',
                             mounted_path='REPLACE_WITH_VERIFIED_MODEL_MOUNT',
                             tree_sha256='b480ad92cda91474084c795d2ff64b07a6c477909b22d2784d24abf8fb4ef7df')
    protocol['server']['argv'] = ['--no-enable-prefix-caching' if a == '--enable-prefix-caching' else a
                                  for a in protocol['server']['argv']]
    rules = json.loads((root / 'research/progress_subgoal_v1/decision_rules.json').read_bytes())['package_limits']
    protocol['limits'] = {'authorized_seconds': rules['maximum_reservation_seconds_per_session'],
                          'internal_seconds': rules['internal_seconds'],
                          'admission_cutoff_seconds': rules['admission_cutoff_seconds'],
                          'cleanup_reserve_seconds': rules['cleanup_reserve_seconds'],
                          'installation_seconds': protocol['limits']['installation_seconds'],
                          'model_verification_seconds': protocol['limits']['model_verification_seconds'],
                          'startup_ceiling_seconds': protocol['limits']['startup_ceiling_seconds'],
                          'maximum_attempts': rules['maximum_attempts'], 'automatic_retries': rules['automatic_retries'],
                          'maximum_model_requests': MAXIMUM_MODEL_REQUESTS, 'environment_actions': 0, 'scorecards': 0}
    record = experiment_record(root)
    runtime = protocol['requests']
    protocol['requests'] = runtime[:7] + QN.request_plan(record['scheduled_calls'],
                                                         record['call_timing']['timeout_seconds']) + runtime[7:]
    protocol['experiment'] = dict(record, name='progress_subgoal_v1', decision_rules_sha256=DECISION_RULES_SHA256,
                                  protocol_document='reports/progress_subgoal_v1_protocol_v2.md',
                                  third_arm_decision='keep_two_arms (research/progress_subgoal_v1/third_arm_decision.json)',
                                  evaluation_seed='hash only: research/progress_subgoal_v1/evaluation_seed.json',
                                  decision_partition='withheld (the frozen evaluation build)',
                                  scoring='research/progress_subgoal_v1/score.py, unchanged, via '
                                          'scripts/evaluate_progress_subgoal_v1_runtime2.py')
    return protocol


def proposal_record(protocol):
    return {'status': 'proposal_only_no_approval_no_reservation', 'scope': SCOPE, 'purpose': protocol['purpose'],
            'compute_proposal': protocol['limits'], 'sessions': 1, 'game_actions': 0,
            'new_source_use_compute_review_required': True, 'prior_attempts_reusable': False,
            'supersedes': {'review_lock': SUPERSEDED_LOCK, 'review_lock_sha256': SUPERSEDED_LOCK_SHA256,
                           'note': 'superseded review package of the same experiment on the old runtime; '
                                   'no approval, attempt or reservation exists or is inherited'}}


CHANGES = [
    'separate runtime2 scope, approval/attempt paths and attempt prefix; no inherited approvals, reservations or attempts',
    'shared controller copied byte-identically from the verified runtime (certification/direct_publisher_smoke_v1 at 5a21dd3)',
    'wheels: verified publisher dataset driessmit1/arc3-vllm-h100-wheelhouse-v3 version 1 (flat mount, publisher '
    'metadata hashes), 174 wheels checked against the trusted manifest and installed offline with the trusted '
    'hash-pinned lock; replaces the old two-interpreter install from an unversioned wheelhouse and the competition '
    'game wheels',
    'model: dataset-backed private snapshot of Qwen/Qwen3-VL-30B-A3B-Instruct-FP8 at d9748a51 pinned by tree '
    'b480ad92 (owner/dataset/mount left as REPLACE_WITH_ placeholders); replaces the Kaggle Model attachment',
    'image: pinned Kaggle CPython 3.12 image digest; exactly one RTX PRO 6000 checked before model serving',
    'server argv: the verified runtime argv with --no-enable-prefix-caching (identical to the old derived argv)',
    'lifecycle: the verified single-process controller (phase ceilings, counted request ledger, cutoff alarm, '
    'process-group cleanup, final deadline, evidence manifest) replaces the supervisor/worker/monitor/bridge stack',
    'questionnaire stage: the frozen schedule, requests, admission cutoff, per-call bound and consecutive-timeout '
    'stop imported unchanged; idle checks after timeouts are counted /metrics reads; token parity against the frozen '
    'offline audit; cache disabled verified from the retained server configuration',
    'independent evaluator re-derives requests from the frozen question set and scores with the unchanged scorer',
]


def build(root=ROOT, basis=None):
    """{path: bytes} of every generated file. Derived files need the basis; without it they are omitted."""
    root = Path(root)
    result = {}
    if basis is not None:
        basis = Path(basis)
        for name, digest in BASIS_SHA256.items():
            if sha((basis / name).read_bytes()) != digest:
                raise ValueError('basis drift: ' + name)
        for name, digest in SMOKE_SHA256.items():
            if sha((basis / name).read_bytes()) != digest:
                raise ValueError('basis controller drift: ' + name)

        def derive(sources):
            return {target: apply(target, (basis / source).read_text(encoding='utf-8'), replacements, source)
                    for target, (source, replacements) in derivations(sources).items()}
        # The source list is written into runtime_controls.py; imports do not depend on it, so two passes agree.
        first = derive([])
        sources = experiment_sources(root, first)
        result = derive(sources)
        if experiment_sources(root, result) != sources:
            raise ValueError('experiment source closure did not converge')
        for name in ('trusted_manifest.json', 'trusted_requirements.lock'):
            result[NEW + '/' + name] = (basis / OLD / name).read_bytes()
    return result


def records(root=ROOT, basis=None):
    """protocol.json, proposal.json and derivation.json (after the derived files exist under root)."""
    root = Path(root)
    protocol = protocol_record(root)
    if basis is not None:  # the runtime bindings must equal the verified research package's exactly
        verified = json.loads((Path(basis) / OLD / 'protocol.json').read_bytes())
        for key in ('dataset', 'bundle', 'model', 'runtime', 'server', 'kaggle_image', 'competition', 'sampling',
                    'placeholder_prefix'):
            if protocol[key] != verified[key]:
                raise ValueError('runtime binding differs from the verified package: ' + key)
        if ([r for r in protocol['requests'] if r['kind'] not in ('questionnaire', 'questionnaire_idle_check')]
                != [r for r in verified['requests'] if r['kind'] != 'action_selection']):
            raise ValueError('runtime probe plan differs from the verified package')
    out = {NEW + '/protocol.json': encoded(protocol), NEW + '/proposal.json': encoded(proposal_record(protocol))}
    targets = sorted(derivations(experiment_sources(root)))
    r4 = r4_bindings(root)
    sources = experiment_sources(root)
    derivation = {
        'basis_commit': BASIS_COMMIT, 'basis_ref': BASIS_REF,
        'builder': 'scripts/build_progress_subgoal_v1_runtime2.py',
        'controller_copied_unchanged': dict(SMOKE_SHA256),
        'derived_from_basis': {t: {'basis': derivations(sources)[t][0],
                                   'basis_sha256': BASIS_SHA256[derivations(sources)[t][0]],
                                   'output_sha256': sha((root / t).read_bytes())} for t in targets},
        'trusted_inputs_copied': {NEW + '/' + n: BASIS_SHA256[OLD + '/' + n]
                                  for n in ('trusted_manifest.json', 'trusted_requirements.lock')},
        'protocol_derived_from': {'path': SMOKE + '/protocol.json', 'sha256': SMOKE_SHA256[SMOKE + '/protocol.json'],
                                  'runtime_bindings_equal': OLD + '/protocol.json',
                                  'runtime_bindings_equal_sha256': BASIS_SHA256[OLD + '/protocol.json']},
        'hand_written_adapters': {n: sha((root / n).read_bytes()) for n in ADAPTERS if n != ADAPTERS[-1]},
        'experiment_sources_unchanged': {n: sha((root / n).read_bytes()) for n in sources},
        'experiment_sources_bound_by_r4': sorted(n for n in sources if n in r4),
        'experiment_sources_equal_r4_hashes': all(r4[n] == sha((root / n).read_bytes()) for n in sources if n in r4),
        'lazy_imports_not_packaged': lazy_imports_not_packaged(root),
        'superseded_package': {'review_lock': SUPERSEDED_LOCK, 'review_lock_sha256': SUPERSEDED_LOCK_SHA256,
                               'kept_byte_identical': True},
        'changes': CHANGES, 'scientific_configuration_changed': False, 'preserves_baseline_files': True,
        'gpu_launches': 0, 'provider_calls': 0}
    out[NEW + '/derivation.json'] = encoded(derivation)
    return out


def check(root=ROOT):
    """Without the basis: copied controller, recorded derived outputs, regenerated records and r4 source hashes."""
    root = Path(root)
    problems = []
    for name, digest in SMOKE_SHA256.items():
        if sha((root / name).read_bytes()) != digest:
            problems.append('controller drift: ' + name)
    recorded = json.loads((root / NEW / 'derivation.json').read_bytes())
    for target, row in recorded['derived_from_basis'].items():
        if sha((root / target).read_bytes()) != row['output_sha256']:
            problems.append('derived output drift: ' + target)
    for name, data in records(root).items():
        if (root / name).read_bytes() != data:
            problems.append('generated record drift: ' + name)
    r4 = r4_bindings(root)
    for name in experiment_sources(root):
        if name in r4 and r4[name] != sha((root / name).read_bytes()):
            problems.append('experiment source differs from review r4: ' + name)
    if sha((root / SUPERSEDED_LOCK).read_bytes()) != SUPERSEDED_LOCK_SHA256:
        problems.append('superseded review r4 lock changed')
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--basis', type=Path)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        problems = check(ROOT)
        print(json.dumps({'checked': True, 'problems': problems, 'gpu_launches': 0, 'provider_calls': 0}))
        return 1 if problems else 0
    if args.basis is None:
        parser.error('--basis is required to derive (or use --check)')
    derived = build(ROOT, args.basis)
    drift = []
    for name, data in derived.items():
        path = ROOT / name
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        elif not path.is_file() or path.read_bytes() != data:
            drift.append(name)
    generated = records(ROOT, args.basis)
    for name, data in generated.items():
        path = ROOT / name
        if args.write:
            path.write_bytes(data)
        elif not path.is_file() or path.read_bytes() != data:
            drift.append(name)
    print(json.dumps({'derived_files': len(derived), 'records': len(generated), 'written': args.write,
                      'drift': drift, 'gpu_launches': 0, 'provider_calls': 0}))
    return 1 if drift and not args.write else 0


if __name__ == '__main__':
    raise SystemExit(main())
