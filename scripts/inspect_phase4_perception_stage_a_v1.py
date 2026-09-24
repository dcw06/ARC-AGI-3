"""Reproduce offline R2 box overlays and descriptive near-miss measurements."""
import argparse
import hashlib
import io
import json
import math
import sys
import tempfile
import zipfile
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
OUTPUT = ROOT/'reports/perception_stage_a_v1'
MANIFEST = ROOT/'reports/phase4_perception_v1_r2_completed_archive.json'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def decoded_rgb_identity(raw):
    """Compare rendered RGB pixels across PNG encoder versions."""
    from PIL import Image
    with Image.open(io.BytesIO(raw)) as source:
        if source.format != 'PNG':
            raise ValueError('overlay is not PNG')
        image = source.convert('RGB')
        return image.size, digest(image.tobytes())


def overlap(left, right):
    x0, y0 = max(left[0], right[0]), max(left[1], right[1])
    x1, y1 = min(left[2], right[2]), min(left[3], right[3])
    intersection = max(0, x1-x0+1)*max(0, y1-y0+1)
    area = lambda b: (b[2]-b[0]+1)*(b[3]-b[1]+1)
    return Fraction(intersection, area(left)+area(right)-intersection)


def center(box):
    return ((box[0]+box[2])/2, (box[1]+box[3])/2)


def swapped(box):
    return [box[1], box[0], box[3], box[2]]


def nearest(reference, predictions):
    """Each reference chooses independently: greatest IoU, then nearest center, then input order."""
    if not predictions:
        return None
    x, y = center(reference['bbox'])
    candidates = []
    for index, prediction in enumerate(predictions):
        box = prediction['bbox']
        px, py = center(box)
        candidates.append((overlap(reference['bbox'],box),-math.hypot(px-x,py-y),-index,index))
    _, _, _, index = max(candidates)
    prediction = predictions[index]
    px, py = center(prediction['bbox'])
    return {'prediction':prediction['id'],'prediction_index':index,
            'iou':float(overlap(reference['bbox'],prediction['bbox'])),
            'center_dx_cells':px-x,'center_dy_cells':py-y,
            'center_distance_cells':math.hypot(px-x,py-y),
            'width_ratio':(prediction['bbox'][2]-prediction['bbox'][0]+1)/
                (reference['bbox'][2]-reference['bbox'][0]+1),
            'height_ratio':(prediction['bbox'][3]-prediction['bbox'][1]+1)/
                (reference['bbox'][3]-reference['bbox'][1]+1)}


def overlay(case, answer, label):
    from PIL import Image, ImageDraw
    from certification.phase4_multimodal_preflight_v3.images import png

    board=Image.open(io.BytesIO(png(case['grid']))).convert('RGB')
    canvas=Image.new('RGB',(board.width,board.height+46),(20,20,20))
    canvas.paste(board,(0,46))
    draw=ImageDraw.Draw(canvas)
    draw.text((10,8),f'{label}: green=reference  magenta=model  cells=[xmin,ymin,xmax,ymax]',fill='white')
    def box_pixels(box):
        return (box[0]*16,46+box[1]*16,(box[2]+1)*16-1,46+(box[3]+1)*16-1)
    for reference in case['reference']['objects']:
        x0,y0,x1,y1=box_pixels(reference['bbox'])
        draw.rectangle((x0,y0,x1,y1),outline=(0,255,80),width=4)
        draw.text((x0+3,y0+3),'R:'+reference['id'],fill=(0,255,80),stroke_width=1,stroke_fill='black')
    for prediction in answer['objects']:
        x0,y0,x1,y1=box_pixels(prediction['bbox'])
        draw.rectangle((x0,y0,x1,y1),outline=(255,0,190),width=3)
        draw.text((x0+3,min(y1-12,y0+17)),'M:'+prediction['id'],fill=(255,0,190),
                  stroke_width=1,stroke_fill='black')
    out=io.BytesIO();canvas.save(out,format='PNG',optimize=False)
    return out.getvalue()


def source_rows():
    from scripts.replay_phase4_perception_v1_r2_completed import run
    if not run()['passed']:
        raise ValueError('completed archive replay failed')
    manifest=json.loads(MANIFEST.read_bytes())
    archive=ROOT/manifest['archive']
    with zipfile.ZipFile(archive) as bundle:
        name='download/phase4-perception-v1/worker/state.json'
        raw=bundle.read(name)
        if digest(raw)!=manifest['members'][name]:
            raise ValueError('worker evidence hash')
        worker=json.loads(raw)
    if worker['status']!='complete' or len(worker['cases'])!=13:
        raise ValueError('incomplete frozen workload')
    return manifest,worker


