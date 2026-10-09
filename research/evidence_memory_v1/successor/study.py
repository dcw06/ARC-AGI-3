"""The Track 2 Stage 1 study phase inside the verified lifecycle (hand-written; the research callback).

Each session package's run.py calls `run_study` as its `study` stage: after host, bundle, installation, GPU, model
artifact, server start, readiness, the startup and inference probes and the server-log prefix-cache check, and before
the cancellation probes, cleanup and evidence finalization, all on the first cell's clock. It:
1. re-validates the session's protocol bindings (frozen set, token audit, limits, request plan) and, in live mode,
   refuses any frozen set that is not the withheld set built from the committed seed;
2. verifies prefix caching from the server's counters (one counted metrics read, K0000);
3. runs the reviewed runner (successor/runner.py, derived from run/runner.py) over the frozen call order, with its
   per-call admission against the protocol's admission cutoff and per-call bound, through the study service;
4. retains, under study/: the runner's append-only call log (run/), the server configuration and counters
   (server-config.json), cancellations (cancellations.json) and a technical summary (summary.json).
It never scores an answer. Per session, results are technical only (the evaluator reports run/score.technical);
scientific results exist only in the pooled analysis of both sessions (successor/final.py over run/final.py).

Like the reviewed worker, the stage succeeds when every scheduled call ran or when the run stopped only at the
admission cutoff (an incomplete session is a reported result, not a lifecycle failure); any other stop fails the
stage. The retained evidence is evaluated either way.
"""
import json
from pathlib import Path

from research.evidence_memory_v1.successor import plan as PL
from research.evidence_memory_v1.successor import runner as R
from research.evidence_memory_v1.successor.service import StudyService

EVIDENCE_BUDGET_BYTES = 32 * 1024**2  # the reviewed worker's run-evidence budget
KIND = {'live': 'target_model_questionnaire', 'rehearsal': 'rehearsal_fake_server_questionnaire'}


def launch_record(protocol, mode):
    if mode == 'live':
        return {'argv': list(protocol['server']['argv']), 'derived_from': 'protocol.json server.argv'}
    return {'rehearsal_fake_server': True, 'stub': 'research.evidence_memory_v1.successor.stub'}


def run_study(root, package, client, evidence, clock):
    root, mode = Path(root), evidence.mode
    protocol = json.loads((root / package / 'protocol.json').read_bytes())
    frozen, digest = PL.validate_experiment(root, protocol, package)
    if mode == 'live':
        reasons = PL.live_frozen_set_reasons(root, protocol, package)
        if reasons:
            raise PermissionError('frozen set may not run live: ' + '; '.join(reasons))
    counts = PL.validate_audit(json.loads((root / package / PL.AUDIT_NAME).read_bytes()), frozen, digest)
    timing = PL.timing(mode)

    def retain(name):
        return lambda value: evidence.json('study/' + name, value)
    service = StudyService(client, frozen, digest, counts, mode=mode, launch=launch_record(protocol, mode),
                           retain_server=retain('server-config.json'),
                           retain_cancellation=retain('cancellations.json'), clock=clock.now)
    service.startup_check()
    report = R.run(evidence.folder / 'study/run', service, frozen_set=(frozen, digest), started=clock.started,
                   kind=KIND[mode], cutoff_seconds=clock.limits['admission_cutoff_seconds'],
                   bound_seconds=timing['bound'], evidence_budget_bytes=EVIDENCE_BUDGET_BYTES, cancel=None,
                   evidence_lock_root=evidence.folder, clock=clock.now)
    summary = {'run_status': report['status'], 'stop_reason': report['stop_reason'],
               'calls_recorded': report['calls_recorded'], 'scheduled_calls': report['scheduled_calls'],
               'counts': report['counts'], 'phase_reached': report['phase_reached'],
               'probe_set_sha256': digest, 'session': frozen['session'], 'case_source': frozen['case_source'],
               'service_calls': service.calls, 'cancellations': len(service.cancellations),
               'service_stopped': service.broken,
               'outcomes': 'none per session: technical evaluation only; outcomes only from the pooled analysis'}
    evidence.json('study/summary.json', summary)
    if report['status'] != 'complete' and report['stop_reason'] != 'admission_cutoff':
        raise RuntimeError('study run stopped: ' + str(report['stop_reason']))
    return summary
