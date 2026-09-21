"""Read-only offline replay of archived v2 evidence; no credentials or GPU needed."""
import argparse,hashlib,json,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
LOCK='notebooks/phase4-transient-v2-review-r1/review-source-lock.json'
LOCK_SHA='5e0341ec0bd14a1b8ca054ff3df678ea71344d41ccd941058881253c7c8be842'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(path):return json.loads(path.read_bytes())

def inspect(output):
    from certification.phase4_transient_v2.independent_selection import expected
    worker=output/'worker';state=read(worker/'state.json');episodes=[];pairs={}
    for ep in state['episodes']:
        steps=[read(worker/n) for n in ep['steps']];previous=None;exposures=[]
        for index,step in enumerate(steps):
            selected=expected(previous)
            payload=json.loads(step['request']['messages'][1]['content'])['observation']
            if ep['arm']=='transient':assert payload['last_transition_intermediate_grid']==selected
            else:assert 'last_transition_intermediate_grid' not in payload
            if selected is not None:
                exposures.append({'decision_index_zero_based':index,'selected_frame_index':selected['frame_index_zero_based'],
                    'returned_frame_count':selected['returned_frame_count'],'action':step['action'],
                    'repeats_previous_action':index>0 and step['action']==steps[index-1]['action']})
            previous=(read(worker/step['pre']),read(worker/step['post']))
        episodes.append({'episode_id':ep['episode_id'],'arm':ep['arm'],'pair_index':ep['pair_index'],
            'eligible_nonnull_requests':len(exposures),'actually_exposed_requests':len(exposures) if ep['arm']=='transient' else 0,
            'repeats_after_eligible_frame':sum(x['repeats_previous_action'] for x in exposures),'exposures':exposures})
        pairs.setdefault(ep['pair_index'],{})[ep['arm']]=steps
    comparisons=[]
    for pair,arms in sorted(pairs.items()):
        rows=[]
        for index,(control,treatment) in enumerate(zip(arms['control'],arms['transient'])):
            payload=json.loads(treatment['request']['messages'][1]['content'])
            exposed=payload['observation'].pop('last_transition_intermediate_grid') is not None
            baseline=json.loads(control['request']['messages'][1]['content'])
            rows.append({'decision_index_zero_based':index,'transient_exposed':exposed,
                'same_action':control['action']==treatment['action'],
                'same_observation_without_field':baseline==payload})
        comparisons.append({'pair_index':pair,'decisions':rows})
    return {'episodes':episodes,'pairs':comparisons,
        'interpretation_limit':'Observed decisions only; matched step indices after diverging actions are not a controlled causal counterfactual.'}

def run():
    lock=read(ROOT/LOCK);assert sha((ROOT/LOCK).read_bytes())==LOCK_SHA,'review lock drift'
    for name,digest in lock['bindings'].items():assert sha((ROOT/name).read_bytes())==digest,name
    for name,digest in lock['artifacts'].items():assert sha((ROOT/LOCK).parent.joinpath(name).read_bytes())==digest,name
    manifest=read(ROOT/'reports/phase4_transient_v2_archive.json');archive=ROOT/manifest['archive']
    assert sha(archive.read_bytes())==manifest['sha256'] and archive.stat().st_size==manifest['bytes'],'archive drift'
    with tempfile.TemporaryDirectory(prefix='tf2-replay-') as tmp:
        folder=Path(tmp);expected={r['path']:r for r in manifest['files']}
        with zipfile.ZipFile(archive) as z:
            assert len(z.namelist())==len(expected) and set(z.namelist())==set(expected),'archive inventory'
            for name,row in expected.items():
                target=(folder/name).resolve();assert target.is_relative_to(folder.resolve()),'unsafe archive path'
                raw=z.read(name);assert len(raw)==row['bytes'] and sha(raw)==row['sha256'],name
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        downloaded=read(folder/'receipts/phase4_transient_v2_download.json')
        assert downloaded==read(ROOT/'reports/phase4_transient_v2_download.json'),'download manifest drift'
        for row in downloaded['files']:
            raw=(folder/'download'/row['path']).read_bytes()
            assert len(raw)==row['bytes'] and sha(raw)==row['sha256'],row['path']
        reservation=folder/'receipts/phase4_transient_v2_reservation.json'
        assert reservation.read_bytes()==(ROOT/'config/phase4_transient_v2_reservation.json').read_bytes()
        assert read(reservation)['status']=='consumed'
        from certification.phase4_transient_v2.replay import replay
        output=folder/'download/phase4-transient-v2'
        result=replay(output,live=True,seconds=3300)
        assert result['passed'],result['errors']
        inspection=inspect(output)
        observations=[json.loads(s) for s in (folder/'provider-observations.jsonl').read_text().splitlines()]
        before=read(folder/'receipts/phase4_transient_v2_pilot_prelaunch.json')['gpu_quota_seconds']
        after=observations[-1]['gpu_quota_seconds']
        accounting={'reserved_seconds':3600,'reservation_status':'consumed','automatic_retry_authorized':False,
            'notebook_elapsed_seconds':read(output/'evaluation/notebook-result.json')['elapsed_seconds'],
            'account_usage_before_seconds':before['time_used'],'account_usage_after_seconds':after['time_used'],
            'account_usage_delta_seconds':round(after['time_used']-before['time_used'],6),
            'provider_reserved_seconds_at_last_observation':after['time_reserved'],
            'provider_last_status':observations[-1]['status'],'exact_provider_billed_seconds':None,
            'limitations':['Account-level quota delta is not an attempt-specific invoice.',
                'Raw usage duration is malformed; raw allowance disagrees with SDK conversion.',
                'Queue observations do not establish exact GPU start or finish time.',
                'Unused nominal reservation is not new spending authority.']}
        return {'passed':True,'review_lock_sha256':LOCK_SHA,'source_bindings_verified':len(lock['bindings']),
            'archive_sha256':manifest['sha256'],'downloaded_files_verified':len(downloaded['files']),
            'archive_files_verified':len(expected),'replay':result,'decision_inspection':inspection,'accounting':accounting,
            'disposition':'No demonstrated solving improvement in this bounded comparison; not proof the capability can never help.',
            'phase4_complete':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args()
    result=run();raw=json.dumps(result,indent=2)+'\n'
    if args.output:args.output.write_text(raw)
    print(json.dumps({k:v for k,v in result.items() if k not in ('replay','decision_inspection')},indent=2))
