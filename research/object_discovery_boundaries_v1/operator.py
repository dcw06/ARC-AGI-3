"""External operator for an already approved immutable package. No implicit launch."""
import base64
import copy
import json
import math
from pathlib import Path

from . import deployment as D
from . import operations as G
from research.object_identification_v1.mount_check import canonical
from .supervisor import SCOPE


class Operator:
    def __init__(self, package, approval, authorization, review_pin, source_root, operator_lock):
        self.package, self.approval = Path(package).resolve(), Path(approval).resolve()
        self.authorization = Path(authorization).resolve()
        self.pin, self.source = review_pin, Path(source_root).resolve()
        self.operator_lock = Path(operator_lock).resolve()
        self.records = G.Records(self.package.parent)
        self.authority = self.execution_sha = self.preflight_path = None
        self.http_events = []
        self.save_forwarded = False

    def verify_local(self, *, unspent=True):
        G.require(D.verify_review(self.package) == self.pin, 'approved review hash differs')
        lock = G.load(self.package/'review-lock.json')
        for name, pin in lock['source_sha256'].items():
            G.require(D.digest((self.source/name).read_bytes()) == pin, 'reviewed source drift: '+name)
        G.require(D.digest((self.source/'scripts/build_object_boundary_live.py').read_bytes()) == lock['builder_sha256'], 'builder drift')
        operator_lock = G.load(self.operator_lock)
        G.require(operator_lock['review_lock_sha256'] == self.pin, 'operator lock names another package')
        for name, pin in operator_lock['operator_source_sha256'].items():
            G.require(D.digest((self.source/name).read_bytes()) == pin, 'operator source drift: '+name)
        for name, pin in G.load(self.approval/'record-manifest.json').items():
            G.require(D.digest((self.approval/name).read_bytes()) == pin, 'approval receipt differs')
        self.metadata = G.load(self.package/'kernel-metadata.json')
        self.protocol = G.load(self.package/'runtime/protocol.json')
        self.reservation = G.load(self.approval/'reservation.json')
        G.require(self.reservation['review_lock_sha256'] == self.pin and self.reservation['scope'] == SCOPE, 'reservation scope differs')
        auth = G.load(self.authorization)
        G.require(auth.get('approved') is True and auth.get('review_lock_sha256') == self.pin
                  and canonical(auth.get('scope')) == canonical(SCOPE) and auth.get('owner_answer'), 'launch authorization missing/mismatched')
        if unspent:
            self.records.ensure_unspent(self.reservation)
        return operator_lock

    def preflight(self, backend):
        self.verify_local()
        revision = self.records.revision('preflights')
        result = {'schema': 'molmopoint_preflight_v1', 'review_lock_sha256': self.pin,
                  'reservation_id': self.reservation['reservation_id'], 'target': self.metadata['id'],
                  'status': 'checking', 'checks': {}, 'provider_writes': 0,
                  'operator_lock_sha256': D.digest(self.operator_lock.read_bytes())}
        try:
            owner = self.metadata['id'].split('/')[0]
            G.require(backend.account() == owner, 'authenticated account differs')
            result['checks']['account'] = True
            quota = backend.quota()
            available = quota['total_time_allowed']-quota['time_used']-quota['time_reserved']
            G.require(math.isfinite(available) and available >= 3600, 'GPU quota insufficient')
            result.update(quota=quota, unreserved_gpu_seconds=available)
            result['checks']['quota'] = True
            refs = backend.own_kernels(owner)
            known = G.load(self.package/'review-evidence/known-owner-notebook.json')['target']
            G.require(known in refs and self.metadata['id'] not in refs, 'owner catalogue/target absence not established')
            result['checks']['target_absent'] = True
            inventories = []
            for item in self.protocol['datasets']:
                facts, files = backend.dataset(item)
                G.put(revision/(item['kind']+'-provider.json'), {'facts': facts, 'files': files})
                G.require(facts['ref'] == item['ref'] and facts['version'] == item['version'], 'dataset identity/version differs')
                if item['kind'] != 'wheelhouse':
                    G.require(facts['private'] is True and facts['ready'] is True and facts['collaborators'] == 0, 'private dataset access/readiness differs')
                checked = G.inventory_check(item, files)
                inventories.append({'kind': item['kind'], **checked})
                result['inventories'] = inventories
                G.require(checked['passed'], 'dataset inventory differs; retained provider listing identifies differences')
            G.require(sum(len(item['files']) for item in self.protocol['datasets']) == 220, '220 inventory entries required')
            result['checks'].update(dataset_identity_versions=True, private_access=True, inventories=True)
            self.verify_local()
            result['status'] = 'passed'
        except BaseException as error:
            result.update(status='failed_stop_no_retry', error_type=type(error).__name__)
            if isinstance(error, ValueError):
                result['reason'] = str(error)
        finally:
            result['checked_at_utc'] = G.stamp()
            result['http_events'] = list(self.http_events)
            G.put(revision/'preflight.json', result)
        return revision/'preflight.json'

    def prepare(self, preflight_path, serializer):
        """Validate and serialize everything before spending the reservation."""
        self.verify_local()
        self.preflight_path = Path(preflight_path).resolve()
        G.require(self.preflight_path.is_relative_to(self.records.root/'gpu-operations-v2/preflights'), 'preflight outside revision store')
        raw = self.preflight_path.read_bytes()
        preflight = G.validate_preflight(raw, self.pin, self.reservation['reservation_id'], self.metadata['id'])
        G.require(preflight['operator_lock_sha256'] == D.digest(self.operator_lock.read_bytes()), 'operator differs from preflight')
        authority = G.load(self.approval/'prepared_approval_records_not_launch_authority.json')
        proofs = {pin: (self.approval/name).read_bytes() for pin, name in authority['retained_evidence'].items()}
        def retain(data):
            pin = D.digest(data)
            proofs[pin] = data
            authority['retained_evidence'][pin] = 'authority/'+pin+'.json'
            return pin
        compute = copy.deepcopy(authority['compute_authorization'])
        compute.update(owner_answer=G.load(self.authorization)['owner_answer'], recorded_at_utc=G.stamp(),
                       prior_compute_approval_sha256=retain(canonical(compute)),
                       owner_launch_authorization_sha256=retain(self.authorization.read_bytes()))
        authority['compute_authorization'] = compute
        claim = {'schema': 'molmopoint_single_use_launch_claim_v1', 'review_lock_sha256': self.pin,
                 'attempt_id': self.reservation['reservation_id'], 'consumed': True, 'claimed_at_utc': G.stamp(),
                 'authorization_sha256': retain(canonical(compute)), 'reservation_sha256': retain((self.approval/'reservation.json').read_bytes()),
                 'preflight_sha256': retain(raw), 'operator_lock_sha256': retain(self.operator_lock.read_bytes()),
                 'automatic_retries': 0, 'maximum_save_calls': 1}
        authority['launch_claim'] = claim
        authority['evidence_blobs'] = {pin: base64.b64encode(data).decode() for pin, data in proofs.items()}
        D.verify_authority(self.package, authority)
        # This is a proposed in-memory envelope until Records.consume succeeds. Never write it in a dry check.
        book = D.seal(self.package, authority)
        request, body = serializer(self.package, book)
        G.validate_request(body, self.package, authority)
        self.authority = authority
        self.execution_sha = D.digest(canonical(book))
        return book, request, body

    def before_send(self, body, raw_body):
        self.verify_local(unspent=False)
        G.require(not self.save_forwarded and self.authority is not None, 'one prepared submission only')
        G.require(D.digest(self.operator_lock.read_bytes()) == self.authority['launch_claim']['operator_lock_sha256'], 'operator lock changed')
        G.validate_boundary(self.package, self.authority, self.preflight_path.read_bytes(), self.records, body=body)
        text = body.get('text')
        G.require(D.digest(canonical(json.loads(text))) == self.execution_sha, 'serialized notebook differs')
        self.records.consume_send(self.authority['launch_claim'], {
            'review_lock_sha256': self.pin, 'execution_notebook_sha256': self.execution_sha,
            'request_body_sha256': D.digest(raw_body), 'forwarding_at_utc': G.stamp(), 'maximum_save_calls': 1})
        self.save_forwarded = True

    def launch(self, backend, preflight_path, serializer):
        execution = self.records.revision('executions')
        result = {'review_lock_sha256': self.pin, 'status': 'preparing', 'provider_saved_package_verified': False}
        try:
            book, request, _ = self.prepare(preflight_path, serializer)
            G.require(backend.account() == self.metadata['id'].split('/')[0], 'authenticated account differs')
            self.records.consume(self.reservation, self.authority['launch_claim'])
            G.put(execution/'launch-claim.json', self.authority['launch_claim'])
            G.put(execution/'profile.ipynb', book)
            G.put(execution/'execution-lock.json', {'review_lock_sha256': self.pin,
                  'execution_notebook_sha256': self.execution_sha, 'authority_sha256': D.digest(canonical(self.authority)),
                  'metadata_sha256': D.digest((self.package/'kernel-metadata.json').read_bytes())})
            response = backend.save(request)  # Transport MUST call before_send before forwarding.
            G.require(self.save_forwarded, 'save did not traverse the validated transport')
            G.put(execution/'provider-save-response.json', response)
            G.require(not response['error'] and not any(response['invalid_sources'].values()), 'provider rejected save/sources; no retry')
            G.require(response['ref'].strip('/').removeprefix('code/') == self.metadata['id'] and response['version'] == 1, 'unexpected saved identity/version')
            snapshot = backend.saved(self.metadata['id'])
            G.put(execution/'provider-saved-snapshot.json', snapshot)
            verification = G.validate_saved(snapshot, book, self.package, self.authority, response['version'])
            G.put(execution/'provider-saved-verification.json', verification)
            result.update(status='submitted_once_saved_package_verified', provider_saved_package_verified=True,
                          version=response['version'], ref=response['ref'], url=response['url'], **verification)
        except BaseException as error:
            result.update(status='stopped_preserve_records_no_retry', error_type=type(error).__name__)
            if isinstance(error, ValueError):
                result['reason'] = str(error)
        finally:
            result.update(recorded_at_utc=G.stamp(), save_calls_forwarded=int(self.save_forwarded),
                          http_events=list(self.http_events))
            G.put(execution/'submission-receipt.json', result)
        return execution/'submission-receipt.json'
