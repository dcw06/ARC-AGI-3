"""Derive the Track 2 Stage 1 session packages (A and B) on the verified direct-publisher runtime.

No network, installation, GPU, provider call, approval or reservation. Re-running with --check verifies instead of
writing. Inputs, all committed:
- the verified runtime at 5a21dd3 (origin/wheelhouse-replacement-audit), vendored byte for byte:
  certification/direct_publisher_smoke_v1/ at its own path (imported unchanged), and, as derivation inputs only,
  research/evidence_memory_v1/successor/verified_sources/ (the control-interface v2 package files and scripts that ran on
  GPU: lifecycle, live gate, notebook, launch accounting, evidence, rehearsal, protocol);
- each session's frozen set (probes.json) and pinned-tokenizer audit (token-audit.json), produced separately by
  research/evidence_memory_v1/successor/freeze.py and scripts/audit_evidence_memory_v1_tokens.py;
- the shared withheld-seed commitment (research/evidence_memory_v1/successor/seed-commitment.json).
Each derived source is its reference file with the reference banner replaced, the ordered global renames below, and
that file's own substitutions, each required to match an exact number of times; a residue check refuses leftover
reference names. The study's runner is derived the same way from research/evidence_memory_v1/run/runner.py.
The reused Track 2 modules are those of 107d8b4, except the owner's protocol-freeze amendments (FREEZE_AMENDMENTS:
the recall decoding schema and the three-way margin reading), which tests check against the baseline exactly. Each
protocol names the frozen protocol document, and each review lock binds it with the other review documents. Session
B's launch tooling also requires session A's technical completion (successor/session_order.py); A's is unchanged.

    python scripts/build_evidence_memory_v1_sessions.py           # write
    python scripts/build_evidence_memory_v1_sessions.py --check   # fail on any drift
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.evidence_memory_v1.successor import plan as PL  # noqa: E402

BASIS_COMMIT = '5a21dd339d22ec6e13307722b42dcef0882f6829'
BASIS_BRANCH = 'origin/wheelhouse-replacement-audit'
TRACK2_BASELINE = '107d8b4'
REFERENCE = 'research/evidence_memory_v1/successor/verified_sources'
V2 = 'research/control_interface_action_selection_v2'
SHARED = 'certification/direct_publisher_smoke_v1'
COMMITMENT = 'research/evidence_memory_v1/successor/seed-commitment.json'
BUILDER = 'scripts/build_evidence_memory_v1_sessions.py'
# Every vendored file at the basis commit: origin path -> SHA-256, recorded in the vendored folder's SOURCES.json
# (tests compare each one with the basis commit's object when that commit is available locally).
SOURCES = json.loads((ROOT / REFERENCE / 'SOURCES.json').read_bytes())
REFERENCE_SHA256 = SOURCES['files']
# Track 2 modules the successor reuses unchanged (the scientific configuration and the reviewed run stack).
TRACK2_REUSED = tuple('research/evidence_memory_v1/' + n for n in (
    '__init__.py', 'fidelity.py', 'mutations.py', 'protocol.py', 'readers.py', 'render.py', 'schema.py', 'stage1.py',
    'study.py', 'tokens.py', 'trajectories.py', 'writers.py', 'run/__init__.py', 'run/evaluate.py', 'run/evidence.py',
    'run/final.py', 'run/probes.py', 'run/runner.py', 'run/schedule.py', 'run/score.py', 'run/service.py',
    'run/transport.py', 'run/fake_server.py', 'run/fake_vllm.py', 'run/probes.json'))
# The frozen protocol (owner decisions of October 9, 2026). The draft reports/evidence_memory_v1_protocol_v2.md stays
# unchanged as history.
PROTOCOL_DOCUMENT = 'reports/evidence_memory_v1_protocol_v2_frozen.md'
# The only changes to reused Track 2 modules: the owner's freeze decisions, each the exact change from the 107d8b4 file
# ((old, new, count) applied in order). Tests apply them to the baseline blob and require the committed file; the
# derivation records both hashes. Nothing else in a reused module differs from the baseline.
FREEZE_AMENDMENTS = {
    'research/evidence_memory_v1/stage1.py': (
        'decision 1 (amended October 10, 2026, after the withheld draw): the recall DECODING schema allows exactly the '
        'eight valid answers (vLLM 0.19 refuses uniqueItems; the exact enum also enforces distinct values and '
        '"no_evidence" alone); readers.validate_response is unchanged', (
            ('import hashlib\nimport json\n', 'import hashlib\nimport itertools\nimport json\n', 1),
            ("RECALL_VALUES = P.VALUES + ('no_evidence',)\n",
             "RECALL_VALUES = P.VALUES + ('no_evidence',)\n"
             '# The eight valid recall answers, in canonical order: one to three distinct observed values, or "no_evidence"\n'
             '# alone (protocol v2 frozen, section 2). The recall decoding schema allows exactly these.\n'
             "RECALL_ANSWERS = tuple(c for r in (1, 2, 3) for c in itertools.combinations(P.VALUES, r)) + (('no_evidence',),)\n",
             1),
            ('def response_schema(kind):\n    if kind',
             'def response_schema(kind):\n'
             '    """The decoding schema sent with each request (protocol v2 frozen, section 2). A recall answer is one of the\n'
             '    eight valid answers in canonical order (RECALL_ANSWERS): vLLM 0.19 refuses `uniqueItems`, and the exact enum\n'
             '    lets the decoder enforce distinct values and "no_evidence" alone. Scoring is unchanged:\n'
             '    readers.validate_response applies the same rules to an answer in any order."""\n'
             '    if kind', 1),
            ("                'properties': {'values': {'type': 'array', 'minItems': 1, 'uniqueItems': True,\n"
             "                                          'items': {'type': 'string', 'enum': list(RECALL_VALUES)}}}}\n",
             "                'properties': {'values': {'enum': [list(answer) for answer in RECALL_ANSWERS]}}}\n", 1))),
    'research/evidence_memory_v1/protocol.py': (
        'decision 2: the unsupported-claim margins are read three ways (met / exceeded / not_shown) with unchanged '
        'thresholds; only met permits advancement, as before', (
            ('"""Stage 1 instruments for reports/evidence_memory_v1_protocol_v2.md (Track 2). No model is called; '
             'CPU only.\n',
             '"""Stage 1 instruments for reports/evidence_memory_v1_protocol_v2_frozen.md (Track 2; the draft\n'
             'reports/evidence_memory_v1_protocol_v2.md is kept as history). No model is called; CPU only.\n', 1),
            ('\n\ndef conclusions(result):\n',
             '\n\ndef unsupported_margin(u):\n'
             '    """The three-way reading of the unsupported-claim difference (memory minus recent_raw), protocol v2 '
             'frozen,\n'
             '    section 9: `met` (point <= +0.02 and 95% upper bound <= +0.05), `exceeded` (point > +0.02), '
             '`not_shown` (point\n'
             '    <= +0.02 but upper bound > +0.05: not measured precisely enough to show the margin); `not_estimable` '
             'without an\n'
             '    interval. Only `met` permits advancement, exactly as strict as the earlier two-way rule."""\n'
             "    if u['ci95'] is None:\n"
             "        return 'not_estimable'\n"
             "    if u['estimate'] > UNSUPPORTED_MARGIN_POINT:\n"
             "        return 'exceeded'\n"
             "    return 'met' if u['ci95'][1] <= UNSUPPORTED_MARGIN_UPPER else 'not_shown'\n"
             '\n\ndef conclusions(result):\n', 1),
            ("    u = result['unsupported_difference_memory_minus_recent_raw']\n"
             "    safety = ('not_estimable' if u['ci95'] is None else\n"
             "              'within_margin' if u['estimate'] <= UNSUPPORTED_MARGIN_POINT and u['ci95'][1] <= "
             "UNSUPPORTED_MARGIN_UPPER\n"
             "              else 'outside_margin')\n",
             "    safety = unsupported_margin(result['unsupported_difference_memory_minus_recent_raw'])\n", 1),
            ("    elif out['access_vs_recent_history'] == 'memory_preserves_access' and safety == 'within_margin':\n",
             "    elif out['access_vs_recent_history'] == 'memory_preserves_access' and safety == 'met':\n", 1),
            ("    elif out['access_vs_recent_history'] == 'memory_preserves_access':\n"
             "        out['verdict'] = 'memory_preserves_access_unsupported_claims_outside_margin'\n",
             "    elif out['access_vs_recent_history'] == 'memory_preserves_access' and safety == 'exceeded':\n"
             "        out['verdict'] = 'memory_preserves_access_unsupported_claims_outside_margin'\n"
             "    elif out['access_vs_recent_history'] == 'memory_preserves_access':  # not_shown (or not_estimable)\n"
             "        out['verdict'] = 'memory_preserves_access_unsupported_claims_margin_not_shown'\n", 1))),
}
# Baseline test files changed to cover those decisions (the only other modified baseline files).
FREEZE_AMENDED_TESTS = {
    'tests/test_evidence_memory_v1_stage1.py': 'decision 1: the recall decoding schema is the exact enum of the eight '
                                               'valid answers; every answer it admits scores valid, and duplicates or '
                                               '"no_evidence" with another value still score invalid',
    'tests/test_evidence_memory_v1_protocol.py': 'decision 2: the margin outcome is renamed (exceeded) and every branch '
                                                 'of the three-way reading is tested, boundaries included',
}
SESSION_ORDER = 'research/evidence_memory_v1/successor/session_order.py'  # decision 4: session B's launch tooling


