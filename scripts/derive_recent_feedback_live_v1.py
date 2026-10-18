"""Reproducible live-runtime derivations from the unchanged, validated r5 source."""
import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'research/initial_geometry_assistance_v1'
TARGET = ROOT/'research/recent_feedback_v1'
PINS = {'live_worker.py': '538eeafdd1a13f5515ea33ee7f518cb284ebbd1ec129357d28ee99460377c6c8',
        'live_runtime.py': 'e704fa557b55d5b805d6aeb274cc4f57ebce24f556ba27f4ada2c3c30515ea6b',
        'live_package.py': '95f63c1932675178a40e57a67c48f3fab2c876af746610c43fc16aee0d6856da',
        'live_evaluation.py': '75e0b4bbc717ce1751f926d2484d59862561062dc6a852c3f3d723377b6e3a84'}


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('derivation edit not unique: '+before[:90])
    return text.replace(before, after)


def derive(name):
    raw = (BASE/name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PINS[name]:
        raise ValueError('validated r5 base source changed: '+name)
    text = raw.decode()
    for module in ('engine', 'engine_bridge', 'geometry', 'live_io', 'live_resources', 'model_io', 'game_wheels', 'live_operator'):
        text = text.replace('from .'+module+' import ', 'from research.initial_geometry_assistance_v1.'+module+' import ')
    text = text.replace("'initial_geometry_", "'recent_feedback_").replace('INITIAL_GEOMETRY_', 'RECENT_FEEDBACK_')
    text = text.replace('initial-geometry-', 'recent-feedback-')
    text = text.replace('research.initial_geometry_assistance_v1.live_worker', 'research.recent_feedback_v1.live_worker')
    if name == 'live_worker.py':
        text = replace_once(text, 'from .episodes import episode\n',
                            'from .episodes import episode\nfrom .live_contract import check_cases, MAX_PROMPT_TOKENS\n')
        text = replace_once(text, "    cases = json.loads(Path(config['cases']).read_bytes())['cases']\n",
                            "    cases = json.loads(Path(config['cases']).read_bytes())['cases']\n    check_cases(cases)\n")
        text = replace_once(text, '        expected = token_audit(body)\n',
                            "        expected = token_audit(body)\n        if type(expected) is not int or not 0 < expected <= MAX_PROMPT_TOKENS:\n            raise ValueError('prospective prompt-token budget exceeded before HTTP admission')\n")
    elif name == 'live_runtime.py':
        begin, end = text.index('def verify_inputs('), text.index('\ndef finalize(')
        text = text[:begin]+'from .live_contract import verify_inputs\n\n'+text[end:]
        text = replace_once(text, 'research.initial_geometry_assistance_v1.live_runtime', 'research.recent_feedback_v1.live_runtime') if 'research.initial_geometry_assistance_v1.live_runtime' in text else text
    elif name == 'live_package.py':
        text = text.replace("for folder in ('agent', 'research/initial_geometry_assistance_v1'):",
                            "for folder in ('agent', 'research/initial_geometry_assistance_v1', 'research/recent_feedback_v1'):")
        text = replace_once(text, "    for name, pin in manifest['automatic_replay_sources_sha256'].items():\n        if sha(root/name) != pin:\n            raise ValueError('provenance producer changed since full replay')\n", '')
        text = replace_once(text, "    files = {name: (root/name).read_bytes() for name in sorted(sources)}\n",
            "    sources.update(['research/recent_feedback_v1/protocol.json', 'research/recent_feedback_v1/live_protocol.json',\n"
            "                    'research/feedback_availability_v1.py', 'scripts/derive_recent_feedback_live_v1.py',\n"
            "                    'scripts/build_recent_feedback_live_v1.py', 'scripts/rehearse_recent_feedback_live_v1.py',\n"
            "                    'tests/test_recent_feedback_live_v1.py',\n"
            "                    'tests/test_recent_feedback_v1.py'])\n"
            "    files = {name: (root/name).read_bytes() for name in sorted(sources)}\n")
        text = text.replace('from research.initial_geometry_assistance_v1.live_runtime import check_authority, run',
                            'from research.recent_feedback_v1.live_runtime import check_authority, run')
        text = text.replace('Private paired initial-geometry gameplay study.', 'Private paired recent-feedback gameplay study.')
        text = text.replace('ARC3 Initial Geometry Paired Gameplay V1', 'ARC3 Recent Feedback Paired Gameplay V1')
    elif name == 'live_evaluation.py':
        text = replace_once(text, 'from .model_io import validate_reply\n',
                            'from .model_io import validate_reply\nfrom .live_contract import check_cases, MAX_PROMPT_TOKENS\n') if 'from .model_io import validate_reply\n' in text else replace_once(text,
                            'from research.initial_geometry_assistance_v1.model_io import validate_reply\n',
                            'from research.initial_geometry_assistance_v1.model_io import validate_reply\nfrom .live_contract import check_cases, MAX_PROMPT_TOKENS\n')
        text = replace_once(text, "if type(native) is not int or native <= 0 or (token_audit is not None and token_audit(request['body']) != native):",
                            "if type(native) is not int or not 0 < native <= MAX_PROMPT_TOKENS or (token_audit is not None and token_audit(request['body']) != native):")
        text = replace_once(text, "    cases = json.loads((inputs/'cases.json').read_bytes())['cases']\n",
                            "    cases = json.loads((inputs/'cases.json').read_bytes())['cases']\n    check_cases(cases)\n")
    header = '# Generated by scripts/derive_recent_feedback_live_v1.py; validated r5 base SHA256 '+PINS[name]+'.\n'
    return (header+text).encode()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for name in PINS:
        raw = derive(name)
        path = TARGET/name
        if args.check:
            if not path.is_file() or path.read_bytes() != raw:
                raise ValueError('live derivation differs: '+name)
        else:
            path.write_bytes(raw)
    print('All four live derivations match validated r5 transformations' if args.check else 'Wrote four prospective live derivations; no compute')
