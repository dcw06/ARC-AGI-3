"""Replay retained target evidence without changing its original verdict."""
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from certification.phase4_v12.evaluate import evaluate as original_evaluate, monitor_fields
from certification.phase4_v12.telemetry import read_telemetry
from certification.phase4_v13.evaluate import evaluate


def replay():
    read = lambda p: json.loads(p.read_text(encoding='utf-8'))
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    run = ROOT/'reports/runs/phase4-v12-pilot-20260918'
    out = run/'download/phase4-development-v12'
    receipt = read(ROOT/'reports/phase4_v12_pilot_evaluation.json')
    for name, binding in receipt['evidence'].items():
        if sha(run/name) != binding['sha256']:
            raise ValueError('retained evidence drift: '+name)
    lock_path = ROOT/'notebooks/phase4-lifecycle-v12-review-r1/review-source-lock.json'
    lock = read(lock_path)
    for name, digest in lock['bindings'].items():
        if sha(ROOT/name) != digest: raise ValueError('frozen v12 source drift: '+name)
    rows = read(ROOT/'certification/phase4_v1/workload.json')
    report = read(out/'control/outer.json')
    report['worker'] = read(out/'worker/state.json')
    report.update(monitor_fields(read(out/'monitor/monitor-result.json'),
        read_telemetry(out/'monitor'), first_cell_monotonic=report['first_cell_monotonic']))
    original = original_evaluate(report, rows)
    assert original['errors'] == ['single audited canary evidence missing'], original['errors']
    corrected = evaluate(report, rows)
    assert corrected['passed'], corrected['errors']
    # Exercise the complete live evaluator, not only the canary helper.
    failures = {}
    variants = [('missing', None), ('wrong_contract', {**report['worker']['canary_audit'], 'action_contract':'old'}),
        ('token_mismatch', {**report['worker']['canary_audit'], 'tokenizer_prompt_tokens':45}),
        ('over_limit', {**report['worker']['canary_audit'], 'server_completion_tokens':129})]
    for label, canary in variants:
        candidate = {**report, 'worker':{**report['worker'], 'canary_audit':canary}}
        result = evaluate(candidate, rows)
        assert not result['passed'] and result['capacity_candidate'] is None
        failures[label] = result['errors']
    for key in ('cleanup_verified','gpu_cleanup_verified','independent_gpu_cleanup_verified'):
        candidate = {**report, key:False}
        # Independent cleanup is enforced by supervisor error before evaluator.
        if key == 'independent_gpu_cleanup_verified': candidate['error']='independent GPU cleanup failed'
        result = evaluate(candidate,rows)
        assert not result['passed'] and result['capacity_candidate'] is None
        failures[key] = result['errors']
    evidence_before = sha(out/'evaluation/notebook-result.json')
    sources = [*sorted((ROOT/'certification/phase4_v13').glob('*.py')),
               ROOT/'tests/test_phase4_v13_evaluator.py', Path(__file__)]
    result = {'scope':'offline_diagnostic_replay_not_new_target_execution',
        'historical_provider_status':'ERROR','historical_verdict_changed':False,
        'original_evaluator':original,'corrected_evaluator':corrected,
        'negative_replay_cases':failures,'source_lock_sha256':sha(lock_path),
        'evidence_archive_sha256':receipt['evidence_archive_sha256'],
        'notebook_result_sha256':evidence_before,
        'revision_bindings':{p.relative_to(ROOT).as_posix():sha(p) for p in sources},
        'gpu_seconds_authorized':0,'phase4_complete':False,
        'limitations':'Replay validates retained lifecycle evidence under corrected canary acceptance. It does not change the failed notebook verdict or establish a newly executed end-to-end notebook.'}
    path = ROOT/'reports/phase4_v13_v12_replay.json'
    with path.open('x',encoding='utf-8') as f: json.dump(result,f,indent=2)
    assert sha(out/'evaluation/notebook-result.json')==evidence_before
    print(json.dumps({'original_errors':original['errors'],'corrected_passed':corrected['passed'],
        'negative_cases':len(failures),'report':str(path)}))


if __name__=='__main__': replay()
