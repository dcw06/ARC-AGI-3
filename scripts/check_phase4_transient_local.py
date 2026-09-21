"""CPU lifecycle and actual development-game checks; scripted, not model evidence."""
import hashlib,json,signal,sys,tempfile,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from certification.phase4_transient_v1.pilot import run
from certification.phase4_transient_v1.replay import replay
from certification.phase4_transient_v1.worker import run_cases
from certification.phase4_transient_v1.trajectory import evaluate_trajectories
from certification.phase4_transient_v1.fixtures import ScriptedService
from certification.phase4_transient_v1.evidence import EvidenceStore

def main():
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('CPU validation ceiling')))
    signal.setitimer(signal.ITIMER_REAL,360)
    with tempfile.TemporaryDirectory(prefix='transient-local-') as folder:
        base=Path(folder);output=base/'smoke'
        report,result=run(output,ROOT,mode='local',seconds=120,reserve=10)
        independent=replay(output,live=False,seconds=120)
        if not independent['passed']:raise ValueError(independent['errors'])
        from arc_agi import Arcade,OperationMode
        from agent.framework_adapter import LocalFrameworkAdapter
        manifest=json.loads((ROOT/'reports/phase4_v2_offline_package.json').read_bytes())
        games=base/'games'
        with zipfile.ZipFile(ROOT/'evidence/phase4-v2-development-offline.zip') as z:
            for name,info in manifest['files'].items():
                if not name.startswith('environment_files/'):continue
                raw=z.read(name)
                if len(raw)!=info['bytes'] or hashlib.sha256(raw).hexdigest()!=info['sha256']:raise ValueError('game hash')
                target=games/name.removeprefix('environment_files/')
                if not target.resolve().is_relative_to(games.resolve()):raise ValueError('game path')
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        actual=base/'actual';store=EvidenceStore(actual,'worker')
        def factory(row):
            arcade=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(games),recordings_dir=str(base/row['episode_id']))
            return LocalFrameworkAdapter(arcade,seed_by_game={row['game_id']:0})
        started=time.monotonic()
        state=run_cases(ScriptedService(),store,factory,started=started,deadline=started+180,
            cancel=actual/'control/cancel.json',live=False)
        comparison=evaluate_trajectories(state,actual/'worker',seconds=200)
        receipt={'scope':'scripted CPU fixtures and actual development engine, not model performance',
            'passed':True,'smoke_passed':independent['passed'],'smoke_elapsed_seconds':report['elapsed_seconds'],
            'cleanup_verified':report['cleanup_verified'],'scratch_removed':report['scratch_removed'],
            'actual_engine_requests':state['requests_started'],'actual_engine_episodes':len(state['episodes']),
            'actual_engine_seconds':time.monotonic()-started,'comparison':comparison,'model_inference':False}
        archive=ROOT/'evidence/phase4-transient-v1-local.zip'
        with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
            for path in sorted(base.rglob('*')):
                if path.is_file() and (path.is_relative_to(output) or path.is_relative_to(actual)):
                    z.write(path,path.relative_to(base))
        receipt.update(archive=archive.relative_to(ROOT).as_posix(),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    signal.setitimer(signal.ITIMER_REAL,0)
    (ROOT/'reports/phase4_transient_v1_local.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
    print(json.dumps({k:v for k,v in receipt.items() if k!='comparison'}))

if __name__=='__main__':main()
