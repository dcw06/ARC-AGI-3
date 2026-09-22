"""Frozen case inventory and exact requests; independent of environment APIs."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def request_hash(request):return hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest()
def canary_request(model):
    from certification.phase4_grounding_v1.action_contract import response_format
    return {'model':model,'messages':[{'role':'system','content':'Return a JSON action object for ACTION6 with integer x and y in [0,63].'},
        {'role':'user','content':'Choose display coordinates for a click; return only the action JSON.'}],
        'temperature':0,'seed':0,'max_tokens':128,'chat_template_kwargs':{'enable_thinking':False},'response_format':response_format([6])}
def load_cases():
    rows=json.loads(Path(__file__).with_name('cases.json').read_bytes())
    ids=[r['case_id'] for r in rows]
    if len(rows)!=12 or len(set(ids))!=12 or len({r['request_sha256'] for r in rows})!=12:raise ValueError('case inventory')
    for row in rows:
        if row['request_sha256']!=request_hash(row['request']):raise ValueError('request binding')
    return rows
