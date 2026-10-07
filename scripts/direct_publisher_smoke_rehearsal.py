"""Run every scripted CPU rehearsal of the direct publisher smoke test and retain the report (GPU disabled).

  python scripts/direct_publisher_smoke_rehearsal.py

Writes reports/direct_publisher_smoke_rehearsal.json and keeps the nominal scenario's evidence folder under
reports/direct_publisher_smoke_rehearsal_evidence/. This is scripted rehearsal evidence of the control code only; it is
not GPU compatibility evidence. Exits 1 if any scenario does not behave as expected.
"""
import datetime
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from certification.direct_publisher_smoke_v1.binding import LiveRefused, require_live  # noqa: E402
from certification.direct_publisher_smoke_v1.evidence import REHEARSAL_LIMITS  # noqa: E402
from certification.direct_publisher_smoke_v1.rehearsal import SCENARIOS, scenario  # noqa: E402

REPORT = ROOT / 'reports/direct_publisher_smoke_rehearsal.json'
KEPT = ROOT / 'reports/direct_publisher_smoke_rehearsal_evidence'


def main():
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    try:
        require_live(ROOT)
        live_gate = {'refused': False}
    except LiveRefused as exc:
        live_gate = {'refused': True, 'reasons': exc.reasons}
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    rows = []
    if not KEPT.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('rehearsal evidence directory escapes the checkout')
    with tempfile.TemporaryDirectory(prefix='direct-publisher-smoke-rehearsal-') as base:
        for name in SCENARIOS:
            summary, result = scenario(name, base)
            if name == 'nominal':
                shutil.rmtree(KEPT, ignore_errors=True)
                shutil.copytree(summary['evidence_dir'], KEPT / 'nominal')
            summary.pop('evidence_dir')
            rows.append(summary)
            print(f"{name:28} {'as expected' if summary['as_expected'] else 'UNEXPECTED'}  "
                  f"stage={summary['failed_stage']}  requests={summary['requests_issued']}")
    report = {
        'schema': 'direct_publisher_smoke_rehearsal_v1',
        'evidence_class': 'scripted_cpu_rehearsal',
        'gpu_compatibility_evidence': False,
        'limits_of_this_evidence': REHEARSAL_LIMITS,
        'source_revision': revision,
        'host': {'python': platform.python_version(), 'platform': platform.platform(),
                 'gpu': 'none (CUDA_VISIBLE_DEVICES empty; no GPU query is made in rehearsal mode)'},
        'ran_at': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
        'live_gate_on_this_checkout': live_gate,
        'scenarios': rows,
        'all_as_expected': all(r['as_expected'] for r in rows),
    }
    REPORT.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')
    return 0 if report['all_as_expected'] and live_gate['refused'] else 1


if __name__ == '__main__':
    sys.exit(main())
