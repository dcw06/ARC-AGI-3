"""Seal the prospective feedback comparison locally; never contacts a provider."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from research.recent_feedback_v1.live_contract import check_cases, protocol, verify_inputs
from research.recent_feedback_v1.live_package import build


def derived_cases(base):
    design = json.loads((ROOT/'research/recent_feedback_v1/protocol.json').read_bytes())
    cases = deepcopy(json.loads((Path(base)/'cases.json').read_bytes())['cases'])
    if [c['game_id'] for c in cases] != design['games']:
        raise ValueError('base game order differs')
    for case, order in zip(cases, design['candidate_order']):
        case['geometry'] = {'reviewed': case['geometry']['reviewed']}
        case['order'] = order
    return cases


def prepare_inputs(base, output):
    base, output = Path(base), Path(output)
    frozen = protocol()
    if sha(base/'manifest.json') != frozen['base_input_manifest_sha256']:
        raise ValueError('historical reviewed input manifest differs')
    original = json.loads((base/'manifest.json').read_bytes())
    for name, pin in original['files'].items():
        if Path(name).name != name or sha(base/name) != pin:
            raise ValueError('historical reviewed input bytes differ')
    cases = check_cases(derived_cases(base))
    output.mkdir(exist_ok=False)
    write_new(output/'cases.json', {'schema': 'recent_feedback_cases_v1', 'cases': cases})
    for case in cases:
        name = case['case_id']+'.png'
        (output/name).write_bytes((base/name).read_bytes())
    write_new(output/'manifest.json', {'schema': 'recent_feedback_inputs_v1',
        'base_input_manifest_sha256': sha(base/'manifest.json'),
        'protocol_sha256': sha(ROOT/'research/recent_feedback_v1/live_protocol.json'),
        'files': {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()}})
    pin = sha(output/'manifest.json')
    verify_inputs(output, pin)
    return pin


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('base-inputs', 'inputs', 'game-environment', 'runtime', 'scope-review', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--game-pin', required=True)
    args = parser.parse_args()
    pin = prepare_inputs(args.base_inputs, args.inputs)
    runtime = json.loads(args.runtime.read_bytes())
    runtime['input_manifest_sha256'] = pin
    print(json.dumps(build(ROOT, args.inputs, pin, args.game_environment, args.game_pin,
                           runtime, args.output, scope_review=args.scope_review)))
