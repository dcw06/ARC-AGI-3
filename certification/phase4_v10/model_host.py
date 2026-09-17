"""Owned model-side tokenizer/inference service; never detaches from worker PGID."""
import argparse
from pathlib import Path
import time
from certification.phase4_v10.live_probes import require_live_authority
from certification.phase4_v10.bridge import BridgeServer

def main():
    require_live_authority()
    p=argparse.ArgumentParser()
    p.add_argument('--socket',type=Path,required=True)
    p.add_argument('--scratch',type=Path,required=True)
    p.add_argument('--deadline',type=float,required=True)
    p.add_argument('--cancel',type=Path,required=True)
    args=p.parse_args()
    if time.monotonic()>=args.deadline or args.cancel.exists(): raise TimeoutError('model startup admission closed')
    from certification.phase4_v10.service import SharedModelService
    service=SharedModelService(args.scratch)
    service.start()
    with BridgeServer(args.socket,service,args.deadline,args.cancel) as server:
        while time.monotonic()<args.deadline and not args.cancel.exists(): server.handle_request()

if __name__=='__main__': main()
