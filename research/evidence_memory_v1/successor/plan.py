"""Session constants, the counted request plan, the token audit and the experiment binding of the Track 2 Stage 1
successor packages (hand-written; shared by both session packages, the builder, the evaluator and the tests).

Nothing scientific is defined here. Prompts, arms, schemas, the common token budget, the frozen set and its schedule
come from research/evidence_memory_v1/stage1.py and protocol.py; per-call timing, admission and the
consecutive-timeout stop from research/evidence_memory_v1/run/schedule.py (v1's reviewed rules); scoring and the
technical report from run/score.py; the pooled analysis from run/final.py. This module only binds them to the
verified direct-publisher runtime (certification/direct_publisher_smoke_v1), whose ledger counts every HTTP request
to the model server. Each scheduled study call n may issue:
  Q{n:05d}  its chat completion (POST; the frozen 60 s call timeout applies);
  M{n:05d}  one metrics read after an answer (the per-call prefix-cache check from the server's counters);
  V{n:05d}  metrics reads after a timeout (server-idle verification, polled every 0.25 s within its window);
and K0000 is one metrics read before the first study call (prefix caching verified from the counters after the
startup canary). `maximum_model_requests` is the plan's worst case: an answered call issues two requests, a
timed-out call one completion and at most IDLE_READS metrics reads.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SESSIONS = {
    'A': {'package': 'research/evidence_memory_v1_session_a', 'module': 'research.evidence_memory_v1_session_a',
          'scope': 'evidence-memory-v1-session-a', 'attempt': 'em1a'},
    'B': {'package': 'research/evidence_memory_v1_session_b', 'module': 'research.evidence_memory_v1_session_b',
          'scope': 'evidence-memory-v1-session-b', 'attempt': 'em1b'},
}
FROZEN_NAME, AUDIT_NAME = 'probes.json', 'token-audit.json'
SEED_PLACEHOLDER = 'REPLACE_WITH_WITHHELD_SEED_SHA256'
AUDIT_SCHEMA = 'evidence_memory_v1_session_token_audit'
PINNED_TOKENIZER = {'model': 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8', 'revision': 'd9748a51ae66354c4dad665aab2c71f26cf2c8cd',
                    'transformers': '4.57.6', 'tokenizers': '0.22.2'}
PROMPT_TOKEN_CEILING, CONTEXT_TOKENS = 60000, 65536  # the reviewed service's pre-transport admission ceilings
# Protocol v2 section 12 (unchanged): per-session reservation, lifecycle, cutoff, reserve, one attempt, no retry.
STUDY_LIMITS = {'authorized_seconds': 3600, 'internal_seconds': 3300, 'cleanup_reserve_seconds': 300,
                'admission_cutoff_seconds': 3000, 'maximum_attempts': 1, 'automatic_retries': 0,
                'environment_actions': 0, 'scorecards': 0}
# The verified runtime's own phase ceilings (installation, model verification, server startup), unchanged.
RUNTIME_CEILINGS = {'installation_seconds': 900, 'model_verification_seconds': 600, 'startup_ceiling_seconds': 900}
REHEARSAL_TIMING = (2.0, 1, 3.0)  # run/worker.timing('rehearsal'): call timeout, teardown, idle window
METRICS_TIMEOUT_SECONDS = 5  # research/evidence_comprehension_v1/transport.METRICS_READ_SECONDS
IDLE_POLL_SECONDS = 0.25  # research/evidence_comprehension_v1/transport.verify_idle's polling pause
VERIFIED_PREFIX = ('S1', 'S2', 'S3', 'I1', 'I2', 'I3', 'I4')  # the verified lifecycle's startup and inference probes
VERIFIED_SUFFIX = ('C1', 'C2', 'C3')  # its cancellation probes, after the study

# The study phase's live import closure (beyond the session package and certification/direct_publisher_smoke_v1).
# tests/test_evidence_memory_v1_successor.py extracts each review notebook and imports the live entry points from the
# payload alone, so a missing module fails there rather than on a GPU.
STUDY_SOURCES = tuple(sorted({
    'research/evidence_memory_v1/__init__.py', 'research/evidence_memory_v1/fidelity.py',
    'research/evidence_memory_v1/protocol.py', 'research/evidence_memory_v1/readers.py',
    'research/evidence_memory_v1/render.py', 'research/evidence_memory_v1/schema.py',
    'research/evidence_memory_v1/stage1.py', 'research/evidence_memory_v1/tokens.py',
    'research/evidence_memory_v1/trajectories.py', 'research/evidence_memory_v1/writers.py',
    'research/evidence_memory_v1/run/__init__.py', 'research/evidence_memory_v1/run/evidence.py',
    'research/evidence_memory_v1/run/probes.py', 'research/evidence_memory_v1/run/schedule.py',
    'research/evidence_memory_v1/run/score.py', 'research/evidence_memory_v1/run/transport.py',
    'research/evidence_memory_v1/successor/__init__.py', 'research/evidence_memory_v1/successor/plan.py',
    'research/evidence_memory_v1/successor/runner.py', 'research/evidence_memory_v1/successor/service.py',
    'research/evidence_memory_v1/successor/study.py',
    'research/transition_evidence_v1/__init__.py', 'research/transition_evidence_v1/transition.py',
    'research/transition_evidence_v1/vocabulary.py', 'research/transition_evidence_v2/__init__.py',
    'research/transition_evidence_v2/transition.py', 'research/transition_evidence_v2/vocabulary.py',
    'research/ws3_questionnaire_v1/__init__.py', 'research/ws3_questionnaire_v1/evidence.py',
    'research/evidence_comprehension_v2/__init__.py', 'research/evidence_comprehension_v2/evidence.py',
    'research/evidence_comprehension_v2/schedule.py', 'research/evidence_comprehension_v1/__init__.py',
    'research/evidence_comprehension_v1/evidence.py', 'research/evidence_comprehension_v1/probes.py',
    'research/evidence_comprehension_v1/schedule.py', 'research/evidence_comprehension_v1/transport.py',
    'research/action_effect_history_v1/__init__.py', 'research/action_effect_history_v1/contract.py',
    'research/action_effect_history_v1/service.py', 'research/action_effect_v1/__init__.py',
    'research/action_effect_v1/records.py'}))


def session_of(package):
    for label, spec in SESSIONS.items():
        if spec['package'] == package:
            return label
    raise ValueError('not a Track 2 session package: ' + str(package))


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def timing(mode):
    """Per-call timing the study phase uses: the frozen live values, or run/worker.timing's rehearsal values."""
    from research.evidence_memory_v1.run import schedule as S
    if mode == 'live':
        timeout, teardown, verify = S.PER_CALL_TIMEOUT_SECONDS, S.TEARDOWN_SECONDS, S.CANCELLATION_VERIFY_SECONDS
    elif mode == 'rehearsal':
        timeout, teardown, verify = REHEARSAL_TIMING
    else:
        raise ValueError('mode must be live or rehearsal')
    return {'timeout': timeout, 'teardown': teardown, 'verify': verify,
            'bound': timeout + teardown + verify + S.BRIDGE_MARGIN_SECONDS}


