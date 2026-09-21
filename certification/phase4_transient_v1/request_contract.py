"""Model-side request guards: standard library only, no game environment imports."""
import json
from pathlib import Path
from functools import lru_cache
from certification.phase4_transient_v1.action_contract import response_format,request_legal_actions
ROOT=Path(__file__).resolve().parents[2]
@lru_cache(maxsize=1)
def protocol():return json.loads((ROOT/'reports/phase4_transient_v1_protocol.json').read_text())

def validate_request(request):
    spec=protocol()
    if set(request)!={'model','messages','temperature','seed','max_tokens','chat_template_kwargs','response_format'}:
        raise ValueError('request fields')
    if (request['model']!=spec['model_binding']['model_id'] or type(request['seed']) is not int
        or request['seed'] not in (0,1,2) or type(request['temperature']) not in (int,float) or request['temperature']!=0
        or type(request['max_tokens']) is not int or request['max_tokens']!=128
        or request['chat_template_kwargs']!={'enable_thinking':False}):raise ValueError('request settings')
    messages=request['messages']
    if (len(messages)!=2 or [m['role'] for m in messages]!=['system','user']
        or messages[0]['content'] not in [v['text'] for v in spec['prompts'].values()]):raise ValueError('prompt')
    if request['response_format']!=response_format(request_legal_actions(messages)):raise ValueError('schema')
    from certification.phase4_transient_v1.selection import enforce_payload
    enforce_payload(request)
    payload=json.loads(messages[1]['content'])
    expected={'current_grid','state','levels_completed','win_levels','legal_actions','previous_grid',
              'recent_actions','recent_final_grids','history_compaction'}
    if set(payload)!={'observation'}:raise ValueError('observation envelope')
    keys=set(payload['observation'])
    if keys not in (expected,expected|{'last_transition_intermediate_grid'}):raise ValueError('observation fields')
