"""Two-session pooled evaluation (frozen protocol v2; hand-written; CPU only; post-run; never repairs evidence).

The frozen trajectory evaluator (closed_loop/evaluate.py) and outcome functions (outcomes.py) are unchanged and
evaluate one session at a time. The protocol's comparisons pool both blocks. This module:
1. recomputes each session's study report (report.study_report: the runtime v2 target evaluator over the frozen
   trajectory evaluator, plus, in live mode, the evaluating checkout's review lock) and requires it to equal the
   retained session record in canonical JSON, so a stale or edited session evaluation cannot be pooled;
2. requires both sessions technically complete and accepted (§9: a technically incomplete run reports no outcome
   result) and, in live mode, the session-2 execution lock to bind the retained session-1 record by SHA-256;
3. requires the amendment-S1 self-review annotations, hashed by the caller from the committed record, whose sample
   equals the deterministic redraw from these sessions (selfreview.py), before any pooled comparison is computed;
4. rebuilds every episode's records with the frozen evaluator (each must have no problem) and computes:
   - primary behavioural recovery per arm over the primary games ar25, wa30 and ls20 (s5i5, the declared blind
     spot, is reported separately, §4), main episodes of both blocks; the block-1 continuation repeats are kept
     out of the arm rates and used for run-to-run variance (§5); intervals are the episode-cluster bootstrap with
     the protocol seed and Wilson as a naive reference (§8);
   - the same per block and game, and point differences between arms (descriptive);
   - the preregistered suggestion-following exits (§8.1; descriptive): for each recovered opportunity in a
     reflection arm, whether a suggestion block was in force at the exit step's policy request and whether the
     dispatched exit action equals its first distinguishing-test action;
   - completed levels, the provisional false-interruption gate (not certifiable with wa30 alone, §8.3), realised
     cost and reliability;
   - reproducibility: whether each repeat and each block-2 episode reproduces its counterpart's trajectory, and
     the number of distinct trajectories per game and arm. Deterministic decoding (temperature 0, seed 0) can make
     repeated episodes identical; intervals over identical episodes then overstate precision;
   - each §8.6 advancement condition and the verdict ("inconclusive" unless all hold; the gate condition cannot
     hold in this study).

Amendment S2 (owner decision, October 12, 2026, frozen protocol §14), recorded after the sessions ran (block 2 replayed
block 1 exactly), before any outcome was inspected and before any pooled comparison was computed:
- the self-review sample is drawn over distinct trajectories only (selfreview.sample_for);
- `pooled` is computed exactly as frozen and reported, labelled as overstating precision when exact duplicates exist;
- `pooled_distinct` computes the same quantities over distinct trajectories only (exact duplicates excluded, the
  copy earliest in (session, episode) order kept) and is the interpretive headline. The §8.6 verdict is not
  recomputed there; it is the frozen one, inconclusive by construction (§8.3);
- a session-1 evaluation re-run under a later review lock may stand in for the one the session-2 execution lock
  binds, if the bound launch-time record is supplied and the two are equal apart from the evaluating lock.
"""
import hashlib
import json
from pathlib import Path

from research.stagnation_supervision_v1 import intervention as I, outcomes as O
from research.transition_evidence_v2 import vocabulary as V
from research.stagnation_supervision_runtime_v2 import selfreview as SR

VERSION = 'stagnation_supervision_pooled_evaluation_v1'
ARMS = ('continuation', 'periodic', 'triggered')
PRIMARY_GAMES = ('ar25', 'wa30', 'ls20')
BLIND_SPOT = 's5i5'
GAMES = PRIMARY_GAMES + (BLIND_SPOT,)
PAIRS = (('triggered', 'continuation'), ('triggered', 'periodic'), ('periodic', 'continuation'))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False, default=str)


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _first_tests(episode):
    """Per step: the first distinguishing-test action of the suggestion block shown with that step's policy request,
    or None. The block (already checked against the replayed supervisor by the frozen evaluator) must render exactly
    from the stored valid intervention it names."""
    events = {e['action_index']: e for e in (episode.get('supervision') or {}).get('events', [])}
    tests = []
    for step in episode['steps']:
        shown = step.get('suggestion_shown')
        if shown is None:
            tests.append(None)
            continue
        event = events.get(shown['issued_after_action'])
        if (event is None or event.get('outcome') != 'called' or event.get('delivered') != shown['text']
                or not event['call']['parsed']['valid']):
            raise ValueError(f"step {step['index']}: suggestion block has no delivered reflection")
        intervention = event['call']['parsed']['intervention']
        if I.render(intervention) != shown['text']:
            raise ValueError(f"step {step['index']}: suggestion text does not render from the stored intervention")
        tests.append(intervention['distinguishing_test']['actions'][0])
    return tests


