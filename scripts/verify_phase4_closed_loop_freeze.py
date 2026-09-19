"""Verify the closed-loop protocol freeze only; never reserve or launch compute."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    lock=json.loads((ROOT/'reports/phase4_closed_loop_v1_review_lock.json').read_text())
    for name,digest in lock['bindings'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('closed-loop preparation drift: '+name)
    budget=json.loads((ROOT/'reports/phase4_closed_loop_v1_compute_budget.json').read_text())
    if budget['authorized_seconds']!=0 or budget['authorized_attempts']!=0 or budget['reservation'] is not None:
        raise ValueError('proposal must not carry compute authority')
    print(json.dumps({'frozen_bindings_verified':len(lock['bindings']),
                      'runner_ready':False,'gpu_seconds_authorized':0,'reservation':None}))

if __name__=='__main__':main()
