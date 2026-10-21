"""Derive a six-move instruction probe without altering the completed pilot."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def replace(text,before,after):
    if text.count(before)!=1:raise ValueError('parent template differs: '+before)
    return text.replace(before,after)

SYSTEM=(
    'Execute the supplied six-move instruction for the orange-and-blue player. '
    'The route is explicitly supplied: follow its order rather than inventing another route. '
    'Return exactly one legal action per reply, no reset, click or batch. '
    'Count actions already executed using the provided history; a blocked attempted move still counts. '
    'Images are 448 by 448, each native cell is 7 by 7 pixels, without overlays. '
    'Initial and previous images are historical; the current image shows the present state. '
    'Return only compact JSON with exactly action_id, action_data and predicted_visible_change. '
    'action_id is 1, 2, 3 or 4; action_data is always {}. '
    'predicted_visible_change is yes, no or unknown. No explanations or additional fields.'
)

def derive():
    pins=json.loads(Path(__file__).with_suffix('.parents.json').read_bytes());result={}
    for name,pin in pins.items():
        raw=(ROOT/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=pin:raise ValueError('parent changed: '+name)
        text=raw.decode().replace('ls20_instruction','ls20_six_move').replace('ls20-instruction','ls20-six-move')
        text=text.replace('LS20_INSTRUCTION','LS20_SIX_MOVE').replace('ls20/instructed/','ls20/six_move/').replace('ls20-instructed','ls20-six-move')
        leaf=Path(name).name
        if leaf=='live_contract.py':
            text=replace(text,'ACTION_CAP=40','ACTION_CAP=6')
            text=text.replace('Fixed private instruction text and initial board; demonstration moves excluded.',
                'Frozen initial board and explicit six-move instruction; future frames excluded.')
            text=text.replace('routes and reference answers are forbidden','only the frozen initial board and route instruction are allowed')
        elif leaf=='policy.py':
            start=text.index('SYSTEM=(');end=text.index('\n\ndef make_request',start)
            text=text[:start]+'SYSTEM='+repr(SYSTEM)+'\n'+text[end:]
            text=text.replace('Full-action VLM policy with supplied rules, but no route or object masks.',
                'VLM chooses one action per reply from an explicitly supplied six-move route.')
        elif leaf=='live_worker.py':
            text=replace(text,'request_plan(),41,clock','request_plan(),7,clock')
            text=text.replace('One bounded, private ls20 VLM episode; no route is available to the policy.',
                'One bounded ls20 VLM sequence-following probe; no forced or corrected actions.')
        elif leaf=='audit.py':
            text=replace(text,"ledger['maximum_model_requests']!=41","ledger['maximum_model_requests']!=7")
            text=replace(text,"    return dict(study_schedule_complete=",'''    from .live_contract import protocol
    frozen=protocol()
    transitions=[e['record'] for e in events if e['kind']=='transition']
    actions=[r['action']['action_id'] for r in transitions]
    states=[digest(r['after']) for r in transitions]
    commands_match=actions==frozen['expected_action_ids']
    states_match=states==frozen['expected_observation_sha256_by_step']
    return dict(command_following_success=commands_match,
        reference_execution_match=commands_match and states_match,
        executed_action_ids=actions,expected_action_ids=frozen['expected_action_ids'],
        observed_states_match_reference=states_match,
        study_schedule_complete=''')
            text=replace(text,'route_was_supplied=False','route_was_supplied=True')
            text=text.replace('One exposed instructed level-1 pilot; no discovery, generalization or comparison claim.',
                'One explicitly supplied six-move route; no autonomous planning, rule-discovery or level-solving claim.')
        elif leaf=='live_runtime.py':
            for before,after in (("'generations': 41","'generations': 7"),("'counted_HTTP_requests': 41","'counted_HTTP_requests': 7"),
                                 ("'policy_actions': 40","'policy_actions': 6"),("'offline_engine_actions': 41","'offline_engine_actions': 7")):
                text=replace(text,before,after)
        elif leaf=='live_package.py':
            text=text.replace('at most forty-one generations','at most seven generations')
            text=text.replace('level-1 instruction-following pilot','six-move sequence-following probe')
        elif leaf=='live_evaluation.py':
            text=text.replace('One exposed ls20 level-1 episode with supplied controls and rules. VLM plans the actions. No rule-discovery or generalization claim.',
                'One explicitly supplied six-move route. No autonomous route-planning, discovery or level-solving claim.')
        result['research/ls20_six_move_v1/'+leaf]=text.encode()
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    result=derive()
    for name,raw in result.items():
        path=ROOT/name
        if args.check:
            if path.read_bytes()!=raw:raise ValueError('derived source changed: '+name)
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    print(json.dumps(dict(matched=True,derived_files=len(result),GPU_jobs=0)))
if __name__=='__main__':main()
