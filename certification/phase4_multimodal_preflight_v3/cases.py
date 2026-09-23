"""Frozen preflight probes and exact requests; stdlib only, independent of environment APIs."""
import base64,copy,hashlib,json
from pathlib import Path
from certification.phase4_multimodal_preflight_v3 import images
ROOT=Path(__file__).resolve().parents[2]
MODEL='Qwen/Qwen3-VL-30B-A3B-Instruct-FP8'
PROBE_IDS=('T0','I1','I2','I3')
MAX_TOKENS=64
SYSTEM=('Answer only from the supplied observation. Grid coordinates are zero-based cells: x is column '
    'increasing right, y is row increasing down. Return only the requested JSON object. Do not infer game rules.')
LEGEND='Palette legend (color index: RGB): '+', '.join(f'{i}:({r},{g},{b})' for i,(r,g,b) in enumerate(images.PALETTE))+'.'
BOARD_QUESTION=('The attached image is a 64x64 grid of cells, each rendered as a uniform 16x16 pixel block. '
    +LEGEND+' Exactly one filled square differs from the uniform background. Report the quadrant of the '
    'grid that contains it and its color index. Use quadrant "none" and color null if no image is attached.')
CANARY_QUESTION=('The attached image is a 4x4 grid of cells, each rendered as a uniform 16x16 pixel block. '
    +LEGEND+' Report the color index of the cell at x=1, y=2.')

def request_hash(request):return hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest()

def canary_request(model):
    # Byte-identical to the grounding/integrated startup canary (known request hash).
    from certification.phase4_multimodal_preflight_v3.action_contract import response_format
    return {'model':model,'messages':[{'role':'system','content':'Return a JSON action object for ACTION6 with integer x and y in [0,63].'},
        {'role':'user','content':'Choose display coordinates for a click; return only the action JSON.'}],
        'temperature':0,'seed':0,'max_tokens':128,'chat_template_kwargs':{'enable_thinking':False},'response_format':response_format([6])}

def response_format(kind):
    color={'anyOf':[{'type':'null'},{'type':'integer','minimum':0,'maximum':15}]}
    if kind=='board':
        props={'quadrant':{'type':'string','enum':['top_left','top_right','bottom_left','bottom_right','none']},'color':color}
    else:props={'color':{'type':'integer','minimum':0,'maximum':15}}
    return {'type':'json_schema','json_schema':{'name':'multimodal_preflight_'+kind,'strict':True,
        'schema':{'type':'object','properties':props,'required':list(props),'additionalProperties':False}}}

def board(color,x0,y0,background=0,size=16):
    grid=[[background]*64 for _ in range(64)]
    for y in range(y0,y0+size):
        for x in range(x0,x0+size):grid[y][x]=color
    return grid

GRIDS={'I1':[[5,9,9,14],[8,11,2,14],[3,12,6,10],[15,13,4,1]],
    'I2':board(8,8,8),'I3':board(9,40,40)}
EXPECTED={'T0':{'quadrant':'none','color':None},'I1':{'color':12},
    'I2':{'quadrant':'top_left','color':8},'I3':{'quadrant':'bottom_right','color':9}}

def build_request(probe):
    kind='canary' if probe=='I1' else 'board'
    text=CANARY_QUESTION if probe=='I1' else BOARD_QUESTION
    content=[{'type':'text','text':text}]
    if probe!='T0':content.insert(0,{'type':'image_url','image_url':{'url':images.data_url(images.png(GRIDS[probe]))}})
    return {'model':MODEL,'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':content}],
        'temperature':0,'seed':0,'max_tokens':MAX_TOKENS,'chat_template_kwargs':{'enable_thinking':False},
        'response_format':response_format(kind)}

def image_part(request):
    parts=[p for m in request['messages'] if isinstance(m['content'],list) for p in m['content'] if p.get('type')=='image_url']
    if len(parts)>1:raise ValueError('at most one image per probe')
    if not parts:return None
    url=parts[0]['image_url']['url'];prefix='data:image/png;base64,'
    if not url.startswith(prefix):raise ValueError('only inline PNG data URLs')
    return base64.b64decode(url[len(prefix):],validate=True)

def text_only(request):
    """The same request with the image part removed: the T0-style token baseline."""
    value=copy.deepcopy(request)
    for m in value['messages']:
        if isinstance(m['content'],list):m['content']=[p for p in m['content'] if p.get('type')!='image_url']
    return value

def generate():
    rows=[]
    for probe in PROBE_IDS:
        request=build_request(probe);raw=image_part(request)
        row={'probe_id':probe,'request':request,'request_sha256':request_hash(request),'expected':EXPECTED[probe]}
        if raw is not None:
            h,w=len(GRIDS[probe])*images.CELL,len(GRIDS[probe][0])*images.CELL
            row['image']={'png_sha256':images.sha(raw),'png_bytes':len(raw),'input_height':h,'input_width':w,
                'grid':GRIDS[probe],'provisional_arithmetic':images.expected_image_tokens(h,w)}
        rows.append(row)
    return rows

def load_cases():
    rows=json.loads(Path(__file__).with_name('cases.json').read_bytes())
    if [r['probe_id'] for r in rows]!=list(PROBE_IDS):raise ValueError('probe inventory')
    for row in rows:
        if row['request_sha256']!=request_hash(row['request']):raise ValueError('request binding')
        raw=image_part(row['request'])
        if (raw is None)!=(row['probe_id']=='T0'):raise ValueError('image presence')
        if raw is not None:
            # Independent decoder: the retained PNG must reproduce the frozen grid exactly.
            if images.sha(raw)!=row['image']['png_sha256'] or images.grid_from_png(raw)!=row['image']['grid']:raise ValueError('image binding')
    texts={json.dumps(text_only(r['request']),sort_keys=True) for r in rows if r['probe_id'] in ('T0','I2','I3')}
    if len(texts)!=1:raise ValueError('T0/I2/I3 must differ only by the image part')
    return rows
