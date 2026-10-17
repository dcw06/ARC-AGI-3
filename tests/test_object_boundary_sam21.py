"""Pure geometry/prompt regression tests; no checkpoint, inference or GPU."""
import copy
import unittest
from research.object_discovery_boundaries_v1 import sam21 as S


class SAM21(unittest.TestCase):
    def points(self):return [dict(pixel_xy=[14.25,28.75],cell_xy=[2,4]),dict(pixel_xy=[447.,0.1],cell_xy=[63,0])]

    def test_each_original_float_seed_is_a_separate_positive_object(self):
        result=S.point_prompts(self.points())
        self.assertEqual(result['input_points'],[[[[14.25,28.75]],[[447.,0.1]]]])
        self.assertEqual(result['input_labels'],[[[1],[1]]])

    def test_seeds_never_snap_clip_or_swap_axes(self):
        for xy,cell in (([448,0],[64,0]),([-1,0],[-1,0]),([True,1],[0,0]),([float('nan'),1],[0,0]),([14.2,28.7],[4,2])):
            with self.subTest(xy=xy),self.assertRaises(ValueError):S.point_prompts([dict(pixel_xy=xy,cell_xy=cell)])

    def test_duplicate_seeds_are_not_suppressed(self):
        p=self.points()[0];self.assertEqual(len(S.point_prompts([p,p])['input_points'][0]),2)

    def test_candidate_selected_by_model_quality_and_stable_tie(self):
        self.assertEqual(S.select_candidate([.1,.7,.5]),1)
        self.assertEqual(S.select_candidate([.7,.7,.1]),0)
        for values in ([.2],[.2,float('nan'),.4],[True,.4,.3]):
            with self.assertRaises(ValueError):S.select_candidate(values)

    def test_projection_uses_exact_majority_strict_logit_zero_and_xy(self):
        a=[[-1.]*448 for _ in range(448)]
        # Cell (2,3): 24 positive pixels is insufficient, 25 is enough.
        spots=[(x,y) for y in range(21,28) for x in range(14,21)]
        for x,y in spots[:24]:a[y][x]=1.
        self.assertEqual(S.mask_from_logits(a),[])
        x,y=spots[24];a[y][x]=0.
        self.assertEqual(S.mask_from_logits(a),[])
        a[y][x]=.001
        self.assertEqual(S.mask_from_logits(a),[[2,3]])

    def test_nonfinite_and_wrong_resolution_masks_refuse(self):
        with self.assertRaises(ValueError):S.mask_from_logits([[1.]*64 for _ in range(64)])
        a=[[1.]*448 for _ in range(448)];a[3][2]=float('inf')
        with self.assertRaises(ValueError):S.mask_from_logits(a)

    def test_empty_masks_retained_without_filling_or_seed_repair(self):
        r=S.proposal(1,self.points()[0],[],[.2,.5,.3],1)
        self.assertTrue(r['empty_mask']);self.assertEqual(r['cells'],[]);self.assertIsNone(r['bbox_xyxy'])
        self.assertFalse(r['semantic_object_boundary_certified'])

    def test_disconnected_mask_and_hole_preserved(self):
        r=S.proposal(2,self.points()[0],[[2,3],[4,3],[2,5]],[.9,.4,.2],0)
        self.assertEqual(r['cells'],[[2,3],[4,3],[2,5]])
        self.assertEqual(r['bbox_xyxy'],[2,3,4,5])
        with self.assertRaises(ValueError):S.proposal(2,self.points()[0],[[2,3]],[.9,.4,.2],1)


if __name__=='__main__':unittest.main()
