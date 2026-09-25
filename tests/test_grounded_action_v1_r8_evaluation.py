"""R8 evaluator deadline repair: original evidence passes; invalid timing evidence fails."""
import hashlib,json,tempfile,unittest,zipfile
from pathlib import Path
from scripts import archive_grounded_action_v1_r8 as archive
from scripts.evaluate_grounded_action_v1_r8 import evaluate,within_deadline

PREFIX='reports/runs/phase4-grounded-action-v1-r8/download'
INVALID={'missing':None,'string':'562.2','bool':True,'nan':float('nan'),'infinite':float('inf'),
         'negative':-1.0,'at_limit':3300,'over_limit':3300.001}

def extract(folder):
    lock=json.loads(archive.LOCK.read_bytes())
    with zipfile.ZipFile(archive.ROOT/lock['archive']) as bundle:
        for name in lock['members']:
            path=folder/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(bundle.read(name))
    return lock

def mutate(folder,member,key,value):
    """Change one retained JSON field and re-hash the manifest so only the timing rule can reject it."""
    path=folder/PREFIX/'phase4-grounded-action-v1'/member;data=json.loads(path.read_bytes())
    if value is None:data.pop(key)
    else:data[key]=value
    raw=json.dumps(data,allow_nan=True).encode();path.write_bytes(raw)
    manifest_path=folder/'reports/perception_stage_b_r8_download.json';manifest=json.loads(manifest_path.read_bytes())
    for row in manifest['files']:
        if row['path']=='phase4-grounded-action-v1/'+member:row.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    manifest_path.write_text(json.dumps(manifest))

def run(folder):
    return evaluate(download=folder/PREFIX,manifest_path=folder/'reports/perception_stage_b_r8_download.json',record_root=folder)

class DeadlineRuleTests(unittest.TestCase):
    def test_rule(self):
        for value in (0,0.0,562.197766555,3299.999):self.assertTrue(within_deadline(value),value)
        for name,value in INVALID.items():
            with self.subTest(name=name):self.assertFalse(within_deadline(value))

class ArchivedEvidenceTests(unittest.TestCase):
    def test_original_archive_passes_unchanged(self):
        before=archive.ARCHIVE.read_bytes()
        result=archive.replay()
        self.assertEqual(result['evaluation_status'],'verified_complete_development_pair')
        self.assertEqual(archive.ARCHIVE.read_bytes(),before)
    def test_invalid_first_cell_and_supervisor_timing_fail(self):
        for member,key,reason in (('control/notebook-cost.json','elapsed_seconds','first-cell deadline'),
                                  ('control/outer.json','elapsed_seconds','supervisor deadline/cleanup')):
            for name,value in INVALID.items():
                with self.subTest(member=member,case=name),tempfile.TemporaryDirectory() as tmp:
                    folder=Path(tmp);extract(folder);mutate(folder,member,key,value)
                    with self.assertRaises(ValueError) as caught:run(folder)
                    self.assertEqual(str(caught.exception),reason)

if __name__=='__main__':unittest.main()
