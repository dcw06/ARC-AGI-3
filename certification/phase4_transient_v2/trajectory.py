"""Reconstruct requests and progress from retained trajectories, not worker summaries."""
import hashlib,json,math
from pathlib import Path
from agent.state import GameRuntimeState
from agent.action import ActionDecision,serialize_action
from arcengine import GameState
from certification.phase4_transient_v2.contract import protocol,unpack,digest,request_for
from certification.phase4_transient_v2.action_contract import validate_action

def evaluate_trajectories(worker,folder,*,seconds=3300):
    folder=Path(folder);expected={'state.json'};initial={};summaries=[];seen_cards=set();seen_decisions=set()
    def read(name):
        if Path(name).name!=name or not name.endswith('.json'):raise ValueError('unsafe evidence name')
        path=folder/name
        if path.is_symlink() or path.stat().st_size>1024**2:raise ValueError('invalid evidence record')
        expected.add(name)
        return json.loads(path.read_text())
    def observation(name):
        value=read(name)
        if name!='obs-'+digest(value)+'.json':raise ValueError('content-addressed observation drift')
        from certification.phase4_transient_v2.independent_selection import expected as expected_frame
        expected_frame((value,value))
        return unpack(value)
    def journal(entry,kind):
        if entry['kind']!=kind or entry['status']!='acknowledged':raise ValueError('journal outcome')
    def timestamp(value):
        if type(value) not in (float,int) or not math.isfinite(value) or not 0<=value<seconds:raise ValueError('timestamp')
        return value
    rows=protocol()['schedule'];episodes=worker['episodes']
    if len(episodes)!=len(rows):raise ValueError('incomplete pairs')
    calls=0;last_end=worker['request_window_started_seconds']
    for row,ep in zip(rows,episodes):
        if any(ep.get(k)!=v for k,v in row.items()):raise ValueError('schedule/seed/arm binding')
        if any(type(ep[k]) is not int for k in ('environment_seed','request_seed','max_decisions','max_dispatch_attempts')):
            raise ValueError('schedule numeric types')
        if ep['status']!='complete' or ep['error'] is not None or ep['client_closed'] is not True:raise ValueError('episode completion')
        if ep['scorecard_id'] in seen_cards or not ep['scorecard_id']:raise ValueError('scorecard isolation')
        seen_cards.add(ep['scorecard_id'])
        if ep['scorecard_receipt']['card_id']!=ep['scorecard_id']:raise ValueError('scorecard finalization binding')
        lifecycle=ep['lifecycle_journal']
        if len(lifecycle)!=2:raise ValueError('lifecycle count')
        journal(lifecycle[0],'scorecard_open');journal(lifecycle[1],'scorecard_close')
        if (lifecycle[0]['fields']['card_id']!=ep['scorecard_id']
            or lifecycle[1]['prepared_fields']['card_id']!=ep['scorecard_id']):raise ValueError('lifecycle identity')
        if not last_end<=timestamp(ep['started_seconds'])<=timestamp(ep['ended_seconds'])<=worker['ended_seconds']:
            raise ValueError('episode order/deadline')
        last_end=ep['ended_seconds'];obs=observation(ep['initial_observation'])
        if obs.game_id!=row['game_id']:raise ValueError('game binding')
        key=(row['game_id'],row['pair_index'])
        if key in initial and initial[key]!=obs.canonical_hash:raise ValueError('initial-state inequality')
        initial[key]=obs.canonical_hash
        previous_transition=None
        history=GameRuntimeState(obs,action_budget_limit=20);base=obs.levels_completed
        entries=ep['client_journal'];steps=ep['steps'];n=len(steps)
        if n>20 or len(entries)!=n+1 or len(set(steps))!=n:raise ValueError('episode action/bootstrap count')
        journal(entries[0],'bootstrap_reset')
        if (entries[0]['prepared_fields']['requested_game_id']!=row['game_id']
            or entries[0]['prepared_fields']['scorecard_id']!=ep['scorecard_id']
            or entries[0]['fields']['observation_hash']!=obs.canonical_hash
            or entries[0]['fields']['guid']!=obs.guid):raise ValueError('bootstrap binding')
        actions=[];unchanged=[];frame_unchanged=[];progress=[];previous_time=ep['started_seconds']
        for index,name in enumerate(steps):
            step=read(name);calls+=1
            if step['episode_id']!=row['episode_id'] or step['step']!=index or step['status']!='acknowledged':raise ValueError('step identity/status')
            if step['decision_id']!=row['episode_id']+f'-{index}' or step['decision_id'] in seen_decisions:raise ValueError('decision identity')
            seen_decisions.add(step['decision_id'])
            before=observation(step['pre'])
            if before.canonical_hash!=obs.canonical_hash or before.guid!=obs.guid:raise ValueError('trajectory discontinuity')
            if obs.state in (GameState.WIN,GameState.GAME_OVER):raise ValueError('dispatch after terminal')
            from certification.phase4_transient_v2.independent_selection import verify_request
            verify_request(step['request'],history,row,previous_transition)
            if step['request_sha256']!=digest(step['request']):raise ValueError('request hash')
            raw=step['response_content'].encode()
            if step['response_truncated'] is not False or len(raw)>8192 or len(raw)!=step['response_bytes'] or hashlib.sha256(raw).hexdigest()!=step['response_sha256']:raise ValueError('response evidence')
            audit=step['audit']
            for key in ('tokenizer_prompt_tokens','server_prompt_tokens','server_completion_tokens'):
                if type(audit[key]) is not int:raise ValueError('token type')
            if (audit['request_sha256']!=step['request_sha256'] or not 0<audit['server_prompt_tokens']<=65408
                or audit['server_prompt_tokens']!=audit['tokenizer_prompt_tokens']
                or not 1<=audit['server_completion_tokens']<=128
                or not 0<=timestamp(audit['service_seconds'])<180):raise ValueError('token audit')
            action=validate_action(step['response_content'],obs.available_actions)['action']
            if step['action']!=action:raise ValueError('response/action binding')
            sequence=[timestamp(step[k]) for k in ('started_seconds','returned_seconds','dispatch_seconds','ack_seconds')]
            if not previous_time<=sequence[0]<=sequence[1]<=sequence[2]<=sequence[3]<=ep['ended_seconds']:raise ValueError('step order')
            if sequence[3]>=worker['request_window_cutoff_seconds']:raise ValueError('late dispatch')
            previous_time=sequence[-1];entry=entries[index+1];journal(entry,'action')
            if entry!=step['journal']:raise ValueError('journal copy mismatch')
            decision=ActionDecision(**action,source='closed_loop_model',decision_id=step['decision_id'])
            wire=serialize_action(decision,game_id=obs.game_id,guid=obs.guid,legal_actions=obs.available_actions)
            fields=entry['prepared_fields']
            if (fields['decision_id']!=step['decision_id'] or fields['action_id']!=action['action_id']
                or fields['pre_state_hash']!=obs.canonical_hash or fields['payload_sha256']!=wire.payload_sha256):raise ValueError('dispatch binding')
            post=observation(step['post'])
            from certification.phase4_transient_v2.independent_selection import expected as expected_frame
            expected_frame((read(step['pre']),read(step['post'])))
            if (post.guid!=obs.guid or post.game_id!=obs.game_id or post.full_reset
                or entry['fields']['post_state_hash']!=post.canonical_hash
                or not obs.levels_completed<=post.levels_completed<=post.win_levels
                or post.win_levels!=obs.win_levels):raise ValueError('post-state/progress binding')
            actions.append(action);unchanged.append(post.canonical_hash==obs.canonical_hash)
            frame_unchanged.append(bool((post.latest_frame.shape==obs.latest_frame.shape) and (post.latest_frame==obs.latest_frame).all()))
            if post.levels_completed>obs.levels_completed:progress.append({'step':index+1,'level_delta':post.levels_completed-obs.levels_completed,'seconds':sequence[-1]-ep['started_seconds']})
            history.counters.conservative_spent_actions+=1
            history.replace_observation(post,action_id=action['action_id'],action_data=action['action_data'],transition_id=step['decision_id'])
            previous_transition=(read(step['pre']),read(step['post']))
            obs=post
        final=observation(ep['final_observation'])
        if final.canonical_hash!=obs.canonical_hash or final.guid!=obs.guid:raise ValueError('final observation')
        reason='win' if obs.state==GameState.WIN else 'game_over' if obs.state==GameState.GAME_OVER else 'action_cap'
        if ep['terminal_reason']!=reason or reason=='action_cap' and n!=20:raise ValueError('incomplete episode')
        streak=longest=0;repeat=after_noop=0
        for i,a in enumerate(actions):
            same=i>0 and a==actions[i-1];streak=streak+1 if same else 1;longest=max(longest,streak)
            repeat+=int(same);after_noop+=int(bool(same and unchanged[i-1]))
        summaries.append({'pair_index':row['pair_index'],'request_seed':row['request_seed'],'game_id':row['game_id'],'arm':row['arm'],'actions':n,'level_delta':obs.levels_completed-base,
            'terminal_reason':reason,'progress_events':progress,'canonical_change_rate':None if not n else 1-sum(unchanged)/n,
            'frame_change_rate':None if not n else 1-sum(frame_unchanged)/n,'adjacent_repeats':repeat,
            'repeat_rate':None if n<2 else repeat/(n-1),'longest_streak':longest,'repeats_after_unchanged':after_noop,
            'action_distribution':{str(k):sum(a['action_id']==k for a in actions) for k in range(1,8)},
            'click_coordinates':[a['action_data'] for a in actions if a['action_id']==6]})
    if (type(worker['requests_started']) is not int or type(worker['dispatch_attempts']) is not int
        or calls!=worker['requests_started'] or calls!=worker['dispatch_attempts'] or calls>120):raise ValueError('global budget/inventory')
    if (folder/'model-ready.json').exists():expected.add('model-ready.json')
    if {p.name for p in folder.iterdir() if p.is_file()}!=expected:raise ValueError('unreferenced/missing evidence')
    pairs=[]
    for game,pair_index in sorted(initial):
        arms={s['arm']:s for s in summaries if s['game_id']==game and s['pair_index']==pair_index}
        pairs.append({'pair_index':pair_index,'game_id':game,'level_delta_difference':arms['transient']['level_delta']-arms['control']['level_delta'],'arms':arms})
    return {'episodes':summaries,'pairs':pairs,'paired_level_wins':sum(p['level_delta_difference']>0 for p in pairs),
        'paired_level_ties':sum(p['level_delta_difference']==0 for p in pairs),'paired_level_losses':sum(p['level_delta_difference']<0 for p in pairs),
        'arms':{arm:{'completed_level_increase':sum(e['level_delta'] for e in summaries if e['arm']==arm),
                     'wins':sum(e['terminal_reason']=='win' for e in summaries if e['arm']==arm),
                     'game_overs':sum(e['terminal_reason']=='game_over' for e in summaries if e['arm']==arm),
                     'acknowledged_transitions':sum(e['actions'] for e in summaries if e['arm']==arm)}
                for arm in ('control','transient')},
        'interpretation':'20-action early-progress experiment; zero progress does not establish that the prompt change can never help'}
