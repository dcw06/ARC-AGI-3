"""Derive lifecycle/transport safeguards from pinned pilot sources; no execution."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def change(text,before,after,count=1):
    if text.count(before)!=count:raise ValueError('parent template differs: '+before)
    return text.replace(before,after)

def derive():
    pins=json.loads(Path(__file__).with_suffix('.parents.json').read_bytes());result={}
    for name,pin in pins.items():
        raw=(ROOT/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=pin:raise ValueError('parent changed: '+name)
        text=raw.decode();leaf=Path(name).name
        text=text.replace('action_effect_choice_live_v2','verified_feedback_live_v1')
        text=text.replace('action_effect_pilot_fixture','verified_feedback_live_fixture')
        text=text.replace('test_action_effect_pilot_','test_verified_feedback_live_')
        text=text.replace('ACTION_EFFECT_CHOICE_V2_','VERIFIED_FEEDBACK_V1_')
        text=text.replace('action-effect-choice-v2-','verified-feedback-v1-')
        text=text.replace('neutral_choice','summary_only').replace('compare_review','verified_feedback')
        for label in ('worker','private_runtime','return_witness','live_review_lock','readonly_preflight','independent_content','independent_evaluation'):
            text=text.replace('action_effect_choice_'+label+'_v2','verified_feedback_'+label+'_v1')
        if leaf=='live_worker.py':
            text=text.replace('from research.action_effect_choice_v2.flow import run_case','from research.verified_feedback_v1.flow import run_case')
            for a,b in [('len(ids) > 9','len(ids) > 33'),('super().__init__(plan, 9, clock)','super().__init__(plan, 33, clock)'),
                        ('resets >= 4','resets >= 16'),('dispatches >= 16','dispatches >= 68'),('closes >= 4','closes >= 16')]:text=change(text,a,b)
        elif leaf=='live_runtime.py':
            for a,b in [("'generations': 9, 'counted_HTTP_requests': 9","'generations': 33, 'counted_HTTP_requests': 33"),
                ("'checkpoints': 2, 'policy_conditions': 4","'checkpoints': 8, 'policy_conditions': 16"),
                ("'policy_actions': 8, 'prefix_dispatches': 8, 'bootstrap_resets': 4, 'offline_engine_actions': 20",
                 "'policy_actions': 32, 'prefix_dispatches': 36, 'bootstrap_resets': 16, 'offline_engine_actions': 84"),
                ("'local_scorecards': 4","'local_scorecards': 16"),("len(worker['conditions']) != 4","len(worker['conditions']) != 16")]:text=change(text,a,b)
        elif leaf=='live_evaluation.py':
            text=change(text,'Four exposed compatibility conditions; phase-specific format coverage only. No arm advantage, forecast accuracy or gameplay advancement claim.',
                'Eight correlated exposed checkpoints; descriptive feedback-presentation comparison only. Supplied retrospective labels earn no understanding credit. No advancement or generalization claim.')
        elif leaf=='live_package.py':
            text=change(text,"execution_roots += ['research/action_effect_choice_v2/protocol.json']",
                "execution_roots += ['research/action_effect_choice_v2/protocol.json', 'research/verified_feedback_v1/protocol.json']")
            text=change(text,'Private phase-specific format-only pilot: four conditions, at most nine generations.',
                'Private verified executed-feedback comparison: sixteen conditions, at most thirty-three generations.')
        elif leaf=='rehearse_action_effect_choice_live_v2.py':
            text=change(text,"extension = json.loads(body['messages'][1]['content'][-1]['text'])",
                "extension = next(json.loads(p['text']) for p in body['messages'][1]['content'] if p['type']=='text' and p['text'].startswith('{') and 'candidate_choice_v1' in json.loads(p['text']))")
            text=change(text,"expected_replay['bootstrap'] < 4","expected_replay['bootstrap'] < 16")
        elif leaf.startswith('test_action_effect_pilot_'):
            for a,b in [('is_9_unique','is_33_unique'),('len(request_plan(rows)), 9','len(request_plan(rows)), 33'),
                ('(4, 16, 4)','(16, 68, 16)'),("['issued'], 9","['issued'], 33"),('len(sent), 9','len(sent), 33'),
                ("['conditions']), 4","['conditions']), 16"),("['issued'], 5","['issued'], 17"),
                ("['dispatch_attempts'], 8","['dispatch_attempts'], 36"),("['closed_scorecards'], 4","['closed_scorecards'], 16"),
                ('(9, 8, 8, 20, 4)','(33, 36, 32, 84, 16)'),("['generations'], 5","['generations'], 17"),
                ("['scheduled_candidate_forecasts'], 16","['scheduled_candidate_forecasts'], 64"),
                ("result['decisions']), 4","result['decisions']), 16"),('result[\'decisions\']), 4','result[\'decisions\']), 16')]:text=text.replace(a,b)
        target=name.replace('action_effect_choice_live_v2','verified_feedback_live_v1').replace('test_action_effect_pilot_','test_verified_feedback_live_')
        target=target.replace('scripts/build_action_effect_choice_live_v2.py','scripts/build_verified_feedback_live_v1.py')
        target=target.replace('scripts/rehearse_action_effect_choice_live_v2.py','scripts/rehearse_verified_feedback_live_v1.py')
        result[target]=text
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    files=derive()
    for name,text in files.items():
        path=ROOT/name
        if args.check:
            if path.read_bytes()!=text.encode():raise ValueError('derived source changed: '+name)
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(text.encode())
    print(json.dumps({'matched':True,'derived_files':len(files),'GPU_jobs':0}))
if __name__=='__main__':main()
