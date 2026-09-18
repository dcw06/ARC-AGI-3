"""Load and verify portable v13 evidence, without changing historical records."""
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile
from certification.phase4_v13.evaluate import monitor_fields
from certification.phase4_v13.telemetry import read_telemetry

ROOT = Path(__file__).resolve().parents[2]


def load():
    read = lambda p: json.loads(p.read_text(encoding='utf-8'))
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    receipt = read(ROOT/'reports/phase4_v13_pilot_evaluation.json')
    archive = ROOT/receipt['evidence_archive']
    assert sha(archive) == receipt['evidence_archive_sha256']
    lock = read(ROOT/'notebooks/phase4-lifecycle-v13-review-r1/review-source-lock.json')
    for name, digest in lock['bindings'].items():
        assert sha(ROOT/name) == digest, name
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        with zipfile.ZipFile(archive) as bundle:
            for item in bundle.infolist():
                assert (root/item.filename).resolve().is_relative_to(root.resolve())
            bundle.extractall(root)
        for name, binding in receipt['evidence'].items():
            assert sha(root/name) == binding['sha256'], name
        out = root/'download/phase4-development-v13'
        final = read(out/'evaluation/notebook-result.json')
        assert final['passed'] and final['completed'] and final['source_removed']
        assert final['evaluation_sha256'] == sha(out/'evaluation/result.json')
        assert final['cleanup_sha256'] == sha(out/'control/notebook-cost.json')
        report = read(out/'control/outer.json')
        report['worker'] = read(out/'worker/state.json')
        report.update(monitor_fields(read(out/'monitor/monitor-result.json'),
            read_telemetry(out/'monitor'), first_cell_monotonic=report['first_cell_monotonic']))
    return report, read(ROOT/'certification/phase4_v1/workload.json')
