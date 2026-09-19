"""Freeze a matched development protocol and budget proposal; never launch compute."""
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sha=lambda value:hashlib.sha256(value).hexdigest()

def prepare(proposal,features):
    games=sorted({row['game_id'] for row in proposal['cases']})
    if len(games)!=15:raise ValueError('exact 15 development games required')
    prompts={}
    for arm in ('baseline','no_concrete_examples'):
        texts={r['request']['messages'][0]['content'] for r in proposal['cases'] if r['arm']==arm}
        if len(texts)!=1:raise ValueError('system prompt drift')
        text=texts.pop();prompts[arm]={'text':text,'sha256':sha(text.encode())}
    schedule=[]
    for index,game in enumerate(games):
        arms=['baseline','no_concrete_examples']
        if index%2:arms.reverse()
        for arm in arms:
            schedule.append({'episode_id':f'cl1-{index:02d}-{arm}','pair_index':index,
                'game_id':game,'arm':arm,'environment_seed':0,'request_seed':0,
                'max_decisions':20,'max_dispatch_attempts':20,'max_initial_bootstraps':1})
    protocol={'id':'phase4-closed-loop-v1','status':'frozen_protocol_pending_review_and_runner',
        'configuration':'E1S-R-derived arc_action_v12 closed-loop two-arm development comparison',
        'model_binding':features['model_binding'],
        'model_tree_sha256':'052ab27f06c28261e143b8c1638382d107b034692bc0cd1792ec4e02ddab8627',
        'environment':{'python':'3.12','torch_distribution':'2.10.0','torch_runtime':'2.10.0+cu128',
            'cuda':'12.8','vllm':'0.19.0','transformers':'4.57.6','split_model_game_environments':True},
        'model_mount':'/kaggle/input/models/qwen-lm/qwen-3-vl/transformers/30b-a3b-instruct-fp8/1',
        'prompts':prompts,'schedule':schedule,'distinct_games':15,'pairs':15,'episodes':30,
        'request_settings':{'temperature':0,'seed':0,'max_tokens':128,'enable_thinking':False,
            'action_output_contract':'arc_action_v12','context_tokens':65536,'prompt_token_ceiling':65408},
        'representation':{'treatment_parent':'E1S-R','workspace':'none','recent_transition_limit':1,
            'context_mode':features['shared']['context_mode'],
            'history_loss_reporting':features['shared']['history_loss_reporting']},
        'initial_pair_equality_required':True,'policy_fallbacks':0,'later_resets':0,'automatic_retries':0,
        'primary_measures':['paired_completed_level_delta','episodes_ending_WIN'],
        'secondary_measures':['acknowledged_transitions','canonical_change_rate','frame_change_rate',
            'adjacent_action_repeat_rate','longest_action_streak','repeats_after_unchanged_observation',
            'first_level_progress_step','action_distribution','click_coordinates','terminal_reason'],
        'full_transition_evidence_required':True,'partial_attempt_cannot_pass':True,
        'source_approval':None,'compute_authorization':None,'phase4_complete':False,'production_C_admit':None}
    budget={'id':'phase4-closed-loop-v1-compute-proposal','status':'proposed_not_authorized_not_reserved',
        'proposed_attempts':1,'authorized_attempts':0,'authorized_seconds':0,'reservation':None,
        'proposed_provider_seconds':3600,'internal_seconds':3300,'installation_deadline_seconds':900,
        'model_startup_seconds':900,'workload_seconds':1200,'absolute_workload_cutoff_seconds':3000,
        'cleanup_reserve_seconds':300,'max_policy_calls':600,'max_canary_calls':1,'max_total_calls':601,
        'max_output_tokens_per_call':128,'max_total_output_tokens':76928,'max_dispatch_attempts':600,
        'max_bootstraps':30,'max_local_scorecard_opens':30,'max_local_scorecard_closes':30,
        'concurrency':1,'automatic_retries':0,'request_timeout_seconds':120,'bridge_timeout_seconds':180,
        'private':True,'internet':False,'accelerator':'NvidiaRtxPro6000',
        'vram_gib':86,'ram_gib':128,'scratch_gib':4,'evidence_mib':128,
        'evidence_component_mib':{'control':4,'monitor':16,'worker':88,'evaluation':12,'logs':8},
        'response_prefix_bytes':8192,'failure_frame_bytes':65536,'max_record_bytes':1048576,
        'monitor_interval_seconds':0.25,'maximum_sample_gap_seconds':1,
        'exact_provider_billed_seconds':None,'production_runs':0,'holdout_runs':0}
    return protocol,budget

def main():
    proposal=json.loads((ROOT/'reports/phase4_action_selection_probe_proposal.json').read_text())
    features=json.loads((ROOT/'config/e1_feature_manifests.yaml').read_text())
    protocol,budget=prepare(proposal,features)
    for name,value in [('protocol',protocol),('compute_budget',budget)]:
        with (ROOT/f'reports/phase4_closed_loop_v1_{name}.json').open('x',encoding='utf-8') as f:
            json.dump(value,f,indent=2)
    print('Prepared 15 matched pairs, 600 policy calls maximum; zero compute authorized.')

if __name__=='__main__':main()
