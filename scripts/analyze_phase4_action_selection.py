"""Descriptive analysis of hash-verified archived actions; no inference or GPU calls."""
from collections import Counter,defaultdict
import hashlib,json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def sequence_metrics(actions):
    keys=[json.dumps({'action_id':a['action_id'],'action_data':a['action_data']},sort_keys=True) for a in actions]
    repeats=sum(a==b for a,b in zip(keys,keys[1:]))
    longest=run=0;previous=None
    for key in keys:
        run=run+1 if key==previous else 1
        longest=max(longest,run);previous=key
    return {'actions':len(keys),'adjacent_pairs':max(0,len(keys)-1),'adjacent_repeats':repeats,
            'distinct_actions':len(set(keys)),'longest_identical_run':longest}


def analyze(worker):
    clients=[]; counts=Counter();coordinates=Counter();by_game=defaultdict(list)
    for client in worker['clients']:
        actions=client['dispatch_audit']
        entries=[e for e in client['client_journal'] if e['kind']=='action']
        assert len(actions)==len(entries)
        metrics=sequence_metrics(actions)
        unchanged=0
        for action,entry in zip(actions,entries):
            assert action['outcome']=='acknowledged' and entry['status']=='acknowledged'
            assert entry['fields']['action_id']==action['action_id']
            assert entry['fields']['decision_id']==action['decision_id']
            assert entry['fields']['post_state_hash']==action['post_hash']
            unchanged+=entry['fields']['pre_state_hash']==entry['fields']['post_state_hash']
            counts[action['action_id']]+=1
            if action['action_id']==6:coordinates[(action['action_data']['x'],action['action_data']['y'])]+=1
        row={'client_id':client['client_id'],'game_id':client['game_id'],**metrics,
             'unchanged_canonical_hash_actions':unchanged,'levels_completed':client['result']['levels_completed'],
             'terminal_reason':client['result']['terminal_reason'],
             'action6_count':sum(a['action_id']==6 for a in actions)}
        clients.append(row);by_game[client['game_id']].append(row)
    samples=worker['prompt_samples']
    fingerprints=Counter();request_matches=0
    retained_requests=Counter((r['client_id'],r['request_sha256']) for r in worker['requests'])
    observations=[]
    for sample in samples:
        request=sample['request']
        digest=hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest()
        # Same serialization as the frozen worker's MeasuredCompletion.
        matches=retained_requests[(sample['client_id'],digest)]>0
        request_matches+=matches
        system=request['messages'][0]['content']
        fingerprints[hashlib.sha256(system.encode()).hexdigest()]+=1
        observation=json.loads(request['messages'][1]['content'])['observation']
        grid=observation['current_grid']
        observations.append({'client_id':sample['client_id'],'request_hash_matched':matches,
          'grid_height':len(grid),'grid_width':len(grid[0]) if grid else 0,
          'grid_sha256':hashlib.sha256(json.dumps(grid,separators=(',',':')).encode()).hexdigest(),
          'example_coordinate_color':grid[34][12] if len(grid)>34 and len(grid[34])>12 else None,
          'legal_actions':observation['legal_actions']})
    totals={key:sum(c[key] for c in clients) for key in ('actions','adjacent_pairs','adjacent_repeats','unchanged_canonical_hash_actions','levels_completed')}
    totals.update(clients=len(clients),distinct_games=len(by_game),
       single_action_clients=sum(c['distinct_actions']==1 for c in clients),
       longest_identical_run=max(c['longest_identical_run'] for c in clients),
       terminal_reasons=dict(Counter(c['terminal_reason'] for c in clients)))
    games=[]
    for game,group in sorted(by_game.items()):
        games.append({'game_id':game,'clients':len(group),**{k:sum(c[k] for c in group) for k in
           ('actions','adjacent_repeats','adjacent_pairs','action6_count','unchanged_canonical_hash_actions','levels_completed')},
           'single_action_clients':sum(c['distinct_actions']==1 for c in group),
           'terminal_reasons':dict(Counter(c['terminal_reason'] for c in group))})
    return {'totals':totals,'action_counts':dict(sorted(counts.items())),
      'click_coordinates':[{'x':x,'y':y,'count':n} for (x,y),n in coordinates.most_common()],
      'clients':clients,'games':games,'prompt_sample_count':len(samples),
      'prompt_samples_omitted':worker['prompt_samples_omitted'],'sample_request_hash_matches':request_matches,
      'system_prompt_hashes':dict(fingerprints),'sample_observations':observations}


def main():
    receipt=json.loads((ROOT/'reports/phase4_v13_pilot_evaluation.json').read_text())
    archive=ROOT/receipt['evidence_archive']
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==receipt['evidence_archive_sha256']
    name='download/phase4-development-v13/worker/state.json'
    with zipfile.ZipFile(archive) as z:data=z.read(name)
    digest=hashlib.sha256(data).hexdigest()
    assert digest==receipt['evidence'][name]['sha256']
    worker=json.loads(data);result=analyze(worker)
    assert result['sample_request_hash_matches']==result['prompt_sample_count']
    result.update(scope='offline_descriptive_action_selection_analysis',configuration='E1S-R-derived arc_action_v12',
      archive_sha256=receipt['evidence_archive_sha256'],worker_sha256=digest,
      script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),new_model_calls=0,
      limitations=['Full raw successful responses and per-step grids were not retained.',
       'Canonical-hash changes are not proof of visual progress or meaningful action effect.',
       'Prompt samples are the first retained completions, not a random or full-trajectory sample.',
       'Association with prompt examples does not establish causation.'])
    path=ROOT/'reports/phase4_action_selection_analysis.json'
    with path.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k in ('totals','action_counts','click_coordinates','prompt_sample_count','sample_request_hash_matches')},indent=2))


if __name__=='__main__':main()
