"""CPU-only actual development-engine integration with scripted actions, not solving evidence."""
import argparse,json,signal,tempfile,time,zipfile
from pathlib import Path
from arc_agi import Arcade,OperationMode
from agent.framework_adapter import LocalFrameworkAdapter
from certification.phase4_closed_loop_v1.evidence import EvidenceStore
from certification.phase4_closed_loop_v1.game_assets import stage_games
from certification.phase4_closed_loop_v1.worker import run_cases
from certification.phase4_closed_loop_v1.fixtures import ScriptedService
from certification.phase4_closed_loop_v1.trajectory import evaluate_trajectories
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--games',type=Path,required=True)
    args=parser.parse_args()
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('CPU engine check ceiling')))
    signal.setitimer(signal.ITIMER_REAL,360)
    with tempfile.TemporaryDirectory(prefix='closed-loop-games-') as tmp:
        path=Path(tmp);output=path/'output';store=EvidenceStore(output,'worker')
        stage_games(args.games,path/'games',json.loads((ROOT/'reports/phase4_v2_offline_package.json').read_text()))
        def factory(row):
            arcade=Arcade(operation_mode=OperationMode.OFFLINE,environments_dir=str(path/'games'),recordings_dir=str(path/row['episode_id']))
            return LocalFrameworkAdapter(arcade,seed_by_game={row['game_id']:row['environment_seed']})
        started=time.monotonic()
        state=run_cases(ScriptedService(),store,factory,started=started,deadline=started+300,
            cancel=output/'control/cancel.json',live=False)
        comparison=evaluate_trajectories(state,output/'worker',seconds=360)
        receipt={'scope':'actual local game engines with scripted CPU actions; not model evidence',
            'passed':True,'episodes':len(state['episodes']),'requests_started':state['requests_started'],
            'elapsed_seconds':time.monotonic()-started,'model_inference':False,'comparison':comparison}
        with zipfile.ZipFile(ROOT/'evidence/phase4-closed-loop-v1-local-games.zip','x',zipfile.ZIP_DEFLATED) as z:
            for p in sorted(output.rglob('*')):
                if p.is_file():z.write(p,p.relative_to(output))
    signal.setitimer(signal.ITIMER_REAL,0)
    (ROOT/'reports/phase4_closed_loop_v1_local_games.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='comparison'}))

if __name__=='__main__':main()
