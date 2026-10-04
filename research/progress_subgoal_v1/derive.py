"""Derive the progress_subgoal_v1 runner from the reviewed WS3 questionnaire v1 stack (GPU-disabled; nothing frozen).

Pattern of scripts/derive_ws3_questionnaire_v1.py: each derived file is its WS3 source with WS3's banner line removed,
the global renames below, and that file's own substitutions, each required to match an exact number of times. The
WS3 sources are read, never edited; their SHA-256 at derivation time is recorded in SOURCE_SHA256 so any later change
to them is detected (tests). WS3's runtime itself derives from evidence comprehension v3, which ran live as attempt
ecv3-089bf11f.

Derived (exact copies plus counted substitutions): authority, host, worker, runner, resources, monitor, supervisor,
evidence (WS3's r2 recovery loader), and the WS3 launch, rehearse and evaluate scripts as modules of this package
(`launch`, `rehearse_run`, `evaluate_run`; scripts/ is outside this track's files).
Hand-written adapters (not derived): probes, service, fake_server, schedule, transport, rehearsal_timing (and score,
the evaluator).

Usage: python -m research.progress_subgoal_v1.derive [--check]
"""
import argparse
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = 'research/progress_subgoal_v1/'
BANNER = '# Derived from {source} by research/progress_subgoal_v1/derive.py; edit the derivation, not this file.\n'
GLOBAL = (('ws3_questionnaire_v1', 'progress_subgoal_v1'),
          ('ws3-questionnaire-v1', 'progress-subgoal-v1'),
          ('WS3Q_', 'PSV1_'),
          ('ws3q-', 'psv1-'),
          ('ws3 questionnaire v1', 'progress subgoal v1'),
          # WS3's launch, rehearse and evaluate scripts become modules of this package
          ('scripts/progress_subgoal_v1_launch.py', PACKAGE + 'launch.py'),
          ('scripts.progress_subgoal_v1_launch', 'research.progress_subgoal_v1.launch'),
          ('scripts/rehearse_progress_subgoal_v1.py', PACKAGE + 'rehearse_run.py'),
          ('scripts.rehearse_progress_subgoal_v1', 'research.progress_subgoal_v1.rehearse_run'),
          ('scripts/evaluate_progress_subgoal_v1.py', PACKAGE + 'evaluate_run.py'),
          ('scripts.evaluate_progress_subgoal_v1', 'research.progress_subgoal_v1.evaluate_run'))
SOURCES = {PACKAGE + name + '.py': 'research/ws3_questionnaire_v1/' + name + '.py'
           for name in ('authority', 'host', 'worker', 'runner', 'resources', 'monitor', 'supervisor', 'evidence')}
SOURCES.update({PACKAGE + 'launch.py': 'scripts/ws3_questionnaire_v1_launch.py',
                PACKAGE + 'rehearse_run.py': 'scripts/rehearse_ws3_questionnaire_v1.py',
                PACKAGE + 'evaluate_run.py': 'scripts/evaluate_ws3_questionnaire_v1.py'})

REQUIRED_OLD = """REQUIRED_SOURCE = {'research/progress_subgoal_v1/' + name for name in
                   ('authority.py', 'probes.py', 'probes.json', 'score.py', 'schedule.py', 'transport.py',
                    'service.py', 'host.py', 'worker.py', 'runner.py', 'monitor.py', 'resources.py', 'supervisor.py',
                    'evidence.py', 'fake_server.py')}
REQUIRED_SOURCE |= {'research/transition_evidence_v1/' + name for name in  # the questionnaire and its records
                    ('questionnaire.py', 'score.py', 'transition.py', 'reference.py', 'vocabulary.py', 'fixtures.py')}
"""
REQUIRED_NEW = """REQUIRED_SOURCE = {'research/progress_subgoal_v1/' + name for name in
                   ('authority.py', 'probes.py', 'probes.json', 'score.py', 'schedule.py', 'transport.py',
                    'service.py', 'host.py', 'worker.py', 'runner.py', 'monitor.py', 'resources.py', 'supervisor.py',
                    'evidence.py', 'fake_server.py', 'questions.py', 'fixtures.py', 'subgoal.py', 'reference.py',
                    'launch.py')}
REQUIRED_SOURCE |= {'research/transition_evidence_v1/' + name for name in  # the transition contract (records)
                    ('transition.py', 'vocabulary.py')}
"""
SCRIPT_ROOT = ('ROOT = Path(__file__).resolve().parents[1]', 'ROOT = Path(__file__).resolve().parents[2]', 1)
REHEARSAL_SET_OLD = "    os.environ.update(PSV1_REHEARSAL='1', CUDA_VISIBLE_DEVICES='')\n"
REHEARSAL_SET_NEW = (REHEARSAL_SET_OLD +
                     "    from research.progress_subgoal_v1.probes import FROZEN_PATH, REHEARSAL_ENV, write_rehearsal_set\n"
                     "    if not FROZEN_PATH.is_file() and not (os.environ.get(REHEARSAL_ENV)\n"
                     "                                          and Path(os.environ[REHEARSAL_ENV]).is_file()):\n"
                     "        # Before the freeze only: a stand-in question set (the dry run plus development).\n"
                     "        os.environ[REHEARSAL_ENV] = str(workdir / 'rehearsal-probes.json')\n"
                     "        write_rehearsal_set(os.environ[REHEARSAL_ENV])\n")

