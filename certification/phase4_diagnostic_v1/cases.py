"""Immutable request inventory; no games or inference on import."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PROPOSAL_SHA256='d8de6535ff6d54c155e151ca48660b7e84b01029f3ebc51208a0b4f09c6e4655'

def request_hash(request):
    return hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest()

def load_cases():
    data=(ROOT/'reports/phase4_action_selection_probe_proposal.json').read_bytes()
    if hashlib.sha256(data).hexdigest()!=PROPOSAL_SHA256:raise ValueError('diagnostic proposal drift')
    cases=json.loads(data)['cases']
    if len(cases)!=45 or len({(c['game_id'],c['arm']) for c in cases})!=45:
        raise ValueError('diagnostic inventory')
    for case in cases:
        if request_hash(case['request'])!=case['request_sha256']:raise ValueError('request drift')
    return cases
