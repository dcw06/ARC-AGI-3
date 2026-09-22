"""Offline review probes; never starts a model, environment or launch helper."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_integrated_case_v1 import build,encode
from certification.phase4_transient_v2.request_contract import validate_request
from certification.phase4_transient_v2.response_evidence import capture
from certification.phase4_transient_v2.selection import enforce_payload

def rejected(fn):
    try:fn()
    except ValueError as exc:return str(exc)
    raise AssertionError('Expected historical limit rejection')

def check():
    folder=ROOT/'reports/integrated_case_v1'
    lock=json.loads((folder/'spec-lock.json').read_bytes())
    for name,digest in lock['bindings'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    values=build()
    for name,value in values.items():assert (folder/name).read_bytes()==encode(value),name
    spec=json.loads((ROOT/'certification/phase4_transient_v2/protocol.json').read_bytes())
    base={'model':spec['model_binding']['model_id'],'temperature':0,'seed':0,
          'chat_template_kwargs':{'enable_thinking':False},'response_format':{},
          'max_tokens':2048,'messages':[]}
    limit=rejected(lambda:validate_request(base));assert limit=='request settings'
    base.update(max_tokens=128,messages=[{'role':'system','content':'Structured inventory'},
                                       {'role':'user','content':'{}'}])
    prompt=rejected(lambda:validate_request(base));assert prompt=='prompt'
    # Constructed stress case, NOT a claim that ar25 returned six frames.
    grid=values['initial_observation.json']['frames'][-1]
    request={'messages':[{'role':'system','content':'Review changes.'},
                         {'role':'user','content':json.dumps({'pre':grid,'frames':[grid]*6})}]}
    payload_bytes=len(json.dumps(request).encode())
    payload_error=rejected(lambda:enforce_payload(request))
    assert payload_error=='request byte limit'
    raw='x'*8193;evidence=capture(raw,{})
    assert evidence['response_truncated'] and evidence['response_bytes']==8193
    assert len(evidence['response_content'].encode())==8192
    assert evidence['response_sha256']==hashlib.sha256(raw.encode()).hexdigest()
    a,b,c=[{tuple(p) for p in o['cells']} for o in values['geometry_reference.json']['objects']]
    assert {(62-x,y) for x,y in a}==b and {(x+15,y+30) for x,y in b}==c
    assert all(len(v)==45 for v in (a,b,c))
    assert 8+1+8+8+1==26 and 8*128+2048+16*1024+128==19584
    files=['certification/phase4_transient_v2/request_contract.py',
           'certification/phase4_transient_v2/service.py','certification/phase4_transient_v2/bridge.py',
           'certification/phase4_transient_v2/response_evidence.py','agent/state.py',
           'agent/framework_adapter.py','reports/integrated_case_v1/spec-lock.json']
    return {'status':'review_probes_passed_not_launch_acceptance',
            'frozen_spec_unchanged':True,'geometry_and_budget_checks':True,
            'historical_completion_guard':limit,'historical_prompt_guard':prompt,
            'constructed_six_frame_request_bytes':payload_bytes,'historical_payload_guard':payload_error,
            'response_8193_bytes_retained':8192,'response_full_hash_preserved':True,
            'response_truncation_flag':True,
            'historical_bridge_max_bytes':1048576,
            'baseline_code_not_bound_by_spec_lock':[n for n in (
                'certification/phase4_transient_v2/contract.py',
                'certification/phase4_transient_v2/action_contract.py','agent/representation.py') if n not in lock['bindings']],
            'missing_executable_deliverables':[n for n in (
                'certification/phase4_integrated_v1/worker.py',
                'certification/phase4_integrated_v1/evaluate.py',
                'notebooks/phase4-integrated-v1-review-r1/profile.ipynb') if not (ROOT/n).exists()],
            'inspected_file_hashes':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in files},
            'model_calls':0,'environment_actions':0,'gpu_runs':0}

if __name__=='__main__':print(json.dumps(check(),indent=2))
