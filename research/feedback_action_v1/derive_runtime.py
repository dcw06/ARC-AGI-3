"""Derive the feedback-action v1 live gate, notebook packaging, launch accounting and package script from the verified
runtime (branch wheelhouse-replacement-audit, commit 5a21dd3), and check the verified controller files reused verbatim.

The sources ran on one RTX PRO 6000 as the control-interface action-selection v2 package (review lock beeb6719...).
They are not on this branch, so each source is read from its git blob (`git cat-file blob <id>`) and its SHA-256 must
equal the value recorded here before anything is derived. Renames, then each file's counted substitutions, are
applied as in derive.py; a block substitution replaces the text between two anchors that must each occur once. Any
remaining control-interface name fails the derivation. `--check` reports drift; without the source objects (a clone
without that branch) it reports the sources as unavailable rather than passing.

Verbatim reuse (checked, not rewritten):
- certification/direct_publisher_smoke_v1/{__init__,host,install,server,preflight}.py, proposal.json,
  trusted_manifest.json, trusted_requirements.lock: byte-identical to their 5a21dd3 blobs and to the bindings of the
  GPU-run review lock;
- runtime.verify_cache_disabled: the text of runtime_controls.verify_cache_disabled.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
COMMIT = '5a21dd3'
BANNER = '# Derived from {source} at {commit} by research/feedback_action_v1/derive_runtime.py; edit the derivation.\n'
REFERENCE_HEADER = '# Derived by scripts/build_control_interface_action_selection_v2.py; edit the derivation.\n'
RENAMES = (('research.control_interface_action_selection_v2', 'research.feedback_action_v1.live'),
           ('research/control_interface_action_selection_v2', 'research/feedback_action_v1/live'),
           ('control_interface_action_selection_v2', 'feedback_action_v1'),
           ('control-interface-action-selection-v2', 'feedback-action-v1'))
# (path at COMMIT, git blob id, sha256)
SOURCES = {
    'binding': ('research/control_interface_action_selection_v2/binding.py', '43d69e1700a89681896b8c777abe90dde611b017',
                'ff2ddcf04e811f00eb6002485968c88ad1c383eeeb9dfdb01514b1458b18bad1'),
    'notebook': ('research/control_interface_action_selection_v2/notebook.py', 'c12f67ec58740677c7f2990c105ec43239478d68',
                 'a208d642caa0a5c6e5126432ab3a0c034157b224cab117a59224749d2a3e1c15'),
    'launch': ('research/control_interface_action_selection_v2/launch.py', '49ee13ef72c78c3ac5842a1cac7f76b7dc328e8d',
               '1148e4ee138102cc8ada817318aa01643163d101827c43d19c7748b925d7a682'),
    'package': ('scripts/control_interface_action_selection_v2_package.py', '3495b541fc2ee092fed6ff66f76340d74a85cc7d',
                '66f215eb350bc3e30c9cdea1b353046af203a5d00c31a983b41d037602f25b68'),
    'runtime_controls': ('research/control_interface_action_selection_v2/runtime_controls.py',
                         'f9b2957ef7fc9984bf8792732fe330e6fea036fc',
                         'd2e8fa1051de4b63109480f85536913cf1e3171546db4f16eb10bc80339a0603'),
}
# Verified controller files reused byte for byte: path -> (git blob id, sha256 = the GPU-run review-lock binding).
VERBATIM = {
    'certification/direct_publisher_smoke_v1/__init__.py': (
        '7b7dc19651e55056266d8aa22b1e8db3f9f2e554', '08c32bf5bc6167ad1202120f90a00043271310c34896d33188c78e2049eb2665'),
    'certification/direct_publisher_smoke_v1/host.py': (
        '1c2125e842e5ed1db326b09da623184e132fd947', '6eab062887c5ba4460f4a5f953da8b6b17fc7ddf40404ec74e9d10bbb8c1c9a8'),
    'certification/direct_publisher_smoke_v1/install.py': (
        'a9a28d677cfbf36cff9054783b6dfddefba72585', '568ef619fce6fc8ed03eda07e7a240f079e017379e1494f4a6b95672cad0019b'),
    'certification/direct_publisher_smoke_v1/server.py': (
        '5e76ad3b3ef74af57b98c9a2c0eb570cb6ce1628', 'e3cbdf0949f21fc2edb6f8c781a55aaeacf3410aa4f5794e3ebe420f2bcee888'),
    'certification/direct_publisher_smoke_v1/preflight.py': (
        '8d24d0f20cf8678153945bf328e3c937112a4fba', '369a39a09c4f5f97b0d92613c3ecc6aa281779af4721a4154fe98576e4fc3b0d'),
    'certification/direct_publisher_smoke_v1/proposal.json': (
        '468e47192c8ef0ea70b96f2f1a7051a0cb12aeae', 'cb5e1cee9903861e16960664c4d392821fb880e4125c7bce1865ea69573a600c'),
    'certification/direct_publisher_smoke_v1/trusted_manifest.json': (
        'b38f70b767f28351f3c6eb21196a7abb76acd5f9', '91ad9ede70c4fdf027cf5739a828f9063dc07c22c6010a64ebd1af0db8f0462b'),
    'certification/direct_publisher_smoke_v1/trusted_requirements.lock': (
        '89e8d2d7117b3a146308579e0418d9be5232115b', 'ba80d35062245421daf1cae65474281952cc0c44fb46e11cf7f68d0ece496406'),
}
GPU_RUN_REVIEW_LOCK = 'beeb6719ed817e3cb42a9842b03a7c47a2ee75aa87831908520318a54c041dc7'

# ---- review documents (freeze revision r2) ----------------------------------------------------------------------------
# Hash-bound by every review lock and verified by every repository-side gate (review check, launch tooling, launch-build,
# the live independent evaluation). The runtime payload never carries them, so only the in-payload gate skips them.
# They are the frozen protocol text, the independent evaluator's files that are not embedded (live_evaluation.py and
# its closure outside the payload), the derivations, the package script and the structured-output check.
REVIEW_DOCUMENTS = ('reports/feedback_action_v1_protocol_v2_frozen.md', 'research/feedback_action_v1/live_evaluation.py',
                    'research/feedback_action_v1/evaluate.py', 'research/transition_evidence_v1/reference.py',
                    'scripts/evaluate_feedback_action_v1.py', 'research/feedback_action_v1/derive.py',
                    'research/feedback_action_v1/derive_runtime.py', 'scripts/feedback_action_v1_package.py',
                    'scripts/check_feedback_action_v1_structured_outputs.py',
                    'reports/feedback_action_v1/structured_outputs_check_r2.json')
BINDING_REVIEW_REQUIRED = ('# Review documents every review lock must bind; every repository-side gate verifies them (never '
                           'in the payload).\nREVIEW_REQUIRED = (\n'
                           + ''.join(f'    {name!r},\n' for name in REVIEW_DOCUMENTS) + ')\n')
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

# ---- binding.py: the live gate ---------------------------------------------------------------------------------------
LOAD_PROTOCOL = '''def load_protocol(root=ROOT):
    """The runtime binding (runtime.json, validated by runtime.load) and the unchanged experiment protocol's
    lifecycle, which must agree with it. `limits` is the gate's name for the runtime lifecycle."""
    from .runtime import load
    protocol = load(root)
    experiment = read_json(root, EXPERIMENT)
    if experiment.get('id') != 'feedback-action-v1' or experiment.get('arms') != ['baseline', 'candidate']:
        raise ValueError('not the feedback-action v1 experiment protocol')
    life, frozen = protocol['lifecycle'], experiment['limits']
    if (frozen['maximum_policy_calls'] != life['maximum_policy_calls'] or frozen['internal_seconds'] != life[
            'internal_seconds'] or frozen['cleanup_reserve_seconds'] != life['cleanup_reserve_seconds']
            or frozen['pair_admission_seconds'] != life['pair_admission_seconds']
            or frozen['provider_timeout_seconds'] != life['authorized_seconds']):
        raise ValueError('runtime lifecycle differs from the experiment protocol')
    from .owner_gates import load as load_gates
    load_gates(Path(root) / GATES)
    protocol['limits'] = life
    return protocol


