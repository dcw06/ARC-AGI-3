"""Offline replay of retained diagnostic v2 R2 evidence; never launch compute."""
import hashlib,json,tempfile,zipfile
from pathlib import Path
from certification.phase4_diagnostic_v2.evaluate import evaluate as previous
from certification.phase4_diagnostic_v2.telemetry import read_telemetry
from certification.phase4_diagnostic_v3.evaluate import evaluate

ROOT=Path(__file__).resolve().parents[1]

def main():
    lock=json.loads((ROOT/'reports/phase4_diagnostic_v3_review_lock.json').read_text())
    for name,digest in lock['bindings'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('replay binding drift: '+name)
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(ROOT/lock['archive']) as archive:
            for name in archive.namelist():
                if not (Path(tmp)/name).resolve().is_relative_to(Path(tmp).resolve()):
                    raise ValueError('unsafe archive path')
            archive.extractall(tmp)
        folder=Path(tmp)/'phase4-action-diagnostic-v2'
        read=lambda name:json.loads((folder/name).read_text())
        report=read('control/outer.json')
        report['worker']=read('worker/state.json')
        report['gpu_telemetry']=read_telemetry(folder/'monitor')['samples']
        old=previous(report);revised=evaluate(report)
        if old['errors']!=['request window']:raise ValueError('unexpected original failure')
        result={'scope':'offline_evaluator_revision_not_new_GPU_run',
                'original_evaluator':old,'revised_evaluator':revised,
                'original_notebook_result':read('evaluation/notebook-result.json'),
                'notebook_cost':read('control/notebook-cost.json'),
                'independent_cleanup':read('control/gpu-cleanup.json'),
                'historical_notebook_status_changed':False,
                'phase4_complete':False,'new_compute_authorized':False,
                'exact_provider_billed_seconds':None}
    destination=ROOT/'reports/phase4_diagnostic_v3_replay.json'
    destination.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':revised['passed'],'errors':revised['errors'],
                      'comparison':revised['comparison']['arms'] if revised['passed'] else None}))

if __name__=='__main__':main()
