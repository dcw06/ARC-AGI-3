"""Compare pre-fix/fixed admission using real pinned files but no raw evidence.

Private retained inputs are required; nothing is published or inferred. This
isolates the reported gap: an authenticated comparison file is not a replay.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.initial_geometry_assistance_v1.prepare import build_inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--control-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('preserve previous regression records')
    source = subprocess.check_output(['git', 'show', '49475e8:research/initial_geometry_assistance_v1/prepare.py'], cwd=ROOT)
    module = types.ModuleType('research.initial_geometry_assistance_v1.baseline_prepare')
    module.__package__ = 'research.initial_geometry_assistance_v1'
    # Keep the current protocol only for the unchanged six-board schedule.
    # The baseline source did not check automatic-artifact/provenance pins in it.
    module.__file__ = str(ROOT/'research/initial_geometry_assistance_v1/prepare.py')
    exec(compile(source, '49475e8/prepare.py', 'exec'), module.__dict__)
    with tempfile.TemporaryDirectory(prefix='initial-geometry-flag-only-') as folder:
        thin = Path(folder)
        names = ['gpu-live-review-r1/references/confirmed-review.json', 'sam-comparison-evaluation-r1.json',
                 'control-independent-evaluation-r1.json']
        names += [f'preparation-r1/inputs/board-{i:02d}.png' for i in range(1, 7)]
        for name in names:
            dest = thin/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(args.control_root/name, dest)
        inputs = [thin/n for n in names[:3]] + [thin/'preparation-r1/inputs']
        # Signature is reference, automatic, source, image directory, output.
        module.build_inputs(*inputs, thin/'baseline-output')
        refused = None
        try:
            build_inputs(*inputs, thin/'fixed-output', control_root=thin,
                         molmopoint_checkpoint=thin/'absent-checkpoint', sam_acquisition=thin/'absent-acquisition')
        except (ValueError, FileNotFoundError) as exc:
            refused = type(exc).__name__ + ': ' + str(exc)
        if refused is None or (thin/'fixed-output').exists():
            raise AssertionError('fixed preparation admitted flags without retained evidence')
        record = {'schema': 'initial_geometry_real_flag_only_regression_v1', 'baseline_commit': '49475e8',
                  'baseline_accepted_pinned_flags_without_raw_evidence': True,
                  'fixed_refused_before_output': True, 'fixed_refusal_type': refused.split(':', 1)[0],
                  'supplied_pinned_inputs': len(names), 'raw_SAM_logits_supplied': False,
                  'provider_evidence_supplied': False, 'model_generations': 0, 'GPU_jobs': 0}
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(record, stream, indent=2); stream.write('\n')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
