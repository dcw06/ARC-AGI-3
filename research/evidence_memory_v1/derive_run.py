"""Derive the Track 2 Stage 1 run package from the reviewed WS3 questionnaire v1 stack (GPU-disabled).

The WS3 files (themselves derived from evidence comprehension v3, which ran live as ecv3-089bf11f) are reused, never
edited. Each derived file is its WS3 source with WS3's banner removed, the global renames below applied in order,
and that file's own substitutions, each required to match an exact number of times. A residue check refuses any
remaining WS3 name. `--check` (and tests/test_evidence_memory_v1_run.py) fails on any drift.

Derived files live in research/evidence_memory_v1/run/ (runtime, launcher, rehearsal, evaluator) and tests/.
Hand-written (not derived): run/{__init__,probes,score,schedule,service,fake_server,evidence,transport}.py, which
adapt the Stage 1 frozen set (stage1.py) or re-export reviewed objects unchanged.

GPU-disabled: the derived authority refuses every live request before reading any approval (`LIVE_ENABLED = False`);
no source approval, compute authorization or reservation exists for Stage 1.

    python -m research.evidence_memory_v1.derive_run          # write the derived files
    python -m research.evidence_memory_v1.derive_run --check  # fail on drift
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
BANNER = '# Derived from {source} by research/evidence_memory_v1/derive_run.py; edit the derivation, not this file.\n'
GLOBAL = (('research/ws3_questionnaire_v1/', 'research/evidence_memory_v1/run/'),
          ('research.ws3_questionnaire_v1', 'research.evidence_memory_v1.run'),
          ('scripts/ws3_questionnaire_v1_launch.py', 'research/evidence_memory_v1/run/launch.py'),
          ('scripts.ws3_questionnaire_v1_launch', 'research.evidence_memory_v1.run.launch'),
          ('scripts.evaluate_ws3_questionnaire_v1', 'research.evidence_memory_v1.run.evaluate'),
          ('scripts.rehearse_ws3_questionnaire_v1', 'research.evidence_memory_v1.run.rehearse'),
          ('scripts/check_ws3_questionnaire_v1.py', 'a diagnostics harness (not derived for Track 2)'),
          ('ws3-questionnaire-v1', 'evidence-memory-v1-stage1'),
          ('WS3Q_', 'EM1S_'),
          ('ws3q-', 'em1s-'),
          ('ws3_questionnaire_v1', 'evidence_memory_v1_stage1'),
          ('evidence-ws3 questionnaire v1', 'evidence memory v1 stage 1'),
          ('ws3 questionnaire v1', 'evidence memory v1 stage 1'))
DEPTH_2 = ('ROOT = Path(__file__).resolve().parents[2]', 'ROOT = Path(__file__).resolve().parents[3]', 1)
DEPTH_1 = ('ROOT = Path(__file__).resolve().parents[1]', 'ROOT = Path(__file__).resolve().parents[3]', 1)

SESSION_A_CALLS, SESSION_A_PASS_1, MAX_SESSION_CALLS = 2896, 2592, 2896


def _slow_latencies():
    from research.evidence_memory_v1.run import rehearsal_timing
    return rehearsal_timing.slow_latencies()


SLOW = _slow_latencies()

REQUIRED_OLD = """REQUIRED_SOURCE = {'research/evidence_memory_v1/run/' + name for name in
                   ('authority.py', 'probes.py', 'probes.json', 'score.py', 'schedule.py', 'transport.py',
                    'service.py', 'host.py', 'worker.py', 'runner.py', 'monitor.py', 'resources.py', 'supervisor.py',
                    'evidence.py', 'fake_server.py')}
REQUIRED_SOURCE |= {'research/transition_evidence_v1/' + name for name in  # the questionnaire and its records
                    ('questionnaire.py', 'score.py', 'transition.py', 'reference.py', 'vocabulary.py', 'fixtures.py')}
"""
REQUIRED_NEW = """REQUIRED_SOURCE = {'research/evidence_memory_v1/run/' + name for name in
                   ('__init__.py', 'authority.py', 'probes.py', 'probes.json', 'score.py', 'schedule.py',
                    'transport.py', 'service.py', 'host.py', 'worker.py', 'runner.py', 'monitor.py', 'resources.py',
                    'supervisor.py', 'evidence.py', 'fake_server.py', 'fake_vllm.py', 'rehearsal_timing.py',
                    'evaluate.py')}
REQUIRED_SOURCE |= {'research/evidence_memory_v1/' + name for name in  # the Stage 1 question set and its scorer
                    ('__init__.py', 'stage1.py', 'protocol.py', 'readers.py', 'render.py', 'schema.py', 'fidelity.py',
                     'trajectories.py', 'writers.py', 'tokens.py')}