'''

SESSION_ONE = '''SESSION_ONE_FIELDS = ('attempt_id', 'evaluation', 'evaluation_sha256')


def session_names(root):
    """The session-1 evaluation a session-2 attempt depends on (embedded in its launch package); else nothing."""
    execution = read_json(root, EXECUTION)
    return [execution['session_1']['evaluation']] if execution.get('session') == 2 else []


def check_session_one(root, execution):
    """Session 2 runs only after session 1 was independently evaluated and stopped under none of F2a and F3-F6
    (protocol v2 section 10). The evaluation is bound by hash; its verdict is the evaluator's, never a label."""
    link = execution.get('session_1')
    if not isinstance(link, dict) or set(link) != set(SESSION_ONE_FIELDS) or not ATTEMPT.fullmatch(
            str(link.get('attempt_id'))):
        raise ValueError('session 2 must bind its session-1 evaluation')
    if sha256(resolve(root, link['evaluation'])) != link['evaluation_sha256']:
        raise ValueError('session-1 evaluation drift')
    evaluation = read_json(root, link['evaluation'])
    study = evaluation.get('evaluation') or {}
    if (evaluation.get('mode') != 'live' or evaluation.get('attempt_id') != link['attempt_id']
            or study.get('session') != 1 or study.get('session_2_permitted') is not True):
        raise ValueError('session 1 is not a live, evaluated session that permits session 2')
    return evaluation