def session_episodes(run_folder, spec, trigger_spec, session):
    """Every episode of one session, rebuilt by the frozen evaluator; any problem refuses."""
    from research.stagnation_supervision_v1.closed_loop import evaluate as E
    from research.stagnation_supervision_v1.closed_loop.evidence import load_verified
    run = load_verified(run_folder)
    inventory = json.loads((Path(run_folder) / 'manifest.json').read_bytes())
    evidence_sha256 = O.digest(inventory)
    replay = E._replay_module()
    schedule = {s['pair_id']: s for s in spec['schedule']}
    out = []
    for episode in run['episodes']:
        result = E.evaluate_episode(episode, spec, trigger_spec, replay)
        if result['problems'] or result['evaluation_input'] is None:
            raise ValueError(f"{episode.get('episode_id')}: episode evidence has problems")
        row = schedule[episode['pair_id']]
        events = (episode.get('supervision') or {}).get('events', [])
        out.append({**result['evaluation_input'], 'session': str(session), 'episode': episode['episode_id'],
                    'pair_id': episode['pair_id'], 'block': row['block'], 'game_id': episode['game_id'],
                    'game': episode['game_id'].split('-', 1)[0], 'repeat_of': row.get('repeat_of'),
                    'repeat': row.get('repeat_of') is not None, 'levels_completed': result['levels_completed'],
                    'stop_reason': result['stop_reason'], 'first_tests': _first_tests(episode),
                    'evidence_inventory_sha256': evidence_sha256,
                    'reflection_evidence': episode.get('supervision'),
                    'delivered': [e['action_index'] for e in events
                                  if e.get('outcome') == 'called' and e.get('delivered') is not None]})
    return out


def _opportunities(e, trigger_spec, horizon):
    return O.opportunities(e['records'], trigger_spec, horizon)


def recovery(episodes, trigger_spec, horizon):
    """Primary rate per arm: recovered / (recovered + not_recovered), with both intervals and all counts."""
    out = {}
    for arm in ARMS:
        rows = [e for e in episodes if e['arm'] == arm]
        per, status, opportunities, censored, exits = [], {}, 0, 0, []
        for e in rows:
            result = _opportunities(e, trigger_spec, horizon)
            statuses = [o['status'] for o in result['opportunities']]
            k = statuses.count('recovered')
            per.append((k, k + statuses.count('not_recovered')))
            opportunities += len(statuses)
            censored += len(result['censored_horizon_firings'])
            for s in statuses:
                status[s] = status.get(s, 0) + 1
            exits += [o['actions_to_exit'] for o in result['opportunities'] if o['actions_to_exit'] is not None]
        k, n = sum(p[0] for p in per), sum(p[1] for p in per)
        out[arm] = {'episodes': len(rows), 'opportunities': opportunities, 'status': status,
                    'censored_horizon_firings': censored, 'recovered': k, 'decided': n,
                    'rate': k / n if n else None, 'wilson_95': O.wilson(k, n),
                    'episode_cluster_bootstrap_95': O.cluster_bootstrap(per), 'actions_to_exit': sorted(exits)}
    return out


def differences(rates):
    return {f'{a}_minus_{b}': (None if rates[a]['rate'] is None or rates[b]['rate'] is None
                               else rates[a]['rate'] - rates[b]['rate']) for a, b in PAIRS}


