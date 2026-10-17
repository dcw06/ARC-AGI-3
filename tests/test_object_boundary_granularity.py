"""Geometry, real adapter API contracts, raw replay and six-frame routing.

No real checkpoint, inference, network or GPU is used by these tests.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest

from research.object_discovery_boundaries_v1 import granularity as G
from research.object_discovery_boundaries_v1.granularity_runtime import verify_sources
from research.object_discovery_boundaries_v1.granularity_worker import inputs_for, run_frames, write_json
from research.object_discovery_boundaries_v1.masks import validate_predictions
from research.object_discovery_boundaries_v1.scoring import score_frame


class PureContracts(unittest.TestCase):
    def test_each_level_and_mode_is_a_separate_condition(self):
        for model in G.MODELS:
            for mode in ('seeded','automatic'):
                for level in G.levels(model):
                    policy=G.condition(model,mode,level)
                    self.assertFalse(policy['select_best_granularity'])
                    self.assertFalse(policy['references_available_to_inference'])
        for model, level in [('unsamv2',True),('unsamv2',0.2),('semantic_sam_l',1.0),('semantic_sam_l',7)]:
            with self.assertRaises(ValueError):G.condition(model,'automatic',level)

    def test_seed_pixel_coordinates_are_normalized_without_snapping(self):
        point=dict(pixel_xy=[14.25,28.75],cell_xy=[2,4])
        self.assertEqual(G.normalized_semantic_point(point),[[14.25/448,28.75/448]])
        point['cell_xy']=[4,2]
        with self.assertRaises(ValueError):G.normalized_semantic_point(point)

    def test_semantic_raw_channel_order_matches_upstream_prompt_switch(self):
        self.assertEqual([G.SEMANTIC_CHANNEL[i] for i in range(1,7)],[3,2,0,4,1,5])

    def test_quality_only_budget_stable_ties_and_nonfinite_refusal(self):
        self.assertEqual(G.ranked_indices([.3,.7,.7,.1],2),[1,2])
        self.assertEqual(len(G.ranked_indices([.1]*100)),96)
        for bad in ([True],[float('nan')],[float('inf')]):
            with self.assertRaises(ValueError):G.ranked_indices(bad)

    def test_empty_and_duplicate_masks_remain_failed_or_duplicate_proposals(self):
        policy=G.condition('unsamv2','automatic',.1)
        proposals=[G.proposal(i,mask,source_index=i-1,quality=.5,policy=policy)
                   for i,mask in enumerate(([[2,4]],[],[[2,4]]),1)]
        validate_predictions(proposals)
        reference=dict(inventory_policy='synthetic',reference_exhaustive_confirmed=True,
                       regions=[dict(id='a',cells=[[2,4]],parent_id=None,mask_reviewed=True,disposition='include')])
        result=score_frame(proposals,reference)
        self.assertEqual(result['prediction_count'],3)
        self.assertEqual(result['matched_count'],1)
        self.assertEqual(result['detection_precision'],1/3)

    def test_no_checkpoint_or_gpu_dependencies_on_module_import(self):
        # Importing the runtime is standard-library-only; actual backend imports
        # and model construction are explicit and delayed until execution.
        source=Path(G.__file__).with_name('granularity_runtime.py').read_text()
        self.assertIn('def load_backend(',source)
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):verify_sources(folder,'unsamv2')


@unittest.skipUnless(importlib.util.find_spec('numpy') and importlib.util.find_spec('torch') and importlib.util.find_spec('PIL'), 'optional segmentation CPU dependencies')
class AdapterIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import numpy as np
        import torch
        cls.np,cls.torch=np,torch
        cls.image=np.zeros((448,448,3),dtype=np.uint8)
        cls.point=dict(pixel_xy=[14.25,28.75],cell_xy=[2,4])

    def test_unsam_seeded_uses_native_xy_gra_and_quality_without_refinement(self):
        from research.object_discovery_boundaries_v1.granularity_backends import UnSAMv2Backend
        np=self.np;calls=[]
        class Predictor:
            def __init__(self,model):pass
            def set_image(self,image):calls.append(('image',image.shape))
            def predict(self,**kw):
                calls.append(kw)
                masks=np.full((3,448,448),-1.)
                masks[1,28:35,14:21]=1
                masks[2,:,:]=1
                return masks,np.asarray([.1,.8,.8]),np.zeros((3,256,256))
        raw=UnSAMv2Backend(None,Predictor,None).seeded(self.image,[self.point],.3)
        self.assertEqual(calls[1]['point_coords'].tolist(),[[14.25,28.75]])
        self.assertEqual(calls[1]['gra'],.3)
        self.assertTrue(calls[1]['return_logits'])
        self.assertNotIn('mask_input',calls[1])
        result=G.assemble(raw,G.condition('unsamv2_plus','seeded',.3),[self.point])
        self.assertEqual(result['objects'][0]['cells'],[[2,4]])
        self.assertEqual(raw['raw_masks'].shape,(1,3,448,448))

    def test_semantic_seeded_uses_raw_predict_not_visualization_and_channel_map(self):
        from research.object_discovery_boundaries_v1.granularity_backends import SemanticSAMBackend
        torch=self.torch;calls=[]
        class Predictor:
            def __init__(self,model):pass
            def predict(self,original,tensor,point):
                calls.append(point)
                masks=torch.full((6,640,640),-1.)
                masks[3]=1
                return masks,torch.tensor([[[.1,.2,.3,.4,.5,.6]]])
            def predict_masks(self,*args,**kwargs):raise AssertionError('visualization helper forbidden')
        image_tensor=lambda image:(self.np.zeros((640,640,3)),None)
        backend=SemanticSAMBackend(None,Predictor,None,image_tensor)
        raw=backend.seeded(self.image,[self.point],1)
        self.assertEqual(calls,[G.normalized_semantic_point(self.point)])
        self.assertEqual(raw['metadata']['raw_channel'],3)
        self.assertTrue(raw['masks'].all())
        self.assertEqual(raw['raw_masks'].shape,(1,6,640,640))

    def test_automatic_generators_receive_correct_api_and_no_molmo_points(self):
        from research.object_discovery_boundaries_v1.granularity_backends import UnSAMv2Backend,SemanticSAMBackend
        calls=[]
        class Generator:
            def __init__(self,model,**kw):calls.append(kw)
            def generate(self,image,**kw):calls.append(kw);return []
        raw=UnSAMv2Backend(None,None,Generator).automatic(self.image,.7)
        self.assertEqual(calls[1],dict(gra=.7))
        self.assertFalse(calls[0]['use_m2m'])
        self.assertEqual(calls[0]['min_mask_region_area'],0)
        self.assertEqual(raw['masks'].shape,(0,448,448))
        calls.clear()
        raw=SemanticSAMBackend(None,None,Generator,lambda image:(None,None)).automatic(self.image,2)
        self.assertEqual(calls[0]['level'],[2]);self.assertEqual(calls[1],{})
        self.assertEqual(raw['masks'].shape,(0,448,448))

    def test_projection_resizes_640_to_448_before_7_pixel_cell_mapping(self):
        from research.object_discovery_boundaries_v1.granularity_backends import binary_original
        mask=self.np.zeros((1,640,640),dtype=bool)
        mask[0,40:50,20:30]=True
        cells=G.project(binary_original(mask,logits=False)[0].tolist())
        self.assertEqual(cells,[[2,4]])
        with self.assertRaises(ValueError):binary_original(self.np.zeros((1,1024,1024)),logits=True)
        with self.assertRaises(ValueError):binary_original(self.np.full((1,448,448),float('nan')),logits=True)

    def test_automatic_budget_capping_reports_discarded_proposals(self):
        # Avoid allocating 100 full masks: ndarray-index-compatible wrapper.
        class Mask:
            def tolist(self):return [[False]*448 for _ in range(448)]
        raw=dict(masks=[Mask()]*100,qualities=[.5]*100)
        result=G.assemble(raw,G.condition('unsamv2','automatic',.5))
        self.assertEqual(result['raw_proposal_count'],100)
        self.assertEqual(result['discarded_by_proposal_budget'],4)
        self.assertEqual(result['selected_raw_indices'],list(range(96)))
        self.assertTrue(all(p['empty_mask'] for p in result['objects']))

    def fixture(self,folder):
        from certification.phase4_multimodal_preflight_v3.images import png
        inputs=folder/'inputs';inputs.mkdir()
        frames=[]
        for i in range(1,7):
            name=f'board-{i:02d}'
            (inputs/(name+'.png')).write_bytes(png([[5]*64 for _ in range(64)],cell=7))
            frames.append(dict(case_id=name,image_sha256=hashlib.sha256((inputs/(name+'.png')).read_bytes()).hexdigest(),
                               points=[] if i==1 else [self.point],source_response_valid=i!=1))
        write_json(inputs/'seeds.json',dict(frames=frames))
        write_json(inputs/'manifest.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs.iterdir()})
        return inputs,frames

    def test_six_frame_worker_automatic_includes_invalid_seed_ls20_seeded_skips_it(self):
        np=self.np
        class Backend:
            calls=0
            def automatic(self,image,level):
                self.calls+=1
                return dict(masks=np.zeros((0,448,448),dtype=bool),qualities=[],metadata=[],
                            raw_masks=np.zeros((0,448,448),dtype=bool),raw_qualities=np.array([]))
            def seeded(self,image,points,level):
                self.calls+=1
                mask=np.full((1,3,448,448),-1.);mask[0,0,28:35,14:21]=1.
                return dict(masks=mask[:,0]>0,qualities=[.9],metadata={},raw_masks=mask,raw_qualities=np.array([[.9,.2,.1]]))
        with tempfile.TemporaryDirectory() as path:
            folder=Path(path);inputs,_=self.fixture(folder)
            for mode,count in [('automatic',6),('seeded',5)]:
                backend=Backend();output=folder/mode
                run_frames(backend,inputs,output,G.condition('unsamv2','seeded' if mode=='seeded' else 'automatic',.1),time.monotonic()+120)
                self.assertEqual(backend.calls,count)
                first=json.loads((output/'board-01.json').read_bytes())
                self.assertEqual(first['skipped'],mode=='seeded')
                self.assertTrue((output/'worker-manifest.json').is_file())
                with self.assertRaises(FileExistsError):run_frames(backend,inputs,output,G.condition('unsamv2',mode,.1),time.monotonic()+120)
            # Disallow an answer-bearing file from entering inference inputs.
            (inputs/'answers.json').write_text('{}')
            with self.assertRaises(ValueError):inputs_for(inputs)

    def test_evaluator_replays_raw_mask_selection_and_rejects_rehashed_tampering(self):
        from scripts.evaluate_granularity_segmentation import evaluate
        np=self.np
        class Backend:
            def seeded(self,image,points,level):
                raw=np.full((1,3,448,448),-1.);raw[0,0,28:35,14:21]=1.
                return dict(masks=raw[:,0]>0,qualities=[.9],metadata={},raw_masks=raw,raw_qualities=np.array([[.9,.2,.1]]))
        with tempfile.TemporaryDirectory() as path:
            folder=Path(path);inputs,frames=self.fixture(folder)
            output=folder/'frames'
            run_frames(Backend(),inputs,output,G.condition('unsamv2','seeded',.1),time.monotonic()+120)
            refs=folder/'references.json'
            write_json(refs,dict(frames=[dict(case_id=f['case_id'],grid=[[5]*64 for _ in range(64)],
                inventory_policy='synthetic',reference_exhaustive_confirmed=True,
                regions=[dict(id='object',parent_id=None,cells=[[2,4]],mask_reviewed=True,disposition='include')]) for f in frames]))
            result=evaluate(output,inputs,refs)
            self.assertEqual([f['whole']['matched_count'] for f in result['frames']],[0,1,1,1,1,1])
            file=output/'board-02.json';saved=json.loads(file.read_bytes())
            saved['objects'][0]['cells']=[[4,2]]
            file.write_text(json.dumps(saved))
            manifest=output/'worker-manifest.json';pins=json.loads(manifest.read_bytes())
            pins[file.name]=hashlib.sha256(file.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(pins))
            with self.assertRaisesRegex(ValueError,'raw mask replay'):
                evaluate(output,inputs,refs)

    def test_evaluator_handles_empty_automatic_and_fixed_semantic_channel(self):
        from scripts.evaluate_granularity_segmentation import evaluate
        np=self.np
        class Backend:
            def automatic(self,image,level):
                # Keep an explicitly empty proposal, not a missing response.
                raw=np.zeros((1,448,448),dtype=bool)
                return dict(masks=raw,qualities=[.5],metadata=[],raw_masks=raw,raw_qualities=np.array([.5]))
            def seeded(self,image,points,level):
                raw=np.full((1,6,640,640),-1.)
                raw[0,3,40:50,20:30]=1.
                chosen=np.zeros((1,448,448),dtype=bool);chosen[0,28:35,14:21]=True
                return dict(masks=chosen,qualities=[.4],metadata={},raw_masks=raw,
                            raw_qualities=np.array([[.1,.2,.3,.4,.5,.9]]))
        with tempfile.TemporaryDirectory() as path:
            folder=Path(path);inputs,frames=self.fixture(folder)
            refs=folder/'references.json'
            write_json(refs,dict(frames=[dict(case_id=f['case_id'],grid=[[5]*64 for _ in range(64)],
                inventory_policy='synthetic',reference_exhaustive_confirmed=True,
                regions=[dict(id='object',parent_id=None,cells=[[2,4]],mask_reviewed=True,disposition='include')]) for f in frames]))
            for mode in ('automatic','seeded'):
                output=folder/mode
                run_frames(Backend(),inputs,output,G.condition('semantic_sam_l',mode,1),time.monotonic()+120)
                result=evaluate(output,inputs,refs)
                if mode=='automatic':
                    self.assertEqual([f['whole']['prediction_count'] for f in result['frames']],[1]*6)
                    self.assertEqual([f['whole']['matched_count'] for f in result['frames']],[0]*6)
                else:
                    self.assertEqual([f['whole']['matched_count'] for f in result['frames']],[0,1,1,1,1,1])


if __name__=='__main__':unittest.main()
