"""Replay the entire episode independently; supplied rules never earn discovery credit."""
import json
import math
from pathlib import Path
from research.initial_geometry_assistance_v1.geometry import digest
from .flow import run_episode
from .live_contract import verify_inputs
from .live_worker import canary

def audit_study(output,inputs,*,token_audit,replay_factory):
    from .live_evaluation import lines,audit_transport
    from research.initial_geometry_assistance_v1.live_io import sha
    output,inputs=Path(output),Path(inputs)
    verify_inputs(inputs,sha(inputs/'manifest.json'))
    initial=json.loads((inputs/'initial.json').read_bytes())
    instructions=(inputs/'instructions.txt').read_text(encoding='utf-8')
    events=lines(output/'ls20-six-move.jsonl');requests=[e for e in events if e['kind']=='request']
    replies=[e['text'] for e in events if e['kind']=='response'];emitted=[];position=0
    stop=[e for e in events if e['kind']=='admission_stop']
    if len(stop)>1:raise ValueError('multiple stop receipts')
    if stop and (set(stop[0])!={'kind','check_index','overrun_seconds'} or
        type(stop[0]['check_index']) is not int or stop[0]['check_index']<1 or
        type(stop[0]['overrun_seconds']) not in (int,float) or not math.isfinite(stop[0]['overrun_seconds']) or
        not 0<=stop[0]['overrun_seconds']<300):raise ValueError('admission-stop receipt differs')
    check_index=0
    def now():
        nonlocal check_index
        check_index+=1
        return stop[0]['overrun_seconds'] if stop and check_index==stop[0]['check_index'] else -1
    def complete(body):
        nonlocal position
        if position>=len(replies) or digest(body)!=requests[position]['request_sha256'] or digest(body)!=digest(requests[position]['body']):
            raise ValueError('full request reconstruction differs')
        text=replies[position];position+=1;return text
    result=run_episode(initial,instructions,replay_factory(),complete,emitted.append,deadline=0,now=now)
    if digest(events)!=digest(emitted) or position!=len(replies):raise ValueError('episode or stop reason differs from game replay')
    if result['error'] is not None:raise ValueError('episode technical error')
    expected={'canary':canary()}
    expected.update({'ls20/six_move/'+str(i):e['body'] for i,e in enumerate(requests[:len(replies)])})
    calls,effects=audit_transport(lines(output/'transport.jsonl'),expected,token_audit=token_audit)
    if [c['id'] for c in calls]!=list(expected) or calls[0]['content'].strip()!='ok':raise ValueError('HTTP schedule differs')
    if [c['content'] for c in calls[1:]]!=replies:raise ValueError('complete HTTP replies differ')
    wanted_sequence=[('HTTP','canary')]
    for index,e in enumerate(events):
        if e['kind']=='request' and e['step']<len(replies):wanted_sequence.append(('HTTP','ls20/six_move/'+str(e['step'])))
        mapping={'bootstrap_intent':('bootstrap','initial'),'dispatch_intent':('dispatch','transition'),'closed':('close',None)}
        if e['kind'] in mapping:
            operation,following=mapping[e['kind']]
            if following is None or (index+1<len(events) and events[index+1]['kind']==following):wanted_sequence.append(('engine',operation))
    sequence=[(c['transport_index'],('HTTP',c['id'])) for c in calls]
    totals=dict(bootstrap=0,dispatch=0,close=0)
    for e in effects:
        operation=e.get('operation')
        if operation not in totals:raise ValueError('engine effect differs')
        totals[operation]+=1
        wanted=dict(kind='engine_admission',episode='ls20-six-move',operation=operation,
            bootstrap_attempts=totals['bootstrap'],dispatch_attempts=totals['dispatch'],close_attempts=totals['close'],transport_index=e['transport_index'])
        if digest(e)!=digest(wanted):raise ValueError('engine counters differ')
        sequence.append((e['transport_index'],('engine',operation)))
    if [s for _,s in sorted(sequence)]!=wanted_sequence:raise ValueError('engine/HTTP order differs')
    worker=json.loads((output/'worker-result.json').read_bytes())
    wanted=dict(schema='ls20_six_move_worker_v1',error=None,episodes=[result],bootstrap_attempts=1,
                dispatch_attempts=result['new_dispatches'],close_attempts=1,lifecycle_certified=False)
    if set(worker)!=set(wanted)|{'ledger'} or any(digest(worker[k])!=digest(v) for k,v in wanted.items()):raise ValueError('worker totals differ')
    ledger=worker['ledger']
    if ledger['issued']!=len(calls) or ledger['maximum_model_requests']!=7 or ledger['refusals'] or len(ledger['entries'])!=len(calls):
        raise ValueError('request ledger differs')
    if (ledger['by_kind']!={'canary':1,'policy':len(replies)} or
        set(ledger)!={'maximum_model_requests','issued','by_kind','counting_rule','entries','refusals'} or
        type(ledger['issued']) is not int or type(ledger['maximum_model_requests']) is not int):
        raise ValueError('request ledger totals/types differ')
    for entry,call in zip(ledger['entries'],calls):
        wanted={k:v for k,v in call['admission'].items() if k not in ('kind','request_kind')}
        wanted.update(kind=call['admission']['request_kind'],outcome='http_200')
        if set(entry)!=set(wanted)|{'seconds'} or any(digest(entry[k])!=digest(v) for k,v in wanted.items()):raise ValueError('request entry differs')
        if type(entry['seconds']) not in (int,float) or not 0<=entry['seconds']<=30:raise ValueError('request time exceeds bound')
    if totals!={'bootstrap':1,'dispatch':result['new_dispatches'],'close':1}:raise ValueError('actual engine totals differ')
    from .live_contract import protocol
    frozen=protocol()
    transitions=[e['record'] for e in events if e['kind']=='transition']
    actions=[r['action']['action_id'] for r in transitions]
    states=[digest(r['after']) for r in transitions]
    commands_match=actions==frozen['expected_action_ids']
    states_match=states==frozen['expected_observation_sha256_by_step']
    return dict(command_following_success=commands_match,
        reference_execution_match=commands_match and states_match,
        executed_action_ids=actions,expected_action_ids=frozen['expected_action_ids'],
        observed_states_match_reference=states_match,
        study_schedule_complete=result['reason']!='deadline',episode=result,
        level1_passed=result['level1_passed'],policy_generations=len(replies),generations=len(calls),
        offline_actions_including_bootstraps=1+result['new_dispatches'],local_scorecards=1,
        rule_discovery_claim_permitted=False,route_was_supplied=True,
        prompt_tokens=sum(c['usage']['prompt_tokens'] for c in calls),
        completion_tokens=sum(c['usage']['completion_tokens'] for c in calls),
        outcome_claim_permitted=False,qualification='One explicitly supplied six-move route; no autonomous planning, rule-discovery or level-solving claim.')
