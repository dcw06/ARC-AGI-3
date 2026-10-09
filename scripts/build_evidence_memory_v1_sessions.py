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
         "    names += list(STUDY_SOURCES)\n", 1),
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
            (s.package + '/launch.py', V2 + '/launch.py', ()),
            (s.package + '/evidence.py', V2 + '/evidence.py', evidence),
            (s.package + '/rehearsal.py', V2 + '/rehearsal.py', rehearsal)]


def script_files(s):
    package_script = (
        ('"""Direct publisher smoke test packaging (no upload, no reservation, no GPU).',
         f'"""Track 2 Stage 1 session {s.label} packaging (no upload, no reservation, no GPU).', 1),
        ("prefix='control-interface-review-check-'", f"prefix='evidence-memory-session-{s.lower}-review-check-'", 1))
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
                    limits=limits, requests=plan,
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
            'track2_reused_unchanged': {path: sha_of(path) for path in TRACK2_REUSED},
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
                'unchanged: prompts, arms, schemas, budgets, seeds and seed procedure, schedule, admission and stop '
                'rules, scoring, the technical-only session report and the pooled analysis'],
            'scientific_configuration_changed': False, 'preserves_baseline_files': True})
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
