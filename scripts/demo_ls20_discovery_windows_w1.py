"""CPU fixtures: fixed actions, prospective forecasts, raw trace, offline replay.

With --mac-source, load only the hash-verified M1 extractor package from that
checkout. Neither the engine nor a supplied-rule solver is imported.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from research.ls20_discovery_windows import M1View, HypothesisManager, execute_step
from research.ls20_discovery_windows.contract import digest, require
from research.ls20_discovery_windows.journal import read_checked, replay_payloads
from tests.ls20_windows_fixture import RawMemory, action, obs


def load_mac(source, commit):
    manifest=json.loads((ROOT/'research/ls20_discovery_windows/m1_sources.json').read_text())
    require(commit in manifest, 'unreviewed M1 source commit')
    for name,expected in manifest[commit].items():
        raw=(Path(source)/name).read_bytes().replace(b'\r\n',b'\n')
        require(hashlib.sha256(raw).hexdigest()==expected, 'M1 source differs: '+name)
    package=Path(source)/'research/ls20_discovery_mac'
    spec=importlib.util.spec_from_file_location('_windows_demo_mac_m1_'+commit,package/'__init__.py',
                                             submodule_search_locations=[str(package)])
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module.EvidenceMemory


def scenarios():
    # Outcomes and scenario names belong to the evaluator, never the predictor.
    return [
        ('misleading_then_transient',obs(),[
            (action(),dict(status='acknowledged',post=obs())),
            (action(),dict(status='acknowledged',post=obs(frames=[[[0,1]],[[0,0]]]))),
            (action(),dict(status='acknowledged',post=obs(frames=[[[0,1]],[[0,0]]])))]),
        ('action_context_confound',obs(state='A'),[
            (action(1),dict(status='acknowledged',post=obs([[0,1]],state='B'))),
            (action(2),dict(status='acknowledged',post=obs([[0,1]],state='B'))),
            (action(1),dict(status='acknowledged',post=obs([[0,1]],state='B'))),
            (action(1),dict(status='acknowledged',post=obs([[0,1]],state='B')))]),
        ('failed_and_unknown',obs(),[
            (action(),dict(status='dispatch_failed',error='scripted rejection before delivery')),
            (action(),dict(status='acknowledged',post=obs())),
            (action(),dict(status='outcome_unknown',reason='scripted lost reply'))])]


def verify_bundle(bundle):
    all_scores=[]
    for case in bundle['cases']:
        previous=None
        scores=[]
        for step,record in enumerate(case['steps']):
            if previous is not None:
                require(record['before']==previous, 'cross-step snapshot discontinuity')
            require(record['prediction']['mode']==case['mode'], 'comparison mode mismatch')
            scores.append(replay_payloads(record['before'],record['prediction'],record['after'],
                record['result'],step,bundle['m1_producer_commit']))
            previous=record['after']
        require(scores==case['scores'], 'stored scores differ')
        require(case['handoff']==HypothesisManager(M1View(previous,bundle['m1_producer_commit'])).export(),
                'handoff does not reconstruct')
        all_scores.extend(scores)
    return all_scores


def run(output, source=None, commit='f4bf522e96b1642bed8772c29f153bfe44f98bd5'):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    memory_class=load_mac(source,commit) if source else None
    bundle=dict(version='ls20_windows_w1_trace_v1',m1_producer_commit=commit,
        memory_kind='pinned_mac_m1' if source else 'raw_only_test_double',
        base_commit='1ad910bcd3a541279c4a6f224cce15368bec74aa',
        source_sha256={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in sorted((ROOT/'research/ls20_discovery_windows').glob('*.py'))},cases=[])
    for mode in ('immediate','competing'):
        for name,initial,steps in scenarios():
            memory=memory_class('toy-'+name,initial) if source else RawMemory(initial)
            directory=output/mode/name
            retained=[]
            for index,(act,outcome) in enumerate(steps):
                def dispatch(issued, result=outcome, ordinal=index):
                    require(issued==act, 'fixed policy action changed')
                    require((directory/f'step-{ordinal:04d}.prediction.json').is_file(),
                            'dispatch preceded prediction seal')
                    return result
                execute_step(memory,act,dispatch,directory,producer_commit=commit,mode=mode)
                stem=f'step-{index:04d}'
                retained.append({key:read_checked(directory/f'{stem}.{key}.json')
                                 for key in ('before','prediction','after','result')})
            scores=[replay_payloads(r['before'],r['prediction'],r['after'],r['result'],i,commit)
                    for i,r in enumerate(retained)]
            bundle['cases'].append(dict(name=name,mode=mode,steps=retained,scores=scores,
                handoff=HypothesisManager(M1View(memory.snapshot(),commit)).export()))
    verify_bundle(bundle)
    (output/'trace.json').write_text(json.dumps(bundle,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    aggregate={}
    for mode in ('immediate','competing'):
        scores=[s for case in bundle['cases'] if case['mode']==mode for s in case['scores']]
        aggregate[mode]=dict(attempts=len(scores),scored=sum(s['scored'] for s in scores),
            singleton_forecasts=sum(s['covered'] for s in scores),correct_singleton_forecasts=sum(s['correct'] for s in scores),
            incorrect_singleton_forecasts=sum(s['covered'] and not s['correct'] for s in scores),
            disagreements=sum(s['prediction_status']=='candidate_disagreement' for s in scores))
    summary=dict(version=bundle['version'],m1_producer_commit=commit,memory_kind=bundle['memory_kind'],
        matched_fixed_actions=True,conditions=aggregate,model_calls=0,gpu_jobs=0,real_game_actions=0,
        trace_sha256=hashlib.sha256((output/'trace.json').read_bytes()).hexdigest(),
        interpretation='Constructed diagnostics only; no gameplay, causal identification, held-out evaluation, or statistical advantage claim.')
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output')
    parser.add_argument('--mac-source')
    parser.add_argument('--mac-commit',default='f4bf522e96b1642bed8772c29f153bfe44f98bd5')
    parser.add_argument('--verify',help='Replay a retained trace.json without dispatching any action')
    args=parser.parse_args()
    if args.verify:
        value=json.loads(Path(args.verify).read_text(encoding='utf-8'))
        print(json.dumps(dict(verified_steps=len(verify_bundle(value)))))
    else:
        parser.error('--output required') if not args.output else run(args.output,args.mac_source,args.mac_commit)


if __name__=='__main__': main()