def amended(path, baseline):
    """The baseline bytes of a reused module with its freeze amendment applied."""
    return substitute(path, baseline.decode('utf-8'), FREEZE_AMENDMENTS[path][1]).encode('utf-8')


def baseline_of(path):
    """The 107d8b4 bytes of an amended module, recovered by undoing its amendment (each change is unique)."""
    text = (ROOT / path).read_text(encoding='utf-8')
    for old, new, count in reversed(FREEZE_AMENDMENTS[path][1]):
        text = substitute(path, text, ((new, old, count),))
    return text.encode('utf-8')


def review_documents(s):
    """Hash-bound by each review lock for review and verified by the review check; never in the runtime payload: the
    frozen protocol, the structured-output check and its receipt, the independent evaluator and the pooled analysis,
    the token audit, the builder and the session's package script."""
    return (PROTOCOL_DOCUMENT, 'scripts/check_evidence_memory_v1_structured_outputs.py',
            'reports/evidence_memory_v1_successor/structured_outputs_check_r3.json',
            'research/evidence_memory_v1/successor/evaluate.py', 'research/evidence_memory_v1/successor/final.py',
            'research/evidence_memory_v1/run/evaluate.py', 'research/evidence_memory_v1/run/final.py',
            'scripts/audit_evidence_memory_v1_tokens.py', BUILDER, f'scripts/{s.name}_package.py')


