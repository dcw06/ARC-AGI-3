"""Pin and derive the previously reviewed lifecycle, packaging and SDK boundary.

The scientific interface/flow is imported unchanged from the frozen CPU study.
The new worker and independent content auditor are separately reviewed sources.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT/'research/feedback_summary_probe_live_v1'
DEST = ROOT/'research/action_effect_choice_live_v1'


def derive():
    pins = json.loads(Path(__file__).with_suffix('.parents.json').read_bytes())
    files = {}
    for name, pin in pins.items():
        raw = (PARENT/name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != pin:
            raise ValueError('lifecycle derivation parent changed: '+name)
        text = raw.decode().replace('feedback_summary_probe', 'action_effect_choice')
        text = text.replace('feedback-summary-probe', 'action-effect-choice')
        text = text.replace('FEEDBACK_SUMMARY_PROBE', 'ACTION_EFFECT_CHOICE')
        files[name] = text
    runtime = files['live_runtime.py']
    runtime = runtime.replace("'generations': 81, 'counted_HTTP_requests': 81", "'generations': 33, 'counted_HTTP_requests': 33")
    runtime = runtime.replace("'recognition_generations': 16, ", '')
    runtime = runtime.replace("'policy_actions': 64", "'policy_actions': 32").replace("'offline_engine_actions': 116", "'offline_engine_actions': 84")
    runtime = runtime.replace("worker['continuations']", "worker['conditions']")
    runtime = runtime.replace(" or\n                len(worker['recognition']) != 16", '')
    files['live_runtime.py'] = runtime
    package = files['live_package.py']
    package = package.replace("execution_sources = source_inventory(root, execution_roots)",
        "execution_roots += ['research/action_effect_choice_v1/protocol.json']\n    execution_sources = source_inventory(root, execution_roots)")
    package = package.replace("glob('test_feedback_summary_live_*.py')", "glob('test_action_effect_live_*.py')")
    package = package.replace("'scripts/audit_action_effect_choice_live_tokens_v1.py', 'research/action_effect_choice_v1/protocol.json'",
        "'scripts/derive_action_effect_choice_live_v1.parents.json', 'research/action_effect_choice_v1/protocol.json', 'research/action_effect_choice_v1/scoring.py', 'research/action_effect_choice_live_v1/audit.py'")
    package = package.replace('Private paired feedback-probe gameplay study.', 'Private paired candidate-forecast and two-action diagnostic.')
    files['live_package.py'] = package
    evaluation = files['live_evaluation.py']
    start = evaluation.index('def audit_study(')
    end = evaluation.index('\ndef evaluate(', start)
    evaluation = evaluation[:start]+'from .audit import audit_study\n\n'+evaluation[end:]
    evaluation = evaluation.replace('from .audit import audit_continuation\n', '')
    evaluation = evaluation.replace('from research.action_effect_choice_v1.audit import audit_recognition_request\n', '')
    evaluation = evaluation.replace('from .interface import recognition_key, recognition_request\n', '')
    evaluation = evaluation.replace('from .scoring import score_recognition\n', '')
    files['live_evaluation.py'] = evaluation
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    files = derive()
    DEST.mkdir(exist_ok=True)
    for name, text in files.items():
        path = DEST/name
        raw = text.encode()
        if args.check:
            if path.read_bytes() != raw: raise ValueError('derived source drift: '+name)
        else: path.write_bytes(raw)
    print(json.dumps({'derived_files': len(files), 'matched': True, 'GPU_jobs': 0}))


if __name__ == '__main__': main()
