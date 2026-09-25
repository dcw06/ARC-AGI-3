"""Action-effect records and fixtures: mechanical labels, independent re-check, failure safety."""
import copy,json,unittest,zipfile
from pathlib import Path
from research.action_effect_v1.records import effect_record,policy_view,EffectHistory,EFFECT_FIELDS
from research.action_effect_v1 import fixtures

ROOT=Path(__file__).resolve().parents[1]
FROZEN=json.loads(fixtures.OUTPUT.read_bytes())
CASES={c['case_id']:c for c in FROZEN['cases']}

def independent_diff(before,after):
    """Second implementation: sets of differing coordinates (None for a shape change)."""
    if [len(r) for r in before]!=[len(r) for r in after]:return None
    cells_a={(x,y,v) for y,r in enumerate(before) for x,v in enumerate(r)}
    cells_b={(x,y,v) for y,r in enumerate(after) for x,v in enumerate(r)}
    return len({(x,y) for x,y,_ in cells_a^cells_b})

class FrozenFixtureTests(unittest.TestCase):
    def test_regeneration_is_deterministic(self):
        self.assertEqual(fixtures.OUTPUT.read_text(encoding='utf-8'),fixtures.render())
    def test_independent_recheck_of_every_label(self):
        for c in FROZEN['cases']:
            with self.subTest(case=c['case_id']):
                r=c['reference_record'];self.assertEqual(r,effect_record(c['pre'],c['action'],c['outcome']))
                if c['outcome']['status']!='acknowledged':continue
                ref=c['pre']['frames'][-1];counts=[independent_diff(ref,f) for f in c['outcome']['post']['frames']]
                self.assertEqual(r['changed_cells_by_frame'],counts)
                changed=[n is None or n>0 for n in counts]
                self.assertEqual((r['final_frame_changed'],r['any_frame_changed']),(changed[-1],any(changed)))
                self.assertEqual(r['level_delta'],c['outcome']['post']['levels_completed']-c['pre']['levels_completed'])
    def test_intended_properties(self):
        g=fixtures.base();ref=json.loads((ROOT/'reports/integrated_case_v1/geometry_reference.json').read_bytes())
        cells={o['id']:o['cells'] for o in ref['objects']}
        r=lambda cid:CASES[cid]['reference_record']
        self.assertEqual((r('identical_frames')['changed_cells_by_frame'],r('identical_frames')['final_frame_changed']),([0],False))
        self.assertEqual(r('disappearance')['changed_cells_by_frame'],[len(cells['B'])])
        self.assertEqual(r('colour_only')['changed_cells_by_frame'],[sum(g[y][x]==5 for x,y in cells['A'])])
        self.assertGreater(r('movement')['changed_cells_by_frame'][0],0)
        i=r('intermediate_return');self.assertEqual((i['changed_cells_by_frame'][1],i['final_frame_changed'],i['any_frame_changed'],i['returned_to_pre_frame']),(0,False,True,True))
        l=r('level_counter_only');self.assertEqual((l['changed_cells_by_frame'],l['final_frame_changed'],l['level_delta']),([0],False,1))
        d=r('dimension_change');self.assertEqual((d['changed_cells_by_frame'],d['dimension_changed_by_frame'],d['final_frame_changed']),([None],[True],True))
        a,b=r('same_type_coordinates_a'),r('same_type_coordinates_b')
        self.assertEqual((a['action_id'],b['action_id']),(6,6));self.assertNotEqual(a['action_data'],b['action_data'])
        self.assertNotEqual(policy_view(a),policy_view(b))
    def test_failed_and_unknown_never_become_no_ops(self):
        for cid,status in (('dispatch_failed','dispatch_failed'),('outcome_unknown','outcome_unknown')):
            rec=CASES[cid]['reference_record'];self.assertEqual(rec['status'],status)
            self.assertTrue(all(rec[f] is None for f in EFFECT_FIELDS),cid)
            view=policy_view(rec);self.assertIsNone(view['changed_cells_by_frame']);self.assertIsNone(view['final_frame_changed'])
            self.assertNotEqual(view['changed_cells_by_frame'],[0])
        pre=CASES['dispatch_failed']['pre']
        for outcome in ({'status':'dispatch_failed'},{'status':'outcome_unknown','reason':''},{'status':'no_op'},{}):
            with self.assertRaises(ValueError):effect_record(pre,{'action_id':6,'action_data':{'x':1,'y':1}},outcome)

