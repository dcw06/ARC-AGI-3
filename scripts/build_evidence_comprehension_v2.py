"""Build the frozen evidence-comprehension v2 question set (offline; no model, no GPU).

Partitions:
- withheld (the decision): fresh seeded trajectories, asked twice;
- development: fresh seeded trajectories from a different seed, asked once, descriptive;
- transfer: the six archived live observations (without grids) that v1 already used, asked once and
  reported descriptively as previously exposed contexts.

Each context's questions are asked under the baseline and under the candidate of their track. Every key is
computed twice (probes.primary_key from shown entries; independent.answer from raw frames and outcomes) and
the build fails on any disagreement, any discontinuity, any representation that is not information-equivalent,
any condition that differs from the baseline by more than its registered intervention, or coverage below the
frozen minimums.

Also writes the v1 baseline freeze record: the hashes of the completed v1 diagnostic's files, which stay
unchanged and serve as the baseline for this work.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.evidence_comprehension_v2 import independent, probes as P, representation as R  # noqa: E402
from research.evidence_comprehension_v2 import trajectories as T  # noqa: E402
from research.evidence_comprehension_v2.score import best_shortcut  # noqa: E402
from scripts.build_evidence_comprehension_v1 import BASE_CASE, FIXTURES, archived_episodes  # noqa: E402

OUTPUT = ROOT / 'research/evidence_comprehension_v2/probes.json'
SUMMARY = ROOT / 'reports/evidence_comprehension_v2_probe_summary.json'
BASELINE = ROOT / 'reports/evidence_comprehension_v1_baseline_freeze.json'
REQUESTS = ROOT / '.cache/evidence_comprehension_v2_requests.jsonl'
V1_PROBES = ROOT / 'research/evidence_comprehension_v1/probes.json'
SCHEDULE_SEED = 'evidence-comprehension-v2-schedule'
# Frozen minimums for the withheld partition, per target family and condition.
MIN_TARGET_QUESTIONS, MIN_TARGET_DISAGREEMENT, MIN_TARGET_CONTEXTS = 60, 20, 30
MIN_COMPONENT_QUESTIONS = 60
V1_REVIEW_LOCK = 'notebooks/evidence-comprehension-v1-review-r3/review-source-lock.json'
V1_LAUNCH_LOCK = 'notebooks/evidence-comprehension-v1-run/launch-package-lock.json'
V1_REVIEW_LOCK_SHA256 = 'fa425fd07469defdccae26ffdbdc29233380d0086bbdd480b31e24515715c051'
# Files of the completed v1 attempt. Each one the r3 review lock binds must still match the hash it bound.
V1_BASELINE_FILES = (
    V1_REVIEW_LOCK, V1_LAUNCH_LOCK,
    'reports/evidence_comprehension_v1_protocol.md',  # revision 5: the protocol the r3 package bound
    'research/evidence_comprehension_v1/probes.json', 'research/evidence_comprehension_v1/probes.py',
    'research/evidence_comprehension_v1/independent.py', 'research/evidence_comprehension_v1/score.py',
    'research/action_effect_history_v1/contract.py', 'research/action_effect_v1/records.py',
    'reports/evidence_comprehension_v1_probe_summary.json', 'reports/evidence_comprehension_v1_token_audit.json',
    'reports/evidence_comprehension_v1_review.md', 'reports/evidence_comprehension_v1_results.md',
    'reports/evidence_comprehension_v1_live_evaluation.json', 'reports/evidence_comprehension_v1_live_archive.json',
    'evidence/evidence-comprehension-v1-live.tar.xz', 'reports/evidence_comprehension_v1_source_approval.json',
    'reports/evidence_comprehension_v1_compute_authorization.json', 'reports/evidence_comprehension_v1_postrun_provider.json')
V1_HISTORICAL = ('reports/evidence_comprehension_v1_protocol_r4.md',)  # context only: superseded before the launch


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def check_representation(context_id, observation, errors):
    """The candidate must carry exactly the baseline's entries and differ only in the history field."""
    base = observation['action_effect_history']
    cand = R.candidate_observation(observation)
    if [R.denormalize_entry(e) for e in cand['action_effect_history']['entries']] != base['entries']:
        errors.append((context_id, 'candidate entries are not information-equivalent'))
    if cand['action_effect_history']['omitted_entries'] != base['omitted_entries']:
        errors.append((context_id, 'omitted count differs'))
    if {k: v for k, v in cand.items() if k != 'action_effect_history'} != {
            k: v for k, v in observation.items() if k != 'action_effect_history'}:
        errors.append((context_id, 'candidate changes more than the history field'))