def vendored(origin):
    """The vendored bytes of a reference file, checked against its recorded SHA-256."""
    path = ROOT / (origin if origin.startswith(SHARED + '/') or origin.startswith('tests/') else REFERENCE + '/' + origin)
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != REFERENCE_SHA256[origin]:
        raise ValueError('vendored reference drift: ' + origin)
    return data


def substitute(target, text, substitutions):
    for old, new, count in substitutions:
        found = text.count(old)
        if found != count:
            raise ValueError(f'{target}: expected {count} of {old[:80]!r}, found {found}')
        text = text.replace(old, new)
    return text


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=1) + '\n').encode()


class Session:
    def __init__(self, label):
        spec = PL.SESSIONS[label]
        self.label, self.lower = label, label.lower()
        self.package, self.module, self.scope = spec['package'], spec['module'], spec['scope']
        self.name = self.module.split('.')[-1]  # evidence_memory_v1_session_a
        self.attempt = spec['attempt']

    def renames(self):
        return (('research.control_interface_action_selection_v2', self.module), (V2, self.package),
                ('control_interface_action_selection_v2', self.name),
                ('control-interface-action-selection-v2', self.scope))

    def header(self, origin):
        return (f'# Derived by {BUILDER} from {origin} at {BASIS_COMMIT[:7]} ({BASIS_BRANCH}); '
                'edit the derivation.\n')

    def derive(self, origin, substitutions, target):
        lines = vendored(origin).decode('utf-8').splitlines(keepends=True)
        if lines and lines[0].startswith('# Derived by '):
            lines = lines[1:]
        text = ''.join(lines)
        for old, new in self.renames():
            text = text.replace(old, new)
        text = substitute(target, text, substitutions)
        residue = [n for n in ('control_interface', 'control-interface', 'action_selection', 'action-selection',
                               "r'cia-", 'Milestone E') if n in text]
        if residue:
            raise ValueError(f'{target}: unexpected reference residue {residue}')
        return (self.header(origin) + text).encode()


BINDING_REVIEW_REQUIRED = """# Review documents every review lock must bind; every repository-side gate verifies them (never in the payload).
REVIEW_REQUIRED = ('reports/evidence_memory_v1_protocol_v2_frozen.md', 'research/evidence_memory_v1/successor/evaluate.py',
                   'research/evidence_memory_v1/successor/final.py', 'research/evidence_memory_v1/run/evaluate.py',
                   'research/evidence_memory_v1/run/final.py')
"""
BINDING_CHECK_SOURCES_HEAD = '''def check_sources(root, lock_name, review_documents=True):
    """The reviewed runtime sources and, unless inside the runtime payload, the review documents, by hash."""
'''
BINDING_REVIEW_CHECK = """    if review_documents:
        listed = lock.get('review_documents') or {}
        missing = sorted(set(REVIEW_REQUIRED) - set(listed))
        if missing:
            raise ValueError('review documents incomplete: ' + ', '.join(missing))
        for name, digest in sorted(listed.items()):
            if sha256(resolve(root, name)) != digest:
                raise ValueError('review document drift: ' + name)
"""


