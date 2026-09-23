"""Final acceptance requires completed dependency/source cleanup and publication."""
import hashlib
import json
from pathlib import Path
import time
from certification.phase4_integrated_v2.evidence import EvidenceStore

def finalize(output,started,completed):
    output=Path(output)
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    evaluation=output/'evaluation/result.json'
    cost=output/'control/notebook-cost.json'
    elapsed=time.monotonic()-started
    verdict={'passed':False,'phase4_complete':False,'elapsed_seconds':elapsed,
             'source_removed':True,'completed':completed,'error':None}
    try:
        result=json.loads(evaluation.read_text())
        cleanup=json.loads(cost.read_text())
        if (not completed or not result['passed'] or cleanup['error'] is not None
                or cleanup['dependency_trees_removed'] is not True or elapsed>=3300):
            raise ValueError('notebook completion/cleanup/deadline not satisfied')
        verdict.update(passed=True,evaluation_sha256=digest(evaluation),cleanup_sha256=digest(cost))
    except Exception as exc:
        verdict['error']=type(exc).__name__+': '+str(exc)[:512]
    store=EvidenceStore(output,'evaluation')
    store.save('notebook-result.json',verdict)
    if time.monotonic()-started>=3300 and verdict['passed']:
        verdict.update(passed=False,error='final receipt publication exceeded deadline')
        store.save('notebook-result.json',verdict)
    if not verdict['passed']: raise RuntimeError(verdict['error'])
    return verdict
