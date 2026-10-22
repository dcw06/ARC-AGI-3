"""Pin the completed pilot's lifecycle; derive a new k=4 cross-navigation runner."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def replace(text, before, after):
    if text.count(before) != 1: raise ValueError('parent template differs: '+before)
    return text.replace(before, after)


def derive():
    pins = json.loads(Path(__file__).with_suffix('.parents.json').read_bytes()); result = {}
    for name, pin in pins.items():
        raw = (ROOT/name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != pin: raise ValueError('parent changed: '+name)
        text = raw.decode().replace('ls20_instruction', 'ls20_knn_path').replace('ls20-instruction', 'ls20-knn-path')
        text = text.replace('LS20_INSTRUCTION', 'LS20_KNN_PATH').replace('ls20/instructed/', 'ls20/knn_path/').replace('ls20-instructed', 'ls20-knn-path')
        leaf = Path(name).name
        if leaf == 'live_contract.py':
            text = replace(text, 'ACTION_CAP=40', 'ACTION_CAP=24')
        elif leaf == 'live_worker.py':
            text = replace(text, 'request_plan(),41,clock', 'request_plan(),27,clock')
            text = replace(text, 'range(ACTION_CAP)', 'range(ACTION_CAP+2)')
        elif leaf == 'audit.py':
            text = replace(text, "ledger['maximum_model_requests']!=41", "ledger['maximum_model_requests']!=27")
            text = replace(text, "    return dict(study_schedule_complete=", "    return dict(cross_reached=result['cross_reached'],path_assessment=result['path_assessment'],assessment_generations=len(result['assessment_history']),study_schedule_complete=")
            text = replace(text, 'policy_generations=len(replies)', "policy_generations=max(0,len(replies)-len(result['assessment_history']))")
        elif leaf == 'live_runtime.py':
            for before, after in (("'generations': 41", "'generations': 27"), ("'counted_HTTP_requests': 41", "'counted_HTTP_requests': 27"),
                                  ("'policy_actions': 40", "'policy_actions': 24"), ("'offline_engine_actions': 41", "'offline_engine_actions': 25")):
                text = replace(text, before, after)
        elif leaf == 'live_package.py':
            text = text.replace('at most forty-one generations', 'at most twenty-seven generations')
            text = text.replace('level-1 instruction-following pilot', 'k=4 floor-color and cross-navigation probe')
        text = text.replace('One exposed ls20 level-1 episode with supplied controls and rules. VLM plans the actions. No rule-discovery or generalization claim.',
            'One assisted k=4 floor-color and cross-navigation probe. No discovery, level-solving or comparative improvement claim.')
        text = text.replace('One exposed instructed level-1 pilot; no discovery, generalization or comparison claim.',
            'One assisted cross-navigation probe; no discovery, level-solving or comparison claim.')
        result['research/ls20_knn_path_v1/'+leaf] = text.encode()
    return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--check', action='store_true'); args = parser.parse_args()
    result = derive()
    for name, raw in result.items():
        path = ROOT/name
        if args.check:
            if path.read_bytes() != raw: raise ValueError('derived source changed: '+name)
        else: path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    print(json.dumps(dict(matched=True, derived_files=len(result), GPU_jobs=0)))

if __name__ == '__main__': main()
