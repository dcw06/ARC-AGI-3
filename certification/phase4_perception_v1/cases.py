"""Matched stateless requests; reference answers are never in model messages."""
import json
from pathlib import Path
from research.perception_v1.fixtures import build,D4
from research.perception_v1.controls import cases as controls
from certification.phase4_multimodal_preflight_v3.cases import MODEL,SYSTEM,LEGEND,canary_request,image_part,request_hash,build_request
from certification.phase4_multimodal_preflight_v3.images import data_url,png
ROOT=Path(__file__).resolve().parents[2]
PERCEPTION_CAP=2048
CONTROL_CAP=512
TASK=('Describe visually distinct bounded objects, keeping borders/stripes in non_object_regions. '
      'Do not infer game rules, goals, actions or object effects. Report inclusive bbox [xmin,ymin,xmax,ymax]. '
      'Coordinates are zero-based grid cells, grid[y][x]; x increases right and y down. '
      'Colors include internal markings; report markings separately. Occupancy is a 3x3 mask within each '
      'object bbox: boundaries floor(i*size/3), a block is 1 when at least half its cells belong to the object. '
      'Match outer geometry independently of color/position; transform maps a to b, reflection before rotation. '
      'When multiple transforms fit, report any valid transform; use uncertain when you cannot identify one. '
      'Use unique short IDs, at most 6 objects, 3 non-object regions and '
      '6 relations. Describe only the supplied observation. '+LEGEND+
      ' Grid size is 64x64. An image, when supplied, uses 16x16 pixels per cell.')
def obj(props):return {'type':'object','properties':props,'required':list(props),'additionalProperties':False}
def arr(item,n,m=0):return {'type':'array','items':item,'minItems':m,'maxItems':n}
def integer(a,b):return {'type':'integer','minimum':a,'maximum':b}
def text(n):return {'type':'string','minLength':1,'maxLength':n}
def schema(kind):
    if kind=='perception':
        box=arr(integer(0,63),4,4);colors=arr(integer(0,15),3)
        value=obj({'objects':arr(obj({'id':text(24),'bbox':box,'colors':colors,
            'occupancy':arr(arr(integer(0,1),3,3),3,3),'has_markings':{'type':'boolean'},
            'marking_colors':colors,'description':text(48)}),6),
            'non_object_regions':arr(obj({'bbox':box,'description':text(48)}),3),
            'relations':arr(obj({'a':text(24),'b':text(24),'same_shape':{'type':'boolean'},
                'transform':{'type':'string','enum':[*D4,'different_shape','uncertain']}}),6)})
    else:
        from certification.phase4_multimodal_preflight_v3.action_contract import response_format
        action=response_format(range(1,8))['json_schema']['schema']['properties']['action']
        value=obj({'coordinate_arguments':obj({str(i):{'type':'boolean'} for i in range(1,8)}),
            'click':action,'non_coordinate':action,'directional_ids':{'anyOf':[{'type':'null'},arr(integer(1,7),7)]}})
    return {'type':'json_schema','json_schema':{'name':'perception_v1_'+kind,'strict':True,'schema':value}}
def request(kind,content):
    return {'model':MODEL,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':content}],
        'temperature':0,'seed':0,'max_tokens':PERCEPTION_CAP if kind=='perception' else CONTROL_CAP,
        'chat_template_kwargs':{'enable_thinking':False},'response_format':schema(kind)}
def generate():
    rows=[{'probe_id':'image_canary','kind':'canary','source_group':'synthetic_preflight_I2',
           'request':build_request('I2'),'expected':{'quadrant':'top_left','color':8}}]
    for case in build():
        for representation in ('text','image'):
            observation=({'type':'text','text':json.dumps({'grid':case['grid']},separators=(',',':'))}
                if representation=='text' else {'type':'image_url','image_url':{'url':data_url(png(case['grid']))}})
            rows.append({'probe_id':case['id']+'_'+representation,'kind':'perception','case_id':case['id'],
                'source_group':case['source_group'],'representation':representation,
                'request':request('perception',[{'type':'text','text':TASK},observation])})
    for control in controls():
        rows.append({'probe_id':'control_'+control['id'],'kind':'control','case_id':control['id'],
            'source_group':'interface_'+control['id'],'request':request('control',[
                {'type':'text','text':json.dumps(control['request'],sort_keys=True,separators=(',',':'))}])})
    for row in rows:row['request_sha256']=request_hash(row['request'])
    return rows
def load_cases():
    rows=json.loads(Path(__file__).with_name('cases.json').read_bytes());planned=generate()
    if [{k:v for k,v in r.items() if k!='frozen_local_expectation'} for r in rows]!=planned:
        raise ValueError('frozen request inventory drift')
    return rows
def score(row,content,finish):
    if row['kind']=='perception':
        from research.perception_v1.scoring import score as evaluate
        return evaluate(next(c for c in build() if c['id']==row['case_id']),content,finish)
    if row['kind']=='control':
        from research.perception_v1.controls import score as evaluate
        return evaluate(next(c for c in controls() if c['id']==row['case_id']),content,finish)
    from certification.phase4_multimodal_preflight_v3.probes import score as evaluate
    return evaluate({'probe_id':'I2','expected':row['expected']},content,finish)
