"""Bounded offline installation into the notebook environment; authority first."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

from certification.phase4_v6.evidence import EvidenceStore
from certification.phase4_v6.live_probes import require_live_authority


def install(code, output, started):
    require_live_authority()  # No package changes without a reviewed live release.
    logs = EvidenceStore(output,'logs')
    control = EvidenceStore(output,'control')
    errors=[]
    process=None
    def drain():
        data=bytearray()
        try:
            while chunk:=process.stdout.read(4096):
                if len(data)+len(chunk)>1024**2: raise ValueError('install log exhausted')
                data.extend(chunk); logs.write('install.json',bytes(data))
        except Exception as exc: errors.append(str(exc)[:256])
        finally: process.stdout.close()
    try:
        if time.monotonic()-started>=900: raise TimeoutError('install budget exhausted before start')
        process=subprocess.Popen([sys.executable,'-c',code],start_new_session=True,
                                 stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        thread=threading.Thread(target=drain,daemon=True);thread.start()
        while process.poll() is None:
            if errors: raise RuntimeError('install evidence: '+errors[0])
            if time.monotonic()-started>=895: raise TimeoutError('offline installation deadline')
            time.sleep(.05)
        if process.returncode: raise RuntimeError('offline installation failed')
    finally:
        if process is not None:
            try: os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait(timeout=2);thread.join(timeout=2)
            result=subprocess.run(['ps','-axo','pgid='],capture_output=True,text=True,check=True,timeout=1)
            if str(process.pid) in result.stdout.split() or thread.is_alive() or errors:
                raise RuntimeError('installation cleanup/log retention failed')
    if time.monotonic()-started>=900: raise TimeoutError('install including cleanup exceeded')
    control.save('install.json',{'status':'completed', 'first_cell_monotonic':started,
                               'elapsed_seconds':time.monotonic()-started})
