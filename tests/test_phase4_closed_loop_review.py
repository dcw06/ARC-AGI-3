import copy,hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from certification.phase4_closed_loop_v1.replay import replay
ROOT=Path(__file__).resolve().parents[1]

class ReviewTests(unittest.TestCase):
    def test_model_contract_has_no_game_dependencies(self):
        code='''import builtins,sys
sys.path.insert(0,sys.argv[1])
original=builtins.__import__
def guarded(name,*args,**kwargs):
    if name.split('.')[0] in ('arcengine','arc_agi','agent','numpy'):raise RuntimeError('game-side import: '+name)
    return original(name,*args,**kwargs)
builtins.__import__=guarded
from certification.phase4_closed_loop_v1.service import SharedModelService
from certification.phase4_closed_loop_v1.request_contract import protocol,validate_request
print(protocol()['pairs'])
'''
        result=subprocess.run([sys.executable,'-I','-c',code,str(ROOT)],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_finalization_receipts_independently_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('control','worker','evaluation','monitor'):(root/name).mkdir()
            def put(name,value):(root/name).write_text(json.dumps(value))
            put('control/outer.json',{});put('worker/state.json',{})
            put('evaluation/result.json',{'passed':True,'comparison':{}})
            put('control/notebook-cost.json',{'dependency_trees_removed':True,'error':None,'elapsed_seconds':100})
            cleanup={'gpu_cleanup_verified':True,'groups_absent':True,'error':None,'remaining_process_count':0}
            put('control/gpu-cleanup.json',cleanup)
            final={'passed':True,'completed':True,'source_removed':True,'error':None,'elapsed_seconds':101,
                'evaluation_sha256':hashlib.sha256((root/'evaluation/result.json').read_bytes()).hexdigest(),
                'cleanup_sha256':hashlib.sha256((root/'control/notebook-cost.json').read_bytes()).hexdigest()}
            put('evaluation/notebook-result.json',final)
            with patch('certification.phase4_closed_loop_v1.replay.evaluate',return_value={'passed':True,'errors':[],'comparison':{}}),patch('certification.phase4_closed_loop_v1.replay.read_telemetry',return_value={'samples':[]}):
                self.assertTrue(replay(root)['passed'])
                for key,value in [('source_removed',False),('completed',False),('elapsed_seconds',3300),('cleanup_sha256','wrong')]:
                    changed=copy.deepcopy(final);changed[key]=value;put('evaluation/notebook-result.json',changed)
                    self.assertFalse(replay(root)['passed'])
                put('evaluation/notebook-result.json',final)
                cleanup['gpu_cleanup_verified']=False;put('control/gpu-cleanup.json',cleanup)
                self.assertFalse(replay(root)['passed'])

if __name__=='__main__':unittest.main()
