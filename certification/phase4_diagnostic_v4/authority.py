"""Separate source approval and single-attempt compute authority; no auto-approval."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def require(root=None):
    root=ROOT if root is None else Path(root)
    folder=root/'certification/phase4_diagnostic_v4'
    try:
        execution=json.loads((folder/'execution_lock.json').read_text())
        ledger=json.loads((folder/'compute_ledger.json').read_text())
        review_path=root/execution['review_lock']
        if not review_path.resolve().is_relative_to(root.resolve()): raise ValueError('review path')
        digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
        if digest(review_path)!=execution['review_sha256']: raise ValueError('review drift')
        review=json.loads(review_path.read_text())
        required={p.relative_to(root).as_posix() for p in folder.glob('*.py')}
        required.add('certification/phase4_diagnostic_v4/protocol.json')
        required.add('reports/phase4_action_selection_probe_proposal.json')
        if not required<=set(review['bindings']): raise ValueError('incomplete source binding')
        for name,expected in review['bindings'].items():
            path=(root/name).resolve()
            if not path.is_relative_to(root.resolve()) or digest(path)!=expected: raise ValueError('source drift')
        if (not execution.get('source_approval_reference') or not ledger.get('approval_reference')
                or ledger['authorized_seconds']!=3600 or ledger['maximum_attempts']!=1
                or execution['attempt_id']!=ledger['attempt_id']): raise ValueError('separate approval required')
        def reference(name):
            path=(root/name).resolve()
            if not path.is_relative_to(root.resolve()):raise ValueError('approval path')
            return json.loads(path.read_text())
        source=reference(execution['source_approval_reference'])
        compute=reference(ledger['approval_reference'])
        if (source.get('status')!='approved' or source.get('review_lock_sha256')!=digest(review_path)
            or compute.get('scope')!='phase4-action-diagnostic-v4' or compute.get('authorized_seconds')!=3600
            or compute.get('maximum_attempts')!=1 or compute.get('automatic_retries')!=0
            or compute.get('maximum_total_completions')!=46
            or compute.get('source_approval_reference')!=execution['source_approval_reference']):
            raise ValueError('diagnostic approval scope')
        events=ledger['events']
        reserve=[e for e in events if e['kind']=='reserve']
        claims=[e for e in events if e['kind']=='launch_request_started']
        if (len(reserve)!=1 or len(claims)!=1 or reserve[0]['seconds']!=3600
                or reserve[0]['execution_lock_sha256']!=digest(folder/'execution_lock.json')
                or claims[0]['attempt_id']!=execution['attempt_id']
                or any(e['kind'].startswith('attempt_completed') for e in events)):
            raise ValueError('single bound reservation/launch claim required')
        return execution
    except (OSError,KeyError,ValueError,TypeError) as exc:
        raise PermissionError('diagnostic requires approved source lock and separate bound GPU reservation') from exc
