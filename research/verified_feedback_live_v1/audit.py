"""Independent retained-evidence replay and evaluation-only counterfactual scoring.

Fresh CPU engines must be supplied. No model inference or provider operation is
performed here. Reference outcomes never enter the inference payload.
"""
from collections import Counter
from copy import deepcopy
import json
import math
from pathlib import Path

from research.verified_feedback_v1.flow import run_case
from research.action_effect_choice_v2.flow import reference_branch
from research.action_effect_choice_v2.interface import parse_choice
from research.action_effect_choice_v2.scoring import branch_key, effect_size, score
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_io import sha
from research.recent_feedback_v1.audit import baseline_request
from .live_contract import check_checkpoints, verify_inputs
from .live_worker import canary, request_plan
from research.verified_feedback_v1.feedback import NOTE


def independent_commit(cp, pair, variant, events, texts):
    """Rebuild the envelope from the raw answer, not the producer's receipt."""
    commits = [e for e in events if e.get('kind') == 'forecast_commit']
    if not texts:
        if commits: raise ValueError('forecast commit without response')
        return None
    try: answer = parse_choice(texts[0], first=True)
    except (ValueError, TypeError, RecursionError):
        if commits: raise ValueError('invalid first response cannot commit a forecast')
        return None
    envelope = {'schema': 'verified_feedback_forecast_v1', 'trajectory_id': cp['checkpoint_id']+'-'+variant,
        'study_decision_index': 0, 'game_action_index': len(cp['prefix']),
        'before_observation_sha256': digest(cp['current']), 'candidates': pair, 'answer': answer}
    wanted = {'kind': 'forecast_commit', 'forecast': envelope, 'forecast_sha256': digest(envelope)}
    if not commits:
        # Exact prefix replay below proves admission stopped before commitment.
        if any(e.get('kind') == 'dispatch_intent' and e['decision'] == 0 for e in events):
            raise ValueError('dispatch without immutable forecast commitment')
        return None
    if len(commits) != 1 or digest(commits[0]) != digest(wanted):
        raise ValueError('independent pre-dispatch forecast commitment differs')
    response = next(i for i,e in enumerate(events) if e.get('kind')=='response' and e['decision']==0)
    commit = next(i for i,e in enumerate(events) if e.get('kind')=='forecast_commit')
    dispatch = next((i for i,e in enumerate(events) if e.get('kind')=='dispatch_intent' and e['decision']==0), None)
    if not response < commit or (dispatch is not None and not commit < dispatch):
        raise ValueError('forecast not journaled before dispatch')
    for event in events:
        if event.get('kind')=='transition' and event.get('transition_sha256')!=digest(event.get('record')):
            raise ValueError('independent executed transition commitment differs')
    return envelope


def independent_display(cp, pair, first_text, transition):
    """Separate row/column arithmetic; never call the production receipt builder."""
    answer = parse_choice(first_text, first=True)
    before, after = transition['before'], transition['after']
    changed = [(x,y) for y in range(64) for x in range(64) if before['grid'][y][x]!=after['grid'][y][x]]
    count = len(changed)
    category = ('none' if count==0 else '1_to_4' if 1<=count<=4 else '5_to_64' if 5<=count<=64 else '65_plus')
    forecast = answer['candidate_predictions'][answer['selected_candidate']]
    if digest(transition['action']) != digest(pair[answer['selected_candidate']]) or transition['step']!=len(cp['prefix']):
        raise ValueError('independent receipt event/action differs')
    return {'schema':'last_executed_study_action_feedback_v1','previous_study_decision_index':0,
        'game_action_index':len(cp['prefix']),'action':transition['action'],'original_selected_forecast':forecast,
        'observed_changed_cell_count':count,'observed_changed_cell_category':category,
        'observed_visible_change':'yes' if count else 'no',
        'original_forecast_check':'unknown' if forecast=='unknown' else 'matched' if forecast==category else 'mismatched',
        'forecast_comparison_available':forecast!='unknown','qualification':NOTE}


