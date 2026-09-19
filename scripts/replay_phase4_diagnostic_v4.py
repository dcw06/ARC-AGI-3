"""Independently evaluate the hash-bound archived v4 diagnostic; no compute launch."""
import hashlib,json,tempfile,zipfile
from pathlib import Path
from certification.phase4_diagnostic_v4.evaluate import evaluate
from certification.phase4_diagnostic_v4.telemetry import read_telemetry

ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    manifest=json.loads((ROOT/'reports/phase4_diagnostic_v4_evidence_lock.json').read_text())
    for name,digest in manifest['bindings'].items():
        if sha(ROOT/name)!=digest:raise ValueError('evidence/source binding drift: '+name)
    review=ROOT/'notebooks/phase4-action-diagnostic-v4-review-r1'
    lock=json.loads((review/'review-source-lock.json').read_text())
    for base,key in ((ROOT,'bindings'),(review,'artifacts')):
        for name,digest in lock[key].items():
            if sha(base/name)!=digest:raise ValueError('frozen source/artifact drift: '+name)
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(ROOT/manifest['archive']) as archive:
            for name in archive.namelist():
                if not (Path(tmp)/name).resolve().is_relative_to(Path(tmp).resolve()):
                    raise ValueError('unsafe archive path')
            archive.extractall(tmp)
        folder=Path(tmp)/'phase4-action-diagnostic-v4'
        read=lambda name:json.loads((folder/name).read_text())
        report=read('control/outer.json');worker=read('worker/state.json')
        report['worker']=worker
        report['gpu_telemetry']=read_telemetry(folder/'monitor')['samples']
        result=evaluate(report)
        target=read('evaluation/result.json');final=read('evaluation/notebook-result.json')
        cost=read('control/notebook-cost.json');cleanup=read('control/gpu-cleanup.json')
        errors=list(result['errors'])
        if not target.get('passed') or target.get('comparison')!=result['comparison']:
            errors.append('target/local evaluator disagreement')
        if not (final.get('passed') is True and final.get('completed') is True
                and final.get('source_removed') is True and final.get('error') is None
                and 0<=final.get('elapsed_seconds',float('inf'))<3300
                and final.get('evaluation_sha256')==sha(folder/'evaluation/result.json')
                and final.get('cleanup_sha256')==sha(folder/'control/notebook-cost.json')):
            errors.append('final notebook receipt')
        if not (cost.get('dependency_trees_removed') is True and cost.get('error') is None
                and 0<=cost.get('elapsed_seconds',float('inf'))<3300):
            errors.append('dependency cleanup/deadline')
        if not (cleanup.get('gpu_cleanup_verified') is True and cleanup.get('groups_absent') is True
                and cleanup.get('remaining_process_count')==0 and cleanup.get('error') is None):
            errors.append('independent cleanup receipt')
        prior=json.loads((ROOT/'reports/phase4_diagnostic_v3_replay.json').read_text())['revised_evaluator']['comparison']
        pairs=[{'game_id':game,'arm':arm,'previous':old[arm],'current':result['comparison']['per_game'][game][arm]}
               for game,old in prior['per_game'].items()
               for arm in ('baseline','relocated_example','no_concrete_examples')]
        mismatches=[p for p in pairs if p['previous']!=p['current']]
        receipt={'passed':not errors,'errors':errors,'scope':'independent archived v4 target diagnostic replay',
            'evaluator':result,'notebook_result':final,'notebook_cost':cost,'independent_cleanup':cleanup,
            'requests_started':worker['requests_started'],'model_startup_seconds':worker['model_startup_seconds'],
            'diagnostic_window_seconds':worker['ended_seconds']-worker['request_window_started_seconds'],
            'monitor_samples':report['gpu_samples'],
            'prior_run_comparison':{'paired_actions':len(pairs),'identical_actions':len(pairs)-len(mismatches),'changed_actions':mismatches},
            'archive_sha256':sha(ROOT/manifest['archive']),'phase4_complete':False,
            'production_C_admit':None,'exact_provider_billed_seconds':None}
    (ROOT/'reports/phase4_diagnostic_v4_evaluation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'passed':receipt['passed'],'errors':errors,'elapsed_seconds':final['elapsed_seconds'],
        'arms':result['comparison']['arms'],'identical_prior_actions':len(pairs)-len(mismatches)}))
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
