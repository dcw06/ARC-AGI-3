"""Build the frozen evidence-comprehension v1 probe set (offline; no model, no GPU).

Contexts:
- evidence_only: synthetic histories built by the real record code from the action-effect
  fixtures, in the live observation format without grids;
- full_observation: the exact observations the live history arm received, taken from the
  hash-verified action-effect-history v1 archive, grids included.

Every key is computed twice (probes.primary_key from the shown entries; independent.answer from
raw frames and outcomes) and the build fails on any disagreement.
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
from research.evidence_comprehension_v1.score import heuristic_baselines  # noqa: E402

FIXTURES = ROOT / 'research/action_effect_v1/fixtures.json'
ARCHIVE_LOCK = ROOT / 'reports/action_effect_history_v1_archive.json'
EPISODES = 'reports/runs/action-effect-history-v1/download/action-effect-history-v1/worker/run/episodes/'
OUTPUT = ROOT / 'research/evidence_comprehension_v1/probes.json'
SUMMARY = ROOT / 'reports/evidence_comprehension_v1_probe_summary.json'
REAL_EPISODES = ('b1-ar25-history', 'b1-s5i5-history', 'b1-wa30-history')  # block 2 repeated these exactly
REAL_DECISIONS = (0, 3, 5, 7, 9, 11)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


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


def real_contexts(episodes):
    contexts = []
    for name in REAL_EPISODES:
        episode = episodes[name]
        for k in REAL_DECISIONS:
            step = episode['steps'][k]
            call = episode['calls'][step['call_index']]
            observation = json.loads(call['request']['messages'][1]['content'])['observation']
            if sorted(observation['legal_actions']) != sorted(step['before']['available_actions']):
                raise ValueError('legal actions differ from the engine observation')
            contexts.append({'context_id': f'real-{name}-d{k:02d}', 'source': 'archived_live_request', 'grids': True,
                             'provenance': {'episode_id': name, 'decision': k, 'call_index': step['call_index'],
                                            'request_sha256': call['request_sha256'],
                                            'server_prompt_tokens': call['server_prompt_tokens'],
                                            'request_chars': len(call['request']['messages'][0]['content'])
                                            + len(call['request']['messages'][1]['content'])},
                             'observation': observation,
                             'raw_entries': independent.archived_entries(episode, k)})
    return contexts


def build():
    fixtures = json.loads(FIXTURES.read_bytes())
    cases = P.fixture_cases(fixtures)
    archive_sha, episodes = archived_episodes()
    contexts = []
    for context in P.synthetic_contexts():
        contexts.append({**context, 'observation': P.synthetic_observation(context, cases),
                         'raw_entries': independent.synthetic_entries(context, fixtures)})
    contexts += real_contexts(episodes)
    probes, disagreements = [], []
    for context in contexts:
        rng = random.Random(sha(f'{P.VERSION}:{context["context_id"]}'.encode()))
        observation = context['observation']
        entries, omitted = context.pop('raw_entries')
        history = observation['action_effect_history']
        if omitted != history['omitted_entries'] or [e['step'] for e in entries] != [e['step'] for e in history['entries']]:
            disagreements.append((context['context_id'], 'shown entries'))
        for probe in P.make_probes(context, observation, rng):
            check = independent.answer(entries, observation['legal_actions'], probe['family'], probe['arg'])
            if check != probe['key']:
                disagreements.append((probe['probe_id'], probe['key'], check))
            probes.append(probe)
    if disagreements:
        raise ValueError(f'primary and independent keys disagree: {disagreements[:5]}')
    value = {'version': P.VERSION, 'system_prompt': P.SYSTEM_PROMPT, 'max_tokens': P.MAX_TOKENS,
             'fixtures_sha256': sha(FIXTURES.read_bytes()), 'source_archive_sha256': archive_sha,
             'contexts': [{k: v for k, v in c.items()} for c in contexts], 'probes': probes}
    return value


def token_estimate(value):
    """Prompt tokens per request, scaled from the archived live requests' measured tokens per character."""
    real = [c for c in value['contexts'] if c['grids']]
    ratio = sum(c['provenance']['server_prompt_tokens'] for c in real) / sum(c['provenance']['request_chars'] for c in real)
    contexts = {c['context_id']: c for c in value['contexts']}
    per_condition = {}
    for probe in value['probes']:
        request = P.build_request(contexts[probe['context_id']], probe)
        chars = sum(len(m['content']) for m in request['messages']) + len(json.dumps(request['response_format']))
        row = per_condition.setdefault(probe['condition'], {'probes': 0, 'estimated_prompt_tokens': 0, 'max': 0})
        estimate = round(chars * ratio)
        row['probes'] += 1
        row['estimated_prompt_tokens'] += estimate
        row['max'] = max(row['max'], estimate)
    return {'tokens_per_char_from_archive': round(ratio, 5), 'by_condition': per_condition,
            'note': 'estimate only; the budget proposal must use the pinned tokenizer'}


def summary(value):
    counts = {}
    for probe in value['probes']:
        key = probe['key'] if isinstance(probe['key'], str) else ('empty' if probe['key'] == [] else 'value')
        for label in (f"{probe['condition']}/{probe['family']}", f"{probe['condition']}/{probe['family']}/key={key}",
                      *[f"{probe['condition']}/{probe['family']}/{s}" for s in probe['strata']]):
            counts[label] = counts.get(label, 0) + 1
    observations = {c['context_id']: c['observation'] for c in value['contexts']}
    return {'version': value['version'], 'probe_set_sha256': sha(encode(value)),
            'contexts': {'evidence_only': sum(not c['grids'] for c in value['contexts']),
                         'full_observation': sum(c['grids'] for c in value['contexts'])},
            'probes': len(value['probes']), 'counts': dict(sorted(counts.items())),
            'heuristic_baselines': heuristic_baselines(value['probes'], observations),
            'token_estimate': token_estimate(value)}


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='rebuild in memory and compare with the frozen files')
    args = parser.parse_args()
    value = build()
    raw = encode(value)
    report = (json.dumps(summary(value), sort_keys=True, indent=1) + '\n').encode()
    if args.check:
        if OUTPUT.read_bytes() != raw or SUMMARY.read_bytes() != report:
            raise SystemExit('frozen probe set differs from a fresh build')
        print('probe set matches a fresh build:', sha(raw))
    else:
        OUTPUT.write_bytes(raw)
        SUMMARY.write_bytes(report)
        print(json.dumps({'probes': len(value['probes']), 'bytes': len(raw), 'sha256': sha(raw)}))