REQUIRED_SOURCE |= {'research/transition_evidence_v2/' + name for name in ('transition.py', 'vocabulary.py')}
REQUIRED_SOURCE |= {'research/transition_evidence_v1/' + name for name in ('transition.py', 'vocabulary.py')}
REQUIRED_SOURCE |= {'research/ws3_questionnaire_v1/evidence.py'}  # WS3's committed-state recovery, re-exported
"""
GATE_OLD = """    try:
        root = Path(root)
        review = _read(root, REVIEW)"""
GATE_NEW = """    try:
        if not LIVE_ENABLED:  # GPU-disabled package: refuse before reading any approval or touching a GPU
            raise ValueError('Stage 1 has no approved live run')
        root = Path(root)
        review = _read(root, REVIEW)"""

# The connected rehearsals use the reviewed stack's POSIX-only parts (fcntl, process groups, Unix sockets).
POSIX_IMPORTS_OLD = """from research.evidence_memory_v1.run.evidence import forge, load_unverified_calls, truncate
from research.evidence_memory_v1.run.evaluate import evaluate_output
from research.evidence_memory_v1.run.rehearse import rehearse
"""
POSIX_IMPORTS_NEW = """if os.name == 'posix':  # the reviewed run stack is POSIX-only (fcntl, process groups, Unix sockets)
    from research.evidence_memory_v1.run.evidence import forge, load_unverified_calls, truncate
    from research.evidence_memory_v1.run.evaluate import evaluate_output
    from research.evidence_memory_v1.run.rehearse import rehearse
