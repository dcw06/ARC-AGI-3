"""Read-only checks of the frozen integrated specification and reuse blockers."""
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def check():
    subprocess.run([sys.executable,str(ROOT/'scripts/build_integrated_case_v1.py'),'--check'],check=True)
    from certification.phase4_transient_v2.request_contract import validate_request
    spec=json.loads((ROOT/'certification/phase4_transient_v2/protocol.json').read_bytes())
    request={'model':spec['model_binding']['model_id'],'messages':[],
             'temperature':0,'seed':0,'max_tokens':2048,
             'chat_template_kwargs':{'enable_thinking':False},'response_format':{}}
    try:validate_request(request)
    except ValueError as exc:
        assert str(exc)=='request settings'
    else:raise AssertionError('historical guard unexpectedly accepts structured completion cap')
    request['max_tokens']=128
    request['messages']=[{'role':'system','content':'Identify visible regions and state observable predictions.'},
                         {'role':'user','content':'{}'}]
    try:validate_request(request)
    except ValueError as exc:
        assert str(exc)=='prompt'
    else:raise AssertionError('historical guard unexpectedly accepts new prompt')
    from certification.phase4_transient_v2.authority import LIMITS
    assert LIMITS['maximum_episodes']==6 and LIMITS['maximum_policy_calls']==120
    case=json.loads((ROOT/'reports/integrated_case_v1/case.json').read_bytes())
    assert case['max_actions_per_arm']==8 and case['max_model_calls']==26
    assert case['provider_seconds_authorized']==0
    assert 8*128+2048+8*1024+8*1024+128==case['max_generated_tokens']
    return {'specification_checks':'passed','historical_guard_rejects_2048_tokens':True,
            'historical_guard_rejects_structured_prompt':True,
            'historical_authority_scope_matches':False,
            'integrated_runner_exists':(ROOT/'certification/phase4_integrated_v1/worker.py').exists(),
            'integrated_review_notebook_exists':(ROOT/'notebooks/phase4-integrated-v1-review-r1/profile.ipynb').exists(),
            'launch_ready':False,'model_calls':0,'gpu_runs':0,
            'reason':'Specification-only package; historical executable request and authority contracts are incompatible.'}

if __name__=='__main__':print(json.dumps(check(),indent=2))
