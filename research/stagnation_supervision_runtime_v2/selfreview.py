"""Self-review under amendment S1 (frozen protocol v2 §7 and §14; hand-written; CPU only; post-run; no model).

The independent blinded human label audit is not performed. This module draws the preregistered, seeded sample for
the researcher's unblinded descriptive self-review and validates the annotations. It reads decision-point lists only
(labels per decision point, delivered reflections, recovered opportunities); it never computes or reads an arm-level
summary. Labels are never changed: annotations are kept apart from the mechanical scores and are descriptive.

Sample (seed `stagnation-v1-selfreview`), from the main episodes of both sessions (the block-1 continuation repeats
are excluded because they duplicate their originals by design):
  label points   20 LC from wa30, 20 ST from ar25 and 20 IND from wa30 and ar25 (the gate-eligible stratum); the
                 same quotas from ls20 as a separate stratum, never pooled with the first;
  reflections    20 delivered reflections from ar25, wa30 and ls20, 10 per reflection arm, the remainder from the
                 other arm when one has fewer;
  recoveries     20 recovered opportunities from ar25, wa30 and ls20, any arm.
s5i5, the declared blind-spot case, is not sampled. A stratum with fewer candidates than its quota is taken whole and
the shortfall is recorded. Candidates are ranked by SHA-256(seed, stratum, key) and the lowest are taken, so the draw
depends only on the seed and the candidate lists, never on their order or on any outcome summary.

Order (protocol §7): the sample is drawn and annotated, and the annotations are committed and hashed, before any
pooled comparison is computed (`pooled.evaluate_sessions` refuses otherwise). The 20% disagreement rule is reported
descriptively only; the false-interruption gate is not certifiable in any case (§8.3).
"""
import hashlib
import json

from research.stagnation_supervision_v1 import outcomes as O

VERSION = 'stagnation_supervision_selfreview_v1'
SEED = 'stagnation-v1-selfreview'
SAMPLED_GAMES = ('ar25', 'wa30', 'ls20')
LABEL_QUOTA = 20
LABEL_STRATA = {  # stratum: (label, games)
    'gate_eligible/LC': ('LC', ('wa30',)),
    'gate_eligible/ST': ('ST', ('ar25',)),
    'gate_eligible/IND': ('IND', ('wa30', 'ar25')),
    'ls20/LC': ('LC', ('ls20',)),
    'ls20/ST': ('ST', ('ls20',)),
    'ls20/IND': ('IND', ('ls20',)),
}
REFLECTION_ARMS = ('periodic', 'triggered')
REFLECTION_QUOTA = 20
RECOVERY_QUOTA = 20
ANSWERS = ('yes', 'no', 'unclear')
FIELDS = {
    'label': ('label_describes_visible_situation',),
    'reflection': ('cites_available_evidence', 'turns_uncertainty_into_fact', 'test_can_distinguish_explanations'),
    'recovery': ('more_than_a_changed_action',),
}
MAX_NOTE = 1000


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _rank(seed, stratum, key):
    return hashlib.sha256(f'{seed}\0{stratum}\0{key}'.encode()).hexdigest()


def candidates(episodes, trigger_spec, horizon):
    """Decision-point lists by stratum. episodes: dicts with 'episode', 'session', 'game', 'arm', 'repeat',
    'records' and 'delivered' (action indices of delivered reflections), as `pooled.session_episodes` builds them."""
    out = {name: [] for name in LABEL_STRATA}
    out.update({f'reflections/{arm}': [] for arm in REFLECTION_ARMS}, recoveries=[])
    for e in episodes:
        if e['repeat'] or e['game'] not in SAMPLED_GAMES:
            continue
        where = {'session': e['session'], 'episode': e['episode'], 'game': e['game'], 'arm': e['arm']}
        for index, label in enumerate(O.labels(e['records'])):
            for name, (wanted, games) in LABEL_STRATA.items():
                if label == wanted and e['game'] in games:
                    out[name].append({'key': f"{e['episode']}#{index}", **where, 'index': index, 'label': label})
        if e['arm'] in REFLECTION_ARMS:
            for index in e['delivered']:
                out[f"reflections/{e['arm']}"].append({'key': f"{e['episode']}#{index}", **where, 'index': index})
        for o in O.opportunities(e['records'], trigger_spec, horizon)['opportunities']:
            if o['status'] == 'recovered':
                out['recoveries'].append({'key': f"{e['episode']}#{o['opened_at']}", **where,
                                          'opened_at': o['opened_at'], 'exit_at': o['exit_at']})
    for rows in out.values():
        keys = [r['key'] for r in rows]
        if len(keys) != len(set(keys)):
            raise ValueError('duplicate decision-point key')
    return out