def suggestion_following(episodes, trigger_spec, horizon):
    """§8.1 descriptive measure, per reflection arm and game, with totals over the primary games."""
    out = {}
    for arm in ('periodic', 'triggered'):
        by_game = {}
        for game in GAMES:
            row = {'recovered_exits': 0, 'with_suggestion_in_force': 0, 'exit_equals_first_test_action': 0,
                   'without_suggestion_in_force': 0}
            for e in episodes:
                if e['arm'] != arm or e['game'] != game:
                    continue
                for o in _opportunities(e, trigger_spec, horizon)['opportunities']:
                    if o['status'] != 'recovered':
                        continue
                    row['recovered_exits'] += 1
                    test = e['first_tests'][o['exit_at']]
                    if test is None:
                        row['without_suggestion_in_force'] += 1
                        continue
                    row['with_suggestion_in_force'] += 1
                    dispatched = e['records'][o['exit_at']]['action']['dispatched']
                    row['exit_equals_first_test_action'] += canonical(dispatched) == canonical(test)
            n = row['with_suggestion_in_force']
            row['share'] = row['exit_equals_first_test_action'] / n if n else None
            by_game[game] = row
        total = {k: sum(by_game[g][k] for g in PRIMARY_GAMES) for k in by_game[PRIMARY_GAMES[0]] if k != 'share'}
        total['share'] = (total['exit_equals_first_test_action'] / total['with_suggestion_in_force']
                          if total['with_suggestion_in_force'] else None)
        out[arm] = {'by_game': by_game, 'primary_games': total}
    return {'by_arm': out, 'status': 'preregistered descriptive measure; never the primary endpoint, gate or advancement'}


def _signature(records):
    return O.digest([[f['action'], f['after'], f['dispatch']] for f in map(O._facts, records)])


def reproducibility(episodes, trigger_spec, horizon):
    by_id = {e['episode']: e for e in episodes}

    def rate(e):
        statuses = [o['status'] for o in _opportunities(e, trigger_spec, horizon)['opportunities']]
        k, n = statuses.count('recovered'), statuses.count('recovered') + statuses.count('not_recovered')
        return k / n if n else None

    repeats = []
    for e in episodes:
        if e['repeat']:
            original = by_id[e['repeat_of']]
            a, b = rate(original), rate(e)
            repeats.append({'repeat': e['episode'], 'original': original['episode'],
                            'identical_trajectory': _signature(e['records']) == _signature(original['records']),
                            'original_rate': a, 'repeat_rate': b,
                            'absolute_difference': None if a is None or b is None else abs(a - b)})
    blocks = []
    for e in episodes:
        if e['block'] == 2 and not e['repeat']:
            twin = by_id.get(e['episode'].replace('b2-', 'b1-', 1))
            if twin is not None:
                blocks.append({'block_2': e['episode'], 'block_1': twin['episode'],
                               'identical_trajectory': _signature(e['records']) == _signature(twin['records'])})
    distinct = {}
    for game in GAMES:
        for arm in ARMS:
            sigs = {_signature(e['records']) for e in episodes
                    if not e['repeat'] and e['game'] == game and e['arm'] == arm}
            distinct[f'{game}/{arm}'] = len(sigs)
    spreads = [r['absolute_difference'] for r in repeats if r['absolute_difference'] is not None]
    return {'repeats': repeats, 'block_2_vs_block_1': blocks, 'distinct_main_trajectories': distinct,
            'repeat_episode_spread': max(spreads) if spreads else None,
            'note': ('temperature 0 and seed 0 make episodes with identical inputs replay identically unless the serving '
                     'stack is nondeterministic; identical episodes are reproductions, not independent replicates, and '
                     'episode-cluster intervals over them overstate precision')}


def reliability(episodes):
    out = {}
    for arm in ARMS:
        rows = [e for e in episodes if e['arm'] == arm]
        facts = [O._facts(r) for e in rows for r in e['records']]
        reflections = [r for e in rows for r in e['reflections']]
        failed = sum(f['dispatch'] == V.FAILED for f in facts)
        unknown = sum(f['dispatch'] == V.OUTCOME_UNKNOWN for f in facts)
        invalid = sum(r['status'] != 'failed' and r['valid'] is not True for r in reflections)
        out[arm] = {'dispatches': len(facts), 'failed_dispatches': failed, 'unknown_dispatches': unknown,
                    'failed_or_unknown_rate': (failed + unknown) / len(facts) if facts else None,
                    'episodes': len(rows), 'invalid_policy_output_stops': sum(e['stop_reason'] == 'invalid_output' for e in rows),
                    'reflection_calls': len(reflections), 'invalid_reflections': invalid,
                    'failed_reflections': sum(r['status'] == 'failed' for r in reflections),
                    'invalid_reflection_rate': invalid / len(reflections) if reflections else None}
    return out


