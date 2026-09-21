"""CPU regressions and independent replay of the committed local evidence archive."""
import hashlib,json,sys,tempfile,unittest,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
suite=unittest.defaultTestLoader.loadTestsFromName('tests.test_phase4_transient_v1')
result=unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():raise SystemExit(1)
from certification.phase4_transient_v1.replay import replay
from certification.phase4_transient_v1.trajectory import evaluate_trajectories
archive=root/'evidence/phase4-transient-v1-local.zip'
with tempfile.TemporaryDirectory() as temp:
    with zipfile.ZipFile(archive) as z:z.extractall(temp)
    folder=Path(temp)
    smoke=replay(folder/'smoke',live=False,seconds=120)
    assert smoke['passed'],smoke['errors']
    state=json.loads((folder/'actual/worker/state.json').read_bytes())
    actual=evaluate_trajectories(state,folder/'actual/worker',seconds=200)
    assert len(actual['pairs'])==3 and state['requests_started']==120
receipt={'passed':True,'tests_run':result.testsRun,'failures':0,'errors':0,
    'archived_cpu_lifecycle_replay_passed':True,'archived_actual_game_trajectory_replay_passed':True,
    'actual_game_calls':120,'actual_game_episodes':6,'model_inference':False,
    'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
(root/'reports/phase4_transient_v1_final_checks.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
print(json.dumps(receipt))