def check_keys(batch, shown, legal, errors):
    for probe in batch:
        check = independent.answer(shown, legal, probe['family'], probe['arg'])
        if not P.same_answer(probe['family'], check, probe['key']):
            errors.append((probe['probe_id'], probe['key'], check))


def check_window(context_id, observation, shown, omitted, errors):
    history = observation['action_effect_history']
    if omitted != history['omitted_entries'] or [r['step'] for r in shown] != [e['step'] for e in history['entries']]:
        errors.append((context_id, 'shown entries differ from the independent window'))


def pack(trajectory, frames):
    """The trajectory with every frame replaced by a reference into the shared frame table."""
    def ref(text):
        key = sha(text.encode())[:16]
        if frames.setdefault(key, text) != text:
            raise ValueError('frame reference collision')
        return key
    events = [{**e, 'pre': ref(e['pre']), **({'returned': [ref(f) for f in e['returned']]} if 'returned' in e else {})}
              for e in trajectory['events']]
    return {**trajectory, 'events': events, 'final': ref(trajectory['final'])}


def add_context(partition, context_id, observation, all_steps, shown, omitted, balancer, source, errors, extra):
    check_window(context_id, observation, shown, omitted, errors)
    check_representation(context_id, observation, errors)
    args = P.question_args(observation, all_steps, P.rng_for(context_id), balancer)
    contexts, probes = [], []
    template = extra.get('template', 'archived')
    for condition in P.CONDITIONS:
        batch = P.make_probes(partition, context_id, condition, observation, args, template)
        check_keys(batch, shown, observation['legal_actions'], errors)
        probes += batch
        contexts.append({'context_id': f'{partition}:{condition}:{context_id}', 'partition': partition,
                         'condition': condition, 'source': source, 'source_context': context_id,
                         'observation': P.present(observation, condition), **extra})
    return contexts, probes


def schedule(probes):
    """Pass 1: withheld contexts in seeded order, each pair's conditions adjacent in seeded order; pass 2: the
    withheld pass 1 reversed; then development and transfer, pass 1 only."""
    rng = random.Random(sha(SCHEDULE_SEED.encode()))
    order = []
    for partition in ('withheld', 'development', 'transfer'):
        by_context = {}
        for p in probes:
            if p['partition'] == partition:
                by_context.setdefault(p['source_context'], {}).setdefault(p['pair_id'], []).append(p['probe_id'])
        contexts = sorted(by_context)
        rng.shuffle(contexts)
        ids = []
        for c in contexts:
            for pair in sorted(by_context[c]):
                members = sorted(by_context[c][pair])
                rng.shuffle(members)
                ids += members
        order.append(('pass_1', partition, ids))
        if P.PASSES[partition] == 2:
            order.append(('pass_2', partition, list(reversed(ids))))
    first = [o for o in order if o[1] == 'withheld']
    return [{'pass': p, 'partition': part, 'probe_ids': ids} for p, part, ids in first + [
        o for o in order if o[1] != 'withheld']]