"""
CORRECT_OLD = "['families']['withheld']['raw_evidence']['progress_status']['correct']"
CORRECT_NEW = "['answers']['pass_1']['correct']"

DERIVED = {
    'research/evidence_memory_v1/run/authority.py': ('research/ws3_questionnaire_v1/authority.py', (
        DEPTH_2,
        ("REVIEW = 'notebooks/evidence-memory-v1-stage1-review-r2/review-source-lock.json'",
         "REVIEW = 'notebooks/evidence-memory-v1-stage1-review-r1/review-source-lock.json'", 1),
        ("'maximum_questionnaire_calls': 5616,", f"'maximum_questionnaire_calls': {MAX_SESSION_CALLS},", 1),
        ("          'holdout_runs': 0}\n",
         "          'holdout_runs': 0}\nLIVE_ENABLED = False  # Track 2 Stage 1: GPU-disabled; no live run is approved\n", 1),
        (REQUIRED_OLD, REQUIRED_NEW, 1),
        (GATE_OLD, GATE_NEW, 1),
    )),
    'research/evidence_memory_v1/run/host.py': ('research/ws3_questionnaire_v1/host.py', (DEPTH_2,)),
    # v1's fake vLLM server decides "canary" by a user message not starting with '{' (true of every v1-WS3 question,
    # false for Stage 1's 'Evidence:' prose). Unchanged, it counted every Stage 1 question as the canary, so the
    # questionnaire call counter never advanced and no fault keyed to HANG_AT ever fired. The canary test becomes an
    # overridable method with v1's rule as its default; run/fake_server.py identifies the canary by request hash.
    'research/evidence_memory_v1/run/fake_vllm.py': ('research/evidence_comprehension_v1/fake_server.py', (
        ("        is_canary = not request['messages'][1]['content'].startswith('{')\n",
         "        is_canary = self.is_canary(request)\n", 1),
        ("    def handle(self, handler, request):\n",
         "    def is_canary(self, request):\n"
         "        \"\"\"v1's rule; a question set whose user messages are not JSON overrides it.\"\"\"\n"
         "        return not request['messages'][1]['content'].startswith('{')\n\n"
         "    def latency_for(self, number):\n"
         "        \"\"\"v1's rule: the same injected latency for every questionnaire call.\"\"\"\n"
         "        return self.latency\n\n"
         "    def handle(self, handler, request):\n", 1),
        # The injected latency may depend on the questionnaire call number (run/rehearsal_timing.py).
        ("        until = time.monotonic() + (STUCK_SECONDS if hang else self.latency)\n",
         "        until = time.monotonic() + (STUCK_SECONDS if hang else self.latency_for(number))\n", 1),
    )),
    'research/evidence_memory_v1/run/worker.py': ('research/ws3_questionnaire_v1/worker.py', (
        DEPTH_2,
        # Rehearsal only, derived from the frozen schedule (run/rehearsal_timing.py): pass 1 alone, or the repeat
        # pass alone, outlasts the cutoff even with zero overhead. The repeat fault slows only the repeat calls, so
        # it must reach the fake server: it joins the faults the worker forwards to the host.
        ("SLOW_LATENCY = {'slow_withheld_pass_1': 0.13, 'slow_withheld_pass_2': 0.06}",
         "SLOW_LATENCY = {{'slow_withheld_pass_1': {slow_withheld_pass_1}, 'slow_withheld_pass_2': "
         "{slow_withheld_pass_2}}}  # derived: run/rehearsal_timing.py".format(**SLOW), 1),
        ("               'trickle_metrics', 'http_error', 'late_reply')\n",
         "               'trickle_metrics', 'http_error', 'late_reply', 'slow_withheld_pass_2')\n", 1),
    )),
    'research/evidence_memory_v1/run/runner.py': ('research/ws3_questionnaire_v1/runner.py', ()),
    'research/evidence_memory_v1/run/resources.py': ('research/ws3_questionnaire_v1/resources.py', ()),
    'research/evidence_memory_v1/run/monitor.py': ('research/ws3_questionnaire_v1/monitor.py', ()),
    'research/evidence_memory_v1/run/supervisor.py': ('research/ws3_questionnaire_v1/supervisor.py', (DEPTH_2,)),
    'research/evidence_memory_v1/run/launch.py': ('scripts/ws3_questionnaire_v1_launch.py', (DEPTH_1,)),
    'research/evidence_memory_v1/run/rehearse.py': ('scripts/rehearse_ws3_questionnaire_v1.py', (DEPTH_1,)),
    'research/evidence_memory_v1/run/evaluate.py': ('scripts/evaluate_ws3_questionnaire_v1.py', ()),
    'tests/test_evidence_memory_v1_run_connected.py': ('tests/test_ws3_questionnaire_v1_connected.py', (
        (POSIX_IMPORTS_OLD, POSIX_IMPORTS_NEW, 1),
        ("class Rehearsals(unittest.TestCase):",
         "@unittest.skipUnless(os.name == 'posix', 'the reviewed run stack is POSIX-only')\n"
         "class Rehearsals(unittest.TestCase):", 1),
        ("{'answered': 5616}", f"{{'answered': {SESSION_A_CALLS}}}", 1),
        (CORRECT_OLD, CORRECT_NEW, 3),
        ("probes[c['probe_id']]['family'] == 'progress_status'", "probes[c['probe_id']]['kind'] == 'recall'", 1),
        ("probes[c['probe_id']]['condition'] == 'raw_evidence'", "probes[c['probe_id']]['arm'] == 'recent_raw'", 1),
        ("json.loads(c['response']) == {'answer': probes[c['probe_id']]['key']})",
         "json.loads(c['response']) == probes[c['probe_id']]['key'])", 1),
        ("            wrong = 'unknown' if probes[flip['probe_id']]['key'] == 'confirmed' else 'confirmed'",
         "            wrong = ({'values': ['changed_then_returned']}\n"
         "                     if probes[flip['probe_id']]['key'] != {'values': ['changed_then_returned']}\n"
         "                     else {'values': ['no_observed_change']})", 1),
        ("v.update(response=json.dumps({'answer': wrong}))", "v.update(response=json.dumps(wrong))", 1),
        ("('incomplete', 'interrupted_evidence', 5616)", f"('incomplete', 'interrupted_evidence', {SESSION_A_CALLS})", 1),
        ("truncate(truncated / 'worker/run', 2500)", f"truncate(truncated / 'worker/run', {SESSION_A_PASS_1})", 1),
        ("calls_recorded=2500", f"calls_recorded={SESSION_A_PASS_1}", 1),
        ("track = next(p['track'] for p in", "track = next('questionnaire' for p in", 1),
    )),
}
ALLOWED_RESIDUE = ('research/ws3_questionnaire_v1/evidence.py',)


def derive_one(target):
    source, substitutions = DERIVED[target]
    lines = (ROOT / source).read_text(encoding='utf-8').splitlines(keepends=True)
    if lines and lines[0].startswith('# Derived from '):
        lines = lines[1:]
    text = ''.join(lines)
    for old, new in GLOBAL:
        text = text.replace(old, new)
    for old, new, count in substitutions:
        found = text.count(old)
        if found != count:
            raise ValueError(f'{target}: expected {count} of {old[:70]!r}, found {found}')
        text = text.replace(old, new)
    residue = text
    for allowed in ALLOWED_RESIDUE:
        residue = residue.replace(allowed, '')
    if any(name in residue for name in ('ws3_questionnaire', 'ws3-questionnaire', 'WS3Q_', 'ws3q-',
                                        'scripts/evaluate_ws3', 'scripts/rehearse_ws3')):
        raise ValueError(f'{target}: unexpected remaining WS3 reference')
    return BANNER.format(source=source) + text


def derive():
    return {target: derive_one(target) for target in DERIVED}


def stale():
    return [t for t, text in derive().items()
            if not (ROOT / t).is_file() or (ROOT / t).read_text(encoding='utf-8') != text]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    if parser.parse_args().check:
        drift = stale()
        if drift:
            raise SystemExit('derived files differ from the derivation: ' + ', '.join(drift))
        print(f'{len(DERIVED)} derived files match the derivation')
        sys.exit(0)
    for target, text in derive().items():
        (ROOT / target).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / target).write_text(text, encoding='utf-8', newline='\n')
    print(f'wrote {len(DERIVED)} derived files')