def paired_context(checkpoints, rows, output):
    from .live_evaluation import lines, _same
    paired=[]
    for cp in checkpoints:
        first=[r for r in rows if r['checkpoint_id']==cp['checkpoint_id'] and r['decision']==0]
        valid=len(first)==2 and all(r['observed'] and r['score']['valid'] for r in first)
        second=[r for r in rows if r['checkpoint_id']==cp['checkpoint_id'] and r['decision']==1]
        reached=len(second)==2 and all(r['observed'] for r in second)
        states=[];requests=[]
        for variant in cp['order']:
            events=lines(Path(output)/(cp['checkpoint_id']+'-'+variant+'.jsonl'))
            states.append(next((digest(e['record']['after']) for e in events if e.get('kind')=='transition' and e['decision']==0),None))
            requests.append(any(e.get('kind')=='request' and e['decision']==1 for e in events))
        comparable=reached and all(requests) and all(s is not None for s in states)
        paired.append({'checkpoint_id':cp['checkpoint_id'],'first_answers_comparable':valid,
            'first_parsed_answers_equal':None if not valid else _same(first[0]['score']['prediction'],first[1]['score']['prediction']),
            'second_state_comparable':comparable,'second_states_equal':None if not comparable else states[0]==states[1]})
    return paired


def audit_case(cp, pair, variant, events, replay_engine):
    """Rebuild every prompt and full transition; never trust terminal labels."""
    emitted, originals = [], [e for e in events if e.get('kind') == 'request']
    texts = [e['text'] for e in events if e.get('kind') == 'response']
    position = 0
    if events and events[0].get('kind') == 'not_admitted':
        stop = events[0]
        remaining = stop.get('remaining_seconds')
        if (set(stop) != {'kind', 'remaining_seconds', 'headroom_seconds'} or
                type(stop['headroom_seconds']) is not int or stop['headroom_seconds'] != 120 or
                type(remaining) not in (int, float) or not math.isfinite(remaining) or
                not -300 < remaining < 120 or replay_engine is not None):
            raise ValueError('unstarted condition admission receipt differs')
        result = dict(checkpoint_id=cp['checkpoint_id'], condition=variant, reason='not_admitted',
                      error=None, model_calls=0, new_dispatches=0, final_observation=None, lifecycle_certified=False)
        if events != [stop, {'kind': 'summary', **result}]:
            raise ValueError('unstarted condition contains work or false summary')
        return result
    stops = [e for e in events if e.get('kind') == 'admission_stop']
    if len(stops) > 1:
        raise ValueError('multiple admission stop receipts')
    stop = stops[0] if stops else None
    if stop is not None and (set(stop) != {'kind', 'check_index', 'overrun_seconds'} or
            type(stop['check_index']) is not int or stop['check_index'] < 1 or
            type(stop['overrun_seconds']) not in (int, float) or not math.isfinite(stop['overrun_seconds']) or
            not 0 <= stop['overrun_seconds'] < 300):
        raise ValueError('admission stop receipt exceeds cleanup reserve or differs')
    checks = 0
    def replay_clock():
        nonlocal checks
        checks += 1
        # Reproduce the precise admission boundary; every earlier event, full
        # request and actual observation must still match a fresh engine replay.
        return stop['overrun_seconds'] if stop is not None and checks == stop['check_index'] else -1

    def complete(body):
        nonlocal position
        if position >= len(originals) or position >= len(texts):
            raise ValueError('missing retained request/response')
        original = originals[position]
        if original.get('request_sha256') != digest(body) or digest(original.get('body')) != digest(body):
            raise ValueError('full reconstructed request differs')
        # Independent row/column arithmetic verifies the displayed summary.
        stripped = deepcopy(body)
        if position==1 and variant=='verified_feedback':
            from .live_evaluation import loads
            fact = stripped['messages'][1]['content'].pop()
            prior = next(e['record'] for e in emitted if e.get('kind')=='transition' and e['decision']==0)
            if fact.get('type')!='text' or digest(loads(fact['text']))!=digest(independent_display(cp,pair,texts[0],prior)):
                raise ValueError('independent displayed feedback differs')
        stripped['messages'][1]['content'].pop()  # frozen candidate extension
        stripped['messages'][0] = deepcopy(cp['base_request']['messages'][0])
        baseline_request(stripped, 'recent_summary')
        text = texts[position]
        position += 1
        return text

    try:
        result = run_case(cp, pair, variant, replay_engine, complete, emitted.append,
                          deadline=0, now=replay_clock)
    except (TimeoutError, IndexError, StopIteration) as exc:
        raise ValueError('retained prefix cannot be independently replayed') from exc
    if digest(emitted) != digest(events) or position != len(texts):
        raise ValueError('retained events/stop reason/final state differ from exact game replay')
    if (result['reason'] == 'exception' or result['model_calls'] > 2 or
            (result['reason'] == 'deadline') != bool(stop)):
        raise ValueError('incomplete condition or scope exceeded')
    independent_commit(cp,pair,variant,events,texts)
    return result


