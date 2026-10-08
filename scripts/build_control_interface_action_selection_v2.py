"""Derive a separate explicit-output-contract development probe; no provider/GPU/authority work.

Preserves v1 files and reuses its exact frozen observations. Edit this derivation
for generated v2 files. Token auditing and review freezing are separate steps.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = 'research/control_interface_action_selection_v1'
NEW = 'research/control_interface_action_selection_v2'
SCOPE = 'control-interface-action-selection-v2'
HEADER = '# Derived by scripts/build_control_interface_action_selection_v2.py; edit the derivation.\n'
CONTRACT = {
    'template': '{"action":{"action_id":INTEGER_ID,"action_data":ACTION_DATA}}',
    'integer_id': 'Replace INTEGER_ID with one currently legal JSON integer. Never use a quoted number, an ACTION label, or reset 0.',
    'action_data': 'Replace ACTION_DATA with {} for actions 1,2,3,4,5,7; for action 6 use {"x":X,"y":Y}, replacing X and Y with integers in [0,63].',
    'shape': 'Emit exactly one outer action key; its object has exactly action_id and action_data. Do not emit placeholders or add keys.',
}


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=1) + '\n').encode()


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError('derivation anchor drift: ' + old[:100])
    return text.replace(old, new)


def scoped(text):
    text = text.replace('control_interface_action_selection_v1', 'control_interface_action_selection_v2')
    text = text.replace('control-interface-action-selection-v1', SCOPE)
    return text


def build(root=ROOT):
    root = Path(root)
    result = {}
    basis = {}
    for p in sorted((root / OLD).iterdir()):
        if p.suffix in ('.py', '.json', '.lock'):
            basis[p.relative_to(root).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    probe = scoped((root / OLD / 'probe.py').read_text(encoding='utf-8'))
    probe = replace(probe, "PACKAGE = 'research/control_interface_action_selection_v2'",
        "PACKAGE = 'research/control_interface_action_selection_v2'\nCASE_PACKAGE = 'research/control_interface_action_selection_v1'\n"
        + 'OUTPUT_CONTRACT = ' + repr(CONTRACT))
    # Preserve the existing instruction and explicitly identify the new shared
    # contract. Its placeholder notation supplies no concrete action answer.
    probe = replace(probe, "with empty action_data. Keep the response under 64 tokens.')",
        "with empty action_data. Keep the response under 64 tokens. '\n"
        "    'Follow the shared output_contract after the observation. action_id must be a JSON integer, '\n"
        "    'never a string or an ACTION label. Replace the template placeholders; do not emit them.')")
    probe = replace(probe, 'folder = Path(root) / PACKAGE', 'folder = Path(root) / CASE_PACKAGE')
    probe = replace(probe, "canonical({'observation': observation}).decode()",
        "canonical({'observation': observation, 'output_contract': OUTPUT_CONTRACT}).decode()")
    probe = replace(probe, "'action': None, 'error': None}",
        "'integer_id': False, 'format_valid': False, 'action': None, 'error': None}")
    probe = replace(probe, "        result['legal_id'] = type(action_id) is int and action_id in legal",
        "        result['integer_id'] = type(action_id) is int\n"
        "        result['format_valid'] = result['integer_id'] and isinstance(data, dict)\n"
        "        result['legal_id'] = type(action_id) is int and action_id in legal")
    probe = replace(probe, "for k in ('json_object', 'shape', 'legal_id', 'arguments', 'valid')",
        "for k in ('json_object', 'shape', 'integer_id', 'format_valid', 'legal_id', 'arguments', 'valid')")
    anchor = '    for case in cases:\n        key = case[\'case_id\']'
    probe = replace(probe, anchor, '''    for arm in ARMS:
        rows = [v for (c, a, p), v in checked.items() if a == arm]
        formatted = sum(v['format_valid'] for v in rows)
        legal = sum(v['format_valid'] and v['legal_id'] for v in rows)
        summary['arms'][arm]['format_valid_both_passes'] = sum(
            all(checked[(c['case_id'], arm, p)]['format_valid'] for p in (1, 2)) for c in cases)
        summary['arms'][arm]['legality_given_format_per_response'] = {
            'numerator': legal, 'denominator': formatted,
            'fraction': legal / formatted if formatted else None}
        summary['arms'][arm]['arguments_given_format_and_legal_per_response'] = {
            'numerator': sum(v['valid'] for v in rows), 'denominator': legal,
            'fraction': sum(v['valid'] for v in rows) / legal if legal else None}
    summary['by_step'] = {}
    for step in sorted({c['step'] for c in cases}):
        contexts = [c for c in cases if c['step'] == step]
        summary['by_step'][str(step)] = {'contexts': len(contexts), 'arms': {
            arm: {metric: sum(all(checked[(c['case_id'], arm, p)][key] for p in (1, 2)) for c in contexts)
                  for metric, key in (('valid_both_passes', 'valid'), ('format_valid_both_passes', 'format_valid'))}
            for arm in ARMS}}
''' + anchor)
    result[NEW + '/probe.py'] = (HEADER + probe).encode()
    namespace = {'__name__': 'derived_probe'}
    exec(compile(probe, '<derived-v2-probe>', 'exec'), namespace)
    protocol = json.loads((root / OLD / 'protocol.json').read_bytes())
    protocol.update(schema='control_interface_action_selection_v2_protocol', scope=SCOPE,
        kernel_id='REPLACE_WITH_OWNER/arc3-control-interface-action-selection-v2',
        purpose='paired retained-observation action selection with shared explicit output contract; zero game actions; no policy promotion')
    experiment = protocol['experiment']
    experiment.update(system_sha256=hashlib.sha256(namespace['SYSTEM'].encode()).hexdigest(),
        shared_output_contract_sha256=hashlib.sha256(namespace['canonical'](CONTRACT)).hexdigest(),
        background='shared explicit output contract; new development condition, not unchanged v1 baseline',
        scoring='strict full validity; structural format and legality given format reported separately')
    result[NEW + '/protocol.json'] = encoded(protocol)
    for p in (root / OLD).glob('*.py'):
        if p.name == 'probe.py':
            continue
        text = scoped(p.read_text(encoding='utf-8'))
        text = text.removeprefix('# Derived by scripts/build_control_interface_action_selection_v2.py; edit the derivation.\n')
        if p.name in ('binding.py', 'notebook.py'):
            text = replace(text, "PACKAGE + '/cases.json', PACKAGE + '/cases-lock.json', PACKAGE + '/derivation.json', PACKAGE + '/token-audit.json'",
                repr(OLD + '/cases.json') + ', ' + repr(OLD + '/cases-lock.json') + ", PACKAGE + '/derivation.json', PACKAGE + '/token-audit.json'")
        if p.name == 'runtime_controls.py':
            text = replace(text, "Path(root) / P.PACKAGE / 'cases.json'", "Path(root) / P.CASE_PACKAGE / 'cases.json'")
            text = replace(text, '    argv = protocol[\'server\'][\'argv\']',
                "    if experiment.get('shared_output_contract_sha256') != P.digest(P.OUTPUT_CONTRACT):\n"
                "        raise ValueError('shared output contract drift')\n"
                "    argv = protocol['server']['argv']")
        if p.name == 'evidence.py':
            text = text.replace('gpu_control_interface_action_selection_development_probe',
                                'gpu_control_interface_action_selection_v2_development_probe')
        result[NEW + '/' + p.name] = (HEADER + text).encode()
    for name in ('trusted_manifest.json', 'trusted_requirements.lock'):
        result[NEW + '/' + name] = (root / OLD / name).read_bytes()
    result[NEW + '/proposal.json'] = encoded({'status': 'proposal_only_no_approval_no_reservation',
        'scope': SCOPE, 'purpose': protocol['purpose'], 'compute_proposal': protocol['limits'],
        'new_source_use_compute_review_required': True, 'prior_attempts_reusable': False})
    result[NEW + '/derivation.json'] = encoded({'basis_commit': '8230c5c', 'baseline_bindings': basis,
        'builder': 'scripts/build_control_interface_action_selection_v2.py', 'case_package': OLD,
        'preserves_baseline_files': True, 'changes': ['separate v2 scope; no inherited approvals or attempts',
        'identical explicit output contract for both arms; new shared background',
        'integer/object format score separated from legality and argument validity',
        'conditional denominators and step0/step10 diagnostics; full validity remains primary',
        'unchanged runtime controller, cleanup, deadlines, frozen cases, schedule and request cap']})
    for old, new in [('scripts/control_interface_action_selection_package.py', 'scripts/control_interface_action_selection_v2_package.py'),
                     ('scripts/audit_control_interface_action_selection_v1.py', 'scripts/audit_control_interface_action_selection_v2.py')]:
        text = scoped((root / old).read_text(encoding='utf-8')).removeprefix(HEADER)
        if old.endswith('_package.py'):
            text = text.replace('scripts/control_interface_action_selection_package.py', 'scripts/control_interface_action_selection_v2_package.py')
            text = text.replace('control_interface_action_selection_review_check_',
                                'control_interface_action_selection_v2_review_check_')
        result[new] = (HEADER + text).encode()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for name, data in build().items():
        p = ROOT / name
        if args.check:
            if p.read_bytes() != data:
                raise SystemExit('v2 derivation drift: ' + name)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
    print(json.dumps({'derived_files': len(build()), 'checked': args.check, 'gpu_launches': 0, 'provider_calls': 0}))


if __name__ == '__main__':
    main()