def advancement(primary, by_block, gate, levels, reliable, spread):
    def higher(a, b):
        return a['rate'] is not None and b['rate'] is not None and a['rate'] > b['rate']

    stagnation = [by_block[b]['ar25'] for b in ('1', '2')]
    t, p = gate['triggered'], gate['periodic']
    rt, rp, rc = (reliable[a] for a in ('triggered', 'periodic', 'continuation'))

    def no_worse(x, *others):
        return x is not None and all(o is None or x <= o for o in others)

    diffs = differences(primary)
    conditions = {
        'against_periodic_both_blocks_stagnation_case': all(higher(b['triggered'], b['periodic']) for b in stagnation),
        'against_continuation': higher(primary['triggered'], primary['continuation']),
        'false_interruptions_within_cap_and_at_most_periodic': (
            t['status'] == 'within_provisional_cap' and t['rate'] is not None and p['rate'] is not None
            and t['rate'] <= p['rate']),
        'no_regressions': (levels['triggered'] >= max(levels['continuation'], levels['periodic'])
                           and no_worse(rt['failed_or_unknown_rate'], rp['failed_or_unknown_rate'], rc['failed_or_unknown_rate'])
                           and rt['invalid_policy_output_stops'] <= min(rp['invalid_policy_output_stops'], rc['invalid_policy_output_stops'])
                           and no_worse(rt['invalid_reflection_rate'] or 0.0, rp['invalid_reflection_rate'])),
        'beyond_repeat_episode_variance': (
            spread is not None and all(diffs[k] is not None and diffs[k] > spread
                                       for k in ('triggered_minus_periodic', 'triggered_minus_continuation'))),
    }
    return {'conditions': conditions, 'verdict': 'advances' if all(conditions.values()) else 'inconclusive',
            'note': ('the false-interruption condition cannot hold in this study: wa30 is the only qualified '
                     'continuation control, so the gate is not certifiable (owner decision, frozen protocol §8.3)')}


def compute(episodes, trigger_spec, horizon):
    """Every pooled quantity from verified episodes (no binding checks; `evaluate_sessions` performs them first)."""
    main = [e for e in episodes if not e['repeat']]
    primary_main = [e for e in main if e['game'] in PRIMARY_GAMES]
    primary = recovery(primary_main, trigger_spec, horizon)
    by_block = {str(b): {g: recovery([e for e in main if e['block'] == b and e['game'] == g], trigger_spec, horizon)
                         for g in GAMES} for b in (1, 2)}
    levels = {arm: sum(e['levels_completed'] for e in primary_main if e['arm'] == arm) for arm in ARMS}
    gate = {arm: O.interruptions(main, arm) for arm in ('triggered', 'periodic')}
    reliable = reliability(primary_main)
    variance = reproducibility(episodes, trigger_spec, horizon)
    blind = [e for e in main if e['game'] == BLIND_SPOT]
    return {
        'primary': {'games': list(PRIMARY_GAMES), 'by_arm': primary, 'differences': differences(primary),
                    'unit': 'episode; repeats excluded; s5i5 reported separately'},
        'by_block_and_game': {b: {g: {'by_arm': r, 'differences': differences(r)} for g, r in rows.items()}
                              for b, rows in by_block.items()},
        'suggestion_following': suggestion_following(main, trigger_spec, horizon),
        'solving': {'completed_levels_primary_games': levels,
                    'completed_levels_s5i5': {arm: sum(e['levels_completed'] for e in blind if e['arm'] == arm) for arm in ARMS}},
        'false_interruptions': gate,
        'false_interruptions_calls': {arm: O.interruptions(main, arm, what='calls') for arm in ('triggered', 'periodic')},
        'realised_cost': O.realised_cost(main),
        'reliability': reliable,
        'reproducibility': variance,
        'blind_spot_s5i5': {'by_arm': recovery(blind, trigger_spec, horizon),
                            'scope': 'declared blind-spot case; never pooled into the primary comparison (§4)'},
        'advancement': advancement(primary, by_block, gate, levels, reliable, variance['repeat_episode_spread']),
    }