def audit_study(output, inputs, *, token_audit, replay_factory):
    from .live_evaluation import lines, loads, audit_transport, _same, _number, _kind
    if token_audit is None or replay_factory is None:
        raise ValueError('independent native counts and fresh CPU engine replay required')
    output, inputs = Path(output), Path(inputs)
    verify_inputs(inputs, sha(inputs/'manifest.json'))
    checkpoints = check_checkpoints(loads((inputs/'checkpoints.json').read_bytes())['checkpoints'])
    pairs = {r['checkpoint_id']: r['candidates'] for r in loads((inputs/'candidate-pairs.json').read_bytes())}
    expected, responses, sequence = {'canary': canary()}, {}, [('HTTP', 'canary')]
    summaries, rows = [], []
    schedule_stopped, previous_remaining = False, float('inf')
    prefix_dispatches = new_dispatches = 0
    for cp in checkpoints:
        identity, pair = cp['checkpoint_id'], pairs[cp['checkpoint_id']]
        for variant in cp['order']:
            name = identity+'-'+variant
            events = lines(output/(name+'.jsonl'))
            unstarted = bool(events and events[0].get('kind') == 'not_admitted')
            if schedule_stopped and not unstarted:
                raise ValueError('work resumed after schedule admission stopped')
            if unstarted:
                remaining = events[0].get('remaining_seconds')
                if type(remaining) not in (int, float) or remaining > previous_remaining:
                    raise ValueError('unstarted condition clock moved backwards')
                previous_remaining = remaining
            result = audit_case(cp, pair, variant, events,
                                None if unstarted else replay_factory(cp, name+'-replay'))
            summaries.append(result)
            schedule_stopped |= result['reason'] in ('deadline', 'not_admitted')
            prefix_dispatches += sum(e['kind'] == 'restored_transition' for e in events)
            transitions = [e['record'] for e in events if e['kind'] == 'transition']
            texts = [e['text'] for e in events if e['kind'] == 'response']
            new_dispatches += len(transitions)
            for index, event in enumerate(events):
                kind = event['kind']
                if kind == 'request':
                    if event['decision'] >= len(texts):
                        continue  # retained intent, refused before model admission
                    request_id = identity+'/'+variant+'/'+str(event['decision'])
                    if request_id in expected: raise ValueError('duplicate condition decision')
                    expected[request_id] = event['body']
                    sequence.append(('HTTP', request_id))
                elif kind == 'response':
                    responses[identity+'/'+variant+'/'+str(event['decision'])] = event['text']
                elif kind in ('bootstrap_intent', 'restore_dispatch_intent', 'dispatch_intent', 'closed'):
                    completion = {'bootstrap_intent': 'initial', 'restore_dispatch_intent': 'restored_transition',
                                  'dispatch_intent': 'transition'}.get(kind)
                    if completion is not None and (index+1 >= len(events) or events[index+1]['kind'] != completion):
                        # Exact prefix replay proves the final intent was not
                        # admitted; an engine transport failure is never salvaged.
                        continue
                    sequence.append(('engine', name, 'bootstrap' if kind == 'bootstrap_intent' else
                                     'close' if kind == 'closed' else 'dispatch'))
            previous = None
            for decision in range(2):
                if decision >= len(texts):
                    rows.append({'checkpoint_id': identity, 'variant': variant, 'decision': decision,
                                 'observed': False, 'stop_reason': result['reason'],
                                 'candidate_forecasts_scheduled': 2, 'candidate_forecasts_correct': 0})
                    continue
                path = transitions[:decision]
                before = cp['current'] if not path else path[-1]['after']
                references = {}
                for label in ('A', 'B'):
                    engine = replay_factory(cp, name+'-reference-'+str(decision)+'-'+label)
                    reference_events = []
                    references[label] = reference_branch(cp, pair, label, engine, reference_events.append,
                        path=path, deadline=float('inf'), now=lambda: 0)
                    if reference_events[-1] != {'kind': 'closed', 'receipt': {
                            'closed': True, 'local_scorecard_opened': True,
                            'local_scorecard_closed': True, 'online_calls': 0}}:
                        raise ValueError('reference engine/local scorecard not closed')
                key = branch_key(before, pair, references)
                prior_record = None if decision == 0 else transitions[decision-1]
                scored = score(texts[decision], key, first=decision == 0,
                    previous_forecast=None if previous is None else previous['candidate_predictions'][previous['selected_candidate']],
                    previous_observed=None if prior_record is None else
                        ('yes' if prior_record['before']['grid'] != before['grid'] else 'no'),
                    previous_effect=None if prior_record is None else effect_size(prior_record['before'], before))
                if scored['valid']:
                    answer = parse_choice(texts[decision], first=decision == 0)
                    if decision < len(transitions) and not _same(
                            references[answer['selected_candidate']]['after'], transitions[decision]['after']):
                        raise ValueError('actual selected transition differs from fresh reference branch')
                    if decision >= len(transitions) and result['reason'] != 'deadline':
                        raise ValueError('missing selected transition without witnessed admission stop')
                    previous = answer
                retrospective = {field: scored.pop(field) for field in (
                    'previous_observation_correct','previous_check_correct','previous_forecast_was_known')}
                retrospective['understanding_credit_permitted'] = False
                retrospective['interpretation'] = ('host_supplied_consistency_only' if variant=='verified_feedback' and decision==1
                                                   else 'descriptive_reading_only_not_primary')
                rows.append({'checkpoint_id': identity, 'variant': variant, 'decision': decision,
                             'observed': True, 'stop_reason': result['reason'], 'reference_key': key,
                             'candidate_forecasts_scheduled': 2,
                             'candidate_forecasts_correct': sum(v['correct'] for v in scored['forecasts'].values()),
                             'score': scored, 'retrospective_diagnostic': retrospective,
                             'reference_records_sha256': digest(references)})
    calls, effects = audit_transport(lines(output/'transport.jsonl'), expected, token_audit=token_audit)
    if [c['id'] for c in calls] != list(expected) or calls[0]['content'].strip() != 'ok':
        raise ValueError('full HTTP schedule or canary content differs')
    by_id = {c['id']: c for c in calls}
    if any(by_id[identity]['content'] != text for identity, text in responses.items()):
        raise ValueError('condition answer differs from complete retained HTTP reply')
    actual = [(c['transport_index'], ('HTTP', c['id'])) for c in calls]
    resets = dispatches = closes = 0
    for effect in effects:
        op = effect.get('operation')
        if op not in ('bootstrap', 'dispatch', 'close'): raise ValueError('unknown engine effect')
        resets += op == 'bootstrap'; dispatches += op == 'dispatch'; closes += op == 'close'
        wanted = dict(kind='engine_admission', episode=effect.get('episode'), operation=op,
            bootstrap_attempts=resets, dispatch_attempts=dispatches, close_attempts=closes,
            transport_index=effect['transport_index'])
        if not _same(effect, wanted): raise ValueError('engine admission counters differ')
        actual.append((effect['transport_index'], ('engine', effect['episode'], op)))
    if [event for _, event in sorted(actual)] != sequence:
        raise ValueError('HTTP/engine interleaving differs')
    worker = loads((output/'worker-result.json').read_bytes())
    wanted = dict(schema='verified_feedback_worker_v1', error=None, conditions=summaries,
                  bootstrap_attempts=resets, dispatch_attempts=dispatches, close_attempts=closes,
                  closed_scorecards=closes, lifecycle_certified=False)
    if set(worker) != set(wanted) | {'ledger'} or any(not _same(worker[k], v) for k, v in wanted.items()):
        raise ValueError('worker summaries or aggregate totals differ')
    ledger = worker['ledger']
    if (ledger.get('refusals') != [] or not _same(ledger.get('maximum_model_requests'), 33) or
            not _same(ledger.get('issued'), len(calls)) or
            not _same(ledger.get('by_kind'), dict(Counter(_kind(c['id']) for c in calls))) or
            len(ledger.get('entries', [])) != len(calls)):
        raise ValueError('worker HTTP ledger totals differ')
    for entry, call in zip(ledger['entries'], calls):
        wanted = {k: v for k, v in call['admission'].items() if k not in ('kind', 'request_kind')}
        wanted.update(kind=call['admission']['request_kind'], outcome='http_200')
        if (set(entry) != set(wanted) | {'seconds'} or any(not _same(entry[k], v) for k, v in wanted.items()) or
                not _number(entry['seconds'], 0, 30.001)):
            raise ValueError('worker HTTP ledger entry differs')
    plan = {item['id'] for item in request_plan(checkpoints)}
    started = sum(s['reason'] != 'not_admitted' for s in summaries)
    if (not 0 <= resets <= started <= 16 or closes != started or not 0 <= prefix_dispatches <= 36 or
            len(summaries) != 16 or len(rows) != 32 or
            not 0 <= new_dispatches <= 32 or dispatches != prefix_dispatches+new_dispatches or
            resets+dispatches > 84 or len(calls) != 1+len(responses) or len(calls) > 33 or
            any(c['id'] not in plan for c in calls)):
        raise ValueError('frozen schedule counts or scope differ')
    coverage = dict(scheduled=32, reached=sum(r['observed'] for r in rows),
                    valid=sum(r['observed'] and r['score']['valid'] for r in rows))
    paired = paired_context(checkpoints, rows, output)
    return dict(format_only=False, phase_coverage=coverage,
        format_coverage_complete=coverage['reached']==coverage['valid']==32, paired_context=paired,
        study_schedule_complete=not any(s['reason'] in ('deadline', 'not_admitted') for s in summaries),
        retrospective_understanding_claim_permitted=False,
        schema='verified_feedback_independent_content_v1', content_replay_passed=True,
        lifecycle_certified=False, outcome_claim_permitted=False, decisions=rows, conditions=summaries,
        generations=len(calls), policy_generations=len(responses), bootstrap_resets=resets,
        prefix_dispatches=prefix_dispatches, continuation_dispatches=new_dispatches,
        local_scorecards=closes, offline_actions_including_bootstraps=resets+dispatches,
        scheduled_candidate_forecasts=64, correct_candidate_forecasts=sum(r['candidate_forecasts_correct'] for r in rows),
        prompt_tokens=sum(c['usage']['prompt_tokens'] for c in calls),
        completion_tokens=sum(c['usage']['completion_tokens'] for c in calls),
        native_tokens_independently_rechecked=True,
        qualification='Scripted dependencies establish software behavior only; live outcome certification additionally requires exact package, provider completion and finalization witnesses.')
