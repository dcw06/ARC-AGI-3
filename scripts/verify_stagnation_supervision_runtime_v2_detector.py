"""Write (once) or check the runtime v2 detector/integration verification receipt. CPU only; no model, GPU or provider.

  python -m scripts.verify_stagnation_supervision_runtime_v2_detector           # write the write-once receipt
  python -m scripts.verify_stagnation_supervision_runtime_v2_detector --check   # recompute and compare
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'reports/stagnation_supervision_runtime_v2_detector_verification.json'


def main():
    from research.stagnation_supervision_runtime_v2.verification import run
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = json.loads(json.dumps(run(), sort_keys=True))
    if args.check:
        if json.loads(OUT.read_bytes()) != result:
            raise SystemExit('recomputed verification differs from the retained receipt')
    else:
        if OUT.exists():
            raise SystemExit('write-once receipt exists: ' + str(OUT))
        if not result['passed']:
            raise SystemExit('verification failed; no receipt written')
        with OUT.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(result, indent=1, sort_keys=True) + '\n')
    print(json.dumps({k: (v['passed'] if isinstance(v, dict) and 'passed' in v else v)
                      for k, v in result.items() if k != 'frozen_files_sha256'}, indent=1))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
