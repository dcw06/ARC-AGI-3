"""Pin unchanged restoration/scoring/preparation machinery; insert explicit phase."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def derive():
    pins = json.loads(Path(__file__).with_suffix('.parents.json').read_bytes())
    files = {}
    for name, pin in pins.items():
        raw = (ROOT/name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != pin: raise ValueError('v1 derivation parent changed: '+name)
        value = raw.decode()
        if name.endswith('/flow.py'):
            old = 'body = make_request(base, pair, variant, previous)'
            if value.count(old) != 1: raise ValueError('flow template differs')
            value = value.replace(old, 'body = make_request(base, pair, variant, previous,\n'
                "                                study_decision_index=decision, restored_prefix_length=len(checkpoint['prefix']))")
        elif name.endswith('/preparation.py'):
            value = value.replace('action_effect_choice_CPU_inputs_v1', 'action_effect_choice_CPU_inputs_v2')
            old = "make_request(cp['base_request'], row['candidates'], variant)"
            if value.count(old) != 2: raise ValueError('preparation template differs')
            value = value.replace(old, "make_request(cp['base_request'], row['candidates'], variant,\n"
                "                study_decision_index=0, restored_prefix_length=len(cp['prefix']))")
        else:
            if name != 'scripts/rehearse_action_effect_choice_v1.py': raise ValueError('unknown derivation parent')
            value = value.replace('research.action_effect_choice_v1', 'research.action_effect_choice_v2')
            old = 'body=make_request(base,pair,variant,prior)'
            if value.count(old) != 1: raise ValueError('rehearsal template differs')
            value = value.replace(old, "record['predicted_visible_change']=('unknown'if forecast=='unknown'else'no'if forecast=='none'else'yes')\n"
                "                    base=request_for(cp['initial'],cp['initial_case']['geometry']['reviewed'],branch['after'],\n"
                "                        cp['prefix']+[record],len(cp['prefix'])+1,cp['base_request']['model'])\n"
                "                    body=make_request(base,pair,variant,prior,study_decision_index=1,restored_prefix_length=len(cp['prefix']))")
        files[name.replace('action_effect_choice_v1', 'action_effect_choice_v2')] = value
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    files = derive()
    for name, value in files.items():
        path = ROOT/name
        if args.check:
            if path.read_bytes() != value.encode(): raise ValueError('derived file differs: '+name)
        else: path.write_bytes(value.encode())
    print(json.dumps({'derived_files': len(files), 'matched': True, 'GPU_jobs': 0}))


if __name__ == '__main__': main()
