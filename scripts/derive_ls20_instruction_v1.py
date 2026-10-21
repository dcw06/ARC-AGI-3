"""Derive the already-reviewed lifecycle/package boundary, never execute it."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARENTS=('live_runtime.py','live_package.py','live_operator.py','live_evaluation.py','source_closure.py')

def replace(value,before,after):
    if value.count(before)!=1:raise ValueError('parent template changed: '+before)
    return value.replace(before,after)

def derive():
    pins=json.loads(Path(__file__).with_suffix('.parents.json').read_bytes());result={}
    for leaf in PARENTS:
        name='research/verified_feedback_live_v1/'+leaf;raw=(ROOT/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=pins[name]:raise ValueError('parent source pin differs')
        text=raw.decode().replace('verified_feedback_live_v1','ls20_instruction_v1')
        text=text.replace('verified-feedback-v1-','ls20-instruction-v1-').replace('VERIFIED_FEEDBACK_V1_','LS20_INSTRUCTION_V1_')
        for label in ('private_runtime','return_witness','live_review_lock','readonly_preflight','independent_evaluation'):
            text=text.replace('verified_feedback_'+label+'_v1','ls20_instruction_'+label+'_v1')
        if leaf=='live_runtime.py':
            begin=text.index('SCOPE = ');end=text.index('\n\n\ndef check_authority',begin)
            scope=dict(GPU='one RTX PRO 6000',session_timeout_seconds=3600,worker_seconds=3300,
                admission_seconds=3000,cleanup_reserve_seconds=300,generations=41,counted_HTTP_requests=41,
                policy_actions=40,bootstrap_resets=1,offline_engine_actions=41,local_scorecards=1,
                online_game_calls=0,online_scorecards=0,scoreboard_submissions=0,automatic_retries=0,
                attempts=1,access='private_account_only',internet=False,TPU=False)
            text=text[:begin]+'SCOPE = '+repr(scope)+text[end:]
            text=replace(text,"len(worker['conditions']) != 16", "len(worker['episodes']) != 1")
        elif leaf=='live_package.py':
            begin=text.index('    execution_roots = [');end=text.index('    sources = source_inventory(root, review_roots)',begin)
            roots="""    execution_roots = [
        'research/ls20_instruction_v1/live_runtime.py','research/ls20_instruction_v1/live_worker.py',
        'research/initial_geometry_assistance_v1/engine_bridge.py','agent/framework_adapter.py',
        'research/ls20_instruction_v1/live_protocol.json',
        'certification/direct_publisher_smoke_v1/proposal.json',
        'certification/direct_publisher_smoke_v1/trusted_manifest.json',
        'certification/direct_publisher_smoke_v1/trusted_requirements.lock']
    execution_sources = source_inventory(root, execution_roots)
    review_roots = execution_roots + [
        'research/ls20_instruction_v1/live_package.py','research/ls20_instruction_v1/live_operator.py',
        'research/ls20_instruction_v1/live_evaluation.py','research/ls20_instruction_v1/audit.py',
        'research/ls20_instruction_v1/runtime_template.json',
        'scripts/derive_ls20_instruction_v1.py','scripts/derive_ls20_instruction_v1.parents.json',
        'tests/test_ls20_instruction_v1.py']
"""
            text=text[:begin]+roots+text[end:]
            text=replace(text,'Private verified executed-feedback comparison: sixteen conditions, at most thirty-three generations.',
                'Private ls20 level-1 instruction-following pilot: one episode, at most forty-one generations. Review only.')
        elif leaf=='live_evaluation.py':
            text=replace(text,'from .live_contract import check_checkpoints, verify_inputs, MAX_PROMPT_TOKENS',
                'from .live_contract import verify_inputs, MAX_PROMPT_TOKENS')
            begin=text.index('    checkpoints = check_checkpoints(')
            end=text.index('    if not required <= set(evidence):',begin)
            text=text[:begin]+"    required.add('ls20-instructed.jsonl')\n"+text[end:]
            text=replace(text,'Eight correlated exposed checkpoints; descriptive feedback-presentation comparison only. Supplied retrospective labels earn no understanding credit. No advancement or generalization claim.',
                'One exposed ls20 level-1 episode with supplied controls and rules. VLM plans the actions. No rule-discovery or generalization claim.')
        result['research/ls20_instruction_v1/'+leaf]=text
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    result=derive()
    for name,value in result.items():
        path=ROOT/name
        if args.check:
            if path.read_bytes()!=value.encode():raise ValueError('derived source changed: '+name)
        else:path.write_bytes(value.encode())
    print(json.dumps(dict(matched=True,derived_files=len(result),GPU_jobs=0)))

if __name__=='__main__':main()
