"""Run the exact 110-client development workload under the external supervisor."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from certification.phase4_v1.lifecycle import validate_freeze
from certification.phase4_v2.supervisor import supervise, save
from certification.phase4_v2.evaluate import evaluate
from certification.phase4_v2.package import verify_environment_mount


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environments', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--package-manifest', type=Path, default=ROOT / 'reports/phase4_v2_offline_package.json')
    args = parser.parse_args()
    _, rows = validate_freeze()
    verify_environment_mount(args.environments, json.loads(args.package_manifest.read_text()))
    command = lambda scratch: [sys.executable, str(Path(__file__).with_name('worker.py')),
                                str(scratch), str(args.environments.resolve())]
    result = supervise(command, args.output)
    evaluation = evaluate(result, rows)
    save(args.output / 'evaluation.json', evaluation)
    print(json.dumps(evaluation))
    raise SystemExit(0 if evaluation['passed'] else 1)
