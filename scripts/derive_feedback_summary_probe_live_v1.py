"""Derive the 81-request live package from the retained 73-request runtime.

The completed study and CPU snapshot are never edited. --check is read-only.
Parent bytes are pinned; explicit replacements fail if a template drifts.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = 'research/feedback_summary_probe_live_v1/'
PARENT_PINS = {'research/feedback_probe_v1/live_evaluation.py': '2ac4ef7ce8dd48bc1b89a4479e80543953d265b0ea1496ad1f9e4151c2c0a22c', 'research/feedback_probe_v1/live_operator.py': '13c36a5ea25c1d6890a9fa2c14a02b77f1ab0c53dc7b024746ea70a066e3aff4', 'research/feedback_probe_v1/live_package.py': '59abba62ec324a51de37675177b6f472d8609ad68305dd3c92fd989c4bde4390', 'research/feedback_probe_v1/live_runtime.py': '80ee35247129f67b8bf843a4d1aba816d0aa1a942dd761600c0a89b05b82e162', 'research/feedback_probe_v1/live_worker.py': '461b365acbfe7e45c751f52c81aa08b3bfb2431fadc6fd91218a9b2c3d53fdf9', 'research/feedback_probe_v1/runtime_template.json': '0378951a48cc7bf1e83dc3198513af9746e80e5725faf6c1da5eb56baba42266', 'research/feedback_summary_probe_v1/protocol.json': 'a5897001cbc6d97ffbe8f7f086d7a73b240d5b3dfdd5a5ac13b62926ed1db312', 'scripts/build_feedback_probe_live_v1.py': '687a7be715283f62abb09f179ddd728b792a21ba21aa0099abb203b263008c4b', 'scripts/rehearse_feedback_probe_live_v1.py': 'e1bd7eec63290c559b350494fa7747712d1e9395b4b94a1eaaf73b7a3bb97518', 'tests/test_feedback_probe_live_evaluation_v1.py': 'c930557128df95c706d7f59de9f60e0ca4e42f3d59572bea15d1768258caa63f', 'tests/test_feedback_probe_live_operator_v1.py': 'ba27d533a35728bf6849b99da713cd21e420ff701eb1d27ce1a740c7ab887e6c', 'tests/test_feedback_probe_live_package_v1.py': 'b1ed4d4ace797e8b817098603760a821a26ea946ad7199b90fc1c2138492e27b', 'tests/test_feedback_probe_live_worker_v1.py': '6147ea257d67777a7f7f99a37d033977e3f1e8a13e129dcc233d5412a496b654', 'tests/test_feedback_probe_sources_v1.py': 'fd6db542b280b061577bad6b8fd327daa663714b87c6008558fb5d0299590158'}


def parent(name):
    raw = (ROOT/name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PARENT_PINS[name]:
        raise ValueError('pinned derivation parent changed: '+name)
    return raw.decode()


def change(value, old, new):
    if old not in value:
        raise ValueError('derivation replacement missing: '+old[:80])
    return value.replace(old, new)


def common(value):
    for old, new in (
        ('research.feedback_probe_v1', 'research.feedback_summary_probe_live_v1'),
        ('research/feedback_probe_v1/', DEST),
        ('feedback_probe_live_fixture', 'feedback_summary_live_fixture'),
        ('feedback_probe_live_v1', 'feedback_summary_probe_live_v1'),
        ('feedback_probe_', 'feedback_summary_probe_'),
        ('FEEDBACK_PROBE', 'FEEDBACK_SUMMARY_PROBE'),
        ('feedback-probe-', 'feedback-summary-probe-'),
    ):
        value = value.replace(old, new)
    return value


def derive():
    files = {}
    for name in ('live_runtime.py', 'live_worker.py', 'live_package.py', 'live_operator.py', 'live_evaluation.py', 'runtime_template.json'):
        files[DEST+name] = common(parent('research/feedback_probe_v1/'+name))
    runtime = files[DEST+'live_runtime.py']
    runtime = change(runtime, "'generations': 73, 'counted_HTTP_requests': 73", "'generations': 81, 'counted_HTTP_requests': 81")
    runtime = change(runtime, "'recognition_generations': 8", "'recognition_generations': 16")
    runtime = change(runtime, "len(worker['recognition']) != 8", "len(worker['recognition']) != 16")
    files[DEST+'live_runtime.py'] = runtime
    worker = files[DEST+'live_worker.py']
    worker = change(worker, "ids.append((identity+'/recognition', 'recognition'))",
        "ids.extend((identity+'/'+variant+'/recognition', 'recognition') for variant in checkpoint['order'])")
    worker = worker.replace('len(ids) > 73', 'len(ids) > 81').replace('super().__init__(plan, 73, clock)', 'super().__init__(plan, 81, clock)')
    start = worker.index("            body = recognition_request(checkpoint['base_request'])")
    end = worker.index("            for variant in checkpoint['order']:", start)
    worker = worker[:start]+'''            for variant in checkpoint['order']:
                admission()
                body = recognition_request(checkpoint['base_request'], variant)
                retained = json.loads((inputs/'model-inputs'/(identity+'-'+variant+'-recognition.json')).read_bytes())
                if digest(body) != digest(retained):
                    raise ValueError('recognition request differs from sealed model input')
                recognition.append({'checkpoint_id': identity, 'variant': variant,
                                    'text': complete(identity+'/'+variant+'/recognition', body)})
'''+worker[end:]
    files[DEST+'live_worker.py'] = worker
    evaluation = files[DEST+'live_evaluation.py']
    evaluation = change(evaluation, 'from .audit import audit_continuation',
        'from .audit import audit_continuation\nfrom research.feedback_summary_probe_v1.audit import audit_recognition_request')
    old = '''        recognition_id = identity+'/recognition'
        expected[recognition_id] = recognition_request(checkpoint['base_request'])
        expected_interleaving.append(('HTTP', recognition_id))
        recognition_expected.append((checkpoint, recognition_id))'''
    new = '''        for variant in checkpoint['order']:
            recognition_id = identity+'/'+variant+'/recognition'
            expected[recognition_id] = recognition_request(checkpoint['base_request'], variant)
            audit_recognition_request(checkpoint, variant, expected[recognition_id])
            expected_interleaving.append(('HTTP', recognition_id))
            recognition_expected.append((checkpoint, variant, recognition_id))'''
    evaluation = change(evaluation, old, new)
    evaluation = change(evaluation, 'for checkpoint, identity in recognition_expected:', 'for checkpoint, variant, identity in recognition_expected:')
    evaluation = change(evaluation, "'stratum': checkpoint['stratum'],\n                            'score':", "'stratum': checkpoint['stratum'], 'variant': variant,\n                            'score':")
    evaluation = change(evaluation, "raw_recognition = [{'checkpoint_id': checkpoint['checkpoint_id'], 'text': by_id[identity]['content']}\n                       for checkpoint, identity in recognition_expected]",
        "raw_recognition = [{'checkpoint_id': checkpoint['checkpoint_id'], 'variant': variant, 'text': by_id[identity]['content']}\n                       for checkpoint, variant, identity in recognition_expected]")
    evaluation = evaluation.replace("ledger.get('maximum_model_requests'), 73", "ledger.get('maximum_model_requests'), 81")
    evaluation = evaluation.replace('len(recognition) != 8', 'len(recognition) != 16').replace('len(calls) != 9+', 'len(calls) != 17+').replace('len(calls) > 73', 'len(calls) > 81')
    files[DEST+'live_evaluation.py'] = evaluation
    package = files[DEST+'live_package.py']
    package = change(package, "for p in (root/'tests').glob('test_feedback_summary_probe_*v1.py')", "for p in (root/'tests').glob('test_feedback_summary_live_*.py')")
    package = change(package, "    sources = source_inventory(root, review_roots)",
        "    review_roots += ['scripts/derive_feedback_summary_probe_live_v1.py', 'scripts/audit_feedback_summary_probe_live_tokens_v1.py', 'research/feedback_summary_probe_v1/protocol.json']\n    sources = source_inventory(root, review_roots)")
    files[DEST+'live_package.py'] = package
    for prefix in ('build', 'rehearse'):
        source = parent(f'scripts/{prefix}_feedback_probe_live_v1.py')
        files[f'scripts/{prefix}_feedback_summary_probe_live_v1.py'] = common(source)
    rehearsal = files['scripts/rehearse_feedback_summary_probe_live_v1.py']
    rehearsal = change(rehearsal, "recognition_key(c['base_request']) for c in checkpoints}",
        "recognition_key(c['base_request']) for c in checkpoints for variant in c['order']}")
    rehearsal = change(rehearsal, "digest(recognition_request(c['base_request'])):", "digest(recognition_request(c['base_request'], variant)):")
    files['scripts/rehearse_feedback_summary_probe_live_v1.py'] = rehearsal
    files[DEST+'__init__.py'] = '"""Separately reviewed 81-request feedback-summary live study."""\n'
    files[DEST+'continuation.py'] = 'from research.feedback_summary_probe_v1.continuation import continuation\n'
    files[DEST+'audit.py'] = 'from research.feedback_summary_probe_v1.audit import audit_continuation\n'
    files[DEST+'interface.py'] = ('from research.feedback_summary_probe_v1.interface import VARIANTS, policy_request, recognition_request\n'
        'from research.feedback_probe_v1.interface import recognition_key, RECOGNITION_SYSTEM\n')
    files[DEST+'scoring.py'] = 'from research.feedback_probe_v1.scoring import score_recognition\n'
    files[DEST+'source_closure.py'] = ('from research.feedback_probe_v1.source_closure import (\n'
        '    source_inventory, source_payload, verify_source_inventory, safe_member, write_source_payload)\n')
    files[DEST+'protocol.json'] = parent('research/feedback_summary_probe_v1/protocol.json')
    for kind in ('worker', 'evaluation', 'package', 'operator', 'sources'):
        name = f'tests/test_feedback_probe_live_{kind}_v1.py' if kind != 'sources' else 'tests/test_feedback_probe_sources_v1.py'
        text = common(parent(name))
        text = text.replace('tests.test_feedback_summary_probe_audit_v1', 'tests.test_feedback_probe_audit_v1')
        if kind == 'worker':
            for old, new in [('len(plan), 73', 'len(plan), 81'), ("for p in plan), 8", "for p in plan), 16"),
                ("['issued'], 73", "['issued'], 81"), ("len(result['recognition']), 8", "len(result['recognition']), 16"),
                ("['issued'], 25", "['issued'], 33")]:
                text = change(text, old, new)
        if kind == 'evaluation': text = change(text, '(73, 36, 64, 116, 16)', '(81, 36, 64, 116, 16)')
        if kind == 'sources':
            text = change(text, 'from research.feedback_summary_probe_live_v1.preparation import verify_prepared',
                          'from research.feedback_probe_v1.preparation import verify_prepared')
        files[f'tests/test_feedback_summary_live_{kind}.py'] = text
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    files = derive()
    for name, value in sorted(files.items()):
        path = ROOT/name
        raw = value.encode()
        if args.check:
            if not path.is_file() or path.read_bytes() != raw: raise ValueError('derived file differs: '+name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    print(json.dumps({'derived_files':len(files),'matched':True,'GPU_jobs':0,'provider_writes':0}))


if __name__ == '__main__': main()
