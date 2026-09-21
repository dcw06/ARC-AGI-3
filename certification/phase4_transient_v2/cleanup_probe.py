"""Independent post-termination GPU check; cannot repair monitoring coverage."""
import csv
import subprocess
import time


def inspect_gpu(deadline, expected_uuid=None):
    from certification.phase4_transient_v2.live_probes import require_live_authority
    require_live_authority()
    def query(flag):
        remaining=deadline-time.monotonic()
        if remaining<=0: raise TimeoutError('GPU cleanup deadline exhausted')
        result=subprocess.run(['nvidia-smi',flag,'--format=csv,noheader,nounits'],
            capture_output=True,text=True,check=True,timeout=min(2,remaining))
        if len(result.stdout)>8192: raise ValueError('GPU cleanup output too large')
        return [[v.strip() for v in row] for row in csv.reader(result.stdout.strip().splitlines())]
    rows=query('--query-gpu=uuid,name')
    if (len(rows)!=1 or len(rows[0])!=2 or 'RTX PRO 6000' not in rows[0][1]
            or not rows[0][0] or (expected_uuid is not None and rows[0][0]!=expected_uuid)):
        raise ValueError('GPU cleanup identity mismatch')
    uuid=rows[0][0]
    processes=query('--query-compute-apps=gpu_uuid,pid')
    for row in processes:
        if len(row)!=2 or row[0]!=uuid or not row[1].isdigit():
            raise ValueError('ambiguous GPU cleanup process inventory')
    return {'gpu_uuid':uuid,'remaining_process_count':len(processes)}


def check_cleanup(*, deadline, expected_uuid, groups_absent, query=inspect_gpu, clock=time.monotonic):
    begin=clock()
    receipt={'scope':'independent_post_termination_GPU_check','gpu_cleanup_verified':False,
             'groups_absent':groups_absent,'monitoring_coverage_restored':False,'error':None}
    try:
        if begin>=deadline: raise TimeoutError('GPU cleanup deadline exhausted')
        evidence=query(deadline,expected_uuid)
        receipt.update(evidence)
        if not groups_absent: raise RuntimeError('owned process cleanup not verified')
        if evidence['remaining_process_count']!=0: raise RuntimeError('GPU processes remain')
        if clock()>=deadline: raise TimeoutError('GPU cleanup deadline exceeded')
        receipt['gpu_cleanup_verified']=True
    except Exception as exc:
        receipt['error']=type(exc).__name__+': '+str(exc)[:256]
    receipt['probe_seconds']=clock()-begin
    return receipt
