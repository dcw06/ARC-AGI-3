"""Freeze the WS3 transition questionnaire (draft r2.2) into the runtime format (offline; no model, no GPU).

The runtime (research/ws3_questionnaire_v1/, derived from the reviewed evidence-comprehension v3 stack) reads only
this frozen file: `contexts` as a list of {context_id, partition, condition, evidence}, `probes` (each with its
frozen question, key and metadata, plus `track: questionnaire` for the shared runner), and the frozen `schedule`.
A fresh build must be byte-identical (`--check`). The builder itself (research/transition_evidence_v1/
questionnaire.py) is never imported at runtime.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / 'research/ws3_questionnaire_v1/probes.json'
SUMMARY = ROOT / 'reports/ws3_questionnaire_v1_probe_summary.json'


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def build():
    from research.transition_evidence_v1 import questionnaire as Q
    built = Q.build()
    contexts = []
    for cid in sorted(built['contexts']):
        partition, condition, _ = cid.split(':', 2)
        contexts.append({'context_id': cid, 'partition': partition, 'condition': condition,
                         'evidence': built['contexts'][cid]})
    probes = [{**p, 'track': 'questionnaire'} for p in built['probes']]
    return {'version': Q.VERSION, 'system_prompt': Q.SYSTEM_PROMPT, 'answers': Q.ANSWERS, 'roles': Q.ROLES,
            'over_claim_gates': {g: sorted(map(list, m)) for g, m in Q.OVER_CLAIM_GATES.items()},
            'contexts': contexts, 'probes': probes, 'schedule': built['schedule']}


def summary(value, raw):
    from research.transition_evidence_v1 import questionnaire as Q
    return {'version': value['version'], 'probe_set_sha256': hashlib.sha256(raw).hexdigest(),
            'probes': len(value['probes']), 'contexts': len(value['contexts']),
            'scheduled_calls': sum(len(b['probe_ids']) for b in value['schedule']),
            'calls_by_phase': {f"{b['partition']}/{b['pass']}": len(b['probe_ids']) for b in value['schedule']},
            'coverage': Q.coverage(value['probes'])}


def outputs(value):
    raw = encode(value)
    return {OUTPUT: raw, SUMMARY: (json.dumps(summary(value, raw), sort_keys=True, indent=1) + '\n').encode()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    files = outputs(build())
    if parser.parse_args().check:
        stale = [str(p.relative_to(ROOT)) for p, raw in files.items() if not p.exists() or p.read_bytes() != raw]
        if stale:
            raise SystemExit(f'frozen files differ from a fresh build: {stale}')
        print('question set matches a fresh build:', hashlib.sha256(files[OUTPUT]).hexdigest())
    else:
        OUTPUT.parent.mkdir(exist_ok=True)
        for path, raw in files.items():
            path.write_bytes(raw)
        print(json.dumps({'bytes': len(files[OUTPUT]), 'sha256': hashlib.sha256(files[OUTPUT]).hexdigest()}))
