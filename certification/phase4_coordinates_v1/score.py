"""Recompute answers from actual requests; never trust stored answer keys."""
import json
from collections import Counter

def truth(case):
    p=json.loads(case['request']['messages'][1]['content']);g=p['grid'];x,y=p['x'],p['y']
    if type(x) is not int or type(y) is not int or not 0<=x<len(g) or not 0<=y<len(g):raise ValueError('coordinate')
    if not 1<=len(g)<=64 or any(len(row)!=len(g) or any(type(c) is not int or not 0<=c<=15 for c in row) for row in g):raise ValueError('grid')
    # Flattening is independent of builder's two-dimensional indexing.
    flat=[c for row in g for c in row];n=len(g);target,transpose=flat[y*n+x],flat[x*n+y]
    if x==y or target==transpose:raise ValueError('ambiguous target/transpose')
    return target,transpose

def classify(case,content):
    target,transpose=truth(case)
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:raise ValueError('duplicate key')
            d[k]=v
        return d
    try:
        value=json.loads(content,object_pairs_hook=unique)
        if type(value) is not dict or set(value)!={'color'} or type(value['color']) is not int or not 0<=value['color']<=15:raise ValueError('schema')
    except (ValueError,TypeError):return 'malformed'
    return 'correct' if value['color']==target else 'transposed' if value['color']==transpose else 'other_valid'

def evaluate(cases,responses):
    ids=[c['case_id'] for c in cases]
    if len(ids)!=len(set(ids)) or len(responses)!=len(ids):raise ValueError('inventory')
    result={'technical_passed':True,'errors':[],'by_condition':{},'by_size':{},'by_stratum':{},'by_source':{},'condition_by_size':{},'condition_by_stratum':{},'condition_by_source':{},'pairs':{},'cases':[]}
    for case,row in zip(cases,responses):
        if row.get('case_id')!=case['case_id'] or row.get('request_sha256')!=case['request_sha256']:raise ValueError('response order/identity')
        if row.get('status')=='missing':
            if not isinstance(row.get('error'),str) or not row['error'] or 'content' in row:raise ValueError('invalid missing receipt')
            category='missing';result['errors'].append(case['case_id']+': execution failure')
        elif row.get('status')=='received' and isinstance(row.get('content'),str):category=classify(case,row['content'])
        else:raise ValueError('response envelope')
        result['cases'].append({'case_id':case['case_id'],'category':category})
        for key,label in [('by_condition',case['condition']),('by_size',f'{case["source_kind"]}-{case["size"]}'),('by_stratum',case['stratum']),('by_source',case['source_group'])]:
            bucket=result[key].setdefault(label,Counter());bucket['planned']+=1;bucket[category]+=1
        for key,label in [('condition_by_size',f'{case["source_kind"]}-{case["size"]}'),('condition_by_stratum',case['stratum']),('condition_by_source',case['source_group'])]:
            bucket=result[key].setdefault(case['condition']+':'+label,Counter());bucket['planned']+=1;bucket[category]+=1
        result['pairs'].setdefault(case['pair_id'],{})[case['condition']]=category
    paired=Counter()
    for pair in result['pairs'].values():
        if set(pair)!={'baseline','explicit'}:raise ValueError('incomplete condition pair')
        a,b=pair['baseline'],pair['explicit']
        category='incomplete' if 'missing' in (a,b) else 'improvement' if a!='correct' and b=='correct' else 'regression' if a=='correct' and b!='correct' else 'unchanged_correctness'
        paired[category]+=1
    result['paired_correctness']=dict(paired);result['technical_passed']=not result['errors']
    for key in ('by_condition','by_size','by_stratum','by_source','condition_by_size','condition_by_stratum','condition_by_source'):
        for bucket in result[key].values():bucket['exact_accuracy']=bucket['correct']/bucket['planned']
    return result