def check_reservation(root, lock_name):
'''

BINDING = (
    ('"""Protocol loading and the live-path gate: unresolved placeholders, reviewed sources, separate source approval,\n'
     'Record C compute authorization and an unconsumed single-attempt reservation. Import is inert."""',
     '"""Feedback-action v1 live-path gate (successor runtime v1): unresolved placeholders, reviewed sources, separate\n'
     'source approval, compute authorization bound to the runtime binding, the unchanged experiment protocol and the\n'
     'owner-gate record, account/permission/byte evidence for the publisher dataset, and an unconsumed single-attempt\n'
     'reservation for one session (session 2 also needs session 1\'s independent evaluation). Import is inert."""', 1),
    ("PROTOCOL = PACKAGE + '/protocol.json'\n",
     "PROTOCOL = PACKAGE + '/runtime.json'  # the runtime binding; the unchanged experiment protocol is EXPERIMENT\n"
     "EXPERIMENT = PACKAGE + '/protocol.json'\n"
     "GATES = PACKAGE + '/owner_gates.json'\n", 1),
    ("COMPUTE_LIMITS = ('authorized_seconds', 'internal_seconds', 'cleanup_reserve_seconds', 'admission_cutoff_seconds',\n"
     "                  'maximum_attempts', 'maximum_model_requests', 'automatic_retries')",
     "COMPUTE_LIMITS = ('authorized_seconds', 'internal_seconds', 'cleanup_reserve_seconds', 'installation_seconds',\n"
     "                  'startup_ceiling_seconds', 'pair_admission_seconds', 'maximum_attempts', 'maximum_policy_calls',\n"
     "                  'maximum_canaries', 'automatic_retries')", 1),
    ('ROOT = Path(__file__).resolve().parents[2]\n',
     'ROOT = Path(__file__).resolve().parents[3]  # one directory deeper than the source\n', 1),
    ("ATTEMPT = re.compile(r'cia-[a-zA-Z0-9-]{8,80}')", "ATTEMPT = re.compile(r'fa1-[a-zA-Z0-9-]{8,80}')", 1),
    ("'control-interface action selection live path refused: '", "'feedback-action v1 live path refused: '", 1),
    (('def load_protocol(root=ROOT):\n', 'def unresolved(protocol):'), LOAD_PROTOCOL, 'block'),
    (("    required = {p.relative_to(root).as_posix()", "    missing = sorted(required - set(lock.get('bindings', {})))"),
     "    from .notebook import source_names\n    required = set(source_names(root))  # every embedded file\n", 'block'),
    ("    if compute.get('protocol_sha256') != sha256(resolve(root, PROTOCOL)):\n"
     "        raise ValueError('compute authorization not bound to the protocol')\n",
     "    if compute.get('protocol_sha256') != sha256(resolve(root, PROTOCOL)):\n"
     "        raise ValueError('compute authorization not bound to the runtime binding')\n"
     "    if compute.get('experiment_protocol_sha256') != sha256(resolve(root, EXPERIMENT)):\n"
     "        raise ValueError('compute authorization not bound to the experiment protocol')\n"
     "    if compute.get('owner_gates_sha256') != sha256(resolve(root, GATES)):\n"
     "        raise ValueError('compute authorization not bound to the owner-gate record')\n", 1),
    ('def check_reservation(root, lock_name):\n', SESSION_ONE, 1),
    ("        raise ValueError('attempt id')\n",
     "        raise ValueError('attempt id')\n"
     "    if execution.get('session') not in (1, 2):\n"
     "        raise ValueError('the execution lock must name session 1 or 2')\n"
     "    if execution['session'] == 2:\n"
     "        check_session_one(root, execution)\n", 1),
    ('reports/feedback_action_v1_package.md', 'reports/feedback_action_v1_successor_package.md', 1),
    # Freeze revision r2: the review documents.
    ("GATES = PACKAGE + '/owner_gates.json'\n", "GATES = PACKAGE + '/owner_gates.json'\n" + BINDING_REVIEW_REQUIRED, 1),
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

# ---- notebook.py: review snapshot and launch artifacts ---------------------------------------------------------------
CELL = """CELL = '''import base64, hashlib, json, lzma, pathlib, shutil, sys, tempfile, time
started = time.monotonic()  # one clock: installation start through cleanup
MODE = 'live'
source = pathlib.Path(tempfile.mkdtemp(prefix='feedback-action-v1-source-'))
try:
    payload = json.loads(lzma.decompress(base64.b85decode({packed!r})))
    bindings = {bindings!r}
    if set(payload) != set(bindings):
        raise ValueError('embedded source inventory differs from its bindings')
    for name, value in payload.items():
        data = base64.b64decode(value)
        if hashlib.sha256(data).hexdigest() != bindings[name]:
            raise ValueError('embedded source drift: ' + name)
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    sys.path.insert(0, str(source))
    from scripts.feedback_action_v1_launch import notebook_entry
    receipt = notebook_entry(source, started, MODE)  # live: the gate refuses here, before installation, model or GPU
    print(json.dumps({{k: receipt.get(k) for k in ('session', 'study_status', 'error', 'elapsed_seconds')}}))
