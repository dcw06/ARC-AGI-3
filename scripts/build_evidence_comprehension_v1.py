"""Build the frozen evidence-comprehension v1 probe set, revision 2 (offline; no model, no GPU).

Conditions:
- evidence_only (the main gate): continuous synthetic trajectories, built by the real record code, in
  the live observation format without grids. Adjacent-state continuity is asserted.
- legacy_description / corrected_description: dimension-change trajectories with the live
  description text and with a corrected one; the same questions, reported separately.
- archived_with_grids / archived_without_grids: preselected exact live observations from the
  hash-verified action-effect-history archive, asked the same questions with and without grids.

Every key is computed twice (probes.primary_key from the shown entries; independent.answer from raw
frames and outcomes) and the build fails on any disagreement or discontinuity.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.evidence_comprehension_v1 import independent, probes as P  # noqa: E402
from research.evidence_comprehension_v1.score import best_shortcuts, shortcut_baselines  # noqa: E402

FIXTURES = ROOT / 'research/action_effect_v1/fixtures.json'
ARCHIVE_LOCK = ROOT / 'reports/action_effect_history_v1_archive.json'
EPISODES = 'reports/runs/action-effect-history-v1/download/action-effect-history-v1/worker/run/episodes/'
OUTPUT = ROOT / 'research/evidence_comprehension_v1/probes.json'
SUMMARY = ROOT / 'reports/evidence_comprehension_v1_probe_summary.json'
REQUESTS = ROOT / '.cache/evidence_comprehension_v1_requests.jsonl'
BASE_CASE = 'identical_frames'  # the ar25 development frame used by the record fixtures
REAL_EPISODES = ('b1-ar25-history', 'b1-s5i5-history', 'b1-wa30-history')  # block 2 repeated these exactly
REAL_DECISIONS = (5, 11)  # preselected: a mid-episode and the final decision of each case


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def archived_episodes():
    lock = json.loads(ARCHIVE_LOCK.read_bytes())
    archive = ROOT / lock['archive']
    if sha(archive.read_bytes()) != lock['archive_sha256']:
        raise ValueError('archive hash mismatch')
    result = {}
    with zipfile.ZipFile(archive) as bundle:
        for name in REAL_EPISODES:
            member = EPISODES + name + '.json'
            raw = bundle.read(member)
            if sha(raw) != lock['members'][member]['sha256']:
                raise ValueError('archived episode hash mismatch: ' + name)
            result[name] = json.loads(raw)
    return lock['archive_sha256'], result


def rng_for(context_id):
    return random.Random(sha(f'{P.VERSION}:{context_id}'.encode()))


def check_keys(probes, entries, legal, disagreements):
    for probe in probes:
        check = independent.answer(entries, legal, probe['family'], probe['arg'])
        if check != probe['key']:
            disagreements.append((probe['probe_id'], probe['key'], check))


def check_window(context_id, observation, entries, omitted, disagreements):
    history = observation['action_effect_history']
    if omitted != history['omitted_entries'] or [e['step'] for e in entries] != [e['step'] for e in history['entries']]:
        disagreements.append((context_id, 'shown entries'))


def build():
    fixtures = json.loads(FIXTURES.read_bytes())
    base = next(c for c in fixtures['cases'] if c['case_id'] == BASE_CASE)['pre']['frames'][-1]
    archive_sha, episodes = archived_episodes()
    contexts, probes, disagreements = [], [], []
    trajectories = P.synthetic_contexts(base)
    discontinuities = [e for t in trajectories for e in P.continuity_errors(t)]
    if discontinuities:
        raise ValueError(f'discontinuous synthetic trajectories: {discontinuities[:3]}')
    for t in trajectories:
        entries, omitted = independent.synthetic_entries(t)
        designed = t['source'] == 'synthetic_designed'
        if t['context_id'].startswith('dim-'):
            legacy = P.synthetic_observation(t)
            args = P.probe_args(legacy, rng_for(t['context_id']), exhaustive=True)
            for condition, observation in (('legacy_description', legacy),
                                           ('corrected_description', P.synthetic_observation(t, corrected=True))):
                check_window(t['context_id'], observation, entries, omitted, disagreements)
                batch = P.make_probes(t['context_id'], condition, observation, args, match_group='description')
                check_keys(batch, entries, t['legal_actions'], disagreements)
                probes += batch
                contexts.append({'context_id': f'{condition}:{t["context_id"]}', 'condition': condition,
                                 'source': t['source'], 'observation': observation, 'trajectory': t})
            continue
        observation = P.synthetic_observation(t)
        check_window(t['context_id'], observation, entries, omitted, disagreements)
        batch = P.make_probes(t['context_id'], 'evidence_only', observation,
                              P.probe_args(observation, rng_for(t['context_id']), exhaustive=designed))
        check_keys(batch, entries, t['legal_actions'], disagreements)
        probes += batch
        contexts.append({'context_id': f'evidence_only:{t["context_id"]}', 'condition': 'evidence_only',
                         'source': t['source'], 'observation': observation, 'trajectory': t})
    for name in REAL_EPISODES:
        episode = episodes[name]
        for k in REAL_DECISIONS:
            step = episode['steps'][k]
            call = episode['calls'][step['call_index']]
            full = json.loads(call['request']['messages'][1]['content'])['observation']
            if sorted(full['legal_actions']) != sorted(step['before']['available_actions']):
                raise ValueError('legal actions differ from the engine observation')
            source_id = f'{name}-d{k:02d}'
            entries, omitted = independent.archived_entries(episode, k)
            args = P.probe_args(full, rng_for(source_id))
            provenance = {'episode_id': name, 'decision': k, 'call_index': step['call_index'],
                          'request_sha256': call['request_sha256'], 'server_prompt_tokens': call['server_prompt_tokens']}
            for condition, observation in (('archived_with_grids', full), ('archived_without_grids', P.without_grids(full))):
                check_window(source_id, observation, entries, omitted, disagreements)
                batch = P.make_probes(source_id, condition, observation, args, match_group='grids')
                check_keys(batch, entries, full['legal_actions'], disagreements)
                probes += batch
                contexts.append({'context_id': f'{condition}:{source_id}', 'condition': condition,
                                 'source': 'archived_live_request', 'observation': observation, 'provenance': provenance})
    if disagreements:
        raise ValueError(f'primary and independent keys disagree: {disagreements[:5]}')
    return {'version': P.VERSION, 'system_prompt': P.SYSTEM_PROMPT, 'max_tokens': P.MAX_TOKENS,
            'fixtures_sha256': sha(FIXTURES.read_bytes()), 'source_archive_sha256': archive_sha,
            'contexts': contexts, 'probes': probes}


def summary(value):
    best = best_shortcuts(value['probes'])
    counts = {}
    for probe in value['probes']:
        key = probe['key'] if isinstance(probe['key'], str) else ('empty' if probe['key'] == [] else 'value')
        for label in (f"{probe['condition']}/{probe['family']}", f"{probe['condition']}/{probe['family']}/key={key}",
                      *[f"{probe['condition']}/{probe['family']}/{s}" for s in probe['strata']]):
            counts[label] = counts.get(label, 0) + 1
        if best[(probe['condition'], probe['family'])][0] not in probe['shortcuts_correct']:
            label = f"{probe['condition']}/{probe['family']}/best_shortcut_wrong"
            counts[label] = counts.get(label, 0) + 1
    by_condition = {}
    for c in value['contexts']:
        by_condition[c['condition']] = by_condition.get(c['condition'], 0) + 1
    return {'version': value['version'], 'probe_set_sha256': sha(encode(value)), 'contexts': by_condition,
            'probes': len(value['probes']), 'counts': dict(sorted(counts.items())),
            'shortcut_baselines': shortcut_baselines(value['probes'])}


def export_requests(value):
    """Exact requests for the pinned-tokenizer audit (scripts/audit_evidence_comprehension_v1_tokens.py)."""
    contexts = {c['context_id']: c for c in value['contexts']}
    REQUESTS.parent.mkdir(exist_ok=True)
    with REQUESTS.open('w', encoding='utf-8') as stream:
        for probe in value['probes']:
            request = P.build_request(contexts[probe['context_id']], probe)
            stream.write(json.dumps({'probe_id': probe['probe_id'], 'condition': probe['condition'],
                                     'key_response': json.dumps({'answer': probe['key']}, separators=(',', ':')),
                                     'request': request}, sort_keys=True) + '\n')
    return len(value['probes'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='rebuild in memory and compare with the frozen files')
    parser.add_argument('--export-requests', action='store_true', help='write exact requests for the token audit')
    args = parser.parse_args()
    value = build()
    raw = encode(value)
    report = (json.dumps(summary(value), sort_keys=True, indent=1) + '\n').encode()
    if args.check:
        if OUTPUT.read_bytes() != raw or SUMMARY.read_bytes() != report:
            raise SystemExit('frozen probe set differs from a fresh build')
        print('probe set matches a fresh build:', sha(raw))
    elif args.export_requests:
        print(json.dumps({'requests': export_requests(value), 'path': REQUESTS.relative_to(ROOT).as_posix()}))
    else:
        OUTPUT.write_bytes(raw)
        SUMMARY.write_bytes(report)
        print(json.dumps({'probes': len(value['probes']), 'bytes': len(raw), 'sha256': sha(raw)}))
