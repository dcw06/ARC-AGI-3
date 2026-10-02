# Derived from research/ws3_questionnaire_v1/evidence.py by research/progress_subgoal_v1/derive.py; edit the derivation, not this file.
"""Run evidence for the WS3 questionnaire run: v2's append-only call log, plus committed-state recovery.

The writer (`RunEvidence`) is v2's, unchanged. The loader first applies v2's strict verification. If that fails only
because a write was interrupted, it recovers the **last committed state** instead of discarding the partial run:
- the manifest (always replaced atomically, so it is the last committed version) must parse and match its version;
- every manifest-listed file must still verify byte-for-byte;
- the call log's first `bytes` bytes must match the manifest's hash (anything after them was never committed). This
  includes a manifest that still records zero calls while `calls.jsonl` already exists: a kill during the first append
  leaves a log whose bytes (a partial or even a whole first line) were never committed, so the committed log is empty;
- the only other files allowed are interrupted temporary files (`manifest.json.tmp`, `run.json.tmp`), which are
  ignored because they were never committed;
- the run index may be one step ahead of its manifest record: the writer replaces `run.json` (atomically, so it is a
  whole file) before the manifest, and a kill between the two leaves a newer, uncommitted index. It is then used for
  metadata only and flagged `index_committed: false`. Every index limit is re-checked by the independent evaluator
  against the frozen values, and calls always come only from the committed log.

A recovered run is always `incomplete`, with `stop_reason` kept if the committed index had one and otherwise
`interrupted_evidence`, and `evidence_recovery` describing what was ignored. So partial evidence stays usable and can
never be mistaken for complete evidence. The evaluator reports `evidence_recovery`, scores the recovered answers for
descriptive analysis only, and never grants a recovered run technical completion or a promotable verdict.

Why this exists: when the monitor is lost, the supervisor tears the worker down with SIGTERM, which can land in the
middle of an atomic write. In a fresh-checkout rehearsal (package r2 review) the worker was killed while writing
`manifest.json.tmp`. The committed state (6 calls) was consistent, yet v2's strict loader refused the whole run. The same
race exists, latent, in the v1-v3 stacks.
"""
import hashlib
import json
from pathlib import Path

from research.evidence_comprehension_v2 import evidence as _v2
from research.evidence_comprehension_v2.evidence import (  # noqa: F401  (re-exported, unchanged)
    CALLS, MANIFEST, VERSION, EvidenceError, RunEvidence, StorageExhausted, atomic_write, encode, forge,
    load_unverified_calls, truncate)

INTERRUPTED_TEMPORARY = frozenset({MANIFEST + '.tmp', 'run.json.tmp'})


def load_verified(folder):
    try:
        return _v2.load_verified(folder)
    except EvidenceError as strict:
        return load_committed(folder, str(strict))


def load_committed(folder, strict_error):
    folder = Path(folder)
    try:
        manifest = json.loads((folder / MANIFEST).read_bytes())
    except (OSError, ValueError) as exc:
        raise EvidenceError('manifest missing or unreadable') from exc
    if manifest.get('version') != VERSION or not isinstance(manifest.get('files'), dict) \
            or not isinstance(manifest.get('calls'), dict) or set(manifest['files']) != {'run.json'}:
        raise EvidenceError('manifest version')
    on_disk = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()} - {MANIFEST}
    lines = manifest['calls'].get('lines')
    expected = {'run.json'} | ({CALLS} if lines else set())
    # With no committed calls, a call log on disk holds only uncommitted bytes of the first append.
    ignorable = INTERRUPTED_TEMPORARY | (set() if lines else {CALLS})
    extra = on_disk - expected
    if expected - on_disk or extra - ignorable:
        raise EvidenceError(f'file inventory mismatch: missing {sorted(expected - on_disk)[:3]}, '
                            f'extra {sorted(extra - ignorable)[:3]}')
    if (folder / 'run.json').is_symlink():
        raise EvidenceError('symlinked evidence: run.json')
    run_raw = (folder / 'run.json').read_bytes()
    row = manifest['files']['run.json']
    index_committed = len(run_raw) == row['bytes'] and hashlib.sha256(run_raw).hexdigest() == row['sha256']
    calls, trailing = [], 0
    if CALLS in on_disk:
        path = folder / CALLS
        if path.is_symlink():
            raise EvidenceError('symlinked evidence: ' + CALLS)
        raw = path.read_bytes()
        committed = raw[:manifest['calls']['bytes']]
        if len(committed) != manifest['calls']['bytes'] or hashlib.sha256(committed).hexdigest() != manifest['calls']['sha256']:
            raise EvidenceError('committed call log does not verify')
        trailing = len(raw) - len(committed)
        if committed and not committed.endswith(b'\n'):
            raise EvidenceError('committed call log ends inside a line')
        calls = [json.loads(line) for line in committed[:-1].split(b'\n')] if committed else []
        if len(calls) != (lines or 0):
            raise EvidenceError('committed call count differs from the manifest')
    for n, call in enumerate(calls):
        if not isinstance(call, dict) or call.get('index') != n:
            raise EvidenceError(f'committed call {n} carries index {call.get("index") if isinstance(call, dict) else None}')
    try:
        index = json.loads(run_raw)
    except ValueError as exc:
        raise EvidenceError('run index unreadable') from exc
    if not isinstance(index, dict):
        raise EvidenceError('run index is not an object')
    recovery = {'index_committed': index_committed, 'strict_error': strict_error[:200], 'ignored_temporary_files': sorted(extra),
                'ignored_uncommitted_log_bytes': trailing,
                'index_calls_recorded': index.get('calls_recorded'), 'committed_calls': len(calls)}
    return {**index, 'status': 'incomplete', 'stop_reason': index.get('stop_reason') or 'interrupted_evidence',
            'calls_recorded': len(calls), 'evidence_recovery': recovery, 'calls': calls}