finally:
    if source.exists():
        shutil.rmtree(source)
'''


"""

SOURCE_NAMES = '''def source_names(root=ROOT):
    """Every embedded file: the static import closure of the first cell, the game interpreter and the model
    interpreter (runtime.ENTRIES), and the data files the embedded code reads."""
    from .runtime import DATA_FILES, ENTRIES, closure
    names = set(DATA_FILES)
    for entries in ENTRIES.values():
        names.update(closure(entries, root)[0])
    return sorted(names)


'''

REVIEW_TEXT = (
    "                           '# Feedback-action v1: one session on the verified runtime (review snapshot)\\n'\n"
    "                           'Hypothesis testing on three exposed development games (s5i5, ls20, sk48): one block '\n"
    "                           'of six episodes (24 actions, 32 decision calls each), at most 192 policy calls and one '\n"
    "                           'canary. Offline hash-pinned installation of the model interpreter from the verified '\n"
    "                           'publisher mount and of the game interpreter from the competition wheels, the pinned '\n"
    "                           'model snapshot, no automatic retry, no scored submission. GPU disabled. This notebook '\n"
    "                           'refuses to run unless the dataset/account and direct-use evidence, source approval, '\n"
    "                           'compute authorization and an unconsumed one-session reservation are all present and '\n"
    "                           'match.'},\n")

NOTEBOOK = (
    ("ROOT, SOURCE, ACCOUNT, PERMISSION, BYTES, evidence_names, load_protocol, require_live, review_lock,",
     "ROOT, SOURCE, ACCOUNT, PERMISSION, BYTES, evidence_names, load_protocol, require_live, review_lock, session_names,",
     1),
    (("CELL = '''import base64", 'def source_names(root=ROOT):'), CELL, 'block'),
    (('def source_names(root=ROOT):', 'def image_metadata(protocol):'), SOURCE_NAMES, 'block'),
    (("                           '# Milestone E paired action selection v1", "                          {'cell_type': 'code'"),
     REVIEW_TEXT, 'block'),
    ("'title': 'ARC3 Control Interface Action Selection V1 Review'", "'title': 'ARC3 Feedback Action V1 Review'", 1),
    ("RESERVATION, CLAIM, *evidence_names(root))}", "RESERVATION, CLAIM, *evidence_names(root),\n"
     "                                                                    *session_names(root))}", 1),
    # Freeze revision r2: every review lock binds the review documents by hash.
    ("review_lock, session_names,", "review_lock, session_names,\n" + " " * 58 + "REVIEW_REQUIRED,", 1),
    ("            'unresolved_placeholders': pending, 'gpu_enabled': False}\n",
     "            'unresolved_placeholders': pending, 'gpu_enabled': False,\n"
     "            'review_documents': {n: hashlib.sha256((Path(root) / n).read_bytes()).hexdigest()\n"
     "                                 for n in REVIEW_REQUIRED}}\n", 1),
)

