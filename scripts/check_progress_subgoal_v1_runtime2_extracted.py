"""Import-closure check of the frozen review notebook's payload (CPU only; Linux; scripted stub, fixture wheels).

The exact embedded payload of notebooks/progress-subgoal-v1-runtime2-review-r<N>/profile.ipynb is decoded (hashes
checked, nothing executed from the notebook cell) into a temporary directory. Then, in an isolated interpreter
(`python -I`, the payload as the only repository path), the complete CPU rehearsal of the derived lifecycle runs
from that payload alone: fixture installation, the scripted stub as an owned process group, all 5,852 frozen
questionnaire calls, cancellation probes, cleanup and evidence. Every repository module the run imported must come from
the payload. The retained evidence is then evaluated independently against the payload's own frozen files.

Not GPU or model evidence; the scripted answers' labels are not results.

Usage: python scripts/check_progress_subgoal_v1_runtime2_extracted.py --revision 7 [--out FILE]
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SCRIPT = r'''import json, os, sys
from pathlib import Path
root, folder = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(root))
os.environ['CUDA_VISIBLE_DEVICES'] = ''
from research.progress_subgoal_v1_runtime2.rehearsal import scenario
result, protocol = scenario(root, folder, 'none', 'scripted')
(folder / 'declared-protocol.json').write_text(json.dumps(protocol, sort_keys=True, indent=1) + '\n')
outside = sorted(name for name, module in sys.modules.items()
                 if name.split('.')[0] in ('research', 'certification', 'scripts', 'agent', 'evaluation')
                 and getattr(module, '__file__', None) and not Path(module.__file__).resolve().is_relative_to(root.resolve()))
print(json.dumps({'passed': result['passed'], 'failed_stage': result['failed_stage'], 'error': result['error'],
                  'cleanup_verified': result['cleanup_verified'], 'issued': result['ledger']['issued'],
                  'questionnaire': result.get('questionnaire'), 'modules_outside_payload': outside,
                  'evidence_class': result['evidence_class'], 'lifecycle_seconds': result['elapsed_seconds'],
                  'phases': [[p['phase'], p['seconds']] for p in result['phases']]}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', type=int, default=7)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if sys.platform != 'linux':
        raise SystemExit('Linux required for process-group and CPU fixture controls')
    from scripts.check_progress_subgoal_v1_runtime2_embedded_inputs import check, extract
    from scripts.evaluate_progress_subgoal_v1_runtime2 import evaluate_output
    folder = ROOT / f'notebooks/progress-subgoal-v1-runtime2-review-r{args.revision}'
    notebook = json.loads((folder / 'profile.ipynb').read_bytes())
    inputs = check(notebook)  # the extracted payload's default trusted-input path (174 wheels), isolated
    work = Path(tempfile.mkdtemp(prefix='psv1r2-extracted-', dir=Path.home()))
    try:
        payload = work / 'payload'
        payload.mkdir()
        extract(notebook, payload)
        env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'VIRTUAL_ENV')}
        env['CUDA_VISIBLE_DEVICES'] = ''
        begun = time.monotonic()
        process = subprocess.run([sys.executable, '-I', '-c', SCRIPT, str(payload), str(work / 'rehearsal')],
                                 cwd=work, env=env, capture_output=True, text=True, timeout=3600)
        rehearsal_seconds = round(time.monotonic() - begun, 1)
        try:
            run = json.loads(process.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            run = {'passed': False, 'stderr': process.stderr[-1500:]}
        evaluation, begun = None, time.monotonic()
        if (work / 'rehearsal/declared-protocol.json').is_file():
            declared = json.loads((work / 'rehearsal/declared-protocol.json').read_bytes())
            value = evaluate_output(work / 'rehearsal/evidence', mode='rehearsal', root=payload, protocol=declared)
            evaluation = {k: value[k] for k in ('technically_complete', 'gate_status', 'gate', 'lifecycle_errors',
                                                'call_errors')}
            evaluation['seconds'] = round(time.monotonic() - begun, 1)
        record = {'schema': 'progress_subgoal_v1_runtime2_extracted_payload_check_v1', 'review_revision': args.revision,
                  'evidence_class': 'scripted_cpu_rehearsal', 'gpu_compatibility_evidence': False, 'gpu_used': False,
                  'model_calls': 0, 'provider_calls': 0, 'default_trusted_inputs': inputs, 'exit_code': process.returncode,
                  'isolated_rehearsal': run, 'isolated_rehearsal_wall_seconds': rehearsal_seconds,
                  'independent_evaluation': evaluation,
                  'passed': (inputs.get('passed') is True and process.returncode == 0 and run.get('passed') is True
                             and run.get('modules_outside_payload') == [] and evaluation is not None
                             and evaluation['technically_complete'] is True),
                  'note': 'scripted CPU stub, fixture wheels; labels are not results'}
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if args.out:
        args.out.write_bytes((json.dumps(record, sort_keys=True, indent=1) + '\n').encode())
    print(json.dumps({k: record[k] for k in ('passed', 'exit_code')} | {'run': record['isolated_rehearsal']}, indent=1))
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
