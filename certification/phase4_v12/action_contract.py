"""Versioned action schema shared by game requests and model-only startup probe."""
import json

CONTRACT_ID='arc_action_v12'


def legal_ids(values):
    values=list(values)
    if not values or any(type(v) is not int or not 1<=v<=7 for v in values):
        raise ValueError('nonempty legal action IDs 1..7 required')
    return sorted(set(values))


def response_format(legal):
    legal=legal_ids(legal)
    def branch(ids,data):
        return {'type':'object','properties':{'action_id':{'type':'integer','enum':ids},
            'action_data':data},'required':['action_id','action_data'],'additionalProperties':False}
    branches=[]
    simple=[v for v in legal if v!=6]
    if simple:branches.append(branch(simple,{'type':'object','properties':{},'additionalProperties':False}))
    if 6 in legal:
        branches.append(branch([6],{'type':'object','properties':{
            'x':{'type':'integer','minimum':0,'maximum':63},
            'y':{'type':'integer','minimum':0,'maximum':63}},
            'required':['x','y'],'additionalProperties':False}))
    schema={'type':'object','properties':{'action':{'anyOf':branches}},
        'required':['action'],'additionalProperties':False}
    return {'type':'json_schema','json_schema':{'name':CONTRACT_ID,'strict':True,'schema':schema}}


def request_legal_actions(messages):
    if len(messages)!=2 or messages[0]['role']!='system' or messages[1]['role']!='user':
        raise ValueError('v12 requires one stateless observation request')
    return legal_ids(json.loads(messages[1]['content'])['observation']['legal_actions'])


def validate_action(content, legal):
    legal=legal_ids(legal)
    value=json.loads(content)
    if not isinstance(value,dict) or set(value)!={'action'}:raise ValueError('invalid action object')
    action=value['action']
    if not isinstance(action,dict) or set(action)!={'action_id','action_data'} or type(action['action_id']) is not int or action['action_id'] not in legal:
        raise ValueError('action_id must be a currently legal integer')
    data=action['action_data']
    if action['action_id']==6:
        if not isinstance(data,dict) or set(data)!={'x','y'} or any(type(v) is not int or not 0<=v<=63 for v in data.values()):
            raise ValueError('ACTION6 requires valid integer x and y in [0,63]')
    elif not isinstance(data,dict) or data:
        raise ValueError('only ACTION6 may carry action_data')
    return value


def validate_canary(content):
    # Standard-library-only: the model environment cannot import game libraries.
    return validate_action(content,[6])