LAUNCH = ()

# ---- scripts/feedback_action_v1_package.py ----------------------------------------------------------------------------
PACKAGE_DOC = '''"""Feedback-action v1 packaging (no upload, no reservation, no approval, no GPU).

  python scripts/feedback_action_v1_package.py review-build --revision 1
      freeze notebooks/feedback-action-v1-review-r<N>/ (GPU disabled; review snapshot, not an approval)
  python scripts/feedback_action_v1_package.py review-check --revision 1
      execute that notebook's code locally with no GPU and a decoy nvidia-smi; it must stop at the live gate before
      any installation, model or GPU activity; writes reports/feedback_action_v1_review_check_r<N>.json
  python scripts/feedback_action_v1_package.py review-rehearse --revision 1
      execute the same cell with only its MODE token switched to 'rehearsal': the full connected session (scripted
      model, real offline engine) from the extracted payload; writes reports/feedback_action_v1_review_rehearsal_r<N>.json
  python scripts/feedback_action_v1_package.py launch-build
      build the launch package; refuses unless every live-gate condition holds
"""'''

REHEARSE = '''def review_rehearse(revision, session=1, seconds=2400):
    """The frozen cell with only MODE switched: one connected rehearsal session from the extracted payload."""
    from research.grounded_action_v1.engine import restore_game_mount
    from scripts.evaluate_feedback_action_v1 import evaluate_output
    folder = review_folder(revision)
    code = json.loads((folder / 'profile.ipynb').read_text(encoding='utf-8'))['cells'][1]['source']
    if code.count("MODE = 'live'\\n") != 1:
        raise SystemExit('frozen notebook must run in live mode only')
    base = Path.home() / 'fa1-review'
    base.mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(dir=base))
    games = restore_game_mount(work / 'games')
    (work / 'working').mkdir()
    env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'VIRTUAL_ENV') and not k.startswith('FA1_')}
    env.update(FA1_REHEARSAL='1', CUDA_VISIBLE_DEVICES='', FA1_REHEARSAL_WORKING=str(work / 'working'),
               FA1_REHEARSAL_GAMES=str(games), FA1_REHEARSAL_SECONDS=str(seconds), FA1_REHEARSAL_SESSION=str(session),
               TMPDIR=str(work))
    for key in ('FA1_REHEARSAL_GAME_PYTHON', 'FA1_REHEARSAL_MODEL_PYTHON', 'FA1_REHEARSAL_TOKENIZER',
                'FA1_REHEARSAL_GRAMMAR'):
        if os.environ.get(key):
            env[key] = os.environ[key]
    cell_file = work / 'review_cell.py'
    cell_file.write_text(code.replace("MODE = 'live'\\n", "MODE = 'rehearsal'\\n"), encoding='utf-8')
    process = subprocess.run([sys.executable, '-I', str(cell_file)], cwd=work, env=env, capture_output=True,
                             text=True, timeout=seconds + 600)
    output = work / 'working' / 'feedback-action-v1'
    value = evaluate_output(output, mode='rehearsal', rehearsal_seconds=seconds) if output.exists() else None
    leftovers = sorted(p.name for p in work.iterdir() if p.name.startswith('feedback-action-v1-source-'))
    receipt = {'schema': 'feedback_action_v1_review_rehearsal_v1', 'review_revision': revision,
               'review_lock_sha256': sha256(folder / 'review-source-lock.json'), 'session': session,
               'evidence_class': 'scripted_cpu_rehearsal_from_extracted_payload', 'gpu_compatibility_evidence': False,
               'interpreters': {'game': env.get('FA1_REHEARSAL_GAME_PYTHON', 'review interpreter'),
                                'model': env.get('FA1_REHEARSAL_MODEL_PYTHON', 'review interpreter')},
               'pinned_tokenizer': bool(env.get('FA1_REHEARSAL_TOKENIZER')),
               'grammar_checked': env.get('FA1_REHEARSAL_GRAMMAR') == '1',
               'exit_code': process.returncode, 'extracted_source_left': leftovers,
               'technically_complete': bool(value and value['technically_complete']),
               'lifecycle_errors': value['lifecycle_errors'] if value else ['no output'],
               'evaluation': {k: value['evaluation'][k] for k in ('replay_passed', 'session', 'failure_rules',
                                                                  'session_2_permitted', 'technical_validity')}
               if value and value['evaluation'] else None,
               'stderr_tail': process.stderr[-1500:]}
    receipt['passed'] = process.returncode == 0 and receipt['technically_complete'] and not leftovers
    out = ROOT / f'reports/feedback_action_v1_review_rehearsal_r{revision}.json'
    out.write_text(json.dumps(receipt, indent=1) + '\\n', encoding='utf-8')
    return receipt


def main():
'''

