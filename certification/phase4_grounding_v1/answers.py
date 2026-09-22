"""Independent answer reconstruction and strict scoring; correctness is an outcome."""
import json

def components(grid,color):
    # Union-find differs from the builder's flood fill.
    w=len(grid[0]);parent={y*w+x:y*w+x for y,row in enumerate(grid) for x,v in enumerate(row) if v==color}
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    for i in parent:
        for j in (i-w,i-1 if i%w else -1):
            if j in parent:parent[find(i)]=find(j)
    groups={}
    for i in parent:groups.setdefault(find(i),[]).append((i%w,i//w))
    return list(groups.values())

def recompute(task):
    kind=task['kind']
    if kind=='coordinate':return {'color':task['grid'][task['y']][task['x']]}
    if kind=='locate':
        candidates=[p for p in components(task['grid'],task['color']) if len(p)==task['area']]
        if len(candidates)!=1:raise ValueError('ambiguous or absent component')
        points=candidates[0]
    elif kind=='changes':
        a,b=task['before'],task['after']
        if len(a)!=len(b) or any(len(r)!=len(s) for r,s in zip(a,b)):raise ValueError('shape mismatch')
        points=[(i,j) for j,row in enumerate(a) for i,v in enumerate(row) if v!=b[j][i]]
    else:raise ValueError('unknown task')
    points.sort(key=lambda p:(p[1],p[0]));first={'x':points[0][0],'y':points[0][1]} if points else None
    result={'count':len(points),'bbox':[min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)] if points else None,'first':first}
    if kind=='changes':result['first_change']={'before':task['before'][points[0][1]][points[0][0]],'after':task['after'][points[0][1]][points[0][0]]} if points else None
    return result

def schema(kind):
    integer=lambda maximum:{'type':'integer','minimum':0,'maximum':maximum}
    point={'type':'object','properties':{'x':integer(63),'y':integer(63)},'required':['x','y'],'additionalProperties':False}
    properties={'color':integer(15)} if kind=='coordinate' else {
        'count':integer(4096),'bbox':{'anyOf':[{'type':'null'},{'type':'array','items':integer(63),'minItems':4,'maxItems':4}]},
        'first':{'anyOf':[{'type':'null'},point]}}
    if kind=='changes':properties['first_change']={'anyOf':[{'type':'null'},{'type':'object','properties':{'before':integer(15),'after':integer(15)},'required':['before','after'],'additionalProperties':False}]}
    return {'type':'json_schema','json_schema':{'name':'grounding_'+kind,'strict':True,
        'schema':{'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}}}

def parse(content,kind):
    def pairs(rows):
        out={}
        for k,v in rows:
            if k in out:raise ValueError('duplicate key')
            out[k]=v
        return out
    value=json.loads(content,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite')))
    def integer(v,limit):return type(v) is int and 0<=v<=limit
    if not isinstance(value,dict):raise ValueError('object required')
    keys={'color'} if kind=='coordinate' else {'count','bbox','first'}|({'first_change'} if kind=='changes' else set())
    if set(value)!=keys:raise ValueError('keys')
    if kind=='coordinate':
        if not integer(value['color'],15):raise ValueError('color')
    else:
        if not integer(value['count'],4096):raise ValueError('count')
        b=value['bbox'];p=value['first']
        if b is not None and (type(b) is not list or len(b)!=4 or not all(integer(v,63) for v in b)):raise ValueError('bbox')
        if p is not None and (not isinstance(p,dict) or set(p)!={'x','y'} or not all(integer(v,63) for v in p.values())):raise ValueError('point')
        if kind=='changes':
            c=value['first_change']
            if c is not None and (not isinstance(c,dict) or set(c)!={'before','after'} or not all(integer(v,15) for v in c.values())):raise ValueError('change colors')
    return value

def score(case,content):
    expected=recompute(case['task'])
    try:actual=parse(content,case['task']['kind'])
    except (ValueError,TypeError):return {'malformed':True,'correct':False,'fields':{},'axis_swap_match':False}
    swapped=False;t=case['task']
    if t['kind']=='coordinate' and t['x']<len(t['grid']) and t['y']<len(t['grid'][0]):
        swapped=actual!=expected and actual=={'color':t['grid'][t['x']][t['y']]}
    return {'malformed':False,'correct':actual==expected,'fields':{k:actual[k]==v for k,v in expected.items()},'axis_swap_match':swapped}
