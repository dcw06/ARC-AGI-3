"""Run evidence for the Stage 1 run: WS3's module (v2's append-only call log plus committed-state recovery), with one
addition: a verified run whose index was never finalized is recovered, never accepted as is.

Everything is re-exported from research/ws3_questionnaire_v1/evidence.py unchanged except `load_verified`, which
wraps WS3's. WS3 recovers only when v2's strict verification fails. But the runner commits its index after every
call with status 'running' and finalizes it ('complete', or 'incomplete' with a stop reason) only after its loop; a
termination between a per-call commit and that final write (the lost-monitor teardown's SIGTERM) leaves fully
consistent evidence that v2 accepts, with status 'running' and no stop reason. Such a run is recovered here like an
interrupted write: status 'incomplete', stop_reason kept or 'interrupted_evidence', and `evidence_recovery` recording
`index_finalized: false`, the index status and the committed calls. A recovered run is never technically complete
and never carries a promotable result (the evaluator checks `evidence_recovery`). Approach reused from Track 4
(progress_subgoal_v1, b859a8a).
"""
from research.ws3_questionnaire_v1 import evidence as _ws3
from research.ws3_questionnaire_v1.evidence import (  # noqa: F401  (re-exported, unchanged)
    CALLS, INTERRUPTED_TEMPORARY, MANIFEST, VERSION, EvidenceError, RunEvidence, StorageExhausted, atomic_write,
    encode, forge, load_committed, load_unverified_calls, truncate)

FINAL_STATUSES = frozenset({'complete', 'incomplete'})  # the runner's only finalized index states


def load_verified(folder):
    run = _ws3.load_verified(folder)  # v2's strict loader, or WS3's committed-state recovery when that fails
    if 'evidence_recovery' in run or run.get('status') in FINAL_STATUSES:
        return run
    # Consistent evidence whose index was never finalized: the writer stopped after a per-call commit and before
    # the final index write. Recover it as an interrupted run.
    recovery = {'index_committed': True, 'index_finalized': False, 'index_status': run.get('status'),
                'strict_error': None, 'ignored_temporary_files': [], 'ignored_uncommitted_log_bytes': 0,
                'index_calls_recorded': run.get('calls_recorded'), 'committed_calls': len(run['calls'])}
    return {**run, 'status': 'incomplete', 'stop_reason': run.get('stop_reason') or 'interrupted_evidence',
            'calls_recorded': len(run['calls']), 'evidence_recovery': recovery}