def draw(lists, seed=SEED, inputs=None):
    """The deterministic sample (see module docstring) and its canonical digest."""
    ordered = {name: sorted(rows, key=lambda r: _rank(seed, name, r['key'])) for name, rows in lists.items()}
    strata = {}
    for name in LABEL_STRATA:
        strata[name] = {'kind': 'label', 'quota': LABEL_QUOTA, 'selected': ordered[name][:LABEL_QUOTA]}
    half = REFLECTION_QUOTA // len(REFLECTION_ARMS)
    taken = {arm: ordered[f'reflections/{arm}'][:half] for arm in REFLECTION_ARMS}
    for arm in REFLECTION_ARMS:  # fill a short arm's remainder from the other arm, in rank order
        other = [a for a in REFLECTION_ARMS if a != arm][0]
        room = half - len(taken[arm])
        if room > 0:
            taken[other] = ordered[f'reflections/{other}'][:half + room]
    for arm in REFLECTION_ARMS:
        strata[f'reflections/{arm}'] = {'kind': 'reflection', 'quota': half, 'selected': taken[arm]}
    strata['recoveries'] = {'kind': 'recovery', 'quota': RECOVERY_QUOTA, 'selected': ordered['recoveries'][:RECOVERY_QUOTA]}
    for name, row in strata.items():
        row['candidates'] = len(lists[name])
    reflections = sum(len(strata[f'reflections/{a}']['selected']) for a in REFLECTION_ARMS)
    shortfall = {name: row['quota'] - len(row['selected']) for name, row in strata.items()
                 if row['kind'] != 'reflection' and len(row['selected']) < row['quota']}
    if reflections < REFLECTION_QUOTA:
        shortfall['reflections'] = REFLECTION_QUOTA - reflections
    sample = {'schema': VERSION, 'amendment': 'S1', 'seed': seed,
              'protocol': 'reports/stagnation_supervision_v1_protocol_v2_frozen.md',
              'quotas': {'label_per_stratum': LABEL_QUOTA, 'reflections': REFLECTION_QUOTA, 'recoveries': RECOVERY_QUOTA},
              'inputs': inputs, 'strata': strata, 'shortfall': shortfall,
              'scope': 'unblinded descriptive self-review by the sole researcher; not an independent audit'}
    return {**sample, 'sample_sha256': digest(sample)}


def template(sample):
    """An empty annotation record for the sample: every answer null, every note empty."""
    return {'schema': VERSION + '_annotations', 'sample_sha256': sample['sample_sha256'],
            'reviewer': 'the sole researcher (designer, implementer, operator and analyst); unblinded',
            'annotations': {name: [{'key': item['key'], **{f: None for f in FIELDS[row['kind']]}, 'note': ''}
                                   for item in row['selected']]
                            for name, row in sample['strata'].items()}}


def validate(sample, annotations):
    """Every sampled item annotated exactly once, in order, with allowed answers. Returns the descriptive summary;
    raises ValueError on any incomplete or mismatched record."""
    body = {k: v for k, v in sample.items() if k != 'sample_sha256'}
    if sample.get('sample_sha256') != digest(body):
        raise ValueError('sample digest')
    if annotations.get('schema') != VERSION + '_annotations' or annotations.get('sample_sha256') != sample['sample_sha256']:
        raise ValueError('annotations are not bound to this sample')
    given = annotations.get('annotations')
    if not isinstance(given, dict) or set(given) != set(sample['strata']):
        raise ValueError('annotation strata differ from the sample')
    summary = {}
    for name, row in sample['strata'].items():
        fields = FIELDS[row['kind']]
        items = given[name]
        if not isinstance(items, list) or [i.get('key') for i in items] != [s['key'] for s in row['selected']]:
            raise ValueError(f'{name}: annotated keys differ from the sample')
        counts = {f: dict.fromkeys(ANSWERS, 0) for f in fields}
        for item in items:
            if set(item) != {'key', 'note', *fields}:
                raise ValueError(f'{name}: annotation fields')
            if not isinstance(item['note'], str) or len(item['note']) > MAX_NOTE:
                raise ValueError(f'{name}: note must be text of at most {MAX_NOTE} characters')
            for f in fields:
                if item[f] not in ANSWERS:
                    raise ValueError(f'{name}: {f} must be one of {ANSWERS}')
                counts[f][item[f]] += 1
        summary[name] = {'annotated': len(items), 'answers': counts}
    disagreement = {}
    for scope in ('gate_eligible', 'ls20'):
        rows = [summary[n]['answers']['label_describes_visible_situation'] for n in LABEL_STRATA if n.startswith(scope)]
        no, yes = sum(r['no'] for r in rows), sum(r['yes'] for r in rows)
        rate = no / (no + yes) if no + yes else None
        disagreement[scope] = {'disagree': no, 'agree': yes, 'unclear': sum(r['unclear'] for r in rows),
                               'disagreement_rate': rate,
                               'above_20_percent': None if rate is None else rate > 0.20,
                               'status': 'descriptive only (amendment S1); not label certification'}
    return {'version': VERSION, 'sample_sha256': sample['sample_sha256'], 'strata': summary,
            'label_disagreement': disagreement}