def package_files(s, scheduled, maximum):
    """The derived sources of one session package: (target, origin, substitutions)."""
    refused = f"evidence memory v1 session {s.label} live path refused: "
    binding = (
        ('Record C compute authorization and an unconsumed single-attempt reservation. Import is inert."""',
         'Record C compute authorization and an unconsumed single-attempt reservation; for Track 2 Stage 1 also\n'
         'LIVE_ENABLED and the withheld frozen set (refused before any approval is read). Import is inert."""', 1),
        ("ATTEMPT = re.compile(r'cia-[a-zA-Z0-9-]{8,80}')",
         f"ATTEMPT = re.compile(r'{s.attempt}-[a-zA-Z0-9-]{{8,80}}')\n"
         "LIVE_ENABLED = False  # Track 2 Stage 1 is GPU-disabled; enabling it needs a new reviewed, approved revision", 1),
        ("'control-interface action selection live path refused: '", repr(refused), 1),
        ("or limits['maximum_model_requests'] != 131", "or limits['maximum_model_requests'] < 1", 1),
        (f"    required |= {{'research/control_interface_action_selection_v1/cases.json', "
         f"'research/control_interface_action_selection_v1/cases-lock.json', PACKAGE + '/derivation.json', "
         f"PACKAGE + '/token-audit.json'}}\n",
         "    required |= {PACKAGE + '/probes.json', PACKAGE + '/derivation.json', PACKAGE + '/token-audit.json'}\n"
         "    from research.evidence_memory_v1.successor.plan import STUDY_SOURCES\n"
         "    required |= set(STUDY_SOURCES)  # the study phase's live import closure\n", 1),
        ("    if pending:\n        reasons.append('unresolved placeholders: ' + ', '.join(pending))\n    execution = None\n",
         "    if pending:\n        reasons.append('unresolved placeholders: ' + ', '.join(pending))\n"
         "    from .runtime_controls import live_frozen_set_reasons\n"
         "    reasons += live_frozen_set_reasons(root, protocol)\n"
         "    if not LIVE_ENABLED:  # refuse before reading any approval, evidence, reservation or claim\n"
         "        reasons.append('GPU-disabled package: Track 2 Stage 1 has no approved live run (LIVE_ENABLED is False)')\n"
         "        raise LiveRefused(reasons)\n"
         "    execution = None\n", 1),
        (f'reports/{s.name}_package.md', 'reports/evidence_memory_v1_successor/runtime_diff.md', 1),
        # Review documents (r3): verified wherever they exist by design, i.e. the repository checkout (review check,
        # launch tooling, launch-build) and the live independent evaluation. The runtime payload never carries them,
        # so only the in-payload gate (consume, run.live_main) skips them.
        (f"BYTES = 'reports/{s.name}_byte_verification.json'\n",
         f"BYTES = 'reports/{s.name}_byte_verification.json'\n" + BINDING_REVIEW_REQUIRED, 1),
        ("def check_sources(root, lock_name):\n", BINDING_CHECK_SOURCES_HEAD, 1),
        ("            raise ValueError('source drift: ' + name)\n    return lock\n",
         "            raise ValueError('source drift: ' + name)\n" + BINDING_REVIEW_CHECK + "    return lock\n", 1),
        ("def require_live(root=None, need_claim=True):\n",
         "def require_live(root=None, need_claim=True, review_documents=True):\n", 1),
        ("    the launch tooling to create the claim itself.\"\"\"\n",
         "    the launch tooling to create the claim itself. `review_documents=False` is used only inside the runtime\n"
         "    payload, which never carries the review documents; they were verified when the launch package was built.\"\"\"\n",
         1),
        ("        check_sources(root, lock_name)\n        check_approvals(root, lock_name, protocol)\n",
         "        check_sources(root, lock_name, review_documents)\n        check_approvals(root, lock_name, protocol)\n", 1),
        ("    protocol, execution = require_live(root)\n    marker = ",
         "    protocol, execution = require_live(root, review_documents=False)  # inside the runtime payload\n"
         "    marker = ", 1),
    )
    run = (
        ('-> startup probes -> inference -> cancellation probes -> termination and cleanup -> retained evidence.',
         '-> startup probes -> inference -> the Track 2 Stage 1 study phase -> cancellation probes -> termination and\n'
         'cleanup -> retained evidence.', 1),
        ("NOT_ESTABLISHED = ['solving ability, level progress or action usefulness', 'Phase 4 completion', "
         "'throughput or capacity limits',\n                   'behaviour beyond the frozen request plan']",
         "NOT_ESTABLISHED = ['any memory, retention or reading outcome (outcomes exist only in the pooled two-session "
         "analysis)',\n                   'solving ability, level progress or action usefulness', 'Phase 4 completion',\n"
         "                   'throughput or capacity limits', 'behaviour beyond the frozen request plan']", 1),
        (f'        from {s.module}.probe import run_cases\n',
         f'        from research.evidence_memory_v1.successor.study import run_study\n'
         f'        from {s.module}.binding import PACKAGE\n', 1),
        ("        result['action_selection'] = stage('action_selection', lambda: run_cases(experiment_root, client, "
         "evidence, clock))\n        telemetry('after_action_selection')\n",
         "        result['study'] = stage('study', lambda: run_study(experiment_root, PACKAGE, client, evidence, clock))\n"
         "        telemetry('after_study')\n", 1),
        ("prefix='control-interface-probe-'", f"prefix='evidence-memory-session-{s.lower}-'", 1),
        ("    protocol, execution = require_live(root)  # again: nothing below runs unless every condition holds\n",
         "    protocol, execution = require_live(root, review_documents=False)  # again, inside the runtime payload\n", 1),
    )
    controls_old = vendored(V2 + '/runtime_controls.py').decode('utf-8')
    controls_old = controls_old[controls_old.index('from . import probe as P'):controls_old.index('def verify_cache_disabled')]
    for old, new in s.renames():
        controls_old = controls_old.replace(old, new)
    runtime_controls = (
        ('"""Research-specific preconditions layered over the unchanged smoke lifecycle."""',
         '"""Track 2 Stage 1 preconditions layered over the unchanged verified lifecycle (bindings in\n'
         'research/evidence_memory_v1/successor/plan.py)."""', 1),
        (controls_old,
         'from research.evidence_memory_v1.successor import plan as PL\n\n'
         f"PACKAGE = '{s.package}'\n\n\n"
         'def validate_protocol(root, protocol):\n'
         '    """Frozen set, token audit, protocol v2 limits, the counted request plan and prefix caching."""\n'
         '    PL.validate_experiment(root, protocol, PACKAGE)\n\n\n'
         'def live_frozen_set_reasons(root, protocol):\n'
         '    """Only the withheld set built from the committed seed may run live."""\n'
         '    return PL.live_frozen_set_reasons(root, protocol, PACKAGE)\n\n\n', 1),
    )
    markdown = (f'# Track 2 evidence memory v1, Stage 1 session {s.label} (GPU-disabled package)\\n\'\n'
                "                           'One attempt: offline install from the verified flat publisher mount with "
                "our trusted '\n"
                f"                           'hash-pinned requirements, pinned model startup, at most {maximum} counted '\n"
                "                           'model requests (startup, study metrics and cancellation probes included), "
                "cancellation, cleanup and '\n"
                f"                           'retained evidence. {scheduled} scheduled study calls; zero game actions; "
                "technical evaluation only per session. This notebook refuses to run unless the dataset/account and "
                "direct-use evidence, '")
    notebook = (
        ("prefix='direct-publisher-smoke-source-'", f"prefix='evidence-memory-session-{s.lower}-source-'", 1),
        ("raise SystemExit('smoke test failed; evidence in", "raise SystemExit('session lifecycle failed; evidence in", 1),
        ("    names += ['research/control_interface_action_selection_v1/cases.json', "
         "'research/control_interface_action_selection_v1/cases-lock.json', PACKAGE + '/derivation.json', "
         "PACKAGE + '/token-audit.json']\n",
         "    names += [PACKAGE + '/probes.json', PACKAGE + '/derivation.json', PACKAGE + '/token-audit.json']\n"
         "    from research.evidence_memory_v1.successor.plan import STUDY_SOURCES\n"
         "    names += list(STUDY_SOURCES)\n"
         + (f"    names.append('{SESSION_ORDER}')  # the launch tooling's session-A condition\n"
            if s.label == 'B' else ''), 1),
        ("'# Milestone E paired action selection v1 (development observations only)\\n'\n"
         "                           'One attempt: offline install from the verified flat publisher mount with our "
         "trusted '\n"
         "                           'hash-pinned requirements, pinned model startup, at most 131 counted '\n"
         "                           'model requests (startup and cancellation probes included), cancellation, cleanup "
         "and '\n"
         "                           'retained evidence. 120 paired research completions; zero game actions. No solving "
         "or game-progress claim. This notebook refuses to run unless the dataset/account and direct-use evidence, '",
         "'" + markdown, 1),
        ("'ARC3 Control Interface Action Selection V1 Review'", f"'ARC3 Evidence Memory V1 Session {s.label} Review'", 1),
        # The frozen protocol and the review documents are bound by the review lock (not embedded in the payload).
        ('SIZE_GUARD = 900000\n',
         'SIZE_GUARD = 900000\n'
         '# Hash-bound by the review lock and verified by the review check; never part of the runtime payload.\n'
         'REVIEW_DOCUMENTS = (\n' + ''.join(f'    {name!r},\n' for name in review_documents(s)) + ')\n', 1),
        ("            'unresolved_placeholders': pending, 'gpu_enabled': False}\n",
         "            'unresolved_placeholders': pending, 'gpu_enabled': False,\n"
         "            'review_documents': {n: sha256(Path(root) / n) for n in REVIEW_DOCUMENTS}}\n", 1),
    )
    launch = ()
    if s.label == 'B':  # decision 4: B's launch tooling waits for A's technical completion; A's tooling is unchanged
        notebook += (
            ('ROOT, SOURCE, ACCOUNT, PERMISSION, BYTES, evidence_names, load_protocol, require_live, review_lock,\n',
             'ROOT, SOURCE, ACCOUNT, PERMISSION, BYTES, LiveRefused, evidence_names, load_protocol, require_live, '
             'review_lock,\n', 1),
            ('    """The launch package (built in memory). Refuses unless the live gate passes for `root`."""\n'
             '    protocol, execution = require_live(root)\n',
             '    """The launch package (built in memory). Refuses unless the live gate passes for `root` and, for session '
             'B, unless\n'
             "    session A's retained technical evaluation shows A technically complete, bound by hash in this session's "
             'compute\n'
             '    authorization (research/evidence_memory_v1/successor/session_order.py; launch tooling only, never the '
             'live gate)."""\n'
             '    from research.evidence_memory_v1.successor import session_order\n'
             '    try:\n'
             '        protocol, execution = require_live(root)\n'
             '    except LiveRefused as exc:  # name the session-order condition too (checking the record reads no '
             'approval)\n'
             '        raise LiveRefused(exc.reasons + session_order.record_reasons(root)) from exc\n'
             '    order = session_order.reasons(root, COMPUTE)\n'
             '    if order:\n'
             '        raise LiveRefused(order)\n', 1),
        )
        launch = (
            ('(CLAIM, EXECUTION, RECEIPT, LiveRefused, require_live,\n',
             '(CLAIM, COMPUTE, EXECUTION, RECEIPT, LiveRefused, require_live,\n', 1),
            ('new attempt needs a new authorization and reservation."""',
             'new attempt needs a new authorization and reservation.\n\n'
             "Session B only: the claim and the launch package also require session A's retained technical evaluation "
             'to show A\n'
             "technically complete, bound by hash in session B's compute authorization\n"
             '(research/evidence_memory_v1/successor/session_order.py). If A is not technically complete, B is never '
             'launched."""', 1),
            ('    protocol, execution = require_live(root, need_claim=False)\n    try:\n',
             '    protocol, execution = require_live(root, need_claim=False)\n'
             '    from research.evidence_memory_v1.successor import session_order\n'
             '    order = session_order.reasons(root, COMPUTE)\n'
             '    if order:  # session B is never claimed before session A is technically complete\n'
             "        raise LaunchRefused('; '.join(order))\n"
             '    try:\n', 1),
        )
    evidence = (
        (f"LIVE = 'gpu_{s.name}_development_probe'", f"LIVE = 'gpu_{s.name}_stage1_run'", 1),
        ("            result['model_action_selection_evidence'] = bool(result.get('passed'))\n"
         "            result['evidence_scope'] = 'retained-observation development probe; no game progress measured'",
         "            result['study_lifecycle_passed'] = bool(result.get('passed'))\n"
         f"            result['evidence_scope'] = ('Track 2 Stage 1 session {s.label}: technical evidence only; outcomes "
         "only from the pooled '\n                                        'two-session analysis')", 1),
    )
    rehearsal = (
        ('"""Fixture installation plus local scripted HTTP, timeout/cancellation and cleanup. Zero GPU/model calls."""',
         '"""Fixture installation plus local scripted HTTP, timeout/cancellation and cleanup. Zero GPU/model calls.\n'
         'The study phase talks to research/evidence_memory_v1/successor/stub.py (scripted answers, vLLM counters)."""',
         1),
        ('from . import binding, probe, run\n',
         'from . import binding, run\n\n'
         '# Rehearsal limits: the frozen limits shortened for CPU fixtures (the study admission rule is unchanged).\n'
         'REHEARSAL_LIMITS = {\'internal_seconds\': 360, \'admission_cutoff_seconds\': 240, '
         '\'cleanup_reserve_seconds\': 60,\n'
         '                    \'installation_seconds\': 120, \'startup_ceiling_seconds\': 15, '
         '\'model_verification_seconds\': 15}\n\n\n'
         'def rehearsal_limits(root, **overrides):\n'
         '    return {**binding.load_protocol(root)[\'limits\'], **REHEARSAL_LIMITS, **overrides}\n', 1),
        ("def scenario(root, folder, fault='none'):", "def scenario(root, folder, fault='none', latency=0.0, **limits):", 1),
        ("    protocol['limits'].update(internal_seconds=180, admission_cutoff_seconds=150, cleanup_reserve_seconds=30,\n"
         "                             installation_seconds=90, startup_ceiling_seconds=10, model_verification_seconds=10)\n",
         "    protocol['limits'] = rehearsal_limits(root, **limits)\n", 1),
        ("        item['timeout_seconds'] = 1 if fault == 'timeout' and item['kind'] == 'action_selection' else 5\n",
         "        item['timeout_seconds'] = 5\n", 1),
        (f"    argv = lambda py: [py, '-m', '{s.module}.rehearsal_stub',\n"
         "        '--port', str(protocol['server']['port']), '--served', protocol['server']['served_model_name'], "
         "'--research-fault', fault]\n",
         "    argv = lambda py: [py, '-m', 'research.evidence_memory_v1.successor.stub',\n"
         "        '--port', str(protocol['server']['port']), '--served', protocol['server']['served_model_name'],\n"
         "        '--root', str(root), '--package', binding.PACKAGE, '--fault', fault, '--latency', str(latency)]\n", 1),
    )
    init = (('"""Milestone E paired retained-observation development probe; imports have no effects."""',
             f'"""Track 2 evidence memory v1, Stage 1 session {s.label} on the verified runtime (GPU-disabled); '
             'imports have no effects."""', 1),)
    return [(s.package + '/__init__.py', V2 + '/__init__.py', init),
            (s.package + '/binding.py', V2 + '/binding.py', binding),
            (s.package + '/run.py', V2 + '/run.py', run),
            (s.package + '/runtime_controls.py', V2 + '/runtime_controls.py', runtime_controls),
            (s.package + '/notebook.py', V2 + '/notebook.py', notebook),
            (s.package + '/launch.py', V2 + '/launch.py', launch),
            (s.package + '/evidence.py', V2 + '/evidence.py', evidence),
            (s.package + '/rehearsal.py', V2 + '/rehearsal.py', rehearsal)]


