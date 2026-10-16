"""Native decoder contract, exact coordinates and point-hit semantics."""
from types import SimpleNamespace
import json
from pathlib import Path
import tempfile
import unittest

from research.molmopoint_identification_v1.adapter import points_to_cells, prepare_inputs, decode_generation
from research.molmopoint_identification_v1.scoring import match_points, score_case, score_target


class CoordinateTests(unittest.TestCase):
    def test_every_448_cell_is_exactly_seven_pixels(self):
        for y in range(64):
            raw = [[x,0,x*7+3.5,y*7+3.5] for x in range(64)]
            self.assertEqual([p['cell_xy'] for p in points_to_cells(raw,(448,448))],
                             [[x,y] for x in range(64)])
        got = points_to_cells([[0,0,6.999,7],[1,0,7,6.999],[2,0,447.999,447.999]],(448,448))
        self.assertEqual([p['cell_xy'] for p in got],[[0,1],[1,0],[63,63]])
        with self.assertRaises(ValueError):
            points_to_cells([[0,0,448,0]],(448,448))

    def test_every_board_cell_and_axis_order(self):
        raw = [[y*64+x,0,x*8+4,y*8+4] for y in range(64) for x in range(64)]
        # Respect the 96-point output ceiling for each response.
        for start in range(0,len(raw),96):
            part = raw[start:start+96]
            got = points_to_cells(part,(512,512))
            self.assertEqual([p['cell_xy'] for p in got],[[int(r[2]//8),int(r[3]//8)] for r in part])

    def test_rectangular_original_dimensions_and_boundaries(self):
        got = points_to_cells([[0,0,0,0],[1,0,16,4],[2,0,1023.99,255.99]],(1024,256))
        self.assertEqual([p['cell_xy'] for p in got],[[0,0],[1,1],[63,63]])

    def test_invalid_native_coordinates_never_clamped(self):
        for row in [[0,0,512,0],[0,0,-1,0],[0,0,float('nan'),0],[0,0,float('inf'),0],
                    [0,0,True,0],[True,0,0,0],[0,1,0,0],[0,0,'4',0]]:
            with self.subTest(row=row),self.assertRaises(ValueError):
                points_to_cells([row],(512,512))
        with self.assertRaises(ValueError):
            points_to_cells([[0,0,0,0]]*97,(512,512))

    def test_empty_is_no_detection_not_crash(self):
        self.assertEqual(points_to_cells([], (512,512)),[])


class NativeInterfaceTests(unittest.TestCase):
    def components(self):
        metadata = {'token_pooling':'pool','subpatch_mapping':'map','image_sizes':[(512,512)]}
        model = SimpleNamespace(config=SimpleNamespace(model_type='molmo_point'),
            build_logit_processor_from_inputs=lambda x:['native-constraint'],
            extract_image_points=lambda *args:[[0,0,20.0,28.0]])
        processor = SimpleNamespace(apply_chat_template=lambda *args,**kwargs:{'metadata':dict(metadata),'input_ids':'ids'})
        return model,processor,metadata

    def test_processor_metadata_and_native_constraints_required(self):
        model,processor,metadata = self.components()
        def template(messages,**kwargs):
            self.assertTrue(kwargs['return_pointing_metadata'])
            self.assertEqual(messages[0]['content'][0]['text'],'Point to the distinct visible objects in this game image.')
            return {'metadata':dict(metadata),'input_ids':'ids'}
        processor.apply_chat_template = template
        inputs,kept,logits = prepare_inputs(model,processor,SimpleNamespace(size=(512,512)),'objects')
        self.assertEqual(inputs,{'input_ids':'ids'})
        self.assertEqual(kept,metadata)
        self.assertTrue(logits)
        model.build_logit_processor_from_inputs = lambda x:[]
        with self.assertRaises(ValueError):
            prepare_inputs(model,processor,SimpleNamespace(size=(512,512)),'objects')

    def test_decode_retains_special_tokens_and_uses_original_size(self):
        model,processor,metadata = self.components()
        text = '<POINT_0><POINT_5><POINT_9>0'
        def post(ids,**kwargs):
            self.assertFalse(kwargs['skip_special_tokens'])
            self.assertFalse(kwargs['clean_up_tokenization_spaces'])
            return [text]
        processor.post_process_image_text_to_text = post
        out = decode_generation(model,processor,[42,43],metadata,(512,512),finish_reason='stop')
        self.assertEqual(out['points'][0]['cell_xy'],[2,3])
        self.assertEqual(out['raw_text_with_special_tokens'],text)
        model.extract_image_points = lambda *args:[]
        with self.assertRaises(ValueError):
            decode_generation(model,processor,[42,43],metadata,(512,512),finish_reason='stop')

    def test_truncated_and_oversized_generations_refused(self):
        model,processor,metadata = self.components()
        with self.assertRaises(ValueError):
            decode_generation(model,processor,[42],metadata,(512,512),finish_reason='length')
        with self.assertRaises(ValueError):
            decode_generation(model,processor,[42]*1025,metadata,(512,512),finish_reason='stop')

    def test_wrong_architecture_and_original_size_refused(self):
        model,processor,metadata = self.components()
        model.config.model_type = 'internvl_chat'
        with self.assertRaises(ValueError):
            prepare_inputs(model,processor,SimpleNamespace(size=(512,512)),'objects')
        model.config.model_type = 'molmo_point'
        with self.assertRaises(ValueError):
            prepare_inputs(model,processor,SimpleNamespace(size=(448,448)),'objects')


class ScoringTests(unittest.TestCase):
    def test_target_hit_is_specific_to_requested_object_and_single_point(self):
        ref = {'case_id':'fixture','regions':[
            {'id':'intended','target_points':[[1,2]]},
            {'id':'distractor','target_points':[[4,5]]}]}
        self.assertFalse(score_target(ref,'intended',[{'cell_xy':[4,5]}])['target_hit'])
        self.assertTrue(score_target(ref,'intended',[{'cell_xy':[1,2]}])['target_hit'])
        self.assertFalse(score_target(ref,'intended',[])['target_hit'])
        multiple = score_target(ref,'intended',[{'cell_xy':[1,2]},{'cell_xy':[4,5]}])
        self.assertFalse(multiple['response_valid'])
        self.assertFalse(multiple['target_hit'])

    def test_point_must_hit_occupied_cell_not_bounding_box_hole(self):
        region = {'id':'ring','target_points':[[1,1],[3,3]]}
        self.assertEqual(match_points([region],[{'cell_xy':[2,2]}]),[])
        self.assertEqual(len(match_points([region],[{'cell_xy':[1,1]}])),1)

    def test_one_point_cannot_cover_two_regions_within_a_stratum(self):
        refs = [{'id':str(i),'target_points':[[1,1]]} for i in range(2)]
        self.assertEqual(len(match_points(refs,[{'cell_xy':[1,1]}])),1)

    def test_hierarchical_strata_and_unlabelled_barriers_not_negative_truth(self):
        region = {'id':'part','parent_id':'parent','kind':'other','target_points':[[1,1]]}
        ref = {'case_id':'fixture','regions':[region]}
        result = score_case(ref,[{'cell_xy':[1,1]}],'objects')
        self.assertEqual(result['localization']['parts']['matched_regions'],1)
        barrier = score_case(ref,[{'cell_xy':[1,1]}],'barrier_candidates')
        self.assertIsNone(barrier['localization']['whole_regions']['coverage'])
        self.assertIsNone(barrier['collision_accuracy'])

    def test_invalid_cells_refused(self):
        for p in [[True,0],[64,0],[-1,0],[1.5,2]]:
            with self.assertRaises(ValueError):
                match_points([],[{'cell_xy':p}])


class TargetedPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_object_identification_v1 import snapshot
        from research.object_identification_v1.probe import prepare
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        snapshot(cls.root/'snapshot')
        prepare(cls.root/'snapshot',cls.root/'source')
        refs = json.loads((cls.root/'source/references/answers.json').read_bytes())
        cls.plan = {'schema':'molmopoint_target_plan_v1','targets':[
            {'case_id':r['case_id'],'target_region_id':r['regions'][0]['id'],
             'prompt':'Point to the center of the small green square.'} for r in refs]}
        cls.targets = cls.root/'targets.json'
        cls.targets.write_text(json.dumps(cls.plan))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_448_image_roundtrip_and_target_reference_isolation(self):
        from certification.phase4_multimodal_preflight_v3.images import grid_from_png
        from research.molmopoint_identification_v1.prepare import prepare
        out = self.root/'prepared'
        result = prepare(self.root/'source',out,self.targets)
        self.assertEqual(result['proposed_requests'],6)
        requests = [json.loads(raw) for raw in (out/'inputs/requests.jsonl').read_bytes().splitlines()]
        for req in requests:
            self.assertEqual(req['original_image_size_wh'],[448,448])
            self.assertEqual(req['cell_pixels'],7)
            original = grid_from_png((self.root/'source'/req['image']).read_bytes(),cell=8)
            self.assertEqual(grid_from_png((out/req['image']).read_bytes(),cell=7),original)
            self.assertNotIn('target_region_id',req)
            self.assertNotIn('target_points',req)
        self.assertEqual(len(list((out/'inputs').iterdir())),7)
        self.assertTrue((out/'references/selected-targets.json').exists())
        with self.assertRaises(FileExistsError):
            prepare(self.root/'source',out,self.targets)

    def test_unknown_and_missing_targets_refused_before_writing(self):
        from copy import deepcopy
        from research.molmopoint_identification_v1.prepare import prepare
        for i in range(2):
            plan = deepcopy(self.plan)
            if i == 0:
                plan['targets'][0]['target_region_id'] = 'missing'
            else:
                plan['targets'].pop()
            file = self.root/f'invalid-{i}.json'
            file.write_text(json.dumps(plan))
            out = self.root/f'invalid-out-{i}'
            with self.assertRaises(ValueError):
                prepare(self.root/'source',out,file)
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
