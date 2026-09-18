"""Live probe adapter. Import is inert; v6 live authority remains closed."""
from pathlib import Path


def require_live_authority(root=None):
    from certification.phase4_v12.authority import require
    return require(root)


class LiveResourceProbes:
    evidence_class = 'live_resource_probes'

    def __init__(self, worker_pid, scratch):
        require_live_authority()  # Before agent imports, ps or nvidia-smi.
        if type(worker_pid) is not int or worker_pid <= 0:
            raise ValueError('invalid owned worker PID')
        self.worker_pid = worker_pid
        self.scratch_path = Path(scratch)

    def bind(self):
        from evaluation.phase4_target import bind_gpu
        from certification.phase4_v12.monitor import VRAM
        return bind_gpu(VRAM)

    def sample(self, uuid, ceiling):
        # Return raw values so diagnostics can retain a rejected VRAM sample.
        # The monitor validates identity and the unchanged ceiling immediately.
        import csv
        import subprocess
        result=subprocess.run(['nvidia-smi','--query-gpu=uuid,name,memory.total,memory.used',
            '--format=csv,noheader,nounits'],capture_output=True,text=True,check=True,timeout=2)
        rows=list(csv.reader(result.stdout.strip().splitlines()))
        if len(rows)!=1 or len(rows[0])!=4: raise ValueError('ambiguous GPU telemetry')
        identity,name,total,used=[value.strip() for value in rows[0]]
        return {'uuid':identity,'name':name,'total_bytes':int(total)*1024**2,
                'used_bytes':int(used)*1024**2}

    def rss(self, worker_pid):
        if worker_pid != self.worker_pid:
            raise ValueError('worker ownership mismatch')
        from evaluation.phase4_runner import group_rss_bytes
        return group_rss_bytes(worker_pid)

    def scratch(self):
        # Reject links rather than omitting unknown disk consumption.
        if self.scratch_path.is_symlink() or not self.scratch_path.is_dir():
            raise ValueError('invalid scratch directory')
        total = 0
        for path in self.scratch_path.rglob('*'):
            if path.is_symlink():
                raise ValueError('symlink in scratch')
            if path.is_file():
                total += path.stat().st_size
        return total

    def gpu_processes(self):
        from evaluation.phase4_target import gpu_pids
        return gpu_pids()
