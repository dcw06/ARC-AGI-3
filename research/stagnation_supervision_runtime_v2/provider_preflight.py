"""Runtime v2 provider read-receipt validation (hand-written; pure functions; no network, credentials or provider calls).

Successor of scripts/stagnation_provider_preflight_v1.py, whose fixed plan names the superseded inputs (unversioned
wheel dataset, Kaggle Model). The runtime v2 plan reads, for each required source, its identity and a version-bound
first file page:
  wheel dataset  driessmit1/arc3-vllm-h100-wheelhouse-v3 version 1 (listed names must belong to the trusted
                 174-wheel inventory plus the three bound publisher metadata files);
  model dataset  the private version-pinned snapshot (listed names must belong to its 20-file inventory);
  competition    arc-prize-2026-arc-agi-3.
An operator collects the raw responses with a separately reviewed read-only adapter immediately before submission;
`validate` recomputes every normalized claim from the raw bytes (five-minute freshness, exact request identity,
HTTP 200, untruncated, identity match, nonempty file page) and checks the launch metadata's exact source inventory.
Read access is not mount, byte, installation or attachment-acceptance evidence; the submission response validator
and the in-notebook byte checks remain mandatory. With the placeholders unresolved, `plan` refuses.
"""
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

MAX_BYTES = 262144
FRESH_SECONDS = 300
PROTOCOL = 'research/stagnation_supervision_runtime_v2/protocol.json'


def _dataset_plan(ref, version):
    owner, slug = ref.split('/')
    return [('datasets.DatasetApiService/GetDataset', {'ownerSlug': owner, 'datasetSlug': slug}),
            ('datasets.DatasetApiService/ListDatasetFiles', {'ownerSlug': owner, 'datasetSlug': slug,
                                                             'datasetVersionNumber': version, 'pageSize': 20})]


def plan(protocol):
    """{(kind, reference): [(endpoint, request), ...]} for the exact runtime v2 sources."""
    dataset, model, competition = protocol['dataset'], protocol['model'], protocol['competition']['ref']
    source = model['kaggle_source']
    if source.startswith(protocol['placeholder_prefix']) or not re.fullmatch(
            r'[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/[1-9][0-9]*', source):
        raise PermissionError('private model dataset binding unresolved')
    model_ref, model_version = source.rsplit('/', 1)
    return {('dataset_sources', f"{dataset['ref']}/{dataset['version']}"): _dataset_plan(dataset['ref'], dataset['version']),
            ('dataset_sources', source): _dataset_plan(model_ref, int(model_version)),
            ('competition_sources', competition): [
                ('competitions.CompetitionApiService/GetCompetition', {'competitionName': competition}),
                ('competitions.CompetitionApiService/ListDataFiles', {'competitionName': competition, 'pageSize': 20})]}


def allowed_names(protocol, root, reference):
    if reference.startswith(protocol['dataset']['ref'] + '/'):
        manifest = json.loads((Path(root) / 'research/stagnation_supervision_runtime_v2/trusted_manifest.json').read_bytes())
        return {r['filename'] for r in manifest['artifacts']} | set(protocol['dataset']['publisher_metadata_sha256'])
    if reference == protocol['model']['kaggle_source']:
        return {r['path'] for r in protocol['model']['files']}
    return None  # competition pages are checked for identity and non-emptiness only


def normalize(record, protocol, root, now=None):
    now = now or datetime.now(timezone.utc)
    key = (record['kind'], record['reference'])
    expected = plan(protocol)
    if key not in expected or len(record['calls']) != len(expected[key]):
        raise ValueError('unexpected source or RPC inventory')
    decoded, stamps = [], []
    for call, (endpoint, request) in zip(record['calls'], expected[key]):
        if call['endpoint'] != endpoint or call['request'] != request:
            raise ValueError('RPC identity')
        body = base64.b64decode(call['response_base64'], validate=True)
        if call['truncated'] is not False or len(body) > MAX_BYTES or hashlib.sha256(body).hexdigest() != call['response_sha256']:
            raise ValueError('raw receipt integrity')
        stamp = datetime.fromisoformat(call['observed_at_utc'])
        if stamp.tzinfo is None or not 0 <= (now - stamp).total_seconds() <= FRESH_SECONDS:
            raise ValueError('stale or future provider observation')
        stamps.append(stamp)
        if type(call['http_status']) is not int or call['http_status'] != 200:
            raise PermissionError('source inaccessible: ' + key[1])
        value = json.loads(body)
        if not isinstance(value, dict) or value.get('error'):
            raise ValueError('provider error')
        decoded.append(value)
    identity, listing = decoded
    if key[0] == 'competition_sources':
        if identity.get('ref') not in (key[1], 'https://www.kaggle.com/competitions/' + key[1]):
            raise ValueError('competition identity')
    elif identity.get('ref') != key[1].rsplit('/', 1)[0]:
        raise ValueError('dataset returned another identity')
    files = listing.get('files') or listing.get('datasetFiles')
    if not isinstance(files, list) or not files or any(not isinstance(f, dict) or not f.get('name') for f in files):
        raise ValueError('readable nonempty file page required')
    allowed = allowed_names(protocol, root, key[1])
    if allowed is not None and any(Path(f['name']).name not in allowed for f in files):
        raise ValueError('listed file outside the bound inventory: ' + key[1])
    raw = json.dumps(record, sort_keys=True, separators=(',', ':')).encode()
    return {'kind': key[0], 'reference': key[1], 'http_status': 200, 'accessible': True,
            'observed_at_utc': min(stamps).isoformat(), 'record_sha256': hashlib.sha256(raw).hexdigest(),
            'limitation': 'identity and first-page read access only; not mount, bytes, installation or acceptance'}


def validate(folder, records, protocol, root, now=None):
    """Exact source inventory in the launch metadata plus one fresh, recomputed receipt per source."""
    metadata = json.loads((Path(folder) / 'kernel-metadata.json').read_bytes())
    expected = plan(protocol)
    wanted = {'dataset_sources': sorted(r for k, r in expected if k == 'dataset_sources'),
              'competition_sources': sorted(r for k, r in expected if k == 'competition_sources'), 'model_sources': []}
    for kind, refs in wanted.items():
        if sorted(metadata.get(kind) or []) != refs:
            raise ValueError('launch attachment inventory differs: ' + kind)
    rows = [normalize(r, protocol, root, now) for r in records]
    keys = [(r['kind'], r['reference']) for r in rows]
    if len(set(keys)) != len(keys) or set(keys) != set(expected):
        raise PermissionError('missing, duplicate or unexpected provider receipts')
    return rows