def script_files(s):
    package_script = (
        ('"""Direct publisher smoke test packaging (no upload, no reservation, no GPU).',
         f'"""Track 2 Stage 1 session {s.label} packaging (no upload, no reservation, no GPU).', 1),
        ("prefix='control-interface-review-check-'", f"prefix='evidence-memory-session-{s.lower}-review-check-'", 1),
        ("            raise SystemExit(f'review artifact drift: {name}')\n",
         "            raise SystemExit(f'review artifact drift: {name}')\n"
         "    for name, digest in lock.get('review_documents', {}).items():\n"
         "        if sha256(ROOT / name) != digest:\n"
         "            raise SystemExit(f'review document drift: {name}')\n", 1))
    if s.label == 'B':
        package_script += (
            ('      build the launch package; refuses unless every live-gate condition holds\n',
             "      build the launch package; refuses unless every live-gate condition holds and session A's retained\n"
             '      technical evaluation shows A technically complete (session B only; successor/session_order.py)\n',
             1),)
    check_script = (
        ("from certification.direct_publisher_smoke_v1 import preflight as P, install as I\n",
         "from certification.direct_publisher_smoke_v1 import preflight as P, install as I\n"
         "import importlib\n", 1),
        ("    print(json.dumps({'passed': len(artifacts) == len(pins) == 174 and len(seen) == 1,\n"
         "        'default_inputs_loaded': True, 'trusted_wheels': len(artifacts), **result}))\n",
         "    # The live entry points import from the payload alone (the checkout is not on sys.path).\n"
         "    for name in (sys.argv[2] + '.run', sys.argv[2] + '.launch', 'research.evidence_memory_v1.successor.study'):\n"
         "        importlib.import_module(name)\n"
         "    outside = sorted(str(m.__file__) for m in list(sys.modules.values()) if getattr(m, '__file__', None)\n"
         "                     and (m.__name__.startswith(('research', 'certification')))\n"
         "                     and not Path(m.__file__).resolve().is_relative_to(root.resolve()))\n"
         "    loaded = sorted(Path(m.__file__).resolve().relative_to(root.resolve()).as_posix()\n"
         "                    for m in list(sys.modules.values()) if getattr(m, '__file__', None)\n"
         "                    and Path(m.__file__).resolve().is_relative_to(root.resolve()))\n"
         "    print(json.dumps({'passed': len(artifacts) == len(pins) == 174 and len(seen) == 1 and not outside,\n"
         "        'default_inputs_loaded': True, 'trusted_wheels': len(artifacts), 'live_modules_imported': loaded,\n"
         "        'modules_outside_payload': outside, **result}))\n", 1),
        ("def check(notebook, package='research.control_interface_action_selection_v1'):\n"
         f"    if package not in ('research.control_interface_action_selection_v1', '{s.module}'):\n",
         f"def check(notebook, package='{s.module}'):\n    if package != '{s.module}':\n", 1),
        ("prefix='control-interface-extracted-check-'", f"prefix='evidence-memory-session-{s.lower}-extracted-check-'", 1),
        ("    parser.add_argument('--version', type=int, choices=(1, 2), default=1)\n", '', 1),
        ("    folder = ROOT / f'notebooks/control-interface-action-selection-v{args.version}-review-r{args.revision}'\n",
         f"    folder = ROOT / f'notebooks/{s.scope}-review-r{{args.revision}}'\n", 1),
        ("    record = check(json.loads((folder / 'profile.ipynb').read_bytes()),\n"
         "                   f'research.control_interface_action_selection_v{args.version}')\n",
         f"    record = check(json.loads((folder / 'profile.ipynb').read_bytes()), '{s.module}')\n", 1),
    )
    return [(f'scripts/{s.name}_package.py', 'scripts/control_interface_action_selection_v2_package.py', package_script),
            (f'scripts/check_{s.name}_embedded_inputs.py', 'scripts/check_control_interface_embedded_inputs.py',
             check_script)]


