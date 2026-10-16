"""Reference provenance and semantic-limit checks on synthetic grids."""
import copy
import unittest
from research.object_discovery_boundaries_v1.reference_audit import audit_case,canonical,digest


class ReferenceAudit(unittest.TestCase):
    def setUp(self):
        self.grid=[[0]*64 for _ in range(64)]
        for x,y,v in [(2,2,1),(3,2,1),(2,3,1),(3,3,2)]: self.grid[y][x]=v
        self.pin=digest(canonical(self.grid))
        self.ref=dict(case_id='synthetic',grid_sha256=self.pin,regions=[dict(id='whole',parent_id=None,
            geometry='rectangle',grid_sha256=self.pin,bbox_xyxy=[2,2,3,3],
            target_points=[[2,2],[3,2],[2,3],[3,3]])])

    def test_colored_fragment_is_not_the_multicolor_object(self):
        result=audit_case(self.ref,self.grid);row=result['regions'][0]
        self.assertEqual(row['colors'],2)
        self.assertFalse(row['same_color_component_exact'])
        self.assertEqual(row['boundary_truth_status'],'region_envelope_requires_mask_review')
        self.assertFalse(result['eligible_for_boundary_pass_verdict'])
        self.assertFalse(result['eligible_for_discovery_precision'])

    def test_explicit_cell_mask_preserves_nonrectangular_shape(self):
        r=self.ref['regions'][0];r.update(geometry='mask',target_points=[[2,2],[3,2],[2,3]])
        row=audit_case(self.ref,self.grid)['regions'][0]
        self.assertTrue(row['same_color_component_exact'])
        self.assertFalse(row['fills_bounding_rectangle'])
        self.assertEqual(row['boundary_cells'],3)
        self.assertEqual(row['boundary_truth_status'],'explicit_cells_require_semantic_review')

    def test_corrupt_grid_duplicate_cells_and_parent_cycles_refuse(self):
        changed=copy.deepcopy(self.grid);changed[0][0]=3
        with self.assertRaisesRegex(ValueError,'grid binding'): audit_case(self.ref,changed)
        self.ref['regions'][0]['target_points'].append([2,2])
        with self.assertRaisesRegex(ValueError,'duplicate occupied'): audit_case(self.ref,self.grid)
        self.ref['regions'][0]['target_points'].pop();self.ref['regions'][0]['parent_id']='whole'
        with self.assertRaisesRegex(ValueError,'parent'): audit_case(self.ref,self.grid)

    def test_identical_sibling_masks_are_not_independent_objects_by_default(self):
        other=copy.deepcopy(self.ref['regions'][0]);other['id']='other';self.ref['regions'].append(other)
        result=audit_case(self.ref,self.grid)
        self.assertEqual(result['identical_sibling_masks_for_review'],[['whole','other']])
        self.assertFalse(result['reference_exhaustiveness_verified'])

    def test_group_union_keeps_gaps_and_disconnected_parts(self):
        self.ref['regions'][0].update(geometry='group',target_points=[[2,2],[3,3]])
        row=audit_case(self.ref,self.grid)['regions'][0]
        self.assertEqual(row['cells'],2)
        self.assertEqual(row['four_connected_parts'],2)
        self.assertFalse(row['fills_bounding_rectangle'])
        self.assertEqual(row['boundary_truth_status'],'group_cells_require_membership_and_boundary_review')


if __name__=='__main__':unittest.main()