def idle_reads():
    """Most metrics reads one idle verification can issue at the live timing (one read, then one per poll)."""
    live = timing('live')
    return 1 + math.ceil((live['teardown'] + live['verify']) / IDLE_POLL_SECONDS)


def call_order(frozen):
    from research.evidence_memory_v1.run.schedule import call_order as order
    return order(frozen)


def study_requests(scheduled_calls):
    """The study phase's planned HTTP requests (ledger entries), in the order they can first be issued."""
    rows = [{'id': 'K0000', 'kind': 'study_metrics', 'method': 'GET', 'path': '/metrics',
             'timeout_seconds': METRICS_TIMEOUT_SECONDS}]
    reads = idle_reads()
    for n in range(scheduled_calls):
        rows += [{'id': f'Q{n:05d}', 'kind': 'study_completion', 'method': 'POST', 'path': '/v1/chat/completions',
                  'timeout_seconds': timing('live')['timeout']},
                 {'id': f'M{n:05d}', 'kind': 'study_metrics', 'method': 'GET', 'path': '/metrics',
                  'timeout_seconds': METRICS_TIMEOUT_SECONDS},
                 {'id': f'V{n:05d}', 'kind': 'study_idle_verification', 'method': 'GET', 'path': '/metrics',
                  'timeout_seconds': METRICS_TIMEOUT_SECONDS, 'max_issues': reads}]
    return rows