class RecordContractTests(unittest.TestCase):
    def test_inputs_only_and_policy_view(self):
        c=CASES['movement'];before=copy.deepcopy(c)
        rec=effect_record(c['pre'],c['action'],c['outcome']);self.assertEqual(c,before)  # inputs untouched
        self.assertEqual(rec,effect_record(copy.deepcopy(c['pre']),copy.deepcopy(c['action']),copy.deepcopy(c['outcome'])))
        self.assertEqual(set(policy_view(rec)),{'action_id','action_data','status','returned_frame_count',
            'changed_cells_by_frame','final_frame_changed','level_delta','reset'})
        text=json.dumps(policy_view(rec)).lower()
        for word in ('recommend','arrow','object','probe','hash','detail'):self.assertNotIn(word,text)
    def test_invalid_inputs_rejected(self):
        g=fixtures.base();pre={'frames':[g],'levels_completed':0}
        for action in ({'action_id':0,'action_data':{}},{'action_id':6},{'action_id':'6','action_data':{}}):
            with self.assertRaises(ValueError):effect_record(pre,action,{'status':'acknowledged','post':pre})
        with self.assertRaises(ValueError):effect_record({'frames':[[[16]]],'levels_completed':0},{'action_id':1,'action_data':{}},{'status':'acknowledged','post':pre})
    def test_history_segments_and_failures(self):
        seq=FROZEN['history_sequence'];e=seq['entries']
        self.assertEqual([x['segment'] for x in e],[0,0,0,0,1,1,2])
        self.assertEqual(e[2]['status'],'dispatch_failed');self.assertIsNone(e[2]['changed_cells_by_frame'])
        self.assertEqual((e[3]['level_delta'],e[5]['reset']),(1,True))
        self.assertEqual(seq['view']['omitted_entries'],2);self.assertEqual([x['step'] for x in seq['view']['entries']],[2,3,4,5,6])
        with self.assertRaises(ValueError):EffectHistory(0)
        with self.assertRaises(ValueError):EffectHistory().append({'status':'acknowledged'})

class R8CompatibilityTests(unittest.TestCase):
    def test_records_reproduce_archived_r8_and_replay_is_unchanged(self):
        from scripts import archive_grounded_action_v1_r8 as archive
        lock=json.loads(archive.LOCK.read_bytes());before=archive.ARCHIVE.read_bytes()
        name='reports/runs/phase4-grounded-action-v1-r8/download/phase4-grounded-action-v1/worker/trajectory.json'
        with zipfile.ZipFile(archive.ROOT/lock['archive']) as z:t=json.loads(z.read(name))
        for ep in t['episodes']:
            for s in ep['steps']:
                rec=effect_record(s['before'],s['action'],{'status':'acknowledged','post':s['after']})
                self.assertEqual({k:rec[k] for k in ('action_id','action_data','returned_frame_count','changed_cells_by_frame','final_frame_changed','level_delta')},
                    {'action_id':6,'action_data':s['action']['action_data'],'returned_frame_count':1,'changed_cells_by_frame':[0],'final_frame_changed':False,'level_delta':0})
                self.assertEqual((rec['pre_canonical_hash'],rec['post_canonical_hash']),(s['before']['canonical_hash'],s['after']['canonical_hash']))
        self.assertEqual(archive.replay()['evaluation_status'],'verified_complete_development_pair')
        self.assertEqual(archive.ARCHIVE.read_bytes(),before)

if __name__=='__main__':unittest.main()
