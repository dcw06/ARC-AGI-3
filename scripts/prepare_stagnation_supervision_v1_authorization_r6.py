"""Prepare R6 authorization candidate from immutable R4; never approve, reserve or upload."""
import base64
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / 'notebooks/stagnation-supervision-v1-review-r4'
OUT = ROOT / 'notebooks/stagnation-supervision-v1-authorization-r6'
AUTH = 'research/stagnation_supervision_v1/closed_loop/authority.py'
REVIEW = 'notebooks/stagnation-supervision-v1-authorization-r6/source-review.json'
MARKER = '    # SSV_AUTHORITY_SIDECARS: only a separately reviewed launch revision may insert authority.\n'


def raw(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def authority(root):
    spec = importlib.util.spec_from_file_location('ssv_r6_authority', Path(root) / AUTH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def candidate():
    from scripts.review_action_effect_history_v1_notebook import verify_bindings
    from scripts.build_stagnation_supervision_v1_review_r4 import cell
    parent, _, encoded = verify_bindings(PARENT)
    payload = {n: base64.b64decode(v) for n, v in encoded.items()}
    payload[AUTH] = (ROOT / 'scripts/stagnation_supervision_v1_authority_r6_template.py').read_bytes()
    bindings = {n: sha(v) for n, v in payload.items()}
    from research.stagnation_supervision_v1.closed_loop.authority import SESSION_LIMITS
    source = {'status': 'reviewed_launch_source', 'scope': 'stagnation-supervision-v1',
              'revision': 'r6', 'parent_review_sha256': sha((PARENT / 'review-source-lock.json').read_bytes()),
              'bindings': bindings, 'session_limits': SESSION_LIMITS,
              'authorized_seconds': 0, 'gpu_launch_authorized': False,
              'change_scope': 'reservation-only cannot execute; explicit successor source and launch approval required; all other R4 runtime bytes identical'}
    packed = base64.b85encode(lzma.compress(json.dumps({n: base64.b64encode(v).decode()
                            for n, v in payload.items()}, sort_keys=True).encode(), preset=6)).decode()
    code = cell(bindings, packed)
    packed_review = base64.b85encode(lzma.compress(raw(source))).decode()
    code = code.replace(f'    bindings={bindings!r}\n',
                        f'    review_bytes=lzma.decompress(base64.b85decode({packed_review!r}))\n'
                        '    bindings=json.loads(review_bytes)["bindings"]\n')
    insertion = (f'    review_path=source/{REVIEW!r}\n'
                 '    review_path.parent.mkdir(parents=True,exist_ok=True)\n'
                 '    review_path.write_bytes(review_bytes)\n' + MARKER)
    if code.count(MARKER) != 1:
        raise ValueError('sidecar insertion point')
    code = code.replace(MARKER, insertion)
    notebook = json.loads((PARENT / 'profile.ipynb').read_bytes())
    notebook['cells'][0]['source'] = ('# Track 3 R6 authorization review candidate\n'
        'Private, GPU disabled, unscored. No approval or reservation embedded. Exactly one session per future '
        'authorized package, no automatic retries or second-session launch. Based on R4; only authority module changes. '
        'Real GPU timing is unmeasured; ls20 is exploratory, and the false-interruption gate remains uncertifiable.')
    notebook['cells'][1]['source'] = code
    metadata = json.loads((PARENT / 'kernel-metadata.json').read_bytes())
    metadata.update(id='daichongwei06/arc3-stagnation-supervision-v1-authorization-r6',
                    title='ARC3 Stagnation Supervision V1 Authorization R6')
    return payload, source, notebook, metadata


def build():
    if OUT.exists():
        raise FileExistsError('immutable candidate already exists')
    payload, source, notebook, metadata = candidate()
    files = {'source-review.json': raw(source), 'profile.ipynb': raw(notebook),
             'kernel-metadata.json': raw(metadata)}
    if len(files['profile.ipynb']) >= 900000:
        raise ValueError('notebook upload size')
    docs = ['scripts/prepare_stagnation_supervision_v1_authorization_r6.py',
            'scripts/review_stagnation_supervision_v1_authorization_r6.py',
            'tests/test_ssv_authorization_r6.py',
            'reports/stagnation_supervision_v1_authorization_review_r6.md',
            'scripts/stagnation_supervision_v1_authority_r6_template.py',
            'scripts/submit_stagnation_supervision_v1_r6_once.py']
    lock = {'scope': source['scope'], 'revision': 'r6', 'status': 'authorization_candidate_pending_user_approval',
            'source_review_sha256': sha(files['source-review.json']),
            'parent_review_sha256': source['parent_review_sha256'],
            'artifacts': {n: sha(v) for n, v in files.items()},
            'review_documents': {n: sha((ROOT / n).read_bytes()) for n in docs},
            'gpu_launch_authorized': False, 'authorized_seconds': 0}
    OUT.mkdir()
    for name, data in files.items():
        (OUT / name).write_bytes(data)
    (OUT / 'review-source-lock.json').write_bytes(raw(lock))
    return lock


def assemble_approved(folder, sidecars, session, destination):
    """Future local packaging only: validates real records; never creates authority or uploads."""
    from scripts.review_stagnation_supervision_v1_authorization_r6 import verify, extract
    import tempfile
    folder, destination = Path(folder), Path(destination)
    lock, notebook, payload, source = verify(folder)
    if session != '1' or destination.exists():
        raise ValueError('new destination and explicit session required')
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        extract(root, payload, source)
        gate = authority(root)
        expected = {gate.SOURCE, gate.COMPUTE, gate.EXECUTION, gate.RESERVATION, gate.SUCCESSOR_SOURCE, gate.LAUNCH}
        if set(sidecars) != expected:
            raise ValueError('exact authority sidecars required')
        for name, value in sidecars.items():
            path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(value)
        execution = gate.require(root)
        if execution['session'] != session:
            raise PermissionError('requested session differs from approved session')
    code = notebook['cells'][1]['source']
    insertion = ''.join(f'    p=source/{name!r};p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes({value!r})\n'
                        for name, value in sorted(sidecars.items()))
    code = code.replace(MARKER, insertion).replace("SESSION='1'\n", f'SESSION={session!r}\n')
    notebook['cells'][1]['source'] = code
    metadata = json.loads((folder / 'kernel-metadata.json').read_bytes())
    metadata['enable_gpu'] = True
    destination.mkdir()
    for name, value in [('profile.ipynb', notebook), ('kernel-metadata.json', metadata)]:
        (destination / name).write_bytes(raw(value))
    (destination / 'package-binding.json').write_bytes(raw({
        'source_review_sha256': lock['source_review_sha256'], 'session': session,
        'attempt_id': execution['attempt_id'], 'sidecars': {n: sha(v) for n, v in sidecars.items()},
        'artifacts': {n: sha((destination / n).read_bytes()) for n in ('profile.ipynb', 'kernel-metadata.json')},
        'submitted': False}))


if __name__ == '__main__':
    print(json.dumps(build(), indent=2))