def compute_distinct(episodes, trigger_spec, horizon):
    """Amendment S2: the frozen quantities over distinct trajectories only (the interpretive headline)."""
    kept, excluded = SR.distinct(episodes)
    primary_main = [e for e in kept if e['game'] in PRIMARY_GAMES]
    primary = recovery(primary_main, trigger_spec, horizon)
    by_game = {g: recovery([e for e in kept if e['game'] == g], trigger_spec, horizon) for g in GAMES}
    blind = [e for e in kept if e['game'] == BLIND_SPOT]
    return {
        'rule': SR.DISTINCT_RULE,
        'episodes': [[e['session'], e['episode']] for e in kept], 'duplicates_excluded': excluded,
        'primary': {'games': list(PRIMARY_GAMES), 'by_arm': primary, 'differences': differences(primary),
                    'unit': 'distinct trajectory; repeats and exact duplicates excluded; s5i5 reported separately'},
        'by_game': {g: {'by_arm': r, 'differences': differences(r)} for g, r in by_game.items()},
        'suggestion_following': suggestion_following(kept, trigger_spec, horizon),
        'solving': {'completed_levels_primary_games': {arm: sum(e['levels_completed'] for e in primary_main if e['arm'] == arm)
                                                       for arm in ARMS},
                    'completed_levels_s5i5': {arm: sum(e['levels_completed'] for e in blind if e['arm'] == arm) for arm in ARMS}},
        'false_interruptions': {arm: O.interruptions(kept, arm) for arm in ('triggered', 'periodic')},
        'false_interruptions_calls': {arm: O.interruptions(kept, arm, what='calls') for arm in ('triggered', 'periodic')},
        'realised_cost': O.realised_cost(kept),
        'reliability': reliability(primary_main),
        'blind_spot_s5i5': {'by_arm': recovery(blind, trigger_spec, horizon),
                            'scope': 'declared blind-spot case; never pooled into the primary comparison (§4)'},
        'advancement': ('not recomputed: the §8.6 verdict is the frozen one in `pooled`, inconclusive by construction '
                        'because the false-interruption gate is not certifiable (§8.3)'),
    }


def _without_lock(record):
    return {k: v for k, v in record.items() if k != 'review_lock'}


