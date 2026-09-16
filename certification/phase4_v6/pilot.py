"""One integrated development pilot; live mode remains explicitly unauthorized."""
import json
import math
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import tempfile
import threading
import time

from certification.phase4_v6.evidence import EvidenceStore
from certification.phase4_v6.live_probes import require_live_authority
from certification.phase4_v6.outer import signal_owned, group_present

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    if path.is_symlink() or path.stat().st_size > 32*1024**2:
        raise ValueError('invalid evidence file')
    return json.loads(path.read_text())


def run(output, environments, *, mode='local', seconds=90, reserve=10,
        started=None, fault='none', prepared=False):
    if mode not in ('local','live') or fault not in ('none','worker','monitor','evidence','cancel'):
        raise ValueError('invalid pilot mode/fault')
    if mode == 'live':
        require_live_authority()  # Before output, subprocesses, installation or GPU queries.
        if seconds != 27540 or reserve != 600 or fault != 'none':
            raise ValueError('live protocol drift')
    if (any(type(v) not in (float,int) or not math.isfinite(v) for v in (seconds,reserve))
            or not 5 < reserve < seconds):
        raise ValueError('invalid pilot deadline')
    started = time.monotonic() if started is None else started
    if type(started) not in (float,int) or not math.isfinite(started) or not 0 <= time.monotonic()-started < seconds-reserve:
        raise ValueError('invalid/exhausted first-cell clock')
    output = Path(output).resolve()
    if prepared:
        if not output.is_dir() or (output/'control/ownership.json').exists():
            raise ValueError('invalid/already-consumed prepared output')
    else:
        output.mkdir(parents=True, exist_ok=False)
    control = EvidenceStore(output, 'control')
    logs = EvidenceStore(output, 'logs')
    report = {'status':'failed', 'error':None, 'scope':mode+'_development_pilot',
        'first_cell_monotonic':started, 'worker_released':False, 'cleanup_verified':False,
        'phase4_complete':False, 'target_gpu_certified':False}
    owned, drainers, log_errors = [], [], []
    rfd = wfd = None
    def drain(process, name):
        data = bytearray()
        try:
            while chunk := process.stdout.read(4096):
                if len(data)+len(chunk) > 3*1024**2:
                    raise ValueError('bounded process log exhausted')
                data.extend(chunk)
                logs.write(name+'.json', bytes(data))
        except Exception as exc:
            log_errors.append(type(exc).__name__+': '+str(exc)[:256])
            # Close the pipe; parent fails and kills the entire owned group.
        finally:
            process.stdout.close()
    def launch(argv, **extra):
        process = subprocess.Popen(argv, cwd=ROOT, start_new_session=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **extra)
        owned.append(process)
        thread = threading.Thread(target=drain, args=(process,str(process.pid)), daemon=True)
        thread.start(); drainers.append(thread)
        return process
    def cleanup(process):
        signal_owned(process, signal.SIGTERM)
        try: process.wait(timeout=.2)
        except subprocess.TimeoutExpired: pass
        signal_owned(process, signal.SIGKILL)
        process.wait(timeout=1)
        deadline = time.monotonic()+1
        while group_present(process.pid) and time.monotonic()<deadline: time.sleep(.02)
        if group_present(process.pid): raise RuntimeError('owned descendants remain')
    def check_deadline():
        elapsed = time.monotonic()-started
        if elapsed >= seconds-reserve and not report.get('admission_canceled'):
            control.save('cancel.json', {'elapsed_seconds':elapsed})
            report['admission_canceled'] = True
        if elapsed >= seconds-4: raise TimeoutError('external deadline reserves cleanup')
        if log_errors: raise RuntimeError('log retention failed: '+log_errors[0])
    with tempfile.TemporaryDirectory(prefix='p4-v6-pilot-') as temp:
        scratch = Path(temp)
        try:
            common = ['--mode',mode,'--output',str(output),'--scratch',str(scratch),
                '--environments',str(Path(environments).resolve()),'--started',str(started),
                '--seconds',str(seconds),'--reserve',str(reserve),'--fault',fault]
            child = [sys.executable,'-m','certification.phase4_v6.pilot_child']
            rfd,wfd = os.pipe()
            worker = launch([sys.executable,str(ROOT/'certification/phase4_v6/gated_exec.py'),
                             str(rfd),*child,'worker',*common], pass_fds=(rfd,))
            os.close(rfd); rfd=None
            nonce = secrets.token_hex(32)
            monitor = launch([*child,'monitor',*common,'--worker-pid',str(worker.pid),'--nonce',nonce])
            control.save('ownership.json', {'worker_pgid':worker.pid,'monitor_pgid':monitor.pid,
                'first_cell_monotonic':started,'nonce':nonce})
            ready_deadline = min(started+seconds-reserve, time.monotonic()+30)
            while not (output/'monitor/ready.json').exists():
                check_deadline()
                if time.monotonic()>=ready_deadline: raise TimeoutError('monitor ready timeout')
                if monitor.poll() is not None: raise RuntimeError('monitor failed before release')
                time.sleep(.02)
            ready = read(output/'monitor/ready.json')
            from certification.phase4_v6.monitor import validate_binding
            uuid = validate_binding(ready['gpu_binding'])
            expected_scope = 'live_resource_monitor' if mode=='live' else 'injected_resource_monitor_not_target_evidence'
            if (ready['nonce']!=nonce or ready['worker_pid']!=worker.pid or ready['monitor_pid']!=monitor.pid
                    or ready['scope']!=expected_scope or ready['sample']['uuid']!=uuid):
                raise ValueError('ready identity mismatch')
            telemetry = read(output/'monitor/telemetry.json')
            if not telemetry['samples'] or telemetry['samples'][0]!=ready['sample']:
                raise ValueError('ready not backed by retained sample')
            check_deadline()
            if monitor.poll() is not None or time.monotonic()>=ready_deadline:
                raise RuntimeError('ready expired')
            report['worker_started_seconds'] = time.monotonic()-started
            os.write(wfd,b'G'); os.close(wfd); wfd=None
            report['worker_released']=True
            while worker.poll() is None:
                check_deadline()
                if monitor.poll() is not None: raise RuntimeError('monitor failed with live worker')
                if mode=='live' and not (output/'worker/model-ready.json').exists() and time.monotonic()-started-report['worker_started_seconds']>900:
                    raise TimeoutError('model startup ceiling')
                time.sleep(.02)
            report['child_returncode']=worker.returncode
            cleanup_started=time.monotonic()
            cleanup(worker)  # Monitor keeps sampling through model-group teardown.
            report['worker_stopped_seconds']=time.monotonic()-started
            report['cleanup_seconds']=time.monotonic()-cleanup_started
            control.save('stop-monitor.json', {'worker_group_absent':True,
                                              'elapsed_seconds':report['worker_stopped_seconds']})
            while monitor.poll() is None:
                check_deadline(); time.sleep(.02)
            if worker.returncode!=0 or monitor.returncode!=0: raise RuntimeError('child failure')
            report['cleanup_verified']=True
            receipt=read(output/'monitor/monitor-result.json')
            if mode=='live' and receipt.get('gpu_cleanup_verified') is not True:
                raise RuntimeError('missing actual GPU cleanup')
            report['cleanup_seconds']=time.monotonic()-cleanup_started
            report['gpu_cleanup_verified']=receipt.get('gpu_cleanup_verified',False)
            report['worker']=read(output/'worker/state.json')
            from certification.phase4_v6.evaluate import monitor_fields
            report.update(monitor_fields(receipt,read(output/'monitor/telemetry.json'), first_cell_monotonic=started))
            report['status']='worker_completed_pending_independent_evaluation'
        except Exception as exc:
            report['error']=type(exc).__name__+': '+str(exc)[:512]
        finally:
            for fd in (rfd,wfd):
                if fd is not None: os.close(fd)
            try:
                for process in owned: cleanup(process)
                report['cleanup_verified']=True
            except Exception as exc:
                report['error']=report['error'] or 'cleanup: '+str(exc)[:256]
                report['cleanup_verified']=False
            for thread in drainers: thread.join(timeout=1)
            if log_errors or any(t.is_alive() for t in drainers):
                report['error']=report['error'] or 'log retention incomplete'
            from evaluation.phase4_runner import tree_bytes
            report['final_scratch_bytes']=tree_bytes(scratch)
    report['scratch_removed']=not scratch.exists()
    report['elapsed_seconds']=time.monotonic()-started
    if report['error'] or report.get('admission_canceled') or report['elapsed_seconds']>=seconds:
        report['status']='failed'
    # Worker evidence remains in worker/state.json; do not duplicate full journals.
    control.save('outer.json', {k:v for k,v in report.items() if k not in ('worker','gpu_telemetry')})
    from certification.phase4_v1.lifecycle import validate_freeze
    _,rows=validate_freeze()
    if mode=='live':
        from certification.phase4_v6.evaluate import evaluate
    else:
        from certification.phase4_v3.evaluate import evaluate
    result=evaluate(report,rows)
    result.update(phase4_complete=False, target_gpu_certified=False, mode=mode)
    EvidenceStore(output,'evaluation').save('result.json',result)
    return report,result
