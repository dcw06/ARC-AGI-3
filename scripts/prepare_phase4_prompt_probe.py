"""Prepare an unexecuted, paired initial-decision probe from archived prompts."""
import copy,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def variants(request):
    original=request['messages'][0]['content']
    click='Valid ACTION6 shape: {"action":{"action_id":6,"action_data":{"x":12,"y":34}}}. '
    note='These coordinates illustrate the format; choose coordinates from the observation. '
    simple='For actions 1,2,3,4,5,7 use empty action_data, for example {"action":{"action_id":1,"action_data":{}}}. '
    assert all(original.count(s)==1 for s in (click,note,simple))
    texts={'baseline':original,
      'relocated_example':original.replace('"x":12,"y":34','"x":47,"y":9'),
      'no_concrete_examples':original.replace(click,'').replace(note,'').replace(simple,'For actions 1,2,3,4,5,7 use empty action_data. ')}
    result={}
    for name,text in texts.items():
        value=copy.deepcopy(request);value['messages'][0]['content']=text
        result[name]=value
    return result


def main():
    receipt=json.loads((ROOT/'reports/phase4_v13_pilot_evaluation.json').read_text())
    archive=ROOT/receipt['evidence_archive']
    sha=lambda b:hashlib.sha256(b).hexdigest()
    assert sha(archive.read_bytes())==receipt['evidence_archive_sha256']
    with zipfile.ZipFile(archive) as z:raw=z.read('download/phase4-development-v13/worker/state.json')
    assert sha(raw)==receipt['evidence']['download/phase4-development-v13/worker/state.json']['sha256']
    worker=json.loads(raw);games={c['client_id']:c['game_id'] for c in worker['clients']}
    selected={}
    for i,sample in enumerate(worker['prompt_samples']):
        game=games[sample['client_id']]
        observation=json.loads(sample['request']['messages'][1]['content'])['observation']
        assert observation['history_compaction']['total_transitions']==0
        if game not in selected:selected[game]=(i,sample)
    assert len(selected)==15
    cases=[]
    # Rotate arm order across games to balance a later sequential serving probe.
    names=['baseline','relocated_example','no_concrete_examples']
    for index,(game,(i,sample)) in enumerate(sorted(selected.items())):
        arms=variants(sample['request']);order=names[index%3:]+names[:index%3]
        for arm in order:
            request=arms[arm]
            cases.append({'game_id':game,'arm':arm,'source_sample_index':i,'source_client_id':sample['client_id'],
              'request':request,'request_sha256':sha(json.dumps(request,sort_keys=True).encode())})
    manifest={'status':'prepared_not_authorized_not_executed','scope':'paired_initial_decision_prompt_example_probe',
      'model_calls_authorized':0,'gpu_seconds_authorized':0,'planned_maximum_calls':45,
      'maximum_completion_tokens_per_call':128,'planned_maximum_completion_tokens':5760,
      'automatic_retries':0,'environment_actions':0,'historical_configuration':'E1S-R-derived arc_action_v12',
      'archive_sha256':receipt['evidence_archive_sha256'],'cases':cases}
    output=ROOT/'reports/phase4_action_selection_probe_proposal.json'
    with output.open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2)
    print(json.dumps({'cases':len(cases),'games':len(selected),'status':manifest['status']}))


if __name__=='__main__':main()
