"""Fail-closed preparation helpers. No approval creation, reservation or provider mutation."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = {
 'dataset_sources':['driessmit1/arc3-vllm-h100-wheelhouse-v3'],
 'model_sources':['qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1'],
 'competition_sources':['arc-prize-2026-arc-agi-3'],
}
REJECTED = ('invalidDatasetSources','invalidModelSources','invalidCompetitionSources','invalidKernelSources',
            'invalid_dataset_sources','invalid_model_sources','invalid_competition_sources','invalid_kernel_sources')


def validate_response(value):
    if not isinstance(value,dict):raise ValueError('provider response is not an object')
    for key in REJECTED:
        field=value.get(key)
        if field is not None and (not isinstance(field,list) or field):
            raise ValueError('provider rejected attachment: '+key)
    if value.get('error') or not value.get('url'):
        raise ValueError('provider result requires reconciliation')
    return value


def validate_preflight(folder, observations, *, now=None):
    """Require exact declared sources and fresh, identity-bound successful read receipts.

    Upstream read-only source adapters must record these normalized receipts with
    raw response hashes. Read access does not prove runtime installation or that
    SaveKernel will accept attachments; response validation remains mandatory.
    """
    metadata=json.loads((Path(folder)/'kernel-metadata.json').read_bytes())
    for kind, expected in REQUIRED.items():
        if metadata.get(kind)!=expected:raise ValueError('required attachment inventory: '+kind)
    expected={(kind,ref) for kind,refs in REQUIRED.items() for ref in refs}
    seen=set();now=now or datetime.now(timezone.utc)
    for row in observations:
        key=(row['kind'],row['reference'])
        if key in seen or key not in expected:raise ValueError('duplicate/unexpected source receipt')
        seen.add(key)
        body=bytes.fromhex(row['response_hex'])
        if hashlib.sha256(body).hexdigest()!=row['response_sha256']:raise ValueError('source response integrity')
        stamp=datetime.fromisoformat(row['observed_at_utc'])
        if stamp.tzinfo is None or not 0 <= (now-stamp).total_seconds() <= 300:
            raise ValueError('source receipt stale or future')
        if row['http_status']!=200 or row['accessible'] is not True or row['resolved_reference']!=key[1]:
            raise PermissionError('required source unavailable: '+key[1])
        if not body or not isinstance(json.loads(body),dict):raise ValueError('source response malformed')
    if seen!=expected:raise PermissionError('missing required attachment preflight')


def consume_explicit_approvals(source_path,launch_path,*,source_hash,reservation_hash):
    """Read only. Never promote a recommendation into approval or write authority."""
    source_raw=Path(source_path).read_bytes();source=json.loads(source_raw)
    launch=json.loads(Path(launch_path).read_bytes())
    for record,kind in ((source,'source'),(launch,'launch')):
        if (record.get('approval_kind')!=kind or record.get('status')!='approved'
            or record.get('review_lock_sha256')!=source_hash
            or record.get('explicit_confirmation') is not True):
            raise PermissionError('explicit '+kind+' approval missing')
        provenance=record.get('provenance',{})
        if (provenance.get('type')!='user_confirmation' or not provenance.get('message_reference')
                or not provenance.get('verbatim_text') or provenance.get('interpretation_only') is not False):
            raise PermissionError('actual user confirmation reference required')
    if (source['provenance']['message_reference']==launch['provenance']['message_reference']):
        # One user message may answer both questions, but they need distinct answer references.
        if source['provenance'].get('answer_reference')==launch['provenance'].get('answer_reference'):
            raise PermissionError('separate source and launch decisions required')
    if (launch.get('source_approval_sha256')!=hashlib.sha256(source_raw).hexdigest()
            or launch.get('reservation_sha256')!=reservation_hash
            or launch.get('submission_authorized') is not True
            or launch.get('authorization_scope')!='submit_and_execute_one_attempt'):
        raise PermissionError('launch approval binding')
    return source,launch