PACKAGE = (
    (('"""Direct publisher smoke test packaging', '\nimport argparse'), PACKAGE_DOC, 'block'),
    ("prefix='control-interface-review-check-'", "prefix='feedback-action-v1-review-check-'", 1),
    ('def main():\n', REHEARSE, 1),
    ("    parser.add_argument('command', choices=['review-build', 'review-check', 'launch-build'])\n",
     "    parser.add_argument('command', choices=['review-build', 'review-check', 'review-rehearse', 'launch-build'])\n"
     "    parser.add_argument('--session', type=int, default=1)\n", 1),
    ("    try:\n        launch_artifacts(ROOT)\n",
     "    if args.command == 'review-rehearse':\n"
     "        receipt = review_rehearse(args.revision, args.session)\n"
     "        print(json.dumps({k: receipt[k] for k in ('passed', 'exit_code', 'technically_complete', 'lifecycle_errors',\n"
     "                                                   'evaluation')}, indent=1))\n"
     "        return 0 if receipt['passed'] else 1\n"
     "    try:\n        launch_artifacts(ROOT)\n", 1),
)

DERIVED = {
    'research/feedback_action_v1/live/binding.py': ('binding', BINDING),
    'research/feedback_action_v1/live/notebook.py': ('notebook', NOTEBOOK),
    'research/feedback_action_v1/live/launch.py': ('launch', LAUNCH),
    'scripts/feedback_action_v1_package.py': ('package', PACKAGE),
}


class SourceUnavailable(RuntimeError):
    pass


def blob(name):
    path, blob_id, digest = SOURCES[name]
    try:
        data = subprocess.run(['git', 'cat-file', 'blob', blob_id], cwd=ROOT, capture_output=True, check=True,
                              timeout=60).stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise SourceUnavailable(f'{path} at {COMMIT} (blob {blob_id}) is not available in this clone') from exc
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f'{path}: source blob differs from its recorded SHA-256')
    return data.decode('utf-8')


def derive_one(target):
    name, substitutions = DERIVED[target]
    text = blob(name).removeprefix(REFERENCE_HEADER)
    for old, new in RENAMES:
        text = text.replace(old, new)
    for old, new, count in substitutions:
        if count == 'block':
            start, end = old
            for anchor in (start, end):
                if text.count(anchor) != 1:
                    raise ValueError(f'{target}: anchor {anchor[:50]!r} must occur once, found {text.count(anchor)}')
            i, j = text.index(start), text.index(end)
            if j <= i:
                raise ValueError(f'{target}: block anchors out of order')
            text = text[:i] + new + text[j:]
            continue
        found = text.count(old)
        if found != count:
            raise ValueError(f'{target}: expected {count} of {old[:70]!r}, found {found}')
        text = text.replace(old, new)
    if 'control_interface' in text or 'control-interface' in text or 'Control Interface' in text:
        raise ValueError(f'{target}: unexpected remaining control-interface reference')
    return BANNER.format(source=SOURCES[name][0], commit=COMMIT) + text


def derive():
    return {target: derive_one(target) for target in DERIVED}


def verbatim_problems(root=ROOT):
    """Reused controller files that are not byte-identical to their recorded blobs and review-lock bindings."""
    problems = []
    for name, (blob_id, digest) in VERBATIM.items():
        data = (Path(root) / name).read_bytes()
        header = f'blob {len(data)}\0'.encode()
        if hashlib.sha1(header + data).hexdigest() != blob_id or hashlib.sha256(data).hexdigest() != digest:
            problems.append(name)
    return problems


def function_text(source, name):
    import ast
    tree = ast.parse(source)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    return '\n'.join(source.splitlines()[node.lineno - 1:node.end_lineno])


def copied_function_problems(root=ROOT):
    """runtime.verify_cache_disabled must be the verified runtime's function, character for character."""
    own = function_text((Path(root) / 'research/feedback_action_v1/live/runtime.py').read_text(encoding='utf-8'),
                        'verify_cache_disabled')
    return [] if own == function_text(blob('runtime_controls'), 'verify_cache_disabled') else [
        'research/feedback_action_v1/live/runtime.py: verify_cache_disabled']


