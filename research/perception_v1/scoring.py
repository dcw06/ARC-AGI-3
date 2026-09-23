"""Dimension-separated metrics with deterministic rational one-to-one matching."""
import itertools,json
from fractions import Fraction
from .fixtures import D4,inverse

def box(b):
    if type(b) is not list or len(b)!=4 or any(type(v) is not int or not 0<=v<64 for v in b) or b[0]>b[2] or b[1]>b[3]:raise ValueError('bbox')
    return {(x,y) for y in range(b[1],b[3]+1) for x in range(b[0],b[2]+1)}
def iou(a,b):return Fraction(len(a&b),len(a|b))
def strict_json(content):
    def pairs(rows):
        d={}
        for k,v in rows:
            if k in d:raise ValueError('duplicate key')
            d[k]=v
        return d
    return json.loads(content,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite')))
def parse(content,finish):
    if finish!='stop' or len(content.encode())>32768:raise ValueError('unfinished/oversized')
    v=strict_json(content)
    if type(v) is not dict or set(v)!= {'objects','non_object_regions','relations'}:raise ValueError('fields')
    for field,limit in [('objects',6),('non_object_regions',3),('relations',6)]:
        if type(v[field]) is not list or len(v[field])>limit:raise ValueError(field)
    ids=set()
    def text(s,n):
        if type(s) is not str or not 0<len(s)<=n:raise ValueError('text')
    def colors(s):
        if type(s) is not list or len(s)>3 or any(type(x) is not int or not 0<=x<=15 for x in s) or len(set(s))!=len(s):raise ValueError('colors')
    for o in v['objects']:
        if type(o) is not dict or set(o)!={'id','bbox','colors','occupancy','has_markings','marking_colors','description'}:raise ValueError('object')
        text(o['id'],24);text(o['description'],48);box(o['bbox']);colors(o['colors']);colors(o['marking_colors'])
        if o['id'] in ids:raise ValueError('duplicate id')
        ids.add(o['id'])
        if type(o['has_markings']) is not bool:raise ValueError('markings')
        a=o['occupancy']
        if type(a) is not list or len(a)!=3 or any(type(r) is not list or len(r)!=3 or any(type(x) is not int or x not in (0,1) for x in r) for r in a):raise ValueError('occupancy')
    for o in v['non_object_regions']:
        if type(o) is not dict or set(o)!={'bbox','description'}:raise ValueError('region')
        box(o['bbox']);text(o['description'],48)
    for r in v['relations']:
        if type(r) is not dict or set(r)!={'a','b','same_shape','transform'}:raise ValueError('relation')
        if r['a'] not in ids or r['b'] not in ids or r['a']==r['b'] or type(r['same_shape']) is not bool or r['transform'] not in (*D4,'different_shape','uncertain'):raise ValueError('relation values')
    return v
def ratio(n,d):return {'numerator':n,'denominator':d,'rate':float(Fraction(n,d)) if d else None}
def score(case,content,finish='stop'):
    error=None
    try:v=parse(content,finish)
    except (ValueError,TypeError,KeyError) as exc:error=str(exc);v={'objects':[],'relations':[],'non_object_regions':[]}
    truth=case['reference']['objects'];pred=v['objects'];t=[box(o['bbox']) for o in truth];p=[box(o['bbox']) for o in pred]
    best=None
    for choice in itertools.product([None]+list(range(len(p))),repeat=len(t)):
        used=[i for i in choice if i is not None]
        if len(used)!=len(set(used)) or any(i is not None and not t[j]&p[i] for j,i in enumerate(choice)):continue
        total=sum((iou(t[j],p[i]) for j,i in enumerate(choice) if i is not None),Fraction())
        tie=tuple(len(p) if i is None else i for i in choice)
        if best is None or total>best[0] or total==best[0] and tie<best[1]:best=(total,tie,choice)
    matches={j:i for j,i in enumerate(best[2]) if i is not None and iou(t[j],p[i])>=Fraction(1,2)}
    used=set(matches.values());extras=set(range(len(p)))-used
    matched=len(matches);contour=colors=mark=markcolors=exact=cellcorrect=0;local=[]
    for j,i in matches.items():
        a,b=truth[j],pred[i];same=a['occupancy']==b['occupancy'];contour+=same;exact+=a['bbox']==b['bbox']
        colors+=set(a['colors'])==set(b['colors']);mark+=a['has_markings']==b['has_markings'];markcolors+=set(a['marking_colors'])==set(b['marking_colors'])
        cellcorrect+=sum(x==y for r,s in zip(a['occupancy'],b['occupancy']) for x,y in zip(r,s))
        local.append({'reference':a['id'],'prediction':b['id'],'bbox_iou':float(iou(t[j],p[i]))})
    mapping={pred[i]['id']:truth[j]['id'] for j,i in matches.items()};relations={};duplicates=extraneous=0
    order={o['id']:i for i,o in enumerate(truth)}
    for r in v['relations']:
        if r['a'] not in mapping or r['b'] not in mapping:extraneous+=1;continue
        a,b=mapping[r['a']],mapping[r['b']];trans=r['transform']
        if order[a]>order[b]:a,b=b,a;trans=inverse(trans) if trans in D4 else trans
        if (a,b) in relations:duplicates+=1;continue
        relations[a,b]=(r['same_shape'],trans)
    samecorrect=transformcorrect=coarse=missing=0;shape_pairs=0
    for r in case['reference']['relations']:
        value=relations.get((r['a'],r['b']));valid=r['transforms'];shape_pairs+=bool(valid)
        if value is None:missing+=1;continue
        samecorrect+=value[0]==bool(valid);transformcorrect+=bool(valid) and value[1] in valid
        coarse+=bool(valid) and value[1] in D4 and any(value[1].startswith('mirror')==x.startswith('mirror') for x in valid)
    return {'valid':error is None,'error':error,'case':case['id'],'source_group':case['source_group'],
        'detection_recall':ratio(matched,len(t)),'detection_precision':ratio(matched,len(p)),
        'misses':len(t)-matched,'extraneous_objects':len(extras),
        'duplicate_objects':sum(any(iou(p[i],t[j])>=Fraction(1,2) for j in matches) for i in extras),
        'distractor_errors':sum(any(iou(q,box(b))>=Fraction(1,2) for b in case['reference']['non_object_regions']) for q in p),
        'localization':local,'bbox_exact':ratio(exact,matched),'contour_exact':ratio(contour,matched),
        'contour_cells':ratio(cellcorrect,9*matched),'detected_and_contour_exact':ratio(contour,len(t)),
        'colors':ratio(colors,matched),'has_markings':ratio(mark,matched),'marking_colors':ratio(markcolors,matched),
        'detected_and_markings_correct':ratio(mark,len(t)),'detected_and_marking_colors_correct':ratio(markcolors,len(t)),
        'same_shape':ratio(samecorrect,len(case['reference']['relations'])),'transform':ratio(transformcorrect,shape_pairs),
        'rotation_vs_reflection':ratio(coarse,shape_pairs) if case['chiral_scoring'] else None,
        'missing_relations':missing,'duplicate_relations':duplicates,'extraneous_relations':extraneous}
