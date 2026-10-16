"""Synthetic extent, matching and inventory-contract tests; no model inference."""
import copy,itertools
from types import SimpleNamespace
import unittest
from research.object_discovery_boundaries_v1.masks import seed_masks,boundary,validate_predictions
from research.object_discovery_boundaries_v1.scoring import score_frame,assignment
from research.object_discovery_boundaries_v1.decoding import decode_inventory


def reference(masks,*,complete=True):
    return dict(case_id='synthetic',inventory_policy='Synthetic visual instances',reference_exhaustive_confirmed=complete,
        reviewer='SYNTHETIC ONLY',regions=[dict(id='r'+str(i),parent_id=None,cells=m,mask_reviewed=True,disposition='include')
            for i,m in enumerate(masks)])


def prediction(masks):return [dict(id='p'+str(i),level='whole',cells=m) for i,m in enumerate(masks)]


class Masks(unittest.TestCase):
    def test_nonrectangular_component_preserves_hole_and_edge(self):
        grid=[[0]*64 for _ in range(64)]
        for x,y in [(0,0),(1,0),(2,0),(0,1),(2,1),(0,2),(1,2),(2,2)]:grid[y][x]=9
        p=seed_masks(grid,[{'cell_xy':[0,0]}])[0]
        self.assertEqual(len(p['cells']),8);self.assertNotIn([1,1],p['cells'])
        self.assertEqual(p['bbox_xyxy'],[0,0,2,2]);self.assertEqual(len(p['boundary_cells']),8)

    def test_diagonal_same_color_does_not_connect_and_multicolor_does_not_merge(self):
        grid=[[0]*64 for _ in range(64)];grid[2][2]=9;grid[3][3]=9;grid[2][3]=8
        self.assertEqual(seed_masks(grid,[{'cell_xy':[2,2]}])[0]['cells'],[[2,2]])

    def test_duplicate_and_background_seeds_are_retained(self):
        grid=[[0]*64 for _ in range(64)];grid[2][2]=9
        out=seed_masks(grid,[{'cell_xy':[2,2]},{'cell_xy':[2,2]},{'cell_xy':[0,0]}])
        self.assertEqual(len(out),3);self.assertEqual(out[0]['cells'],out[1]['cells'])
        self.assertEqual(len(out[2]['cells']),4095)

    def test_invalid_coordinates_masks_and_ids_are_not_repaired(self):
        grid=[[0]*64 for _ in range(64)]
        for p in ([True,0],[-1,0],[64,0],[1.2,2]):
            with self.subTest(p=p),self.assertRaises(ValueError):seed_masks(grid,[{'cell_xy':p}])
        for masks in ([[[1,1],[1,1]]],[[]]):
            with self.assertRaises(ValueError):validate_predictions(prediction(masks))
        p=prediction([[[1,1]],[[2,2]]]);p[1]['id']=p[0]['id']
        with self.assertRaises(ValueError):validate_predictions(p)


class Scoring(unittest.TestCase):
    def test_exact_and_missing_masks_keep_reference_denominator(self):
        result=score_frame(prediction([[[1,1]]]),reference([[[1,1]],[[4,4]]]))
        self.assertEqual(result['detection_recall'],.5)
        self.assertEqual(result['mean_iou_over_all_labelled_objects'],.5)
        self.assertEqual(result['boundary_f1_over_all_labelled_objects'],.5)

    def test_duplicate_detections_cannot_gain_multiple_credit(self):
        result=score_frame(prediction([[[1,1]],[[1,1]]]),reference([[[1,1]]]))
        self.assertEqual(result['matched_count'],1);self.assertEqual(result['false_positive_count'],1)
        self.assertEqual(result['detection_precision'],.5)

    def test_incomplete_or_ambiguous_reference_does_not_claim_false_positive(self):
        ref=reference([[[1,1]]],complete=False)
        for ambiguous in (False,True):
            ref['reference_exhaustive_confirmed']=ambiguous
            if ambiguous:ref['regions'].append(dict(id='uncertain',parent_id=None,cells=[[4,4]],mask_reviewed=True,disposition='ambiguous'))
            result=score_frame(prediction([[[1,1]],[[3,3]]]),ref)
            self.assertIsNone(result['detection_precision']);self.assertIsNone(result['false_positive_count'])
            self.assertEqual(result['unadjudicated_unmatched_predictions'],1)

    def test_unreviewed_masks_refuse_and_parent_parts_stay_separate(self):
        ref=reference([[[1,1],[2,1]],[[1,1]]]);ref['regions'][1]['parent_id']='r0'
        result=score_frame(prediction([[[1,1],[2,1]]]),ref)
        self.assertEqual(result['reference_count'],1)
        ref['regions'][0]['mask_reviewed']=False
        with self.assertRaises(ValueError):score_frame([],ref)

    def test_merge_and_filled_hole_fail_exact_mask_and_lower_iou(self):
        ref=reference([[[1,1]],[[2,1]]]);result=score_frame(prediction([[[1,1],[2,1]]]),ref)
        self.assertEqual(result['matched_count'],1);self.assertEqual(result['exact_mask_fraction'],0)
        self.assertEqual(result['mean_iou_over_all_labelled_objects'],.25)

    def test_global_assignment_matches_bruteforce_including_greedy_trap(self):
        for weights in ([[.8,.7],[.75,0]],[[1,3,2],[4,0,2],[1,1,5]],[[0,0],[0,0]]):
            expected=max(sum(weights[i][j] for i,j in enumerate(order)) for order in itertools.permutations(range(len(weights))))
            self.assertAlmostEqual(sum(weights[i][j] for i,j in assignment(weights)),expected)

    def test_empty_denominators_do_not_manufacture_perfect_detection(self):
        result=score_frame([],reference([]))
        self.assertIsNone(result['detection_precision']);self.assertIsNone(result['detection_recall'])
        self.assertIsNone(result['mean_iou_over_all_labelled_objects'])


class InventoryDecode(unittest.TestCase):
    def setup_decoder(self,text):
        model=SimpleNamespace(config=SimpleNamespace(no_more_points_class=True,patch_location='3x3'),
            extract_image_points=lambda *a:[[1,0,7.,14.]])
        processor=SimpleNamespace(post_process_image_text_to_text=lambda *a,**kw:[text])
        metadata=dict(image_sizes=[(448,448)],token_pooling=SimpleNamespace(shape=(4,4)),subpatch_mapping=[])
        return model,processor,metadata

    def test_new_inventory_token_cap_does_not_slice_to_old_target_cap(self):
        m,p,d=self.setup_decoder('<POINT_0><POINT_5><POINT_9>1')
        result=decode_inventory(m,p,[1]*1025,d,(448,448),finish_reason='stop')
        self.assertEqual(result['points'][0]['cell_xy'],[1,2])
        with self.assertRaises(ValueError):decode_inventory(m,p,[1]*4097,d,(448,448),finish_reason='stop')

    def test_inventory_fragments_and_truncation_still_refuse(self):
        m,p,d=self.setup_decoder('<POINT_0><POINT_5><POINT_9>1<POINT_0>')
        with self.assertRaises(ValueError):decode_inventory(m,p,[1],d,(448,448),finish_reason='stop')
        with self.assertRaises(ValueError):decode_inventory(m,p,[1],d,(448,448),finish_reason='length')


if __name__=='__main__':unittest.main()
