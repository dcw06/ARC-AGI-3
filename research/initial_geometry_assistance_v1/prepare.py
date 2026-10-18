"""Pinned private inputs; the policy never receives labels or reference scores."""
import hashlib
import json
from pathlib import Path

from certification.phase4_multimodal_preflight_v3.images import grid_from_png, png
from .geometry import canonical, check_grid, digest, inventory
from .automatic_replay import replay_comparison

REFERENCE_SHA = '5304e35b1f0ee17e0ffd77293ac4fba260bbfa08755c2d48e914ed72ac9cec63'
AUTOMATIC_SHA = 'baaf83f11b36343580a80e996c166e23bd2ece31a561173dbf02ace9d8290408'
SOURCE_EVALUATION_SHA = '32eae91f0e49ad7da71e87e2b82b24f16d1dba440fe115522b47d1d5d53600ff'


def pinned(path, expected):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('input hash differs: ' + str(path))
    return json.loads(raw)


def build_inputs(reference, automatic, source_evaluation, image_dir, output, *,
                 control_root, molmopoint_checkpoint, sam_acquisition):
    # Check independently fixed pins BEFORE deriving either arm.
    protocol_path = Path(__file__).with_name('protocol.json')
    protocol = json.loads(protocol_path.read_bytes())
    if (protocol['reference_sha256'] != REFERENCE_SHA or protocol['automatic_masks_sha256'] != AUTOMATIC_SHA
            or protocol['automatic_source_evaluation_sha256'] != SOURCE_EVALUATION_SHA):
        raise ValueError('protocol evidence pins differ')
    refs = pinned(reference, REFERENCE_SHA)
    claimed = pinned(automatic, protocol['automatic_masks_sha256'])
    source = pinned(source_evaluation, SOURCE_EVALUATION_SHA)
    # The supplied yes/no fields never grant admission. Recompute their evidence
    # and every object, then require the entire historical artifact to reproduce.
    auto = replay_comparison(control_root, molmopoint_checkpoint, sam_acquisition)
    if canonical(auto) != canonical(claimed):
        raise ValueError('stored automatic comparison differs from evidence replay')
    expected_ids = [c['case_id'] for c in protocol['cases']]
    if not (expected_ids == [f['case_id'] for f in refs['frames']] == [f['case_id'] for f in auto['frames']]
            == [c['case_id'] for c in source['cases']]):
        raise ValueError('six ordered boards required')
    cases, files = [], {}
    for spec, ref, row, src in zip(protocol['cases'], refs['frames'], auto['frames'], source['cases']):
        name = spec['case_id']
        grid = check_grid(ref['grid'])
        image_raw = (Path(image_dir) / (name+'.png')).read_bytes()
        if (digest(grid) != ref['grid_sha256'] or grid_from_png(image_raw, cell=7) != grid
                or png(grid, cell=7) != image_raw):
            raise ValueError('initial image/grid binding differs')
        if not ref['reference_exhaustive_confirmed'] or row['game'] != spec['game_id'].split('-')[0]:
            raise ValueError('reference review/game binding differs')
        whole = [r for r in ref['regions'] if r['parent_id'] is None and r['disposition'] == 'include']
        if not whole or any(r['mask_reviewed'] is not True for r in whole):
            raise ValueError('unreviewed whole object')
        if row['source_response_valid'] != src['response_valid']:
            raise ValueError('automatic validity differs')
        if not src['response_valid'] and row['objects']:
            raise ValueError('invalid automatic response salvaged')
        cases.append({'case_id': name, 'game_id': spec['game_id'], 'seed': 0, 'order': spec['order'],
                      'grid': grid, 'grid_sha256': digest(grid),
                      'image_sha256': hashlib.sha256(image_raw).hexdigest(),
                      'geometry': {'automatic': inventory([r['cells'] for r in row['objects']]),
                                   'reviewed': inventory([r['cells'] for r in whole])}})
        files[name+'.png'] = image_raw
    if sum(len(c['geometry']['reviewed']) for c in cases) != 37:
        raise ValueError('whole-object inventory differs')
    if sum(len(c['geometry']['automatic']) for c in cases) != 22 or cases[0]['geometry']['automatic']:
        raise ValueError('retained automatic inventory differs')
    # No owner labels/roles, old human actions or reference scores are copied.
    files['cases.json'] = canonical({'schema': 'initial_geometry_inputs_v1', 'cases': cases})
    output = Path(output)
    output.mkdir(exist_ok=False)
    for name, raw in files.items():
        with (output / name).open('xb') as stream:
            stream.write(raw)
    manifest = {'schema': 'initial_geometry_input_manifest_v1', 'reference_sha256': REFERENCE_SHA,
                'automatic_masks_sha256': AUTOMATIC_SHA, 'automatic_source_evaluation_sha256': SOURCE_EVALUATION_SHA,
                'automatic_provenance_manifest_sha256': protocol['automatic_provenance_manifest_sha256'],
                'automatic_replay_sources_sha256': {
                    'research/initial_geometry_assistance_v1/'+name: hashlib.sha256(
                        Path(__file__).with_name(name).read_bytes()).hexdigest()
                    for name in ('automatic_replay.py', 'automatic_provenance.json', 'prepare.py')},
                'files': {n: hashlib.sha256(raw).hexdigest() for n, raw in files.items()},
                'protocol_sha256': hashlib.sha256(protocol_path.read_bytes()).hexdigest()}
    (output / 'manifest.json').write_bytes(canonical(manifest))
    return manifest
