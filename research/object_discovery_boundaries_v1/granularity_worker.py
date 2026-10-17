"""Reference-free development worker. A caller owns process/deadline cleanup."""
import json
from pathlib import Path
import time

from .granularity import condition, assemble
from .granularity_runtime import file_sha
from .sam21 import point_prompts


def write_json(path, value):
    with Path(path).open('xb') as stream:
        stream.write((json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode())


def inputs_for(directory):
    directory = Path(directory)
    manifest = json.loads((directory/'manifest.json').read_bytes())
    expected = {'seeds.json'} | {f'board-{i:02d}.png' for i in range(1,7)}
    if set(manifest) != expected or {p.name for p in directory.iterdir()} != expected | {'manifest.json'}:
        raise ValueError('only six images and retained seeds may enter inference')
    for name, pin in manifest.items():
        path = directory/name
        if path.is_symlink() or not path.is_file() or file_sha(path) != pin:
            raise ValueError('input hash differs')
    frames = json.loads((directory/'seeds.json').read_bytes())['frames']
    if [f['case_id'] for f in frames] != [f'board-{i:02d}' for i in range(1,7)]:
        raise ValueError('six ordered frames required')
    for f in frames:
        point_prompts(f['points'])
        if type(f['source_response_valid']) is not bool or not f['source_response_valid'] and f['points']:
            raise ValueError('invalid MolmoPoint response cannot supply partial seeds')
        if f['image_sha256'] != manifest[f['case_id']+'.png']:
            raise ValueError('seed/image binding differs')
    return frames


def run_frames(backend, inputs, output, policy, deadline, *, smoke_case=None):
    """Persist all masks before reference-free quality selection/projection.

    One granularity per invocation prevents hindsight selection across levels.
    The separate evaluator is the only component that accepts references.
    """
    import numpy as np
    import torch
    from PIL import Image
    if policy != condition(policy['model'], policy['mode'], policy['granularity']):
        raise ValueError('comparison policy differs')
    frames = inputs_for(inputs)
    if smoke_case is not None:
        if smoke_case not in [frame['case_id'] for frame in frames]:
            raise ValueError('unknown one-image smoke case')
        frames = [frame for frame in frames if frame['case_id']==smoke_case]
        if policy['mode']=='seeded' and (not frames[0]['source_response_valid'] or not frames[0]['points']):
            raise ValueError('seeded runtime smoke must actually exercise inference')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output/'policy.json', policy)
    write_json(output/'worker-scope.json', dict(purpose='one_image_runtime_smoke' if smoke_case else 'six_board_comparison',
                                               cases=[frame['case_id'] for frame in frames]))
    for frame in frames:
        if time.monotonic() >= deadline:
            raise TimeoutError('granularity worker deadline reached')
        name = frame['case_id']
        if policy['mode'] == 'seeded' and (not frame['source_response_valid'] or not frame['points']):
            write_json(output/(name+'.json'), dict(case_id=name, skipped=True, objects=[],
                reason='no valid retained seeds', source_response_valid=frame['source_response_valid']))
            continue
        with Image.open(Path(inputs)/(name+'.png')) as opened:
            if opened.size != (448,448) or opened.mode != 'RGB':
                raise ValueError('plain RGB448 image required')
            image = np.asarray(opened)
        with torch.inference_mode():
            if policy['mode'] == 'seeded':
                raw = backend.seeded(image, frame['points'], policy['granularity'])
            else:
                # Deliberately independent of seed availability, including ls20.
                raw = backend.automatic(image, policy['granularity'])
        arrays = {k: v for k,v in raw.items() if isinstance(v, np.ndarray)}
        with (output/(name+'-raw.npz')).open('xb') as stream:
            np.savez_compressed(stream, **arrays)
        write_json(output/(name+'-raw-metadata.json'), dict(metadata=raw['metadata'], qualities=raw['qualities']))
        converted = assemble(raw, policy, frame['points'] if policy['mode'] == 'seeded' else None)
        write_json(output/(name+'.json'), dict(case_id=name, skipped=False,
                   image_sha256=frame['image_sha256'], source_response_valid=frame['source_response_valid'],
                   raw_sha256=file_sha(output/(name+'-raw.npz')), **converted))
    if time.monotonic() >= deadline:
        raise TimeoutError('granularity evidence finalization deadline reached')
    write_json(output/'worker-manifest.json', {p.name:file_sha(p) for p in sorted(output.iterdir())})
    if time.monotonic() >= deadline:
        raise TimeoutError('granularity manifest finalization overrun')
    return dict(state='worker_output_collected', policy=policy,
                purpose='one_image_runtime_smoke' if smoke_case else 'six_board_comparison',
                cases=[frame['case_id'] for frame in frames],
                worker_manifest_sha256=file_sha(output/'worker-manifest.json'),
                requires_external_lifecycle_verification=True,
                new_MolmoPoint_generations=0, game_actions=0, scorecards=0)