LOAD_VERIFIED_OLD = """def load_verified(folder):
    try:
        return _v2.load_verified(folder)
    except EvidenceError as strict:
        return load_committed(folder, str(strict))
"""
LOAD_VERIFIED_NEW = """FINAL_STATUSES = frozenset({'complete', 'incomplete'})  # the runner's only finalized index states


def load_verified(folder):
    try:
        run = _v2.load_verified(folder)
    except EvidenceError as strict:
        return load_committed(folder, str(strict))
    if run.get('status') in FINAL_STATUSES:
        return run
    # Consistent evidence whose index was never finalized: the writer stopped after a per-call commit (status
    # 'running') and before the final index write. Never accept it as is: recover it as an interrupted run.
    recovery = {'index_committed': True, 'index_finalized': False, 'index_status': run.get('status'),
                'strict_error': None, 'ignored_temporary_files': [], 'ignored_uncommitted_log_bytes': 0,
                'index_calls_recorded': run.get('calls_recorded'), 'committed_calls': len(run['calls'])}
    return {**run, 'status': 'incomplete', 'stop_reason': run.get('stop_reason') or 'interrupted_evidence',
            'calls_recorded': len(run['calls']), 'evidence_recovery': recovery}
"""

DERIVED = {
    PACKAGE + 'authority.py': (
        # the two-arm schedule: 2 x 2 x 1,395 decision calls + 272 development calls
        ("'maximum_questionnaire_calls': 5616,", "'maximum_questionnaire_calls': 5852,", 1),
        # review revision r4 (r1: lock in its own inventory; r2: fixed slow-fault latencies; r3: running-index loader gap)
        ("REVIEW = 'notebooks/progress-subgoal-v1-review-r2/review-source-lock.json'",
         "REVIEW = 'notebooks/progress-subgoal-v1-review-r4/review-source-lock.json'", 1),
        (REQUIRED_OLD, REQUIRED_NEW, 1),
    ),
    PACKAGE + 'host.py': (),
    PACKAGE + 'worker.py': (
        # Derived from the frozen schedule and the rehearsal cutoff (rehearsal_timing.py, after Track 2's b1b7681):
        # the pass-1 fault slows every call; the pass-2 fault slows only pass-2 calls, so it is forwarded to the host
        # (and from there to the fake server). WS3's fixed 0.13/0.06 s were sized for 2,500 calls per pass.
        ("SLOW_LATENCY = {'slow_withheld_pass_1': 0.13, 'slow_withheld_pass_2': 0.06}",
         "SLOW_LATENCY = {{'slow_withheld_pass_1': {slow_withheld_pass_1}, 'slow_withheld_pass_2': "
         "{slow_withheld_pass_2}}}  # derived: rehearsal_timing.py", 1),
        ("               'trickle_metrics', 'http_error', 'late_reply')",
         "               'trickle_metrics', 'http_error', 'late_reply', 'slow_withheld_pass_2')", 1),
    ),
    PACKAGE + 'runner.py': (),
    PACKAGE + 'resources.py': (),
    PACKAGE + 'monitor.py': (),
    PACKAGE + 'supervisor.py': (),
    PACKAGE + 'evidence.py': (
        # Review of fb0a85f (r3 check, monitor_exit): the runner commits its index after every call with status
        # 'running' and finalizes it only after its loop. A worker killed between those writes (the lost-monitor
        # teardown) leaves fully consistent evidence, so v2's strict loader accepts it and the recovery path above never
        # runs: the evaluator saw status 'running' with stop_reason None. A verified but never-finalized index is now
        # recovered exactly like an interrupted write. (WS3 r2's loader, from which this derives, has the same gap.)
        (LOAD_VERIFIED_OLD, LOAD_VERIFIED_NEW, 1),
    ),
    PACKAGE + 'launch.py': (SCRIPT_ROOT,),
    PACKAGE + 'rehearse_run.py': (SCRIPT_ROOT, (REHEARSAL_SET_OLD, REHEARSAL_SET_NEW, 1)),
    PACKAGE + 'evaluate_run.py': (
        # this protocol's evaluator takes the decision partition explicitly (labelled `withheld` in the runner shape)
        ("            analysis = analyze(frozen['probes'], {k: v for k, v in passes.items() if v})",
         "            analysis = analyze(frozen['probes'], {k: v for k, v in passes.items() if v}, 'withheld')", 1),
        # the gate needs every primary and over-claim-gate answer (this protocol's completeness policy)
        ("    gate_status = ('complete' if analysis and analysis['completeness']['withheld'] == 'complete' and not recovered\n"
         "                   else 'incomplete')  # WS3: every withheld answer; the verdict applies its own policy",
         "    gate_status = ('complete' if analysis and not recovered and analysis['completeness']['primary']\n"
         "                   == analysis['completeness']['over_claim_gates'] == 'complete'\n"
         "                   else 'incomplete')  # every primary and over-claim-gate answer; readiness applies its own rules",
         1),
        # this protocol reports readiness per arm; a recovered run is never eligible
        ("            'gate': ({'questionnaire': 'incomplete' if recovered else analysis['verdict']}",
         "            'gate': ({arm: 'incomplete' if recovered else row['status']\n"
         "                      for arm, row in analysis['readiness'].items()}", 1),
    ),
}
# SHA-256 of each WS3 source when this derivation was written (the reviewed WS3 v1 r2 working tree at c8f4c42).
SOURCE_SHA256 = {
    'research/ws3_questionnaire_v1/authority.py': '3637b1ed2e2c53b429c1605c715d7a9de49cc426f39bf785ac7f558031ad52ae',
    'research/ws3_questionnaire_v1/host.py': '6486118540c627e39f9b458ce3b4f2f9b21a1586888b0ce8cde478ba5384924e',
    'research/ws3_questionnaire_v1/worker.py': 'a9055299984431f7abf5c8dce27135fdf6340055bdeb3d86663b239b77ae1b5d',
    'research/ws3_questionnaire_v1/runner.py': '2507871358d76f7a6fe0ba96d46e31b47b7c1c72db2828cd0d65e0083c86de06',
    'research/ws3_questionnaire_v1/resources.py': '598c34033e2a2bac96e26663bb3b04b35ec10050266a71c7188ceb680c416782',
    'research/ws3_questionnaire_v1/monitor.py': '70d379c2223c23b50e38f4e3f7c0a36a13c08c4e05c8b226c20d5576a5792749',
    'research/ws3_questionnaire_v1/supervisor.py': 'a65c5432fa1f9a23e77972a660c4c89cd95accde195badae9ecce39c21747ce1',
    'research/ws3_questionnaire_v1/evidence.py': 'adb3dd9f382ef7952f947029f3daa6645847bfe1aeda645d575cb72b499ab701',
    'scripts/ws3_questionnaire_v1_launch.py': '0731a29e0c5ca1a1a5c8f736419ca5f9405b597cbc6e6aa4ac783067fa123390',
    'scripts/rehearse_ws3_questionnaire_v1.py': '12541d3aa22f4f1fa60d2307f0dbf9c3ea328bb5c7ad7e907b59baa499b47f78',
    'scripts/evaluate_ws3_questionnaire_v1.py': '295ae605f13abd36561f1ea39a588fc93fb536baf11f3c614ec460c1fcccc9aa',
}


