"""Externally owned CPU rehearsal of Stage B; no live GPU mode."""
import json
from pathlib import Path
import sys
import tempfile
import time

from certification.phase4_integrated_v2.outer import run_local
from .replay import replay_file


def run_review(output, *, seconds=90, fault='none'):
    if fault not in ('none', 'startup', 'cancel', 'evidence') or not 20 <= seconds <= 180:
        raise ValueError('review fixture limits')
    started = time.monotonic()
    output = Path(output)
    data_root = output.with_name(output.name + '-data')
    data_root.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='stage-b-owned-fixture-') as folder:
        scratch = Path(folder)
        command = [sys.executable, '-m', 'research.grounded_action_v1.target_fixture', 'worker',
                   '--output', str(output), '--data-root', str(data_root), '--scratch', str(scratch),
                   '--deadline', str(started + seconds - 10), '--fault', fault]
        def monitor(pid, root):
            return [sys.executable, '-m', 'certification.phase4_integrated_v2.monitor',
                    '--injected', str(pid), str(root / 'monitor')]
        report = run_local(command, monitor, output, seconds=seconds, reserve=10,
                           started=started, readiness_seconds=10)
    report['scratch_removed'] = not scratch.exists()
    report['data_root'] = str(data_root)
    if report['status'] == 'local_commands_completed_pending_evidence_review':
        try:
            replay = replay_file(data_root / 'record.json')
            report['replay_status'] = replay['status']
            report['calls'] = replay['calls']
            report['dispatches'] = replay['dispatches']
            report['status'] = 'review_cpu_fixture_verified'
        except Exception as exc:
            report.update(status='failed', error=type(exc).__name__ + ': ' + str(exc)[:256])
    (output / 'review-result.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    return report


def main():
    raise PermissionError('Stage B review supervisor has no live GPU entrypoint')


if __name__ == '__main__':
    main()