def build(folder):
    from research.perception_v1.fixtures import build as fixture_cases
    from research.perception_v1.scoring import parse, score

    manifest,worker=source_rows()
    cases={case['id']:case for case in fixture_cases()}
    folder.mkdir(parents=True,exist_ok=False)
    summaries=[];generated={}
    for case_id,case in cases.items():
        for arm in ('text','image'):
            row=next(row for row in worker['cases'] if row['probe_id']==case_id+'_'+arm)
            if digest(row['response_content'].encode())!=row['response_sha256']:
                raise ValueError('response hash')
            answer=parse(row['response_content'],row['audit']['finish_reason'])
            frozen=score(case,row['response_content'],row['audit']['finish_reason'])
            if frozen!=row['answer']:
                raise ValueError('frozen score drift')
            references=case['reference']['objects'];predictions=answer['objects']
            details=[]
            for reference in references:
                raw=nearest(reference,predictions)
                swapped_best=max((overlap(reference['bbox'],swapped(p['bbox'])) for p in predictions),default=Fraction())
                details.append({'reference':reference['id'],'reference_bbox':reference['bbox'],
                                'nearest':raw,'axis_swapped_best_iou':float(swapped_best)})
            filename=f'{case_id}_{arm}.png'
            generated[filename]=overlay(case,answer,case_id+' '+arm)
            summaries.append({'case':case_id,'arm':arm,'source_group':case['source_group'],
                'request_sha256':row['request_sha256'],'response_sha256':row['response_sha256'],
                'reference_count':len(references),'predicted_count':len(predictions),
                'frozen_detected':frozen['detection_recall']['numerator'],
                'reference_details':details,
                'mean_nearest_iou':sum(d['nearest']['iou'] if d['nearest'] else 0 for d in details)/len(details),
                'mean_axis_swapped_nearest_iou':sum(d['axis_swapped_best_iou'] for d in details)/len(details),
                'predicted_boxes':[{'id':p['id'],'bbox':p['bbox']} for p in predictions],
                'overlay':filename})
    controls=[]
    for row in worker['cases'][11:]:
        if not row['probe_id'].startswith('control_'):
            raise ValueError('control order')
        controls.append({'id':row['probe_id'],'request_sha256':row['request_sha256'],
            'response_sha256':row['response_sha256'],'answer':row['answer'],
            'response':parse_control(row['response_content'])})
    generated['analysis.json']=(json.dumps({'status':'descriptive_offline_only',
        'archive_sha256':manifest['sha256'],'cases':summaries,'controls':controls,
        'matching_rule':'Each reference independently selects highest inclusive-box IoU; ties use nearest center then input order. This is exploratory and does not alter frozen 1:1 IoU>=0.5 scoring.',
        'axis_swap_rule':'Predicted [xmin,ymin,xmax,ymax] is changed to [ymin,xmin,ymax,xmax] only for a separately labeled exploratory comparison.',
        'model_calls':0,'environment_actions':0,'gpu_runs':0},indent=2)+'\n').encode()
    for name,raw in generated.items():
        (folder/name).write_bytes(raw)
    lock={'status':'offline_inspection_no_rescoring','archive_sha256':manifest['sha256'],
          'files':{name:digest(raw) for name,raw in sorted(generated.items())}}
    (folder/'inspection-lock.json').write_bytes((json.dumps(lock,indent=2)+'\n').encode())
    return lock


def parse_control(content):
    from research.perception_v1.scoring import strict_json
    value=strict_json(content)
    return {'coordinate_arguments':value['coordinate_arguments'],
            'click':value['click'],'non_coordinate':value['non_coordinate'],
            'directional_ids':value['directional_ids']}


def check():
    lock=json.loads((OUTPUT/'inspection-lock.json').read_bytes())
    with tempfile.TemporaryDirectory() as temp:
        generated=build(Path(temp)/'inspection')
        if generated['archive_sha256']!=lock['archive_sha256'] or set(generated['files'])!=set(lock['files']):
            raise ValueError('inspection source/inventory drift')
        png_byte_matches=0
        for name,digest_value in lock['files'].items():
            original=(OUTPUT/name).read_bytes()
            rebuilt=(Path(temp)/'inspection'/name).read_bytes()
            if digest(original)!=digest_value:
                raise ValueError('committed inspection artifact drift: '+name)
            if name.endswith('.png'):
                if decoded_rgb_identity(original)!=decoded_rgb_identity(rebuilt):
                    raise ValueError('decoded overlay pixels drift: '+name)
                png_byte_matches+=int(digest(rebuilt)==digest_value)
            elif original!=rebuilt:
                raise ValueError('inspection analysis drift: '+name)
    print(json.dumps({'status':'verified','overlays':10,'png_byte_matches':png_byte_matches,
                      'archive_sha256':lock['archive_sha256']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    arguments=parser.parse_args()
    if arguments.check:
        check()
    else:
        print(json.dumps(build(OUTPUT)))