def build():
    fixtures = json.loads(FIXTURES.read_bytes())
    base = next(c for c in fixtures['cases'] if c['case_id'] == BASE_CASE)['pre']['frames'][-1]
    contexts, probes, errors, trajectories, frames, seen = [], [], [], {}, {}, set()
    for partition in ('withheld', 'development'):
        balancer = P.Balancer()
        for t in T.contexts(base, partition, seen):
            rows = independent.synthetic_rows(t)
            shown, omitted, all_steps = independent.window(rows)
            c, p = add_context(partition, t['context_id'], T.observation(t), all_steps, shown, omitted, balancer,
                               'synthetic', errors, {'template': t['template']})
            if independent.synthetic_rows(independent.resolve(pack(t, frames), frames)) != rows:
                errors.append((t['context_id'], 'packed trajectory differs'))
            trajectories[t['context_id']] = pack(t, frames)
            contexts += c
            probes += p
    archive_sha, episodes = archived_episodes()
    v1 = json.loads(V1_PROBES.read_bytes())
    balancer = P.Balancer()
    for v1_context in (c for c in v1['contexts'] if c['condition'] == 'archived_without_grids'):
        provenance = v1_context['provenance']
        rows = independent.archived_rows(episodes[provenance['episode_id']], provenance['decision'])
        shown, omitted, all_steps = independent.window(rows)
        context_id = 'tra-' + v1_context['context_id'].split(':', 1)[1]
        c, p = add_context('transfer', context_id, v1_context['observation'], all_steps, shown, omitted, balancer,
                           'archived_live_request_without_grids', errors,
                           {'template': 'archived', 'provenance': {**provenance, 'v1_context_id': v1_context['context_id']}})
        contexts += c
        probes += p
    if errors:
        raise ValueError(f'build checks failed: {errors[:5]}')
    ids = [p['probe_id'] for p in probes]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate probe ids')
    check_coverage(probes)
    return {'version': P.VERSION, 'model': P.MODEL, 'system_prompts': {c: P.system_prompt(c) for c in P.CONDITIONS},
            'control_instruction': P.CONTROL_INSTRUCTION, 'candidate_history_description': R.CANDIDATE_DESCRIPTION,
            'max_tokens': P.MAX_TOKENS, 'passes': P.PASSES, 'fixtures_sha256': sha(FIXTURES.read_bytes()),
            'source_archive_sha256': archive_sha, 'v1_probe_set_sha256': sha(V1_PROBES.read_bytes()),
            'frames': dict(sorted(frames.items())), 'trajectories': trajectories,
            'contexts': contexts, 'probes': probes, 'schedule': schedule(probes)}


def coverage_rows(probes):
    rows = {}
    for p in probes:
        if p['partition'] == 'withheld':
            rows.setdefault((p['condition'], p['family']), []).append(p)
    return rows


def check_coverage(probes):
    failures = []
    for (condition, family), group in sorted(coverage_rows(probes).items()):
        best = best_shortcut(group)
        disagreement = sum(best[0] not in p['shortcuts_correct'] for p in group)
        contexts = len({p['source_context'] for p in group})
        if family in P.TRACKS[P.TRACK_OF[family]]['targets']:
            if len(group) < MIN_TARGET_QUESTIONS or disagreement < MIN_TARGET_DISAGREEMENT or contexts < MIN_TARGET_CONTEXTS:
                failures.append((condition, family, len(group), disagreement, contexts))
        elif len(group) < MIN_COMPONENT_QUESTIONS:
            failures.append((condition, family, len(group)))
    if failures:
        raise ValueError(f'coverage below the frozen minimums: {failures}')


def summary(value):
    counts = {}
    for p in value['probes']:
        key = p['key'] if isinstance(p['key'], str) else ('empty' if p['key'] == [] else 'non_empty')
        for label in (f"{p['partition']}/{p['condition']}/{p['family']}",
                      f"{p['partition']}/{p['condition']}/{p['family']}/key={key}",
                      *[f"{p['partition']}/{p['condition']}/{p['family']}/{s}" for s in p['strata']]):
            counts[label] = counts.get(label, 0) + 1
    groups = {}
    for p in value['probes']:
        groups.setdefault(f"{p['partition']}/{p['condition']}/{p['family']}", []).append(p)
    shortcuts = {}
    for name, group in sorted(groups.items()):
        best = best_shortcut(group)
        shortcuts[name] = {'n': len(group), 'best_shortcut': best[0], 'best_shortcut_accuracy': best[1],
                           'shortcut_disagreement_n': sum(best[0] not in p['shortcuts_correct'] for p in group),
                           'contexts': len({p['source_context'] for p in group})}
    by_partition = {}
    for c in value['contexts']:
        key = f"{c['partition']}/{c['condition']}"
        by_partition[key] = by_partition.get(key, 0) + 1
    calls = sum(len(s['probe_ids']) for s in value['schedule'])
    return {'version': value['version'], 'probe_set_sha256': sha(encode(value)), 'contexts': by_partition,
            'probes': len(value['probes']), 'scheduled_calls': calls, 'counts': dict(sorted(counts.items())),
            'shortcuts': shortcuts}


