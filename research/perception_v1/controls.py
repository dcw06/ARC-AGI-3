"""Interface knowledge fixtures, never a game-effect or action-selection test."""
import json
from certification.phase4_multimodal_preflight_v3.action_contract import response_format,validate_action
from .scoring import strict_json,ratio

def cases():
    spec=response_format(range(1,8))['json_schema']['schema']
    result=[]
    for supplied in (False,True):
        request={'action_specification':spec,'coordinate_convention':'grid[y][x]; x is column, y is row',
            'task':{'classify_coordinate_arguments_for_ids':list(range(1,8)),
                'click_cell':{'x':7,'y':23},'emit_non_coordinate_action_id':1,
                'directional_ids':'Return the list if stated, otherwise null.'},
            'output_fields':['coordinate_arguments','click','non_coordinate','directional_ids']}
        if supplied:request['supplied_interface_roles']={'1':'directional','2':'directional','3':'directional','4':'directional','5':'interact','6':'coordinate click','7':'undo'}
        expected={'coordinate_arguments':{str(i):i==6 for i in range(1,8)},
            'click':{'action_id':6,'action_data':{'x':7,'y':23}},'non_coordinate':{'action_id':1,'action_data':{}},
            'directional_ids':[1,2,3,4] if supplied else None}
        result.append({'id':'I2' if supplied else 'I1','request':request,'expected':expected})
    return result
def score(case,content,finish='stop'):
    try:
        if finish!='stop' or len(content.encode())>8192:raise ValueError('unfinished/oversized')
        value=strict_json(content);expected=case['expected']
        if type(value) is not dict or set(value)!=set(expected):raise ValueError('fields')
        args=value['coordinate_arguments']
        if type(args) is not dict or set(args)!={str(i) for i in range(1,8)} or any(type(v) is not bool for v in args.values()):raise ValueError('argument declarations')
        for key in ('click','non_coordinate'):validate_action(json.dumps({'action':value[key]}),range(1,8))
        direction=value['directional_ids']
        if direction is not None and (type(direction) is not list or len(direction)>7 or any(type(i) is not int or not 1<=i<=7 for i in direction) or len(set(direction))!=len(direction)):raise ValueError('directional list')
    except (ValueError,TypeError,KeyError) as exc:
        return {'valid':False,'error':str(exc),'arguments':ratio(0,7),'click':ratio(0,1),'non_coordinate':ratio(0,1),'directional':ratio(0,1)}
    return {'valid':True,'error':None,'arguments':ratio(sum(args[k]==expected['coordinate_arguments'][k] for k in args),7),
        'click':ratio(value['click']==expected['click'],1),'non_coordinate':ratio(value['non_coordinate']==expected['non_coordinate'],1),
        'directional':ratio(direction is None if expected['directional_ids'] is None else direction is not None and set(direction)==set(expected['directional_ids']),1)}