def runner_file():
    """successor/runner.py: run/runner.py with the frozen set passed in (the session's, not run/probes.json)."""
    origin = 'research/evidence_memory_v1/run/runner.py'
    lines = (ROOT / origin).read_text(encoding='utf-8').splitlines(keepends=True)
    text = ''.join(lines[1:] if lines[0].startswith('# Derived from ') else lines)
    text = substitute('successor/runner.py', text, (
        ('"""Questionnaire runner (worker interpreter): the frozen call order under admission control.\n',
         '"""Questionnaire runner (the study phase, in the lifecycle\'s interpreter): the frozen call order under '
         'admission control.\n', 1),
        ('from .evidence import RunEvidence, StorageExhausted\n',
         'from research.evidence_memory_v1.run.evidence import RunEvidence, StorageExhausted\n', 1),
        ('from .probes import build_request, load_frozen\n', 'from research.evidence_memory_v1.run.probes import build_request\n', 1),
        ('from .schedule import Admission, call_order, ADMISSION_CUTOFF_SECONDS, PER_CALL_BOUND_SECONDS\n',
         'from research.evidence_memory_v1.run.schedule import (Admission, call_order, ADMISSION_CUTOFF_SECONDS,\n'
         '                                                      PER_CALL_BOUND_SECONDS)\n', 1),
        ('def run(path, service, *, started, kind,', 'def run(path, service, *, frozen_set, started, kind,', 1),
        ('    frozen, probe_set_sha256 = load_frozen()\n',
         '    frozen, probe_set_sha256 = frozen_set  # (frozen set, SHA-256 of its bytes): the session package\'s\n', 1),
        ('    from .evidence import load_verified\n', '    from research.evidence_memory_v1.run.evidence import load_verified\n', 1),
    ))
    return (f'# Derived from {origin} by {BUILDER}; edit the derivation, not this file.\n' + text).encode(), origin