def baseline_freeze():
    lock_raw = (ROOT / V1_REVIEW_LOCK).read_bytes()
    if sha(lock_raw) != V1_REVIEW_LOCK_SHA256:
        raise ValueError('v1 r3 review lock hash mismatch')
    lock = json.loads(lock_raw)
    launch = json.loads((ROOT / V1_LAUNCH_LOCK).read_bytes())
    if launch['review_lock_sha256'] != V1_REVIEW_LOCK_SHA256:
        raise ValueError('v1 launch package does not bind the r3 review lock')
    files = {path: sha((ROOT / path).read_bytes()) for path in V1_BASELINE_FILES}
    bound = {**lock['bindings'], **lock['review_documents']}
    matched = {}
    for path, digest in files.items():
        if path in bound:
            if bound[path] != digest:
                raise ValueError(f'{path} differs from the hash the r3 review lock bound')
            matched[path] = True
    if 'reports/evidence_comprehension_v1_protocol.md' not in matched:
        raise ValueError('the r3 review lock does not bind the v1 protocol')
    return {'record': 'evidence comprehension v1 baseline freeze (revision 2)',
            'attempt': launch['attempt_id'], 'review_lock': V1_REVIEW_LOCK,
            'review_lock_sha256': V1_REVIEW_LOCK_SHA256, 'review_lock_revision': lock['revision'],
            'launch_package_lock': V1_LAUNCH_LOCK,
            'protocol': {'path': 'reports/evidence_comprehension_v1_protocol.md', 'revision': 5,
                         'bound_by_review_lock': True},
            'statement': ('The completed v1 diagnostic (prompts, questions, keys, responses, scoring rules, evaluation and '
                          'archive) is the frozen baseline and is not changed. Its questions and answers have been '
                          'inspected, so they are development material, not an untouched validation set. Follow-up '
                          'work is labelled as informed by these results.'),
            'findings_used': ['coordinate_actions: all 19 errors answered [6] when ACTION6 was not legal',
                              'tried_unchanged: weakest family (15/44)',
                              'outcome_class / observed_effect: changed-then-returned read as no change'],
            'files': files, 'files_matching_review_lock_bindings': sorted(matched),
            'historical_context_only': {path: sha((ROOT / path).read_bytes()) for path in V1_HISTORICAL}}


def export_requests(value):
    contexts = {c['context_id']: c for c in value['contexts']}
    REQUESTS.parent.mkdir(exist_ok=True)
    with REQUESTS.open('w', encoding='utf-8') as stream:
        for probe in value['probes']:
            request = P.build_request(contexts[probe['context_id']], probe)
            stream.write(json.dumps({'probe_id': probe['probe_id'], 'partition': probe['partition'],
                                     'condition': probe['condition'], 'family': probe['family'],
                                     'key_response': json.dumps({'answer': probe['key']}, separators=(',', ':')),
                                     'request': request}, sort_keys=True) + '\n')
    return len(value['probes'])


def outputs(value):
    return {OUTPUT: encode(value), SUMMARY: (json.dumps(summary(value), sort_keys=True, indent=1) + '\n').encode(),
            BASELINE: (json.dumps(baseline_freeze(), sort_keys=True, indent=1) + '\n').encode()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='rebuild in memory and compare with the frozen files')
    parser.add_argument('--export-requests', action='store_true', help='write exact requests for the token audit')
    args = parser.parse_args()
    value = build()
    files = outputs(value)
    if args.check:
        stale = [str(path.relative_to(ROOT)) for path, raw in files.items() if not path.exists() or path.read_bytes() != raw]
        if stale:
            raise SystemExit(f'frozen files differ from a fresh build: {stale}')
        print('question set matches a fresh build:', sha(files[OUTPUT]))
    elif args.export_requests:
        print(json.dumps({'requests': export_requests(value), 'path': REQUESTS.relative_to(ROOT).as_posix()}))
    else:
        for path, raw in files.items():
            path.write_bytes(raw)
        print(json.dumps({'probes': len(value['probes']), 'bytes': len(files[OUTPUT]), 'sha256': sha(files[OUTPUT]),
                          'scheduled_calls': sum(len(s['probe_ids']) for s in value['schedule'])}))