def derive_one(target):
    source = SOURCES[target]
    lines = (ROOT / source).read_text(encoding='utf-8').splitlines(keepends=True)
    if lines and lines[0].startswith('# Derived from '):
        lines = lines[1:]
    text = ''.join(lines)
    for old, new in GLOBAL:
        text = text.replace(old, new)
    for old, new, count in DERIVED[target]:
        if '{slow_withheld_pass_1}' in new:
            from research.progress_subgoal_v1.rehearsal_timing import slow_latencies
            new = new.format(**slow_latencies())
        found = text.count(old)
        if found != count:
            raise ValueError(f'{target}: expected {count} of {old[:70]!r}, found {found}')
        text = text.replace(old, new)
    for residue in ('ws3_questionnaire_v1', 'ws3-questionnaire-v1', 'WS3Q_', 'ws3q-', 'scripts.evaluate_',
                    'scripts.rehearse_', '_v1_launch'):
        if residue in text:
            raise ValueError(f'{target}: unexpected remaining reference {residue!r}')
    return BANNER.format(source=source) + text


def derive():
    return {target: derive_one(target) for target in DERIVED}


def source_hashes():
    return {source: hashlib.sha256((ROOT / source).read_bytes()).hexdigest() for source in SOURCES.values()}


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
        (ROOT / target).write_text(text, encoding='utf-8', newline='\n')
    print(f'wrote {len(DERIVED)} derived files')
    print(source_hashes())
