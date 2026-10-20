"""Independent retained-evidence replay and evaluation-only counterfactual scoring.

Fresh CPU engines must be supplied. No model inference or provider operation is
performed here. Reference outcomes never enter the inference payload.
"""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

from research.action_effect_choice_v1.flow import run_case, reference_branch
from research.action_effect_choice_v1.interface import parse_choice
from research.action_effect_choice_v1.scoring import branch_key, effect_size, score
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_io import sha
from research.recent_feedback_v1.audit import baseline_request
from .live_contract import check_checkpoints, verify_inputs
from .live_worker import canary, request_plan


def audit_case(cp, pair, variant, events, replay_engine):
    """Rebuild every prompt and full transition; never trust terminal labels."""
    emitted, originals = [], [e for e in events if e.get('kind') == 'request']
    texts = [e['text'] for e in events if e.get('kind') == 'response']
    position = 0

    def complete(body):
        nonlocal position
        if position >= len(originals) or position >= len(texts):
            raise ValueError('missing retained request/response')
        original = originals[position]
        if original.get('request_sha256') != digest(body) or digest(original.get('body')) != digest(body):
            raise ValueError('full reconstructed request differs')
        # Independent row/column arithmetic verifies the displayed summary.
        stripped = deepcopy(body)
        stripped['messages'][1]['content'].pop()  # frozen candidate extension
        stripped['messages'][0] = deepcopy(cp['base_request']['messages'][0])
        baseline_request(stripped, 'recent_summary')
        text = texts[position]
        position += 1
        return text

    result = run_case(cp, pair, variant, replay_engine, complete, emitted.append,
                      deadline=float('inf'), now=lambda: 0)
    if digest(emitted) != digest(events) or position != len(originals) or position != len(texts):
        raise ValueError('retained events/stop reason/final state differ from exact game replay')
    if result['reason'] in ('deadline', 'exception') or result['model_calls'] > 2:
        raise ValueError('incomplete condition or scope exceeded')
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
    prefix_dispatches = new_dispatches = 0
    for cp in checkpoints:
        identity, pair = cp['checkpoint_id'], pairs[cp['checkpoint_id']]
        for variant in cp['order']:
            name = identity+'-'+variant
            events = lines(output/(name+'.jsonl'))
            result = audit_case(cp, pair, variant, events, replay_factory(cp, name+'-replay'))
            summaries.append(result)
            prefix_dispatches += len(cp['prefix'])
            transitions = [e['record'] for e in events if e['kind'] == 'transition']
            texts = [e['text'] for e in events if e['kind'] == 'response']
            new_dispatches += len(transitions)
            for event in events:
                kind = event['kind']
                if kind == 'request':
                    request_id = identity+'/'+variant+'/'+str(event['decision'])
                    if request_id in expected: raise ValueError('duplicate condition decision')
                    expected[request_id] = event['body']
                    sequence.append(('HTTP', request_id))
                elif kind == 'response':
                    responses[identity+'/'+variant+'/'+str(event['decision'])] = event['text']
                elif kind in ('bootstrap_intent', 'restore_dispatch_intent', 'dispatch_intent', 'closed'):
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
                    if decision >= len(transitions) or not _same(
                            references[answer['selected_candidate']]['after'], transitions[decision]['after']):
                        raise ValueError('actual selected transition differs from fresh reference branch')
                    previous = answer
                rows.append({'checkpoint_id': identity, 'variant': variant, 'decision': decision,
                             'observed': True, 'stop_reason': result['reason'], 'reference_key': key,
                             'candidate_forecasts_scheduled': 2,
                             'candidate_forecasts_correct': sum(v['correct'] for v in scored['forecasts'].values()),
                             'score': scored, 'reference_records_sha256': digest(references)})
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
    wanted = dict(schema='action_effect_choice_worker_v1', error=None, conditions=summaries,
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
    if (resets != 16 or closes != 16 or prefix_dispatches != 36 or len(summaries) != 16 or len(rows) != 32 or
            not 0 <= new_dispatches <= 32 or dispatches != prefix_dispatches+new_dispatches or
            resets+dispatches > 84 or len(calls) != 1+len(responses) or len(calls) > 33 or
            any(c['id'] not in plan for c in calls)):
        raise ValueError('frozen schedule counts or scope differ')
    return dict(schema='action_effect_choice_independent_content_v1', content_replay_passed=True,
        lifecycle_certified=False, outcome_claim_permitted=False, decisions=rows, conditions=summaries,
        generations=len(calls), policy_generations=len(responses), bootstrap_resets=resets,
        prefix_dispatches=prefix_dispatches, continuation_dispatches=new_dispatches,
        local_scorecards=closes, offline_actions_including_bootstraps=resets+dispatches,
        scheduled_candidate_forecasts=64, correct_candidate_forecasts=sum(r['candidate_forecasts_correct'] for r in rows),
        prompt_tokens=sum(c['usage']['prompt_tokens'] for c in calls),
        completion_tokens=sum(c['usage']['completion_tokens'] for c in calls),
        native_tokens_independently_rechecked=True,
        qualification='Scripted dependencies establish software behavior only; live outcome certification additionally requires exact package, provider completion and finalization witnesses.')