def split_reference(requests):
    """(prefix, suffix) of a verified plan: everything before its research requests and everything after."""
    ids = [r['id'] for r in requests]
    prefix = [r for r in requests if r['id'] in VERIFIED_PREFIX]
    suffix = [r for r in requests if r['id'] in VERIFIED_SUFFIX]
    if ([r['id'] for r in prefix] != list(VERIFIED_PREFIX) or [r['id'] for r in suffix] != list(VERIFIED_SUFFIX)
            or ids[:len(prefix)] != list(VERIFIED_PREFIX) or ids[len(ids) - len(suffix):] != list(VERIFIED_SUFFIX)):
        raise ValueError('the verified request plan no longer has its startup, inference and cancellation probes')
    return prefix, suffix


def request_plan(reference_requests, scheduled_calls):
    prefix, suffix = split_reference(reference_requests)
    return prefix + study_requests(scheduled_calls) + suffix


def maximum_requests(plan):
    return sum(item.get('max_issues', 1) for item in plan)


def load_frozen(root, package):
    raw = (Path(root) / package / FROZEN_NAME).read_bytes()
    return json.loads(raw), sha256_bytes(raw)


def scheduled_requests(frozen):
    """[(index, pass_id, probe_id, request)] in the frozen call order."""
    from research.evidence_memory_v1.run.probes import build_request
    contexts = {c['context_id']: c for c in frozen['contexts']}
    probes = {p['probe_id']: p for p in frozen['probes']}
    return [(n, pass_id, probe_id, build_request(contexts[probes[probe_id]['context_id']], probes[probe_id]))
            for n, (_, pass_id, probe_id) in enumerate(call_order(frozen))]


def request_sha256(request):
    from research.action_effect_history_v1.service import request_hash
    return request_hash(request)


def audit_rows(frozen):
    """The token audit's identity columns: one row per scheduled call, in call order."""
    return [{'index': n, 'pass_id': pass_id, 'probe_id': probe_id, 'request_sha256': request_sha256(request)}
            for n, pass_id, probe_id, request in scheduled_requests(frozen)]


def validate_audit(audit, frozen, frozen_sha256):
    """The token audit must cover exactly the scheduled requests of this frozen set, with pinned-tokenizer counts
    inside the reviewed ceilings and pure-Python parity. Returns {request_sha256: prompt_tokens}."""
    from research.evidence_memory_v1 import protocol as P
    rows = audit.get('requests')
    if (audit.get('schema') != AUDIT_SCHEMA or audit.get('passed') is not True or audit.get('session') != frozen['session']
            or audit.get('frozen_set_sha256') != frozen_sha256 or audit.get('tokenizer') != PINNED_TOKENIZER
            or not isinstance(rows, list)):
        raise ValueError('token audit missing, failed or not bound to this frozen set and tokenizer')
    expected = audit_rows(frozen)
    if [{k: r.get(k) for k in ('index', 'pass_id', 'probe_id', 'request_sha256')} for r in rows] != expected:
        raise ValueError('token audit rows differ from the scheduled requests')
    counts = {}
    for row in rows:
        tokens = row.get('prompt_tokens')
        if (type(tokens) is not int or not 0 < tokens <= PROMPT_TOKEN_CEILING
                or tokens + P.MAX_TOKENS > CONTEXT_TOKENS or row.get('pure_python_prompt_tokens') != tokens
                or counts.setdefault(row['request_sha256'], tokens) != tokens):
            raise ValueError('token audit count outside the ceilings, without parity or inconsistent')
    return counts