def sha_of(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def protocol_for(s, frozen, frozen_sha, audit_sha, commitment):
    reference = json.loads(vendored(V2 + '/protocol.json'))
    scheduled = sum(len(b['probe_ids']) for b in frozen['schedule'])
    plan = PL.request_plan(reference['requests'], scheduled)
    limits = {**PL.STUDY_LIMITS, **PL.RUNTIME_CEILINGS, 'maximum_model_requests': PL.maximum_requests(plan)}
    protocol = {key: reference[key] for key in ('dataset', 'bundle', 'competition', 'kaggle_image', 'model', 'runtime',
                                                'sampling', 'server')}
    protocol.update(schema=f'{s.name}_protocol', scope=s.scope, placeholder_prefix='REPLACE_WITH_',
                    kernel_id=f'REPLACE_WITH_OWNER/arc3-{s.scope}',
                    purpose=(f'Track 2 evidence memory v1, Stage 1 session {s.label}: frozen reader questions under a '
                             'common token budget; zero game actions; technical evaluation only per session'),
                    protocol_document=PROTOCOL_DOCUMENT, limits=limits, requests=plan,
                    experiment=PL.experiment_section(frozen, frozen_sha, audit_sha, s.package, commitment))
    return protocol, scheduled


def build(root=ROOT):
    commitment = json.loads((ROOT / COMMITMENT).read_bytes())['withheld_seed_sha256']
    result = {}
    runner, runner_origin = runner_file()
    result['research/evidence_memory_v1/successor/runner.py'] = runner
    for label in sorted(PL.SESSIONS):
        s = Session(label)
        frozen_raw = (ROOT / s.package / PL.FROZEN_NAME).read_bytes()
        audit_raw = (ROOT / s.package / PL.AUDIT_NAME).read_bytes()
        frozen = json.loads(frozen_raw)
        protocol, scheduled = protocol_for(s, frozen, hashlib.sha256(frozen_raw).hexdigest(),
                                           hashlib.sha256(audit_raw).hexdigest(), commitment)
        result[s.package + '/protocol.json'] = encoded(protocol)
        maximum = protocol['limits']['maximum_model_requests']
        derived = {}
        for target, origin, substitutions in package_files(s, scheduled, maximum) + script_files(s):
            result[target] = s.derive(origin, substitutions, target)
            derived[target] = origin
        for name in ('trusted_manifest.json', 'trusted_requirements.lock'):
            result[s.package + '/' + name] = (ROOT / SHARED / name).read_bytes()
        result[s.package + '/proposal.json'] = encoded({
            'status': 'proposal_only_no_approval_no_reservation', 'scope': s.scope, 'session': label,
            'purpose': protocol['purpose'], 'compute_proposal': protocol['limits'], 'scheduled_study_calls': scheduled,
            'new_source_use_compute_review_required': True, 'prior_attempts_reusable': False,
            'live_enabled_in_this_package': False})
        result[s.package + '/derivation.json'] = encoded({
            'basis_commit': BASIS_COMMIT, 'basis_branch': BASIS_BRANCH, 'builder': BUILDER,
            'reference_sources': {origin: REFERENCE_SHA256[origin] for origin in sorted(REFERENCE_SHA256)},
            'vendored_reference_folder': REFERENCE, 'shared_runtime': SHARED + ' (byte-identical to the basis commit)',
            'derived': derived, 'study_runner': {'research/evidence_memory_v1/successor/runner.py': runner_origin},
            'track2_baseline_commit': TRACK2_BASELINE,
            'track2_reused_unchanged': {path: sha_of(path) for path in TRACK2_REUSED if path not in FREEZE_AMENDMENTS},
            'protocol_document': PROTOCOL_DOCUMENT,
            'track2_amended_at_protocol_freeze': {
                path: {'decision': decision, 'baseline_sha256': hashlib.sha256(baseline_of(path)).hexdigest(),
                       'sha256': sha_of(path)}
                for path, (decision, _) in sorted(FREEZE_AMENDMENTS.items())},
            'track2_baseline_tests_amended_at_protocol_freeze': dict(sorted(FREEZE_AMENDED_TESTS.items())),
            'session_inputs': {s.package + '/' + PL.FROZEN_NAME: hashlib.sha256(frozen_raw).hexdigest(),
                               s.package + '/' + PL.AUDIT_NAME: hashlib.sha256(audit_raw).hexdigest(),
                               COMMITMENT: sha_of(COMMITMENT)},
            'changes': [
                'runtime only: the verified direct-publisher lifecycle replaces the WS3 supervisor/worker/host/monitor '
                'stack, the phase4 two-interpreter installation and the Kaggle Model binding',
                'publisher dataset driessmit1/arc3-vllm-h100-wheelhouse-v3 version 1 with publisher metadata hashes; '
                'trusted hash-pinned lock and manifest; offline venv install',
                'dataset-backed pinned model snapshot (tree SHA-256 pinned; owner/mount bindings are REPLACE_WITH_ '
                'placeholders); immutable Python 3.12 image; competition binding retained',
                'every model-server HTTP request is counted by the verified ledger; the study adds K0000 and per-call '
                'Q/M/V entries; the cap is the plan worst case',
                'pinned-tokenizer prompt counts come from the offline token audit (transformers cross-check) instead '
                'of an in-run tokenizer; token parity is still enforced per call',
                'separate scope, approvals, claim, receipt and reservation per session; LIVE_ENABLED is False and the '
                'live gate refuses the development stand-in',
                'unchanged by this derivation: prompts, arms, schemas, budgets, seeds and seed procedure, schedule, '
                'admission and stop rules, scoring, the technical-only session report and the pooled analysis',
                'protocol freeze (owner decisions of October 9, 2026; ' + PROTOCOL_DOCUMENT + '), applied to the '
                'reused modules themselves, not by this derivation: the recall decoding schema allows exactly the eight valid answers '
                '(scoring unchanged; request digests and token audits rebuilt, prompt token counts unchanged); the '
                'unsupported-claim margins are read three ways (met / exceeded / not_shown; only met advances)',
                'the review lock binds the frozen protocol and review documents; the protocol names protocol_document']
            + (["session B's launch tooling (claim and launch package) refuses unless session A's retained technical "
                "evaluation shows A technically complete, bound by hash in B's compute authorization "
                '(successor/session_order.py); the per-scope live gate is unchanged'] if label == 'B' else []),
            'scientific_configuration_changed': False,
            'baseline_files_modified': sorted([*FREEZE_AMENDMENTS, *FREEZE_AMENDED_TESTS]),
            'preserves_baseline_files': False})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    artifacts = build()
    drift = []
    for name, data in artifacts.items():
        path = ROOT / name
        if args.check:
            if not path.is_file() or path.read_bytes() != data:
                drift.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    if drift:
        raise SystemExit('derivation drift: ' + ', '.join(drift))
    print(json.dumps({'derived_files': len(artifacts), 'checked': args.check, 'network_calls': 0, 'gpu_launches': 0,
                      'provider_calls': 0}))


if __name__ == '__main__':
    main()
