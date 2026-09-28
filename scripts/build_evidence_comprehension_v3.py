"""Build the frozen evidence-comprehension v3 question set (offline; no model, no GPU).

Partitions: withheld (the decision; two passes), development (one pass), transfer (v1's six archived observations
without grids; one pass; previously exposed; no counterfactual variants). Every original context is asked under
both conditions of both tracks; every counterfactual-eligible synthetic context is also asked, for the control
track only, with its matched synthetic counterfactual history.

The build fails on:
- any key that disagrees with the independent derivation;
- a tool field or computed control metadata that disagrees with its independent recomputation;
- an intervention that is not a pure addition to its reference observation;
- a counterfactual that changes anything but ACTION6 action references, or leaves an inconsistent reference;
- coverage below the frozen minimums;
- a repeated request, or an observation that repeats one from v1, v2 or elsewhere in v3.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.evidence_comprehension_v2 import trajectories as T  # noqa: E402
from research.evidence_comprehension_v2.score import best_shortcut  # noqa: E402
from research.evidence_comprehension_v3 import cases as C, independent as I, probes as P, representation as R  # noqa: E402
from scripts.build_evidence_comprehension_v1 import BASE_CASE, FIXTURES, archived_episodes  # noqa: E402
from scripts.build_evidence_comprehension_v2 import check_representation, pack  # noqa: E402

OUTPUT = ROOT / 'research/evidence_comprehension_v3/probes.json'
SUMMARY = ROOT / 'reports/evidence_comprehension_v3_probe_summary.json'
V1_PROBES = ROOT / 'research/evidence_comprehension_v1/probes.json'
V2_PROBES = ROOT / 'research/evidence_comprehension_v2/probes.json'
SCHEDULE_SEED = 'evidence-comprehension-v3-schedule'
# Frozen minimums (withheld partition, original variant, per target family and condition).
MIN_TARGET_QUESTIONS, MIN_TARGET_DISAGREEMENT, MIN_TARGET_CONTEXTS = 100, 20, 60
MIN_COMPONENT_QUESTIONS = 100
MIN_COUNTERFACTUAL_PAIRS = 40


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def prior_observations():
    """Canonical observations of every v1 and v2 context: v3 must not repeat any of them."""
    seen = set()
    for path in (V1_PROBES, V2_PROBES):
        for c in json.loads(path.read_bytes())['contexts']:
            seen.add(C.canonical(c['observation']))
    return seen


def check_interventions(context_id, observation, errors):
    a1 = R.with_control_metadata(observation)
    if {k: v for k, v in a1.items() if k != R.CONTROL_FIELD} != observation:
        errors.append((context_id, 'A1 is not a pure addition'))
    meta = a1[R.CONTROL_FIELD]['legal_actions_with_action_data']
    if [(m['action_id'], m['action_data']) for m in meta] != I.control_metadata(observation['legal_actions']):
        errors.append((context_id, 'computed control metadata disagrees with the independent recomputation'))
    b0 = P.present(observation, 'B0_normalized_history')
    b1 = P.present(observation, 'B1_tool_eligibility')
    if R.strip_tool_fields(b1) != b0:
        errors.append((context_id, 'B1 is not a pure addition to B0'))
    check_representation(context_id, observation, errors)
    return b1


def check_tool(context_id, b1, shown, errors):
    presented = [(e['step'], e[R.TOOL_RULE], e[R.TOOL_REASON]) for e in b1['action_effect_history']['entries']]
    if presented != I.tool_eligibility(shown):
        errors.append((context_id, 'tool fields disagree with the independent recomputation'))


def check_keys(batch, shown, legal, errors):
    for probe in batch:
        check = I.answer(shown, legal, probe['family'], probe['arg'])
        if not P.V2.same_answer(probe['family'], check, probe['key']):
            errors.append((probe['probe_id'], probe['key'], check))


def check_window(context_id, observation, shown, omitted, errors):
    history = observation['action_effect_history']
    if omitted != history['omitted_entries'] or [r['step'] for r in shown] != [e['step'] for e in history['entries']]:
        errors.append((context_id, 'shown entries differ from the independent window'))


def check_counterfactual(original, variant, errors):
    cid = original['context_id']
    for a, b in zip(original['events'], variant['events']):
        if {k: v for k, v in a.items() if k != 'action'} != {k: v for k, v in b.items() if k != 'action'}:
            errors.append((cid, 'counterfactual changed more than an action'))
        if a['action']['action_id'] != 6 and a['action'] != b['action']:
            errors.append((cid, 'counterfactual changed a non-ACTION6 action'))
    if len(original['events']) != len(variant['events']) or any(e['action']['action_id'] == 6 for e in variant['events']):
        errors.append((cid, 'counterfactual still contains ACTION6 or lost events'))
    o, v = T.observation(original), T.observation(variant)
    if {k: x for k, x in o.items() if k not in ('action_effect_history', 'recent_actions')} != {
            k: x for k, x in v.items() if k not in ('action_effect_history', 'recent_actions')}:
        errors.append((cid, 'counterfactual changed a non-history field'))
    if v['recent_actions'] != ([variant['events'][-1]['action']['action_id']] if variant['events'] else []):
        errors.append((cid, 'counterfactual recent_actions inconsistent'))
    strip = lambda e: {k: x for k, x in e.items() if k not in ('action_id', 'action_data')}  # noqa: E731
    if [strip(e) for e in o['action_effect_history']['entries']] != [strip(e) for e in v['action_effect_history']['entries']]:
        errors.append((cid, 'counterfactual changed an outcome'))


def add(partition, context_id, variant, observation, all_steps, shown, omitted, args, template, source, extra, errors):
    check_window(f'{context_id}:{variant}', observation, shown, omitted, errors)
    b1 = check_interventions(f'{context_id}:{variant}', observation, errors)
    check_tool(f'{context_id}:{variant}', b1, shown, errors)
    batch = P.make_probes(partition, context_id, variant, observation, args, template)
    check_keys(batch, shown, observation['legal_actions'], errors)
    contexts = []
    for condition in P.CONDITIONS:
        if variant == 'counterfactual' and P.CONDITIONS[condition] != 'control':
            continue
        contexts.append({'context_id': f'{partition}:{condition}:{variant}:{context_id}', 'partition': partition,
                         'condition': condition, 'variant': variant, 'source': source, 'source_context': context_id,
                         'template': template, 'observation': P.present(observation, condition), **extra})
    return contexts, batch


def build():
    fixtures = json.loads(FIXTURES.read_bytes())
    base = next(c for c in fixtures['cases'] if c['case_id'] == BASE_CASE)['pre']['frames'][-1]
    contexts, probes, errors, trajectories, frames = [], [], [], {}, {}
    seen = prior_observations()
    for partition in ('withheld', 'development'):
        balancer = P.V2.Balancer()
        for t in C.contexts(base, partition, seen):
            rows = I.synthetic_rows(t)
            shown, omitted, all_steps = I.window(rows)
            observation = T.observation(t)
            args = P.question_args(observation, all_steps, P.rng_for(t['context_id']), balancer)
            c, p = add(partition, t['context_id'], 'original', observation, all_steps, shown, omitted, args,
                       t['template'], 'synthetic', {}, errors)
            contexts += c
            probes += p
            trajectories[t['context_id']] = pack(t, frames)
            if C.counterfactual_eligible(t):
                v = C.counterfactual(t)
                check_counterfactual(t, v, errors)
                v_observation = T.observation(v)
                if C.canonical(v_observation) in seen:
                    errors.append((t['context_id'], 'counterfactual observation repeats another'))
                seen.add(C.canonical(v_observation))
                v_rows = I.synthetic_rows(v)
                v_shown, v_omitted, _ = I.window(v_rows)
                c, p = add(partition, t['context_id'], 'counterfactual', v_observation, all_steps, v_shown, v_omitted,
                           args, t['template'], 'synthetic_counterfactual_history',
                           {'replacement_action': v['replacement_action']}, errors)
                contexts += c
                probes += p
                trajectories[t['context_id'] + ':counterfactual'] = pack(v, frames)
    archive_sha, episodes = archived_episodes()
    v1 = json.loads(V1_PROBES.read_bytes())
    balancer = P.V2.Balancer()
    for v1_context in (c for c in v1['contexts'] if c['condition'] == 'archived_without_grids'):
        provenance = v1_context['provenance']
        rows = I.archived_rows(episodes[provenance['episode_id']], provenance['decision'])
        shown, omitted, all_steps = I.window(rows)
        context_id = 'tra-' + v1_context['context_id'].split(':', 1)[1]
        observation = v1_context['observation']
        args = P.question_args(observation, all_steps, P.rng_for(context_id), balancer)
        c, p = add('transfer', context_id, 'original', observation, all_steps, shown, omitted, args, 'archived',
                   'archived_live_request_without_grids',
                   {'provenance': {**provenance, 'v1_context_id': v1_context['context_id']}}, errors)
        contexts += c
        probes += p
    if errors:
        raise ValueError(f'build checks failed: {errors[:5]}')
    requests = {}
    by_context = {c['context_id']: c for c in contexts}
    for p in probes:
        digest = sha(json.dumps(P.build_request(by_context[p['context_id']], p), sort_keys=True).encode())
        if digest in requests:
            raise ValueError(f'repeated request: {p["probe_id"]} and {requests[digest]}')
        requests[digest] = p['probe_id']
    check_coverage(probes)
    return {'version': P.VERSION, 'model': P.MODEL,
            'system_prompts': {c: P.system_prompt(c) for c in P.CONDITIONS},
            'computed_control_metadata_example': R.control_metadata([1, 2, 6]),
            'tool_fields_description': R.TOOL_DESCRIPTION, 'max_tokens': P.MAX_TOKENS, 'passes': P.PASSES,
            'fixtures_sha256': sha(FIXTURES.read_bytes()), 'source_archive_sha256': archive_sha,
            'v1_probe_set_sha256': sha(V1_PROBES.read_bytes()), 'v2_probe_set_sha256': sha(V2_PROBES.read_bytes()),
            'frames': dict(sorted(frames.items())), 'trajectories': trajectories, 'contexts': contexts,
            'probes': probes, 'schedule': schedule(probes)}


def schedule(probes):
    """Pass 1: withheld contexts in seeded order; each question's conditions and variants adjacent, in seeded
    order. Pass 2: withheld pass 1 exactly reversed. Then development and transfer, pass 1 only."""
    rng = random.Random(sha(SCHEDULE_SEED.encode()))
    order = []
    for partition in ('withheld', 'development', 'transfer'):
        by_context = {}
        for p in probes:
            if p['partition'] == partition:
                question = p['probe_id'].rsplit('-', 1)[1]
                by_context.setdefault(p['source_context'], {}).setdefault(question, []).append(p['probe_id'])
        ids = []
        contexts = sorted(by_context)
        rng.shuffle(contexts)
        for c in contexts:
            for question in sorted(by_context[c]):
                members = sorted(by_context[c][question])
                rng.shuffle(members)
                ids += members
        order.append({'pass': 'pass_1', 'partition': partition, 'probe_ids': ids})
        if P.PASSES[partition] == 2:
            order.append({'pass': 'pass_2', 'partition': partition, 'probe_ids': list(reversed(ids))})
    return order


def check_coverage(probes):
    failures = []
    groups = {}
    for p in probes:
        if p['partition'] == 'withheld' and p['variant'] == 'original':
            groups.setdefault((p['condition'], p['family']), []).append(p)
    for (condition, family), group in sorted(groups.items()):
        best = best_shortcut(group)
        disagreement = sum(best[0] not in p['shortcuts_correct'] for p in group)
        contexts = len({p['source_context'] for p in group})
        if family in P.TRACKS[P.TRACK_OF[family]]['targets']:
            if len(group) < MIN_TARGET_QUESTIONS or disagreement < MIN_TARGET_DISAGREEMENT or contexts < MIN_TARGET_CONTEXTS:
                failures.append((condition, family, len(group), disagreement, contexts))
        elif len(group) < MIN_COMPONENT_QUESTIONS:
            failures.append((condition, family, len(group)))
    pairs = {p['source_context'] for p in probes if p['partition'] == 'withheld' and p['variant'] == 'counterfactual'}
    if len(pairs) < MIN_COUNTERFACTUAL_PAIRS:
        failures.append(('counterfactual contexts', len(pairs)))
    if failures:
        raise ValueError(f'coverage below the frozen minimums: {failures}')


def summary(value):
    groups, counts = {}, {}
    for p in value['probes']:
        name = f"{p['partition']}/{p['variant']}/{p['condition']}/{p['family']}"
        groups.setdefault(name, []).append(p)
        key = p['key'] if isinstance(p['key'], str) else ('empty' if p['key'] == [] else 'non_empty')
        for label in (name, f'{name}/key={key}', *[f'{name}/{s}' for s in p['strata']]):
            counts[label] = counts.get(label, 0) + 1
    shortcuts = {}
    for name, group in sorted(groups.items()):
        best = best_shortcut(group)
        shortcuts[name] = {'n': len(group), 'best_shortcut': best[0], 'best_shortcut_accuracy': best[1],
                           'shortcut_disagreement_n': sum(best[0] not in p['shortcuts_correct'] for p in group),
                           'contexts': len({p['source_context'] for p in group})}
    phases = {f"{s['partition']}/{s['pass']}": len(s['probe_ids']) for s in value['schedule']}
    return {'version': value['version'], 'probe_set_sha256': sha(encode(value)), 'probes': len(value['probes']),
            'scheduled_calls': sum(phases.values()), 'calls_by_phase': phases,
            'contexts': len(value['contexts']),
            'counterfactual_contexts': {part: len({p['source_context'] for p in value['probes']
                                                  if p['partition'] == part and p['variant'] == 'counterfactual'})
                                        for part in ('withheld', 'development')},
            'counts': dict(sorted(counts.items())), 'shortcuts': shortcuts}


def outputs(value):
    return {OUTPUT: encode(value), SUMMARY: (json.dumps(summary(value), sort_keys=True, indent=1) + '\n').encode()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='rebuild in memory and compare with the frozen files')
    args = parser.parse_args()
    files = outputs(build())
    if args.check:
        stale = [str(p.relative_to(ROOT)) for p, raw in files.items() if not p.exists() or p.read_bytes() != raw]
        if stale:
            raise SystemExit(f'frozen files differ from a fresh build: {stale}')
        print('question set matches a fresh build:', sha(files[OUTPUT]))
    else:
        for path, raw in files.items():
            path.write_bytes(raw)
        report = json.loads(files[SUMMARY])
        print(json.dumps({k: report[k] for k in ('probes', 'scheduled_calls', 'calls_by_phase', 'contexts',
                                                  'counterfactual_contexts', 'probe_set_sha256')}, indent=1))