def experiment_section(frozen, frozen_sha256, audit_sha256, package, withheld_seed_sha256=SEED_PLACEHOLDER):
    """The protocol's experiment binding for one session package (the builder writes it; the gate re-derives it)."""
    from research.evidence_memory_v1 import protocol as P, stage1 as ST
    from research.evidence_memory_v1.run import schedule as S, score as SC
    passes = {block['pass']: len(block['probe_ids']) for block in frozen['schedule']}
    live = timing('live')
    return {'version': ST.VERSION, 'session': frozen['session'], 'groups': frozen['groups'],
            'frozen_set': package + '/' + FROZEN_NAME, 'frozen_set_sha256': frozen_sha256,
            'case_source': frozen['case_source'], 'frozen_seed_sha256': frozen['seed_sha256'],
            'withheld_seed_sha256': withheld_seed_sha256,
            'token_audit': package + '/' + AUDIT_NAME, 'token_audit_sha256': audit_sha256,
            'scheduled_calls': sum(passes.values()), 'passes': passes,
            'arms': list(ST.ARM_ORDER), 'primary_arms': list(P.ARMS), 'reference_arm': P.REFERENCE,
            'max_tokens': P.MAX_TOKENS, 'temperature': 0, 'request_seed': 0,
            'prompt_token_ceiling': PROMPT_TOKEN_CEILING, 'context_tokens': CONTEXT_TOKENS,
            'system_sha256': hashlib.sha256(P.SYSTEM.encode()).hexdigest(), 'prefix_caching': False,
            'per_call_seconds': live, 'max_consecutive_timeouts': S.MAX_CONSECUTIVE_TIMEOUTS,
            'invalid_rate_max': SC.INVALID_RATE_MAX,
            'analysis': 'technical only per session (run/score.py); pooled analysis once on A and B (run/final.py)'}


def validate_experiment(root, protocol, package):
    """Every Track 2 binding of a session protocol; raises ValueError on any drift."""
    from research.evidence_memory_v1 import stage1 as ST
    label = session_of(package)
    frozen, digest = load_frozen(root, package)
    audit_raw = (Path(root) / package / AUDIT_NAME).read_bytes()
    experiment = protocol.get('experiment') or {}
    if (frozen.get('session') != label or frozen.get('version') != ST.VERSION or frozen.get('model') != ST.MODEL
            or frozen.get('case_source') not in ST.CASE_SOURCES):
        raise ValueError('frozen set does not belong to this session package')
    validate_audit(json.loads(audit_raw), frozen, digest)
    seed = experiment.get('withheld_seed_sha256')
    if not (seed == SEED_PLACEHOLDER or (isinstance(seed, str) and len(seed) == 64
                                         and all(c in '0123456789abcdef' for c in seed))):
        raise ValueError('withheld seed commitment must be the placeholder or a SHA-256')
    expected = experiment_section(frozen, digest, sha256_bytes(audit_raw), package, seed)
    if experiment != expected:
        drift = sorted(k for k in set(expected) | set(experiment) if expected.get(k) != experiment.get(k))
        raise ValueError('frozen experiment configuration drift: ' + ', '.join(drift))
    limits = protocol['limits']
    if any(limits.get(k) != v for k, v in {**STUDY_LIMITS, **RUNTIME_CEILINGS}.items()):
        raise ValueError('session limits differ from protocol v2 section 12 or the verified runtime ceilings')
    plan = protocol['requests']
    if plan != request_plan(plan, experiment['scheduled_calls']):
        raise ValueError('counted request plan drift')
    if limits.get('maximum_model_requests') != maximum_requests(plan):
        raise ValueError('maximum_model_requests is not the plan worst case')
    argv = protocol['server']['argv']
    if argv.count('--no-enable-prefix-caching') != 1 or '--enable-prefix-caching' in argv:
        raise ValueError('prefix caching must be explicitly disabled')
    if (protocol['sampling'] != {'seed': 0, 'temperature': 0}
            or protocol['server']['served_model_name'] != ST.MODEL or protocol['model']['model_id'] != ST.MODEL):
        raise ValueError('sampling or served model differs from the frozen requests')
    return frozen, digest


def live_frozen_set_reasons(root, protocol, package):
    """Why the committed frozen set may not run live (empty when it may). Only the withheld set built from the
    committed seed may reach a model; the development stand-in never does."""
    reasons = []
    try:
        frozen, digest = load_frozen(root, package)
    except (OSError, ValueError) as exc:
        return [f'frozen set unreadable: {exc}']
    experiment = protocol.get('experiment') or {}
    if frozen.get('case_source') != 'withheld' or experiment.get('case_source') != 'withheld':
        reasons.append(f"frozen set case source is {frozen.get('case_source')!r}, not withheld "
                       '(owner gate: draw the withheld seed and build the frozen set)')
    commitment = experiment.get('withheld_seed_sha256')
    if commitment == SEED_PLACEHOLDER or frozen.get('seed_sha256') != commitment:
        reasons.append('frozen set seed does not match the committed withheld seed SHA-256')
    if experiment.get('frozen_set_sha256') != digest:
        reasons.append('frozen set differs from the protocol binding')
    return reasons
