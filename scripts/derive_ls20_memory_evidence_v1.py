"""Derive the instructed pilot's reviewed lifecycle for the evidence-memory pilot; never execute it."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

RENAMES = (('ls20_instruction_', 'ls20_memory_evidence_'), ('ls20-instruction-v1-', 'ls20-memory-evidence-v1-'),
           ('LS20_INSTRUCTION_V1_', 'LS20_MEMORY_EVIDENCE_V1_'), ('ls20/instructed/', 'ls20/memory_evidence/'),
           ('ls20-instructed', 'ls20-memory-evidence'))


def replace(text, before, after):
    if text.count(before) != 1: raise ValueError('parent template differs: '+before)
    return text.replace(before, after)


def derive():
    pins = json.loads(Path(__file__).with_suffix('.parents.json').read_bytes()); result = {}
    for name, pin in pins.items():
        raw = (ROOT/name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != pin: raise ValueError('parent changed: '+name)
        text = raw.decode()
        for before, after in RENAMES:
            text = text.replace(before, after)
        leaf = Path(name).name
        if leaf == 'live_package.py':
            text = replace(text, 'Private ls20 level-1 instruction-following pilot: one episode, at most forty-one generations. Review only.',
                'Private ls20 level-1 evidence-memory pilot: one episode, at most forty-one generations. Review only.')
            text = replace(text, "'tests/test_ls20_memory_evidence_v1.py']",
                "'tests/test_ls20_memory_evidence_v1.py','tests/test_ls20_memory_evidence_policy_v1.py']")
        elif leaf == 'live_evaluation.py':
            text = replace(text, 'One exposed ls20 level-1 episode with supplied controls and rules. VLM plans the actions. No rule-discovery or generalization claim.',
                'One exposed ls20 level-1 episode with supplied controls and rules plus a computed evidence memory. VLM plans the actions. No rule-discovery, generalization or causal claim.')
        elif leaf == 'audit.py':
            text = replace(text, 'One exposed instructed level-1 pilot; no discovery, generalization or comparison claim.',
                'One exposed level-1 pilot with supplied rules and a computed evidence memory; no discovery, generalization or causal comparison claim.')
        if name.startswith('tests/'):
            result['tests/test_ls20_memory_evidence_v1.py'] = text.encode()
        else:
            result['research/ls20_memory_evidence_v1/'+leaf] = text.encode()
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
