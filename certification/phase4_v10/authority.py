"""Separate source approval and single-attempt compute authority; no auto-approval."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def require(root=None):
    root=ROOT if root is None else Path(root)
    folder=root/'certification/phase4_v10'
    try:
        execution=json.loads((folder/'execution_lock.json').read_text())
        ledger=json.loads((folder/'compute_ledger.json').read_text())
        review_path=root/execution['review_lock']
        if not review_path.resolve().is_relative_to(root.resolve()): raise ValueError('review path')
        digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
        if digest(review_path)!=execution['review_sha256']: raise ValueError('review drift')
        review=json.loads(review_path.read_text())
        required={p.relative_to(root).as_posix() for p in folder.glob('*.py')}
        required.add('certification/phase4_v10/protocol.json')
        if not required<=set(review['bindings']): raise ValueError('incomplete source binding')
        for name,expected in review['bindings'].items():
            path=(root/name).resolve()
            if not path.is_relative_to(root.resolve()) or digest(path)!=expected: raise ValueError('source drift')
        if (not execution.get('source_approval_reference') or not ledger.get('approval_reference')
                or ledger['authorized_seconds']!=28800 or ledger['maximum_attempts']!=1
                or execution['attempt_id']!=ledger['attempt_id']): raise ValueError('separate approval required')
        events=ledger['events']
        reserve=[e for e in events if e['kind']=='reserve']
        claims=[e for e in events if e['kind']=='launch_request_started']
        if (len(reserve)!=1 or len(claims)!=1 or reserve[0]['seconds']!=28800
                or reserve[0]['execution_lock_sha256']!=digest(folder/'execution_lock.json')
                or claims[0]['attempt_id']!=execution['attempt_id']
                or any(e['kind'].startswith('attempt_completed') for e in events)):
            raise ValueError('single bound reservation/launch claim required')
        return execution
    except (OSError,KeyError,ValueError,TypeError) as exc:
        raise PermissionError('v10 requires approved source lock and separate bound GPU pilot reservation') from exc
