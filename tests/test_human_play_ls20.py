import hashlib
import json
import tempfile
import unittest
import uuid
from pathlib import Path
from human_play.server import Store, STATIC, DEFAULT_GAMES, GAMES


@unittest.skipUnless((DEFAULT_GAMES/'ls20').is_dir(), 'prepare the public ls20 environment first')
class LS20(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.store=Store(logs_dir=Path(self.temp.name))
        self.s=self.store.create({'game_id':'ls20'})
        self.reference=json.loads((STATIC/'ls20-level1.json').read_text())

    def tearDown(self):
        self.temp.cleanup()

    def test_tenth_game_and_exact_initial_indices(self):
        self.assertEqual(len(GAMES),10)
        self.assertEqual(GAMES[-1],'ls20')
        f=self.s.current['frames'][-1]
        self.assertEqual(hashlib.sha256(json.dumps(f,separators=(',',':')).encode()).hexdigest(),self.reference['frame_sha256'])
        for o in self.reference['objects']:
            self.assertEqual(len(o['cells']),o['cell_count'])
            for c in o['cells']:
                self.assertEqual(c['row'],c['y']);self.assertEqual(c['column'],c['x'])
                self.assertEqual(c['index'],c['y']*64+c['x'])
                self.assertEqual(c['color_index'],f[c['y']][c['x']])
        self.assertEqual(self.s.export()['metadata']['objects_and_roles_reference'],self.reference)

    def test_control_collision_marker_and_first_level_completion(self):
        for i,a in enumerate(self.reference['verified_first_level_actions']):
            view=self.s.step({'action_id':a,'expected_sequence':i,'event_id':uuid.uuid4().hex})
            self.assertFalse(view['uncertain'])
        self.assertEqual(view['observation']['levels_completed'],1)
        self.assertEqual(view['observation']['state'],'NOT_FINISHED')
        raws=self.s.export()['transitions']
        before=raws[0]['before']['frames'][-1];after=raws[0]['outcome']['after']['frames'][-1]
        self.assertEqual(before[45][34],12);self.assertEqual(after[40][34],12)
        b=raws[7]['before']['frames'][-1];a=raws[7]['outcome']['after']['frames'][-1]
        self.assertNotEqual([row[:12] for row in b[53:63]],[row[:12] for row in a[53:63]])


if __name__=='__main__':unittest.main()