def record():
    """The derivation record (research/feedback_action_v1/live/derivation.json)."""
    from research.feedback_action_v1 import derive as harness
    value = {
        'schema': 'feedback_action_v1_runtime_derivation_v1',
        'status': 'successor_runtime_v1_derivation_no_authority',
        'verified_runtime': {'branch': 'wheelhouse-replacement-audit', 'commit': COMMIT,
                             'gpu_run_review_lock_sha256': GPU_RUN_REVIEW_LOCK,
                             'gpu_runs': 'control-interface action selection v1 (review r2) and v2 (review r1), one '
                                         'RTX PRO 6000 each, both technically passed with cleanup; zero game actions'},
        'verbatim': {name: {'git_blob': b, 'sha256': d, 'source': f'{name} at {COMMIT}'}
                     for name, (b, d) in VERBATIM.items()},
        'derived_from_verified_runtime': {
            target: {'source': SOURCES[name][0], 'source_git_blob': SOURCES[name][1], 'source_sha256': SOURCES[name][2],
                     'substitutions': len(DERIVED[target][1]), 'builder': 'research/feedback_action_v1/derive_runtime.py'}
            for target, (name, _) in DERIVED.items()},
        'copied_function': {'research/feedback_action_v1/live/runtime.py:verify_cache_disabled': {
            'source': SOURCES['runtime_controls'][0], 'source_sha256': SOURCES['runtime_controls'][2]}},
        'derived_from_action_effect_history_v1': {
            target: {'source': source, 'source_sha256': hashlib.sha256((ROOT / source).read_bytes()).hexdigest(),
                     'substitutions': len(subs), 'builder': 'research/feedback_action_v1/derive.py'}
            for target, (source, subs) in harness.DERIVED.items()},
        'hand_written': ['research/feedback_action_v1/live/runtime.py', 'research/feedback_action_v1/live/runtime.json',
                         'research/feedback_action_v1/live/authority.py', 'research/feedback_action_v1/live/rehearsal.py',
                         'research/feedback_action_v1/live/owner_gates.py',
                         'research/feedback_action_v1/live/owner_gates.json',
                         'research/feedback_action_v1/live/game_requirements.lock',
                         'research/feedback_action_v1/live_evaluation.py'],
        'game_requirements_lock': {'derived_from': 'reports/phase4_v2_offline_package.json (wheels/*: names, versions '
                                                   'and SHA-256 of the 31 competition wheels)',
                                   'resolution': 'the six game pins resolve to exactly these 31 wheels (pip --dry-run, '
                                                 'offline, from the committed archive copy of the same wheels)'},
        'unchanged_science': ['research/feedback_action_v1/adapter.py', 'research/feedback_action_v1/evidence.py',
                              'research/feedback_action_v1/evaluate.py', 'research/feedback_action_v1/live/protocol.json',
                              'research/feedback_action_v1/live/fake_server.py'],
    }
    return value


def stale():
    drift = [t for t, text in derive().items()
             if not (ROOT / t).is_file() or (ROOT / t).read_text(encoding='utf-8') != text]
    drift += verbatim_problems() + copied_function_problems()
    path = ROOT / 'research/feedback_action_v1/live/derivation.json'
    if not path.is_file() or path.read_bytes() != encoded(record()):
        drift.append('research/feedback_action_v1/live/derivation.json')
    return drift


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=1) + '\n').encode()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    if parser.parse_args().check:
        try:
            drift = stale()
        except SourceUnavailable as exc:
            raise SystemExit('sources unavailable (not a pass): ' + str(exc))
        if drift:
            raise SystemExit('derived or reused files differ from the derivation: ' + ', '.join(drift))
        print(f'{len(DERIVED)} derived files, {len(VERBATIM)} verbatim files and 1 copied function match')
        sys.exit(0)
    problems = verbatim_problems()
    if problems:
        raise SystemExit('verbatim controller files differ from their recorded blobs: ' + ', '.join(problems))
    for target, text in derive().items():
        (ROOT / target).write_text(text, encoding='utf-8', newline='\n')
    (ROOT / 'research/feedback_action_v1/live/derivation.json').write_bytes(encoded(record()))
    print(f'wrote {len(DERIVED)} derived files and the derivation record')
