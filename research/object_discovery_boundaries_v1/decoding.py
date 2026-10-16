"""Inventory-specific native decoding; completed single-target decoder unchanged."""
from research.molmopoint_identification_v1.adapter import validate_point_sequence,points_to_cells,dimensions
from .prepare import MAX_NEW_TOKENS


def decode_inventory(model,processor,token_ids,metadata,image_size,*,finish_reason):
    if finish_reason!='stop':raise ValueError('unfinished inventory output')
    if (type(token_ids) is not list or not 1<=len(token_ids)<=MAX_NEW_TOKENS
            or any(type(v) is not int or v<0 for v in token_ids)):
        raise ValueError('bounded integer inventory tokens required')
    if (len(metadata['image_sizes'])!=1 or dimensions(metadata['image_sizes'][0])!=dimensions(image_size)
            or getattr(model.config,'no_more_points_class',None) is not True
            or getattr(model.config,'patch_location',None)!='3x3'):
        raise ValueError('pinned native metadata/grammar required')
    text=processor.post_process_image_text_to_text([token_ids],skip_special_tokens=False,clean_up_tokenization_spaces=False)[0]
    sequence=validate_point_sequence(text,metadata['token_pooling'])
    native=model.extract_image_points(text,metadata['token_pooling'],metadata['subpatch_mapping'],metadata['image_sizes'])
    if sequence['complete_points']!=len(native):raise ValueError('native decoder dropped or added points')
    return dict(raw_text_with_special_tokens=text,point_sequence=sequence,
        native_points=[[int(r[0]),int(r[1]),float(r[2]),float(r[3])] for r in native],
        points=points_to_cells(native,image_size))
