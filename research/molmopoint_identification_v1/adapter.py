"""Native pointing metadata and deterministic cell mapping; no loading or dispatch."""
import hashlib
import json
import math
from numbers import Integral, Real
from pathlib import Path

MODEL = 'allenai/MolmoPoint-8B'
REVISION = '188130f961c8e0888a34e11121a1423c461a01ba'
PROMPTS = {
    'objects': 'Point to the distinct visible objects in this game image.',
    'barrier_candidates': 'Point to the visible wall or barrier candidates in this game image.',
}
MAX_POINTS = 96


def verify_snapshot(folder):
    """Check a complete, local snapshot before anyone imports its custom code."""
    folder = Path(folder).resolve()
    pin = json.loads(Path(__file__).with_name('model_pin.json').read_bytes())
    if pin['repository'] != MODEL or pin['revision'] != REVISION:
        raise ValueError('model identity differs')
    expected = {row['name'] for row in pin['files']}
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*.py')}
    if actual != {n for n in expected if n.endswith('.py')}:
        raise ValueError('missing or unexpected Python source')
    receipts = {}
    for item in pin['files']:
        path = folder/item['name']
        if (path.is_symlink() or not path.resolve().is_relative_to(folder)
                or not path.is_file() or path.stat().st_size != item['bytes']):
            raise ValueError('missing or different snapshot file: '+item['name'])
        sha256 = hashlib.sha256()
        git = hashlib.sha1(('blob '+str(item['bytes'])+'\0').encode())
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024*1024), b''):
                sha256.update(chunk)
                git.update(chunk)
        value = sha256.hexdigest()
        if ('upstream_sha256' in item and value != item['upstream_sha256']
                or 'git_blob_sha1' in item and git.hexdigest() != item['git_blob_sha1']
                or 'reviewed_sha256' in item and value != item['reviewed_sha256']):
            raise ValueError('snapshot hash differs: '+item['name'])
        receipts[item['name']] = value
    return {'model':MODEL,'revision':REVISION,'files_sha256':receipts,
            'runtime_validated':False,'use_permission_established':False}


def dimensions(image_size):
    if (type(image_size) not in (list,tuple) or len(image_size) != 2
            or any(isinstance(v,bool) or not isinstance(v,Integral) or v <= 0 for v in image_size)):
        raise ValueError('positive original image width and height required')
    return tuple(int(v) for v in image_size)


def points_to_cells(points, image_size):
    """Publisher rows are [object_id, image_index, pixel_x, pixel_y], not y,x."""
    width, height = dimensions(image_size)
    if type(points) not in (list,tuple) or len(points) > MAX_POINTS:
        raise ValueError('bounded list of native decoded points required')
    result = []
    for row in points:
        if type(row) not in (list,tuple) or len(row) != 4:
            raise ValueError('native point must have four fields')
        oid, image_index, px, py = row
        if (any(isinstance(v,bool) or not isinstance(v,Integral) for v in (oid,image_index))
                or oid < 0 or image_index != 0):
            raise ValueError('one image and nonnegative integer object IDs required')
        if (any(isinstance(v,bool) or not isinstance(v,Real) or not math.isfinite(v) for v in (px,py))
                or not 0 <= px < width or not 0 <= py < height):
            raise ValueError('decoded pixel point outside original image; never clamp or repair')
        result.append({'object_id':int(oid),'image_index':0,
                       'pixel_xy':[float(px),float(py)],
                       'cell_xy':[math.floor(float(px)/(width/64)),math.floor(float(py)/(height/64))]})
    return result


def prepare_inputs(model, processor, image, task):
    """Use the publisher's metadata/pointing mechanism; caller owns compute limits."""
    if task not in PROMPTS:
        raise ValueError('unknown pointing task')
    return prepare_prompt_inputs(model,processor,image,PROMPTS[task])


def prepare_prompt_inputs(model, processor, image, prompt):
    """Prepare one prompt from a frozen request plan, using original-image metadata."""
    if type(prompt) is not str or not 1 <= len(prompt) <= 1000:
        raise ValueError('bounded pointing prompt required')
    if getattr(getattr(model,'config',None),'model_type',None) != 'molmo_point':
        raise ValueError('expected the pinned MolmoPoint architecture')
    image_size = dimensions(image.size)
    messages = [{'role':'user','content':[
        {'type':'text','text':prompt}, {'type':'image','image':image}]}]
    inputs = processor.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
        return_tensors='pt', return_dict=True, padding=True, return_pointing_metadata=True)
    metadata = inputs.pop('metadata')
    if not {'token_pooling','subpatch_mapping','image_sizes'} <= set(metadata):
        raise ValueError('point decoder metadata missing')
    sizes = metadata['image_sizes']
    if len(sizes) != 1 or dimensions(sizes[0]) != image_size:
        raise ValueError('point metadata does not refer to the original image')
    logits = model.build_logit_processor_from_inputs(inputs)
    if not logits:
        raise ValueError('pointing constraint processor missing')
    return inputs, metadata, logits


def decode_generation(model, processor, token_ids, metadata, image_size, *, finish_reason):
    """Retain special tokens for the native decoder; never parse text coordinates."""
    if finish_reason != 'stop':
        raise ValueError('unfinished pointing output must be retained as invalid')
    if (type(token_ids) is not list or not 1 <= len(token_ids) <= 1024
            or any(type(v) is not int or v < 0 for v in token_ids)):
        raise ValueError('generated token evidence required')
    if len(metadata['image_sizes']) != 1 or dimensions(metadata['image_sizes'][0]) != dimensions(image_size):
        raise ValueError('point metadata original dimensions differ')
    text = processor.post_process_image_text_to_text([token_ids], skip_special_tokens=False,
                                                    clean_up_tokenization_spaces=False)[0]
    native = model.extract_image_points(text, metadata['token_pooling'],
                                       metadata['subpatch_mapping'],metadata['image_sizes'])
    # A native decoder can drop an unmapped patch. Do not mistake that for no detection.
    import re
    triples = re.findall(r'<POINT_\d+> ?<POINT_\d+> ?<POINT_\d+> ?[0-9]+', text)
    if len(triples) != len(native):
        raise ValueError('native decoder dropped or added point triples')
    return {'raw_text_with_special_tokens':text,'generated_token_ids':list(token_ids),'finish_reason':finish_reason,
            'native_points':[[int(row[0]),int(row[1]),float(row[2]),float(row[3])] for row in native],
            'points':points_to_cells(native,image_size)}
