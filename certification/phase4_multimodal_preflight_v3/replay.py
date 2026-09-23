"""Independent terminal evidence evaluation, including final notebook cleanup."""
import hashlib,json
from pathlib import Path
from certification.phase4_multimodal_preflight_v3.evaluate import evaluate
from certification.phase4_multimodal_preflight_v3.telemetry import read_telemetry
from certification.phase4_multimodal_preflight_v3.evidence import LIMITS,TOTAL

def replay(output,*,live=True,seconds=1680):
    output=Path(output);errors=[]
    read=lambda name:json.loads((output/name).read_text())
    report=read('control/outer.json');report['worker']=read('worker/state.json')
    report['evidence_root']=str(output)
    report['gpu_telemetry']=read_telemetry(output/'monitor')['samples']
    result=evaluate(report,live=live,seconds=seconds);errors.extend(result['errors'])
    sizes={name:0 for name in LIMITS};total=0
    for path in output.rglob('*'):
        if path.is_symlink():errors.append('symlink evidence');continue
        if path.is_file():
            name=path.relative_to(output).parts[0];size=path.stat().st_size;total+=size
            if name in sizes:sizes[name]+=size
            elif name!='.evidence.lock':errors.append('unknown evidence component')
    if total>TOTAL or any(sizes[k]>LIMITS[k] for k in sizes):errors.append('evidence ceiling')
    if live:
        try:
            sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            final=read('evaluation/notebook-result.json');cost=read('control/notebook-cost.json')
            cleanup=read('control/gpu-cleanup.json');target=read('evaluation/result.json')
            if not (final.get('passed') is True and final.get('completed') is True and final.get('source_removed') is True
                and final.get('error') is None and 0<=final['elapsed_seconds']<seconds
                and final.get('evaluation_sha256')==sha(output/'evaluation/result.json')
                and final.get('cleanup_sha256')==sha(output/'control/notebook-cost.json')):raise ValueError('notebook receipt')
            if not (cost.get('dependency_trees_removed') is True and cost.get('error') is None
                and 0<=cost['elapsed_seconds']<seconds):raise ValueError('dependency cleanup')
            if not (cleanup.get('gpu_cleanup_verified') is True and cleanup.get('groups_absent') is True
                and cleanup.get('error') is None and cleanup.get('remaining_process_count')==0):raise ValueError('independent cleanup')
            if target.get('passed') is not True or target.get('comparison')!=result['comparison']:raise ValueError('target evaluation mismatch')
        except (OSError,KeyError,ValueError,TypeError) as exc:errors.append('finalization: '+str(exc))
    result.update(passed=not errors,errors=errors,independent_replay=True,evidence_bytes=total,
        exact_provider_billed_seconds=None,phase4_complete=False)
    return result