def verify_commitment(receipt, sample, annotations, digest):
    """Verify an immutable, local Git commit of the completed review before any comparison.

    A caller-supplied digest alone is insufficient. The private receipt names an
    existing commit whose two blobs must be the exact evidence-bound sample and
    annotations now being pooled. No Git/network write occurs during verification.
    """
    import hashlib
    import json
    from pathlib import Path
    import re
    import subprocess
    if receipt is None:
        raise ValueError('prior private annotation commitment required')
    path = Path(receipt)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 8192:
        raise ValueError('invalid private annotation commitment receipt')
    record = json.loads(path.read_bytes())
    commit = record.get('commit', '')
    repository = Path(record['repository']).resolve()
    if record.get('scope') != 'stagnation_supervision_private_annotations_v1' or not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('invalid private annotation commitment')
    def git(*args):
        import os
        env = {k: v for k, v in os.environ.items() if k not in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE')}
        return subprocess.run(['git', '-C', str(repository), *args], check=True,
                              capture_output=True, timeout=10, env=env).stdout
    try:
        if Path(git('rev-parse', '--show-toplevel').decode().strip()).resolve() != repository:
            raise ValueError('commitment repository must be its own private checkout')
        if git('remote').strip():
            raise ValueError('annotation repository must have no publication remote')
        if git('cat-file', '-t', commit).strip() != b'commit':
            raise ValueError('annotation commitment is not a commit')
        committed_annotations = git('show', commit + ':annotations.json')
        committed_sample = git('show', commit + ':sample.json')
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError('private annotation commit unavailable or invalid') from exc
    if (hashlib.sha256(committed_annotations).hexdigest() != digest
            or committed_annotations != Path(annotations).read_bytes()
            or record.get('annotations_sha256') != digest
            or record.get('sample_sha256') != sample['sample_sha256']
            or json.loads(committed_sample) != sample):
        raise ValueError('private annotation commit does not bind these exact evidence inputs and annotations')
    validate(sample, json.loads(committed_annotations))
    return {'commit': commit, 'annotations_sha256': digest, 'sample_sha256': sample['sample_sha256']}


def commit_annotations(repository, receipt, sample_path, annotations_path):
    """Owner-invoked local commitment; refuses reuse, incomplete annotations or a publication remote.

    Use a new private directory outside every other repository. Git's configured
    author identity is required. This never uploads, pushes or computes comparisons.
    """
    import hashlib
    import json
    from pathlib import Path
    import subprocess
    repository, receipt = Path(repository).resolve(), Path(receipt).resolve()
    if repository.exists() or receipt.exists():
        raise FileExistsError('private commitment destination already exists')
    sample = json.loads(Path(sample_path).read_bytes())
    raw = Path(annotations_path).read_bytes()
    validate(sample, json.loads(raw))
    import os
    env = {k: v for k, v in os.environ.items() if k not in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE')}
    probe = subprocess.run(['git', '-C', str(repository.parent), 'rev-parse', '--show-toplevel'],
                           capture_output=True, timeout=10, env=env)
    if probe.returncode == 0:
        raise ValueError('private annotations must be committed outside every other repository')
    repository.mkdir(parents=True, mode=0o700)
    def git(*args):
        return subprocess.run(['git', '-C', str(repository), *args], check=True,
                              capture_output=True, timeout=10, env=env).stdout
    git('init', '--quiet')
    (repository / 'annotations.json').write_bytes(raw)
    (repository / 'sample.json').write_bytes(Path(sample_path).read_bytes())
    git('add', '--', 'annotations.json', 'sample.json')
    git('commit', '--quiet', '-m', 'Commit completed Track 3 self-review before pooled comparison')
    record = {'scope': 'stagnation_supervision_private_annotations_v1', 'repository': str(repository),
              'commit': git('rev-parse', 'HEAD').decode().strip(),
              'annotations_sha256': hashlib.sha256(raw).hexdigest(), 'sample_sha256': sample['sample_sha256']}
    receipt.parent.mkdir(parents=True, exist_ok=True)
    with receipt.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(record, stream, indent=1)
        stream.write('\n')
    verify_commitment(receipt, sample, annotations_path, record['annotations_sha256'])
    return record
