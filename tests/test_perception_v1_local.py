import copy,json,unittest
from research.perception_v1.fixtures import build,gold,D4,transform,inverse,digest
from research.perception_v1.scoring import score
from research.perception_v1 import controls,transitions

class PerceptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.cases=build()
    def test_deterministic_gold_all_dimensions(self):
        self.assertEqual(self.cases,build())
        for c in self.cases:
            s=score(c,json.dumps(gold(c)))
            self.assertTrue(s['valid']);self.assertEqual(s['detection_recall']['rate'],1)
            self.assertEqual(s['contour_exact']['rate'],1);self.assertEqual(s['same_shape']['rate'],1)
            if s['transform']['denominator']:self.assertEqual(s['transform']['rate'],1)
            self.assertEqual(s['marking_colors']['rate'],1)
    def test_chiral_cases_and_ambiguous_p1(self):
        p1,p2,p3,_,p5=self.cases
        self.assertFalse(p1['chiral_scoring'])
        self.assertGreater(len(p1['reference']['relations'][0]['transforms']),1)
        self.assertTrue(all(not t.startswith('mirror') for t in p2['reference']['relations'][0]['transforms']))
        self.assertTrue(all(t.startswith('mirror') for t in p3['reference']['relations'][0]['transforms']))
        self.assertEqual(p5['reference']['relations'][0]['transforms'],[])
    def test_inverse_and_reversed_relation(self):
        shape=self.cases[1]['reference']['objects'][0]['cells']
        for t in D4:self.assertEqual(transform(transform(shape,t),inverse(t)),transform(shape,D4[0]))
        c=self.cases[1];v=gold(c);r=v['relations'][0];r['a'],r['b']=r['b'],r['a'];r['transform']=inverse(r['transform'])
        self.assertEqual(score(c,json.dumps(v))['transform']['rate'],1)
    def test_invalid_omissions_and_duplicate_objects(self):
        c=self.cases[0]
        for text,finish in [('{','stop'),(json.dumps(gold(c)),'length'),('{"objects":[],"objects":[]}','stop')]:
            s=score(c,text,finish);self.assertFalse(s['valid']);self.assertEqual(s['detection_recall']['numerator'],0)
        v=gold(c);v['objects']=[];v['relations']=[];s=score(c,json.dumps(v));self.assertTrue(s['valid'])
        self.assertIsNone(s['detection_precision']['rate']);self.assertEqual(s['same_shape']['numerator'],0)
        v=gold(c);o=copy.deepcopy(v['objects'][0]);o['id']='duplicate';v['objects'].append(o)
        s=score(c,json.dumps(v));self.assertEqual(s['duplicate_objects'],1);self.assertEqual(s['extraneous_objects'],1)
    def test_contour_not_bbox_and_distractor(self):
        c=self.cases[3];v=gold(c);v['objects'][0]['occupancy']=[[1]*3 for _ in range(3)]
        s=score(c,json.dumps(v));self.assertEqual(s['bbox_exact']['rate'],1);self.assertLess(s['contour_exact']['rate'],1)
        v['objects'][0]['bbox']=[29,0,31,63];s=score(c,json.dumps(v));self.assertEqual(s['distractor_errors'],1)
    def test_coordinate_swap_wrong_markings_and_duplicate_relations(self):
        c=self.cases[0];v=gold(c);o=v['objects'][0];o['bbox']=[o['bbox'][1],o['bbox'][0],o['bbox'][3],o['bbox'][2]]
        self.assertLess(score(c,json.dumps(v))['bbox_exact']['numerator'],3)
        v=gold(c);v['objects'][0]['has_markings']=False;v['relations'].append(v['relations'][0])
        s=score(c,json.dumps(v));self.assertLess(s['has_markings']['rate'],1);self.assertEqual(s['duplicate_relations'],1)

class ControlTests(unittest.TestCase):
    def test_supplied_roles_and_correct_actions(self):
        for c in controls.cases():
            s=controls.score(c,json.dumps(c['expected']));self.assertTrue(s['valid'])
            self.assertTrue(all(s[k]['rate']==1 for k in ('arguments','click','non_coordinate','directional')))
        c=controls.cases()[0];v=copy.deepcopy(c['expected']);v['directional_ids']=[1,2,3,4]
        self.assertEqual(controls.score(c,json.dumps(v))['directional']['rate'],0)
    def test_wrong_target_and_illegal_argument_boundaries(self):
        from certification.phase4_multimodal_preflight_v3.action_contract import validate_action
        for x in (0,63):validate_action(json.dumps({'action':{'action_id':6,'action_data':{'x':x,'y':x}}}),[6])
        c=controls.cases()[0];v=copy.deepcopy(c['expected']);v['click']['action_data']={'x':23,'y':7}
        self.assertEqual(controls.score(c,json.dumps(v))['click']['rate'],0)
        for bad in (-1,64,True):
            v['click']['action_data']['x']=bad;self.assertFalse(controls.score(c,json.dumps(v))['valid'])
        v=copy.deepcopy(c['expected']);v['non_coordinate']['action_data']={'x':1,'y':2}
        self.assertFalse(controls.score(c,json.dumps(v))['valid'])

class TransitionTests(unittest.TestCase):
    def intent(self):
        return transitions.commit(episode_id='fixture',game_id='synthetic',seed=0,step=0,request_sha256='a'*64,response_sha256='b'*64,
            before={'frames':[[[0,0],[0,0]]],'levels_completed':0,'state':'playing'},
            action={'action_id':6,'action_data':{'x':1,'y':0}},legal_actions=[6],intended_target='upper right cell',
            prediction='upper right cell changes',alternative='grid unchanged',at=1)
    def record(self):
        i=self.intent()
        return transitions.finalize(i,intent_sha256=digest(i),dispatch={'action':i['action'],'acknowledged':True,'started_at':2,'returned_at':3},
            after={'frames':[[[0,1],[0,0]],[[0,0],[0,0]]],'levels_completed':0,'state':'playing'},
            update={'assessment':'unresolved','evidence_frames':[0,1],'revised_hypothesis':'change was transient'})
    def test_intermediate_change_is_retained_even_when_final_unchanged(self):
        r=self.record();self.assertTrue(transitions.verify(r))
        self.assertEqual(r['frame_changes'][0]['from_before']['bbox'],[1,0,1,0])
        self.assertEqual(r['frame_changes'][1]['from_before']['changed_cells'],0)
        self.assertEqual(r['frame_changes'][1]['from_previous']['changed_cells'],1)
    def test_mutations_rejected(self):
        for mutate in (lambda r:r['intent'].update(prediction='new guess'),lambda r:r['dispatch'].update(acknowledged=False),
                       lambda r:r['dispatch'].update(started_at=0),lambda r:r['after'].update(frames=[]),
                       lambda r:r['model_update'].update(evidence_frames=[2]),lambda r:r.update(level_delta=1)):
            r=self.record();mutate(r)
            with self.assertRaises((ValueError,KeyError)):transitions.verify(r)
    def test_shape_change_and_episode_isolation(self):
        self.assertEqual(transitions.changes([[0]],[[0,0]])['shape_changed'],True)
        r=self.record()
        with self.assertRaises(ValueError):transitions.verify(r,r)

if __name__=='__main__':unittest.main()
