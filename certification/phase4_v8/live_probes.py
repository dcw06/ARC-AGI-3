"""Live probe adapter. Import is inert; v6 live authority remains closed."""
from pathlib import Path


def require_live_authority(root=None):
    from certification.phase4_v8.authority import require
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
        from certification.phase4_v8.monitor import VRAM
        return bind_gpu(VRAM)

    def sample(self, uuid, ceiling):
        from evaluation.phase4_preflight import sample_gpu
        return sample_gpu(uuid, ceiling)

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
