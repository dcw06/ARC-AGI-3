"""Resource probes: live probes need this experiment's authority; rehearsal probes inject only the GPU."""
import csv
from pathlib import Path
import subprocess
import time

from certification.phase4_integrated_v2.monitor import VRAM, validate_binding, validate_sample


class LiveProbes:
    evidence_class = 'live'

    def __init__(self, worker_pid, scratch, *, root=None):
        from .authority import require
        require() if root is None else require(root)
        if type(worker_pid) is not int or worker_pid <= 0:
            raise ValueError('invalid owned worker PID')
        self.worker_pid, self.scratch = worker_pid, Path(scratch)

    def bind(self):
        from evaluation.phase4_target import bind_gpu
        binding = bind_gpu(VRAM)
        validate_binding(binding)
        return binding

    def sample(self, uuid):
        result = subprocess.run(['nvidia-smi', '--query-gpu=uuid,name,memory.total,memory.used',
                                 '--format=csv,noheader,nounits'], capture_output=True, text=True, check=True, timeout=2)
        rows = list(csv.reader(result.stdout.strip().splitlines()))
        if len(rows) != 1 or len(rows[0]) != 4:
            raise ValueError('ambiguous GPU sample')
        identity, name, total, used = (part.strip() for part in rows[0])
        sample = {'uuid': identity, 'name': name, 'total_bytes': int(total) * 1024**2, 'used_bytes': int(used) * 1024**2}
        validate_sample(sample, uuid)
        return sample

    def rss(self, pid):
        if type(pid) is not int or pid != self.worker_pid:
            raise ValueError('RSS probe is bound to the owned worker')
        from evaluation.phase4_runner import group_rss_bytes
        return group_rss_bytes(pid)

    def scratch_bytes(self):
        if not self.scratch.is_dir() or self.scratch.is_symlink():
            raise ValueError('invalid monitored scratch')
        from evaluation.phase4_runner import tree_bytes
        return tree_bytes(self.scratch)

    def gpu_pids(self):
        from evaluation.phase4_target import gpu_pids
        return gpu_pids()


class RehearsalProbes(LiveProbes):
    """Real RSS and scratch measurement; the GPU identity and VRAM are injected (never target evidence)."""
    evidence_class = 'rehearsal_injected_gpu_not_target_evidence'
    FIXTURE = {'uuid': 'GPU-REHEARSAL-INJECTED', 'name': 'RTX PRO 6000 (injected rehearsal)',
               'total_bytes': 96 * 1024**3, 'used_bytes': 1}

    def __init__(self, worker_pid, scratch, *, root=None):
        from .authority import rehearsal_gate
        rehearsal_gate()
        if type(worker_pid) is not int or worker_pid <= 0:
            raise ValueError('invalid owned worker PID')
        self.worker_pid, self.scratch = worker_pid, Path(scratch)

    def bind(self):
        return {'gpu_uuid': self.FIXTURE['uuid'], 'max_used_vram_bytes': VRAM, 'initial_telemetry': dict(self.FIXTURE)}

    def sample(self, uuid):
        sample = dict(self.FIXTURE)
        validate_sample(sample, uuid)
        return sample

    def gpu_pids(self):
        return []


def probes_for(mode):
    if mode == 'live':
        return LiveProbes
    if mode == 'rehearsal':
        return RehearsalProbes
    raise ValueError('mode')


def independent_cleanup(probes, *, expected_uuid, groups_absent, deadline, clock=time.monotonic):
    """Fresh GPU query after process cleanup, retaining a separate verdict."""
    result = {'scope': 'action_effect_history_independent_gpu_cleanup', 'evidence_class': probes.evidence_class,
              'gpu_cleanup_verified': False, 'groups_absent': groups_absent, 'error': None}
    try:
        if clock() >= deadline:
            raise TimeoutError('GPU cleanup deadline')
        sample = probes.sample(expected_uuid)
        pids = probes.gpu_pids()
        if sample['uuid'] != expected_uuid or not groups_absent or pids:
            raise RuntimeError('process group or GPU process remains')
        result.update(gpu_uuid=sample['uuid'], remaining_gpu_pids=0, gpu_cleanup_verified=True)
    except Exception as exc:
        result['error'] = type(exc).__name__ + ': ' + str(exc)[:256]
    return result
