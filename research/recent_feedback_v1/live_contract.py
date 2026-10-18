"""Frozen prospective input/ordering contract and prompt ceiling, stdlib only."""
import json
from pathlib import Path

from certification.phase4_multimodal_preflight_v3.images import grid_from_png
from research.initial_geometry_assistance_v1.geometry import check_inventory, digest
from research.initial_geometry_assistance_v1.live_io import sha

MAX_PROMPT_TOKENS = 8192


def protocol():
    path = Path(__file__).with_name('live_protocol.json')
    value = json.loads(path.read_bytes())
    if sha(path.with_name('protocol.json')) != value['comparison_protocol_sha256']:
        raise ValueError('comparison design changed after live freeze')
    if value['max_prompt_tokens_per_request'] != MAX_PROMPT_TOKENS:
        raise ValueError('live prompt ceiling differs')
    return value


def check_cases(cases):
    frozen = protocol()
    if type(cases) is not list or len(cases) != 6 or digest(cases) != frozen['case_inventory_sha256']:
        raise ValueError('frozen case inventory, geometry or variant order differs')
    for case in cases:
        if (set(case['geometry']) != {'reviewed'} or case['seed'] != 0 or
                case['grid_sha256'] != digest(case['grid'])):
            raise ValueError('reviewed geometry or initial grid binding differs')
        check_inventory(case['geometry']['reviewed'])
    return cases


def verify_inputs(root, pin):
    root = Path(root)
    if sha(root/'manifest.json') != pin:
        raise ValueError('prepared input manifest changed')
    manifest = json.loads((root/'manifest.json').read_bytes())
    if (manifest['protocol_sha256'] != sha(Path(__file__).with_name('live_protocol.json')) or
            manifest['base_input_manifest_sha256'] != protocol()['base_input_manifest_sha256']):
        raise ValueError('live protocol or base input binding differs')
    for name, expected in manifest['files'].items():
        if Path(name).name != name or sha(root/name) != expected:
            raise ValueError('prepared input member changed')
    cases = check_cases(json.loads((root/'cases.json').read_bytes())['cases'])
    expected = {'cases.json'} | {c['case_id']+'.png' for c in cases}
    if set(manifest['files']) != expected or {p.name for p in root.iterdir()} != expected | {'manifest.json'}:
        raise ValueError('live input inventory differs')
    for case in cases:
        path = root/(case['case_id']+'.png')
        if sha(path) != case['image_sha256'] or grid_from_png(path.read_bytes(), cell=7) != case['grid']:
            raise ValueError('board image differs from initial grid')
    return manifest
