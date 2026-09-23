"""Strict answer parsing; correctness is a recorded outcome, never a pass condition."""
import json
QUADRANTS=('top_left','top_right','bottom_left','bottom_right','none')

def parse(content,probe):
    def pairs(rows):
        out={}
        for k,v in rows:
            if k in out:raise ValueError('duplicate key')
            out[k]=v
        return out
    value=json.loads(content,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite')))
    if not isinstance(value,dict):raise ValueError('object required')
    color=value.get('color')
    if probe=='I1':
        if set(value)!={'color'} or type(color) is not int or not 0<=color<=15:raise ValueError('canary answer')
    else:
        if set(value)!={'quadrant','color'} or value['quadrant'] not in QUADRANTS:raise ValueError('board answer')
        if color is not None and (type(color) is not int or not 0<=color<=15):raise ValueError('color')
    return value

def score(row,content,finish_reason):
    """Invalid if unparseable or not finished with stop; otherwise exact comparison."""
    try:
        if finish_reason!='stop':raise ValueError('non-stop finish')
        actual=parse(content,row['probe_id'])
    except (ValueError,TypeError) as exc:
        return {'valid':False,'correct':False,'answer':None,'error':str(exc)[:128]}
    return {'valid':True,'correct':actual==row['expected'],'answer':actual,'error':None}

def behavioural(i2,i3):
    """Two visibly different boards, same question. Identical valid answers need review."""
    if not (i2 and i3 and i2.get('valid') and i3.get('valid')):return 'inconclusive_invalid_or_missing'
    if i2['answer']==i3['answer']:return 'identical_answers_review_required'
    return 'answers_differ_both_correct' if i2['correct'] and i3['correct'] else 'answers_differ'
