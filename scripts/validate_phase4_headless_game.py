"""Real offline game install with a sibling isolated interpreter, no model/GPU."""
import json
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from certification.phase4_v6.clean_environment import CleanEnvironment, ENVIRONMENT_PINS, verify_environment_wheels
from certification.phase4_v6.target_install_probe_r4 import GAME_CHECK

from certification.phase4_v6.headless_environment import HeadlessEnvironment
CleanEnvironment=HeadlessEnvironment
import os
os.environ['MPLBACKEND']='module://matplotlib_inline.backend_inline'
output=ROOT/'reports/runs/phase4-headless-game-local'
wheels=ROOT/'reports/runs/phase4-v2-assets/arc_agi_3_wheels'
manifest=json.loads((ROOT/'reports/phase4_v2_offline_package.json').read_text())
count=verify_environment_wheels(wheels,manifest)
with tempfile.TemporaryDirectory(prefix='p4-split-local-') as folder:
    scratch=Path(folder)
    for role in ('model-placeholder','game'):
        (scratch/role).mkdir()
    empty=CleanEnvironment(scratch/'model-placeholder',output/'model-placeholder',host_python='/usr/bin/python3')
    game=CleanEnvironment(scratch/'game',output/'game',host_python='/usr/bin/python3')
    empty.bootstrap()
    game.bootstrap()
    game.install('install_game',wheels,ENVIRONMENT_PINS)
    game.check()
    game.execute('game_runtime_and_isolation',[game.python,'-I','-c',GAME_CHECK])
    empty.execute('sibling_remains_empty',[empty.python,'-I','-c',
        'import importlib.metadata as m; assert not list(m.distributions())'])
summary={'inherited_backend':'module://matplotlib_inline.backend_inline','child_backend':game.env['MPLBACKEND'],'passed':True,'verified_game_wheels':count,'game_imports_and_dependency_check_passed':True,
         'sibling_environment_remained_empty':True,'scratch_removed':not scratch.exists(),
         'model_service_installed':False,'cuda_verified':False,'gpu_run_launched':False}
(ROOT/'reports/phase4_headless_game_local.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
