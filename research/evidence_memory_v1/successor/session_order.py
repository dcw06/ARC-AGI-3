"""Session B launches only after session A is technically complete (protocol v2 frozen, section 12; owner decision of
October 9, 2026). Hand-written; used by session B's launch tooling only.

Where it is enforced. Session B's launch tooling: `notebook.launch_artifacts` (the launch package, built for
`launch-build`, `launch.write_package` and `launch.submit`) and `launch.claim`. It is never part of the reviewed
per-scope live gate (`binding.require_live`), which also runs inside the Kaggle payload and stays per scope. Session
A's tooling never reads it.

What B's launch tooling requires:
- session A's retained technical evaluation, the output of `research/evidence_memory_v1/successor/evaluate.py` for
  A's output, exists in B's checkout at RECORD;
- B's compute authorization names that file's SHA-256 as `session_a_technical_evaluation_sha256`, and the file
  matches it;
- the record is session A's live-mode evaluation of A's registered withheld frozen set (the `frozen_set_sha256` bound
  in A's protocol), technically complete (lifecycle passed, evidence verified and not recovered, no call errors, a
  complete run), and `session_technically_valid`: every scheduled call answered and the invalid-output rule met in
  every pass (pass 1 and the repeat), for every arm.

If session A is not technically complete, no pooled analysis is possible: the experiment stops and session B is never
launched. The record is technical only; it carries no outcome (successor/evaluate.py).
"""
import hashlib
import json
from pathlib import Path
import re

from research.evidence_memory_v1.successor import plan as PL

RECORD = 'reports/evidence_memory_v1_session_a_technical_evaluation.json'
FIELD = 'session_a_technical_evaluation_sha256'
PASSES = ('pass_1', 'pass_2')


def _read(root, name):
    return (Path(root) / name).read_bytes()


def registered_frozen_set(root):
    """Session A's registered frozen-set SHA-256 (its protocol's binding), or None if unreadable."""
    try:
        value = json.loads(_read(root, PL.SESSIONS['A']['package'] + '/protocol.json'))['experiment']['frozen_set_sha256']
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return value if isinstance(value, str) else None


def _valid_in_every_pass(analysis):
    by_pass, answers = analysis.get('invalid_by_pass'), analysis.get('answers')
    if (analysis.get('technical_status') != 'session_technically_valid' or analysis.get('invalid_rule_met') is not True
            or analysis.get('session') != 'A' or (analysis.get('completeness') or {}).get('withheld') != 'complete'
            or not isinstance(by_pass, dict) or not isinstance(answers, dict)
            or set(by_pass) != set(PASSES) or set(answers) != set(PASSES)):
        return False
    for pass_id in PASSES:
        block, counts = by_pass[pass_id], answers[pass_id]
        arms = block.get('by_arm') if isinstance(block, dict) else None
        if (not isinstance(counts, dict) or type(counts.get('scheduled')) is not int
                or counts.get('answered') != counts['scheduled'] or not isinstance(arms, dict)
                or block.get('rule_met') is not True or any(not isinstance(a, dict) or a.get('rule_met') is not True
                                                            for a in arms.values())):
            return False
    return answers['pass_1']['scheduled'] > 0 and bool(by_pass['pass_1']['by_arm'])


def record_reasons(root):
    """Why the retained session-A record does not show A technically complete; empty when it does. Reads no
    approval, evidence, reservation or claim."""
    try:
        raw = _read(root, RECORD)
    except OSError:
        return [f'session A technical evaluation absent: {RECORD} (session B launches only after session A is '
                'technically complete)']
    try:
        record = json.loads(raw)
    except ValueError:
        record = None
    if not isinstance(record, dict):
        return [f'session A technical evaluation unreadable: {RECORD}']
    reasons = []
    if record.get('session') != 'A' or record.get('package') != PL.SESSIONS['A']['package']:
        reasons.append("the retained technical evaluation is not session A's")
    if record.get('mode') != 'live':
        reasons.append(f"session A's technical evaluation is in mode {record.get('mode')!r}, not live")
    if record.get('case_source') != 'withheld':
        reasons.append(f"session A's evaluated case source is {record.get('case_source')!r}, not withheld")
    registered = registered_frozen_set(root)
    if registered is None or record.get('frozen_set_sha256') != registered:
        reasons.append("session A's technical evaluation is not of session A's registered frozen set")
    run, evidence = record.get('run'), record.get('run_evidence')
    if (record.get('technically_complete') is not True or record.get('lifecycle_passed') is not True
            or record.get('lifecycle_errors') != [] or record.get('call_errors') != []
            or not isinstance(evidence, dict) or evidence.get('verified') is not True
            or evidence.get('recovered') is not False or not isinstance(run, dict) or run.get('status') != 'complete'
            or record.get('gate_status') != 'complete'):
        reasons.append('session A is not technically complete')
    analysis = record.get('analysis')
    if not isinstance(analysis, dict) or not _valid_in_every_pass(analysis):
        reasons.append('session A is not technically valid in every pass')
    return reasons


def reasons(root, compute_name):
    """record_reasons plus the binding: session B's compute authorization (`compute_name`) must name the retained
    record's SHA-256 as FIELD. Empty when session B's launch tooling may proceed."""
    found = record_reasons(root)
    try:
        compute = json.loads(_read(root, compute_name))
    except (OSError, ValueError):
        return found + [f'session B compute authorization unreadable: {compute_name}']
    named = compute.get(FIELD) if isinstance(compute, dict) else None
    if not isinstance(named, str) or not re.fullmatch(r'[0-9a-f]{64}', named):
        found.append(f"session B's compute authorization does not name {FIELD}")
    elif (Path(root) / RECORD).is_file() and hashlib.sha256(_read(root, RECORD)).hexdigest() != named:
        found.append(f"the retained session A technical evaluation does not match the {FIELD} named in session B's "
                     'compute authorization')
    return found