def evaluate_sessions(outputs, records, *, annotations, annotations_sha256, mode='live', specs=None,
                      internal_seconds=None, session2_execution=None, root=None, trigger_spec=None,
                      annotations_commitment=None, session1_launch_record=None):
    """outputs / records: {'1': path, '2': path} (target output folders; retained study-report JSON files).
    session1_launch_record: the session-1 evaluation the session-2 execution lock binds, when records['1'] is a
    re-evaluation under a later review lock (amendment S2).
    Returns the pooled evaluation; comparisons are withheld (None) unless every binding check passes."""
    from research.stagnation_supervision_v1 import thresholds as S
    from research.stagnation_supervision_v1.closed_loop.bridge import session_spec
    from research.stagnation_supervision_v1.closed_loop.runner import protocol
    from research.stagnation_supervision_runtime_v2.report import study_report
    if mode not in ('live', 'rehearsal'):
        raise ValueError('explicit live or rehearsal mode required')
    if mode == 'live' and trigger_spec is not None:
        raise ValueError('live pooling uses frozen thresholds; trigger override refused')
    trigger_spec = trigger_spec if trigger_spec is not None else S.load()
    problems, sessions = [], {}
    if mode == 'live' and (specs is not None or internal_seconds is not None):
        raise ValueError('live pooling uses the frozen session schedules and lifecycle')
    for s in ('1', '2'):
        spec = specs[s] if specs is not None else session_spec(protocol(), s)
        recomputed = study_report(outputs[s], spec, mode=mode, session=s,
                                  internal_seconds=None if internal_seconds is None else internal_seconds[s],
                                  root=root)
        stored = json.loads(Path(records[s]).read_bytes())
        if canonical(recomputed) != canonical(stored):
            problems.append(f'session {s}: retained evaluation differs from its recomputation (stale or edited)')
        complete = recomputed['technically_complete'] and (mode != 'live' or recomputed['target_accepted'])
        if not complete:
            problems.append(f'session {s}: not technically complete')
        sessions[s] = {'record_sha256': sha256_file(records[s]), 'technically_complete': recomputed['technically_complete'],
                       'target_accepted': recomputed['target_accepted'], 'spec': spec}
    if mode == 'live':
        if session2_execution is None:
            problems.append('session-2 execution lock not supplied')
        else:
            bound = (json.loads(Path(session2_execution).read_bytes()).get('session1_evaluation') or {}).get('sha256')
            if session1_launch_record is None:
                if bound != sessions['1']['record_sha256']:
                    problems.append('session-2 execution lock does not bind the retained session-1 evaluation')
            elif bound != sha256_file(session1_launch_record):
                problems.append('session-2 execution lock does not bind the supplied launch-time session-1 evaluation')
            elif (canonical(_without_lock(json.loads(Path(session1_launch_record).read_bytes())))
                  != canonical(_without_lock(json.loads(Path(records['1']).read_bytes())))):
                problems.append('session-1 re-evaluation differs from the launch-time evaluation beyond the evaluating lock')
            else:
                sessions['1']['launch_record_sha256'] = bound
    result = {'version': VERSION, 'mode': mode, 'problems': problems,
              'sessions': {s: {k: v for k, v in r.items() if k != 'spec'} for s, r in sessions.items()},
              'self_review': None, 'pooled': None, 'pooled_distinct': None}
    if problems:
        result['withheld_reason'] = 'binding or technical checks failed; no pooled comparison is computed'
        return result
    horizon = sessions['1']['spec']['limits']['actions_per_episode']
    if sessions['2']['spec']['limits']['actions_per_episode'] != horizon:
        raise ValueError('sessions use different horizons')
    episodes = []
    for s in ('1', '2'):
        episodes += session_episodes(Path(outputs[s]) / 'worker/run', sessions[s]['spec'], trigger_spec, s)
    sample = SR.sample_for(episodes, trigger_spec, horizon, inputs=inputs_digest(episodes))
    try:
        commitment = None
        if sha256_file(annotations) != annotations_sha256:
            raise ValueError('annotations differ from the committed hash')
        if mode == 'live' or annotations_commitment is not None:
            commitment = SR.verify_commitment(annotations_commitment, sample, annotations, annotations_sha256)
        review = SR.validate(sample, json.loads(Path(annotations).read_bytes()))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result['problems'].append(f'self-review (amendment S1): {type(exc).__name__}: {exc}')
        result['withheld_reason'] = 'the self-review must be drawn, annotated and committed before pooled comparison'
        return result
    result['self_review'] = {**review, 'annotations_sha256': annotations_sha256, 'private_commitment': commitment}
    result['pooled'] = compute(episodes, trigger_spec, horizon)
    result['pooled_distinct'] = compute_distinct(episodes, trigger_spec, horizon)
    duplicates = len(result['pooled_distinct']['duplicates_excluded'])
    result['headline'] = {
        'section': 'pooled_distinct',
        'amendment': 'S2 (owner decision, October 12, 2026)',
        'pooled_precision': (f'{duplicates} main episodes exactly duplicate an earlier one; the frozen `pooled` intervals '
                             'count each copy as an independent episode and overstate precision' if duplicates else
                             'no main episode exactly duplicates another; `pooled` and `pooled_distinct` use the same '
                             'episodes')}
    result['limitations'] = [
        'exposed development games and one model; not real-game or generalisation evidence',
        'behavioural recovery is loop exit, not learning or solving; completed levels are reported separately',
        'ls20 is retained with its display-driven novelty limitation and is exploratory for the gate',
        'the false-interruption gate is not certifiable with one qualified control (wa30)',
        'the self-review is the sole researcher\'s unblinded inspection, not an independent audit',
        'deterministic decoding can make repeated episodes identical; intervals then overstate precision',
        'amendment S2: exact duplicates are excluded from `pooled_distinct`; with one distinct trajectory per game and '
        'arm, its intervals reflect variation between games only, not run-to-run variation']
    return result


def inputs_digest(episodes):
    """The sample's binding to the evidence: each episode id with the digest of its rebuilt records."""
    return {'episodes': [[e['session'], e['episode'], O.digest({
        'records': e['records'], 'inventory': e.get('evidence_inventory_sha256'),
        'reflection_evidence': e.get('reflection_evidence'), 'reflections': e.get('reflections'),
        'first_tests': e.get('first_tests'), 'delivered': e.get('delivered')})] for e in episodes]}
